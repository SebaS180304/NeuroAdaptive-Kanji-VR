-- =====================================================================
-- NeuroAdaptive VR -- schema v1 (Phase 3, F3.4) -- migration 0002 (up)
-- =====================================================================
-- Design: claude/MER_Schema_v1.md (1 Oct 2026). This file is executed as is
-- by backend/alembic/versions/0002_schema_v1.py, and database/schema.sql
-- reproduces it after the Phase 1 part.
--
-- Rule: session_events stays the source of truth. Every table below is a
-- PROJECTION that can be rebuilt: project_session(id) deletes what was
-- projected for a session and replays its events ORDER BY id. Every
-- projected row keeps the id of the event it came from (MER D5).
--
-- One projector, two moments (MER D1, decided with Sebas on 1 Oct: in
-- PL/pgSQL, so the backend, the backfill and psql/pgAdmin run the same code):
--   * live: the backend calls project_event(id) right after inserting each
--     event, in the same transaction;
--   * backfill / repair: project_session(session_id).
-- project_event never raises: a failure is rolled back to its own savepoint
-- (the EXCEPTION block) and recorded in projection_errors, and the event
-- itself is kept (contract §7: telemetry is never lost to a projection).
--
-- Time: all arithmetic in session_elapsed_ms (MER D7).
-- NULL means "not recorded", never "none" (MER D9).
-- =====================================================================

-- ---------------------------------------------------------------------
-- Enums: only vocabularies closed by the spec (MER D8)
-- ---------------------------------------------------------------------
CREATE TYPE trial_type AS ENUM (
    'T1_MEANING_TO_KANJI', 'T2_KANJI_TO_MEANING', 'T3_KANJI_TO_READING');

-- ESL and LAL share one scale (contract §3).
CREATE TYPE stimulation_level AS ENUM (
    'OFF', 'MINIMAL', 'BASELINE', 'FOCUS', 'LOW', 'MEDIUM', 'HIGH');

CREATE TYPE kanji_role AS ENUM ('EXPERIMENTAL', 'RESERVE', 'TUTORIAL');

-- ---------------------------------------------------------------------
-- 0. Index for projection and backfill
-- ---------------------------------------------------------------------
CREATE INDEX ix_session_events_session_trial
    ON session_events (session_id, (payload ->> 'trial_id'))
    WHERE payload ? 'trial_id';

-- ---------------------------------------------------------------------
-- 1. Content catalogue (reference data, NOT a projection)
-- ---------------------------------------------------------------------
-- Seeded by database/seed_kanji_items.sql, which tools/kanji_seed_sql.py
-- generates from unity-client/Assets/Resources/kanji_content.json (and
-- tools/kanji_metrics.py --export regenerates together with the json).
CREATE TABLE kanji_items (
    kanji_id               VARCHAR(32) PRIMARY KEY,          -- KANJI_YAMA
    kanji_char             VARCHAR(4)  NOT NULL UNIQUE,
    meaning                VARCHAR(64) NOT NULL,
    target_reading         VARCHAR(16) NOT NULL,
    role                   kanji_role  NOT NULL,
    experimental_set       CHAR(1) CHECK (experimental_set IN ('A','B','C')),
    strokes                SMALLINT NOT NULL,
    morae                  SMALLINT NOT NULL,
    assembly_groups        SMALLINT NOT NULL,
    common_readings        SMALLINT NOT NULL,
    perimetric_complexity  NUMERIC(7,2),
    imageability_glyph     SMALLINT CHECK (imageability_glyph BETWEEN 1 AND 5),
    imageability_object    SMALLINT CHECK (imageability_object BETWEEN 1 AND 5),
    discovery_type         VARCHAR(16) NOT NULL,
    textbook_lesson        VARCHAR(16),
    content_schema_version INTEGER NOT NULL,                 -- kanji_content.json schemaVersion
    content_sha256         CHAR(64) NOT NULL,                -- hash of the seeded json
    loaded_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_kanji_set_role CHECK (
        (role = 'EXPERIMENTAL') = (experimental_set IS NOT NULL))
);

-- ---------------------------------------------------------------------
-- 2. Session structure
-- ---------------------------------------------------------------------
-- One row per STATE_ENTERED. visit_seq is the event's rank among the
-- session's STATE_ENTERED events, so it does not depend on projection order.
-- exited_elapsed_ms = entry of the next one (filled when it arrives).
CREATE TABLE session_states (
    session_id                UUID NOT NULL REFERENCES experiment_sessions(id) ON DELETE CASCADE,
    visit_seq                 SMALLINT NOT NULL,
    state                     game_flow_state NOT NULL,
    entered_event_id          BIGINT NOT NULL UNIQUE REFERENCES session_events(id) ON DELETE CASCADE,
    entered_elapsed_ms        INTEGER NOT NULL,
    exited_elapsed_ms         INTEGER,
    transition_sound_lead_ms  INTEGER,                       -- §5.9; NULL on S1
    esl                       stimulation_level,
    lal                       stimulation_level,
    PRIMARY KEY (session_id, visit_seq),
    CHECK (exited_elapsed_ms IS NULL OR exited_elapsed_ms >= entered_elapsed_ms)
);

-- The block plan (TRIAL_SEQUENCE_GENERATED, contract §5.8)
CREATE TABLE trial_blocks (
    session_id           UUID NOT NULL REFERENCES experiment_sessions(id) ON DELETE CASCADE,
    block_state          game_flow_state NOT NULL,
    source_event_id      BIGINT NOT NULL UNIQUE REFERENCES session_events(id) ON DELETE CASCADE,
    generated_elapsed_ms INTEGER NOT NULL,
    kanji_set            CHAR(1),
    seed_raw             VARCHAR(64),
    seed                 BIGINT,
    block_seed           BIGINT,
    trial_count          SMALLINT NOT NULL,
    min_lag_requested    SMALLINT,
    min_lag_achieved     SMALLINT,
    distinct_pairs       SMALLINT,
    ordering_attempts    INTEGER,
    PRIMARY KEY (session_id, block_state)
);

-- Each entry of `sequence`: what was PLANNED.
CREATE TABLE planned_trials (
    session_id      UUID NOT NULL,
    trial_id        VARCHAR(16) NOT NULL,                    -- S7-007
    block_state     game_flow_state NOT NULL,
    trial_sequence  SMALLINT NOT NULL,
    kanji_id        VARCHAR(32) NOT NULL REFERENCES kanji_items(kanji_id),
    trial_type      trial_type NOT NULL,
    options         VARCHAR(32)[] NOT NULL,
    correct_option  VARCHAR(32) NOT NULL,
    PRIMARY KEY (session_id, trial_id),
    UNIQUE (session_id, block_state, trial_sequence),
    FOREIGN KEY (session_id, block_state)
        REFERENCES trial_blocks(session_id, block_state) ON DELETE CASCADE,
    CHECK (cardinality(options) = 4),
    CHECK (correct_option = ANY (options))
);

-- ---------------------------------------------------------------------
-- 3. Trial: what HAPPENED. One row per trial.
-- ---------------------------------------------------------------------
-- TRIAL_STARTED creates the row; ANSWER_SELECTED and TRIAL_COMPLETED fill
-- it in. No FK to planned_trials on purpose (§5.8, MER D10).
CREATE TABLE trials (
    session_id            UUID NOT NULL REFERENCES experiment_sessions(id) ON DELETE CASCADE,
    trial_id              VARCHAR(16) NOT NULL,
    block_state           game_flow_state NOT NULL,
    trial_sequence        SMALLINT NOT NULL,
    trial_type            trial_type NOT NULL,
    kanji_id              VARCHAR(32) NOT NULL REFERENCES kanji_items(kanji_id),
    contract_version      SMALLINT NOT NULL,                 -- payload.schema_version
    esl                   stimulation_level NOT NULL,
    lal                   stimulation_level NOT NULL,
    -- presentation (TRIAL_STARTED)
    started_event_id      BIGINT NOT NULL UNIQUE REFERENCES session_events(id) ON DELETE CASCADE,
    started_elapsed_ms    INTEGER NOT NULL,
    options               VARCHAR(32)[] NOT NULL,
    correct_option        VARCHAR(32) NOT NULL,
    hint_available        BOOLEAN NOT NULL,
    -- response (ANSWER_SELECTED)
    answer_event_id       BIGINT UNIQUE REFERENCES session_events(id) ON DELETE CASCADE,
    answered_elapsed_ms   INTEGER,
    selected_option       VARCHAR(32),
    is_correct            BOOLEAN,
    response_time_ms      INTEGER CHECK (response_time_ms >= 0),
    timed_out             BOOLEAN,
    -- close (TRIAL_COMPLETED)
    completed_event_id    BIGINT UNIQUE REFERENCES session_events(id) ON DELETE CASCADE,
    completed_elapsed_ms  INTEGER,
    hint_count            SMALLINT,
    cues_presented        VARCHAR(40)[],
    -- stimuli for F4 (§5.9). NULL = not recorded (rows before 30 Sep), NOT "none"
    feedback_shown          BOOLEAN,
    feedback_audio_source   VARCHAR(16) CHECK (feedback_audio_source IN ('AUTHORED','TTS_PLACEHOLDER','NONE')),
    feedback_audio_ms       INTEGER,
    result_sound            VARCHAR(12) CHECK (result_sound IN ('CORRECT','INCORRECT','NONE')),
    result_sound_offset_ms  INTEGER,
    result_sound_ms         INTEGER,
    card_animation          VARCHAR(16) CHECK (card_animation IN ('CORRECT_POP','NONE')),
    -- idle in the response window (§5.10), with the thresholds in force
    idle_ms               INTEGER,
    idle_episodes         SMALLINT,
    idle_longest_ms       INTEGER,
    idle_min_ms           INTEGER,
    idle_head_deg_s       REAL,
    idle_ray_deg_s        REAL,
    PRIMARY KEY (session_id, trial_id),
    UNIQUE (session_id, block_state, trial_sequence),
    CHECK (cardinality(options) = 4),
    CHECK (correct_option = ANY (options)),
    CHECK (selected_option IS NULL OR selected_option = ANY (options)),
    CHECK (answered_elapsed_ms IS NULL OR answered_elapsed_ms >= started_elapsed_ms),
    CHECK (completed_elapsed_ms IS NULL OR answered_elapsed_ms IS NOT NULL),
    -- §5.9: without feedback there is no reading audio, result sound or animation
    CHECK (feedback_shown IS DISTINCT FROM FALSE OR
           (feedback_audio_ms = 0 AND result_sound = 'NONE' AND card_animation = 'NONE')),
    CHECK ((result_sound = 'NONE') = (result_sound_offset_ms IS NULL) OR result_sound IS NULL)
);
CREATE INDEX ix_trials_kanji ON trials (kanji_id);

-- HINT_REQUESTED: one row per request (even when nothing is granted, §5.5).
-- request_seq is the event's rank among the trial's HINT_REQUESTED events.
CREATE TABLE hint_requests (
    source_event_id            BIGINT PRIMARY KEY REFERENCES session_events(id) ON DELETE CASCADE,
    session_id                 UUID NOT NULL,
    trial_id                   VARCHAR(16) NOT NULL,
    request_seq                SMALLINT NOT NULL,
    elapsed_ms                 INTEGER NOT NULL,
    time_since_trial_start_ms  INTEGER NOT NULL,
    hint_available             BOOLEAN NOT NULL,
    cues_granted               VARCHAR(40)[] NOT NULL,       -- '{}' when nothing was granted
    UNIQUE (session_id, trial_id, request_seq),
    FOREIGN KEY (session_id, trial_id) REFERENCES trials(session_id, trial_id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- 4. Environment (ESL)
-- ---------------------------------------------------------------------
CREATE TABLE environment_applications (
    source_event_id              BIGINT PRIMARY KEY REFERENCES session_events(id) ON DELETE CASCADE,
    session_id                   UUID NOT NULL REFERENCES experiment_sessions(id) ON DELETE CASCADE,
    elapsed_ms                   INTEGER NOT NULL,
    state                        game_flow_state NOT NULL,
    esl                          stimulation_level NOT NULL, -- from the context block (§5.7)
    profile_name                 VARCHAR(64) NOT NULL,
    prop_count                   SMALLINT NOT NULL,
    mover_count                  SMALLINT NOT NULL,
    active_props                 VARCHAR(64)[],              -- NULL before 29 Sep
    active_movers                VARCHAR(64)[],
    peripheral_interval_min_ms   INTEGER,
    peripheral_interval_max_ms   INTEGER,
    max_tier                     SMALLINT,
    seed                         BIGINT,
    seed_source                  VARCHAR(12) CHECK (seed_source IN ('SESSION','FALLBACK','OVERRIDE')),
    selection_seed               BIGINT
);
CREATE INDEX ix_env_app_session_time ON environment_applications (session_id, elapsed_ms);

CREATE TABLE peripheral_events (
    source_event_id  BIGINT PRIMARY KEY REFERENCES session_events(id) ON DELETE CASCADE,
    session_id       UUID NOT NULL REFERENCES experiment_sessions(id) ON DELETE CASCADE,
    elapsed_ms       INTEGER NOT NULL,
    state            game_flow_state NOT NULL,
    esl              stimulation_level NOT NULL,
    event_index      INTEGER NOT NULL,
    object_name      VARCHAR(64) NOT NULL,
    duration_ms      INTEGER NOT NULL,
    trial_id         VARCHAR(16),                            -- as received; the views attribute by time
    UNIQUE (session_id, event_index)
);
CREATE INDEX ix_peripheral_session_time ON peripheral_events (session_id, elapsed_ms);

-- ---------------------------------------------------------------------
-- 5. Behaviour: HEAD_AWAY / HEAD_RETURNED (§5.10) -> one episode
-- ---------------------------------------------------------------------
CREATE TABLE head_away_episodes (
    session_id             UUID NOT NULL REFERENCES experiment_sessions(id) ON DELETE CASCADE,
    episode                INTEGER NOT NULL,
    away_event_id          BIGINT NOT NULL UNIQUE REFERENCES session_events(id) ON DELETE CASCADE,
    returned_event_id      BIGINT UNIQUE REFERENCES session_events(id) ON DELETE CASCADE,
    state_at_onset         game_flow_state NOT NULL,
    trial_id_at_onset      VARCHAR(16),
    confirmed_elapsed_ms   INTEGER NOT NULL,                 -- elapsed of HEAD_AWAY
    onset_elapsed_ms       INTEGER NOT NULL,                 -- confirmed + onset_offset_ms
    returned_elapsed_ms    INTEGER,                          -- onset + duration_ms
    duration_ms            INTEGER,
    limit_crossed          VARCHAR(12) NOT NULL CHECK (limit_crossed IN ('YAW','PITCH_UP','PITCH_DOWN')),
    yaw_deg                REAL,
    pitch_deg              REAL,
    max_abs_yaw_deg        REAL,
    max_pitch_up_deg       REAL,
    max_pitch_down_deg     REAL,
    return_reason          VARCHAR(16) CHECK (return_reason IN ('RETURNED','TRACKING_LOST','SESSION_END')),
    -- thresholds in force (to validate)
    yaw_limit_deg          REAL NOT NULL,
    pitch_up_limit_deg     REAL NOT NULL,
    pitch_down_limit_deg   REAL NOT NULL,
    min_away_ms            INTEGER NOT NULL,
    hysteresis_deg         REAL,
    min_return_ms          INTEGER,
    PRIMARY KEY (session_id, episode),
    CHECK (onset_elapsed_ms <= confirmed_elapsed_ms),
    CHECK ((returned_event_id IS NULL) = (duration_ms IS NULL))
);
CREATE INDEX ix_head_away_session_time ON head_away_episodes (session_id, onset_elapsed_ms);

-- ---------------------------------------------------------------------
-- 6. S5 learning and assembly (S2 example + S5)
-- ---------------------------------------------------------------------
CREATE TABLE kanji_exposures (
    source_event_id  BIGINT PRIMARY KEY REFERENCES session_events(id) ON DELETE CASCADE,
    session_id       UUID NOT NULL REFERENCES experiment_sessions(id) ON DELETE CASCADE,
    exposure_index   SMALLINT NOT NULL,
    kanji_id         VARCHAR(32) NOT NULL REFERENCES kanji_items(kanji_id),
    elapsed_ms       INTEGER NOT NULL,
    discovery_type   VARCHAR(16),
    exposure_ms      INTEGER,
    stage_ms         INTEGER[],
    stages_authored  BOOLEAN,
    audio_played     BOOLEAN,
    audio_source     VARCHAR(16) CHECK (audio_source IN ('AUTHORED','TTS_PLACEHOLDER','NONE')),
    assembly_mode    VARCHAR(16) CHECK (assembly_mode IN ('RAY','NOT_IMPLEMENTED')),
    UNIQUE (session_id, exposure_index)
);

-- ASSEMBLY_COMPLETED. exposure_index = 0 is the tutorial example (S2).
CREATE TABLE assemblies (
    session_id            UUID NOT NULL REFERENCES experiment_sessions(id) ON DELETE CASCADE,
    exposure_index        SMALLINT NOT NULL,
    source_event_id       BIGINT NOT NULL UNIQUE REFERENCES session_events(id) ON DELETE CASCADE,
    state                 game_flow_state NOT NULL,
    kanji_id              VARCHAR(32) NOT NULL REFERENCES kanji_items(kanji_id),
    completed_elapsed_ms  INTEGER NOT NULL,
    duration_ms           INTEGER NOT NULL,
    incorrect_attempts    SMALLINT NOT NULL,
    segment_count         SMALLINT NOT NULL,
    segments_placed       SMALLINT NOT NULL,
    hints_shown           SMALLINT NOT NULL,
    row_order             VARCHAR(32)[],
    segments_authored     BOOLEAN,
    forced_by_researcher  BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (session_id, exposure_index)
);

-- ASSEMBLY_SEGMENT_PLACED: one attempt per row. No FK to assemblies: the
-- attempts arrive before the close, and an aborted session leaves attempts
-- without one.
CREATE TABLE assembly_attempts (
    source_event_id      BIGINT PRIMARY KEY REFERENCES session_events(id) ON DELETE CASCADE,
    session_id           UUID NOT NULL REFERENCES experiment_sessions(id) ON DELETE CASCADE,
    exposure_index       SMALLINT NOT NULL,
    elapsed_ms           INTEGER NOT NULL,
    state                game_flow_state NOT NULL,
    kanji_id             VARCHAR(32) NOT NULL REFERENCES kanji_items(kanji_id),
    attempt              SMALLINT NOT NULL,
    slot_index           SMALLINT NOT NULL,
    segment_id           VARCHAR(32) NOT NULL,
    expected_segment_id  VARCHAR(32) NOT NULL,
    is_correct           BOOLEAN NOT NULL,
    selected_ms          INTEGER,
    placed_ms            INTEGER,
    hint_shown           BOOLEAN,
    segments_authored    BOOLEAN,
    UNIQUE (session_id, exposure_index, attempt),
    CHECK (is_correct = (segment_id = expected_segment_id))
);

-- ---------------------------------------------------------------------
-- 7. Projection errors (the event is kept regardless)
-- ---------------------------------------------------------------------
CREATE TABLE projection_errors (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id      BIGINT NOT NULL REFERENCES session_events(id) ON DELETE CASCADE,
    session_id    UUID NOT NULL REFERENCES experiment_sessions(id) ON DELETE CASCADE,
    event_type    VARCHAR(64) NOT NULL,
    error_code    VARCHAR(32) NOT NULL,   -- MISSING_FIELD, UNKNOWN_ENUM, ORPHAN_EVENT, DUPLICATE, FK_VIOLATION, CHECK_VIOLATION, BAD_VALUE, OTHER
    detail        TEXT,
    occurred_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at   TIMESTAMPTZ
);
CREATE INDEX ix_projection_errors_open ON projection_errors (session_id) WHERE resolved_at IS NULL;

-- =====================================================================
-- PROJECTOR
-- =====================================================================

-- Required field: the text value, or a MISSING_FIELD error (SQLSTATE P0101).
CREATE FUNCTION proj_req(p JSONB, k TEXT) RETURNS TEXT
LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
    IF NOT (p ? k) OR jsonb_typeof(p -> k) = 'null' THEN
        RAISE EXCEPTION 'MISSING_FIELD: %', k USING ERRCODE = 'P0101';
    END IF;
    RETURN p ->> k;
END $$;

-- JSON array of strings -> text[]. NULL when the key is absent or null
-- (MER D9: absent means "not recorded").
CREATE FUNCTION proj_arr(p JSONB, k TEXT) RETURNS TEXT[]
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE WHEN jsonb_typeof(p -> k) = 'array'
                THEN ARRAY(SELECT jsonb_array_elements_text(p -> k)) END
$$;

-- JSON array of numbers -> int[]
CREATE FUNCTION proj_int_arr(p JSONB, k TEXT) RETURNS INTEGER[]
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE WHEN jsonb_typeof(p -> k) = 'array'
                THEN ARRAY(SELECT (x)::numeric::int FROM jsonb_array_elements_text(p -> k) x) END
$$;

-- ANSWER_SELECTED / TRIAL_COMPLETED that matched no row: ORPHAN when the trial
-- does not exist, DUPLICATE when it already has another answer/completion.
CREATE FUNCTION proj_orphan_or_dup(e session_events, col TEXT) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    other BIGINT;
BEGIN
    EXECUTE format('SELECT %I FROM trials WHERE session_id = $1 AND trial_id = $2', col)
        INTO other USING e.session_id, e.payload ->> 'trial_id';
    IF other IS NOT NULL THEN
        RAISE EXCEPTION 'DUPLICATE: trial % already has % = %', e.payload ->> 'trial_id', col, other
            USING ERRCODE = 'P0103';
    END IF;
    RAISE EXCEPTION 'ORPHAN_EVENT: no trial % for this %', e.payload ->> 'trial_id', e.event_type
        USING ERRCODE = 'P0102';
END $$;

-- The projection of ONE event, without error handling: project_event wraps it.
-- Every INSERT is ON CONFLICT DO NOTHING and every UPDATE writes the same
-- values again, so projecting an event twice changes nothing (idempotent).
CREATE FUNCTION proj_apply(e session_events) RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    p   JSONB := e.payload;
    ms  INTEGER;
    n   INTEGER;
    seq INTEGER;
BEGIN
    -- Events kept only in the log (MER D13) and unknown ones: nothing to do.
    IF e.event_type NOT IN (
        'STATE_ENTERED', 'TRIAL_SEQUENCE_GENERATED', 'TRIAL_STARTED', 'ANSWER_SELECTED',
        'TRIAL_COMPLETED', 'HINT_REQUESTED', 'ENVIRONMENT_APPLIED', 'PERIPHERAL_EVENT',
        'HEAD_AWAY', 'HEAD_RETURNED', 'KANJI_EXPOSED', 'ASSEMBLY_SEGMENT_PLACED',
        'ASSEMBLY_COMPLETED') THEN
        RETURN;
    END IF;

    ms := proj_req(p, 'session_elapsed_ms')::numeric::int;

    CASE e.event_type

    WHEN 'STATE_ENTERED' THEN
        SELECT count(*) INTO seq FROM session_events s
        WHERE s.session_id = e.session_id AND s.event_type = 'STATE_ENTERED' AND s.id <= e.id;
        INSERT INTO session_states (session_id, visit_seq, state, entered_event_id,
                                    entered_elapsed_ms, transition_sound_lead_ms, esl, lal)
        VALUES (e.session_id, seq, proj_req(p, 'state')::game_flow_state, e.id, ms,
                (p ->> 'transition_sound_lead_ms')::numeric::int,
                (p ->> 'esl')::stimulation_level, (p ->> 'lal')::stimulation_level)
        ON CONFLICT (entered_event_id) DO NOTHING;
        -- close the previous state, and this one if its successor came first
        UPDATE session_states SET exited_elapsed_ms = ms
        WHERE session_id = e.session_id AND visit_seq = seq - 1;
        UPDATE session_states cur SET exited_elapsed_ms = nxt.entered_elapsed_ms
        FROM session_states nxt
        WHERE cur.session_id = e.session_id AND cur.visit_seq = seq
          AND nxt.session_id = e.session_id AND nxt.visit_seq = seq + 1;

    WHEN 'TRIAL_SEQUENCE_GENERATED' THEN
        INSERT INTO trial_blocks (session_id, block_state, source_event_id, generated_elapsed_ms,
                                  kanji_set, seed_raw, seed, block_seed, trial_count,
                                  min_lag_requested, min_lag_achieved, distinct_pairs, ordering_attempts)
        VALUES (e.session_id, proj_req(p, 'block_state')::game_flow_state, e.id, ms,
                p ->> 'kanji_set', p ->> 'seed_raw', (p ->> 'seed')::bigint, (p ->> 'block_seed')::bigint,
                proj_req(p, 'trial_count')::int, (p ->> 'min_lag_requested')::int,
                (p ->> 'min_lag_achieved')::int, (p ->> 'distinct_pairs')::int,
                (p ->> 'ordering_attempts')::int)
        ON CONFLICT (source_event_id) DO NOTHING;
        IF jsonb_typeof(p -> 'sequence') <> 'array' THEN
            RAISE EXCEPTION 'MISSING_FIELD: sequence' USING ERRCODE = 'P0101';
        END IF;
        INSERT INTO planned_trials (session_id, trial_id, block_state, trial_sequence, kanji_id,
                                    trial_type, options, correct_option)
        SELECT e.session_id,
               split_part(p ->> 'block_state', '_', 1) || '-' || lpad(proj_req(x, 'trial_sequence'), 3, '0'),
               (p ->> 'block_state')::game_flow_state, (x ->> 'trial_sequence')::int,
               proj_req(x, 'kanji_id'), proj_req(x, 'trial_type')::trial_type,
               proj_arr(x, 'options'), proj_req(x, 'correct_option')
        FROM jsonb_array_elements(p -> 'sequence') x
        ON CONFLICT DO NOTHING;

    WHEN 'TRIAL_STARTED' THEN
        INSERT INTO trials (session_id, trial_id, block_state, trial_sequence, trial_type, kanji_id,
                            contract_version, esl, lal, started_event_id, started_elapsed_ms,
                            options, correct_option, hint_available)
        VALUES (e.session_id, proj_req(p, 'trial_id'), proj_req(p, 'state')::game_flow_state,
                proj_req(p, 'trial_sequence')::int, proj_req(p, 'trial_type')::trial_type,
                proj_req(p, 'kanji_id'), proj_req(p, 'schema_version')::int,
                proj_req(p, 'esl')::stimulation_level, proj_req(p, 'lal')::stimulation_level,
                e.id, ms, proj_arr(p, 'options'), proj_req(p, 'correct_option'),
                proj_req(p, 'hint_available')::boolean)
        ON CONFLICT (started_event_id) DO NOTHING;

    WHEN 'ANSWER_SELECTED' THEN
        UPDATE trials SET answer_event_id = e.id, answered_elapsed_ms = ms,
               selected_option = proj_req(p, 'selected_option'),
               is_correct = proj_req(p, 'is_correct')::boolean,
               response_time_ms = proj_req(p, 'response_time_ms')::numeric::int,
               timed_out = COALESCE((p ->> 'timed_out')::boolean, FALSE)
        WHERE session_id = e.session_id AND trial_id = proj_req(p, 'trial_id')
          AND (answer_event_id IS NULL OR answer_event_id = e.id);
        GET DIAGNOSTICS n = ROW_COUNT;
        IF n = 0 THEN
            PERFORM proj_orphan_or_dup(e, 'answer_event_id');
        END IF;

    WHEN 'TRIAL_COMPLETED' THEN
        UPDATE trials SET completed_event_id = e.id, completed_elapsed_ms = ms,
               hint_count = (p ->> 'hint_count')::int,
               cues_presented = proj_arr(p, 'cues_presented'),
               feedback_shown = (p ->> 'feedback_shown')::boolean,
               feedback_audio_source = p ->> 'feedback_audio_source',
               feedback_audio_ms = (p ->> 'feedback_audio_ms')::numeric::int,
               result_sound = p ->> 'result_sound',
               result_sound_offset_ms = (p ->> 'result_sound_offset_ms')::numeric::int,
               result_sound_ms = (p ->> 'result_sound_ms')::numeric::int,
               card_animation = p ->> 'card_animation',
               idle_ms = (p ->> 'idle_ms')::numeric::int,
               idle_episodes = (p ->> 'idle_episodes')::int,
               idle_longest_ms = (p ->> 'idle_longest_ms')::numeric::int,
               idle_min_ms = (p ->> 'idle_min_ms')::numeric::int,
               idle_head_deg_s = (p ->> 'idle_head_deg_s')::real,
               idle_ray_deg_s = (p ->> 'idle_ray_deg_s')::real
        WHERE session_id = e.session_id AND trial_id = proj_req(p, 'trial_id')
          AND (completed_event_id IS NULL OR completed_event_id = e.id);
        GET DIAGNOSTICS n = ROW_COUNT;
        IF n = 0 THEN
            PERFORM proj_orphan_or_dup(e, 'completed_event_id');
        END IF;

    WHEN 'HINT_REQUESTED' THEN
        SELECT count(*) INTO seq FROM session_events s
        WHERE s.session_id = e.session_id AND s.event_type = 'HINT_REQUESTED'
          AND s.payload ->> 'trial_id' = p ->> 'trial_id' AND s.id <= e.id;
        INSERT INTO hint_requests (source_event_id, session_id, trial_id, request_seq, elapsed_ms,
                                   time_since_trial_start_ms, hint_available, cues_granted)
        VALUES (e.id, e.session_id, proj_req(p, 'trial_id'), seq, ms,
                proj_req(p, 'time_since_trial_start_ms')::numeric::int,
                proj_req(p, 'hint_available')::boolean,
                COALESCE(proj_arr(p, 'hint_type'), '{}'))
        ON CONFLICT (source_event_id) DO NOTHING;

    WHEN 'ENVIRONMENT_APPLIED' THEN
        INSERT INTO environment_applications
        VALUES (e.id, e.session_id, ms, proj_req(p, 'state')::game_flow_state,
                proj_req(p, 'esl')::stimulation_level, proj_req(p, 'profile_name'),
                proj_req(p, 'prop_count')::int, proj_req(p, 'mover_count')::int,
                proj_arr(p, 'active_props'), proj_arr(p, 'active_movers'),
                (p ->> 'peripheral_interval_min_ms')::numeric::int,
                (p ->> 'peripheral_interval_max_ms')::numeric::int,
                (p ->> 'max_tier')::int, (p ->> 'seed')::bigint, p ->> 'seed_source',
                (p ->> 'selection_seed')::bigint)
        ON CONFLICT (source_event_id) DO NOTHING;

    WHEN 'PERIPHERAL_EVENT' THEN
        INSERT INTO peripheral_events
        VALUES (e.id, e.session_id, ms, proj_req(p, 'state')::game_flow_state,
                proj_req(p, 'esl')::stimulation_level, proj_req(p, 'event_index')::int,
                proj_req(p, 'object_name'), proj_req(p, 'duration_ms')::numeric::int,
                p ->> 'trial_id')
        ON CONFLICT (source_event_id) DO NOTHING;

    WHEN 'HEAD_AWAY' THEN
        INSERT INTO head_away_episodes (session_id, episode, away_event_id, state_at_onset,
                                        trial_id_at_onset, confirmed_elapsed_ms, onset_elapsed_ms,
                                        limit_crossed, yaw_deg, pitch_deg, yaw_limit_deg,
                                        pitch_up_limit_deg, pitch_down_limit_deg, min_away_ms)
        VALUES (e.session_id, proj_req(p, 'episode')::int, e.id, proj_req(p, 'state')::game_flow_state,
                p ->> 'trial_id', ms, ms + proj_req(p, 'onset_offset_ms')::numeric::int,
                proj_req(p, 'limit'), (p ->> 'yaw_deg')::real, (p ->> 'pitch_deg')::real,
                proj_req(p, 'yaw_limit_deg')::real, proj_req(p, 'pitch_up_limit_deg')::real,
                proj_req(p, 'pitch_down_limit_deg')::real, proj_req(p, 'min_away_ms')::numeric::int)
        ON CONFLICT (away_event_id) DO NOTHING;

    WHEN 'HEAD_RETURNED' THEN
        UPDATE head_away_episodes SET returned_event_id = e.id,
               duration_ms = proj_req(p, 'duration_ms')::numeric::int,
               returned_elapsed_ms = onset_elapsed_ms + (p ->> 'duration_ms')::numeric::int,
               max_abs_yaw_deg = (p ->> 'max_abs_yaw_deg')::real,
               max_pitch_up_deg = (p ->> 'max_pitch_up_deg')::real,
               max_pitch_down_deg = (p ->> 'max_pitch_down_deg')::real,
               return_reason = p ->> 'reason',
               hysteresis_deg = (p ->> 'hysteresis_deg')::real,
               min_return_ms = (p ->> 'min_return_ms')::numeric::int
        WHERE session_id = e.session_id AND episode = proj_req(p, 'episode')::int
          AND (returned_event_id IS NULL OR returned_event_id = e.id);
        GET DIAGNOSTICS n = ROW_COUNT;
        IF n = 0 THEN
            IF EXISTS (SELECT 1 FROM head_away_episodes
                       WHERE session_id = e.session_id AND episode = (p ->> 'episode')::int) THEN
                RAISE EXCEPTION 'DUPLICATE: episode % already returned', p ->> 'episode' USING ERRCODE = 'P0103';
            END IF;
            RAISE EXCEPTION 'ORPHAN_EVENT: no HEAD_AWAY episode %', p ->> 'episode' USING ERRCODE = 'P0102';
        END IF;

    WHEN 'KANJI_EXPOSED' THEN
        INSERT INTO kanji_exposures
        VALUES (e.id, e.session_id, proj_req(p, 'exposure_index')::int, proj_req(p, 'kanji_id'), ms,
                p ->> 'discovery_type', (p ->> 'exposure_ms')::numeric::int, proj_int_arr(p, 'stage_ms'),
                (p ->> 'stages_authored')::boolean, (p ->> 'audio_played')::boolean,
                p ->> 'audio_source', p ->> 'assembly')
        ON CONFLICT (source_event_id) DO NOTHING;

    WHEN 'ASSEMBLY_SEGMENT_PLACED' THEN
        INSERT INTO assembly_attempts
        VALUES (e.id, e.session_id, proj_req(p, 'exposure_index')::int, ms,
                proj_req(p, 'state')::game_flow_state, proj_req(p, 'kanji_id'),
                proj_req(p, 'attempt')::int, proj_req(p, 'slot_index')::int,
                proj_req(p, 'segment_id'), proj_req(p, 'expected_segment_id'),
                proj_req(p, 'is_correct')::boolean, (p ->> 'selected_ms')::numeric::int,
                (p ->> 'placed_ms')::numeric::int, (p ->> 'hint_shown')::boolean,
                (p ->> 'segments_authored')::boolean)
        ON CONFLICT (source_event_id) DO NOTHING;

    WHEN 'ASSEMBLY_COMPLETED' THEN
        INSERT INTO assemblies
        VALUES (e.session_id, proj_req(p, 'exposure_index')::int, e.id,
                proj_req(p, 'state')::game_flow_state, proj_req(p, 'kanji_id'), ms,
                proj_req(p, 'duration_ms')::numeric::int, proj_req(p, 'incorrect_attempts')::int,
                proj_req(p, 'segment_count')::int, proj_req(p, 'segments_placed')::int,
                proj_req(p, 'hints_shown')::int, proj_arr(p, 'row_order'),
                (p ->> 'segments_authored')::boolean,
                COALESCE((p ->> 'forced_by_researcher')::boolean, FALSE))
        ON CONFLICT (source_event_id) DO NOTHING;

    END CASE;
END $$;

-- Live entry point. Never raises: a failure is undone to the savepoint the
-- EXCEPTION block opens, logged in projection_errors, and FALSE is returned.
CREATE FUNCTION project_event(p_event_id BIGINT) RETURNS BOOLEAN
LANGUAGE plpgsql AS $$
DECLARE
    e     session_events;
    code  TEXT;
BEGIN
    SELECT * INTO e FROM session_events WHERE id = p_event_id;
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;
    BEGIN
        PERFORM proj_apply(e);
        RETURN TRUE;
    EXCEPTION WHEN OTHERS THEN
        code := CASE SQLSTATE
            WHEN 'P0101' THEN 'MISSING_FIELD'
            WHEN 'P0102' THEN 'ORPHAN_EVENT'
            WHEN 'P0103' THEN 'DUPLICATE'
            WHEN '22P02' THEN CASE WHEN SQLERRM LIKE '%enum%' THEN 'UNKNOWN_ENUM' ELSE 'BAD_VALUE' END
            WHEN '23505' THEN 'DUPLICATE'
            WHEN '23503' THEN 'FK_VIOLATION'
            WHEN '23514' THEN 'CHECK_VIOLATION'
            WHEN '23502' THEN 'MISSING_FIELD'
            ELSE 'OTHER' END;
        INSERT INTO projection_errors (event_id, session_id, event_type, error_code, detail)
        VALUES (e.id, e.session_id, e.event_type, code, SQLSTATE || ': ' || SQLERRM);
        RETURN FALSE;
    END;
END $$;

-- Backfill / repair: rebuild everything projected for one session. Open
-- errors from earlier passes are marked resolved (kept as history); this
-- pass records its own. Returns how many events failed.
CREATE FUNCTION project_session(p_session UUID) RETURNS INTEGER
LANGUAGE plpgsql AS $$
DECLARE
    r       RECORD;
    failed  INTEGER := 0;
BEGIN
    DELETE FROM hint_requests            WHERE session_id = p_session;
    DELETE FROM trials                   WHERE session_id = p_session;
    DELETE FROM planned_trials           WHERE session_id = p_session;
    DELETE FROM trial_blocks             WHERE session_id = p_session;
    DELETE FROM session_states           WHERE session_id = p_session;
    DELETE FROM environment_applications WHERE session_id = p_session;
    DELETE FROM peripheral_events        WHERE session_id = p_session;
    DELETE FROM head_away_episodes       WHERE session_id = p_session;
    DELETE FROM kanji_exposures          WHERE session_id = p_session;
    DELETE FROM assemblies               WHERE session_id = p_session;
    DELETE FROM assembly_attempts        WHERE session_id = p_session;
    UPDATE projection_errors SET resolved_at = now()
    WHERE session_id = p_session AND resolved_at IS NULL;

    FOR r IN SELECT id FROM session_events WHERE session_id = p_session ORDER BY id LOOP
        IF NOT project_event(r.id) THEN
            failed := failed + 1;
        END IF;
    END LOOP;
    RETURN failed;
END $$;

-- =====================================================================
-- VIEWS
-- =====================================================================

-- Validity interval of each environment application
CREATE VIEW v_environment_intervals AS
SELECT ea.*,
       LEAD(ea.elapsed_ms) OVER (PARTITION BY ea.session_id ORDER BY ea.elapsed_ms, ea.source_event_id)
           AS valid_to_ms
FROM environment_applications ea;

-- Behaviour per trial. Windows (MER §8, decided 1 Oct):
--   response = [started, answered)   -> head-away (comparable with idle_ms and RT)
--   trial    = [started, completed)  -> peripheral events (environment exposure)
CREATE VIEW v_trial_behavior AS
SELECT t.session_id, t.trial_id,
       COALESCE(ha.head_away_count, 0)  AS head_away_count,
       COALESCE(ha.head_away_ms, 0)     AS head_away_ms,
       COALESCE(pe.peripheral_count, 0) AS peripheral_event_count
FROM trials t
LEFT JOIN LATERAL (
    SELECT count(*) AS head_away_count,
           sum(LEAST(COALESCE(h.returned_elapsed_ms, t.answered_elapsed_ms), t.answered_elapsed_ms)
               - GREATEST(h.onset_elapsed_ms, t.started_elapsed_ms))::int AS head_away_ms
    FROM head_away_episodes h
    WHERE h.session_id = t.session_id
      AND t.answered_elapsed_ms IS NOT NULL
      AND h.onset_elapsed_ms < t.answered_elapsed_ms
      AND COALESCE(h.returned_elapsed_ms, t.answered_elapsed_ms) > t.started_elapsed_ms
) ha ON TRUE
LEFT JOIN LATERAL (
    SELECT count(*) AS peripheral_count
    FROM peripheral_events p
    WHERE p.session_id = t.session_id
      AND p.elapsed_ms >= t.started_elapsed_ms
      AND p.elapsed_ms <  COALESCE(t.completed_elapsed_ms, t.answered_elapsed_ms, t.started_elapsed_ms)
) pe ON TRUE;

-- trial_timeline(session, n): one row per trial + aggregates over the
-- observation window (the last n answered trials of the SAME block, the
-- current one included; MER §8). Input of the F5a State Estimator.
CREATE FUNCTION trial_timeline(p_session UUID, p_window INT DEFAULT 3)
RETURNS TABLE (
    participant_id UUID, session_id UUID, condition experimental_condition,
    trial_id VARCHAR, block_state game_flow_state, trial_sequence SMALLINT,
    trial_type trial_type, kanji_id VARCHAR, kanji_char VARCHAR, kanji_set CHAR,
    block_seed BIGINT, is_primary_analysis BOOLEAN,
    started_elapsed_ms INT, answered_elapsed_ms INT, completed_elapsed_ms INT,
    esl stimulation_level, lal stimulation_level,
    env_profile VARCHAR, prop_count SMALLINT, mover_count SMALLINT, peripheral_event_count BIGINT,
    selected_option VARCHAR, is_correct BOOLEAN, response_time_ms INT, timed_out BOOLEAN,
    hint_available BOOLEAN, hint_requested BOOLEAN, hint_count SMALLINT,
    first_hint_ms INT, cues_presented VARCHAR[], audio_cue_played BOOLEAN, transformation_cue_played BOOLEAN,
    idle_ms INT, idle_episodes SMALLINT, head_away_count BIGINT, head_away_ms INT,
    feedback_shown BOOLEAN, feedback_audio_ms INT, result_sound VARCHAR,
    result_sound_offset_ms INT, result_sound_ms INT, card_animation VARCHAR,
    window_n BIGINT, window_span_ms INT, window_accuracy NUMERIC,
    window_rt_mean NUMERIC, window_rt_sd NUMERIC, window_rt_cv NUMERIC,
    window_idle_ratio NUMERIC, window_head_away_ms BIGINT
)
LANGUAGE sql STABLE AS $$
WITH base AS (
    SELECT s.participant_id, t.session_id, s.condition,
           t.trial_id, t.block_state, t.trial_sequence, t.trial_type, t.kanji_id,
           k.kanji_char, tb.kanji_set, tb.block_seed,
           t.block_state NOT IN ('S2_VR_TUTORIAL') AS is_primary_analysis,
           t.started_elapsed_ms, t.answered_elapsed_ms, t.completed_elapsed_ms,
           t.esl, t.lal,
           env.profile_name, env.prop_count, env.mover_count, b.peripheral_event_count,
           t.selected_option, t.is_correct, t.response_time_ms, t.timed_out,
           t.hint_available, (hr.n > 0) AS hint_requested, t.hint_count,
           hr.first_ms, t.cues_presented,
           'TARGET_READING_AUDIO'  = ANY (COALESCE(t.cues_presented, '{}')) AS audio_cue,
           'VISUAL_TRANSFORMATION' = ANY (COALESCE(t.cues_presented, '{}')) AS transf_cue,
           t.idle_ms, t.idle_episodes, b.head_away_count, b.head_away_ms,
           t.feedback_shown, t.feedback_audio_ms, t.result_sound,
           t.result_sound_offset_ms, t.result_sound_ms, t.card_animation,
           -- only answered trials without timeout count for the window
           (t.answered_elapsed_ms IS NOT NULL AND t.timed_out IS NOT TRUE) AS in_window
    FROM trials t
    JOIN experiment_sessions s ON s.id = t.session_id
    JOIN kanji_items k ON k.kanji_id = t.kanji_id
    LEFT JOIN trial_blocks tb ON tb.session_id = t.session_id AND tb.block_state = t.block_state
    LEFT JOIN v_trial_behavior b ON b.session_id = t.session_id AND b.trial_id = t.trial_id
    LEFT JOIN LATERAL (
        SELECT count(*) AS n, min(h.time_since_trial_start_ms) AS first_ms
        FROM hint_requests h WHERE h.session_id = t.session_id AND h.trial_id = t.trial_id
    ) hr ON TRUE
    LEFT JOIN LATERAL (
        SELECT e.profile_name, e.prop_count, e.mover_count
        FROM environment_applications e
        WHERE e.session_id = t.session_id AND e.elapsed_ms <= t.started_elapsed_ms
        ORDER BY e.elapsed_ms DESC, e.source_event_id DESC LIMIT 1
    ) env ON TRUE
    WHERE t.session_id = p_session
),
win AS (
    SELECT b1.trial_id,
           count(b2.*) AS n,
           (max(b2.answered_elapsed_ms) - min(b2.started_elapsed_ms))::int AS span,
           avg(b2.is_correct::int) AS acc,
           avg(b2.response_time_ms) AS rt_mean,
           stddev_samp(b2.response_time_ms) AS rt_sd,
           sum(b2.idle_ms)::numeric / NULLIF(sum(b2.response_time_ms), 0) AS idle_ratio,
           sum(b2.head_away_ms) AS ha_ms
    FROM base b1
    JOIN LATERAL (
        SELECT * FROM base b2
        WHERE b2.block_state = b1.block_state AND b2.in_window
          AND b2.trial_sequence <= b1.trial_sequence
        ORDER BY b2.trial_sequence DESC LIMIT p_window
    ) b2 ON TRUE
    WHERE b1.in_window
    GROUP BY b1.trial_id
)
SELECT b.participant_id, b.session_id, b.condition, b.trial_id, b.block_state, b.trial_sequence,
       b.trial_type, b.kanji_id, b.kanji_char, b.kanji_set, b.block_seed, b.is_primary_analysis,
       b.started_elapsed_ms, b.answered_elapsed_ms, b.completed_elapsed_ms,
       b.esl, b.lal, b.profile_name, b.prop_count, b.mover_count, b.peripheral_event_count,
       b.selected_option, b.is_correct, b.response_time_ms, b.timed_out,
       b.hint_available, COALESCE(b.hint_requested, FALSE), b.hint_count,
       b.first_ms, b.cues_presented, b.audio_cue, b.transf_cue,
       b.idle_ms, b.idle_episodes, b.head_away_count, b.head_away_ms,
       b.feedback_shown, b.feedback_audio_ms, b.result_sound,
       b.result_sound_offset_ms, b.result_sound_ms, b.card_animation,
       w.n, w.span, round(w.acc, 3), round(w.rt_mean, 1), round(w.rt_sd, 1),
       round(w.rt_sd / NULLIF(w.rt_mean, 0), 3), round(w.idle_ratio, 3), w.ha_ms
FROM base b LEFT JOIN win w ON w.trial_id = b.trial_id
ORDER BY b.started_elapsed_ms;
$$;

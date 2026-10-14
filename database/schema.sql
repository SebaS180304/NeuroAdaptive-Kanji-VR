-- =====================================================================
-- NeuroAdaptive VR -- Esquema inicial de PostgreSQL (Fase 1)
-- =====================================================================
-- Este archivo es la referencia humana-legible del esquema que producen
-- las migraciones Alembic 0001_initial_schema, 0002_schema_v1 y
-- 0003_adaptation (backend/alembic/versions). Las partes de 0002 y 0003 son
-- copia literal de backend/alembic/versions/sql/0002_schema_v1_up.sql
-- (1 oct 2026) y sql/0003_adaptation_up.sql (14 oct 2026), en ese orden.
-- Los dos deben mantenerse identicos; si se autogenera una nueva
-- migracion con Alembic, este archivo debe regenerarse con:
--   pg_dump --schema-only --no-owner --no-privileges neuroadaptive_vr
--
-- Alcance: ver docstring de backend/app/models/__init__.py. Este es el
-- esquema "fundacional" de la Fase 1 (Foundation & Feasibility) --
-- participante, sesion, snapshot de configuracion y dos tablas de
-- telemetria/validacion tecnica genericas para probar el walking
-- skeleton Unity <-> Backend <-> PostgreSQL. El contenido kanji, los
-- trials, los eventos de adaptacion ESL/LAL y las ventanas EEG se
-- modelan en fases posteriores (M2-M4) sobre esta misma base.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto; -- gen_random_uuid()

-- ---------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------

CREATE TYPE experimental_condition AS ENUM (
    'STATIC',
    'BEHAVIOR_ADAPTIVE',
    'MULTIMODAL_ADAPTIVE'
);

CREATE TYPE session_status AS ENUM (
    'CREATED',
    'IN_PROGRESS',
    'COMPLETED',
    'ABORTED'
);

-- Estados formales S0-S10 del Game Flow v1 (spec seccion 7)
CREATE TYPE game_flow_state AS ENUM (
    'S0_SESSION_INITIALIZATION',
    'S1_WELCOME_ORIENTATION',
    'S2_VR_TUTORIAL',
    'S3_SYSTEM_VALIDATION',
    'S4_EEG_BASELINE',
    'S5_STANDARDIZED_LEARNING',
    'S6_GUIDED_PRACTICE_CALIBRATION',
    'S7_EXPERIMENTAL_RETRIEVAL',
    'S8_IMMEDIATE_ASSESSMENT',
    'S9_SESSION_SUMMARY',
    'S10_HCI_SELF_REPORT'
);

CREATE TYPE validation_component AS ENUM (
    'UNITY_BACKEND_WS',
    'WAVEX_EEG',
    'CLOCK_SYNC',
    'OTHER'
);

CREATE TYPE validation_status AS ENUM (
    'OK',
    'WARNING',
    'ERROR'
);

-- ---------------------------------------------------------------------
-- participants
-- ---------------------------------------------------------------------
-- Metadata de screening (spec 13.1). Sin nombre ni identificador
-- directo: external_code es el codigo pseudonimizado asignado por el
-- investigador fuera del sistema.

CREATE TABLE participants (
    id                                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_code                       VARCHAR(32) NOT NULL UNIQUE,
    age_range                           VARCHAR(32),
    previous_japanese_experience        BOOLEAN,
    previous_kanji_experience           BOOLEAN,
    previous_vr_experience              BOOLEAN,
    self_rated_attention_difficulty     VARCHAR(32),
    consent_obtained                    BOOLEAN NOT NULL DEFAULT FALSE,
    consent_obtained_at                 TIMESTAMPTZ,
    created_at                          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_participants_external_code ON participants (external_code);

-- ---------------------------------------------------------------------
-- experiment_sessions
-- ---------------------------------------------------------------------
-- S0 - Session Initialization (spec 7.1): participante, condicion,
-- kanji set asignado, seed y versiones para reproducibilidad exacta.

CREATE TABLE experiment_sessions (
    id                             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id                 UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    condition                      experimental_condition NOT NULL,
    status                         session_status NOT NULL DEFAULT 'CREATED',
    current_state                  game_flow_state NOT NULL DEFAULT 'S0_SESSION_INITIALIZATION',
    assigned_kanji_set             VARCHAR(8),
    visit_number                   INTEGER NOT NULL DEFAULT 1,
    random_seed                    VARCHAR(64),
    software_version               VARCHAR(32),
    experiment_config_version      VARCHAR(32),
    controller_config_version      VARCHAR(32),
    session_clock_started_at       TIMESTAMPTZ,
    completed_at                   TIMESTAMPTZ,
    created_at                     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_experiment_sessions_participant_id ON experiment_sessions (participant_id);

-- ---------------------------------------------------------------------
-- session_config_snapshots
-- ---------------------------------------------------------------------
-- SESSION_CREATED: config snapshot completo. JSONB flexible a proposito
-- -- varios parametros siguen "to validate" (spec seccion 16).

CREATE TABLE session_config_snapshots (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id     UUID NOT NULL UNIQUE REFERENCES experiment_sessions(id) ON DELETE CASCADE,
    config         JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- system_validation_events
-- ---------------------------------------------------------------------
-- S3 - EEG & System Validation: conexion WAVEX, latencia Quest-Backend,
-- calidad de señal, clock offset (spec 7.4). `detail` es JSONB porque
-- los umbrales de calidad EEG siguen "to validate".

CREATE TABLE system_validation_events (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id         UUID NOT NULL REFERENCES experiment_sessions(id) ON DELETE CASCADE,
    component          validation_component NOT NULL,
    status             validation_status NOT NULL,
    detail             JSONB NOT NULL DEFAULT '{}'::jsonb,
    client_timestamp   TIMESTAMPTZ,
    received_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_system_validation_events_session_id ON system_validation_events (session_id);

-- ---------------------------------------------------------------------
-- session_events
-- ---------------------------------------------------------------------
-- Event log generico de proposito general (walking skeleton). El
-- vocabulario conductual completo (TRIAL_STARTED, HEAD_AWAY, etc. --
-- spec 11.1) se instrumenta formalmente en Fase 3.

CREATE TABLE session_events (
    id                     BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    session_id             UUID NOT NULL REFERENCES experiment_sessions(id) ON DELETE CASCADE,
    event_type             VARCHAR(64) NOT NULL,
    payload                JSONB NOT NULL DEFAULT '{}'::jsonb,
    client_timestamp       TIMESTAMPTZ,
    server_received_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_session_events_session_id ON session_events (session_id);
CREATE INDEX ix_session_events_event_type ON session_events (event_type);


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

-- =====================================================================
-- NeuroAdaptive VR -- adaptation loop (F5a) -- migration 0003 (up)
-- =====================================================================
-- Planteamiento_Tecnico_F5a.md §8.3. Same rules as 0002: session_events stays
-- the source of truth, every table here is a projection with the id of the
-- event it came from, and project_session() rebuilds it.
--
-- What it adds:
--   * distractor_interactions  <- DISTRACTOR_INTERACTION (D5, contract §5.11)
--   * adaptation_decisions     <- ADAPTATION_DECISION (backend, one per answered
--                                 trial of an adaptive S7, NO_CHANGE included),
--                                 plus the outcome of ADAPTATION_OUTCOME (O4, F6)
--   * adaptation_applications  <- ADAPTATION_APPLIED / ADAPTATION_SKIPPED (Unity)
--   * trials.cue_trigger / proactive_index (D9) and the idle fields read from
--     ANSWER_SELECTED as well (§2.2)
--   * proj_apply / project_session replaced with the new types;
--     trial_timeline recreated with the new columns at the end
--   * v_adaptations: each decision with what Unity did with it
--
-- Rows written before this migration are projected by running
-- project_session() for each session (database/backfill_projection.sql).
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. D9 on trials
-- ---------------------------------------------------------------------
ALTER TABLE trials
    ADD COLUMN cue_trigger     VARCHAR(12) CHECK (cue_trigger IN ('PROACTIVE', 'ON_REQUEST')),
    ADD COLUMN proactive_index SMALLINT    CHECK (proactive_index BETWEEN 1 AND 3),
    -- an index only with PROACTIVE, and PROACTIVE always with its index
    ADD CONSTRAINT ck_trials_proactive_index
        CHECK ((proactive_index IS NULL OR cue_trigger = 'PROACTIVE')
               AND (cue_trigger IS DISTINCT FROM 'PROACTIVE' OR proactive_index IS NOT NULL));

-- ---------------------------------------------------------------------
-- 2. D5: DISTRACTOR_INTERACTION
-- ---------------------------------------------------------------------
-- elapsed_ms is when the row was emitted (end of the dwell, end of the
-- orienting window); onset_elapsed_ms = elapsed_ms + onset_offset_ms.
-- box_margin_deg only in rows of 371b2c59 (6 Oct), before the yaw/pitch split.
CREATE TABLE distractor_interactions (
    source_event_id         BIGINT PRIMARY KEY REFERENCES session_events(id) ON DELETE CASCADE,
    session_id              UUID NOT NULL REFERENCES experiment_sessions(id) ON DELETE CASCADE,
    elapsed_ms              INTEGER NOT NULL,
    onset_elapsed_ms        INTEGER NOT NULL,
    state                   game_flow_state NOT NULL,
    trial_id                VARCHAR(16),
    kind                    VARCHAR(10) NOT NULL CHECK (kind IN ('DWELL', 'ORIENTING')),
    object_name             VARCHAR(64) NOT NULL,
    object_group            VARCHAR(12) CHECK (object_group IN ('PROP', 'MOVER', 'PERIPHERAL')),
    duration_ms             INTEGER NOT NULL CHECK (duration_ms >= 0),
    peripheral_event_index  INTEGER,
    head_turn_deg           REAL,
    box_distance_deg        REAL,
    dwell_min_ms            INTEGER,
    dwell_break_ms          INTEGER,
    box_margin_yaw_deg      REAL,
    box_margin_pitch_deg    REAL,
    box_margin_deg          REAL,
    orienting_min_deg       REAL,
    orienting_window_ms     INTEGER,
    CHECK ((kind = 'ORIENTING') = (peripheral_event_index IS NOT NULL))
);
CREATE INDEX ix_distractor_session_time ON distractor_interactions (session_id, elapsed_ms);

-- ---------------------------------------------------------------------
-- 3. The adaptation loop
-- ---------------------------------------------------------------------
-- One row per ADAPTATION_DECISION (backend). esl / lal are the levels the
-- answer reported, i.e. in force when the decision was made.
CREATE TABLE adaptation_decisions (
    source_event_id       BIGINT PRIMARY KEY REFERENCES session_events(id) ON DELETE CASCADE,
    session_id            UUID NOT NULL,
    decision_id           VARCHAR(32) NOT NULL,
    trial_id              VARCHAR(16) NOT NULL,
    trial_sequence        SMALLINT,
    decided_elapsed_ms    INTEGER NOT NULL,
    esl                   stimulation_level,
    lal                   stimulation_level,
    learner_state         VARCHAR(12) NOT NULL CHECK (learner_state IN ('STABLE', 'DISENGAGED', 'OVERLOADED')),
    cause                 VARCHAR(12) CHECK (cause IN ('ENVIRONMENT', 'AWAY', 'IMPULSIVE')),
    confidence            REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    action                VARCHAR(20) NOT NULL CHECK (action IN ('NO_CHANGE', 'CHANGE_ENVIRONMENT', 'CHANGE_ASSISTANCE')),
    dimension             VARCHAR(3) CHECK (dimension IN ('ESL', 'LAL')),
    from_level            stimulation_level,
    to_level              stimulation_level,
    proactive_cues        BOOLEAN NOT NULL,
    reason_code           VARCHAR(32) NOT NULL,
    explanation           TEXT NOT NULL,
    cooldown_until_trial  SMALLINT,
    decision_latency_ms   REAL,
    estimator_version     VARCHAR(32),
    rules_version         VARCHAR(32),
    evidence              VARCHAR(32)[],
    indicators            JSONB,
    thresholds            JSONB,
    -- O4 (F6): ADAPTATION_OUTCOME
    outcome               VARCHAR(10) CHECK (outcome IN ('POSITIVE', 'NEUTRAL', 'NEGATIVE', 'UNCERTAIN')),
    outcome_event_id      BIGINT UNIQUE REFERENCES session_events(id) ON DELETE CASCADE,
    UNIQUE (session_id, decision_id),
    UNIQUE (session_id, trial_id),
    FOREIGN KEY (session_id, trial_id) REFERENCES trials(session_id, trial_id) ON DELETE CASCADE,
    -- one dimension per change, by one step, and nothing for NO_CHANGE (§10.2)
    CHECK ((action = 'NO_CHANGE') = (dimension IS NULL)),
    CHECK ((action = 'NO_CHANGE') = (to_level IS NULL)),
    CHECK (action <> 'CHANGE_ENVIRONMENT' OR dimension = 'ESL'),
    CHECK (action <> 'CHANGE_ASSISTANCE'  OR dimension = 'LAL'),
    CHECK (NOT proactive_cues OR (dimension = 'LAL' AND to_level > from_level))
);

-- One row per ADAPTATION_APPLIED / ADAPTATION_SKIPPED (Unity). No FK to the
-- decision: a TIMEOUT skip can come before (or without) its decision row.
-- esl_after / lal_after: the context block of the row, after the change.
CREATE TABLE adaptation_applications (
    source_event_id          BIGINT PRIMARY KEY REFERENCES session_events(id) ON DELETE CASCADE,
    session_id               UUID NOT NULL REFERENCES experiment_sessions(id) ON DELETE CASCADE,
    elapsed_ms               INTEGER NOT NULL,
    result                   VARCHAR(8) NOT NULL CHECK (result IN ('APPLIED', 'SKIPPED')),
    decision_id              VARCHAR(32),
    decision_trial_id        VARCHAR(16) NOT NULL,
    applied_before_trial_id  VARCHAR(16),
    skip_reason              VARCHAR(12) CHECK (skip_reason IN ('TIMEOUT', 'GUARD', 'NOT_ALLOWED', 'INVALID')),
    dimension                VARCHAR(3) CHECK (dimension IN ('ESL', 'LAL')),
    from_level               stimulation_level,
    to_level                 stimulation_level,
    proactive_cues           BOOLEAN,
    waited_ms                INTEGER,
    esl_after                stimulation_level,
    lal_after                stimulation_level,
    CHECK ((result = 'SKIPPED') = (skip_reason IS NOT NULL)),
    CHECK (result = 'SKIPPED' OR (decision_id IS NOT NULL AND applied_before_trial_id IS NOT NULL))
);
CREATE INDEX ix_adaptation_app_trial ON adaptation_applications (session_id, decision_trial_id);

-- ---------------------------------------------------------------------
-- 4. Projector, with the new event types
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION proj_apply(e session_events) RETURNS VOID
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
        'ASSEMBLY_COMPLETED',
        -- 0003 (F5a)
        'DISTRACTOR_INTERACTION', 'ADAPTATION_DECISION', 'ADAPTATION_APPLIED',
        'ADAPTATION_SKIPPED', 'ADAPTATION_OUTCOME') THEN
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
               timed_out = COALESCE((p ->> 'timed_out')::boolean, FALSE),
               -- 0003: idle travels with the answer since 13 Oct (the backend decides
               -- on ANSWER_SELECTED); older rows get it from TRIAL_COMPLETED
               idle_ms = COALESCE((p ->> 'idle_ms')::numeric::int, idle_ms),
               idle_episodes = COALESCE((p ->> 'idle_episodes')::int, idle_episodes),
               idle_longest_ms = COALESCE((p ->> 'idle_longest_ms')::numeric::int, idle_longest_ms)
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
               idle_ms = COALESCE((p ->> 'idle_ms')::numeric::int, idle_ms),
               idle_episodes = COALESCE((p ->> 'idle_episodes')::int, idle_episodes),
               idle_longest_ms = COALESCE((p ->> 'idle_longest_ms')::numeric::int, idle_longest_ms),
               idle_min_ms = (p ->> 'idle_min_ms')::numeric::int,
               idle_head_deg_s = (p ->> 'idle_head_deg_s')::real,
               idle_ray_deg_s = (p ->> 'idle_ray_deg_s')::real,
               -- 0003, D9: how the cue reached the participant
               cue_trigger = p ->> 'cue_trigger',
               proactive_index = (p ->> 'proactive_index')::int
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

    -- ---------------- 0003 (F5a) ----------------

    WHEN 'DISTRACTOR_INTERACTION' THEN
        INSERT INTO distractor_interactions (
            source_event_id, session_id, elapsed_ms, onset_elapsed_ms, state, trial_id, kind,
            object_name, object_group, duration_ms, peripheral_event_index, head_turn_deg,
            box_distance_deg, dwell_min_ms, dwell_break_ms, box_margin_yaw_deg,
            box_margin_pitch_deg, box_margin_deg, orienting_min_deg, orienting_window_ms)
        VALUES (e.id, e.session_id, ms, ms + COALESCE((p ->> 'onset_offset_ms')::numeric::int, 0),
                proj_req(p, 'state')::game_flow_state, p ->> 'trial_id', proj_req(p, 'kind'),
                proj_req(p, 'object_name'), p ->> 'object_group',
                proj_req(p, 'duration_ms')::numeric::int, (p ->> 'peripheral_event_index')::int,
                (p ->> 'head_turn_deg')::real, (p ->> 'box_distance_deg')::real,
                (p ->> 'dwell_min_ms')::numeric::int, (p ->> 'dwell_break_ms')::numeric::int,
                (p ->> 'box_margin_yaw_deg')::real, (p ->> 'box_margin_pitch_deg')::real,
                (p ->> 'box_margin_deg')::real, (p ->> 'orienting_min_deg')::real,
                (p ->> 'orienting_window_ms')::numeric::int)
        ON CONFLICT (source_event_id) DO NOTHING;

    WHEN 'ADAPTATION_DECISION' THEN
        INSERT INTO adaptation_decisions (
            source_event_id, session_id, decision_id, trial_id, trial_sequence, decided_elapsed_ms,
            esl, lal, learner_state, cause, confidence, action, dimension, from_level, to_level,
            proactive_cues, reason_code, explanation, cooldown_until_trial, decision_latency_ms,
            estimator_version, rules_version, evidence, indicators, thresholds)
        VALUES (e.id, e.session_id, proj_req(p, 'decision_id'), proj_req(p, 'trial_id'),
                (p ->> 'trial_sequence')::int, ms,
                (p ->> 'esl')::stimulation_level, (p ->> 'lal')::stimulation_level,
                proj_req(p, 'learner_state'), p ->> 'cause', proj_req(p, 'confidence')::real,
                proj_req(p, 'action'), p ->> 'dimension',
                (p ->> 'from_level')::stimulation_level, (p ->> 'to_level')::stimulation_level,
                COALESCE((p ->> 'proactive_cues')::boolean, FALSE), proj_req(p, 'reason_code'),
                proj_req(p, 'explanation'), (p ->> 'cooldown_until_trial')::int,
                (p ->> 'decision_latency_ms')::real, p ->> 'estimator_version', p ->> 'rules_version',
                proj_arr(p, 'evidence'), p -> 'indicators', p -> 'thresholds')
        ON CONFLICT (source_event_id) DO NOTHING;

    WHEN 'ADAPTATION_APPLIED', 'ADAPTATION_SKIPPED' THEN
        INSERT INTO adaptation_applications (
            source_event_id, session_id, elapsed_ms, result, decision_id, decision_trial_id,
            applied_before_trial_id, skip_reason, dimension, from_level, to_level,
            proactive_cues, waited_ms, esl_after, lal_after)
        VALUES (e.id, e.session_id, ms,
                CASE e.event_type WHEN 'ADAPTATION_APPLIED' THEN 'APPLIED' ELSE 'SKIPPED' END,
                p ->> 'decision_id', proj_req(p, 'decision_trial_id'), p ->> 'applied_before_trial_id',
                p ->> 'reason', p ->> 'dimension',
                (p ->> 'from_level')::stimulation_level, (p ->> 'to_level')::stimulation_level,
                (p ->> 'proactive_cues')::boolean, (p ->> 'waited_ms')::numeric::int,
                (p ->> 'esl')::stimulation_level, (p ->> 'lal')::stimulation_level)
        ON CONFLICT (source_event_id) DO NOTHING;

    WHEN 'ADAPTATION_OUTCOME' THEN
        -- O4 (F6): the backend classifies a decision after its post window
        UPDATE adaptation_decisions SET outcome = proj_req(p, 'outcome'), outcome_event_id = e.id
        WHERE session_id = e.session_id AND decision_id = proj_req(p, 'decision_id')
          AND (outcome_event_id IS NULL OR outcome_event_id = e.id);
        GET DIAGNOSTICS n = ROW_COUNT;
        IF n = 0 THEN
            IF EXISTS (SELECT 1 FROM adaptation_decisions
                       WHERE session_id = e.session_id AND decision_id = p ->> 'decision_id') THEN
                RAISE EXCEPTION 'DUPLICATE: decision % already classified', p ->> 'decision_id' USING ERRCODE = 'P0103';
            END IF;
            RAISE EXCEPTION 'ORPHAN_EVENT: no ADAPTATION_DECISION %', p ->> 'decision_id' USING ERRCODE = 'P0102';
        END IF;

    END CASE;
END $$;


CREATE OR REPLACE FUNCTION project_session(p_session UUID) RETURNS INTEGER
LANGUAGE plpgsql AS $$
DECLARE
    r       RECORD;
    failed  INTEGER := 0;
BEGIN
    DELETE FROM adaptation_applications  WHERE session_id = p_session;   -- 0003
    DELETE FROM adaptation_decisions     WHERE session_id = p_session;   -- 0003
    DELETE FROM distractor_interactions  WHERE session_id = p_session;   -- 0003
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


-- ---------------------------------------------------------------------
-- 5. trial_timeline gains the 0003 columns (at the end, so existing
--    SELECT lists keep working); a new return type needs DROP + CREATE.
-- ---------------------------------------------------------------------
DROP FUNCTION trial_timeline(UUID, INT);
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
    window_idle_ratio NUMERIC, window_head_away_ms BIGINT,
    -- 0003 (F5a): D9, D5 and the adaptation loop
    cue_trigger VARCHAR, proactive_index SMALLINT,
    distractor_dwell_ms BIGINT, dwell_count BIGINT, orienting_count BIGINT,
    learner_state VARCHAR, decision_confidence REAL, decision_action VARCHAR,
    decision_reason VARCHAR, decision_latency_ms REAL, adaptation_result VARCHAR
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
           (t.answered_elapsed_ms IS NOT NULL AND t.timed_out IS NOT TRUE) AS in_window,
           t.cue_trigger, t.proactive_index,
           di.dwell_ms, di.dwell_n, di.orienting_n,
           ad.learner_state, ad.confidence AS decision_confidence, ad.action AS decision_action,
           ad.reason_code AS decision_reason, ad.decision_latency_ms, aa.result AS adaptation_result
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
    -- D5, same attribution as the estimator (backend/app/adaptation/trials.py):
    -- a DISTRACTOR_INTERACTION counts for the trial answered at or after it,
    -- back to the previous answer of the block (or the block's entry)
    LEFT JOIN LATERAL (
        SELECT COALESCE(max(t2.answered_elapsed_ms),
                        (SELECT max(ss.entered_elapsed_ms) FROM session_states ss
                         WHERE ss.session_id = t.session_id AND ss.state = t.block_state
                           AND ss.entered_elapsed_ms <= t.started_elapsed_ms)) AS lo
        FROM trials t2
        WHERE t2.session_id = t.session_id AND t2.block_state = t.block_state
          AND t2.trial_sequence < t.trial_sequence AND t2.answered_elapsed_ms IS NOT NULL
    ) win_lo ON TRUE
    LEFT JOIN LATERAL (
        SELECT sum(d.duration_ms) FILTER (WHERE d.kind = 'DWELL') AS dwell_ms,
               count(*) FILTER (WHERE d.kind = 'DWELL')     AS dwell_n,
               count(*) FILTER (WHERE d.kind = 'ORIENTING') AS orienting_n
        FROM distractor_interactions d
        WHERE d.session_id = t.session_id AND t.answered_elapsed_ms IS NOT NULL
          AND d.elapsed_ms >  COALESCE(win_lo.lo, t.started_elapsed_ms - 1)
          AND d.elapsed_ms <= t.answered_elapsed_ms
    ) di ON TRUE
    LEFT JOIN adaptation_decisions ad ON ad.session_id = t.session_id AND ad.trial_id = t.trial_id
    LEFT JOIN LATERAL (
        SELECT a.result FROM adaptation_applications a
        WHERE a.session_id = t.session_id AND a.decision_trial_id = t.trial_id
        ORDER BY a.source_event_id DESC LIMIT 1
    ) aa ON TRUE
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
       round(w.rt_sd / NULLIF(w.rt_mean, 0), 3), round(w.idle_ratio, 3), w.ha_ms,
       b.cue_trigger, b.proactive_index,
       COALESCE(b.dwell_ms, 0), COALESCE(b.dwell_n, 0), COALESCE(b.orienting_n, 0),
       b.learner_state, b.decision_confidence, b.decision_action,
       b.decision_reason, b.decision_latency_ms, b.adaptation_result
FROM base b LEFT JOIN win w ON w.trial_id = b.trial_id
ORDER BY b.started_elapsed_ms;
$$;


-- Each decision with what Unity did with it (the last application row of
-- its trial). Changes without an application row are pending or lost.
CREATE VIEW v_adaptations AS
SELECT d.session_id, d.trial_id, d.decision_id, d.decided_elapsed_ms, d.learner_state, d.cause,
       d.confidence, d.action, d.dimension, d.from_level, d.to_level, d.proactive_cues,
       d.reason_code, d.explanation, d.decision_latency_ms, d.outcome,
       a.result AS unity_result, a.skip_reason, a.applied_before_trial_id, a.waited_ms,
       a.elapsed_ms AS applied_elapsed_ms
FROM adaptation_decisions d
LEFT JOIN LATERAL (
    SELECT * FROM adaptation_applications x
    WHERE x.session_id = d.session_id AND x.decision_trial_id = d.trial_id
    ORDER BY x.source_event_id DESC LIMIT 1
) a ON TRUE;

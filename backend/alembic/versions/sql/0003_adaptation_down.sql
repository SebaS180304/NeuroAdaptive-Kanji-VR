-- =====================================================================
-- NeuroAdaptive VR -- adaptation loop (F5a) -- migration 0003 (down)
-- =====================================================================
-- Back to schema v1 as 0002 left it. session_events is untouched, so the
-- dropped rows come back with `alembic upgrade head` + project_session().
-- The function bodies below are those of 0002, verbatim.
-- =====================================================================

DROP VIEW IF EXISTS v_adaptations;
DROP FUNCTION IF EXISTS trial_timeline(UUID, INT);

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


CREATE OR REPLACE FUNCTION project_session(p_session UUID) RETURNS INTEGER
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


DROP TABLE IF EXISTS adaptation_applications;
DROP TABLE IF EXISTS adaptation_decisions;
DROP TABLE IF EXISTS distractor_interactions;

ALTER TABLE trials
    DROP CONSTRAINT IF EXISTS ck_trials_proactive_index,
    DROP COLUMN IF EXISTS proactive_index,
    DROP COLUMN IF EXISTS cue_trigger;

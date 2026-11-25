-- =====================================================================
-- NeuroAdaptive VR -- PostgreSQL schema, as the database stands at Alembic revision 0023
-- =====================================================================
-- Generated, not hand-written. Do not edit: regenerate after every migration.
--
-- Source: pg_dump of the running database on 2026-11-25, schema only (no rows, so no participant data),
-- with the database at alembic_version 0023 (0023_live_vs_xdf). The migrations in
-- backend/alembic/versions/ are the source of truth; this file is the readable reference of what they build.
--
-- Regenerate (PowerShell, repo root, with the stack up):
--   docker compose exec -T db pg_dump --schema-only --no-owner --no-privileges -U neuroadaptive neuroadaptive_vr |
--     Where-Object { $_ -notmatch '^\\(un)?restrict ' } > body.sql
--   then put this header back on top and update the revision and the date.
-- The \restrict / \unrestrict lines pg_dump adds are dropped: they carry a random token each run.
--
-- Tables, columns and relations: database/ERD.md. Event payloads: database/EVENT_CONTRACT.md.
-- =====================================================================
--
-- PostgreSQL database dump
--


-- Dumped from database version 16.13 (Debian 16.13-1.pgdg13+1)
-- Dumped by pg_dump version 16.13 (Debian 16.13-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: experimental_condition; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.experimental_condition AS ENUM (
    'STATIC',
    'BEHAVIOR_ADAPTIVE',
    'MULTIMODAL_ADAPTIVE'
);


--
-- Name: game_flow_state; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.game_flow_state AS ENUM (
    'S0_SESSION_INITIALIZATION',
    'S1_WELCOME_ORIENTATION',
    'S2_VR_TUTORIAL',
    'SR_DELAYED_RETENTION',
    'S3_SYSTEM_VALIDATION',
    'S4_EEG_BASELINE',
    'S5_STANDARDIZED_LEARNING',
    'S6_GUIDED_PRACTICE_CALIBRATION',
    'S7_EXPERIMENTAL_RETRIEVAL',
    'S8_IMMEDIATE_ASSESSMENT',
    'S9_SESSION_SUMMARY',
    'S10_HCI_SELF_REPORT'
);


--
-- Name: kanji_role; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.kanji_role AS ENUM (
    'EXPERIMENTAL',
    'RESERVE',
    'TUTORIAL'
);


--
-- Name: session_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.session_status AS ENUM (
    'CREATED',
    'IN_PROGRESS',
    'COMPLETED',
    'ABORTED'
);


--
-- Name: stimulation_level; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.stimulation_level AS ENUM (
    'OFF',
    'MINIMAL',
    'BASELINE',
    'FOCUS',
    'LOW',
    'MEDIUM',
    'HIGH'
);


--
-- Name: trial_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.trial_type AS ENUM (
    'T1_MEANING_TO_KANJI',
    'T2_KANJI_TO_MEANING',
    'T3_KANJI_TO_READING'
);


--
-- Name: validation_component; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.validation_component AS ENUM (
    'UNITY_BACKEND_WS',
    'WAVEX_EEG',
    'CLOCK_SYNC',
    'OTHER'
);


--
-- Name: validation_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.validation_status AS ENUM (
    'OK',
    'WARNING',
    'ERROR'
);


--
-- Name: abort_stale_sessions(interval); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.abort_stale_sessions(p_idle interval DEFAULT '00:30:00'::interval) RETURNS integer
    LANGUAGE sql
    AS $$
    WITH aborted AS (
        UPDATE experiment_sessions s
        SET status = 'ABORTED', updated_at = now()
        WHERE s.status = 'IN_PROGRESS'
          AND COALESCE((SELECT max(e.server_received_at) FROM session_events e
                        WHERE e.session_id = s.id), s.updated_at) < now() - p_idle
        RETURNING 1)
    SELECT count(*)::int FROM aborted;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: session_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_events (
    id bigint NOT NULL,
    session_id uuid NOT NULL,
    event_type character varying(64) NOT NULL,
    payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    client_timestamp timestamp with time zone,
    server_received_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: proj_apply(public.session_events); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.proj_apply(e public.session_events) RETURNS void
    LANGUAGE plpgsql
    AS $$
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
                            options, correct_option, hint_available, option_kinds)
        VALUES (e.session_id, proj_req(p, 'trial_id'), proj_req(p, 'state')::game_flow_state,
                proj_req(p, 'trial_sequence')::int, proj_req(p, 'trial_type')::trial_type,
                proj_req(p, 'kanji_id'), proj_req(p, 'schema_version')::int,
                proj_req(p, 'esl')::stimulation_level, proj_req(p, 'lal')::stimulation_level,
                e.id, ms, proj_arr(p, 'options'), proj_req(p, 'correct_option'),
                proj_req(p, 'hint_available')::boolean, proj_arr(p, 'option_kinds'))
        ON CONFLICT (started_event_id) DO NOTHING;

    WHEN 'ANSWER_SELECTED' THEN
        UPDATE trials SET answer_event_id = e.id, answered_elapsed_ms = ms,
               selected_option = proj_req(p, 'selected_option'),
               is_correct = proj_req(p, 'is_correct')::boolean,
               response_time_ms = proj_req(p, 'response_time_ms')::numeric::int,
               timed_out = COALESCE((p ->> 'timed_out')::boolean, FALSE),
               option_kind = p ->> 'option_kind',
               lure_selected = (p ->> 'lure_selected')::boolean,
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
                (p ->> 'stages_authored')::smallint, (p ->> 'audio_played')::boolean,
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
            estimator_version, rules_version, evidence, indicators, thresholds,
            eeg_counted, eeg_ei_z, eeg_theta_z, eeg_effect)
        VALUES (e.id, e.session_id, proj_req(p, 'decision_id'), proj_req(p, 'trial_id'),
                (p ->> 'trial_sequence')::int, ms,
                (p ->> 'esl')::stimulation_level, (p ->> 'lal')::stimulation_level,
                proj_req(p, 'learner_state'), p ->> 'cause', proj_req(p, 'confidence')::real,
                proj_req(p, 'action'), p ->> 'dimension',
                (p ->> 'from_level')::stimulation_level, (p ->> 'to_level')::stimulation_level,
                COALESCE((p ->> 'proactive_cues')::boolean, FALSE), proj_req(p, 'reason_code'),
                proj_req(p, 'explanation'), (p ->> 'cooldown_until_trial')::int,
                (p ->> 'decision_latency_ms')::real, p ->> 'estimator_version', p ->> 'rules_version',
                proj_arr(p, 'evidence'), p -> 'indicators', p -> 'thresholds',
                (p -> 'eeg' ->> 'counted')::boolean, (p -> 'eeg' ->> 'ei_z')::real,
                (p -> 'eeg' ->> 'theta_z')::real, p -> 'eeg' ->> 'effect')
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


--
-- Name: proj_arr(jsonb, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.proj_arr(p jsonb, k text) RETURNS text[]
    LANGUAGE sql IMMUTABLE
    AS $$
    SELECT CASE WHEN jsonb_typeof(p -> k) = 'array'
                THEN ARRAY(SELECT jsonb_array_elements_text(p -> k)) END
$$;


--
-- Name: proj_int_arr(jsonb, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.proj_int_arr(p jsonb, k text) RETURNS integer[]
    LANGUAGE sql IMMUTABLE
    AS $$
    SELECT CASE WHEN jsonb_typeof(p -> k) = 'array'
                THEN ARRAY(SELECT (x)::numeric::int FROM jsonb_array_elements_text(p -> k) x) END
$$;


--
-- Name: proj_orphan_or_dup(public.session_events, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.proj_orphan_or_dup(e public.session_events, col text) RETURNS void
    LANGUAGE plpgsql
    AS $_$
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
END $_$;


--
-- Name: proj_req(jsonb, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.proj_req(p jsonb, k text) RETURNS text
    LANGUAGE plpgsql IMMUTABLE
    AS $$
BEGIN
    IF NOT (p ? k) OR jsonb_typeof(p -> k) = 'null' THEN
        RAISE EXCEPTION 'MISSING_FIELD: %', k USING ERRCODE = 'P0101';
    END IF;
    RETURN p ->> k;
END $$;


--
-- Name: project_event(bigint); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.project_event(p_event_id bigint) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
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


--
-- Name: project_session(uuid); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.project_session(p_session uuid) RETURNS integer
    LANGUAGE plpgsql
    AS $$
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


--
-- Name: trial_timeline(uuid, integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trial_timeline(p_session uuid, p_window integer DEFAULT 3) RETURNS TABLE(participant_id uuid, session_id uuid, condition public.experimental_condition, trial_id character varying, block_state public.game_flow_state, trial_sequence smallint, trial_type public.trial_type, kanji_id character varying, kanji_char character varying, kanji_set character, block_seed bigint, is_primary_analysis boolean, started_elapsed_ms integer, answered_elapsed_ms integer, completed_elapsed_ms integer, esl public.stimulation_level, lal public.stimulation_level, env_profile character varying, prop_count smallint, mover_count smallint, peripheral_event_count bigint, selected_option character varying, is_correct boolean, response_time_ms integer, timed_out boolean, hint_available boolean, hint_requested boolean, hint_count smallint, first_hint_ms integer, cues_presented character varying[], audio_cue_played boolean, transformation_cue_played boolean, idle_ms integer, idle_episodes smallint, head_away_count bigint, head_away_ms integer, feedback_shown boolean, feedback_audio_ms integer, result_sound character varying, result_sound_offset_ms integer, result_sound_ms integer, card_animation character varying, window_n bigint, window_span_ms integer, window_accuracy numeric, window_rt_mean numeric, window_rt_sd numeric, window_rt_cv numeric, window_idle_ratio numeric, window_head_away_ms bigint, cue_trigger character varying, proactive_index smallint, distractor_dwell_ms bigint, dwell_count bigint, orienting_count bigint, learner_state character varying, decision_confidence real, decision_action character varying, decision_reason character varying, decision_latency_ms real, adaptation_result character varying)
    LANGUAGE sql STABLE
    AS $$
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


--
-- Name: verify_adaptation_fn(uuid); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.verify_adaptation_fn(p_session uuid DEFAULT NULL::uuid) RETURNS TABLE(session_id uuid, "check" text, detail text)
    LANGUAGE sql STABLE
    AS $$
WITH target AS (
    SELECT s.id, s.condition FROM experiment_sessions s
    WHERE s.id = p_session
       OR (p_session IS NULL AND s.created_at >= TIMESTAMPTZ '2026-10-13 00:00+09')),
raises AS (
    SELECT a.session_id AS sid, x.trial_sequence AS first_seq
    FROM adaptation_applications a
    JOIN trials x ON x.session_id = a.session_id AND x.trial_id = a.applied_before_trial_id
    WHERE a.result = 'APPLIED' AND a.dimension = 'LAL' AND a.proactive_cues),
expected AS (
    SELECT r.sid, r.first_seq + k - 1 AS seq, k AS idx
    FROM raises r CROSS JOIN generate_series(1, 3) k)
-- 2. STATIC never adapts (criterion 5)
SELECT t.id, 'adaptation/static', 'decision ' || d.trial_id
FROM target t JOIN adaptation_decisions d ON d.session_id = t.id WHERE t.condition = 'STATIC'
UNION ALL
SELECT t.id, 'adaptation/static', 'application ' || a.decision_trial_id
FROM target t JOIN adaptation_applications a ON a.session_id = t.id WHERE t.condition = 'STATIC'
UNION ALL
SELECT t.id, 'adaptation/static', 'proactive cue ' || x.trial_id
FROM target t JOIN trials x ON x.session_id = t.id
WHERE t.condition = 'STATIC' AND x.cue_trigger = 'PROACTIVE'
UNION ALL
-- 3. adaptive S7: one decision per answered trial
SELECT t.id, 'adaptation/missing_decision', 'answered without decision ' || x.trial_id
FROM target t JOIN trials x ON x.session_id = t.id
WHERE t.condition <> 'STATIC' AND x.block_state = 'S7_EXPERIMENTAL_RETRIEVAL'
  AND x.answered_elapsed_ms IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM adaptation_decisions d WHERE d.session_id = t.id AND d.trial_id = x.trial_id)
UNION ALL
-- 4. every APPLIED has its change decision, and lands between trials (criterion 3)
SELECT a.session_id, 'adaptation/application',
       format('%s -> %s: %s', a.decision_trial_id, a.applied_before_trial_id,
              CASE
                WHEN d.decision_id IS NULL THEN 'no decision with that decision_id'
                WHEN d.action = 'NO_CHANGE' THEN 'applied a NO_CHANGE'
                WHEN d.to_level IS DISTINCT FROM a.to_level THEN 'applied level differs from the decision'
                WHEN a.elapsed_ms < closed.completed_elapsed_ms THEN 'applied before its trial closed'
                WHEN a.elapsed_ms > nxt.started_elapsed_ms THEN 'applied after the next trial started'
              END)
FROM adaptation_applications a
JOIN target t ON t.id = a.session_id
LEFT JOIN adaptation_decisions d ON d.session_id = a.session_id AND d.decision_id = a.decision_id
LEFT JOIN trials closed ON closed.session_id = a.session_id AND closed.trial_id = a.decision_trial_id
LEFT JOIN trials nxt    ON nxt.session_id = a.session_id AND nxt.trial_id = a.applied_before_trial_id
WHERE a.result = 'APPLIED'
  AND (d.decision_id IS NULL OR d.action = 'NO_CHANGE' OR d.to_level IS DISTINCT FROM a.to_level
       OR a.elapsed_ms < closed.completed_elapsed_ms OR a.elapsed_ms > nxt.started_elapsed_ms)
UNION ALL
-- 7. D9: PROACTIVE only in the 3 trials after an applied LAL raise, indexed 1..3 (criterion 11)
SELECT x.session_id, 'adaptation/proactive',
       format('%s: cue_trigger %s, index %s, expected index %s',
              x.trial_id, x.cue_trigger, x.proactive_index, e.idx)
FROM trials x
JOIN target t ON t.id = x.session_id
LEFT JOIN expected e ON e.sid = x.session_id AND e.seq = x.trial_sequence
WHERE x.block_state = 'S7_EXPERIMENTAL_RETRIEVAL' AND x.completed_event_id IS NOT NULL
  AND x.contract_version IS NOT NULL
  AND ((x.cue_trigger IS NOT DISTINCT FROM 'PROACTIVE') <> (e.idx IS NOT NULL)
       OR x.proactive_index IS DISTINCT FROM e.idx)
  -- trials closed before the D9 fields existed carry no cue_trigger at all
  AND EXISTS (SELECT 1 FROM trials y WHERE y.session_id = x.session_id AND y.cue_trigger IS NOT NULL
              UNION ALL SELECT 1 FROM raises r WHERE r.sid = x.session_id)
UNION ALL
-- 8. open projection errors of the 0003 event types
SELECT p.session_id, 'adaptation/open_error',
       format('%s %s x%s, e.g. %s', p.event_type, p.error_code, count(*), min(p.detail))
FROM projection_errors p JOIN target t ON t.id = p.session_id
WHERE p.resolved_at IS NULL
  AND p.event_type IN ('DISTRACTOR_INTERACTION', 'ADAPTATION_DECISION', 'ADAPTATION_APPLIED',
                       'ADAPTATION_SKIPPED', 'ADAPTATION_OUTCOME', 'ANSWER_SELECTED', 'TRIAL_COMPLETED')
GROUP BY p.session_id, p.event_type, p.error_code
$$;


--
-- Name: verify_assembly_fn(uuid); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.verify_assembly_fn(p_session uuid DEFAULT NULL::uuid) RETURNS TABLE(session_id uuid, "check" text, detail text)
    LANGUAGE sql STABLE
    AS $$
WITH s AS (
    SELECT COALESCE(p_session,
                    (SELECT x.id FROM experiment_sessions x ORDER BY x.created_at DESC LIMIT 1)) AS id),
placed AS (
    SELECT a.exposure_index, min(a.kanji_id) AS kanji, count(DISTINCT a.kanji_id) AS kanjis,
           count(*) FILTER (WHERE NOT a.is_correct) AS wrong,
           count(*) FILTER (WHERE a.is_correct)     AS right_
    FROM assembly_attempts a WHERE a.session_id = (SELECT id FROM s)
    GROUP BY 1)
-- 0. assembly and exposure events that did not project
SELECT p.session_id, 'assembly/open_error',
       format('%s %s (event %s): %s', p.event_type, p.error_code, p.event_id, p.detail)
FROM projection_errors p
WHERE p.session_id = (SELECT id FROM s) AND p.resolved_at IS NULL
  AND p.event_type IN ('ASSEMBLY_SEGMENT_PLACED', 'ASSEMBLY_COMPLETED', 'KANJI_EXPOSED')
UNION ALL
-- 3. incorrect_attempts == wrong placements, segment_count == right placements
--    (unless forced by the researcher), same kanji on both sides
SELECT d.session_id, 'assembly/counts',
       format('exposure %s %s: completed wrong %s, placed wrong %s, segments %s, placed right %s, placed kanji %s, forced %s',
              d.exposure_index, d.kanji_id, d.incorrect_attempts, COALESCE(p.wrong, 0),
              d.segment_count, COALESCE(p.right_, 0), p.kanji, d.forced_by_researcher)
FROM assemblies d LEFT JOIN placed p USING (exposure_index)
WHERE d.session_id = (SELECT id FROM s)
  AND (d.incorrect_attempts IS DISTINCT FROM COALESCE(p.wrong, 0)::smallint
    OR (NOT d.forced_by_researcher AND d.segment_count IS DISTINCT FROM COALESCE(p.right_, 0)::smallint)
    OR p.kanjis > 1
    OR (p.kanji IS NOT NULL AND p.kanji <> d.kanji_id))
UNION ALL
-- attempts of an exposure that never closed (expected in an aborted session)
SELECT (SELECT id FROM s), 'assembly/unclosed',
       format('exposure %s %s: %s wrong, %s right, never completed', p.exposure_index, p.kanji, p.wrong, p.right_)
FROM placed p
WHERE NOT EXISTS (SELECT 1 FROM assemblies d
                  WHERE d.session_id = (SELECT id FROM s) AND d.exposure_index = p.exposure_index)
$$;


--
-- Name: verify_projection_fn(uuid); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.verify_projection_fn(p_session uuid DEFAULT NULL::uuid) RETURNS TABLE(session_id uuid, "check" text, detail text)
    LANGUAGE sql STABLE
    AS $$
WITH checked AS (
    SELECT c.sid FROM (
        SELECT x.session_id AS sid FROM session_states x
        UNION SELECT x.session_id FROM trials x
        UNION SELECT x.session_id FROM projection_errors x WHERE x.resolved_at IS NULL) c
    WHERE p_session IS NULL OR c.sid = p_session),
got AS (
    SELECT g.* FROM (
                  SELECT x.session_id AS sid, 'STATE_ENTERED' AS et, count(*) AS n FROM session_states x GROUP BY 1
        UNION ALL SELECT x.session_id, 'TRIAL_SEQUENCE_GENERATED', count(*) FROM trial_blocks x GROUP BY 1
        UNION ALL SELECT x.session_id, 'TRIAL_STARTED', count(*) FROM trials x GROUP BY 1
        UNION ALL SELECT x.session_id, 'ANSWER_SELECTED', count(x.answer_event_id) FROM trials x GROUP BY 1
        UNION ALL SELECT x.session_id, 'TRIAL_COMPLETED', count(x.completed_event_id) FROM trials x GROUP BY 1
        UNION ALL SELECT x.session_id, 'HINT_REQUESTED', count(*) FROM hint_requests x GROUP BY 1
        UNION ALL SELECT x.session_id, 'ENVIRONMENT_APPLIED', count(*) FROM environment_applications x GROUP BY 1
        UNION ALL SELECT x.session_id, 'PERIPHERAL_EVENT', count(*) FROM peripheral_events x GROUP BY 1
        UNION ALL SELECT x.session_id, 'HEAD_AWAY', count(*) FROM head_away_episodes x GROUP BY 1
        UNION ALL SELECT x.session_id, 'HEAD_RETURNED', count(x.returned_event_id) FROM head_away_episodes x GROUP BY 1
        UNION ALL SELECT x.session_id, 'KANJI_EXPOSED', count(*) FROM kanji_exposures x GROUP BY 1
        UNION ALL SELECT x.session_id, 'ASSEMBLY_SEGMENT_PLACED', count(*) FROM assembly_attempts x GROUP BY 1
        UNION ALL SELECT x.session_id, 'ASSEMBLY_COMPLETED', count(*) FROM assemblies x GROUP BY 1) g
    WHERE g.sid IN (SELECT c.sid FROM checked c)),
-- every event that a projected row points to
refs AS (
              SELECT x.entered_event_id AS id FROM session_states x
    UNION ALL SELECT x.source_event_id FROM trial_blocks x
    UNION ALL SELECT x.started_event_id FROM trials x
    UNION ALL SELECT x.answer_event_id FROM trials x WHERE x.answer_event_id IS NOT NULL
    UNION ALL SELECT x.completed_event_id FROM trials x WHERE x.completed_event_id IS NOT NULL
    UNION ALL SELECT x.source_event_id FROM hint_requests x
    UNION ALL SELECT x.source_event_id FROM environment_applications x
    UNION ALL SELECT x.source_event_id FROM peripheral_events x
    UNION ALL SELECT x.away_event_id FROM head_away_episodes x
    UNION ALL SELECT x.returned_event_id FROM head_away_episodes x WHERE x.returned_event_id IS NOT NULL
    UNION ALL SELECT x.source_event_id FROM kanji_exposures x
    UNION ALL SELECT x.source_event_id FROM assembly_attempts x
    UNION ALL SELECT x.source_event_id FROM assemblies x),
expected AS (
    SELECT e.session_id AS sid, e.event_type AS et, count(*) AS n
    FROM session_events e
    WHERE e.session_id IN (SELECT c.sid FROM checked c)
      AND e.event_type IN ('STATE_ENTERED', 'TRIAL_SEQUENCE_GENERATED', 'TRIAL_STARTED',
                           'ANSWER_SELECTED', 'TRIAL_COMPLETED', 'HINT_REQUESTED',
                           'ENVIRONMENT_APPLIED', 'PERIPHERAL_EVENT', 'HEAD_AWAY', 'HEAD_RETURNED',
                           'KANJI_EXPOSED', 'ASSEMBLY_SEGMENT_PLACED', 'ASSEMBLY_COMPLETED')
      AND NOT (EXISTS (SELECT 1 FROM projection_errors p WHERE p.event_id = e.id)
               AND e.id NOT IN (SELECT r.id FROM refs r))
    GROUP BY 1, 2)
-- 2. event -> row counts, per session and event type
SELECT sid, 'projection/counts',
       format('%s: %s events, %s rows', et, COALESCE(e.n, 0), COALESCE(r.n, 0))
FROM expected e FULL JOIN got r USING (sid, et)
WHERE COALESCE(e.n, 0) <> COALESCE(r.n, 0)
UNION ALL
-- planned trials: one row per entry of every sequence
SELECT b.session_id, 'projection/counts',
       format('%s sequence: %s entries, %s planned_trials', b.block_state,
              jsonb_array_length(e.payload -> 'sequence'), pt.n)
FROM trial_blocks b
JOIN session_events e ON e.id = b.source_event_id
CROSS JOIN LATERAL (SELECT count(*) AS n FROM planned_trials p
                    WHERE p.session_id = b.session_id AND p.block_state = b.block_state) pt
WHERE b.session_id IN (SELECT c.sid FROM checked c)
  AND jsonb_array_length(e.payload -> 'sequence') <> pt.n
UNION ALL
-- 3. value by value, each row against the event that holds its id
SELECT t.session_id, 'projection/values', 'trials/started ' || t.trial_id
FROM trials t JOIN session_events e ON e.id = t.started_event_id
WHERE t.session_id IN (SELECT c.sid FROM checked c)
  AND (t.started_elapsed_ms IS DISTINCT FROM (e.payload->>'session_elapsed_ms')::numeric::int
    OR t.kanji_id IS DISTINCT FROM e.payload->>'kanji_id'
    OR t.trial_type::text IS DISTINCT FROM e.payload->>'trial_type'
    OR t.esl::text IS DISTINCT FROM e.payload->>'esl'
    OR t.lal::text IS DISTINCT FROM e.payload->>'lal'
    OR t.options IS DISTINCT FROM ARRAY(SELECT jsonb_array_elements_text(e.payload->'options'))::varchar[]
    OR t.correct_option IS DISTINCT FROM e.payload->>'correct_option'
    OR t.hint_available IS DISTINCT FROM (e.payload->>'hint_available')::boolean)
UNION ALL
SELECT t.session_id, 'projection/values', 'trials/answer ' || t.trial_id
FROM trials t JOIN session_events e ON e.id = t.answer_event_id
WHERE t.session_id IN (SELECT c.sid FROM checked c)
  AND (t.answered_elapsed_ms IS DISTINCT FROM (e.payload->>'session_elapsed_ms')::numeric::int
    OR t.selected_option IS DISTINCT FROM e.payload->>'selected_option'
    OR t.is_correct IS DISTINCT FROM (e.payload->>'is_correct')::boolean
    OR t.response_time_ms IS DISTINCT FROM (e.payload->>'response_time_ms')::numeric::int)
UNION ALL
SELECT t.session_id, 'projection/values', 'trials/completed ' || t.trial_id
FROM trials t JOIN session_events e ON e.id = t.completed_event_id
WHERE t.session_id IN (SELECT c.sid FROM checked c)
  AND (t.completed_elapsed_ms IS DISTINCT FROM (e.payload->>'session_elapsed_ms')::numeric::int
    OR t.hint_count IS DISTINCT FROM (e.payload->>'hint_count')::int
    OR COALESCE(t.cues_presented, '{}') IS DISTINCT FROM
       ARRAY(SELECT jsonb_array_elements_text(COALESCE(e.payload->'cues_presented', '[]')))::varchar[]
    OR t.feedback_shown IS DISTINCT FROM (e.payload->>'feedback_shown')::boolean
    OR t.feedback_audio_source IS DISTINCT FROM e.payload->>'feedback_audio_source'
    OR t.feedback_audio_ms IS DISTINCT FROM (e.payload->>'feedback_audio_ms')::numeric::int
    OR t.result_sound IS DISTINCT FROM e.payload->>'result_sound'
    OR t.result_sound_offset_ms IS DISTINCT FROM (e.payload->>'result_sound_offset_ms')::numeric::int
    OR t.result_sound_ms IS DISTINCT FROM (e.payload->>'result_sound_ms')::numeric::int
    OR t.card_animation IS DISTINCT FROM e.payload->>'card_animation'
    OR t.idle_ms IS DISTINCT FROM (e.payload->>'idle_ms')::numeric::int
    OR t.idle_episodes IS DISTINCT FROM (e.payload->>'idle_episodes')::int
    OR t.idle_longest_ms IS DISTINCT FROM (e.payload->>'idle_longest_ms')::numeric::int
    OR t.idle_min_ms IS DISTINCT FROM (e.payload->>'idle_min_ms')::numeric::int)
UNION ALL
SELECT h.session_id, 'projection/values', 'hint_requests ' || h.trial_id || '#' || h.request_seq
FROM hint_requests h JOIN session_events e ON e.id = h.source_event_id
WHERE h.session_id IN (SELECT c.sid FROM checked c)
  AND (h.trial_id IS DISTINCT FROM e.payload->>'trial_id'
    OR h.time_since_trial_start_ms IS DISTINCT FROM (e.payload->>'time_since_trial_start_ms')::numeric::int
    OR h.cues_granted IS DISTINCT FROM
       ARRAY(SELECT jsonb_array_elements_text(COALESCE(e.payload->'hint_type', '[]')))::varchar[])
UNION ALL
SELECT s.session_id, 'projection/values', 'session_states ' || s.state::text || '#' || s.visit_seq
FROM session_states s JOIN session_events e ON e.id = s.entered_event_id
WHERE s.session_id IN (SELECT c.sid FROM checked c)
  AND (s.state::text IS DISTINCT FROM e.payload->>'state'
    OR s.entered_elapsed_ms IS DISTINCT FROM (e.payload->>'session_elapsed_ms')::numeric::int
    OR s.transition_sound_lead_ms IS DISTINCT FROM (e.payload->>'transition_sound_lead_ms')::numeric::int)
UNION ALL
SELECT a.session_id, 'projection/values', 'environment_applications at ' || a.elapsed_ms
FROM environment_applications a JOIN session_events e ON e.id = a.source_event_id
WHERE a.session_id IN (SELECT c.sid FROM checked c)
  AND (a.esl::text IS DISTINCT FROM e.payload->>'esl'
    OR a.profile_name IS DISTINCT FROM e.payload->>'profile_name'
    OR a.prop_count IS DISTINCT FROM (e.payload->>'prop_count')::int
    OR a.mover_count IS DISTINCT FROM (e.payload->>'mover_count')::int
    OR a.seed IS DISTINCT FROM (e.payload->>'seed')::bigint
    OR a.seed_source IS DISTINCT FROM e.payload->>'seed_source'
    OR a.selection_seed IS DISTINCT FROM (e.payload->>'selection_seed')::bigint)
UNION ALL
SELECT h.session_id, 'projection/values', 'head_away_episodes episode ' || h.episode
FROM head_away_episodes h
JOIN session_events a ON a.id = h.away_event_id
LEFT JOIN session_events r ON r.id = h.returned_event_id
WHERE h.session_id IN (SELECT c.sid FROM checked c)
  AND (h.onset_elapsed_ms IS DISTINCT FROM
         (a.payload->>'session_elapsed_ms')::numeric::int + (a.payload->>'onset_offset_ms')::numeric::int
    OR h.limit_crossed IS DISTINCT FROM a.payload->>'limit'
    OR h.yaw_limit_deg IS DISTINCT FROM (a.payload->>'yaw_limit_deg')::real
    OR h.min_away_ms IS DISTINCT FROM (a.payload->>'min_away_ms')::numeric::int
    OR h.duration_ms IS DISTINCT FROM (r.payload->>'duration_ms')::numeric::int
    OR h.return_reason IS DISTINCT FROM r.payload->>'reason')
UNION ALL
SELECT x.session_id, 'projection/values', 'assembly_attempts ' || x.exposure_index || '#' || x.attempt
FROM assembly_attempts x JOIN session_events e ON e.id = x.source_event_id
WHERE x.session_id IN (SELECT c.sid FROM checked c)
  AND (x.kanji_id IS DISTINCT FROM e.payload->>'kanji_id'
    OR x.segment_id IS DISTINCT FROM e.payload->>'segment_id'
    OR x.is_correct IS DISTINCT FROM (e.payload->>'is_correct')::boolean)
UNION ALL
SELECT x.session_id, 'projection/values', 'assemblies ' || x.exposure_index
FROM assemblies x JOIN session_events e ON e.id = x.source_event_id
WHERE x.session_id IN (SELECT c.sid FROM checked c)
  AND (x.kanji_id IS DISTINCT FROM e.payload->>'kanji_id'
    OR x.duration_ms IS DISTINCT FROM (e.payload->>'duration_ms')::numeric::int
    OR x.incorrect_attempts IS DISTINCT FROM (e.payload->>'incorrect_attempts')::int)
UNION ALL
-- 4. no open projection errors
SELECT p.session_id, 'projection/open_error',
       format('%s %s (event %s): %s', p.event_type, p.error_code, p.event_id, p.detail)
FROM projection_errors p
WHERE p.resolved_at IS NULL AND p.session_id IN (SELECT c.sid FROM checked c)
$$;


--
-- Name: verify_reproducibility_fn(uuid); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.verify_reproducibility_fn(p_session uuid DEFAULT NULL::uuid) RETURNS TABLE(session_id uuid, "check" text, detail text)
    LANGUAGE sql STABLE
    AS $$
WITH seqs AS (
    SELECT b.session_id AS sid, s.created_at, b.block_state::text AS block,
           b.seed_raw, b.kanji_set AS kset,
           (SELECT string_agg(p.trial_sequence || ':' || p.trial_id || ':' || p.kanji_id || ':'
                              || p.trial_type || ':' || p.correct_option || ':'
                              || array_to_string(p.options, ','), ' | ' ORDER BY p.trial_sequence)
            FROM planned_trials p
            WHERE p.session_id = b.session_id AND p.block_state = b.block_state) AS seq
    FROM trial_blocks b JOIN experiment_sessions s ON s.id = b.session_id),
me AS (
    SELECT COALESCE(p_session, (SELECT q.sid FROM seqs q ORDER BY q.created_at DESC LIMIT 1)) AS id),
mykey AS (
    SELECT q.seed_raw, q.kset FROM seqs q WHERE q.sid = (SELECT id FROM me)
    ORDER BY q.created_at DESC LIMIT 1),
partner AS (
    SELECT q.sid FROM seqs q JOIN mykey USING (seed_raw, kset)
    WHERE q.sid <> (SELECT id FROM me)
    GROUP BY q.sid ORDER BY max(q.created_at) DESC LIMIT 1),
pair AS (
    SELECT id AS sid FROM me WHERE EXISTS (SELECT 1 FROM partner)
    UNION ALL SELECT sid FROM partner),
app AS (
    SELECT a.session_id AS sid, a.source_event_id,
           row_number() OVER (PARTITION BY a.session_id ORDER BY a.source_event_id) AS app_n
    FROM environment_applications a
    WHERE a.session_id IN (SELECT sid FROM pair)),
pe AS (
    SELECT p.session_id AS sid, p.source_event_id, p.esl, p.object_name, p.duration_ms,
           (SELECT a.app_n FROM app a
            WHERE a.sid = p.session_id AND a.source_event_id < p.source_event_id
            ORDER BY a.source_event_id DESC LIMIT 1) AS app_n
    FROM peripheral_events p
    WHERE p.session_id IN (SELECT sid FROM pair)),
ranked AS (
    SELECT pe.*, row_number() OVER (PARTITION BY pe.sid, pe.app_n ORDER BY pe.source_event_id) AS k
    FROM pe)
-- 0. events of the pair that did not project
SELECT p.session_id, 'reproducibility/open_error',
       format('%s %s (event %s): %s', p.event_type, p.error_code, p.event_id, p.detail)
FROM projection_errors p
WHERE p.resolved_at IS NULL AND p.session_id IN (SELECT sid FROM pair)
UNION ALL
-- 2. every block has one identical planned sequence in both sessions
SELECT (SELECT id FROM me), 'reproducibility/sequence',
       format('%s: %s sessions, %s distinct sequences', q.block,
              count(DISTINCT q.sid), count(DISTINCT q.seq))
FROM seqs q WHERE q.sid IN (SELECT sid FROM pair)
GROUP BY q.block
HAVING count(DISTINCT q.sid) <> 2 OR count(DISTINCT q.seq) <> 1
UNION ALL
-- 4. the trials actually presented match, options and their order included
SELECT (SELECT id FROM me), 'reproducibility/trials',
       format('%s: %s sessions, %s distinct presentations', t.trial_id,
              count(DISTINCT t.session_id), count(DISTINCT (t.kanji_id, t.trial_type, t.options)))
FROM trials t WHERE t.session_id IN (SELECT sid FROM pair)
GROUP BY t.trial_id
HAVING count(DISTINCT t.session_id) <> 2 OR count(DISTINCT (t.kanji_id, t.trial_type, t.options)) <> 1
UNION ALL
-- 6. each ESL level gives the same room in both sessions, seeded by the session
SELECT (SELECT id FROM me), 'reproducibility/environment',
       format('%s: %s sessions, %s distinct rooms, seed sources %s', a.esl,
              count(DISTINCT a.session_id),
              count(DISTINCT (a.seed, a.selection_seed,
                              COALESCE(a.active_props, '{}'), COALESCE(a.active_movers, '{}'))),
              string_agg(DISTINCT a.seed_source, ','))
FROM environment_applications a
WHERE a.session_id IN (SELECT sid FROM pair)
GROUP BY a.esl
HAVING count(DISTINCT a.session_id) <> 2
    OR count(DISTINCT (a.seed, a.selection_seed,
                       COALESCE(a.active_props, '{}'), COALESCE(a.active_movers, '{}'))) <> 1
    OR bool_or(a.seed_source IS DISTINCT FROM 'SESSION')
UNION ALL
-- 7. peripheral events: same object for the same (level application, rank inside it)
SELECT (SELECT id FROM me), 'reproducibility/peripheral',
       format('application %s rank %s: ESL %s, objects %s', r.app_n, r.k,
              string_agg(DISTINCT r.esl::text, ','), string_agg(DISTINCT r.object_name, ','))
FROM ranked r
GROUP BY r.app_n, r.k
HAVING count(DISTINCT r.sid) = 2
   AND (count(DISTINCT (r.object_name, r.duration_ms)) <> 1 OR count(DISTINCT r.esl) <> 1)
$$;


--
-- Name: verify_trials_fn(uuid); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.verify_trials_fn(p_session uuid DEFAULT NULL::uuid) RETURNS TABLE(session_id uuid, "check" text, detail text)
    LANGUAGE sql STABLE
    AS $$
WITH s AS (
    SELECT COALESCE(p_session,
                    (SELECT x.id FROM experiment_sessions x ORDER BY x.created_at DESC LIMIT 1)) AS id),
spec (lal, ttype, expected) AS (VALUES
   ('OFF',    'T1_MEANING_TO_KANJI', '{}'::text[]),
   ('OFF',    'T2_KANJI_TO_MEANING', '{}'),
   ('OFF',    'T3_KANJI_TO_READING', '{}'),
   ('LOW',    'T1_MEANING_TO_KANJI', '{}'),
   ('LOW',    'T2_KANJI_TO_MEANING', '{}'),
   ('LOW',    'T3_KANJI_TO_READING', '{}'),
   ('MEDIUM', 'T1_MEANING_TO_KANJI', '{TARGET_READING_AUDIO}'),
   ('MEDIUM', 'T2_KANJI_TO_MEANING', '{TARGET_READING_AUDIO}'),
   ('MEDIUM', 'T3_KANJI_TO_READING', '{VISUAL_ASSOCIATION}'),
   ('HIGH',   'T1_MEANING_TO_KANJI', '{TARGET_READING_AUDIO,VISUAL_TRANSFORMATION}'),
   ('HIGH',   'T2_KANJI_TO_MEANING', '{REVERSE_SEMANTIC_ASSOCIATION,TARGET_READING_AUDIO}'),
   ('HIGH',   'T3_KANJI_TO_READING', '{VISUAL_ASSOCIATION,VISUAL_TRANSFORMATION}')),
obs AS (
   SELECT DISTINCT t.lal::text AS lal, t.trial_type::text AS ttype,
          ARRAY(SELECT c FROM unnest(h.cues_granted) c ORDER BY c)::text[] AS granted
   FROM hint_requests h
   JOIN trials t ON t.session_id = h.session_id AND t.trial_id = h.trial_id
   WHERE h.session_id = (SELECT id FROM s))
-- 1. trial events that did not project
SELECT p.session_id, 'trials/open_error',
       format('%s %s (event %s): %s', p.event_type, p.error_code, p.event_id, p.detail)
FROM projection_errors p
WHERE p.session_id = (SELECT id FROM s) AND p.resolved_at IS NULL
  AND p.event_type IN ('TRIAL_STARTED', 'ANSWER_SELECTED', 'TRIAL_COMPLETED',
                       'HINT_REQUESTED', 'TRIAL_SEQUENCE_GENERATED')
UNION ALL
-- 1b. incomplete trials (started, never answered or never closed)
SELECT t.session_id, 'trials/incomplete',
       format('%s: answered %s, completed %s', t.trial_id,
              t.answer_event_id IS NOT NULL, t.completed_event_id IS NOT NULL)
FROM trials t
WHERE t.session_id = (SELECT id FROM s)
  AND (t.answer_event_id IS NULL OR t.completed_event_id IS NULL)
UNION ALL
-- 2. is_correct is selected = correct, and hint_count is the number of hint rows
SELECT t.session_id, 'trials/consistency',
       format('%s: selected %s, correct %s, is_correct %s, hint_count %s, hint rows %s',
              t.trial_id, max(t.selected_option), max(t.correct_option), bool_or(t.is_correct),
              max(t.hint_count), count(h.source_event_id))
FROM trials t
LEFT JOIN hint_requests h ON h.session_id = t.session_id AND h.trial_id = t.trial_id
WHERE t.session_id = (SELECT id FROM s) AND t.answer_event_id IS NOT NULL
GROUP BY t.session_id, t.trial_id
HAVING bool_or(t.is_correct IS DISTINCT FROM (t.selected_option = t.correct_option))
    OR (bool_or(t.completed_event_id IS NOT NULL)
        AND max(t.hint_count) IS DISTINCT FROM count(h.source_event_id)::smallint)
UNION ALL
-- 3. malformed options (four exactly, the correct and the chosen one among them)
SELECT t.session_id, 'trials/options',
       format('%s: options %s, correct %s, selected %s', t.trial_id, t.options,
              t.correct_option, t.selected_option)
FROM trials t
WHERE t.session_id = (SELECT id FROM s)
  AND (cardinality(t.options) <> 4
    OR NOT (t.correct_option = ANY (t.options))
    OR (t.selected_option IS NOT NULL AND NOT (t.selected_option = ANY (t.options))))
UNION ALL
-- 4. pre-answer audio in a T3 trial (spec 5.2 and 9.2)
SELECT h.session_id, 'trials/audio_in_t3', format('%s (LAL %s): %s', h.trial_id, t.lal, h.cues_granted)
FROM hint_requests h
JOIN trials t ON t.session_id = h.session_id AND t.trial_id = h.trial_id
WHERE h.session_id = (SELECT id FROM s)
  AND t.trial_type = 'T3_KANJI_TO_READING'
  AND 'TARGET_READING_AUDIO' = ANY (h.cues_granted)
UNION ALL
-- 5. cues granted against spec table 9.1 (both sides sorted)
SELECT (SELECT id FROM s), 'trials/cues',
       format('%s %s: granted %s, spec 9.1 %s', obs.lal, obs.ttype, obs.granted,
              ARRAY(SELECT c FROM unnest(spec.expected) c ORDER BY c))
FROM obs JOIN spec ON spec.lal = obs.lal AND spec.ttype = obs.ttype
WHERE obs.granted <> ARRAY(SELECT c FROM unnest(spec.expected) c ORDER BY c)
$$;


--
-- Name: adaptation_applications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.adaptation_applications (
    source_event_id bigint NOT NULL,
    session_id uuid NOT NULL,
    elapsed_ms integer NOT NULL,
    result character varying(8) NOT NULL,
    decision_id character varying(32),
    decision_trial_id character varying(16) NOT NULL,
    applied_before_trial_id character varying(16),
    skip_reason character varying(12),
    dimension character varying(3),
    from_level public.stimulation_level,
    to_level public.stimulation_level,
    proactive_cues boolean,
    waited_ms integer,
    esl_after public.stimulation_level,
    lal_after public.stimulation_level,
    CONSTRAINT adaptation_applications_check CHECK ((((result)::text = 'SKIPPED'::text) = (skip_reason IS NOT NULL))),
    CONSTRAINT adaptation_applications_check1 CHECK ((((result)::text = 'SKIPPED'::text) OR ((decision_id IS NOT NULL) AND (applied_before_trial_id IS NOT NULL)))),
    CONSTRAINT adaptation_applications_dimension_check CHECK (((dimension)::text = ANY ((ARRAY['ESL'::character varying, 'LAL'::character varying])::text[]))),
    CONSTRAINT adaptation_applications_result_check CHECK (((result)::text = ANY ((ARRAY['APPLIED'::character varying, 'SKIPPED'::character varying])::text[]))),
    CONSTRAINT adaptation_applications_skip_reason_check CHECK (((skip_reason)::text = ANY ((ARRAY['TIMEOUT'::character varying, 'GUARD'::character varying, 'NOT_ALLOWED'::character varying, 'INVALID'::character varying])::text[])))
);


--
-- Name: adaptation_decisions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.adaptation_decisions (
    source_event_id bigint NOT NULL,
    session_id uuid NOT NULL,
    decision_id character varying(32) NOT NULL,
    trial_id character varying(16) NOT NULL,
    trial_sequence smallint,
    decided_elapsed_ms integer NOT NULL,
    esl public.stimulation_level,
    lal public.stimulation_level,
    learner_state character varying(16) NOT NULL,
    cause character varying(16),
    confidence real NOT NULL,
    action character varying(20) NOT NULL,
    dimension character varying(3),
    from_level public.stimulation_level,
    to_level public.stimulation_level,
    proactive_cues boolean NOT NULL,
    reason_code character varying(32) NOT NULL,
    explanation text NOT NULL,
    cooldown_until_trial smallint,
    decision_latency_ms real,
    estimator_version character varying(32),
    rules_version character varying(32),
    evidence character varying(32)[],
    indicators jsonb,
    thresholds jsonb,
    outcome character varying(10),
    outcome_event_id bigint,
    eeg_counted boolean,
    eeg_ei_z real,
    eeg_theta_z real,
    eeg_effect character varying(12),
    CONSTRAINT adaptation_decisions_action_check CHECK (((action)::text = ANY ((ARRAY['NO_CHANGE'::character varying, 'CHANGE_ENVIRONMENT'::character varying, 'CHANGE_ASSISTANCE'::character varying])::text[]))),
    CONSTRAINT adaptation_decisions_cause_check CHECK (((cause)::text = ANY ((ARRAY['ENVIRONMENT'::character varying, 'AWAY'::character varying, 'IMPULSIVE'::character varying, 'FAST'::character varying, 'NO_ENVIRONMENT'::character varying])::text[]))),
    CONSTRAINT adaptation_decisions_check CHECK ((((action)::text = 'NO_CHANGE'::text) = (dimension IS NULL))),
    CONSTRAINT adaptation_decisions_check1 CHECK ((((action)::text = 'NO_CHANGE'::text) = (to_level IS NULL))),
    CONSTRAINT adaptation_decisions_check2 CHECK ((((action)::text <> 'CHANGE_ENVIRONMENT'::text) OR ((dimension)::text = 'ESL'::text))),
    CONSTRAINT adaptation_decisions_check3 CHECK ((((action)::text <> 'CHANGE_ASSISTANCE'::text) OR ((dimension)::text = 'LAL'::text))),
    CONSTRAINT adaptation_decisions_check4 CHECK (((NOT proactive_cues) OR (((dimension)::text = 'LAL'::text) AND (to_level > from_level)))),
    CONSTRAINT adaptation_decisions_confidence_check CHECK (((confidence >= (0)::double precision) AND (confidence <= (1)::double precision))),
    CONSTRAINT adaptation_decisions_dimension_check CHECK (((dimension)::text = ANY ((ARRAY['ESL'::character varying, 'LAL'::character varying])::text[]))),
    CONSTRAINT adaptation_decisions_eeg_effect_check CHECK (((eeg_effect)::text = ANY ((ARRAY['CONFIRMED'::character varying, 'VETO'::character varying, 'LED'::character varying, 'UNAVAILABLE'::character varying, 'ONLY_ALERT'::character varying, 'NEUTRAL'::character varying])::text[]))),
    CONSTRAINT adaptation_decisions_learner_state_check CHECK (((learner_state)::text = ANY ((ARRAY['STABLE'::character varying, 'DISENGAGED'::character varying, 'OVERLOADED'::character varying, 'UNDERCHALLENGED'::character varying])::text[]))),
    CONSTRAINT adaptation_decisions_outcome_check CHECK (((outcome)::text = ANY ((ARRAY['POSITIVE'::character varying, 'NEUTRAL'::character varying, 'NEGATIVE'::character varying, 'UNCERTAIN'::character varying])::text[])))
);


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: assemblies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assemblies (
    session_id uuid NOT NULL,
    exposure_index smallint NOT NULL,
    source_event_id bigint NOT NULL,
    state public.game_flow_state NOT NULL,
    kanji_id character varying(32) NOT NULL,
    completed_elapsed_ms integer NOT NULL,
    duration_ms integer NOT NULL,
    incorrect_attempts smallint NOT NULL,
    segment_count smallint NOT NULL,
    segments_placed smallint NOT NULL,
    hints_shown smallint NOT NULL,
    row_order character varying(32)[],
    segments_authored boolean,
    forced_by_researcher boolean DEFAULT false NOT NULL
);


--
-- Name: assembly_attempts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assembly_attempts (
    source_event_id bigint NOT NULL,
    session_id uuid NOT NULL,
    exposure_index smallint NOT NULL,
    elapsed_ms integer NOT NULL,
    state public.game_flow_state NOT NULL,
    kanji_id character varying(32) NOT NULL,
    attempt smallint NOT NULL,
    slot_index smallint NOT NULL,
    segment_id character varying(32) NOT NULL,
    expected_segment_id character varying(32) NOT NULL,
    is_correct boolean NOT NULL,
    selected_ms integer,
    placed_ms integer,
    hint_shown boolean,
    segments_authored boolean,
    CONSTRAINT assembly_attempts_check CHECK ((is_correct = ((segment_id)::text = (expected_segment_id)::text)))
);


--
-- Name: distractor_interactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.distractor_interactions (
    source_event_id bigint NOT NULL,
    session_id uuid NOT NULL,
    elapsed_ms integer NOT NULL,
    onset_elapsed_ms integer NOT NULL,
    state public.game_flow_state NOT NULL,
    trial_id character varying(16),
    kind character varying(10) NOT NULL,
    object_name character varying(64) NOT NULL,
    object_group character varying(12),
    duration_ms integer NOT NULL,
    peripheral_event_index integer,
    head_turn_deg real,
    box_distance_deg real,
    dwell_min_ms integer,
    dwell_break_ms integer,
    box_margin_yaw_deg real,
    box_margin_pitch_deg real,
    box_margin_deg real,
    orienting_min_deg real,
    orienting_window_ms integer,
    CONSTRAINT distractor_interactions_check CHECK ((((kind)::text = 'ORIENTING'::text) = (peripheral_event_index IS NOT NULL))),
    CONSTRAINT distractor_interactions_duration_ms_check CHECK ((duration_ms >= 0)),
    CONSTRAINT distractor_interactions_kind_check CHECK (((kind)::text = ANY ((ARRAY['DWELL'::character varying, 'ORIENTING'::character varying])::text[]))),
    CONSTRAINT distractor_interactions_object_group_check CHECK (((object_group)::text = ANY ((ARRAY['PROP'::character varying, 'MOVER'::character varying, 'PERIPHERAL'::character varying])::text[])))
);


--
-- Name: eeg_epochs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.eeg_epochs (
    session_id uuid NOT NULL,
    epoch_index integer NOT NULL,
    lsl_start double precision NOT NULL,
    start_ms integer,
    end_ms integer,
    game_state text,
    trial_id text,
    esl_level text,
    chunk_clean boolean[] NOT NULL,
    clean_fraction real NOT NULL,
    quality text NOT NULL,
    engagement_index real,
    theta_fz real,
    alpha_parietal real,
    theta_beta real,
    excluded_channels text,
    CONSTRAINT eeg_epochs_chunk_clean_check CHECK ((cardinality(chunk_clean) = ANY (ARRAY[5, 9]))),
    CONSTRAINT eeg_epochs_quality_check CHECK ((quality = ANY (ARRAY['GOOD'::text, 'ACCEPTABLE'::text, 'POOR'::text])))
);


--
-- Name: eeg_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.eeg_sessions (
    session_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    xdf_path text,
    stream_info jsonb DEFAULT '{}'::jsonb NOT NULL,
    filter_params jsonb DEFAULT '{}'::jsonb NOT NULL,
    montage jsonb DEFAULT '{"CH1": "Fp1", "CH2": "F3", "CH3": "Fz", "CH4": "F4", "CH5": "Cz", "CH6": "P3", "CH7": "Pz", "CH8": "P4"}'::jsonb NOT NULL,
    montage_change text,
    sync_offset_ms real,
    sync_drift_ms real,
    alpha_ratio jsonb,
    alpha_passed boolean,
    not_counted_reason text,
    sync_detail jsonb,
    reference jsonb,
    heartbeat_at timestamp with time zone,
    eeg_gap_ms integer,
    grid_origin_lsl double precision,
    bad_channel text,
    bad_channel_from_ms integer,
    monitor jsonb,
    monitor_at timestamp with time zone,
    ica jsonb,
    live_vs_xdf jsonb
);


--
-- Name: environment_applications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.environment_applications (
    source_event_id bigint NOT NULL,
    session_id uuid NOT NULL,
    elapsed_ms integer NOT NULL,
    state public.game_flow_state NOT NULL,
    esl public.stimulation_level NOT NULL,
    profile_name character varying(64) NOT NULL,
    prop_count smallint NOT NULL,
    mover_count smallint NOT NULL,
    active_props character varying(64)[],
    active_movers character varying(64)[],
    peripheral_interval_min_ms integer,
    peripheral_interval_max_ms integer,
    max_tier smallint,
    seed bigint,
    seed_source character varying(12),
    selection_seed bigint,
    CONSTRAINT environment_applications_seed_source_check CHECK (((seed_source)::text = ANY ((ARRAY['SESSION'::character varying, 'FALLBACK'::character varying, 'OVERRIDE'::character varying])::text[])))
);


--
-- Name: experiment_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.experiment_sessions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    participant_id uuid NOT NULL,
    condition public.experimental_condition NOT NULL,
    status public.session_status DEFAULT 'CREATED'::public.session_status NOT NULL,
    current_state public.game_flow_state DEFAULT 'S0_SESSION_INITIALIZATION'::public.game_flow_state NOT NULL,
    assigned_kanji_set character varying(8),
    visit_number integer DEFAULT 1 NOT NULL,
    random_seed character varying(64),
    software_version character varying(32),
    experiment_config_version character varying(32),
    controller_config_version character varying(32),
    session_clock_started_at timestamp with time zone,
    completed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    evaluated_session_id uuid
);


--
-- Name: head_away_episodes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.head_away_episodes (
    session_id uuid NOT NULL,
    episode integer NOT NULL,
    away_event_id bigint NOT NULL,
    returned_event_id bigint,
    state_at_onset public.game_flow_state NOT NULL,
    trial_id_at_onset character varying(16),
    confirmed_elapsed_ms integer NOT NULL,
    onset_elapsed_ms integer NOT NULL,
    returned_elapsed_ms integer,
    duration_ms integer,
    limit_crossed character varying(12) NOT NULL,
    yaw_deg real,
    pitch_deg real,
    max_abs_yaw_deg real,
    max_pitch_up_deg real,
    max_pitch_down_deg real,
    return_reason character varying(16),
    yaw_limit_deg real NOT NULL,
    pitch_up_limit_deg real NOT NULL,
    pitch_down_limit_deg real NOT NULL,
    min_away_ms integer NOT NULL,
    hysteresis_deg real,
    min_return_ms integer,
    CONSTRAINT head_away_episodes_check CHECK ((onset_elapsed_ms <= confirmed_elapsed_ms)),
    CONSTRAINT head_away_episodes_check1 CHECK (((returned_event_id IS NULL) = (duration_ms IS NULL))),
    CONSTRAINT head_away_episodes_limit_crossed_check CHECK (((limit_crossed)::text = ANY ((ARRAY['YAW'::character varying, 'PITCH_UP'::character varying, 'PITCH_DOWN'::character varying])::text[]))),
    CONSTRAINT head_away_episodes_return_reason_check CHECK (((return_reason)::text = ANY ((ARRAY['RETURNED'::character varying, 'TRACKING_LOST'::character varying, 'SESSION_END'::character varying])::text[])))
);


--
-- Name: hint_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.hint_requests (
    source_event_id bigint NOT NULL,
    session_id uuid NOT NULL,
    trial_id character varying(16) NOT NULL,
    request_seq smallint NOT NULL,
    elapsed_ms integer NOT NULL,
    time_since_trial_start_ms integer NOT NULL,
    hint_available boolean NOT NULL,
    cues_granted character varying(40)[] NOT NULL
);


--
-- Name: kanji_exposures; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.kanji_exposures (
    source_event_id bigint NOT NULL,
    session_id uuid NOT NULL,
    exposure_index smallint NOT NULL,
    kanji_id character varying(32) NOT NULL,
    elapsed_ms integer NOT NULL,
    discovery_type character varying(16),
    exposure_ms integer,
    stage_ms integer[],
    stages_authored smallint,
    audio_played boolean,
    audio_source character varying(16),
    assembly_mode character varying(16),
    CONSTRAINT kanji_exposures_assembly_mode_check CHECK (((assembly_mode)::text = ANY ((ARRAY['RAY'::character varying, 'NOT_IMPLEMENTED'::character varying])::text[]))),
    CONSTRAINT kanji_exposures_audio_source_check CHECK (((audio_source)::text = ANY ((ARRAY['AUTHORED'::character varying, 'TTS_PLACEHOLDER'::character varying, 'NONE'::character varying])::text[])))
);


--
-- Name: kanji_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.kanji_items (
    kanji_id character varying(32) NOT NULL,
    kanji_char character varying(4) NOT NULL,
    meaning character varying(64) NOT NULL,
    target_reading character varying(16) NOT NULL,
    role public.kanji_role NOT NULL,
    experimental_set character(1),
    strokes smallint NOT NULL,
    morae smallint NOT NULL,
    assembly_groups smallint NOT NULL,
    common_readings smallint NOT NULL,
    perimetric_complexity numeric(7,2),
    imageability_glyph smallint,
    imageability_object smallint,
    discovery_type character varying(16) NOT NULL,
    textbook_lesson character varying(16),
    content_schema_version integer NOT NULL,
    content_sha256 character(64) NOT NULL,
    loaded_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_kanji_set_role CHECK (((role = 'EXPERIMENTAL'::public.kanji_role) = (experimental_set IS NOT NULL))),
    CONSTRAINT kanji_items_experimental_set_check CHECK ((experimental_set = ANY (ARRAY['A'::bpchar, 'B'::bpchar, 'C'::bpchar]))),
    CONSTRAINT kanji_items_imageability_glyph_check CHECK (((imageability_glyph >= 1) AND (imageability_glyph <= 5))),
    CONSTRAINT kanji_items_imageability_object_check CHECK (((imageability_object >= 1) AND (imageability_object <= 5)))
);


--
-- Name: kanji_pretest_responses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.kanji_pretest_responses (
    participant_id uuid NOT NULL,
    kanji_id character varying(32) NOT NULL,
    seq smallint NOT NULL,
    self_report character varying(8) NOT NULL,
    typed_reading character varying(64),
    typed_meaning character varying(64),
    reading_correct_auto boolean,
    meaning_correct_auto boolean,
    reading_correct boolean,
    meaning_correct boolean,
    classification character varying(16) NOT NULL,
    answered_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_pretest_prompts CHECK ((((self_report)::text = 'NO'::text) = ((reading_correct IS NULL) AND (meaning_correct IS NULL)))),
    CONSTRAINT kanji_pretest_responses_classification_check CHECK (((classification)::text = ANY ((ARRAY['UNKNOWN'::character varying, 'PARTIALLY_KNOWN'::character varying, 'KNOWN'::character varying])::text[]))),
    CONSTRAINT kanji_pretest_responses_self_report_check CHECK (((self_report)::text = ANY ((ARRAY['NO'::character varying, 'UNSURE'::character varying, 'YES'::character varying])::text[])))
);


--
-- Name: kanji_substitutions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.kanji_substitutions (
    participant_id uuid NOT NULL,
    set_name character(1) NOT NULL,
    original_kanji_id character varying(32) NOT NULL,
    substitute_kanji_id character varying(32),
    CONSTRAINT kanji_substitutions_set_name_check CHECK ((set_name = ANY (ARRAY['A'::bpchar, 'B'::bpchar, 'C'::bpchar])))
);


--
-- Name: learner_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.learner_profiles (
    participant_id uuid NOT NULL,
    profile_version character varying(8) DEFAULT 'v1'::character varying NOT NULL,
    computed_at timestamp with time zone DEFAULT now() NOT NULL,
    session_ids uuid[] DEFAULT '{}'::uuid[] NOT NULL,
    profile jsonb NOT NULL
);


--
-- Name: participants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.participants (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    external_code character varying(32) NOT NULL,
    age_range character varying(32),
    previous_japanese_experience boolean,
    previous_kanji_experience boolean,
    previous_vr_experience boolean,
    self_rated_attention_difficulty character varying(32),
    consent_obtained boolean DEFAULT false NOT NULL,
    consent_obtained_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    pretest_completed_at timestamp with time zone
);


--
-- Name: peripheral_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.peripheral_events (
    source_event_id bigint NOT NULL,
    session_id uuid NOT NULL,
    elapsed_ms integer NOT NULL,
    state public.game_flow_state NOT NULL,
    esl public.stimulation_level NOT NULL,
    event_index integer NOT NULL,
    object_name character varying(64) NOT NULL,
    duration_ms integer NOT NULL,
    trial_id character varying(16)
);


--
-- Name: planned_trials; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.planned_trials (
    session_id uuid NOT NULL,
    trial_id character varying(16) NOT NULL,
    block_state public.game_flow_state NOT NULL,
    trial_sequence smallint NOT NULL,
    kanji_id character varying(32) NOT NULL,
    trial_type public.trial_type NOT NULL,
    options character varying(32)[] NOT NULL,
    correct_option character varying(32) NOT NULL,
    CONSTRAINT planned_trials_check CHECK (((correct_option)::text = ANY ((options)::text[]))),
    CONSTRAINT planned_trials_options_check CHECK ((cardinality(options) = 4))
);


--
-- Name: projection_errors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.projection_errors (
    id bigint NOT NULL,
    event_id bigint NOT NULL,
    session_id uuid NOT NULL,
    event_type character varying(64) NOT NULL,
    error_code character varying(32) NOT NULL,
    detail text,
    occurred_at timestamp with time zone DEFAULT now() NOT NULL,
    resolved_at timestamp with time zone
);


--
-- Name: projection_errors_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.projection_errors ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.projection_errors_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: session_config_snapshots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_config_snapshots (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id uuid NOT NULL,
    config jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: session_events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.session_events_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: session_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.session_events_id_seq OWNED BY public.session_events.id;


--
-- Name: session_states; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_states (
    session_id uuid NOT NULL,
    visit_seq smallint NOT NULL,
    state public.game_flow_state NOT NULL,
    entered_event_id bigint NOT NULL,
    entered_elapsed_ms integer NOT NULL,
    exited_elapsed_ms integer,
    transition_sound_lead_ms integer,
    esl public.stimulation_level,
    lal public.stimulation_level,
    CONSTRAINT session_states_check CHECK (((exited_elapsed_ms IS NULL) OR (exited_elapsed_ms >= entered_elapsed_ms)))
);


--
-- Name: system_validation_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.system_validation_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id uuid NOT NULL,
    component public.validation_component NOT NULL,
    status public.validation_status NOT NULL,
    detail jsonb DEFAULT '{}'::jsonb NOT NULL,
    client_timestamp timestamp with time zone,
    received_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: trial_blocks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.trial_blocks (
    session_id uuid NOT NULL,
    block_state public.game_flow_state NOT NULL,
    source_event_id bigint NOT NULL,
    generated_elapsed_ms integer NOT NULL,
    kanji_set character(1),
    seed_raw character varying(64),
    seed bigint,
    block_seed bigint,
    trial_count smallint NOT NULL,
    min_lag_requested smallint,
    min_lag_achieved smallint,
    distinct_pairs smallint,
    ordering_attempts integer
);


--
-- Name: trials; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.trials (
    session_id uuid NOT NULL,
    trial_id character varying(16) NOT NULL,
    block_state public.game_flow_state NOT NULL,
    trial_sequence smallint NOT NULL,
    trial_type public.trial_type NOT NULL,
    kanji_id character varying(32) NOT NULL,
    contract_version smallint NOT NULL,
    esl public.stimulation_level NOT NULL,
    lal public.stimulation_level NOT NULL,
    started_event_id bigint NOT NULL,
    started_elapsed_ms integer NOT NULL,
    options character varying(32)[] NOT NULL,
    correct_option character varying(32) NOT NULL,
    hint_available boolean NOT NULL,
    answer_event_id bigint,
    answered_elapsed_ms integer,
    selected_option character varying(32),
    is_correct boolean,
    response_time_ms integer,
    timed_out boolean,
    completed_event_id bigint,
    completed_elapsed_ms integer,
    hint_count smallint,
    cues_presented character varying(40)[],
    feedback_shown boolean,
    feedback_audio_source character varying(16),
    feedback_audio_ms integer,
    result_sound character varying(12),
    result_sound_offset_ms integer,
    result_sound_ms integer,
    card_animation character varying(16),
    idle_ms integer,
    idle_episodes smallint,
    idle_longest_ms integer,
    idle_min_ms integer,
    idle_head_deg_s real,
    idle_ray_deg_s real,
    cue_trigger character varying(12),
    proactive_index smallint,
    option_kinds text[],
    option_kind character varying(12),
    lure_selected boolean,
    CONSTRAINT ck_trials_proactive_index CHECK ((((proactive_index IS NULL) OR ((cue_trigger)::text = 'PROACTIVE'::text)) AND (((cue_trigger)::text IS DISTINCT FROM 'PROACTIVE'::text) OR (proactive_index IS NOT NULL)))),
    CONSTRAINT trials_card_animation_check CHECK (((card_animation)::text = ANY ((ARRAY['CORRECT_POP'::character varying, 'NONE'::character varying])::text[]))),
    CONSTRAINT trials_check CHECK (((correct_option)::text = ANY ((options)::text[]))),
    CONSTRAINT trials_check1 CHECK (((selected_option IS NULL) OR ((selected_option)::text = ANY ((options)::text[])))),
    CONSTRAINT trials_check2 CHECK (((answered_elapsed_ms IS NULL) OR (answered_elapsed_ms >= started_elapsed_ms))),
    CONSTRAINT trials_check3 CHECK (((completed_elapsed_ms IS NULL) OR (answered_elapsed_ms IS NOT NULL))),
    CONSTRAINT trials_check4 CHECK (((feedback_shown IS DISTINCT FROM false) OR ((feedback_audio_ms = 0) AND ((result_sound)::text = 'NONE'::text) AND ((card_animation)::text = 'NONE'::text)))),
    CONSTRAINT trials_check5 CHECK (((((result_sound)::text = 'NONE'::text) = (result_sound_offset_ms IS NULL)) OR (result_sound IS NULL))),
    CONSTRAINT trials_cue_trigger_check CHECK (((cue_trigger)::text = ANY ((ARRAY['PROACTIVE'::character varying, 'ON_REQUEST'::character varying])::text[]))),
    CONSTRAINT trials_feedback_audio_source_check CHECK (((feedback_audio_source)::text = ANY ((ARRAY['AUTHORED'::character varying, 'TTS_PLACEHOLDER'::character varying, 'NONE'::character varying])::text[]))),
    CONSTRAINT trials_option_kind_check CHECK (((option_kind)::text = ANY ((ARRAY['CORRECT'::character varying, 'LURE_STRONG'::character varying, 'IN_SET'::character varying, 'UNRELATED'::character varying])::text[]))),
    CONSTRAINT trials_options_check CHECK ((cardinality(options) = 4)),
    CONSTRAINT trials_proactive_index_check CHECK (((proactive_index >= 1) AND (proactive_index <= 3))),
    CONSTRAINT trials_response_time_ms_check CHECK ((response_time_ms >= 0)),
    CONSTRAINT trials_result_sound_check CHECK (((result_sound)::text = ANY ((ARRAY['CORRECT'::character varying, 'INCORRECT'::character varying, 'NONE'::character varying])::text[])))
);


--
-- Name: v_adaptations; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_adaptations AS
 SELECT d.session_id,
    d.trial_id,
    d.decision_id,
    d.decided_elapsed_ms,
    d.learner_state,
    d.cause,
    d.confidence,
    d.action,
    d.dimension,
    d.from_level,
    d.to_level,
    d.proactive_cues,
    d.reason_code,
    d.explanation,
    d.decision_latency_ms,
    d.outcome,
    a.result AS unity_result,
    a.skip_reason,
    a.applied_before_trial_id,
    a.waited_ms,
    a.elapsed_ms AS applied_elapsed_ms
   FROM (public.adaptation_decisions d
     LEFT JOIN LATERAL ( SELECT x.source_event_id,
            x.session_id,
            x.elapsed_ms,
            x.result,
            x.decision_id,
            x.decision_trial_id,
            x.applied_before_trial_id,
            x.skip_reason,
            x.dimension,
            x.from_level,
            x.to_level,
            x.proactive_cues,
            x.waited_ms,
            x.esl_after,
            x.lal_after
           FROM public.adaptation_applications x
          WHERE ((x.session_id = d.session_id) AND ((x.decision_trial_id)::text = (d.trial_id)::text))
          ORDER BY x.source_event_id DESC
         LIMIT 1) a ON (true));


--
-- Name: v_environment_intervals; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_environment_intervals AS
 SELECT source_event_id,
    session_id,
    elapsed_ms,
    state,
    esl,
    profile_name,
    prop_count,
    mover_count,
    active_props,
    active_movers,
    peripheral_interval_min_ms,
    peripheral_interval_max_ms,
    max_tier,
    seed,
    seed_source,
    selection_seed,
    lead(elapsed_ms) OVER (PARTITION BY session_id ORDER BY elapsed_ms, source_event_id) AS valid_to_ms
   FROM public.environment_applications ea;


--
-- Name: v_projection_errors; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_projection_errors AS
 SELECT p.id,
    p.session_id,
    p.event_id,
    p.event_type,
    p.error_code,
    p.detail,
    p.occurred_at,
    p.resolved_at,
        CASE
            WHEN (jsonb_typeof((e.payload -> 'session_elapsed_ms'::text)) = 'number'::text) THEN (((e.payload ->> 'session_elapsed_ms'::text))::numeric)::bigint
            ELSE NULL::bigint
        END AS session_elapsed_ms
   FROM (public.projection_errors p
     JOIN public.session_events e ON ((e.id = p.event_id)));


--
-- Name: v_session_overview; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_session_overview AS
 SELECT s.id AS session_id,
    s.participant_id,
    s.condition,
    s.status,
    s.current_state,
    s.assigned_kanji_set,
    s.visit_number,
    s.created_at,
    s.completed_at,
        CASE
            WHEN (ev.event_count = 0) THEN 'NO_DATA'::text
            WHEN (NOT (EXISTS ( SELECT 1
               FROM public.session_states x
              WHERE (x.session_id = s.id)))) THEN 'NOT_PROJECTED'::text
            ELSE 'PROJECTED'::text
        END AS projection_status,
    ev.event_count,
    ev.trials_recorded,
    ev.answers_recorded,
    ev.decisions_recorded,
    ( SELECT count(*) AS count
           FROM public.trials t
          WHERE (t.session_id = s.id)) AS trial_count,
    ans.answered,
    ans.correct,
    ((ans.correct)::numeric / (NULLIF(ans.answered, 0))::numeric) AS accuracy,
    ( SELECT count(*) AS count
           FROM public.adaptation_decisions d
          WHERE (d.session_id = s.id)) AS decision_count,
    ( SELECT count(*) AS count
           FROM public.projection_errors p
          WHERE ((p.session_id = s.id) AND (p.resolved_at IS NULL))) AS open_error_count
   FROM ((public.experiment_sessions s
     CROSS JOIN LATERAL ( SELECT count(*) AS event_count,
            COALESCE(bool_or(((e.event_type)::text = 'TRIAL_STARTED'::text)), false) AS trials_recorded,
            COALESCE(bool_or(((e.event_type)::text = 'ANSWER_SELECTED'::text)), false) AS answers_recorded,
            COALESCE(bool_or(((e.event_type)::text = 'ADAPTATION_DECISION'::text)), false) AS decisions_recorded
           FROM public.session_events e
          WHERE (e.session_id = s.id)) ev)
     CROSS JOIN LATERAL ( SELECT count(*) AS answered,
            count(*) FILTER (WHERE t.is_correct) AS correct
           FROM public.trials t
          WHERE ((t.session_id = s.id) AND (t.answer_event_id IS NOT NULL) AND (t.block_state = ANY (ARRAY['S5_STANDARDIZED_LEARNING'::public.game_flow_state, 'S6_GUIDED_PRACTICE_CALIBRATION'::public.game_flow_state, 'S7_EXPERIMENTAL_RETRIEVAL'::public.game_flow_state, 'S8_IMMEDIATE_ASSESSMENT'::public.game_flow_state])))) ans);


--
-- Name: v_trial_behavior; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_trial_behavior AS
 SELECT t.session_id,
    t.trial_id,
    COALESCE(ha.head_away_count, (0)::bigint) AS head_away_count,
    COALESCE(ha.head_away_ms, 0) AS head_away_ms,
    COALESCE(pe.peripheral_count, (0)::bigint) AS peripheral_event_count
   FROM ((public.trials t
     LEFT JOIN LATERAL ( SELECT count(*) AS head_away_count,
            (sum((LEAST(COALESCE(h.returned_elapsed_ms, t.answered_elapsed_ms), t.answered_elapsed_ms) - GREATEST(h.onset_elapsed_ms, t.started_elapsed_ms))))::integer AS head_away_ms
           FROM public.head_away_episodes h
          WHERE ((h.session_id = t.session_id) AND (t.answered_elapsed_ms IS NOT NULL) AND (h.onset_elapsed_ms < t.answered_elapsed_ms) AND (COALESCE(h.returned_elapsed_ms, t.answered_elapsed_ms) > t.started_elapsed_ms))) ha ON (true))
     LEFT JOIN LATERAL ( SELECT count(*) AS peripheral_count
           FROM public.peripheral_events p
          WHERE ((p.session_id = t.session_id) AND (p.elapsed_ms >= t.started_elapsed_ms) AND (p.elapsed_ms < COALESCE(t.completed_elapsed_ms, t.answered_elapsed_ms, t.started_elapsed_ms)))) pe ON (true));


--
-- Name: session_events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events ALTER COLUMN id SET DEFAULT nextval('public.session_events_id_seq'::regclass);


--
-- Name: adaptation_applications adaptation_applications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.adaptation_applications
    ADD CONSTRAINT adaptation_applications_pkey PRIMARY KEY (source_event_id);


--
-- Name: adaptation_decisions adaptation_decisions_outcome_event_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.adaptation_decisions
    ADD CONSTRAINT adaptation_decisions_outcome_event_id_key UNIQUE (outcome_event_id);


--
-- Name: adaptation_decisions adaptation_decisions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.adaptation_decisions
    ADD CONSTRAINT adaptation_decisions_pkey PRIMARY KEY (source_event_id);


--
-- Name: adaptation_decisions adaptation_decisions_session_id_decision_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.adaptation_decisions
    ADD CONSTRAINT adaptation_decisions_session_id_decision_id_key UNIQUE (session_id, decision_id);


--
-- Name: adaptation_decisions adaptation_decisions_session_id_trial_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.adaptation_decisions
    ADD CONSTRAINT adaptation_decisions_session_id_trial_id_key UNIQUE (session_id, trial_id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: assemblies assemblies_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assemblies
    ADD CONSTRAINT assemblies_pkey PRIMARY KEY (session_id, exposure_index);


--
-- Name: assemblies assemblies_source_event_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assemblies
    ADD CONSTRAINT assemblies_source_event_id_key UNIQUE (source_event_id);


--
-- Name: assembly_attempts assembly_attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assembly_attempts
    ADD CONSTRAINT assembly_attempts_pkey PRIMARY KEY (source_event_id);


--
-- Name: assembly_attempts assembly_attempts_session_id_exposure_index_attempt_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assembly_attempts
    ADD CONSTRAINT assembly_attempts_session_id_exposure_index_attempt_key UNIQUE (session_id, exposure_index, attempt);


--
-- Name: distractor_interactions distractor_interactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.distractor_interactions
    ADD CONSTRAINT distractor_interactions_pkey PRIMARY KEY (source_event_id);


--
-- Name: eeg_epochs eeg_epochs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eeg_epochs
    ADD CONSTRAINT eeg_epochs_pkey PRIMARY KEY (session_id, epoch_index);


--
-- Name: eeg_sessions eeg_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eeg_sessions
    ADD CONSTRAINT eeg_sessions_pkey PRIMARY KEY (session_id);


--
-- Name: environment_applications environment_applications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.environment_applications
    ADD CONSTRAINT environment_applications_pkey PRIMARY KEY (source_event_id);


--
-- Name: experiment_sessions experiment_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.experiment_sessions
    ADD CONSTRAINT experiment_sessions_pkey PRIMARY KEY (id);


--
-- Name: head_away_episodes head_away_episodes_away_event_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.head_away_episodes
    ADD CONSTRAINT head_away_episodes_away_event_id_key UNIQUE (away_event_id);


--
-- Name: head_away_episodes head_away_episodes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.head_away_episodes
    ADD CONSTRAINT head_away_episodes_pkey PRIMARY KEY (session_id, episode);


--
-- Name: head_away_episodes head_away_episodes_returned_event_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.head_away_episodes
    ADD CONSTRAINT head_away_episodes_returned_event_id_key UNIQUE (returned_event_id);


--
-- Name: hint_requests hint_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hint_requests
    ADD CONSTRAINT hint_requests_pkey PRIMARY KEY (source_event_id);


--
-- Name: hint_requests hint_requests_session_id_trial_id_request_seq_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hint_requests
    ADD CONSTRAINT hint_requests_session_id_trial_id_request_seq_key UNIQUE (session_id, trial_id, request_seq);


--
-- Name: kanji_exposures kanji_exposures_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kanji_exposures
    ADD CONSTRAINT kanji_exposures_pkey PRIMARY KEY (source_event_id);


--
-- Name: kanji_exposures kanji_exposures_session_id_exposure_index_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kanji_exposures
    ADD CONSTRAINT kanji_exposures_session_id_exposure_index_key UNIQUE (session_id, exposure_index);


--
-- Name: kanji_items kanji_items_kanji_char_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kanji_items
    ADD CONSTRAINT kanji_items_kanji_char_key UNIQUE (kanji_char);


--
-- Name: kanji_items kanji_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kanji_items
    ADD CONSTRAINT kanji_items_pkey PRIMARY KEY (kanji_id);


--
-- Name: kanji_pretest_responses kanji_pretest_responses_participant_id_seq_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kanji_pretest_responses
    ADD CONSTRAINT kanji_pretest_responses_participant_id_seq_key UNIQUE (participant_id, seq);


--
-- Name: kanji_pretest_responses kanji_pretest_responses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kanji_pretest_responses
    ADD CONSTRAINT kanji_pretest_responses_pkey PRIMARY KEY (participant_id, kanji_id);


--
-- Name: kanji_substitutions kanji_substitutions_participant_id_substitute_kanji_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kanji_substitutions
    ADD CONSTRAINT kanji_substitutions_participant_id_substitute_kanji_id_key UNIQUE (participant_id, substitute_kanji_id);


--
-- Name: kanji_substitutions kanji_substitutions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kanji_substitutions
    ADD CONSTRAINT kanji_substitutions_pkey PRIMARY KEY (participant_id, original_kanji_id);


--
-- Name: learner_profiles learner_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.learner_profiles
    ADD CONSTRAINT learner_profiles_pkey PRIMARY KEY (participant_id, profile_version);


--
-- Name: participants participants_external_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.participants
    ADD CONSTRAINT participants_external_code_key UNIQUE (external_code);


--
-- Name: participants participants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.participants
    ADD CONSTRAINT participants_pkey PRIMARY KEY (id);


--
-- Name: peripheral_events peripheral_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.peripheral_events
    ADD CONSTRAINT peripheral_events_pkey PRIMARY KEY (source_event_id);


--
-- Name: peripheral_events peripheral_events_session_id_event_index_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.peripheral_events
    ADD CONSTRAINT peripheral_events_session_id_event_index_key UNIQUE (session_id, event_index);


--
-- Name: planned_trials planned_trials_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.planned_trials
    ADD CONSTRAINT planned_trials_pkey PRIMARY KEY (session_id, trial_id);


--
-- Name: planned_trials planned_trials_session_id_block_state_trial_sequence_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.planned_trials
    ADD CONSTRAINT planned_trials_session_id_block_state_trial_sequence_key UNIQUE (session_id, block_state, trial_sequence);


--
-- Name: projection_errors projection_errors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projection_errors
    ADD CONSTRAINT projection_errors_pkey PRIMARY KEY (id);


--
-- Name: session_config_snapshots session_config_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_config_snapshots
    ADD CONSTRAINT session_config_snapshots_pkey PRIMARY KEY (id);


--
-- Name: session_config_snapshots session_config_snapshots_session_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_config_snapshots
    ADD CONSTRAINT session_config_snapshots_session_id_key UNIQUE (session_id);


--
-- Name: session_events session_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events
    ADD CONSTRAINT session_events_pkey PRIMARY KEY (id);


--
-- Name: session_states session_states_entered_event_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_states
    ADD CONSTRAINT session_states_entered_event_id_key UNIQUE (entered_event_id);


--
-- Name: session_states session_states_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_states
    ADD CONSTRAINT session_states_pkey PRIMARY KEY (session_id, visit_seq);


--
-- Name: system_validation_events system_validation_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_validation_events
    ADD CONSTRAINT system_validation_events_pkey PRIMARY KEY (id);


--
-- Name: trial_blocks trial_blocks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trial_blocks
    ADD CONSTRAINT trial_blocks_pkey PRIMARY KEY (session_id, block_state);


--
-- Name: trial_blocks trial_blocks_source_event_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trial_blocks
    ADD CONSTRAINT trial_blocks_source_event_id_key UNIQUE (source_event_id);


--
-- Name: trials trials_answer_event_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trials
    ADD CONSTRAINT trials_answer_event_id_key UNIQUE (answer_event_id);


--
-- Name: trials trials_completed_event_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trials
    ADD CONSTRAINT trials_completed_event_id_key UNIQUE (completed_event_id);


--
-- Name: trials trials_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trials
    ADD CONSTRAINT trials_pkey PRIMARY KEY (session_id, trial_id);


--
-- Name: trials trials_session_id_block_state_trial_sequence_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trials
    ADD CONSTRAINT trials_session_id_block_state_trial_sequence_key UNIQUE (session_id, block_state, trial_sequence);


--
-- Name: trials trials_started_event_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trials
    ADD CONSTRAINT trials_started_event_id_key UNIQUE (started_event_id);


--
-- Name: ix_adaptation_app_trial; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_adaptation_app_trial ON public.adaptation_applications USING btree (session_id, decision_trial_id);


--
-- Name: ix_distractor_session_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_distractor_session_time ON public.distractor_interactions USING btree (session_id, elapsed_ms);


--
-- Name: ix_env_app_session_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_env_app_session_time ON public.environment_applications USING btree (session_id, elapsed_ms);


--
-- Name: ix_experiment_sessions_participant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_experiment_sessions_participant_id ON public.experiment_sessions USING btree (participant_id);


--
-- Name: ix_head_away_session_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_head_away_session_time ON public.head_away_episodes USING btree (session_id, onset_elapsed_ms);


--
-- Name: ix_participants_external_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_participants_external_code ON public.participants USING btree (external_code);


--
-- Name: ix_peripheral_session_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_peripheral_session_time ON public.peripheral_events USING btree (session_id, elapsed_ms);


--
-- Name: ix_projection_errors_open; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_projection_errors_open ON public.projection_errors USING btree (session_id) WHERE (resolved_at IS NULL);


--
-- Name: ix_session_events_event_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_session_events_event_type ON public.session_events USING btree (event_type);


--
-- Name: ix_session_events_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_session_events_session_id ON public.session_events USING btree (session_id);


--
-- Name: ix_session_events_session_trial; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_session_events_session_trial ON public.session_events USING btree (session_id, ((payload ->> 'trial_id'::text))) WHERE (payload ? 'trial_id'::text);


--
-- Name: ix_system_validation_events_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_system_validation_events_session_id ON public.system_validation_events USING btree (session_id);


--
-- Name: ix_trials_kanji; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_trials_kanji ON public.trials USING btree (kanji_id);


--
-- Name: adaptation_applications adaptation_applications_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.adaptation_applications
    ADD CONSTRAINT adaptation_applications_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.experiment_sessions(id) ON DELETE CASCADE;


--
-- Name: adaptation_applications adaptation_applications_source_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.adaptation_applications
    ADD CONSTRAINT adaptation_applications_source_event_id_fkey FOREIGN KEY (source_event_id) REFERENCES public.session_events(id) ON DELETE CASCADE;


--
-- Name: adaptation_decisions adaptation_decisions_outcome_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.adaptation_decisions
    ADD CONSTRAINT adaptation_decisions_outcome_event_id_fkey FOREIGN KEY (outcome_event_id) REFERENCES public.session_events(id) ON DELETE CASCADE;


--
-- Name: adaptation_decisions adaptation_decisions_session_id_trial_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.adaptation_decisions
    ADD CONSTRAINT adaptation_decisions_session_id_trial_id_fkey FOREIGN KEY (session_id, trial_id) REFERENCES public.trials(session_id, trial_id) ON DELETE CASCADE;


--
-- Name: adaptation_decisions adaptation_decisions_source_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.adaptation_decisions
    ADD CONSTRAINT adaptation_decisions_source_event_id_fkey FOREIGN KEY (source_event_id) REFERENCES public.session_events(id) ON DELETE CASCADE;


--
-- Name: assemblies assemblies_kanji_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assemblies
    ADD CONSTRAINT assemblies_kanji_id_fkey FOREIGN KEY (kanji_id) REFERENCES public.kanji_items(kanji_id);


--
-- Name: assemblies assemblies_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assemblies
    ADD CONSTRAINT assemblies_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.experiment_sessions(id) ON DELETE CASCADE;


--
-- Name: assemblies assemblies_source_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assemblies
    ADD CONSTRAINT assemblies_source_event_id_fkey FOREIGN KEY (source_event_id) REFERENCES public.session_events(id) ON DELETE CASCADE;


--
-- Name: assembly_attempts assembly_attempts_kanji_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assembly_attempts
    ADD CONSTRAINT assembly_attempts_kanji_id_fkey FOREIGN KEY (kanji_id) REFERENCES public.kanji_items(kanji_id);


--
-- Name: assembly_attempts assembly_attempts_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assembly_attempts
    ADD CONSTRAINT assembly_attempts_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.experiment_sessions(id) ON DELETE CASCADE;


--
-- Name: assembly_attempts assembly_attempts_source_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assembly_attempts
    ADD CONSTRAINT assembly_attempts_source_event_id_fkey FOREIGN KEY (source_event_id) REFERENCES public.session_events(id) ON DELETE CASCADE;


--
-- Name: distractor_interactions distractor_interactions_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.distractor_interactions
    ADD CONSTRAINT distractor_interactions_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.experiment_sessions(id) ON DELETE CASCADE;


--
-- Name: distractor_interactions distractor_interactions_source_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.distractor_interactions
    ADD CONSTRAINT distractor_interactions_source_event_id_fkey FOREIGN KEY (source_event_id) REFERENCES public.session_events(id) ON DELETE CASCADE;


--
-- Name: eeg_epochs eeg_epochs_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eeg_epochs
    ADD CONSTRAINT eeg_epochs_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.eeg_sessions(session_id) ON DELETE CASCADE;


--
-- Name: eeg_sessions eeg_sessions_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eeg_sessions
    ADD CONSTRAINT eeg_sessions_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.experiment_sessions(id) ON DELETE CASCADE;


--
-- Name: environment_applications environment_applications_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.environment_applications
    ADD CONSTRAINT environment_applications_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.experiment_sessions(id) ON DELETE CASCADE;


--
-- Name: environment_applications environment_applications_source_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.environment_applications
    ADD CONSTRAINT environment_applications_source_event_id_fkey FOREIGN KEY (source_event_id) REFERENCES public.session_events(id) ON DELETE CASCADE;


--
-- Name: experiment_sessions experiment_sessions_evaluated_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.experiment_sessions
    ADD CONSTRAINT experiment_sessions_evaluated_session_id_fkey FOREIGN KEY (evaluated_session_id) REFERENCES public.experiment_sessions(id) ON DELETE SET NULL;


--
-- Name: experiment_sessions experiment_sessions_participant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.experiment_sessions
    ADD CONSTRAINT experiment_sessions_participant_id_fkey FOREIGN KEY (participant_id) REFERENCES public.participants(id) ON DELETE CASCADE;


--
-- Name: head_away_episodes head_away_episodes_away_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.head_away_episodes
    ADD CONSTRAINT head_away_episodes_away_event_id_fkey FOREIGN KEY (away_event_id) REFERENCES public.session_events(id) ON DELETE CASCADE;


--
-- Name: head_away_episodes head_away_episodes_returned_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.head_away_episodes
    ADD CONSTRAINT head_away_episodes_returned_event_id_fkey FOREIGN KEY (returned_event_id) REFERENCES public.session_events(id) ON DELETE CASCADE;


--
-- Name: head_away_episodes head_away_episodes_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.head_away_episodes
    ADD CONSTRAINT head_away_episodes_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.experiment_sessions(id) ON DELETE CASCADE;


--
-- Name: hint_requests hint_requests_session_id_trial_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hint_requests
    ADD CONSTRAINT hint_requests_session_id_trial_id_fkey FOREIGN KEY (session_id, trial_id) REFERENCES public.trials(session_id, trial_id) ON DELETE CASCADE;


--
-- Name: hint_requests hint_requests_source_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hint_requests
    ADD CONSTRAINT hint_requests_source_event_id_fkey FOREIGN KEY (source_event_id) REFERENCES public.session_events(id) ON DELETE CASCADE;


--
-- Name: kanji_exposures kanji_exposures_kanji_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kanji_exposures
    ADD CONSTRAINT kanji_exposures_kanji_id_fkey FOREIGN KEY (kanji_id) REFERENCES public.kanji_items(kanji_id);


--
-- Name: kanji_exposures kanji_exposures_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kanji_exposures
    ADD CONSTRAINT kanji_exposures_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.experiment_sessions(id) ON DELETE CASCADE;


--
-- Name: kanji_exposures kanji_exposures_source_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kanji_exposures
    ADD CONSTRAINT kanji_exposures_source_event_id_fkey FOREIGN KEY (source_event_id) REFERENCES public.session_events(id) ON DELETE CASCADE;


--
-- Name: kanji_pretest_responses kanji_pretest_responses_kanji_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kanji_pretest_responses
    ADD CONSTRAINT kanji_pretest_responses_kanji_id_fkey FOREIGN KEY (kanji_id) REFERENCES public.kanji_items(kanji_id);


--
-- Name: kanji_pretest_responses kanji_pretest_responses_participant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kanji_pretest_responses
    ADD CONSTRAINT kanji_pretest_responses_participant_id_fkey FOREIGN KEY (participant_id) REFERENCES public.participants(id) ON DELETE CASCADE;


--
-- Name: kanji_substitutions kanji_substitutions_original_kanji_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kanji_substitutions
    ADD CONSTRAINT kanji_substitutions_original_kanji_id_fkey FOREIGN KEY (original_kanji_id) REFERENCES public.kanji_items(kanji_id);


--
-- Name: kanji_substitutions kanji_substitutions_participant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kanji_substitutions
    ADD CONSTRAINT kanji_substitutions_participant_id_fkey FOREIGN KEY (participant_id) REFERENCES public.participants(id) ON DELETE CASCADE;


--
-- Name: kanji_substitutions kanji_substitutions_substitute_kanji_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kanji_substitutions
    ADD CONSTRAINT kanji_substitutions_substitute_kanji_id_fkey FOREIGN KEY (substitute_kanji_id) REFERENCES public.kanji_items(kanji_id);


--
-- Name: learner_profiles learner_profiles_participant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.learner_profiles
    ADD CONSTRAINT learner_profiles_participant_id_fkey FOREIGN KEY (participant_id) REFERENCES public.participants(id) ON DELETE CASCADE;


--
-- Name: peripheral_events peripheral_events_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.peripheral_events
    ADD CONSTRAINT peripheral_events_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.experiment_sessions(id) ON DELETE CASCADE;


--
-- Name: peripheral_events peripheral_events_source_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.peripheral_events
    ADD CONSTRAINT peripheral_events_source_event_id_fkey FOREIGN KEY (source_event_id) REFERENCES public.session_events(id) ON DELETE CASCADE;


--
-- Name: planned_trials planned_trials_kanji_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.planned_trials
    ADD CONSTRAINT planned_trials_kanji_id_fkey FOREIGN KEY (kanji_id) REFERENCES public.kanji_items(kanji_id);


--
-- Name: planned_trials planned_trials_session_id_block_state_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.planned_trials
    ADD CONSTRAINT planned_trials_session_id_block_state_fkey FOREIGN KEY (session_id, block_state) REFERENCES public.trial_blocks(session_id, block_state) ON DELETE CASCADE;


--
-- Name: projection_errors projection_errors_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projection_errors
    ADD CONSTRAINT projection_errors_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.session_events(id) ON DELETE CASCADE;


--
-- Name: projection_errors projection_errors_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projection_errors
    ADD CONSTRAINT projection_errors_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.experiment_sessions(id) ON DELETE CASCADE;


--
-- Name: session_config_snapshots session_config_snapshots_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_config_snapshots
    ADD CONSTRAINT session_config_snapshots_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.experiment_sessions(id) ON DELETE CASCADE;


--
-- Name: session_events session_events_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_events
    ADD CONSTRAINT session_events_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.experiment_sessions(id) ON DELETE CASCADE;


--
-- Name: session_states session_states_entered_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_states
    ADD CONSTRAINT session_states_entered_event_id_fkey FOREIGN KEY (entered_event_id) REFERENCES public.session_events(id) ON DELETE CASCADE;


--
-- Name: session_states session_states_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_states
    ADD CONSTRAINT session_states_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.experiment_sessions(id) ON DELETE CASCADE;


--
-- Name: system_validation_events system_validation_events_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_validation_events
    ADD CONSTRAINT system_validation_events_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.experiment_sessions(id) ON DELETE CASCADE;


--
-- Name: trial_blocks trial_blocks_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trial_blocks
    ADD CONSTRAINT trial_blocks_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.experiment_sessions(id) ON DELETE CASCADE;


--
-- Name: trial_blocks trial_blocks_source_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trial_blocks
    ADD CONSTRAINT trial_blocks_source_event_id_fkey FOREIGN KEY (source_event_id) REFERENCES public.session_events(id) ON DELETE CASCADE;


--
-- Name: trials trials_answer_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trials
    ADD CONSTRAINT trials_answer_event_id_fkey FOREIGN KEY (answer_event_id) REFERENCES public.session_events(id) ON DELETE CASCADE;


--
-- Name: trials trials_completed_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trials
    ADD CONSTRAINT trials_completed_event_id_fkey FOREIGN KEY (completed_event_id) REFERENCES public.session_events(id) ON DELETE CASCADE;


--
-- Name: trials trials_kanji_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trials
    ADD CONSTRAINT trials_kanji_id_fkey FOREIGN KEY (kanji_id) REFERENCES public.kanji_items(kanji_id);


--
-- Name: trials trials_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trials
    ADD CONSTRAINT trials_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.experiment_sessions(id) ON DELETE CASCADE;


--
-- Name: trials trials_started_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trials
    ADD CONSTRAINT trials_started_event_id_fkey FOREIGN KEY (started_event_id) REFERENCES public.session_events(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--



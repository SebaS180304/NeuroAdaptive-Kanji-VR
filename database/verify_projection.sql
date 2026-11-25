-- verify_projection.sql -- schema v1 (F3.4), MER_Schema_v1.md sec. 6
-- The projected tables must say exactly what session_events says.
--
-- Checks every session that has been projected (has rows in session_states
-- or trials, or any projection error). Run project_session(id) first for the
-- sessions to backfill:
--   SELECT project_session('<uuid>');
--
-- Usage (PowerShell, repo root):
--   Get-Content database\verify_projection.sql | docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr
--
-- Query 1 lists what was checked. Queries 2-4 are the checks: ANY row they
-- return is a discrepancy.

\set ON_ERROR_STOP on

CREATE TEMP VIEW checked AS
SELECT DISTINCT session_id FROM session_states
UNION SELECT DISTINCT session_id FROM trials
UNION SELECT DISTINCT session_id FROM projection_errors WHERE resolved_at IS NULL;

-- 1. Sessions checked
SELECT c.session_id, s.created_at, s.current_state,
       (SELECT count(*) FROM session_events e WHERE e.session_id = c.session_id) AS events
FROM checked c JOIN experiment_sessions s ON s.id = c.session_id
ORDER BY s.created_at;

-- 2. CHECK: event -> row counts, per session and event type
WITH expected AS (
    SELECT session_id, event_type, count(*) AS n
    FROM session_events
    WHERE session_id IN (SELECT session_id FROM checked)
    GROUP BY 1, 2),
got AS (
              SELECT session_id, 'STATE_ENTERED' et, count(*) n FROM session_states GROUP BY 1
    UNION ALL SELECT session_id, 'TRIAL_SEQUENCE_GENERATED', count(*) FROM trial_blocks GROUP BY 1
    UNION ALL SELECT session_id, 'TRIAL_STARTED', count(*) FROM trials GROUP BY 1
    UNION ALL SELECT session_id, 'ANSWER_SELECTED', count(answer_event_id) FROM trials GROUP BY 1
    UNION ALL SELECT session_id, 'TRIAL_COMPLETED', count(completed_event_id) FROM trials GROUP BY 1
    UNION ALL SELECT session_id, 'HINT_REQUESTED', count(*) FROM hint_requests GROUP BY 1
    UNION ALL SELECT session_id, 'ENVIRONMENT_APPLIED', count(*) FROM environment_applications GROUP BY 1
    UNION ALL SELECT session_id, 'PERIPHERAL_EVENT', count(*) FROM peripheral_events GROUP BY 1
    UNION ALL SELECT session_id, 'HEAD_AWAY', count(*) FROM head_away_episodes GROUP BY 1
    UNION ALL SELECT session_id, 'HEAD_RETURNED', count(returned_event_id) FROM head_away_episodes GROUP BY 1
    UNION ALL SELECT session_id, 'KANJI_EXPOSED', count(*) FROM kanji_exposures GROUP BY 1
    UNION ALL SELECT session_id, 'ASSEMBLY_SEGMENT_PLACED', count(*) FROM assembly_attempts GROUP BY 1
    UNION ALL SELECT session_id, 'ASSEMBLY_COMPLETED', count(*) FROM assemblies GROUP BY 1),
types AS (SELECT DISTINCT et FROM got),
grid AS (SELECT c.session_id, t.et FROM checked c CROSS JOIN types t)
SELECT g.session_id, g.et AS event_type,
       COALESCE(e.n, 0) AS events, COALESCE(r.n, 0) AS rows
FROM grid g
LEFT JOIN expected e ON e.session_id = g.session_id AND e.event_type = g.et
LEFT JOIN got r      ON r.session_id = g.session_id AND r.et = g.et
WHERE COALESCE(e.n, 0) <> COALESCE(r.n, 0)
UNION ALL
-- planned trials: one row per entry of every sequence
SELECT b.session_id, 'TRIAL_SEQUENCE_GENERATED/sequence',
       jsonb_array_length(e.payload -> 'sequence'),
       (SELECT count(*) FROM planned_trials p
        WHERE p.session_id = b.session_id AND p.block_state = b.block_state)
FROM trial_blocks b JOIN session_events e ON e.id = b.source_event_id
WHERE b.session_id IN (SELECT session_id FROM checked)
  AND jsonb_array_length(e.payload -> 'sequence') <>
      (SELECT count(*) FROM planned_trials p
       WHERE p.session_id = b.session_id AND p.block_state = b.block_state)
ORDER BY 1, 2;

-- 3. CHECK: value by value, each row against the event that holds its id
SELECT t.session_id, t.trial_id, 'trials/started' AS what
FROM trials t JOIN session_events e ON e.id = t.started_event_id
WHERE t.session_id IN (SELECT session_id FROM checked)
  AND (t.started_elapsed_ms IS DISTINCT FROM (e.payload->>'session_elapsed_ms')::numeric::int
    OR t.kanji_id IS DISTINCT FROM e.payload->>'kanji_id'
    OR t.trial_type::text IS DISTINCT FROM e.payload->>'trial_type'
    OR t.esl::text IS DISTINCT FROM e.payload->>'esl'
    OR t.lal::text IS DISTINCT FROM e.payload->>'lal'
    OR t.options IS DISTINCT FROM ARRAY(SELECT jsonb_array_elements_text(e.payload->'options'))::varchar[]
    OR t.correct_option IS DISTINCT FROM e.payload->>'correct_option'
    OR t.hint_available IS DISTINCT FROM (e.payload->>'hint_available')::boolean)
UNION ALL
SELECT t.session_id, t.trial_id, 'trials/answer'
FROM trials t JOIN session_events e ON e.id = t.answer_event_id
WHERE t.session_id IN (SELECT session_id FROM checked)
  AND (t.answered_elapsed_ms IS DISTINCT FROM (e.payload->>'session_elapsed_ms')::numeric::int
    OR t.selected_option IS DISTINCT FROM e.payload->>'selected_option'
    OR t.is_correct IS DISTINCT FROM (e.payload->>'is_correct')::boolean
    OR t.response_time_ms IS DISTINCT FROM (e.payload->>'response_time_ms')::numeric::int)
UNION ALL
SELECT t.session_id, t.trial_id, 'trials/completed'
FROM trials t JOIN session_events e ON e.id = t.completed_event_id
WHERE t.session_id IN (SELECT session_id FROM checked)
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
SELECT h.session_id, h.trial_id || '#' || h.request_seq, 'hint_requests'
FROM hint_requests h JOIN session_events e ON e.id = h.source_event_id
WHERE h.session_id IN (SELECT session_id FROM checked)
  AND (h.trial_id IS DISTINCT FROM e.payload->>'trial_id'
    OR h.time_since_trial_start_ms IS DISTINCT FROM (e.payload->>'time_since_trial_start_ms')::numeric::int
    OR h.cues_granted IS DISTINCT FROM
       ARRAY(SELECT jsonb_array_elements_text(COALESCE(e.payload->'hint_type', '[]')))::varchar[])
UNION ALL
SELECT s.session_id, s.state::text || '#' || s.visit_seq, 'session_states'
FROM session_states s JOIN session_events e ON e.id = s.entered_event_id
WHERE s.session_id IN (SELECT session_id FROM checked)
  AND (s.state::text IS DISTINCT FROM e.payload->>'state'
    OR s.entered_elapsed_ms IS DISTINCT FROM (e.payload->>'session_elapsed_ms')::numeric::int
    OR s.transition_sound_lead_ms IS DISTINCT FROM (e.payload->>'transition_sound_lead_ms')::numeric::int)
UNION ALL
SELECT a.session_id, a.elapsed_ms::text, 'environment_applications'
FROM environment_applications a JOIN session_events e ON e.id = a.source_event_id
WHERE a.session_id IN (SELECT session_id FROM checked)
  AND (a.esl::text IS DISTINCT FROM e.payload->>'esl'
    OR a.profile_name IS DISTINCT FROM e.payload->>'profile_name'
    OR a.prop_count IS DISTINCT FROM (e.payload->>'prop_count')::int
    OR a.mover_count IS DISTINCT FROM (e.payload->>'mover_count')::int
    OR a.seed IS DISTINCT FROM (e.payload->>'seed')::bigint
    OR a.seed_source IS DISTINCT FROM e.payload->>'seed_source'
    OR a.selection_seed IS DISTINCT FROM (e.payload->>'selection_seed')::bigint)
UNION ALL
SELECT h.session_id, 'episode ' || h.episode, 'head_away_episodes'
FROM head_away_episodes h
JOIN session_events a ON a.id = h.away_event_id
LEFT JOIN session_events r ON r.id = h.returned_event_id
WHERE h.session_id IN (SELECT session_id FROM checked)
  AND (h.onset_elapsed_ms IS DISTINCT FROM
         (a.payload->>'session_elapsed_ms')::numeric::int + (a.payload->>'onset_offset_ms')::numeric::int
    OR h.limit_crossed IS DISTINCT FROM a.payload->>'limit'
    OR h.yaw_limit_deg IS DISTINCT FROM (a.payload->>'yaw_limit_deg')::real
    OR h.min_away_ms IS DISTINCT FROM (a.payload->>'min_away_ms')::numeric::int
    OR h.duration_ms IS DISTINCT FROM (r.payload->>'duration_ms')::numeric::int
    OR h.return_reason IS DISTINCT FROM r.payload->>'reason')
UNION ALL
SELECT x.session_id, x.exposure_index || '#' || x.attempt, 'assembly_attempts'
FROM assembly_attempts x JOIN session_events e ON e.id = x.source_event_id
WHERE x.session_id IN (SELECT session_id FROM checked)
  AND (x.kanji_id IS DISTINCT FROM e.payload->>'kanji_id'
    OR x.segment_id IS DISTINCT FROM e.payload->>'segment_id'
    OR x.is_correct IS DISTINCT FROM (e.payload->>'is_correct')::boolean)
UNION ALL
SELECT x.session_id, x.exposure_index::text, 'assemblies'
FROM assemblies x JOIN session_events e ON e.id = x.source_event_id
WHERE x.session_id IN (SELECT session_id FROM checked)
  AND (x.kanji_id IS DISTINCT FROM e.payload->>'kanji_id'
    OR x.duration_ms IS DISTINCT FROM (e.payload->>'duration_ms')::numeric::int
    OR x.incorrect_attempts IS DISTINCT FROM (e.payload->>'incorrect_attempts')::int)
ORDER BY 1, 3, 2;

-- 4. CHECK: no open projection errors
SELECT session_id, event_id, event_type, error_code, detail
FROM projection_errors
WHERE resolved_at IS NULL AND session_id IN (SELECT session_id FROM checked)
ORDER BY session_id, event_id;

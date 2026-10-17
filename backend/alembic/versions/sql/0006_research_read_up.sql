-- NeuroAdaptive VR -- research portal, read side -- migration 0006 (up)
-- Read-only SQL for the /research router (tasks/plan.md, Task 0.3):
--   v_session_overview   one row per session (projection status, counts, accuracy)
--   v_projection_errors  projection_errors plus the session time of the failed event
--   verify_*_fn()        the checks of database/verify_*.sql as functions that return one
--                        (session_id, check, detail) row per discrepancy
-- The .sql scripts stay as they are for psql use: a change to a check goes in both places.
-- verify_*_fn(NULL) checks what its script checks; verify_*_fn('<id>') checks that session.

-- ---------------------------------------------------------------------
-- v_session_overview
-- ---------------------------------------------------------------------
-- projection_status: NO_DATA (no events), NOT_PROJECTED (events but no session_states
-- rows) or PROJECTED. A count is only meaningful when its *_recorded flag is true:
-- trial_count 0 with trials_recorded false means "never reached", not "zero trials".
-- accuracy: answered S5-S8 trials only; NULL when none was answered.
CREATE VIEW v_session_overview AS
SELECT s.id AS session_id, s.participant_id, s.condition, s.status, s.current_state,
       s.assigned_kanji_set, s.visit_number, s.created_at, s.completed_at,
       CASE WHEN ev.event_count = 0 THEN 'NO_DATA'
            WHEN NOT EXISTS (SELECT 1 FROM session_states x WHERE x.session_id = s.id) THEN 'NOT_PROJECTED'
            ELSE 'PROJECTED' END AS projection_status,
       ev.event_count,
       ev.trials_recorded, ev.answers_recorded, ev.decisions_recorded,
       (SELECT count(*) FROM trials t WHERE t.session_id = s.id) AS trial_count,
       ans.answered, ans.correct,
       ans.correct::numeric / NULLIF(ans.answered, 0) AS accuracy,
       (SELECT count(*) FROM adaptation_decisions d WHERE d.session_id = s.id) AS decision_count,
       (SELECT count(*) FROM projection_errors p
         WHERE p.session_id = s.id AND p.resolved_at IS NULL) AS open_error_count
FROM experiment_sessions s
CROSS JOIN LATERAL (
    SELECT count(*) AS event_count,
           COALESCE(bool_or(e.event_type = 'TRIAL_STARTED'), false)       AS trials_recorded,
           COALESCE(bool_or(e.event_type = 'ANSWER_SELECTED'), false)     AS answers_recorded,
           COALESCE(bool_or(e.event_type = 'ADAPTATION_DECISION'), false) AS decisions_recorded
    FROM session_events e WHERE e.session_id = s.id) ev
CROSS JOIN LATERAL (
    SELECT count(*) AS answered, count(*) FILTER (WHERE t.is_correct) AS correct
    FROM trials t
    WHERE t.session_id = s.id AND t.answer_event_id IS NOT NULL
      AND t.block_state IN ('S5_STANDARDIZED_LEARNING', 'S6_GUIDED_PRACTICE_CALIBRATION',
                            'S7_EXPERIMENTAL_RETRIEVAL', 'S8_IMMEDIATE_ASSESSMENT')) ans;

-- ---------------------------------------------------------------------
-- v_projection_errors
-- ---------------------------------------------------------------------
-- session_elapsed_ms is NULL when the failed payload has no numeric value there
-- (that can be the very error), so a bad payload never breaks the view.
CREATE VIEW v_projection_errors AS
SELECT p.id, p.session_id, p.event_id, p.event_type, p.error_code, p.detail,
       p.occurred_at, p.resolved_at,
       CASE WHEN jsonb_typeof(e.payload -> 'session_elapsed_ms') = 'number'
            THEN (e.payload ->> 'session_elapsed_ms')::numeric::bigint END AS session_elapsed_ms
FROM projection_errors p
JOIN session_events e ON e.id = p.event_id;

-- ---------------------------------------------------------------------
-- verify_projection_fn -- database/verify_projection.sql, checks 2-4
-- ---------------------------------------------------------------------
-- NULL: every projected session. Unlike the script, check 2 does not expect a row from
-- an event that has a projection error and no row pointing to it (open errors are
-- reported by check 4; resolved ones are known, e.g. the DUPLICATE runs of the F3
-- evidence sessions). An error alone is not enough: re-projection logs errors against
-- events that did project.
CREATE FUNCTION verify_projection_fn(p_session uuid DEFAULT NULL)
RETURNS TABLE (session_id uuid, "check" text, detail text)
LANGUAGE sql STABLE AS $$
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

-- ---------------------------------------------------------------------
-- verify_adaptation_fn -- database/verify_adaptation.sql, checks 2, 3, 4, 7, 8
-- ---------------------------------------------------------------------
-- NULL: every session since 13 Oct, as the script. Sections 1, 5, 6 and 9 are
-- summaries, not checks, and are not ported.
CREATE FUNCTION verify_adaptation_fn(p_session uuid DEFAULT NULL)
RETURNS TABLE (session_id uuid, "check" text, detail text)
LANGUAGE sql STABLE AS $$
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

-- ---------------------------------------------------------------------
-- verify_trials_fn -- database/verify_trials_v1.sql, checks 1-5
-- ---------------------------------------------------------------------
-- NULL: the most recent session, as the script.
CREATE FUNCTION verify_trials_fn(p_session uuid DEFAULT NULL)
RETURNS TABLE (session_id uuid, "check" text, detail text)
LANGUAGE sql STABLE AS $$
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

-- ---------------------------------------------------------------------
-- verify_assembly_fn -- database/verify_assembly_v1.sql, checks 0 and 3
-- ---------------------------------------------------------------------
-- NULL: the most recent session, as the script.
CREATE FUNCTION verify_assembly_fn(p_session uuid DEFAULT NULL)
RETURNS TABLE (session_id uuid, "check" text, detail text)
LANGUAGE sql STABLE AS $$
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

-- ---------------------------------------------------------------------
-- verify_reproducibility_fn -- database/verify_reproducibility_v1.sql, checks 0, 2, 4, 6, 7
-- ---------------------------------------------------------------------
-- NULL: the most recent session with a trial block, as the script. The session is
-- compared with the most recent OTHER session that shares its seed_raw and kanji set;
-- with no such session there is nothing to compare and no row comes back (the script
-- would report every block as seen in 1 session). Pair-level rows carry p_session's id.
CREATE FUNCTION verify_reproducibility_fn(p_session uuid DEFAULT NULL)
RETURNS TABLE (session_id uuid, "check" text, detail text)
LANGUAGE sql STABLE AS $$
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

-- verify_trials_v1.sql -- response system (T1/T2/T3), over the schema v1
-- tables (F3.4). Same checks as verify_trials.sql (which reads the JSONB
-- events); both are kept until Phase 3 closes and must agree.
--
-- Checks the MOST RECENT session, like the other verify_*.sql. The session
-- must be projected: the backend does it live; for an older session run
--   SELECT project_session('<uuid>');
--
-- Usage (PowerShell, repo root):
--   Get-Content database\verify_trials_v1.sql | docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr
--
-- Queries 1-5 are the checks: any row they return is an error. Query 1 comes
-- first on purpose: an event that did not project is a row the other checks
-- cannot see.
--
-- Differences with the JSONB version:
--  * check 2 compares the answer with the plan (is_correct must equal
--    selected = correct) and hint_count with the hint rows. The JSONB version
--    also compares is_correct and response_time_ms between ANSWER_SELECTED
--    and TRIAL_COMPLETED; the table keeps one copy (from the answer), so that
--    comparison stays in verify_trials.sql.
--  * the lal and trial_type of a hint come from its trial, not from the
--    HINT_REQUESTED payload.

\set ON_ERROR_STOP on

CREATE TEMP VIEW s AS
SELECT id FROM experiment_sessions ORDER BY created_at DESC LIMIT 1;

-- 0. Trials of the most recent session
SELECT t.block_state AS state, t.lal, t.trial_type,
       count(*)                     AS started,
       count(t.answer_event_id)     AS answered,
       count(t.completed_event_id)  AS completed,
       (SELECT count(*) FROM hint_requests h
         JOIN trials x ON x.session_id = h.session_id AND x.trial_id = h.trial_id
        WHERE h.session_id = (SELECT id FROM s)
          AND x.block_state = t.block_state AND x.lal = t.lal
          AND x.trial_type = t.trial_type) AS hints
FROM trials t
WHERE t.session_id = (SELECT id FROM s)
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;

-- 1. CHECK: trial events that did not project (ORPHAN_EVENT = answer or
--    close without its start; DUPLICATE = a trial started or closed twice;
--    CHECK_VIOLATION = options not 4, correct or selected option missing)
SELECT event_id, event_type, error_code, detail
FROM projection_errors
WHERE session_id = (SELECT id FROM s) AND resolved_at IS NULL
  AND event_type IN ('TRIAL_STARTED', 'ANSWER_SELECTED', 'TRIAL_COMPLETED',
                     'HINT_REQUESTED', 'TRIAL_SEQUENCE_GENERATED')
ORDER BY event_id;

-- 1b. CHECK: incomplete trials (started, never answered or never closed)
SELECT trial_id, answer_event_id IS NOT NULL AS answered,
       completed_event_id IS NOT NULL AS completed
FROM trials
WHERE session_id = (SELECT id FROM s)
  AND (answer_event_id IS NULL OR completed_event_id IS NULL)
ORDER BY trial_id;

-- 2. CHECK: the trial agrees with itself -- is_correct is selected = correct,
--    and hint_count is the number of HINT_REQUESTED rows of the trial
SELECT t.trial_id, t.selected_option, t.correct_option, t.is_correct,
       t.hint_count, count(h.source_event_id) AS hint_rows
FROM trials t
LEFT JOIN hint_requests h ON h.session_id = t.session_id AND h.trial_id = t.trial_id
WHERE t.session_id = (SELECT id FROM s) AND t.answer_event_id IS NOT NULL
GROUP BY t.session_id, t.trial_id
HAVING bool_or(t.is_correct IS DISTINCT FROM (t.selected_option = t.correct_option))
    OR (bool_or(t.completed_event_id IS NOT NULL)
        AND max(t.hint_count) IS DISTINCT FROM count(h.source_event_id)::smallint)
ORDER BY t.trial_id;

-- 3. CHECK: malformed options (four exactly -- spec 9.3, LAL cannot change
--    the number --, the correct one among them, the chosen one too). The
--    table constraints already refuse these rows (they land in query 1);
--    this keeps the check visible.
SELECT trial_id, cardinality(options) AS n_options,
       NOT (correct_option = ANY (options)) AS correct_missing,
       NOT (selected_option = ANY (options)) AS selected_missing, options
FROM trials
WHERE session_id = (SELECT id FROM s)
  AND (cardinality(options) <> 4
    OR NOT (correct_option = ANY (options))
    OR (selected_option IS NOT NULL AND NOT (selected_option = ANY (options))))
ORDER BY trial_id;

-- 4. CHECK: pre-answer audio in a T3 trial (hard rule, spec 5.2 and 9.2: in
--    Kanji -> Reading the answer IS the reading)
SELECT h.trial_id, t.lal, h.cues_granted
FROM hint_requests h
JOIN trials t ON t.session_id = h.session_id AND t.trial_id = h.trial_id
WHERE h.session_id = (SELECT id FROM s)
  AND t.trial_type = 'T3_KANJI_TO_READING'
  AND 'TARGET_READING_AUDIO' = ANY (h.cues_granted)
ORDER BY 1;

-- 5. CHECK: cues granted against spec table 9.1 (transcribed here, apart
--    from the C# code). Both sides sorted: the order is presentation order.
WITH spec (lal, ttype, expected) AS (VALUES
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
SELECT obs.lal, obs.ttype, obs.granted,
       ARRAY(SELECT c FROM unnest(spec.expected) c ORDER BY c) AS spec_9_1
FROM obs JOIN spec ON spec.lal = obs.lal AND spec.ttype = obs.ttype
WHERE obs.granted <> ARRAY(SELECT c FROM unnest(spec.expected) c ORDER BY c)
ORDER BY 1, 2;

-- 6. Coverage: which cells of the 9.1 matrix were exercised (9 cells, 12
--    with OFF). A cell never tried is not a correct cell.
SELECT t.lal, t.trial_type, count(*) AS hints
FROM hint_requests h
JOIN trials t ON t.session_id = h.session_id AND t.trial_id = h.trial_id
WHERE h.session_id = (SELECT id FROM s)
GROUP BY 1, 2 ORDER BY 1, 2;

-- 7. Summary. Every column but trials and cells_9_1 must be 0.
SELECT
  (SELECT count(*) FROM trials WHERE session_id = (SELECT id FROM s)) AS trials,
  (SELECT count(*) FROM projection_errors
    WHERE session_id = (SELECT id FROM s) AND resolved_at IS NULL)    AS projection_errors,
  (SELECT count(*) FROM trials WHERE session_id = (SELECT id FROM s)
     AND (answer_event_id IS NULL OR completed_event_id IS NULL))     AS incomplete,
  (SELECT count(*) FROM trials WHERE session_id = (SELECT id FROM s)
     AND cardinality(options) <> 4)                                   AS bad_options,
  (SELECT count(*) FROM hint_requests h
     JOIN trials t ON t.session_id = h.session_id AND t.trial_id = h.trial_id
    WHERE h.session_id = (SELECT id FROM s)
      AND t.trial_type = 'T3_KANJI_TO_READING'
      AND 'TARGET_READING_AUDIO' = ANY (h.cues_granted))              AS audio_in_t3,
  (SELECT count(DISTINCT (t.lal, t.trial_type)) FROM hint_requests h
     JOIN trials t ON t.session_id = h.session_id AND t.trial_id = h.trial_id
    WHERE h.session_id = (SELECT id FROM s))                          AS cells_9_1;

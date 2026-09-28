-- verify_reproducibility.sql -- acceptance criterion 7 (Planteamiento_Fase2_M2 §6)
-- Two sessions with the same seed and set must produce the same trial
-- sequences AND the same options in the same order.
--
-- Compares the TWO MOST RECENT sessions that share the seed_raw and kanji set
-- of the most recent session. Create the evidence session with the same
-- random_seed and assigned_kanji_set as an earlier complete run.
--
-- Usage (PowerShell, repo root):
--   Get-Content database\verify_reproducibility.sql | docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr
--
-- Queries 2 and 4 are the checks: any row they return is an error.

\set ON_ERROR_STOP on

CREATE TEMP VIEW seqs AS
SELECT e.session_id, s.created_at,
       e.payload->>'block_state' AS block,
       e.payload->>'seed_raw'    AS seed_raw,
       e.payload->>'kanji_set'   AS kset,
       e.payload->'sequence'     AS seq
FROM session_events e JOIN experiment_sessions s ON s.id = e.session_id
WHERE e.event_type = 'TRIAL_SEQUENCE_GENERATED';

CREATE TEMP VIEW pair AS
WITH latest AS (SELECT seed_raw, kset FROM seqs ORDER BY created_at DESC LIMIT 1)
SELECT session_id, max(created_at) AS created_at
FROM seqs JOIN latest USING (seed_raw, kset)
GROUP BY session_id ORDER BY 2 DESC LIMIT 2;

-- 1. The two sessions being compared
SELECT p.session_id, p.created_at, s.random_seed, s.assigned_kanji_set, s.visit_number
FROM pair p JOIN experiment_sessions s ON s.id = p.session_id ORDER BY p.created_at;

-- 2. CHECK: every block has one identical planned sequence in both sessions
SELECT block, count(DISTINCT session_id) AS sessions, count(DISTINCT seq::text) AS distinct_sequences
FROM seqs WHERE session_id IN (SELECT session_id FROM pair)
GROUP BY block
HAVING count(DISTINCT session_id) <> 2 OR count(DISTINCT seq::text) <> 1;

-- 3. Summary per block (expected: sessions = 2, distinct_sequences = 1)
SELECT block, count(DISTINCT session_id) AS sessions, count(DISTINCT seq::text) AS distinct_sequences
FROM seqs WHERE session_id IN (SELECT session_id FROM pair)
GROUP BY block ORDER BY block;

-- 4. CHECK: the trials actually presented match, options and their order included
WITH started AS (
  SELECT e.session_id, e.payload->>'trial_id' AS trial_id,
         e.payload->>'kanji_id' AS kanji, e.payload->>'trial_type' AS ttype,
         e.payload->'options' AS options
  FROM session_events e
  WHERE e.event_type = 'TRIAL_STARTED' AND e.session_id IN (SELECT session_id FROM pair))
SELECT trial_id, count(DISTINCT session_id) AS sessions,
       count(DISTINCT kanji || '|' || ttype || '|' || options::text) AS distinct_presentations
FROM started GROUP BY trial_id
HAVING count(DISTINCT session_id) <> 2 OR count(DISTINCT kanji || '|' || ttype || '|' || options::text) <> 1
ORDER BY trial_id;

-- 5. How many trials were compared
SELECT count(DISTINCT e.payload->>'trial_id') AS trials_compared
FROM session_events e
WHERE e.event_type = 'TRIAL_STARTED' AND e.session_id IN (SELECT session_id FROM pair);

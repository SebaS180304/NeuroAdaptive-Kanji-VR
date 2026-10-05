-- verify_reproducibility.sql -- acceptance criterion 7 (Planteamiento_Fase2_M2 sec. 6)
-- and Phase 3 criterion 2 (Plan_Fase3 F3.2).
-- Two sessions with the same seed and set must produce the same trial
-- sequences AND the same options in the same order, and (since 2 Oct, F3.2)
-- the same environment: same props and movers per ESL level, same seeds, and
-- the same peripheral events.
--
-- Compares the TWO MOST RECENT sessions that share the seed_raw and kanji set
-- of the most recent session. Create the evidence session with the same
-- random_seed and assigned_kanji_set as an earlier complete run.
--
-- Usage (PowerShell, repo root):
--   Get-Content database\verify_reproducibility.sql | docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr
--
-- Queries 2, 4, 6 and 7 are the checks: any row they return is an error.
-- Query 8 is information: other seeds should give other rooms.
--
-- Since 1 Oct every Play creates its own session (SessionBootstrap): for the
-- evidence, run two Plays with newSessionSeed = 777 (same set) and run this
-- right after the second one.

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

-- ---------------------------------------------------------------------
-- Environment (ESL), F3.2: the seed decides the room, not the run
-- ---------------------------------------------------------------------

CREATE TEMP VIEW env AS
SELECT e.session_id, e.id,
       e.payload->>'esl'            AS esl,
       e.payload->>'profile_name'   AS profile,
       e.payload->>'seed'           AS seed,
       e.payload->>'seed_source'    AS seed_source,
       e.payload->>'selection_seed' AS selection_seed,
       COALESCE(e.payload->'active_props',  '[]'::jsonb) AS props,
       COALESCE(e.payload->'active_movers', '[]'::jsonb) AS movers
FROM session_events e
WHERE e.event_type = 'ENVIRONMENT_APPLIED' AND e.session_id IN (SELECT session_id FROM pair);

-- 6. CHECK: each ESL level gives the same room in both sessions -- same
--    base seed (from the session), same selection seed, same props and
--    movers -- and the seed came from the session, not a fallback.
--    (A level applied several times in one session -- LOW in S1, S2, S5, S9
--    -- must also give the same room every time: selection is per level.)
SELECT esl, count(DISTINCT session_id) AS sessions,
       count(DISTINCT (seed, selection_seed, props::text, movers::text)) AS distinct_rooms,
       string_agg(DISTINCT seed_source, ',') AS seed_sources
FROM env
GROUP BY esl
HAVING count(DISTINCT session_id) <> 2
    OR count(DISTINCT (seed, selection_seed, props::text, movers::text)) <> 1
    OR bool_or(seed_source IS DISTINCT FROM 'SESSION')
ORDER BY esl;

-- 7. CHECK: the peripheral events are the same object for the same time in
--    both sessions, compared by (level application, rank inside it).
--    PeripheralEventScheduler re-seeds its generator on EVERY
--    ENVIRONMENT_APPLIED (seed + level), while event_index runs across the
--    whole session -- so index k is a different draw in two runs whose S6
--    lasted different times. Inside one application the k-th event is always
--    the same draw. Only ranks both sessions reached are compared: how many
--    fire depends on how long each run stayed in MEDIUM/HIGH, not on the seed.
WITH app AS (
  SELECT session_id, id, row_number() OVER (PARTITION BY session_id ORDER BY id) AS app_n
  FROM session_events
  WHERE event_type = 'ENVIRONMENT_APPLIED' AND session_id IN (SELECT session_id FROM pair)),
pe AS (
  SELECT e.session_id,
         (SELECT a.app_n FROM app a WHERE a.session_id = e.session_id AND a.id < e.id
          ORDER BY a.id DESC LIMIT 1) AS app_n,
         e.id, e.payload->>'esl' AS esl,
         e.payload->>'object_name' AS obj, e.payload->>'duration_ms' AS dur
  FROM session_events e
  WHERE e.event_type = 'PERIPHERAL_EVENT' AND e.session_id IN (SELECT session_id FROM pair)),
ranked AS (
  SELECT pe.*, row_number() OVER (PARTITION BY session_id, app_n ORDER BY id) AS k FROM pe)
SELECT app_n AS application, k AS rank_in_application,
       string_agg(DISTINCT esl, ',') AS esl,
       count(DISTINCT session_id) AS sessions, count(DISTINCT (obj, dur)) AS distinct_events,
       string_agg(DISTINCT obj, ',') AS objects
FROM ranked
GROUP BY app_n, k
HAVING count(DISTINCT session_id) = 2
   AND (count(DISTINCT (obj, dur)) <> 1 OR count(DISTINCT esl) <> 1)
ORDER BY app_n, k;

-- 7b. What was compared (levels and peripheral events per session)
SELECT session_id,
       string_agg(DISTINCT esl, ',' ORDER BY esl) AS levels,
       (SELECT count(*) FROM session_events p
         WHERE p.session_id = env.session_id AND p.event_type = 'PERIPHERAL_EVENT') AS peripheral_events
FROM env GROUP BY session_id;

-- 8. Information: the room per level of the latest session of EACH seed.
--    Different seeds should give different rooms in MEDIUM and HIGH (LOW
--    picks 2-3 of 3 T1 props, so equal LOW rooms across seeds are normal).
WITH last_per_seed AS (
  SELECT DISTINCT ON (s.random_seed) s.id, s.random_seed
  FROM experiment_sessions s
  WHERE s.random_seed IS NOT NULL
    AND EXISTS (SELECT 1 FROM session_events e
                WHERE e.session_id = s.id AND e.event_type = 'ENVIRONMENT_APPLIED'
                  AND e.payload->>'seed_source' = 'SESSION')
  ORDER BY s.random_seed, s.created_at DESC)
SELECT e.payload->>'esl' AS esl,
       count(DISTINCT l.random_seed) AS seeds,
       count(DISTINCT (e.payload->'active_props')::text || (e.payload->'active_movers')::text) AS distinct_rooms
FROM last_per_seed l JOIN session_events e ON e.session_id = l.id
WHERE e.event_type = 'ENVIRONMENT_APPLIED'
GROUP BY 1 ORDER BY 1;

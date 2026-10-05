-- verify_reproducibility_v1.sql -- acceptance criterion 7 (Planteamiento_Fase2_M2
-- sec. 6) and Phase 3 criterion 2 (Plan_Fase3 F3.2), over the schema v1
-- tables (F3.4). Same checks as verify_reproducibility.sql (JSONB events);
-- both are kept until Phase 3 closes and must agree.
--
-- Two sessions with the same seed and set must produce the same trial
-- sequences, the same options in the same order, the same room per ESL
-- level (props, movers, seeds) and the same peripheral events.
--
-- Compares the TWO MOST RECENT sessions that share the seed_raw and kanji set
-- of the most recent session. Both must be projected (live in the backend,
-- or SELECT project_session('<uuid>')).
--
-- Usage (PowerShell, repo root):
--   Get-Content database\verify_reproducibility_v1.sql | docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr
--
-- Queries 0, 2, 4, 6 and 7 are the checks: any row they return is an error.
-- Query 8 is information: other seeds should give other rooms.
--
-- Since 1 Oct every Play creates its own session (SessionBootstrap): for the
-- evidence, run two Plays with newSessionSeed = 777 (same set) and run this
-- right after the second one.

\set ON_ERROR_STOP on

-- A block's plan as one comparable text: entry by entry, in order
CREATE TEMP VIEW seqs AS
SELECT b.session_id, s.created_at, b.block_state::text AS block,
       b.seed_raw, b.kanji_set AS kset,
       (SELECT string_agg(p.trial_sequence || ':' || p.trial_id || ':' || p.kanji_id || ':'
                          || p.trial_type || ':' || p.correct_option || ':'
                          || array_to_string(p.options, ','), ' | ' ORDER BY p.trial_sequence)
        FROM planned_trials p
        WHERE p.session_id = b.session_id AND p.block_state = b.block_state) AS seq
FROM trial_blocks b JOIN experiment_sessions s ON s.id = b.session_id;

CREATE TEMP VIEW pair AS
WITH latest AS (SELECT seed_raw, kset FROM seqs ORDER BY created_at DESC LIMIT 1)
SELECT session_id, max(created_at) AS created_at
FROM seqs JOIN latest USING (seed_raw, kset)
GROUP BY session_id ORDER BY 2 DESC LIMIT 2;

-- 0. CHECK: events of the pair that did not project (a missing row would
--    look like a difference, or hide one)
SELECT session_id, event_id, event_type, error_code, detail
FROM projection_errors
WHERE resolved_at IS NULL AND session_id IN (SELECT session_id FROM pair)
ORDER BY session_id, event_id;

-- 1. The two sessions being compared
SELECT p.session_id, p.created_at, s.random_seed, s.assigned_kanji_set, s.visit_number
FROM pair p JOIN experiment_sessions s ON s.id = p.session_id ORDER BY p.created_at;

-- 2. CHECK: every block has one identical planned sequence in both sessions
SELECT block, count(DISTINCT session_id) AS sessions, count(DISTINCT seq) AS distinct_sequences
FROM seqs WHERE session_id IN (SELECT session_id FROM pair)
GROUP BY block
HAVING count(DISTINCT session_id) <> 2 OR count(DISTINCT seq) <> 1;

-- 3. Summary per block (expected: sessions = 2, distinct_sequences = 1)
SELECT block, count(DISTINCT session_id) AS sessions, count(DISTINCT seq) AS distinct_sequences
FROM seqs WHERE session_id IN (SELECT session_id FROM pair)
GROUP BY block ORDER BY block;

-- 4. CHECK: the trials actually presented match, options and their order included
SELECT trial_id, count(DISTINCT session_id) AS sessions,
       count(DISTINCT (kanji_id, trial_type, options)) AS distinct_presentations
FROM trials WHERE session_id IN (SELECT session_id FROM pair)
GROUP BY trial_id
HAVING count(DISTINCT session_id) <> 2 OR count(DISTINCT (kanji_id, trial_type, options)) <> 1
ORDER BY trial_id;

-- 5. How many trials were compared
SELECT count(DISTINCT trial_id) AS trials_compared
FROM trials WHERE session_id IN (SELECT session_id FROM pair);

-- ---------------------------------------------------------------------
-- Environment (ESL), F3.2: the seed decides the room, not the run
-- ---------------------------------------------------------------------

-- 6. CHECK: each ESL level gives the same room in both sessions -- same
--    base seed, same selection seed, same props and movers -- and the seed
--    came from the session. (LOW, applied in several states, must give the
--    same room every time: selection is per level.)
SELECT esl, count(DISTINCT session_id) AS sessions,
       count(DISTINCT (seed, selection_seed,
                       COALESCE(active_props, '{}'), COALESCE(active_movers, '{}'))) AS distinct_rooms,
       string_agg(DISTINCT seed_source, ',') AS seed_sources
FROM environment_applications
WHERE session_id IN (SELECT session_id FROM pair)
GROUP BY esl
HAVING count(DISTINCT session_id) <> 2
    OR count(DISTINCT (seed, selection_seed,
                       COALESCE(active_props, '{}'), COALESCE(active_movers, '{}'))) <> 1
    OR bool_or(seed_source IS DISTINCT FROM 'SESSION')
ORDER BY esl;

-- 7. CHECK: peripheral events are the same object for the same time in both
--    sessions, compared by (level application, rank inside it).
--    PeripheralEventScheduler re-seeds its generator on EVERY
--    ENVIRONMENT_APPLIED (seed + level), while event_index runs across the
--    whole session -- so index k is a different draw in two runs whose S6
--    lasted different times. Inside one application the k-th event is always
--    the same draw. Only ranks both sessions reached are compared.
WITH app AS (
  SELECT session_id, source_event_id,
         row_number() OVER (PARTITION BY session_id ORDER BY source_event_id) AS app_n
  FROM environment_applications
  WHERE session_id IN (SELECT session_id FROM pair)),
pe AS (
  SELECT p.session_id, p.source_event_id, p.esl, p.object_name, p.duration_ms,
         (SELECT a.app_n FROM app a
          WHERE a.session_id = p.session_id AND a.source_event_id < p.source_event_id
          ORDER BY a.source_event_id DESC LIMIT 1) AS app_n
  FROM peripheral_events p
  WHERE p.session_id IN (SELECT session_id FROM pair)),
ranked AS (
  SELECT pe.*, row_number() OVER (PARTITION BY session_id, app_n ORDER BY source_event_id) AS k
  FROM pe)
SELECT app_n AS application, k AS rank_in_application,
       string_agg(DISTINCT esl::text, ',') AS esl,
       count(DISTINCT session_id) AS sessions,
       count(DISTINCT (object_name, duration_ms)) AS distinct_events,
       string_agg(DISTINCT object_name, ',') AS objects
FROM ranked
GROUP BY app_n, k
HAVING count(DISTINCT session_id) = 2
   AND (count(DISTINCT (object_name, duration_ms)) <> 1 OR count(DISTINCT esl) <> 1)
ORDER BY app_n, k;

-- 7b. What was compared (levels and peripheral events per session)
SELECT p.session_id,
       (SELECT string_agg(DISTINCT a.esl::text, ',' ORDER BY a.esl::text)
          FROM environment_applications a WHERE a.session_id = p.session_id) AS levels,
       (SELECT count(*) FROM peripheral_events x WHERE x.session_id = p.session_id) AS peripheral_events
FROM pair p ORDER BY p.created_at;

-- 8. Information: the room per level of the latest session of EACH seed.
--    Different seeds should give different rooms in MEDIUM and HIGH (LOW
--    picks 2-3 of 3 T1 props, so equal LOW rooms across seeds are normal).
WITH last_per_seed AS (
  SELECT DISTINCT ON (s.random_seed) s.id, s.random_seed
  FROM experiment_sessions s
  WHERE s.random_seed IS NOT NULL
    AND EXISTS (SELECT 1 FROM environment_applications a
                WHERE a.session_id = s.id AND a.seed_source = 'SESSION')
  ORDER BY s.random_seed, s.created_at DESC)
SELECT a.esl, count(DISTINCT l.random_seed) AS seeds,
       count(DISTINCT (COALESCE(a.active_props, '{}'), COALESCE(a.active_movers, '{}'))) AS distinct_rooms
FROM last_per_seed l JOIN environment_applications a ON a.session_id = l.id
GROUP BY 1 ORDER BY 1;

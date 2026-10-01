-- backfill_projection.sql -- schema v1 (F3.4), MER_Schema_v1.md sec. 6
-- Projects existing sessions into the schema v1 tables with the same code
-- the backend runs live (project_session -> project_event, PL/pgSQL).
-- Idempotent: running it again rebuilds the same rows.
--
-- Requires: alembic upgrade head (migration 0002) and the kanji catalogue:
--   Get-Content database\seed_kanji_items.sql | docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr
--
-- Usage (PowerShell, repo root):
--   Get-Content database\backfill_projection.sql | docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr
-- then:
--   Get-Content database\verify_projection.sql | docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr
--
-- WHICH SESSIONS. Sessions before 7 Sep write `state` with the C# spelling
-- (S1_WelcomeOrientation) and are not projected (MER sec. 7). The default list is
-- the two M2 evidence sessions plus every session created since the M2
-- delivery (28 Sep). Edit `targets` to add or remove sessions.
--
-- Note: a development session reused across Editor runs
-- (SessionBootstrap.existingSessionId) holds several runs under one id, so
-- from the second run on its trials, blocks and head-away episodes repeat and
-- end in projection_errors as DUPLICATE. The first run is projected; the
-- events are all still in session_events.

\set ON_ERROR_STOP on

CREATE TEMP VIEW targets AS
SELECT s.id, s.created_at
FROM experiment_sessions s
WHERE s.id::text LIKE 'b62330de%'          -- M2 evidence
   OR s.id::text LIKE 'b4f53dbd%'          -- M2 evidence
   OR s.created_at >= TIMESTAMPTZ '2026-09-28 00:00+09';

-- One row per session: how many events it has and how many failed to project
SELECT t.id AS session_id, t.created_at,
       (SELECT count(*) FROM session_events e WHERE e.session_id = t.id) AS events,
       project_session(t.id) AS failed
FROM targets t
ORDER BY t.created_at;

-- Errors left open, grouped (details: SELECT * FROM projection_errors WHERE resolved_at IS NULL)
SELECT session_id, event_type, error_code, count(*) AS n, min(detail) AS example
FROM projection_errors
WHERE resolved_at IS NULL AND session_id IN (SELECT id FROM targets)
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;

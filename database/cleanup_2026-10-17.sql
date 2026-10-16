-- cleanup_2026-10-17.sql -- one-off data clean-up before the research portal
-- (tasks/plan.md, Task 0.1; approved by Sebas on 17 Oct 2026).
--
-- 1. Deletes the sessions created before the Japanese Learning Studio scene
--    existed (commit 267d48a, 2026-09-15 12:32:36 +09:00). On 17 Oct these are
--    23 sessions, all CREATED, 323 events; no project document cites them.
--    Every table that references experiment_sessions is ON DELETE CASCADE.
-- 2. Deletes participants left with no sessions, no pre-test answers and no
--    consent (DEV_UNITY is kept: Unity's dev Play reuses it).
-- 3. Resolves the open DUPLICATE errors of the three F3 evidence sessions. They
--    are kept (Evidencia_Criterios_F3.md, Plan_Fase3.md): several Editor runs were
--    stored under one id, the first run is projected and the root cause was fixed.
--
-- Back up first (database/backups/ is gitignored):
--   docker compose exec -T db pg_dump -U neuroadaptive -Fc neuroadaptive_vr > database\backups\pre_cleanup_2026-10-17.dump
-- Dry run (prints the counts, then rolls back):
--   Get-Content database\cleanup_2026-10-17.sql | docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr -v dry_run=1
-- Real run: the same command without -v dry_run=1.

\set ON_ERROR_STOP on
\set cutoff '''2026-09-15 12:32:36+09'''

BEGIN;

\echo '== Before'
SELECT (SELECT count(*) FROM experiment_sessions) AS sessions,
       (SELECT count(*) FROM session_events) AS events,
       (SELECT count(*) FROM participants) AS participants,
       (SELECT count(*) FROM projection_errors WHERE resolved_at IS NULL) AS open_errors;

\echo '== 1. Sessions created before the scene (to delete)'
SELECT left(s.id::text, 8) AS session, s.created_at::date AS created, s.status, p.external_code,
       (SELECT count(*) FROM session_events e WHERE e.session_id = s.id) AS events
FROM experiment_sessions s JOIN participants p ON p.id = s.participant_id
WHERE s.created_at < :cutoff
ORDER BY s.created_at;

DELETE FROM experiment_sessions WHERE created_at < :cutoff;

\echo '== 2. Participants with no sessions, no pre-test answers and no consent (to delete)'
SELECT external_code, created_at::date AS created
FROM participants p
WHERE NOT EXISTS (SELECT 1 FROM experiment_sessions s WHERE s.participant_id = p.id)
  AND NOT EXISTS (SELECT 1 FROM kanji_pretest_responses r WHERE r.participant_id = p.id)
  AND NOT p.consent_obtained
  AND p.external_code <> 'DEV_UNITY'
ORDER BY created_at;

DELETE FROM participants p
WHERE NOT EXISTS (SELECT 1 FROM experiment_sessions s WHERE s.participant_id = p.id)
  AND NOT EXISTS (SELECT 1 FROM kanji_pretest_responses r WHERE r.participant_id = p.id)
  AND NOT p.consent_obtained
  AND p.external_code <> 'DEV_UNITY';

\echo '== 3. DUPLICATE errors of the F3 evidence sessions (to resolve)'
UPDATE projection_errors
SET resolved_at = now(),
    detail = coalesce(detail, '') || ' | resolved 2026-10-17: several Editor runs under one id; '
             || 'first run projected; root cause fixed (Plan_Fase3.md)'
WHERE resolved_at IS NULL
  AND error_code = 'DUPLICATE'
  AND session_id IN ('dc28e1ea-9a07-4aa6-a1f7-05b37c338b12',
                     'fc835228-d993-427a-a3cd-7a290d4af5e6',
                     'd3f19117-516a-47b4-8df2-7a88a695e688');

\echo '== After'
SELECT (SELECT count(*) FROM experiment_sessions) AS sessions,
       (SELECT count(*) FROM session_events) AS events,
       (SELECT count(*) FROM participants) AS participants,
       (SELECT count(*) FROM projection_errors WHERE resolved_at IS NULL) AS open_errors,
       (SELECT count(*) FROM experiment_sessions WHERE created_at < :cutoff) AS sessions_before_scene;

\if :{?dry_run}
\echo '== DRY RUN: rolling back, nothing was changed'
ROLLBACK;
\else
COMMIT;
\endif

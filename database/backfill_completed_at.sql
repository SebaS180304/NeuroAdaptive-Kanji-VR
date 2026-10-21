-- backfill_completed_at.sql -- experiment_sessions.completed_at for sessions completed
-- before 21 Oct 2026 (commit 648662c), when S9 started filling it. Sebas, 21 Oct.
-- The value is what the live rule would have written: the first time the session
-- reached S9 (or S10 if S9 was skipped), from its STATE_ENTERED event. A session
-- reused across Editor runs (several S9 entries, e.g. dc28e1ea) gets the first one.
-- Idempotent: only COMPLETED sessions with completed_at NULL and an S9/S10 event.
-- Nothing reads completed_at for the Learner Profile (it filters by status).
--
-- Usage (PowerShell, repo root):
--   Get-Content database\backfill_completed_at.sql | docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr

UPDATE experiment_sessions s
SET completed_at = f.first_at
FROM (
    SELECT e.session_id, min(e.server_received_at) AS first_at
    FROM session_events e
    WHERE e.event_type = 'STATE_ENTERED'
      AND e.payload->>'state' IN ('S9_SESSION_SUMMARY', 'S10_HCI_SELF_REPORT')
    GROUP BY e.session_id
) f
WHERE f.session_id = s.id AND s.status = 'COMPLETED' AND s.completed_at IS NULL;

-- Expected: 0 rows (every COMPLETED session has completed_at).
SELECT s.id, s.created_at FROM experiment_sessions s
WHERE s.status = 'COMPLETED' AND s.completed_at IS NULL;

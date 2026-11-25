-- NeuroAdaptive VR -- abandoned sessions -- migration 0005 (up)
-- An IN_PROGRESS session whose last event (or, with no events, its last update)
-- is older than p_idle is set to ABORTED. Returns how many sessions changed.
-- The backend runs it at startup and every 5 minutes (app/services/stale_sessions.py).
-- 30 minutes by default: the longest gap between two events in a normal completed
-- session was 1.8 min on 17 Oct (tasks/plan.md). PATCH /sessions/{id}/state never
-- takes a session out of ABORTED, so a late event does not revert it.

CREATE FUNCTION abort_stale_sessions(p_idle interval DEFAULT interval '30 minutes')
RETURNS integer LANGUAGE sql AS $$
    WITH aborted AS (
        UPDATE experiment_sessions s
        SET status = 'ABORTED', updated_at = now()
        WHERE s.status = 'IN_PROGRESS'
          AND COALESCE((SELECT max(e.server_received_at) FROM session_events e
                        WHERE e.session_id = s.id), s.updated_at) < now() - p_idle
        RETURNING 1)
    SELECT count(*)::int FROM aborted;
$$;

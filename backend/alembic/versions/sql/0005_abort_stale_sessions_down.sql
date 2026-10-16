-- NeuroAdaptive VR -- abandoned sessions -- migration 0005 (down)
-- Sessions already set to ABORTED stay ABORTED.
DROP FUNCTION IF EXISTS abort_stale_sessions(interval);

-- =====================================================================
-- NeuroAdaptive VR -- schema v1 (Phase 3, F3.4) -- migration 0002 (down)
-- =====================================================================
-- Drops everything 0002 created. session_events (the source of truth) is
-- untouched, so nothing is lost: upgrading again and running
-- project_session() rebuilds every projected row.
-- =====================================================================

DROP FUNCTION IF EXISTS trial_timeline(UUID, INT);
DROP VIEW IF EXISTS v_trial_behavior;
DROP VIEW IF EXISTS v_environment_intervals;

DROP FUNCTION IF EXISTS project_session(UUID);
DROP FUNCTION IF EXISTS project_event(BIGINT);
DROP FUNCTION IF EXISTS proj_apply(session_events);
DROP FUNCTION IF EXISTS proj_orphan_or_dup(session_events, TEXT);
DROP FUNCTION IF EXISTS proj_int_arr(JSONB, TEXT);
DROP FUNCTION IF EXISTS proj_arr(JSONB, TEXT);
DROP FUNCTION IF EXISTS proj_req(JSONB, TEXT);

DROP TABLE IF EXISTS projection_errors;
DROP TABLE IF EXISTS assembly_attempts;
DROP TABLE IF EXISTS assemblies;
DROP TABLE IF EXISTS kanji_exposures;
DROP TABLE IF EXISTS head_away_episodes;
DROP TABLE IF EXISTS peripheral_events;
DROP TABLE IF EXISTS environment_applications;
DROP TABLE IF EXISTS hint_requests;
DROP TABLE IF EXISTS trials;
DROP TABLE IF EXISTS planned_trials;
DROP TABLE IF EXISTS trial_blocks;
DROP TABLE IF EXISTS session_states;
DROP TABLE IF EXISTS kanji_items;

DROP INDEX IF EXISTS ix_session_events_session_trial;

DROP TYPE IF EXISTS kanji_role;
DROP TYPE IF EXISTS stimulation_level;
DROP TYPE IF EXISTS trial_type;

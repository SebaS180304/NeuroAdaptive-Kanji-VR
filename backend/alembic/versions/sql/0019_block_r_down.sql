-- NeuroAdaptive VR -- block R, delayed retention -- migration 0019 (down)
-- The value SR_DELAYED_RETENTION stays in game_flow_state: PostgreSQL cannot drop an enum value, and rows of
-- block R (if any) would still use it.
ALTER TABLE experiment_sessions DROP COLUMN evaluated_session_id;

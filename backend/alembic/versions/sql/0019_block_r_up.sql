-- NeuroAdaptive VR -- block R, delayed retention -- migration 0019 (up)
-- D-F6-125: block R is its own state between S2 and S3 (trials SR-001..SR-015, projected like any block).
-- D-F6-190 (2), D-F6-223: a session of visit >= 2 stores the session it evaluates; its set comes from there.
ALTER TYPE game_flow_state ADD VALUE IF NOT EXISTS 'SR_DELAYED_RETENTION' AFTER 'S2_VR_TUTORIAL';
ALTER TABLE experiment_sessions
    ADD COLUMN evaluated_session_id UUID REFERENCES experiment_sessions(id) ON DELETE SET NULL;

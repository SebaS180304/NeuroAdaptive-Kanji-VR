-- NeuroAdaptive VR -- the monitor's 8-channel traces -- migration 0024 (up)
-- TR (D-F6-293 (5), D-F6-297 (3), D-F6-301 (5)): live.py writes min/max per 40 ms bin of the causally filtered signal
-- every 0.25 s, only with EEG_MONITOR_TRACES on, and prunes them to the last 30 s of each session. Display only: no
-- rule, window or analysis reads this table. t_ms = session ms on the markers' clock (S3 offset applied).
CREATE TABLE eeg_trace_bins (
    session_id UUID NOT NULL REFERENCES eeg_sessions(session_id) ON DELETE CASCADE,
    t_ms INTEGER NOT NULL,
    mins REAL[] NOT NULL,
    maxs REAL[] NOT NULL,
    PRIMARY KEY (session_id, t_ms)
);
-- «Now» beside each lane (D-F6-297 (2)): {"rms_uv": [8 values, µV RMS of the last second, null = no data], "t_ms"}.
ALTER TABLE eeg_sessions ADD COLUMN traces_now JSONB, ADD COLUMN traces_at TIMESTAMPTZ;
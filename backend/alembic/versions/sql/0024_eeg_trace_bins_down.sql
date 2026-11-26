-- NeuroAdaptive VR -- the monitor's 8-channel traces -- migration 0024 (down)
ALTER TABLE eeg_sessions DROP COLUMN traces_at, DROP COLUMN traces_now;
DROP TABLE eeg_trace_bins;

-- NeuroAdaptive VR -- the live monitor's per-channel figures -- migration 0021 (down)
ALTER TABLE eeg_sessions DROP COLUMN monitor, DROP COLUMN monitor_at;

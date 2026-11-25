-- NeuroAdaptive VR -- the live EEG process's heartbeat -- migration 0016 (down)
ALTER TABLE eeg_sessions DROP COLUMN heartbeat_at, DROP COLUMN eeg_gap_ms;

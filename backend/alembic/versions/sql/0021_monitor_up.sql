-- NeuroAdaptive VR -- the live monitor's per-channel figures -- migration 0021 (up)
-- M1b (D-F6-254, D-F6-265): live.py writes app.eeg.monitor.compute()'s result every 2.5 s when EEG_MONITOR_LIVE is on;
-- the portal's /monitor reads it. Null = off, or a session before this. No rule of the engine reads it.
ALTER TABLE eeg_sessions ADD COLUMN monitor JSONB, ADD COLUMN monitor_at TIMESTAMPTZ;

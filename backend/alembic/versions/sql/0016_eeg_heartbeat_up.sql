-- NeuroAdaptive VR -- the live EEG process's heartbeat -- migration 0016 (up)
-- D-F6-171: live.py writes, every 2 s, when it last ran and how long ago its last EEG sample arrived, so the
-- backend can tell "no valid epochs" (fresh heartbeat) from "process down" (stale heartbeat, X3).
ALTER TABLE eeg_sessions
    ADD COLUMN heartbeat_at TIMESTAMPTZ,
    ADD COLUMN eeg_gap_ms   INTEGER;

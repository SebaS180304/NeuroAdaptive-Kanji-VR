-- NeuroAdaptive VR -- F4 S2 -- migration 0012 (up)
-- How sync_offset_ms and sync_drift_ms were found (D-F6-157, D-F6-159): every SYNC_TAP with its Cz peak
-- and lag, the clear-peak rule used (±500 ms, > 5× the MAD of the 2 s before) and, when a column stays
-- empty, the reason. Written by app/eeg/sync.py.
ALTER TABLE eeg_sessions ADD COLUMN sync_detail JSONB;

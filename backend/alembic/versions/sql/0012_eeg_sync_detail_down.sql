-- NeuroAdaptive VR -- F4 S2 -- migration 0012 (down)
ALTER TABLE eeg_sessions DROP COLUMN IF EXISTS sync_detail;

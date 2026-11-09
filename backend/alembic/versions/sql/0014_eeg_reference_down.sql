-- NeuroAdaptive VR -- F4 S3 -- migration 0014 (down)
ALTER TABLE eeg_sessions DROP COLUMN IF EXISTS reference;

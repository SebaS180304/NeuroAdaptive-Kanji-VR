-- NeuroAdaptive VR -- F4 S3 -- migration 0014 (up)
-- D-F6-73: source (S6, or S4 with the eyes open, marked), and mean and SD of ln(index) per index.
ALTER TABLE eeg_sessions ADD COLUMN reference JSONB;

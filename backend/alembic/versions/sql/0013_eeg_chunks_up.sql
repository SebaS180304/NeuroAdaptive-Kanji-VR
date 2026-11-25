-- NeuroAdaptive VR -- F4 S3 -- migration 0013 (up)
-- D-F6-163: 9 chunks per epoch. Rows of sessions not recomputed keep their 5 and stay valid (D-F6-156).
ALTER TABLE eeg_epochs
    DROP CONSTRAINT eeg_epochs_chunk_clean_check,
    ADD CONSTRAINT eeg_epochs_chunk_clean_check CHECK (cardinality(chunk_clean) IN (5, 9));

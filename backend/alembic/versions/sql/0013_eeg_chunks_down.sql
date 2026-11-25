-- NeuroAdaptive VR -- F4 S3 -- migration 0013 (down)
-- NOT VALID: epochs already computed with 9 chunks stay; only new rows are held to 5.
ALTER TABLE eeg_epochs
    DROP CONSTRAINT eeg_epochs_chunk_clean_check,
    ADD CONSTRAINT eeg_epochs_chunk_clean_check CHECK (cardinality(chunk_clean) = 5) NOT VALID;

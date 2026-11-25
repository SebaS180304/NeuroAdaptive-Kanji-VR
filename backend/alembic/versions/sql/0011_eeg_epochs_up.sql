-- NeuroAdaptive VR -- F4 S2 -- migration 0011 (up)
-- The 5 s epochs (every 2.5 s) of a session with EEG and their quality
-- (Planteamiento_Tecnico_F4.md §2.3; app/eeg/epochs.py). Written after the session from the XDF.
-- The five 1 s chunks are kept, not only the fraction: P7 (D-F6-127) counts every clean
-- second once even when two overlapping epochs share it.

CREATE TABLE eeg_epochs (
    session_id       UUID        NOT NULL REFERENCES eeg_sessions(session_id) ON DELETE CASCADE,
    epoch_index      INTEGER     NOT NULL,
    -- Start on LSL's corrected clock (the XDF's), and start/end on the session clock
    -- (null when the XDF has no UnityMarkers to map one to the other).
    lsl_start        DOUBLE PRECISION NOT NULL,
    start_ms         INTEGER,
    end_ms           INTEGER,
    -- Context at the epoch's midpoint, from the markers.
    game_state       TEXT,
    trial_id         TEXT,
    esl_level        TEXT,
    chunk_clean      BOOLEAN[]   NOT NULL CHECK (cardinality(chunk_clean) = 5),
    clean_fraction   REAL        NOT NULL,
    quality          TEXT        NOT NULL CHECK (quality IN ('GOOD', 'ACCEPTABLE', 'POOR')),
    -- Indices per epoch: empty until features.py (S3 week, F4 §5).
    engagement_index REAL,
    theta_fz         REAL,
    alpha_parietal   REAL,
    theta_beta       REAL,
    PRIMARY KEY (session_id, epoch_index)
);

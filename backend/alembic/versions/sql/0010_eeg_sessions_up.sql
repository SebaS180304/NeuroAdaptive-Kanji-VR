-- NeuroAdaptive VR -- F4 S2 -- migration 0010 (up)
-- One row per session recorded with the AURA cap (Planteamiento_Tecnico_F4.md §2.3).
-- The raw signal stays in the XDF (one per session, both streams: AURA and UnityMarkers,
-- D-F6-127 P9); this row points at it and keeps what the XDF cannot: the montage (AURA
-- sends no channel labels), the S3 sync result and the S4 alpha ratio.

CREATE TABLE eeg_sessions (
    session_id         UUID        PRIMARY KEY REFERENCES experiment_sessions(id) ON DELETE CASCADE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    xdf_path           TEXT,
    -- Per stream: name, type, channel count, nominal rate, units (lsl_reader.py).
    stream_info        JSONB       NOT NULL DEFAULT '{}',
    filter_params      JSONB       NOT NULL DEFAULT '{}',
    -- Fixed montage of D-F6-72, confirmed on 29 Oct; a change of the day goes here
    -- with its reason (D-F6-75).
    montage            JSONB       NOT NULL DEFAULT
        '{"CH1": "Fp1", "CH2": "F3", "CH3": "Fz", "CH4": "F4", "CH5": "Cz", "CH6": "P3", "CH7": "Pz", "CH8": "P4"}',
    montage_change     TEXT,
    -- S3 sync test (F4 §2.4): required |offset| <= 100 ms and drift < 50 ms.
    sync_offset_ms     REAL,
    sync_drift_ms      REAL,
    -- S4 eyes closed / open, per parietal channel, and whether it passed (>= 1.2).
    alpha_ratio        JSONB,
    alpha_passed       BOOLEAN,
    -- Why the EEG does not count in this session, if it does not.
    not_counted_reason TEXT
);

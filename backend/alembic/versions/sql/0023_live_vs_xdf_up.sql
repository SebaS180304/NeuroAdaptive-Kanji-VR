-- NeuroAdaptive VR -- live cut against XDF cut -- migration 0023 (up)
-- V (D-F6-281 (2)): after fill_from_xdf replaces the live rows, autorun compares them (live_epochs.csv, saved before
-- the Stop) with the XDF ones: {live, xdf, common, differ, differ_pct, only_live, only_xdf}. verify_eeg.sql shows it
-- beside the two A-7 figures. Official = what the engine saw live; per-epoch indices for analysis = the XDF cut.
-- Null = not compared (sessions before this, or no live_epochs.csv).
ALTER TABLE eeg_sessions ADD COLUMN live_vs_xdf JSONB;

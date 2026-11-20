-- NeuroAdaptive VR -- option (3) live -- migration 0022 (up)
-- I2 (D-F6-275, D-F6-276): with EEG_LIVE_RULE=ica, live.py writes the ICA fitted at S6's entry (matrices, component,
-- corr, channels, fit seconds) or why there is none (reason), and when a channel out after S6 switched the session to
-- option (2) (switched_to_nosound_at, switch_reason). fill_from_xdf reuses it without refitting. Null = another rule.
ALTER TABLE eeg_sessions ADD COLUMN ica JSONB;

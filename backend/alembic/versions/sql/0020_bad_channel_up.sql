-- NeuroAdaptive VR -- the persistently bad channel -- migration 0020 (up)
-- D-F6-216, D-F6-224: a channel with > 20 % of its samples over 100 uV in 2 consecutive 30 s bins leaves the
-- amplitude check and the indices to the end of the session. eeg_sessions keeps which ("F3", or "F3,Pz" when a 2nd
-- one went out and the EEG stopped counting) and the session time it left from; each epoch keeps the channels out
-- in it. Null = none (every session before this).
ALTER TABLE eeg_sessions ADD COLUMN bad_channel TEXT, ADD COLUMN bad_channel_from_ms INTEGER;
ALTER TABLE eeg_epochs ADD COLUMN excluded_channels TEXT;

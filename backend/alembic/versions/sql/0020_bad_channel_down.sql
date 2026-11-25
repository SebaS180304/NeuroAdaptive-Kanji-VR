-- NeuroAdaptive VR -- the persistently bad channel -- migration 0020 (down)
ALTER TABLE eeg_epochs DROP COLUMN excluded_channels;
ALTER TABLE eeg_sessions DROP COLUMN bad_channel, DROP COLUMN bad_channel_from_ms;

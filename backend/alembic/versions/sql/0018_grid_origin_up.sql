-- NeuroAdaptive VR -- one epoch grid for live and offline -- migration 0018 (up)
-- D-F6-200 (1): live.py stores the origin of its epoch grid (the first S3-corrected stamp) once; fill_from_xdf and
-- replay --xdf cut on it, so offline epochs keep the live index and start. Null = sessions before this: the grid
-- starts at the XDF's first stamp, as before.
ALTER TABLE eeg_sessions ADD COLUMN grid_origin_lsl DOUBLE PRECISION;

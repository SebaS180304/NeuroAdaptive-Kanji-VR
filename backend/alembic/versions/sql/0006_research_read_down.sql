-- NeuroAdaptive VR -- research portal, read side -- migration 0006 (down)
DROP FUNCTION IF EXISTS verify_reproducibility_fn(uuid);
DROP FUNCTION IF EXISTS verify_assembly_fn(uuid);
DROP FUNCTION IF EXISTS verify_trials_fn(uuid);
DROP FUNCTION IF EXISTS verify_adaptation_fn(uuid);
DROP FUNCTION IF EXISTS verify_projection_fn(uuid);
DROP VIEW IF EXISTS v_projection_errors;
DROP VIEW IF EXISTS v_session_overview;

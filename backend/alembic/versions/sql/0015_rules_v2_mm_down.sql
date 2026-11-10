-- NeuroAdaptive VR -- rules-v2-mm: the EEG of each decision -- migration 0015 (down)
-- proj_apply back to its 0003 insert, then the columns go. The payloads keep the eeg block: 0015 up re-projects it.

DO $$
DECLARE
    def TEXT := pg_get_functiondef('proj_apply(session_events)'::regprocedure);
    patched TEXT;
BEGIN
    patched := replace(def,
        $b$estimator_version, rules_version, evidence, indicators, thresholds,
            eeg_counted, eeg_ei_z, eeg_theta_z, eeg_effect)$b$,
        $a$estimator_version, rules_version, evidence, indicators, thresholds)$a$);
    patched := replace(patched,
        $b$proj_arr(p, 'evidence'), p -> 'indicators', p -> 'thresholds',
                (p -> 'eeg' ->> 'counted')::boolean, (p -> 'eeg' ->> 'ei_z')::real,
                (p -> 'eeg' ->> 'theta_z')::real, p -> 'eeg' ->> 'effect')$b$,
        $a$proj_arr(p, 'evidence'), p -> 'indicators', p -> 'thresholds')$a$);
    IF patched = def THEN
        RAISE EXCEPTION '0015 down: the patched insert of proj_apply was not found';
    END IF;
    EXECUTE patched;
END $$;

ALTER TABLE adaptation_decisions
    DROP COLUMN eeg_counted, DROP COLUMN eeg_ei_z, DROP COLUMN eeg_theta_z, DROP COLUMN eeg_effect;

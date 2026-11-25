-- NeuroAdaptive VR -- rules-v2-mm: the EEG of each decision -- migration 0015 (up)
-- D-F6-128: in MULTIMODAL_ADAPTIVE every ADAPTATION_DECISION carries an "eeg" block (app/adaptation/rules.py):
-- whether the EEG counted in the window, the z of the two indices that decide, and what the EEG did. NULL for
-- STATIC and BEHAVIOR_ADAPTIVE. proj_apply is patched in place from its own definition, as 0009 did with
-- v_adaptations, so its other ~280 lines are not copied here; the patch fails loudly if the text moved.

ALTER TABLE adaptation_decisions
    ADD COLUMN eeg_counted BOOLEAN,
    ADD COLUMN eeg_ei_z REAL,
    ADD COLUMN eeg_theta_z REAL,
    ADD COLUMN eeg_effect VARCHAR(12)
        CHECK (eeg_effect IN ('CONFIRMED', 'VETO', 'LED', 'UNAVAILABLE', 'ONLY_ALERT', 'NEUTRAL'));

DO $$
DECLARE
    def TEXT := pg_get_functiondef('proj_apply(session_events)'::regprocedure);
    patched TEXT;
BEGIN
    patched := replace(def,
        $a$estimator_version, rules_version, evidence, indicators, thresholds)$a$,
        $b$estimator_version, rules_version, evidence, indicators, thresholds,
            eeg_counted, eeg_ei_z, eeg_theta_z, eeg_effect)$b$);
    patched := replace(patched,
        $a$proj_arr(p, 'evidence'), p -> 'indicators', p -> 'thresholds')$a$,
        $b$proj_arr(p, 'evidence'), p -> 'indicators', p -> 'thresholds',
                (p -> 'eeg' ->> 'counted')::boolean, (p -> 'eeg' ->> 'ei_z')::real,
                (p -> 'eeg' ->> 'theta_z')::real, p -> 'eeg' ->> 'effect')$b$);
    IF length(patched) - length(def) <> length($b$,
            eeg_counted, eeg_ei_z, eeg_theta_z, eeg_effect$b$) + length($b$,
                (p -> 'eeg' ->> 'counted')::boolean, (p -> 'eeg' ->> 'ei_z')::real,
                (p -> 'eeg' ->> 'theta_z')::real, p -> 'eeg' ->> 'effect'$b$) THEN
        RAISE EXCEPTION '0015 up: the ADAPTATION_DECISION insert of proj_apply was not found exactly once';
    END IF;
    EXECUTE patched;
END $$;

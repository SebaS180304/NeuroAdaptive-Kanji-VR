-- NeuroAdaptive VR -- UNDERCHALLENGED state (behavior-v2 / rules-v2) -- migration 0009 (down)
-- Back to the v1 values. Refuses while a v2 decision is stored, instead of deleting it.

DO $$
DECLARE view_def TEXT := pg_get_viewdef('v_adaptations'::regclass, true);
BEGIN
    IF EXISTS (SELECT 1 FROM adaptation_decisions
               WHERE learner_state = 'UNDERCHALLENGED' OR cause IN ('FAST', 'NO_ENVIRONMENT')) THEN
        RAISE EXCEPTION '0009 down: UNDERCHALLENGED decisions are stored; they would not fit the v1 columns';
    END IF;
    DROP VIEW v_adaptations;
    ALTER TABLE adaptation_decisions
        DROP CONSTRAINT adaptation_decisions_learner_state_check,
        DROP CONSTRAINT adaptation_decisions_cause_check,
        ALTER COLUMN learner_state TYPE VARCHAR(12),
        ALTER COLUMN cause TYPE VARCHAR(12),
        ADD CONSTRAINT adaptation_decisions_learner_state_check
            CHECK (learner_state IN ('STABLE', 'DISENGAGED', 'OVERLOADED')),
        ADD CONSTRAINT adaptation_decisions_cause_check
            CHECK (cause IN ('ENVIRONMENT', 'AWAY', 'IMPULSIVE'));
    EXECUTE 'CREATE VIEW v_adaptations AS ' || view_def;
END $$;

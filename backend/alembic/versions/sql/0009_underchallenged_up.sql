-- NeuroAdaptive VR -- UNDERCHALLENGED state (behavior-v2 / rules-v2) -- migration 0009 (up)
-- D-F6-59: the estimator gains the state UNDERCHALLENGED (15 characters) with the causes FAST
-- and NO_ENVIRONMENT (14). learner_state and cause were VARCHAR(12) with a CHECK listing the
-- v1 values. v_adaptations reads both columns, so it is dropped and recreated from its own
-- definition around the type change. Existing rows are untouched.

DO $$
DECLARE view_def TEXT := pg_get_viewdef('v_adaptations'::regclass, true);
BEGIN
    DROP VIEW v_adaptations;
    ALTER TABLE adaptation_decisions
        DROP CONSTRAINT adaptation_decisions_learner_state_check,
        DROP CONSTRAINT adaptation_decisions_cause_check,
        ALTER COLUMN learner_state TYPE VARCHAR(16),
        ALTER COLUMN cause TYPE VARCHAR(16),
        ADD CONSTRAINT adaptation_decisions_learner_state_check
            CHECK (learner_state IN ('STABLE', 'DISENGAGED', 'OVERLOADED', 'UNDERCHALLENGED')),
        ADD CONSTRAINT adaptation_decisions_cause_check
            CHECK (cause IN ('ENVIRONMENT', 'AWAY', 'IMPULSIVE', 'FAST', 'NO_ENVIRONMENT'));
    EXECUTE 'CREATE VIEW v_adaptations AS ' || view_def;
END $$;

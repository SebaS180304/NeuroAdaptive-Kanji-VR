-- NeuroAdaptive VR -- Learner Profile v1 -- migration 0007 (up)
-- The last computed profile of each participant, per format version (Plan_Fase6 §4,
-- D-F6-2 and D-F6-3). Derived data: app/adaptation/learner_profile.py rebuilds every
-- row from session_events and the schema (--all), so nothing here is a source of truth.
-- Only COMPLETED sessions feed it; ABORTED ones are in no part (Sebas, 21 Oct).
-- A later format (v2 after the pilot, EEG in F4) lives next to the v1 rows.

CREATE TABLE learner_profiles (
    participant_id  UUID        NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    profile_version VARCHAR(8)  NOT NULL DEFAULT 'v1',
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- The COMPLETED sessions the profile covers, oldest first.
    session_ids     UUID[]      NOT NULL DEFAULT '{}',
    -- calibrations, adaptations, trend (tasks/plan.md).
    profile         JSONB       NOT NULL,
    PRIMARY KEY (participant_id, profile_version)
);

-- =====================================================================
-- NeuroAdaptive VR -- kanji pre-test (spec 13.2) -- migration 0004 (up)
-- =====================================================================
-- MER_Schema_v1 §4 reserved `kanji_pretest`; this is it, split in two:
--   * kanji_pretest_responses  one row per participant x kanji asked
--   * kanji_substitutions      the result, written once when the pre-test ends
--   * participants.pretest_completed_at  set in that same transaction; no
--     session is created while it is NULL (tasks/plan.md, decided 16 Oct)
-- Not a projection of session_events: the pre-test runs before any session.
-- =====================================================================

ALTER TABLE participants ADD COLUMN pretest_completed_at TIMESTAMPTZ;

CREATE TABLE kanji_pretest_responses (
    participant_id        UUID        NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    kanji_id              VARCHAR(32) NOT NULL REFERENCES kanji_items(kanji_id),
    seq                   SMALLINT    NOT NULL,             -- 1 = first kanji asked
    self_report           VARCHAR(8)  NOT NULL CHECK (self_report IN ('NO', 'UNSURE', 'YES')),
    typed_reading         VARCHAR(64),
    typed_meaning         VARCHAR(64),
    -- auto = what the system graded; final = after the researcher's review.
    -- All NULL when self_report = 'NO' (no prompts are shown).
    reading_correct_auto  BOOLEAN,
    meaning_correct_auto  BOOLEAN,
    reading_correct       BOOLEAN,
    meaning_correct       BOOLEAN,
    classification        VARCHAR(16) NOT NULL
                          CHECK (classification IN ('UNKNOWN', 'PARTIALLY_KNOWN', 'KNOWN')),
    answered_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (participant_id, kanji_id),
    UNIQUE (participant_id, seq),
    CONSTRAINT ck_pretest_prompts CHECK (
        (self_report = 'NO') = (reading_correct IS NULL AND meaning_correct IS NULL))
);

-- substitute_kanji_id NULL = KNOWN with no valid substitute left: the original
-- stays and the participant is flagged for the inclusion criterion (spec 13.1).
CREATE TABLE kanji_substitutions (
    participant_id       UUID        NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
    set_name             CHAR(1)     NOT NULL CHECK (set_name IN ('A', 'B', 'C')),
    original_kanji_id    VARCHAR(32) NOT NULL REFERENCES kanji_items(kanji_id),
    substitute_kanji_id  VARCHAR(32) REFERENCES kanji_items(kanji_id),
    PRIMARY KEY (participant_id, original_kanji_id),
    UNIQUE (participant_id, substitute_kanji_id)
);

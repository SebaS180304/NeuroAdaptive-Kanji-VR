-- NeuroAdaptive VR -- kanji pre-test -- migration 0004 (down)
DROP TABLE IF EXISTS kanji_substitutions;
DROP TABLE IF EXISTS kanji_pretest_responses;
ALTER TABLE participants DROP COLUMN IF EXISTS pretest_completed_at;

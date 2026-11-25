-- NeuroAdaptive VR -- KANJI_EXPOSED.stages_authored is a count -- migration 0008 (up)
-- Unity sends how many of the four S5 stages came from authored content (1-4); the column and
-- the projection took it as a boolean. Every stored value was "1" (the glyph) until the set A
-- objects arrived on 23 Oct 2026; with them stage 1 counts too, "2"::boolean fails and
-- KANJI_EXPOSED would stop projecting. true -> 1 loses nothing: no row was ever false.

ALTER TABLE kanji_exposures ALTER COLUMN stages_authored TYPE SMALLINT USING stages_authored::int;

-- proj_apply (0003) is rewritten by replacing its one cast, so the rest of its body stays as is.
DO $$
DECLARE def TEXT := pg_get_functiondef('proj_apply(session_events)'::regprocedure);
BEGIN
    IF position('(p ->> ''stages_authored'')::boolean' IN def) = 0 THEN
        RAISE EXCEPTION '0008: proj_apply no longer casts stages_authored to boolean';
    END IF;
    EXECUTE replace(def, '(p ->> ''stages_authored'')::boolean', '(p ->> ''stages_authored'')::smallint');
END $$;

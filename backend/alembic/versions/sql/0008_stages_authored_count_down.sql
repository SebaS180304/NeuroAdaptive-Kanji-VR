-- NeuroAdaptive VR -- KANJI_EXPOSED.stages_authored is a count -- migration 0008 (down)
-- Back to the boolean of 0002: any count above zero is true.

DO $$
DECLARE def TEXT := pg_get_functiondef('proj_apply(session_events)'::regprocedure);
BEGIN
    IF position('(p ->> ''stages_authored'')::smallint' IN def) = 0 THEN
        RAISE EXCEPTION '0008 down: proj_apply does not cast stages_authored to smallint';
    END IF;
    EXECUTE replace(def, '(p ->> ''stages_authored'')::smallint', '(p ->> ''stages_authored'')::boolean');
END $$;

ALTER TABLE kanji_exposures ALTER COLUMN stages_authored TYPE BOOLEAN USING stages_authored > 0;

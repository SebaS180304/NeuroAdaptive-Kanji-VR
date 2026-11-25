-- NeuroAdaptive VR -- lure columns on trials -- migration 0017 (down)
-- proj_apply back to its trial inserts without the lure fields, then the columns go. The events keep them.

DO $$
DECLARE
    def TEXT := pg_get_functiondef('proj_apply(session_events)'::regprocedure);
    patched TEXT;
BEGIN
    patched := replace(def,
        $b$options, correct_option, hint_available, option_kinds)$b$,
        $a$options, correct_option, hint_available)$a$);
    patched := replace(patched,
        $b$proj_req(p, 'hint_available')::boolean, proj_arr(p, 'option_kinds'))$b$,
        $a$proj_req(p, 'hint_available')::boolean)$a$);
    patched := replace(patched,
        $b$timed_out = COALESCE((p ->> 'timed_out')::boolean, FALSE),
               option_kind = p ->> 'option_kind',
               lure_selected = (p ->> 'lure_selected')::boolean,$b$,
        $a$timed_out = COALESCE((p ->> 'timed_out')::boolean, FALSE),$a$);
    IF length(def) - length(patched) <> length($b$, option_kinds$b$) + length($b$, proj_arr(p, 'option_kinds')$b$)
            + length($b$
               option_kind = p ->> 'option_kind',
               lure_selected = (p ->> 'lure_selected')::boolean,$b$) THEN
        RAISE EXCEPTION '0017 down: the patched trial inserts of proj_apply were not found exactly once';
    END IF;
    EXECUTE patched;
END $$;

ALTER TABLE trials DROP COLUMN option_kinds, DROP COLUMN option_kind, DROP COLUMN lure_selected;

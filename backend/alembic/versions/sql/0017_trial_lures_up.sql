-- NeuroAdaptive VR -- lure columns on trials (D-F6-143, D-F6-131) -- migration 0017 (up)
-- Unity has sent them since the lures went live (4 Nov): option_kinds (the kind of each option, in the order shown)
-- in TRIAL_STARTED, option_kind and lure_selected (the chosen option) in ANSWER_SELECTED. Until now they stayed in
-- session_events.payload. They never enter adaptation decisions (D-F6-132). proj_apply is patched in place from its
-- own definition, as 0015 did; the patch fails loudly if the text moved. Trials projected before this migration
-- get the columns from their own events; trials without lures (before 4 Nov) stay NULL.

ALTER TABLE trials
    ADD COLUMN option_kinds  TEXT[],
    ADD COLUMN option_kind   VARCHAR(12) CHECK (option_kind IN ('CORRECT', 'LURE_STRONG', 'IN_SET', 'UNRELATED')),
    ADD COLUMN lure_selected BOOLEAN;

DO $$
DECLARE
    def TEXT := pg_get_functiondef('proj_apply(session_events)'::regprocedure);
    patched TEXT;
BEGIN
    patched := replace(def,
        $a$options, correct_option, hint_available)$a$,
        $b$options, correct_option, hint_available, option_kinds)$b$);
    patched := replace(patched,
        $a$proj_req(p, 'hint_available')::boolean)$a$,
        $b$proj_req(p, 'hint_available')::boolean, proj_arr(p, 'option_kinds'))$b$);
    patched := replace(patched,
        $a$timed_out = COALESCE((p ->> 'timed_out')::boolean, FALSE),$a$,
        $b$timed_out = COALESCE((p ->> 'timed_out')::boolean, FALSE),
               option_kind = p ->> 'option_kind',
               lure_selected = (p ->> 'lure_selected')::boolean,$b$);
    IF length(patched) - length(def) <> length($b$, option_kinds$b$) + length($b$, proj_arr(p, 'option_kinds')$b$)
            + length($b$
               option_kind = p ->> 'option_kind',
               lure_selected = (p ->> 'lure_selected')::boolean,$b$) THEN
        RAISE EXCEPTION '0017 up: the trial inserts of proj_apply were not found exactly once';
    END IF;
    EXECUTE patched;
END $$;

UPDATE trials t SET option_kinds = proj_arr(e.payload, 'option_kinds')
FROM session_events e WHERE e.id = t.started_event_id AND e.payload ? 'option_kinds';

UPDATE trials t SET option_kind = e.payload ->> 'option_kind', lure_selected = (e.payload ->> 'lure_selected')::boolean
FROM session_events e WHERE e.id = t.answer_event_id AND e.payload ? 'option_kind';

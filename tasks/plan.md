# Implementation Plan: Phase 6 week → M3 (Tue 20 – Fri 23 Oct 2026)

Written 20 Oct 2026, updated 21 Oct (Wed 21 dev tasks, F-PROFILE brief). Replaces the Research Web Portal v1 plan, archived in
`tasks/archive/portal_v1_{plan,todo}.md`. Its open items are carried over unchanged:
the headset runs of Tasks 1.8–1.10 and Checkpoint B (here Task 1, and Task 3, which absorbs run 2), and
Checkpoint D (here Task 12, the first thing to cut).

## Sources of truth
- `Claude outputs/docs_proyecto/Plan_Fase6.md`: §0 F5a close, §3 days, §4 Learner
  Profile decisions D-F6-1 – D-F6-4 (approved by Sebas, 20 Oct), §5 criteria, §9 log.
- `Claude outputs/docs_proyecto/Dashboard_Feature_F-PROFILE.md` (PM, 21 Oct): what the
  profile screen shows, its data cases (§2) and content rules; the data the endpoint
  must carry comes from there. Open decision 3 (endpoint shape) is ours.
- `Claude outputs/docs_proyecto/Contenido_UI_F-PROFILE.md` (UI/UX, 21 Oct): the screen
  copy; every `{…}` in it is a field of the profile endpoint.
- Skill `references/design-system.md`, "V1.8 Learner Profile (F-PROFILE)": the form,
  validated by Sebas (canvas 37, 21 Oct). The cross-session link and the V1.5 group
  filter (canvas 38) were validated by Sebas the same day.
- `Claude outputs/docs_proyecto/Consentimiento_Protocolo_Sesion_v0.md` (PM, 21 Oct):
  Part B is the Thu 22 protocol (Task 13).
- `Claude outputs/docs_proyecto/Guion_Pasada_Visor_F5a.md`, run A: script for Task 3.
- `Claude outputs/docs_proyecto/Plan_Fase5a.md` §5: F5a criteria for the evidence.
- Code wins over the docs copy; ask Sebas when a planning detail looks stale.

## Overview
Four days to M3 (Closed-Loop Prototype, behavioural). What is missing is exactly what
the portal work did not touch: the headset checks, the Learner Profile v1 (backend),
a phase test with a participant with no Japanese, and the evidence and tags.

## Week rules (Sebas, 20 Oct)
- Nothing new in the portal. Checkpoint D only if time is left; it is cut first.
- The backend restarts only between runs, never with the headset on.
- Commits in English, one per change; every message is shown to Sebas before
  committing (message files in Downloads, nothing on `main`).
- Each day ends with a draft in `Claude outputs/` for `Plan_Fase6.md` §9.

## Architecture decisions: Learner Profile v1 (Task 6 – 9)
- **One table, one row per participant and format version** (`learner_profiles`,
  migration 0007; option A, Sebas, 20 Oct): PK (`participant_id` FK, `profile_version`
  `'v1'`), `computed_at`, `session_ids UUID[]` (the completed sessions it covers) and
  `profile JSONB`. Overwritten at each trigger (a session completes or aborts); a later `v2` (after the pilot,
  or the EEG column in F4) lives next to the `v1` rows. Three parts:
  1. `calibrations`: one entry per completed session, the S6 profile as
     `S6Profile.as_dict()` already writes it (`rt_ref` per type, `acc_ref`,
     `away_ref_ms`, `env_dwell_ref_ms`, plus `n_trials`, `reliability`).
  2. `adaptations`: `adaptation_decisions` with `action <> 'NO_CHANGE'`, grouped by
     action, dimension and direction (`from_level` → `to_level`, up or down) and cause,
     with counts per outcome (`POSITIVE` / `NEUTRAL` / `NEGATIVE` / `UNCERTAIN` /
     not recorded).
  3. `trend`: accuracy and mean RT per **completed** session, oldest first, the same
     numbers V1.8 already shows (`trial_timeline()`).
  What the F-PROFILE brief (§2, §4) adds to the JSON, so the screen needs no second call:
  - every entry says which session it comes from (`session_id`, `condition`, `started_at`);
  - each adaptation group lists its `decision_ids` (link to the Session View, V1.5) and
    splits `UNCERTAIN` by `outcome_reason` (`NOT_APPLIED`, `INCOMPLETE`), read from the
    `ADAPTATION_OUTCOME` event payload, where `outcome.py` writes it;
  - calibration per session also carries S6 correct as `k` of `n`, `rt_ref_global`, and
    the trial types that fell back to the global median, for the "Too few {T} trials"
    tooltip. The rule is the estimator's: fewer than `MIN_TRIALS_PER_TYPE` = **3** valid
    trials (the copy's "< 2" is out of date; code wins);
  - a group is keyed by estimated state + cause + dimension + direction (so `AWAY`,
    `ENVIRONMENT`, `IMPULSIVE` and the return after `STABLE` stay apart). Each group has
    a string `key` (e.g. `OVERLOADED.<cause>.LAL.UP`), its decisions **per session**
    (`session_id` → `decision_ids`, for the "See [n] decisions in [k] sessions" list),
    outcome counts plus O4 subtype counts (`RESOLVED`, `HELD_WITH_DROP`…, tooltip) and
    the time of its latest decision (tie-break of the group order);
  - each adaptive session carries its `NO_CHANGE` count ("The system checked {d} times");
  - trend per completed session: S7 trials, correct and mean RT (`s7_trials`,
    `s7_correct`, `s7_mean_rt_ms`), with kanji set and condition. **S7 only**, as the
    validated copy reads ("correct in S7", "of 20"); V1.8's old chart used S5–S8
    accuracy and the mean RT of every block, so the numbers differ by design;
  - a session with no `adaptation_decisions` rows at all (before migration 0003, 13 Oct)
    is marked `decisions_recorded: false`, so the screen shows "—", never 0. A STATIC
    session has no groups by design and is not marked.
  No percentages and no "recommended next" field: counts only, and the profile decides
  nothing (D-F6-1).
  Why JSONB and no extra tables: every part is derived and rebuildable; the table only
  stores the last computed result so the portal does not recompute on every read.
- **Calculation in Python, reusing the estimator code.** `app/adaptation/learner_profile.py`
  rebuilds each session's S6 profile from `session_events` with `build_trials` +
  `build_profile` (as `SessionAdaptationState` and `replay.py` do) and reads parts 2 and
  3 from the schema with `text()`. Nothing new in the estimator.
- **Only sessions `COMPLETED` up to S9 count (Sebas, 20 Oct; confirmed 21 Oct over the
  F-PROFILE brief, which proposed counting an aborted session up to S6/S7).** Aborted sessions are
  left out of all three parts: calibration, adaptations and trend. "Completed" is
  `status = 'COMPLETED'`, never `completed_at` (empty on every session before Task 6a).
- **When it runs (D-F6-3, PM review of 20 Oct in Plan_Fase6 §9): on the status change,
  to `COMPLETED` or to `ABORTED`.**
  - `COMPLETED`: Unity's `PATCH /sessions/{id}/state` with S9 or S10
    (`update_session_state`). `get_db` commits after the handler returns, so the
    calculation is queued with FastAPI's `BackgroundTasks` and runs after that commit,
    in its own DB session, without delaying the response. A late S9 on an `ABORTED`
    session keeps it `ABORTED`: no trigger.
  - `ABORTED`: only `abort_stale_sessions()` (migration 0005) sets it, and the SQL
    function returns a count, not ids. In the same transaction, `services/stale_sessions.py`
    reads the participants of the `ABORTED` sessions with `updated_at = now()` (the
    function sets that, and `now()` is fixed per transaction: exactly the sessions it just
    aborted), commits, then computes them. 0005 stays as it is.
  - Why compute on an abort when the aborted session does not count: the participant
    gets a row even when every session aborted (criterion 4: "each participant with
    sessions has a profile"), with empty parts.
  - A failure in the profile is logged and never fails the PATCH or stops the sweep
    loop (losing a state update for a derived table would be the wrong trade); `--all`
    rebuilds anything a failure missed.
- **`completed_at` (Task 6a, PM review of 20 Oct).** `update_session_state` sets it to
  `now_utc()` the first time the status becomes `COMPLETED` (S9, or S10 if S9 was
  skipped) and never moves it afterwards. One commit, before the profile, because the
  pilot and the portal need it; the profile does not read it.
- **Rebuild:** `python -m app.adaptation.learner_profile --all [--check]` recomputes from
  events and schema; `--check` compares with the stored rows and prints differences
  (expected: none). This is the proof of "reconstructible".
- **D-F6-1: the profile never changes how a session starts.** The starting levels come
  from Unity (`SessionBootstrap`) and `rules.initial_state` (HOME_LEVEL); nothing reads
  `learner_profiles` on that path. A test shows it: a participant with a stored profile
  gets the same session response and the same S7 initial state as one without.
- **Endpoint:** `GET /research/participants/{id}/profile` (read-only, `/research` router,
  Pydantic schema in `schemas/research.py`). 404 for an unknown participant; `null`
  profile when there is none yet. Response: `participant_id`, `profile_version`,
  `computed_at`, `session_ids`, `profile` (the JSON above, as stored). This answers open
  decision 3 of the F-PROFILE brief. The portal screen waits for the mockup (D-F6-4); per
  the brief, if Sebas validates it today it is built Fri 23, otherwise the week of 26 Oct
  and M3 shows the profile from the API. **Validated 21 Oct (canvas 37): Task 11 is
  built Fri 23.**
- **V1.5 group filter (Task 11):** `?group=<key>` on the Session View's Adaptations tab.
  V1.5 rows already have state, cause, dimension and levels, so the tab derives each
  row's key with the same function the profile's key follows and filters by it; no
  new endpoint and no ids in the URL.

## Dependency graph
```
T1 run 1 (B + substitution) ─┐
T3 run 3 (adaptive S1→S9, set C; covers run 2) ┴─► Checkpoint B, verify_adaptation clean ──► (fresh adaptive session for T7/T8)
T4 CLAUDE.md commit (independent)
T6a S9 fills completed_at (independent, first commit of Wed)
T6 migration 0007 ─► T7 calculation + rebuild ─► T8 hooks (COMPLETED, ABORTED) ─► T9 endpoint
                                     └──────────► T10 D-F6-1 test
T6a … T10 ─► T10b day draft for §9
mockup validated by Sebas (design chats) ─► T11 frontend (blocked)
consent text (PM) + participant ─► T13 phase test ─► T14 findings
T3 + T13 ─► T15 evidence ─► T16 tags ─► T17 spec v1.4 change list
T12 Checkpoint D (only if time is left)
```

## Phases
- **Tue 20 (headset):** Tasks 1–5 → Checkpoint Tue.
- **Wed 21 (backend):** Task 6a, then Tasks 6–10, Task 10b → Checkpoint Wed. Task 11
  starts only with the validated mockup.
- **Thu 22 (phase test):** Tasks 13–14 → Checkpoint Thu.
- **Fri 23 (M3):** Tasks 15–17, Task 11 if the mockup was validated Wed 21 (+ 12 if
  time) → Checkpoint M3.

## Cut rule (Plan_Fase6.md §3)
1. Checkpoint D (Task 12) goes to the week of 16 Nov.
2. If the profile does not close Wed 21: computed by the rebuild script and shown in
   the M3 note; migration and screen move to the first week of F4.
3. No participant Thu 22 → Fri 23 morning; if not either, M3 ships with `DEV_UNITY`
   sessions, declared, and the test moves to the behavioural dry run.
4. Spec v1.4 does not move: if the document is not ready, its change list goes as an
   annex to the M3 note.

## Risks and mitigations
| Risk | Impact | Mitigation |
| --- | --- | --- |
| Run 3 is ~30 min in the headset after runs 1–2 | Med | Runs 1–2 can stop at S5–S8; run 3 is a fresh Play. Backend restart only between runs |
| A run fails `verify_adaptation` | High | Record as a finding with the session id (F5a rule: record, do not fix this week unless it blocks M3) |
| `outcome` is NULL for a change (not recorded) | Med | Its own bucket "not recorded", never folded into `UNCERTAIN` |
| The profile hook slows or breaks the S9 PATCH | Med | `BackgroundTasks` after the commit, wrapped in try/except, logged |
| Two triggers for one participant at once (S9 PATCH and a sweep) | Low | The upsert is one statement per row; the later one wins and both compute from the same committed data |
| Tests write the real `DEV_UNITY` profile row in the dev DB | Low | It is the row Checkpoint Wed expects; `--all` recomputes it the same |
| The participant's consent text is not ready Thu 22 | High | PM draft v0 exists (21 Oct); Sebas reviews it and checks with his supervisor today. Registration requires it since 17 Oct |
| The mockup is not validated by Fri 23 | Med | Criterion 4b is declared pending in the M3 note; the endpoint is ready |

## Open questions
1. ~~"Per participant **and version**" (D-F6-2)~~ Option A: one row per participant and
   format version, overwritten (Sebas, 20 Oct).
2. ~~Do `ABORTED` sessions count?~~ No, in no part (Sebas, 20 Oct).
3. Who is the participant on Thu 22, and at what time (Sebas).
4. ~~Set for run 3~~ Set C (Sebas, 20 Oct).
5. Fill `completed_at` for the 15 sessions completed before Task 6a (from their S9
   `STATE_ENTERED` event)? Default: no, recorded as a finding, as with the old
   `segments_authored = false` rows (Sebas to confirm).
6. ~~`ABORTED` sessions: the F-PROFILE brief (§2) counted them up to S6/S7~~ They count
   in no part: calibration, adaptations or trend (Sebas, confirmed 21 Oct). The brief's
   §2 row and Plan_Fase6 §4 get the note (day draft of 21 Oct).
7. ~~F-PROFILE open decisions 1–3~~ Validated 21 Oct: the profile's trend replaces the
   V1.8 chart; calibration shows the latest session with the range of all; endpoint
   shape as above. Cross-session link: option (b), a disclosure list (web design chat).
8. ~~Canvas 38 (cross-session link, V1.5 group filter)~~ Validated by Sebas, 21 Oct.

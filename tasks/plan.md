# Implementation Plan: Phase 6 week → M3 (Tue 20 – Fri 23 Oct 2026)

Written 20 Oct 2026, updated 21 Oct (Wed 21 dev tasks, F-PROFILE brief). **Aligned up to: D-F6-44** (the Fri 23 section; older sections were written up to D-F6-11)
(`Estado_Actual.md`). Replaces the Research Web Portal v1 plan, archived in
`tasks/archive/portal_v1_{plan,todo}.md`. Its open items are carried over unchanged:
the headset runs of Tasks 1.8–1.10 and Checkpoint B (here Task 1, and Task 3, which absorbs run 2), and
Checkpoint D (here Task 12, the first thing to cut).

## Sources of truth
- **`Claude outputs/docs_proyecto/Estado_Actual.md`, the alignment board, comes first**
  (rule in `CLAUDE.md`). A decision exists only with a number in its §4; if this plan or
  any other doc disagrees with it, the board wins and Sebas is told. This plan cites the
  board's numbers (R-…, D…, D-A…, D-F6-…).
- `Claude outputs/docs_proyecto/Plan_Fase6.md`: §0 F5a close, §3 days, §4 Learner
  Profile decisions D-F6-1 – D-F6-4 (approved by Sebas, 20 Oct), §5 criteria, §9 log.
- `Claude outputs/docs_proyecto/Dashboard_Feature_F-PROFILE.md` (PM, 21 Oct): what the
  profile screen shows, its data cases (§2) and content rules; the data the endpoint
  must carry comes from there. Open decision 3 (endpoint shape) is ours.
- `Claude outputs/docs_proyecto/Contenido_UI_F-PROFILE.md` (UI/UX, 21 Oct): the screen
  copy; every `{…}` in it is a field of the profile endpoint.
- Skill `references/design-system.md`, "V1.8 Learner Profile (F-PROFILE)": the form,
  validated by Sebas on canvas 30, 38 and 39 (D-F6-6). Where the validated canvas and
  `design-system.md` differ in form, the canvas wins (D-F6-11).
- `Claude outputs/docs_proyecto/Consentimiento_Protocolo_Sesion_v0.md` (PM, 21 Oct):
  Part B is the Thu 22 protocol (Task 13).
- `Claude outputs/docs_proyecto/Guion_Pasada_Visor_F5a.md`, run A: script for Task 3.
- `Claude outputs/docs_proyecto/Plan_Fase5a.md` §5: F5a criteria for the evidence.
- Below the board, the code wins over a stale mirror copy of a doc; ask Sebas when a
  planning detail looks stale.

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
    trials (the copy says so since 21 Oct);
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
  - the profile never mentions aborted sessions (copy of 21 Oct): no count of them is
    needed in the JSON or on screen;
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
  and M3 shows the profile from the API. **Validated 21 Oct (canvas 30, 38, 39; D-F6-6). Split by Sebas
  (21 Oct): Task 11a, the profile block in V1.8, on Wed 21 evening; Task 11b, the
  cross-session list and the V1.5 filter, on Fri 23 if time.**
- **V1.5 group filter (Task 11b):** `?group=<key>` on the Session View's Adaptations tab.
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
mockup validated (canvas 30, 38, 39; D-F6-6) + T9 ─► T11a profile in V1.8 ─► T11a-fix (D-F6-11) ─► T11b V1.5 filter, cross-session list
consent approved (D-F6-9) + participant (Thu 22, 11:00) ─► T13 phase test ─► T14 findings
T3 + T13 ─► T15 evidence ─► T16 tags ─► T17 spec v1.4 change list
T12 Checkpoint D (only if time is left)
```

## Phases
- **Tue 20 (headset):** Tasks 1–5 → Checkpoint Tue.
- **Wed 21 (backend):** Task 6a, then Tasks 6–10, Task 10b → Checkpoint Wed, then
  Task 11a (frontend) with whatever is left of the day.
- **Thu 22 (phase test):** Tasks 13–14 → Checkpoint Thu.
- **Fri 23 (M3):** Tasks 15–17, Task 11b if time (+ 12 if
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
| The mockup is not validated by Fri 23 | Med | Criterion 4b is declared pending in the M3 note; the endpoint is ready |

## Open questions
1. ~~"Per participant **and version**" (D-F6-2)~~ Option A: one row per participant and
   format version, overwritten (Sebas, 20 Oct).
2. ~~Do `ABORTED` sessions count?~~ No, in no part (Sebas, 20 Oct).
3. ~~Who is the participant on Thu 22, and at what time?~~ Thu 22 at 11:00, with the
   consent approved (D-F6-9; time on the board, §1). The participant is registered in the
   portal with a new code, never their name (protocol Part B, step 3; skill rule 6).
4. ~~Set for run 3~~ Set C (Sebas, 20 Oct).
5. ~~Fill `completed_at` for the sessions completed before Task 6a?~~ Yes (Sebas, 21 Oct; **D-F6-10**):
   `database/backfill_completed_at.sql` filled all 16 (not 15) with the first S9/S10
   `STATE_ENTERED` of each.
6. ~~`ABORTED` sessions: the F-PROFILE brief (§2) counted them up to S6/S7~~ They count
   in no part: calibration, adaptations or trend (Sebas, confirmed 21 Oct). The brief's
   §2 row and Plan_Fase6 §4 get the note (day draft of 21 Oct).
7. ~~F-PROFILE open decisions 1–3~~ Validated 21 Oct: the profile's trend replaces the
   V1.8 chart; calibration shows the latest session with the range of all; endpoint
   shape as above. Cross-session link: option (b), a disclosure list (web design chat).
8. ~~Canvas 38 (cross-session link, V1.5 group filter)~~ Validated by Sebas, 21 Oct.

---

## Fri 23 Oct: Unity integration and validation run (D-F6-35)

Written 23 Oct, updated the same morning. **Aligned up to: D-F6-44.** Sources: board D-F6-25 – D-F6-42,
`Plan_Fase6.md` §9 (vie 23), `Diseno_Sala_ESL.md` §10.2–§10.3, the export manifest
the **new** room export from the approved `.blend1` (D-F6-42; Sebas hands over its folder; the 19:36 export `Sala_v148_20261022_1936` is not used), the `*_animacion.md` sheets in
`JapaneseVR/references/JapaneseVRScene/`, `JapaneseVR/COORDINACION_22oct.md`.

### What is already in the repo (22 Oct, do not redo)
| Item | Commit | Left for today |
|---|---|---|
| Eye at 1.60 m, task +0.24 m, clock 2.50 m (D-F6-25) | `1f3892d` | check that the v148 board 17B lines up with the raised task surface (Z 1.24–2.14) |
| `XR Origin (XR Rig).prefab` reverted (D-F6-29) | `stash@{0}`, tree clean | verify only |
| Spheres replaced by 7 animal events, §10.2 paths, provisional cat sill (D-F6-28, D-F6-32) | `368c401`, `6525086`, `9c761a9`, `bde0bc6` | swap the box stand-ins for the FBX meshes |
| Set A prefabs as reference boxes, all-or-none menu (D-F6-26) | `c493456` | run with the FBX, turn 車 |
| v148 room menu | `JapaneseRoomIntegration.cs` **untracked** | rewrite against the manifest of the new export (below) |
| Cat walking on four box legs moved by `PeripheralAnimation`, 4.0 s | `9c761a9` | **replaced** in Task 22: D-F6-38 plays the FBX's baked clips instead |

### Findings that shape the plan
1. **The untracked room script does not match the manifest.** It finds FBX by older codes
   (`16B_Hoja`, `15B_L`, `24`, `06`, `14`) that no export file has, and it leaves out 8 slots
   (chabudai ×2, zabuton ×6, tea sets ×2) and 18B (seen in the 19:36 manifest; the new export
   is expected to keep its format). Rewrite it to read the `manifest.json` of the folder Sebas
   hands over (D-F6-42), never `Sala_v148_20261022_1936`
   (`huecos[].fbx`, `unity_pos`, `unity_rot_y_deg`), with one small table mapping the
   ESL slots to their slot names. Copy the `huecos/` FBX into `Assets/Art/JapaneseRoom/`, with
   their `.fbm` folders. The one known difference: the clock stays at 2.50 m
   (decision 9), not the 2.367 in the manifest, written down as a D-F6-33 note.
2. **The cat is the one exception to D-F6-27 (D-F6-38 – D-F6-40).** `25B_Gato.fbx` is imported as
   **Generic** with Bake Axis Conversion and `importAnimation = true`, and its baked clips play
   through an Animator; `PeripheralAnimation` no longer moves the cat (the box-leg code of
   `9c761a9` goes). The event lasts 8.08 s in the scheduler (D-F6-39) and the provisional sill
   is ≥ 0.40 m deep (D-F6-40). According to `25B_Gato_ficha.md`, the `EVENTO_VentanaDerecha` / `_Izquierda` clips
   carry the root motion: the origin is the stop point, the cat comes in from +0.47 m, turns 180° and walks back
   out. So the event root sits at the stop point (x 2.25) facing along the sill, and nothing
   moves it along the §10.2 Bézier. `CAMINATA_LUGAR` / `_AVANCE` are imported and not used
   (D-F6-38, refined 23 Oct 10:10). Still its own commit.
3. **Bird, butterfly, silhouette and the 5 kanji match their contracts** (separate pieces, pivots
   as in the sheets). Bird has no head piece: the perched head turn stays a root turn ≤ 15°.
4. **`asset_source` fits in one line**: `KANJI_EXPOSED` already carries `audio_source`; add
   `object_source` = `BLENDER_FBX` | `PLACEHOLDER` from `KanjiDiscoveryController`. The backend
   stores the payload as is, so no migration.
5. HEAD_AWAY thresholds are frozen (F5a). The task kept its angles from the eye (+0.24 m on both),
   so the re-measure should confirm ±24° / +12° / −22°. If a v148 prop falls inside the region,
   that goes to PM as a question, and the thresholds stay as they are.

### Dependency graph
```
new room export (D-F6-42, from Sebas) ─┐
T18 pre-flight + revert map ──┬─> T19 room v148 ──> T20 re-measure (E13, X4, D7 doc)
                              │                         │
                              ├─> T21 bird/butterfly/silhouette meshes ─┤
                              ├─> T22 cat (Generic, baked clips) ───────┤
                              └─> T23 kanji set A ─> T23b object_source ┤
                                                                        v
                                             T24 harness green + Link framerate
                                                                        v
                                             T25 validation run S1→S9 ─> freeze ─> T13 phase test
                                                                        v
                                             T26 day draft + tell Sebas
```
T19 waits for the new export. In the meantime: T18, T21, T23, T23b, and T22, which no
longer waits for anything. The measurements in T20 need the room and the animals in their final
meshes, so T20 runs after T19, T21 and T22.

### Revert map (D-F6-25, D-F6-31)
If the run fails **because of the room**, revert, newest first, every commit that only exists
for v148: today's T22, T21, T20, T19, then `bde0bc6`, `9c761a9`, `6525086`, `368c401`,
`1f3892d`. That brings back the 1.36 m room with the three spheres. The kanji commits (T23,
T23b) are independent and stay. T18 dry-runs this sequence in a throwaway worktree, so the
revert is known to apply cleanly before it is needed.

**Dry run, 23 Oct (T18, on `bde0bc6`):** `bde0bc6`, `9c761a9`, `6525086` and `1f3892d` revert
clean. `368c401` conflicts only in `Phase2TestHarness.cs`, because `c493456` (X10, kanji) sits
next to X9. Resolution: keep the `SetAObjectCases();` call and the whole X10 method (`/// X10.` up to
its `Check("X10", …)`), drop the `PeripheralAnimalCases();` call and the X9 method. With that,
1f3892d reverts clean too: eye back to 1.36 m, no X9, X10 intact. Run the dry run again once
today's commits are in.

**Revert map as built (23 Oct, after Task 23b), newest first:** `cb091f2` (18B), `cc83025` (room
11:39), `ea2d32b` (E13/X4 for v148), `aa36eb6` (cat), `95b47b4` (wing rest), `76a05d9` (bird,
butterfly, silhouette), `6dea19c` (room 10:04), then `bde0bc6`, `9c761a9`, `6525086`, `368c401`
(the one conflict, resolved as above), `1f3892d`. Dry run in a throwaway worktree: applies; eye
back at 1.36 m, X9 and X11 gone, X10 and `object_source` (`4f2a934`, `6cba1c9`) stay. The kanji
commits stay because they do not depend on the room.

### Risks
| Risk | Impact | Mitigation |
|---|---|---|
| An animal kind never shows up in the run (random draw) | Med | The tester looks at each animal when it appears (rows only exist with a DWELL or ORIENTING). If a kind is never drawn, the draft says so and Sebas decides whether that counts as a pass |
| v148 materials look wrong in URP (ToUrp shortcut) | Low | Camera capture from the eye before the headset; fix per material |
| Frame drops through Link (33k tris room + 3.4k cat skinning) | Med | Measure in the HUD during S4, S5 and S7; if the frame time is over budget, look at the cat skinning and the room's realtime shadows first |
| Revert conflicts in `JapaneseLearningStudio.unity` | High | Dry run in T18 |
| The 18B waits for another room re-export (D-F6-44); the run and the test wait for it | High | Task 19 goes in without the 18B; 19b is a menu run, the 18B wiring and the C correction trimmed by X11 |
| The room waits for the re-export (D-F6-42) — done 10:40 | Med | T18, T21, T22, T23 and T23b go first; T19 is a menu run plus a capture once the folder arrives |
| The baked cat clips do not line up with the sill once in Unity (axis, mirror, stop point) | Med | Camera capture from the eye during each of the two clips; the envelope measured in Unity rules (D-F6-41) |

### Open questions (Fri 23)
1. ~~Cat~~ → resolved by D-F6-38 – D-F6-40.
2. ~~`.blend` vs `.blend1`~~ → resolved by D-F6-42 (re-export from the approved file).
3. ~~Silhouette trajectory~~ → stays as it is now (Sebas, 23 Oct); its reference box is the one in D-F6-41.
4. ~~Which cat clips~~ → D-F6-38 (refined 23 Oct 10:10): each window plays its `EVENTO_*`; the
   two `CAMINATA_*` are not used.
5. ~~Clash with `9c761a9`~~ → the commit for Task 22 removes the box cat's code; `9c761a9` is not reverted (Sebas, 23 Oct).

# Todo: Phase 6 week → M3 (20 – 23 Oct)

Plan: `tasks/plan.md`. Previous list (portal v1): `tasks/archive/portal_v1_todo.md`.
**Aligned up to: D-F6-44** (Fri 23 section; older sections stay at D-F6-17) (`Estado_Actual.md`, the alignment board; it wins over this list).
Every commit: message file in Downloads, shown to Sebas first, one change each.

---

## Tue 20 Oct: headset

Quest 2 via Link in the Editor. Inspector changes on `SessionBootstrap`
(`devParticipantCode`, `newSessionKanjiSet`, `condition`) are temporary: revert them
after each run. Never save the scene during Play. Restart the backend only between runs,
never with `--reload`, never with the headset on.

### [x] Task 1: Run 1, set B with a substitution (old Tasks 1.8, 1.9 for B, 1.10)
- [x] Portal `/pretest`: register `TEST_VR_B` with consent; answer "Yes" with the right
      reading on one set B kanji (on 18 Oct, 山 → 口), "No" on the rest. Note the substitute
- [x] `SessionBootstrap`: `devParticipantCode = TEST_VR_B`, `newSessionKanjiSet = B`; Play
      through S5–S8 (low `baselineTimeScale` is fine)
- [x] S5–S8 show the substitute in the original's place
- [x] S5: the 4 kept B kanji log "authored" and assemble from real strokes; every group can
      be grasped. A first-choice substitute (口 for 山) also logs "authored"; any other
      substitute logs the placeholder warning, as expected

**Verify (DB, `<id>` from the Unity log):**
- [x] `select kanji_id, segment_count, segments_authored from assemblies where session_id = '<id>';` → `true` for every kanji, the substitute included if it is one of the 10 first-choice reserve kanji
- [x] `select block_state, kanji_id, count(*) from trials where session_id = '<id>' group by 1, 2 order by 1, 2;` → the substitute appears and its original never does

**Deps:** none. **Scope:** XS (no code)

### Task 2: Run 2, set C: folded into Task 3 (Sebas, 20 Oct)
Run 3 is set C with `DEV_UNITY` to S9, so its S5 checks cover run 2.

### [x] Task 3: Run 3, `BEHAVIOR_ADAPTIVE` complete S1 → S9, set C (run A of `Guion_Pasada_Visor_F5a.md`; covers run 2)
**Description:** First full adaptive session with the weekend changes: pre-test gate and
effective set, S4 with fixation cross and closing eye, real segments for B and C.
- Setup: `condition = BEHAVIOR_ADAPTIVE`, `devParticipantCode = DEV_UNITY`, set C
  (Sebas, 20 Oct), visit 1, `baselineTimeScale = 1`. Step 1 of the script (O4 commit) is stale: skip it.
- No headset off and no chat from S1 to S9. S7 follows the script's table (S7-004…006
  slow errors → LAL up; 007…009 no Hint; then normal).

**Acceptance:**
- [x] S4 shows the cross (eyes open) and the eye that closes once (eyes closed)
- [x] S5 (run 2, old Task 1.9 for C): all 5 C kanji log "authored"; every group can be grasped (花's three pieces, 足's foot); `assemblies` query as in Task 1 → `true` for all 5
- [x] The session reaches S9 and its status is `COMPLETED`
- [x] `va <id>` (`database/verify_adaptation.sql`): §1 20 answered in S7, 20 decisions, changes all `APPLIED`, 0 `SKIPPED`; §2–§5, §7, §8 empty; §6 p95 latency tens of ms at most; §9 every change with an outcome
- [x] `verify_projection.sql` clean for the session; `check_loop.sql` and `python -m app.adaptation.replay <id>` give the live decisions and outcomes
- [x] Anything off-script recorded with its trial id (a finding, not a fix)

**Verify:** outputs in a `.txt` in Downloads; session visible in the portal (V1.2–V1.6).

**Deps:** none (after Task 1 or before it, as Sebas prefers). **Scope:** XS

### Checkpoint B: the pre-test feeds the VR loop
- [x] A participant registered and pre-tested in the portal runs a Unity session with their effective set (Task 1)
- [x] Sets B and C assemble from real segments (Tasks 1 and 3); `dashboard/tests/e2e/checkpoint-b.spec.ts`
- [x] Tick old Tasks 1.8, 1.9, 1.10 in `tasks/archive/portal_v1_todo.md`; keep `TEST_VR_B`: `checkpoint-b.spec.ts` needs its substitution (Sebas, 20 Oct)

### [x] Task 4: Commit the CLAUDE.md change
- [x] Only `CLAUDE.md` staged (the XR Origin prefab change is not part of it)
- [x] Message shown to Sebas: `docs(claude): point to the Phase 6 plan`
- [x] Separate commit, also shown: `docs(tasks): plan the Phase 6 week to M3` (this plan, the archived portal plan)

**Deps:** none. **Scope:** XS

### [x] Task 5: Day draft
- [x] `Claude outputs/Borrador_Plan_Fase6_9_20oct.md`: §9 Tue 20 lines (Checkpoint B, run 3 id and result, findings)

### Checkpoint Tue 20
- [x] Checkpoint B ✅; run 3 complete and clean in `verify_adaptation`
- [x] Day draft handed to Sebas

---

## Wed 21 Oct: Learner Profile v1 (backend)

Branch `phase/6-learner-profile` from `phase/7-research-dashboard` (Plan_Fase6 header).
Source: Plan_Fase6 §3 (Wed 21), §4 (D-F6-1 – D-F6-3) and the PM review of Tue 20 in §9.
No frontend until Sebas validates the mockup (Task 11). Data needs: `Dashboard_Feature_F-PROFILE.md` §2 and every `{…}` in `Contenido_UI_F-PROFILE.md`.
Before the branch: the XR Origin prefab change and the uncommitted `tasks/` edits stay
out of every Learner Profile commit (`tasks/` goes in its own `docs(tasks)` commit).

### [x] Task 6a: S9 fills `experiment_sessions.completed_at`
**Description:** `update_session_state` sets `completed_at = now_utc()` the first time the
status becomes `COMPLETED` (S9, or S10 if S9 was skipped). One commit, before the profile.
The older sessions were backfilled afterwards (plan.md open question 5).

**Acceptance:**
- [x] PATCH to S9 → `completed_at` set; a later PATCH to S10 keeps the same value (pytest)
- [x] PATCH to a state before S9 → `completed_at` stays NULL
- [x] A late S9 on an `ABORTED` session → still `ABORTED`, `completed_at` NULL

**Verify:** `pytest tests/test_session_lifecycle.py`; full pytest green.
**Deps:** none. **Files:** `routes/sessions.py`, `tests/test_session_lifecycle.py`. **Scope:** XS

### [x] Task 6: Migration 0007 `learner_profiles`
**Description:** Table as in `plan.md` (PK `participant_id` FK `ON DELETE CASCADE` +
`profile_version`, option A; `computed_at`, `session_ids UUID[]`, `profile JSONB`). Same pattern as
0003–0006: SQL in `alembic/versions/sql/0007_learner_profile_{up,down}.sql`.

**Acceptance:**
- [x] up, down, up again on the dev DB; `database/schema.sql` and `ERD.md` cover 0007
- [x] The `_clean_test_participants` fixture still deletes test participants (cascade)

**Verify:** `alembic upgrade head`; full pytest green.
**Deps:** none. **Files:** migration + 2 SQL, `models/` (if an ORM model is needed; `text()` may be enough), `database/schema.sql`, `database/ERD.md`. **Scope:** S

### [x] Task 7: Calculation and rebuild
**Description:** `app/adaptation/learner_profile.py`: `compute(db, participant_id)` builds
the three parts (calibrations from events via `build_trials` + `build_profile`;
adaptations grouped by action, dimension, direction, cause with outcome counts; trend over
completed sessions, by `status = 'COMPLETED'`, never `completed_at`) and upserts the row.
CLI `--all` and `--check`. JSON as in `plan.md` (each entry with its `session_id` and
condition; groups with `decision_ids` and `UNCERTAIN` split by `outcome_reason`;
`decisions_recorded: false` for sessions before 0003; the calibration, group-key,
per-session ids, subtype, `NO_CHANGE` and trend fields listed in `plan.md`).

**Acceptance:**
- [x] On the 4 adaptive `DEV_UNITY` sessions (`099690e1`, `d392fd25`, `a0c65228`, `a5748886`) + run 3: each calibration equals the S6 profile in that session's `ADAPTATION_DECISION` context; adaptation counts equal a direct `GROUP BY` on `adaptation_decisions`; trend equals a direct query of S7 trials (pytest; S7 only, see plan.md)
- [x] STATIC sessions give calibrations and trend, and no adaptation groups
- [x] An `ABORTED` session appears in no part (Sebas, 20 Oct, confirmed 21 Oct); a NULL outcome counts as "not recorded"
- [x] An `UNCERTAIN` outcome is counted under its reason (`NOT_APPLIED` / `INCOMPLETE`); a group's `decision_ids` equal its rows in `adaptation_decisions`
- [x] A completed session from before 0003 has `decisions_recorded: false`; a STATIC session has no groups and no such flag
- [x] Calibration `k`/`n` match S6's answered trials; a type with < 3 valid S6 trials (`MIN_TRIALS_PER_TYPE`) is listed as a global-median fallback
- [x] A group's per-session ids add up to its count; each adaptive session's `NO_CHANGE` count equals `adaptation_decisions`; trend values equal a direct query of S7 trials
- [x] `--all --check` after `--all` prints no differences

**Verify:** `pytest tests/test_learner_profile.py`; the CLI in the backend container.
**Deps:** 6. **Files:** `app/adaptation/learner_profile.py`, `tests/test_learner_profile.py`. **Scope:** M

### [x] Task 8: Compute when the status becomes `COMPLETED` or `ABORTED`
**Description:** (D-F6-3, PM review of 20 Oct.) `COMPLETED`: `update_session_state` queues
`compute` with `BackgroundTasks`, so it runs after `get_db` commits. `ABORTED`:
`services/stale_sessions.py` reads, in the same transaction, the participants of the
sessions it just aborted (`updated_at = now()`) and computes them after the commit (0005
unchanged). The aborted session is still left out of the profile; the abort gives the
participant a row. Errors are logged and never fail the PATCH or stop the sweep loop.

**Acceptance:**
- [x] PATCH to S9 → the participant's row includes the session (pytest)
- [x] A session swept to `ABORTED` → the participant has a row, and the session is in no part (pytest, with `abort_stale_sessions(interval '0')` on a test session)
- [x] A late S9 on an `ABORTED` session → no trigger, the session is not in the row
- [x] A forced error in `compute` → the PATCH still returns 200 with the state saved; the sweep still returns its count

**Verify:** pytest. **Deps:** 7. **Files:** `routes/sessions.py`, `services/stale_sessions.py`, tests. **Scope:** S

### [x] Task 9: Endpoint `GET /research/participants/{id}/profile`
**Acceptance:**
- [x] Returns the stored row through a Pydantic schema (`participant_id`, `profile_version`, `computed_at`, `session_ids`, `profile`); 404 unknown participant; `profile: null` with no row
- [x] Read-only (no compute on read); the data contract in the skill lists it

**Verify:** `pytest tests/test_learner_profile.py` (endpoint tests live with the profile's). `npm run gen:api` waits for a backend restart (Task 11). **Deps:** 7. **Files:** `routes/research.py`, `schemas/research.py`, skill `data-contract.md`, test. **Scope:** S

### [x] Task 10: D-F6-1 test: the profile does not change how a session starts
**Acceptance:**
- [x] Two pre-tested participants, one with a stored profile (with an `OVERLOADED` → LAL HIGH history) and one without: `POST /sessions` gives the same fields (condition, kanji set and items, no level fields), and `SessionAdaptationState` enters S7 with `HOME_LEVEL` for both
- [x] A comment in the test cites D-F6-1 ("until after the pilot")

**Verify:** pytest. **Deps:** 6, 8. **Files:** `tests/test_learner_profile.py`. **Scope:** XS

### [x] Task 11a: Frontend: the Learner Profile at the top of V1.8 (Wed 21 evening; split by Sebas, 21 Oct)
**Description:** The profile block of the validated canvas (30, 38, 39; D-F6-6): header with the scope line, *Usual performance*,
*What followed each adaptation* (at most 3 groups, "Show [n] more groups"), *Across sessions*
replacing the old V1.8 trend chart (one chart, accuracy as correct of 20), and the "No profile
yet." panel. "See [n] decisions" goes to the session's V1.5 unfiltered for now (11b adds the
filter and the cross-session list). Backend untouched.

**Acceptance:**
- [x] Load the `research-dashboard-conventions` skill first; copy from `Contenido_UI_F-PROFILE.md` (updated 21 Oct), form from design-system.md "V1.8 Learner Profile (F-PROFILE)"; no new tokens
- [x] design-system.md without the aborted-sessions clause (canvas 39, validated 18:22, copied to the skill 21 Oct)
- [x] Adjustments of the 21 Oct copy: global-median mark for a type with < 3 valid S6 trials; empty profile with the validated canvas text, the same with no sessions or only aborted ones; **no mention of aborted sessions anywhere in the profile**; `UNCERTAIN` · `INCOMPLETE` reads "Can't tell: S7 ended first"
- [x] The cases of the canvas render from real data: `DEV_UNITY` (many sessions), STATIC only, adaptive without changes, no completed session ("No profile yet.", also when every session aborted), one session; sessions before 0003 show "—", never 0
- [x] Counts match `adaptation_decisions` / the endpoint (Vitest on the pure text helpers; Playwright on `DEV_UNITY`)
- [x] No regression before the Thu 22 test: build, Vitest 133/133 and Playwright 31/32 green. The one failure, `quality.spec.ts`, fails the same on the last commit without 11a: `/research/quality` takes ~3.7 s and the test waits 5 s while the suite runs in parallel; alone it passes. Finding, not fixed (not part of 11a)
- [x] Screenshots light and dark (`DEV_UNITY`, STATIC only, no profile) with the repo's Playwright; the Playwright MCP has no Chrome on this machine. 5-tell audit reported

**Deps:** 9 (+ `gen:api`, done). **Files:** `features/participants/` (ParticipantView, new profile component, TrendChart), tests. **Scope:** M

### [x] Task 11a-fix: match the canvas artboard (`ParticipantProfile.dc.html`, read 21 Oct); only the "Not recorded" badge stays open (D-F6-16)
Compared after `983aaa7`. **D-F6-11:** where the validated canvas and `design-system.md` differ in form,
the canvas wins (the web design chat copies the differences into `design-system.md`; development
does not wait). Copy stays as `Contenido_UI_F-PROFILE.md` (D-F6-6) where the canvas text is older.
- [x] Header: chips and the sessions fact in **one** wrapping row, right-aligned (not chips above the fact); fact in `--color-text-muted`; header gap 8 px
- [x] Empty profile: keep the scope line ("A summary of the completed sessions. …") and put "No profile computed" in the meta slot
- [x] Usual performance table: "Latest session" and range columns **right-aligned**, 16 px left padding; compact rows (5 px padding, not 40 px); "Typical response time" row 8 px top padding
- [x] Fallback mark: tooltip names the short type ("Too few T3 trials in practice; …"), and gets an `aria-label`
- [x] Adaptations panel: padding 20/24 px; groups as an `<ol>`, each row with a 1 px **top** rule and 12 px vertical padding
- [x] Links: "See [n] decisions" underlined, weight 500; the disclosure uses a 12 px stroke chevron (SVG), not ▾
- [x] Decision list: full width of the group row, under the badges, on `--color-explain-bg`, padding 8/12 px; the date in muted text, "Session 3 (2026-10-16)"
- [x] "Show [n] more groups": transparent background
- [x] Empty texts (STATIC only, no changes): 12 px top padding and a top rule; the "See [d] decisions" link **below** the sentence, not beside it
- [x] Badge tooltip: "POSITIVE, RESOLVED" (comma, no count), not "POSITIVE · RESOLVED 1"
- [ ] **"Not recorded" badge (still open): its form waits for Sebas's validation on the canvas, Thu 22 after 12:00 (D-F6-16).** Until then the badge keeps the form it has since `983aaa7` (the V1.5 dashed "Not recorded" chip with its count); no new form is applied
- [x] Across sessions: 16 px top padding, 8 px gap; a compact chart (~124 px, no x-axis title); the legend row ends with "Completed sessions only, numbered as in the table."; point tooltip "Session 4, Static, set A, 14 of 20 correct"
- [x] Below the profile: a "Pre-test and kanji sets" section (title 22/28, 1 px top rule, columns 1–10) with the lead sentence and the Pre-test / Notes list; "Kanji replaced by the pre-test" in columns 11–16 with an 18/24 title, 1 px top rule, and no intro sentence
- [x] STATIC-only text by number of completed sessions (UI/UX, 21 Oct; `Contenido_UI_F-PROFILE.md` §5, row "Solo STATIC"). With 1 or 2 sessions "Across sessions" says there is no trend yet, so "the trend" is not named:
  - 1: "No adaptations: the only session so far was STATIC, and STATIC never adapts. Usual performance comes from this session."
  - 2: "No adaptations: both sessions so far were STATIC, and STATIC never adapts. Usual performance and the results across sessions come from them."
  - ≥ 3: the current text ("all {n} sessions so far were STATIC … the trend come from these sessions.")
  - Change `staticOnly()` in `profileText.ts` and its tests: `profileText.test.ts` (the 2-session case expected "all 2 sessions") and `ParticipantView.test.tsx` (the STATIC-only case, 2 sessions)
- [x] Not changed on purpose: dates stay in the portal's format (`formatDate`, "2026-10-21"), the canvas shows illustrative "Oct 21 2026"; copy from the 21 Oct document wins over older canvas text ("From practice (S6) of {n} completed sessions", "From {b} completed adaptive session(s)", "Can't tell: S7 ended first"); the "Not recorded" badge stays (real data has it, the canvas has no such case)

### [ ] Task 11b: Frontend: cross-session decisions and the V1.5 group filter (Fri 23 if time, else week of 26 Oct)
- [ ] "See [n] decisions in [k] sessions" disclosure list (canvas 38), newest first, "Session [#] ([date])"
- [ ] V1.5 `?group=<key>`: notice, "Back to the profile", "Show all decisions"; reload and back keep it
- [ ] V1.5 and V1.6: cause "Impulsive" reads "Quick errors"
- [ ] Verified with the Thu 22 participant (one session); F-PROFILE §5 closed
- [x] "No adaptations: the only session so far was STATIC…" (one STATIC session): confirmed by UI/UX on 21 Oct without "the trend", plus a 2-session text; built in Task 11a-fix

**Deps:** 11a. Not needed for M3 (criterion 4b is met by 11a).

### [x] Task 10b: Day draft
- [x] `Claude outputs/Borrador_Plan_Fase6_9_21oct.md`: §9 Wed 21 lines (`completed_at` commit, Learner Profile v1 backend with commits, `DEV_UNITY` profile summary, findings)

### Checkpoint Wed 21
- [x] Full pytest green; `graphify update .`
- [x] `DEV_UNITY` profile computed from its 5 completed adaptive sessions, `--check` clean
- [x] Day draft handed to Sebas
- [x] Open question 5 of `plan.md` answered by Sebas (or the default recorded); question 6 answered 21 Oct (`ABORTED` never counts). Q5 answered 21 Oct: backfilled, 16 sessions (`database/backfill_completed_at.sql`)

---

## Thu 22 Oct: phase test (moved to Fri 23, after Task 25: D-F6-35)

### [ ] Task 13: Phase test with a participant with no Japanese
- [ ] Before: consent approved (D-F6-9, protocol Part B of `Consentimiento_Protocolo_Sesion_v0.md`), participant at 11:00 (Sebas), `/health/db` OK. No commits and no backend restart before 12:00 (board §1)
- [ ] Portal: registration with consent, pre-test
- [ ] Headset: `BEHAVIOR_ADAPTIVE` complete to S9 with their code; Sebas's sheet notes off-script moments with trial ids
- [ ] After: `verify_projection` and `verify_adaptation` 0 discrepancies; each applied change has an outcome (or `UNCERTAIN` with reason); profile row present; session reviewed in the portal

**Deps:** 3, 8, consent, participant. **Scope:** XS (no code)

### [ ] Task 14: Findings
- [ ] Draft `Hallazgos_Prueba_Fase_F5a.md` (in `Claude outputs/`), classified like `Hallazgos_Prueba_Fase_F3.md`
- [ ] Day draft `Claude outputs/Borrador_Plan_Fase6_9_22oct.md`

### Checkpoint Thu 22
- [ ] Participant session complete, with profile; findings classified

---

## Fri 23 Oct: M3

Integration first, then the validation run, then the freeze, then Task 13 (D-F6-35). Each
block gets its own commit, so it can be reverted (revert map in `plan.md`). Exports in
`C:/Users/drdom/Documents/JapaneseVR/` (never the `FALLIDO_*` files).

### [x] Task 18: Pre-flight (no code) · done 23 Oct
- [x] `git diff --quiet -- "unity-client/**/XR Origin (XR Rig).prefab"`: the prefab is the committed one, the change sits in `stash@{0}` (D-F6-29)
- [x] Eye 1.60 m and task +0.24 m are in `1f3892d` (D-F6-25): Camera Offset y = 1.60 in the scene
- [x] Harness run as it stands: write down which cases are red before starting (E13 is red on purpose since `1f3892d`) → **85/86, only E13 red** (props measured from the 1.36 m eye); X4, X9, X10 green; scene left clean
- [x] Dry-run the revert map in a throwaway worktree (`git worktree add`, `git revert --no-commit` newest first): applies clean → clean except `368c401` in `Phase2TestHarness.cs`; the resolution is written down in `plan.md` (keep X10, drop X9)
**Deps:** none. **Scope:** XS

### [x] Task 19: Room v148 from its new export (D-F6-25, D-F6-32, D-F6-40, D-F6-42)
- [x] **Waits for the new export folder from the approved `.blend1`; Sebas hands it over.** `Sala_v148_20261022_1936` is not used. Until it arrives: Tasks 18, 21, 22, 23, 23b
- [x] `JapaneseRoomIntegration` reads the `manifest.json` of that folder: every slot placed at `unity_pos` / `unity_rot_y_deg`; the ESL slots keep their GameObject, `EnvironmentProp` and name; the clock stays at 2.50 m (decision 9, noted)
- [x] Old primitive room switched off, not deleted; provisional cat sill kept (≥ 0.40 m deep since Task 22); no collider on any prop
- [x] Camera capture from the 1.60 m eye: the room looks like the v148 render; the board 17B lines up with the raised task (Z 1.24–2.14)
- [x] 18B podium held back until its re-export with the screen at 25° from the vertical (D-F6-44): S2 keeps the box podium; wiring the new 18B is Task 19b
→ `6dea19c`: 35/36 slots, 18B pending (Task 19b); X11 green, E13 red until Task 20.
**Verify:** menu runs with 0 MISSING against the new manifest; capture compared with `LAY3_CAM_Ojo_160`. **Commit:** `feat(unity): build the v148 room from its manifest`
**Deps:** 18, the new export. **Files:** `Editor/JapaneseRoomIntegration.cs`, scene, `Art/JapaneseRoom/**`. **Scope:** M

### [x] Task 19b: The new room export and the 18B podium (D-F6-44)
- [x] **Waits for the new `export/Sala_v148_*` folder** (full room, manifest compared with `Sala_v148_20261023_1004`: only the 18B changes)
- [x] `ExportDir` points at it; `Pending` empty; the menu runs with 0 MISSING; the 18B goes to `ControlsIntro` and its screen canvas lies on the model's top (25° from the vertical, centre 1.15 m since D-F6-45; was 1.22)
- [x] The export comes from `export_sala_v148_fbx_v3.py`, which flattens the child meshes: the 18 pieces arrive with correct axes and the hierarchy may change in any slot (D-F6-44, refined 11:10). **First, one of the 18** (the maneki-neko of `10_Repisa_Maneki`): imported raw, without the correction, it stands on its shelf at the same world bounds as today (y 2.21–2.43, z 3.74–3.86); X11 against its FBX
- [x] Then the C = (270, 180, 0) correction (`FixChildAxes`, `ExpectedPose`) comes out **in this same commit**, and so does X11's per-piece check against it; it was only for `Sala_v148_20261023_1004`. X11 keeps a guard that fits flattened pieces, chosen once the hierarchy is seen
- [x] X11 green with 36/36; camera capture of S2 from the eye
**Commit:** its own, `feat(unity): wire the upright 18B podium from the room re-export`. **Deps:** 19, the new export. **Scope:** S
→ D-F6-45: `Sala_v148_20261023_1139` only. `cc83025`: room from it, C correction removed (maneki-neko at the same world bounds without it), X11 checks flattened pieces. `cb091f2`: 18B wired, S2 canvas at (0, 1.15, 1.02), 25° from the vertical, X11 checks it lies on the model's screen. 87/87.

### [x] Task 21: Bird, butterfly and silhouette meshes (D-F6-27, D-F6-28)
- [x] `23B_Pajaro.fbx` and `26B_Mariposa.fbx` replace the box stand-ins under each event's `Model`; the wing pieces get the names `PeripheralAnimation` already looks for (Wing L/R); pivots as in the sheets
- [x] `24B_Silueta.fbx` under `OutsideFigureLeft_T3` / `Right_T3`, **current trajectory unchanged**
- [x] Not one sphere left in the v148 room (X9 asserts it); bird 0.4 / 0.7 / 0.4 s with its wings folded while perched; butterfly as in §10.2
→ `76a05d9`: wings on WingL/WingR pivots (bird 0° perched, 10°-80° flying; butterfly 10°-70°), silhouettes facing their walk; X9 green, 86/87 (E13 until Task 20).
**Verify:** X9 green; Play with one event of each kind forced, seen from the eye. **Commit:** `feat(unity): give the bird, the butterfly and the silhouette their Blender meshes`
**Deps:** 18. **Scope:** M

### [x] Task 22: Cat from its rigged FBX (D-F6-38, D-F6-39, D-F6-40)
- [x] `25B_Gato.fbx` imported as **Generic**, Bake Axis Conversion on, `importAnimation = true`; an Animator plays its baked clips. Each window plays its own `EVENTO_VentanaDerecha` / `_Izquierda` clip (8.08 s, root motion included); the two `CAMINATA_*` clips are imported and not used (D-F6-38, refined 23 Oct 10:10)
- [x] `PeripheralAnimation` no longer moves the cat: the box-leg, head and tail code of `9c761a9` goes in this commit, without reverting `9c761a9` (Sebas, 23 Oct), and so does the cat's §10.2 Bézier. The event root sits at the stop point (x 2.25) facing along the sill
- [x] The scheduler records the cat's event as 8.08 s (D-F6-39; still under HIGH's 10 s minimum interval)
- [x] Provisional sill ≥ 0.40 m deep (D-F6-40), simple block, no collider, the colour of the window sill
- [x] X9 cat checks rewritten: Animator plays the right clip per window, 8.08 s, starts and ends out of view, ≤ 3 Hz; nothing in `PeripheralAnimation` moves its bones
→ clip sampled with `SampleAnimation` (8.083 s); stop (±2.25, 0.665, 4.15); sill x 1.64-3.39 × z 4.02-4.42; Unity envelope at the stop 0.12 × 0.37 × 0.37 (D-F6-41 box: 0.12 × 0.37 × 0.38); X9 green, 86/87.
**Verify:** X9 green; Play with each cat event forced, camera capture from the eye at entry, head turn, half turn and exit. **Commit:** its own, `feat(unity): play the cat's baked walk from its rigged FBX`
**Deps:** 18. **Files:** `PeripheralAnimation.cs`, `PeripheralEventScheduler.cs`, `Phase2TestHarness.cs`, scene, `Art/Peripheral/**`. **Scope:** M

### [x] Task 20: Re-measure in Unity (D-F6-25, D-F6-33, D-F6-41)
- [x] E13: the `LayoutOfRecord` rows of the v148 props and the animals measured in Unity with the E13 method; every difference > 1° from §10.3 noted with its cause in the day draft; a misplaced object gets fixed. The cat is measured over its baked clip, not a Bézier
- [x] Reference boxes of D-F6-41: cat ≈ 0.12 × 0.37 × 0.38 m, silhouette 0.34 × 0.34 × 1.36 m. **If the envelope measured in Unity on the imported FBX is different (the cat gave 0.49 × 0.12 × 0.43), the Unity one is used**, and the difference with its cause goes in the day draft
- [x] X4: the HEAD_AWAY task region measured at the 1.60 m eye; thresholds stay at ±24 / +12 / −22 unless a prop falls inside, and then it is a question for PM
- [x] `Claude outputs/Medicion_D7_HeadAway.md`: a new section "v148 room, eye 1.60 m (23 Oct)" with the angles, the method and the result
→ 87/87. E13: 22 v148 rows measured in Unity, the cat over its baked clip; > 1° from §10.3 only the clock (2.50 m), the silhouettes (current path) and the window birds (mesh smaller than the box), all explained in the draft. X4: v148 room targets; **the clock is inside the task region** (centre 10.5° vs +12°), reported by X4 and as duda 7 for PM; thresholds unchanged. `Medicion_D7_HeadAway.md` §10.
**Verify:** E13 and X4 green. **Commit:** `test(unity): measure the v148 room's layout of record`
**Deps:** 19, 21, 22. **Scope:** S

### [x] Task 23: Set A objects (D-F6-26)
- [x] The five `KANJI_0N_*.fbx` copied to `Assets/Art/KanjiLessonAssets/`; the menu assigns all five (or none)
- [x] 車 turned so its top faces the player (ESTADO.md: the cart is read from above); checked with a camera capture from the eye in S5
- [x] X10 green: five prefabs, all assigned, no boxes left
**Commit:** `feat(unity): show the five set A objects from Blender in S5`. **Deps:** 18. **Scope:** S
→ `4f2a934`: 5 models, 0 boxes, 5/5 assigned; 車 turned −90° X on its prefab root (ESTADO.md 02), 0.24 × 0.40 × 0.24 as shown. 87/87.

### [x] Task 23b: `object_source` in `KANJI_EXPOSED`
- [x] `object_source` = `BLENDER_FBX` | `PLACEHOLDER`, next to `audio_source`; harness case asserts both values
**Commit:** separate, `feat(telemetry): say whether the S5 object is real or a placeholder`. **Deps:** 23. **Scope:** XS
→ `6cba1c9`. **Found on the way:** `kanji_exposures.stages_authored` is BOOLEAN and the projection casts the payload with `::boolean`, but Unity sends a count. Until now it was always 1; with the set A objects it is 2, and `'2'::boolean` fails, so every S5 exposure of the run would fail to project (verify_projection). Fix pending Sebas's OK (see the day draft).

### Checkpoint: integration
- [ ] Every block committed on its own (messages in Downloads, shown to Sebas first); `graphify update .`

### [ ] Task 24: Harness green and a smooth headset over Link
- [ ] Whole harness green
- [ ] Quest 2 over Link: frame rate steady at the headset's refresh in S4, S5 and S7, no ASW and no dropped-frame spikes (Oculus Debug Tool performance HUD), with the animals on show
**Deps:** 19–23b. **Scope:** XS (no code unless a drop shows up)

### [ ] Task 25: Validation run S1 → S9 (D-F6-35)
- [ ] Set A, `BEHAVIOR_ADAPTIVE`, visit 1, a test code; Inspector changes reverted after the run; scene never saved in Play
- [ ] `verify_adaptation` and `verify_projection`: 0 discrepancies
- [ ] `select object_name, kind, count(*) from distractor_interactions where session_id = '<id>' and object_group = 'PERIPHERAL' group by 1, 2;` → the animals are there (which kinds were drawn goes in the draft)
- [ ] `KANJI_EXPOSED`: `object_source = BLENDER_FBX` for all five
- [ ] If it fails because of the room: apply the revert map, go back to the 1.36 m room with the spheres (D-F6-31), run again
- [ ] **Passed → freeze** (no commits, no backend restarts) until the phase test ends; tell Sebas so he can set the time
**Deps:** 24, **19b (the test waits for the new 18B, D-F6-44)**. **Scope:** XS (no code)

### [ ] Task 26: Day draft
- [ ] `Claude outputs/Borrador_Plan_Fase6_9_23oct.md`: what was integrated, commits, D-F6-33 differences, the run's session id and results, "Dudas para PM" (dated) or "Sin dudas · 23 oct"
**Deps:** 25 (written as the day goes).

### [ ] Task 15: Criteria evidence of F5a and F6
- [ ] Declare the 3 sessions of 28–29 Sep with duplicated events (`d3f19117`, `dc28e1ea`, `fc835228`); not deleted (PM, 20 Oct)
- [ ] `Evidencia_Criterios_F5a.md` and `Evidencia_Criterios_F6.md` drafts (in `Claude outputs/`), like `Evidencia_Criterios_M2.md`: each criterion with session id, query or test
- [ ] F5a criterion 8 from Task 13 (or declared with `DEV_UNITY` per the cut rule); criterion 9 (EEG) as the EEG chat leaves it

### [ ] Task 16: Tags
- [ ] Shown to Sebas before creating: `phase5a-delivery-2026-10-23` and `m3-delivery-2026-10-23`, on the commits he names
- [ ] Pushed only with his OK

### [ ] Task 17: Change list for spec v1.4
- [ ] `Claude outputs/Cambios_Spec_v1_4.md`: every behaviour that differs from v1.3 since F5a (pre-test gate and substitution, S4 cross and eye, ABORTED rule, adaptation loop, outcomes, Learner Profile, `completed_at` at S9), with the commit or doc that backs it
- [ ] *To validate* (PM, 20 Oct): an `ON_REQUEST` Hint inside the O4 outcome window (`099690e1`, `239269fc` S7-012); exclude or mark those trials, decided with the Thu 22 data

### [ ] Task 12: Checkpoint D of the portal (only if time is left; cut first)
- [ ] Every screen V1.1–V1.11 with screenshots in light and dark
- [ ] The 5-tell audit is clean
- [ ] Full pytest, Vitest and Playwright green
- [ ] The v1 definition of done in `scope-and-roadmap.md` is met

### Checkpoint M3
- [ ] Plan_Fase6 §5 criteria 1–8 have evidence or are declared pending
- [ ] Tags created; day draft `Claude outputs/Borrador_Plan_Fase6_9_23oct.md`

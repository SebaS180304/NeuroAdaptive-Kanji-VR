# Todo: Phase 6 week → M3 (20 – 23 Oct)

Plan: `tasks/plan.md`. Previous list (portal v1): `tasks/archive/portal_v1_todo.md`.
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

### [ ] Task 11a: Frontend: the Learner Profile at the top of V1.8 (Wed 21 evening; split by Sebas, 21 Oct)
**Description:** The profile block of canvas 37: header with the scope line, *Usual performance*,
*What followed each adaptation* (at most 3 groups, "Show [n] more groups"), *Across sessions*
replacing the old V1.8 trend chart (one chart, accuracy as correct of 20), and the "No profile
yet." panel. "See [n] decisions" goes to the session's V1.5 unfiltered for now (11b adds the
filter and the cross-session list). Backend untouched.

**Acceptance:**
- [ ] Load the `research-dashboard-conventions` skill first; copy from `Contenido_UI_F-PROFILE.md` (updated 21 Oct), form from design-system.md "V1.8 Learner Profile (F-PROFILE)"; no new tokens
- [x] design-system.md without the aborted-sessions clause (canvas 39, validated 18:22, copied to the skill 21 Oct)
- [ ] Adjustments of the 21 Oct copy: global-median mark for a type with < 3 valid S6 trials; empty profile with the canvas 37 text, the same with no sessions or only aborted ones; **no mention of aborted sessions anywhere in the profile**; `UNCERTAIN` · `INCOMPLETE` reads "Can't tell: S7 ended first"
- [ ] The cases of the canvas render from real data: `DEV_UNITY` (many sessions), STATIC only, adaptive without changes, no completed session ("No profile yet.", also when every session aborted), one session; sessions before 0003 show "—", never 0
- [ ] Counts match `adaptation_decisions` / the endpoint (Vitest on the pure text helpers; Playwright on `DEV_UNITY`)
- [ ] No regression before the Thu 22 test: build, Vitest and the full Playwright suite (checkpoint-b, checkpoint-c, pre-test) green; otherwise the profile does not ship and V1.8 stays as it is
- [ ] Playwright screenshots light and dark; 5-tell audit reported

**Deps:** 9 (+ `gen:api`, done). **Files:** `features/participants/` (ParticipantView, new profile component, TrendChart), tests. **Scope:** M

### [ ] Task 11b: Frontend: cross-session decisions and the V1.5 group filter (Fri 23 if time, else week of 26 Oct)
- [ ] "See [n] decisions in [k] sessions" disclosure list (canvas 38), newest first, "Session [#] ([date])"
- [ ] V1.5 `?group=<key>`: notice, "Back to the profile", "Show all decisions"; reload and back keep it
- [ ] V1.5 and V1.6: cause "Impulsive" reads "Quick errors"
- [ ] Verified with the Thu 22 participant (one session); F-PROFILE §5 closed

**Deps:** 11a. Not needed for M3 (criterion 4b is met by 11a).

### [x] Task 10b: Day draft
- [x] `Claude outputs/Borrador_Plan_Fase6_9_21oct.md`: §9 Wed 21 lines (`completed_at` commit, Learner Profile v1 backend with commits, `DEV_UNITY` profile summary, findings)

### Checkpoint Wed 21
- [x] Full pytest green; `graphify update .`
- [x] `DEV_UNITY` profile computed from its 5 completed adaptive sessions, `--check` clean
- [x] Day draft handed to Sebas
- [x] Open question 5 of `plan.md` answered by Sebas (or the default recorded); question 6 answered 21 Oct (`ABORTED` never counts). Q5 answered 21 Oct: backfilled, 16 sessions (`database/backfill_completed_at.sql`)

---

## Thu 22 Oct: phase test

### [ ] Task 13: Phase test with a participant with no Japanese
- [ ] Before: consent text ready (PM), participant booked (Sebas), backend restarted and `/health/db` OK
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

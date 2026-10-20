# Todo: Phase 6 week → M3 (20 – 23 Oct)

Plan: `tasks/plan.md`. Previous list (portal v1): `tasks/archive/portal_v1_todo.md`.
Every commit: message file in Downloads, shown to Sebas first, one change each.

---

## Tue 20 Oct: headset

Quest 2 via Link in the Editor. Inspector changes on `SessionBootstrap`
(`devParticipantCode`, `newSessionKanjiSet`, `condition`) are temporary: revert them
after each run. Never save the scene during Play. Restart the backend only between runs,
never with `--reload`, never with the headset on.

### [ ] Task 1: Run 1, set B with a substitution (old Tasks 1.8, 1.9 for B, 1.10)
- [ ] Portal `/pretest`: register `TEST_VR_B` with consent; answer "Yes" with the right
      reading on one set B kanji (on 18 Oct, 山 → 口), "No" on the rest. Note the substitute
- [ ] `SessionBootstrap`: `devParticipantCode = TEST_VR_B`, `newSessionKanjiSet = B`; Play
      through S5–S8 (low `baselineTimeScale` is fine)
- [ ] S5–S8 show the substitute in the original's place
- [ ] S5: the 4 kept B kanji log "authored" and assemble from real strokes; every group can
      be grasped. A first-choice substitute (口 for 山) also logs "authored"; any other
      substitute logs the placeholder warning, as expected

**Verify (DB, `<id>` from the Unity log):**
- [ ] `select kanji_id, segment_count, segments_authored from assemblies where session_id = '<id>';` → `true` for every kanji, the substitute included if it is one of the 10 first-choice reserve kanji
- [ ] `select block_state, kanji_id, count(*) from trials where session_id = '<id>' group by 1, 2 order by 1, 2;` → the substitute appears and its original never does

**Deps:** none. **Scope:** XS (no code)

### Task 2: Run 2, set C: folded into Task 3 (Sebas, 20 Oct)
Run 3 is set C with `DEV_UNITY` to S9, so its S5 checks cover run 2.

### [ ] Task 3: Run 3, `BEHAVIOR_ADAPTIVE` complete S1 → S9, set C (run A of `Guion_Pasada_Visor_F5a.md`; covers run 2)
**Description:** First full adaptive session with the weekend changes: pre-test gate and
effective set, S4 with fixation cross and closing eye, real segments for B and C.
- Setup: `condition = BEHAVIOR_ADAPTIVE`, `devParticipantCode = DEV_UNITY`, set C
  (Sebas, 20 Oct), visit 1, `baselineTimeScale = 1`. Step 1 of the script (O4 commit) is stale: skip it.
- No headset off and no chat from S1 to S9. S7 follows the script's table (S7-004…006
  slow errors → LAL up; 007…009 no Hint; then normal).

**Acceptance:**
- [ ] S4 shows the cross (eyes open) and the eye that closes once (eyes closed)
- [ ] S5 (run 2, old Task 1.9 for C): all 5 C kanji log "authored"; every group can be grasped (花's three pieces, 足's foot); `assemblies` query as in Task 1 → `true` for all 5
- [ ] The session reaches S9 and its status is `COMPLETED`
- [ ] `va <id>` (`database/verify_adaptation.sql`): §1 20 answered in S7, 20 decisions, changes all `APPLIED`, 0 `SKIPPED`; §2–§5, §7, §8 empty; §6 p95 latency tens of ms at most; §9 every change with an outcome
- [ ] `verify_projection.sql` clean for the session; `check_loop.sql` and `python -m app.adaptation.replay <id>` give the live decisions and outcomes
- [ ] Anything off-script recorded with its trial id (a finding, not a fix)

**Verify:** outputs in a `.txt` in Downloads; session visible in the portal (V1.2–V1.6).

**Deps:** none (after Task 1 or before it, as Sebas prefers). **Scope:** XS

### Checkpoint B: the pre-test feeds the VR loop
- [ ] A participant registered and pre-tested in the portal runs a Unity session with their effective set (Task 1)
- [ ] Sets B and C assemble from real segments (Tasks 1 and 3)
- [ ] Tick old Tasks 1.8, 1.9, 1.10 in `tasks/archive/portal_v1_todo.md`; delete `TEST_VR_B` with Sebas's OK

### [ ] Task 4: Commit the CLAUDE.md change
- [ ] Only `CLAUDE.md` staged (the XR Origin prefab change is not part of it)
- [ ] Message shown to Sebas: `docs(claude): point to the Phase 6 plan`
- [ ] Separate commit, also shown: `docs(tasks): plan the Phase 6 week to M3` (this plan, the archived portal plan)

**Deps:** none. **Scope:** XS

### [ ] Task 5: Day draft
- [ ] `Claude outputs/Borrador_Plan_Fase6_9_20oct.md`: §9 Tue 20 lines (Checkpoint B, run 3 id and result, findings)

### Checkpoint Tue 20
- [ ] Checkpoint B ✅; run 3 complete and clean in `verify_adaptation`
- [ ] Day draft handed to Sebas

---

## Wed 21 Oct: Learner Profile v1 (backend)

Branch `phase/6-learner-profile` from `phase/7-research-dashboard` (Plan_Fase6 header).

### [ ] Task 6: Migration 0007 `learner_profiles`
**Description:** Table as in `plan.md` (PK `participant_id` FK `ON DELETE CASCADE` +
`profile_version`, option A; `computed_at`, `session_ids UUID[]`, `profile JSONB`). Same pattern as
0003–0006: SQL in `alembic/versions/sql/0007_learner_profile_{up,down}.sql`.

**Acceptance:**
- [ ] up, down, up again on the dev DB; `database/schema.sql` and `ERD.md` cover 0007
- [ ] The `_clean_test_participants` fixture still deletes test participants (cascade)

**Verify:** `alembic upgrade head`; full pytest green.
**Deps:** none. **Files:** migration + 2 SQL, `models/` (if an ORM model is needed; `text()` may be enough), `database/schema.sql`, `database/ERD.md`. **Scope:** S

### [ ] Task 7: Calculation and rebuild
**Description:** `app/adaptation/learner_profile.py`: `compute(db, participant_id)` builds
the three parts (calibrations from events via `build_trials` + `build_profile`;
adaptations grouped by action, dimension, direction, cause with outcome counts; trend over
completed sessions) and upserts the row. CLI `--all` and `--check`.

**Acceptance:**
- [ ] On the 4 adaptive `DEV_UNITY` sessions (`099690e1`, `d392fd25`, `a0c65228`, `a5748886`) + run 3: each calibration equals the S6 profile in that session's `ADAPTATION_DECISION` context; adaptation counts equal a direct `GROUP BY` on `adaptation_decisions`; trend equals V1.8's numbers (pytest)
- [ ] STATIC sessions give calibrations and trend, and no adaptation groups
- [ ] An `ABORTED` session appears in no part (Sebas, 20 Oct); a NULL outcome counts as "not recorded"
- [ ] `--all --check` after `--all` prints no differences

**Verify:** `pytest tests/test_learner_profile.py`; the CLI in the backend container.
**Deps:** 6. **Files:** `app/adaptation/learner_profile.py`, `tests/test_learner_profile.py`. **Scope:** M

### [ ] Task 8: Compute when a session completes (S9)
**Description:** After `update_session_state` commits a `COMPLETED` status, compute that
participant. No hook on abort: aborted sessions do not count. Errors are logged and never
fail the PATCH.

**Acceptance:**
- [ ] PATCH to S9 → the participant's row includes the session (pytest)
- [ ] A late S9 on an `ABORTED` session → the session is not in the row
- [ ] A forced error in `compute` → the PATCH still returns 200 and the state is saved

**Verify:** pytest. **Deps:** 7. **Files:** `routes/sessions.py`, tests. **Scope:** S

### [ ] Task 9: Endpoint `GET /research/participants/{id}/profile`
**Acceptance:**
- [ ] Returns the stored row through a Pydantic schema; 404 unknown participant; `profile: null` with no row
- [ ] Read-only (no compute on read); the data contract in the skill lists it

**Verify:** `pytest tests/test_research_api.py`. **Deps:** 7. **Files:** `routes/research.py`, `schemas/research.py`, skill `data-contract.md`, test. **Scope:** S

### [ ] Task 10: D-F6-1 test: the profile does not change how a session starts
**Acceptance:**
- [ ] Two pre-tested participants, one with a stored profile (with an `OVERLOADED` → LAL HIGH history) and one without: `POST /sessions` gives the same fields (condition, kanji set and items, no level fields), and `SessionAdaptationState` enters S7 with `HOME_LEVEL` for both
- [ ] A comment in the test cites D-F6-1 ("until after the pilot")

**Verify:** pytest. **Deps:** 6, 8. **Files:** `tests/test_learner_profile.py`. **Scope:** XS

### [ ] Task 11: Frontend: profile at the top of the Participant View (BLOCKED on the mockup)
- [ ] Starts only when Sebas validates the mockup (web design + UI/UX chats). No visual design here
- [ ] Load the `research-dashboard-conventions` skill first; replaces the reserved slot in V1.8

### Checkpoint Wed 21
- [ ] Full pytest green; `graphify update .`
- [ ] `DEV_UNITY` profile computed, `--check` clean
- [ ] Day draft `Claude outputs/Borrador_Plan_Fase6_9_21oct.md`

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
- [ ] `Evidencia_Criterios_F5a.md` and `Evidencia_Criterios_F6.md` drafts (in `Claude outputs/`), like `Evidencia_Criterios_M2.md`: each criterion with session id, query or test
- [ ] F5a criterion 8 from Task 13 (or declared with `DEV_UNITY` per the cut rule); criterion 9 (EEG) as the EEG chat leaves it

### [ ] Task 16: Tags
- [ ] Shown to Sebas before creating: `phase5a-delivery-2026-10-23` and `m3-delivery-2026-10-23`, on the commits he names
- [ ] Pushed only with his OK

### [ ] Task 17: Change list for spec v1.4
- [ ] `Claude outputs/Cambios_Spec_v1_4.md`: every behaviour that differs from v1.3 since F5a (pre-test gate and substitution, S4 cross and eye, ABORTED rule, adaptation loop, outcomes, Learner Profile), with the commit or doc that backs it

### [ ] Task 12: Checkpoint D of the portal (only if time is left; cut first)
- [ ] Every screen V1.1–V1.11 with screenshots in light and dark
- [ ] The 5-tell audit is clean
- [ ] Full pytest, Vitest and Playwright green
- [ ] The v1 definition of done in `scope-and-roadmap.md` is met

### Checkpoint M3
- [ ] Plan_Fase6 §5 criteria 1–8 have evidence or are declared pending
- [ ] Tags created; day draft `Claude outputs/Borrador_Plan_Fase6_9_23oct.md`

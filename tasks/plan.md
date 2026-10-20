# Implementation Plan: Phase 6 week → M3 (Tue 20 – Fri 23 Oct 2026)

Written 20 Oct 2026. Replaces the Research Web Portal v1 plan, archived in
`tasks/archive/portal_v1_{plan,todo}.md`. Its open items are carried over unchanged:
the headset runs of Tasks 1.8–1.10 and Checkpoint B (here Task 1, and Task 3, which absorbs run 2), and
Checkpoint D (here Task 12, the first thing to cut).

## Sources of truth
- `Claude outputs/docs_proyecto/Plan_Fase6.md`: §0 F5a close, §3 days, §4 Learner
  Profile decisions D-F6-1 – D-F6-4 (approved by Sebas, 20 Oct), §5 criteria, §9 log.
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
  `profile JSONB`. Overwritten at each completed session; a later `v2` (after the pilot,
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
  Why JSONB and no extra tables: every part is derived and rebuildable; the table only
  stores the last computed result so the portal does not recompute on every read.
- **Calculation in Python, reusing the estimator code.** `app/adaptation/learner_profile.py`
  rebuilds each session's S6 profile from `session_events` with `build_trials` +
  `build_profile` (as `SessionAdaptationState` and `replay.py` do) and reads parts 2 and
  3 from the schema with `text()`. Nothing new in the estimator.
- **Only sessions `COMPLETED` up to S9 count (Sebas, 20 Oct).** Aborted sessions are
  left out of all three parts: calibration, adaptations and trend.
- **When it runs (D-F6-3).** Because an abort cannot change the profile, it is computed
  only when a session completes: Unity's `PATCH /sessions/{id}/state` with S9
  (`sessions.py` `update_session_state`), after the commit. A late S9 on an `ABORTED`
  session keeps it `ABORTED`, so it is not counted. A failure in the profile is logged and
  never fails the PATCH (losing the state update for a derived table would be the wrong
  trade); `--all` rebuilds anything a failure missed.
- **Rebuild:** `python -m app.adaptation.learner_profile --all [--check]` recomputes from
  events and schema; `--check` compares with the stored rows and prints differences
  (expected: none). This is the proof of "reconstructible".
- **D-F6-1: the profile never changes how a session starts.** The starting levels come
  from Unity (`SessionBootstrap`) and `rules.initial_state` (HOME_LEVEL); nothing reads
  `learner_profiles` on that path. A test shows it: a participant with a stored profile
  gets the same session response and the same S7 initial state as one without.
- **Endpoint:** `GET /research/participants/{id}/profile` (read-only, `/research` router,
  Pydantic schema in `schemas/research.py`). 404 for an unknown participant; `null`
  profile when there is none yet. The portal screen waits for the mockup (D-F6-4).

## Dependency graph
```
T1 run 1 (B + substitution) ─┐
T3 run 3 (adaptive S1→S9, set C; covers run 2) ┴─► Checkpoint B, verify_adaptation clean ──► (fresh adaptive session for T7/T8)
T4 CLAUDE.md commit (independent)
T6 migration 0007 ─► T7 calculation + rebuild ─► T8 close hooks ─► T9 endpoint
                                     └──────────► T10 D-F6-1 test
mockup validated by Sebas (design chats) ─► T11 frontend (blocked)
consent text (PM) + participant ─► T13 phase test ─► T14 findings
T3 + T13 ─► T15 evidence ─► T16 tags ─► T17 spec v1.4 change list
T12 Checkpoint D (only if time is left)
```

## Phases
- **Tue 20 (headset):** Tasks 1–5 → Checkpoint Tue.
- **Wed 21 (backend):** Tasks 6–10 → Checkpoint Wed. Task 11 starts only with the
  validated mockup.
- **Thu 22 (phase test):** Tasks 13–14 → Checkpoint Thu.
- **Fri 23 (M3):** Tasks 15–17 (+ 12 if time) → Checkpoint M3.

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
| The profile hook slows or breaks the S9 PATCH | Med | Runs after the commit, wrapped in try/except, logged |
| The participant's consent text is not ready Thu 22 | High | PM drafts it today (Plan_Fase6 §7); registration requires it since 17 Oct |
| The mockup is not validated by Fri 23 | Med | Criterion 4b is declared pending in the M3 note; the endpoint is ready |

## Open questions
1. ~~"Per participant **and version**" (D-F6-2)~~ Option A: one row per participant and
   format version, overwritten (Sebas, 20 Oct).
2. ~~Do `ABORTED` sessions count?~~ No, in no part (Sebas, 20 Oct).
3. Who is the participant on Thu 22, and at what time (Sebas).
4. ~~Set for run 3~~ Set C (Sebas, 20 Oct).

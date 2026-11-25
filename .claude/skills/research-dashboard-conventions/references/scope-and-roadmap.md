# v1 scope and roadmap

References: project proposal §5.6 (Participant, Session and Experiment View;
timelines and outcomes; comparison of conditions), milestone **M4 · Nov 20 2026**
and `Plan_Fases_Replan_7oct.md` (Sebas's decision of Oct 7).

## Calendar (Oct 7 replan)

| Block | Dates | What it means for the dashboard |
| --- | --- | --- |
| F6 behavioral | Oct 19–23 | Outcome of each adaptation and Learner Profile v1. The replan asks to **leave the SQL views ready from F6 on** |
| F4 · EEG with AURA | Oct 26 – Nov 13 | EEG is **not** part of the dashboard for now (decided Oct 16) |
| **F7 · Dashboard + integration** | **Nov 16–20 (1 week)** | Dashboard build. It is the schedule's **only buffer**: if F4 slips, it shrinks to the Session View. Decided on **Fri Nov 6** |
| M4 | Nov 20 | Milestone review |

Design (mockups in Claude Design) and the backend read router can move ahead of
F7.

## Fixed assumptions (decided)

- Runs only on the lab machine.
- **Post-session** review; no live monitoring.
- Read-only.
- Custom app (React), not Metabase/Grafana.
- No authentication while it stays local.

## Data that exists in the repo today (Oct 16)

| Data | Where | Since |
| --- | --- | --- |
| States, blocks, plan, trials, hints, environment, peripherals, head-away, S5/S2 | Migration `0002` | F3 |
| `trial_timeline()` with adaptation and distractor columns | Migration `0003` (redefined) | F5a |
| Distractor interactions (`DWELL`, `ORIENTING`) | `distractor_interactions` (`0003`) | F5a, events since Oct 6 |
| Adaptation decisions (state, cause, confidence, action, explanation, cooldown) | `adaptation_decisions` (`0003`) | F5a |
| What Unity did with each decision | `adaptation_applications`, `v_adaptations` (`0003`) | F5a |
| Outcome of each adaptation (O4) | `adaptation_decisions.outcome` (`0003`) | F6, filled by `ADAPTATION_OUTCOME` |
| Kanji pre-test and per-participant substitutions | `kanji_pretest_responses`, `kanji_substitutions`, `participants.pretest_completed_at` (`0004`) | Oct 16 |
| Abandoned sessions set to `ABORTED` | `abort_stale_sessions()` (`0005`) | Oct 17 |
| Session overview, projection errors with session time, verify checks as functions | `v_session_overview`, `v_projection_errors`, `verify_*_fn()` (`0006`) | Oct 17 |
| S6 calibration profile | Persisted per completed session in `learner_profiles.profile` → `calibrations` (`0007`), rebuilt from `session_events` (D-F6-2, D-F6-3) | Oct 21 |
| Cross-session Learner Profile v1 | `learner_profiles` (`0007`): calibrations, adaptation groups with outcomes, S7 trend; COMPLETED sessions only (D-F6-2); `GET /research/participants/{id}/profile` | Oct 21 |
| EEG | Does not exist yet | F4 |
| HCI self-report (S10) | No table | No date |

## In v1

| # | Screen / function | Shows | Data |
| --- | --- | --- | --- |
| V1.1 | Session list | Table filterable by participant (`external_code`), condition, date and `status` (`CREATED`, `IN_PROGRESS`, `COMPLETED`, `ABORTED`), plus "not projected". Quality indicator | `experiment_sessions`, `participants`, count of `projection_errors` |
| V1.2 | Session View · Summary | Total and per-state duration, accuracy, mean RT and CV, hints, head-away, number of adaptations by action and by outcome | `session_states`, `trial_timeline()`, `v_adaptations` |
| V1.3 | Session View · Timeline | Lanes over `session_elapsed_ms` (order in `visualization-rules.md`), with **real adaptations and distractors** | see `data-contract.md` |
| V1.4 | Session View · Trials | `trial_timeline()` rows, including the decision columns (`learner_state`, `decision_action`, `decision_reason`, `adaptation_result`) | `trial_timeline(session_id)` |
| V1.5 | Session View · Adaptations | One row per decision with a change (optionally `NO_CHANGE`): state, cause, confidence, from → to, explanation, what Unity did (`APPLIED` / `SKIPPED` + reason), cooldown and outcome | `v_adaptations`, `adaptation_decisions` |
| V1.6 | Session View · Plan vs execution | Planned against executed trials per block | `planned_trials` vs `trials` |
| V1.7 | Data quality | Open `projection_errors` by code and the result of the `verify_*.sql` queries | `v_projection_errors`, the five `verify_*_fn()` (`0006`) |
| V1.8 | Minimal Participant View | Sessions in order, accuracy and RT trend, pre-test status, substitutions and flagged kanji (the only place they are shown) | `experiment_sessions`, `trial_timeline()`, `kanji_substitutions` |
| V1.9 | CSV export | Trials (`trial_timeline`) and adaptations of one session | same endpoints |
| V1.10 | Kanji pre-test (capture) | Runs the spec §13.2 pre-test with the participant before their first session. **The only screen that writes** (see below) | `/participants/{id}/pretest` (existing, `0004`) |
| V1.11 | Participant list | Added by Sebas, Oct 17. Reached from the rail's "Participants" item; each code opens V1.8. One row per participant: code and registration date, pre-test status (not started / in progress with n answered / completed), number of sessions and the conditions used, last session date and its accuracy, and notes for the researcher: previous Japanese study reported (spec §13.1) and kanji kept with no substitute. Filters: code, pre-test status, condition, only with notes | `participants` (`created_at`, `previous_japanese_experience`, `pretest_completed_at`), `kanji_pretest_responses` (count), `experiment_sessions`, `trial_timeline()`, `kanji_substitutions` (`substitute_kanji_id` NULL) |

**Status (Oct 20):** every screen V1.1–V1.11 is built (`tasks/todo.md`, Phases 1–3).
Checkpoint C passed on Oct 19 on session `099690e1`; Checkpoint D (v1 done) is next.

**Definition of done:** with a real F5a `BEHAVIOR_ADAPTIVE` session, the screen
reconstructs what happened, in what order, with which environment, and what the
system decided and why, without opening pgAdmin. What the UI shows matches
`verify_projection.sql` and `verify_adaptation.sql`.

### V1.10 · Kanji pre-test (added Oct 16 by Sebas; function only, the UI/UX chat designs it)

**Objective.** Before a participant's first session, the researcher and the
participant sit at the lab PC and go through the 15 kanji of sets A, B and C. The
test finds the kanji the participant already knows, and the backend swaps each one
for the reserve kanji that best fits its set. Until the pre-test is complete the
backend refuses to create any session for that participant (409), and Unity's error
message points to this screen. So the screen is needed **before the pilot**, not
only in F7.

**Flow.**
1. **Pick or register the participant.** The list shows each participant's
   `external_code` and pre-test status:
   - not started;
   - in progress, with the number answered;
   - completed, with the date.

   A completed pre-test opens its result read-only. It cannot be redone or edited.

   **New participant** (decided by Sebas, Oct 16; to be confirmed with MIRAI):
   1. **The researcher** enters the `external_code` from their own list (the link
      between a code and a person stays outside the system) and confirms that
      consent was obtained. Without consent, nothing goes further.
   2. **The participant** answers the spec §13.1 screening questions about
      themselves at the keyboard:
      - age range;
      - previous Japanese study;
      - previous kanji study;
      - previous VR use;
      - self-rated attention difficulty, which is optional.

      These are self-report, so the wording is plain and non-clinical. Options
      approved by Sebas on Oct 17 (`tasks/plan.md`); each list is a fixed
      `Literal` set in the API schema:

      | Question (participant-facing) | Options shown | Stored value |
      | --- | --- | --- |
      | How old are you? | 18–24 · 25–34 · 35–44 · 45 or older · Prefer not to answer | `age_range`: `18-24`, `25-34`, `35-44`, `45+`, NULL |
      | Have you studied Japanese before (classes, courses or self-study)? | Yes · No · Prefer not to answer | `previous_japanese_experience`: true / false / NULL |
      | Have you studied kanji before? | Yes · No · Prefer not to answer | `previous_kanji_experience` |
      | Have you used a VR headset before? | Yes · No · Prefer not to answer | `previous_vr_experience` |
      | How often is it hard for you to keep your attention on study tasks? *(optional)* | Never · Rarely · Sometimes · Often · Very often · Prefer not to answer | `self_rated_attention_difficulty`: `NEVER`, `RARELY`, `SOMETIMES`, `OFTEN`, `VERY_OFTEN`, NULL |

      The attention question has 5 options; the mockup shows 4 placeholder pills,
      so the pill group gets one more. How the participant feels before a session
      (spec §13.1, "alertness/fatigue") is asked per session, not here.
   3. Both parts are sent as **one** `POST /participants`. There is no edit
      afterwards.
   4. If the participant reports previous Japanese study, or prefers not to
      answer, the researcher sees a notice (inclusion criterion "no previous
      study of Japanese", spec §13.1, **accepted** by MIRAI on Oct 9; worded "not
      reported" for Prefer not to answer) and decides whether to continue to the
      pre-test.
2. **One kanji at a time.** The participant sees the character and answers "Do you
   know this kanji?" with **No / Not sure / Yes**.
   - **No:** saved as unknown, and the next kanji appears.
   - **Not sure / Yes:** the participant types the **reading** (hiragana, katakana
     or romaji) and the **meaning** (English). **Check** shows the automatic result
     for each field (correct or incorrect). The researcher can flip either result,
     then **Save** moves on.
3. **The backend always decides the next kanji.** It may be a reserve kanji that is
   being tried as a substitute. The screen shows only the character: no set name and
   no "substitute" label, because the participant is looking at the same screen.
4. **Progress** is the number of kanji answered. The total is not known in advance,
   because every kanji the participant knows adds at least one more item, so do not
   show "n of 15".
5. **When it ends**, a summary shows the completion time and the number of kanji
   answered, with a link to the participant's page. It does **not** show
   substitutions or flagged kanji (Sebas, Oct 16, 23:57): the participant is still
   looking at this screen. Those appear only in Participant View (V1.8), where the
   researcher checks flagged kanji against MIRAI's inclusion criterion, spec §13.1.

**Rules.**
- **Never show the correct reading or meaning**, on any screen, the summary
  included. A partially known kanji stays in the study set, and showing its answer
  would teach it.
- Classification wording: Unknown / Partially known / Known. No clinical language.
  Participants are identified only by `external_code`.
- The whole screen works with the keyboard alone, and every control has a label.
  Correct and incorrect are never shown by colour alone.

**States the design must cover.**
- Loading, and the backend unreachable.
- Participant not found.
- `external_code` already exists (409 on create).
- Consent not confirmed: registration and the pre-test are blocked.
- 409, from a second tab or a double submit: reload the state, continue, and show a
  short notice.
- A page reload in the middle of a test resumes at the right kanji.
- 422: Not sure / Yes saved without both results.
- Completed.

**Data (existing, tested Oct 16).**
- `GET /participants` returns the list.
- `POST /participants` takes `{external_code, consent_obtained, age_range,
  previous_japanese_experience, previous_kanji_experience, previous_vr_experience,
  self_rated_attention_difficulty}` and answers 409 if the code exists. Backend work is
  pending: it must set `consent_obtained_at`, refuse the pre-test without consent, and
  give fixed answer lists for `age_range` and `self_rated_attention_difficulty`.
- `GET /participants/{id}/pretest` returns:
  - `completed`, `completed_at`, `answered`;
  - `next`: `{kanji_id, kanji}`, or `null` when done;
  - `substitutions`: `[{set, original, substitute}]`;
  - `flagged`: `[{set, original}]`.
- `POST .../pretest/check` takes `{kanji_id, typed_reading, typed_meaning}` and
  returns `{reading_correct, meaning_correct}`. Nothing is stored.
- `POST .../pretest/responses` takes `{kanji_id, self_report: NO|UNSURE|YES,
  typed_reading, typed_meaning, reading_correct, meaning_correct}` and returns the
  new state. It answers 409 if the kanji is not the expected next one or the
  pre-test is completed, and 422 if fields are missing.

**Exception to read-only (decided by Sebas, Oct 16).** This screen writes, through
the existing `/participants/{id}/pretest` routes. It never uses `/research`, which
stays `GET`-only.

**Hook.** Route `/pretest`. Participant View (V1.8) links to it while
`pretest_completed_at` is null.

**Out of scope.**
- Editing or redoing a completed pre-test.
- Reviewing each answer (typed text, auto result vs researcher's result). That is
  F-PRETEST.

**Open.**
- MIRAI confirms who records consent and how.
- ~~The answer options for age range and attention difficulty.~~ Decided by Sebas on
  Oct 17 (`tasks/plan.md`, "Registration options").

**Done when.** A Playwright run of a `TEST_PRETEST` participant goes end to end, and
`kanji_pretest_responses` and `kanji_substitutions` match what was answered.

**No EEG in v1** (decided Oct 16): there is no EEG lane, not even a reserved one
that implies a date. The timeline is built so a lane can be added later without
reworking the others.

## Outside v1 (open path)

Each row becomes a `feature-spec` when the PM chat schedules it.
Statuses: `Idea → Planned → Design validated → In dev → Done`.

| ID | Feature | Depends on | Hook in v1 | Status |
| --- | --- | --- | --- | --- |
| F-EXPERIMENT | Experiment View: Static vs Behavior-Adaptive vs Multimodal-Adaptive | Pilot data (F8). **Decided Oct 16: after the pilot** | Condition filter in the session list | Idea |
| F-EEG | EEG lane: windows, GOOD / ACCEPTABLE / POOR quality, exclusions; normalized indices | F4 (AURA). **Decided Oct 16: not yet** | Timeline accepts new lanes | Idea |
| F-MULTI | Multimodal decisions: EEG contribution to confidence and behavioral fallback | F4 S3 + F-EEG | Source column in V1.5 | Idea |
| F-PROFILE | Cross-session Learner Profile: dimensions, evidence, confidence, history. Only `COMPLETED` sessions count; an `ABORTED` session is in no part, even if it reached S6 or S7 (Sebas, 21 Oct) | F6 (Oct 19–23) | Top of the Participant View (D-F6-4, 20 Oct) | In progress: Task 11a done (`983aaa7`), 11a-fix and 11b pending (D-F6-7, D-F6-11) |
| F-CALIB | Session S6 calibration profile (`rt_ref`, `acc_ref`, `reliability`…) in the Session View | Data persisted with the Learner Profile (`0007`); a per-session read is still to add | Reserved card in the summary | Idea |
| F-PRETEST | Pre-test detail (answers, auto vs researcher review) | Data already exists (`0004`) | Participant View | Idea |
| F-HCI | HCI self-report (S10, 7 items) | New table | Reserved section in the summary | Idea |
| F-CONFIG | Experimental configuration of the session | `session_config_snapshots` (already exists) | Summary | Idea |
| F-LIVE | Live monitoring | Mirai's decision (today: no) | None | Idea |
| F-AUTH | Authentication / leaving the lab machine | Mirai's decision (today: no) | None | Idea |

Rule: nothing in this table is implemented without its `feature-spec` and a
validated design. v1 only leaves the visible reserved slot where the table says
so; F-PROFILE is the exception, built in F6 (D-F6-4).

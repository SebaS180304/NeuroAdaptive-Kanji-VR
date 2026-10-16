# Todo: Research Web Portal v1

Plan: `tasks/plan.md`. One change per commit, in English. Show Sebas each message first.
Never on main. Branches: Phase 0 and Task 1.2 go on `feature/kanji-pretest`; from Task
1.3 on, `phase/7-research-dashboard`, created from its tip. Dashboard commits use scope `dashboard`; read-router commits use scope
`research-api`. After code changes, run `graphify update .`. Restart the backend only
between headset sessions.

Each screen task ends with these checks:
- [ ] Playwright screenshot against its artboard, light and dark
- [ ] Keyboard-only pass
- [ ] NULL shown as `—` with a tooltip, never 0
- [ ] No clinical wording
- [ ] The 5-tell audit table, reported to Sebas

---

## Phase 0: Data foundation

### [ ] Task 0.1: Backup and clean-up
**Description:**
- `pg_dump` to `database/backups/` (gitignored).
- In one transaction, delete the 23 sessions created before 2026-09-15 12:32 +09:00 (all
  `CREATED`, 323 events), then the participants left with no sessions, no pre-test
  answers and no consent, except `DEV_UNITY`.
- Mark the open `DUPLICATE` errors of `dc28e1ea`, `fc835228` and `d3f19117` as resolved,
  with the note "several Editor runs under one id; first run projected; see
  Plan_Fase3.md".
- Commit the script as `database/cleanup_2026-10-17.sql`.

**Acceptance:**
- [x] Sebas approved the clean-up split (17 Oct)
- [ ] Sebas approved the final SQL and the counts before it ran
- [ ] No session older than the scene remains, and `verify_projection.sql` passes
- [ ] Open projection errors: 0 from the 3 evidence sessions, and the rest listed

**Verify:** the before/after counts are printed by the script itself; restoring the dump
into a scratch database works.

**Deps:** none. **Scope:** S

### [ ] Task 0.2: Abandoned sessions become ABORTED (migration 0005)
**Description:**
- SQL function `abort_stale_sessions(p_idle interval DEFAULT '30 minutes') RETURNS int`.
- The backend lifespan runs it at startup and then every 5 min, and logs the count when
  it is above 0. `shortcut:` an in-process loop instead of `pg_cron`.
- Write the up and down SQL.

**Acceptance:**
- [ ] An `IN_PROGRESS` session with its last event more than 30 min ago → `ABORTED`; one with a recent event is untouched
- [ ] `COMPLETED` and `CREATED` sessions are never touched
- [ ] A later `PATCH .../state` does not revert `ABORTED` (existing rule, now tested)
- [ ] The 31 stale `IN_PROGRESS` sessions in the dev DB become `ABORTED` on the first run

**Verify:** pytest with backdated `server_received_at`; migration up / down / up.

**Deps:** 0.1. **Scope:** S

### [ ] Task 0.3: Read-side SQL for the portal (migration 0006)
**Description:**
- `v_session_overview`: one row per session with:
  - `projected` (events present but no `session_states` rows = not projected; no events
    at all = no data);
  - event count, trial count, decision count;
  - accuracy over answered S5–S8 trials;
  - open error count.
- `v_projection_errors`: errors plus `session_elapsed_ms`, read from the event payload in
  SQL.
- `verify_projection_fn()`, `verify_adaptation_fn()`, `verify_trials_fn()`,
  `verify_assembly_fn()` and `verify_reproducibility_fn()`. Each returns `(session_id,
  check, detail)` rows, one per discrepancy, ported from the `.sql` scripts and parameterised
  by session where the script was hard-coded. The scripts stay as they are for `psql` use.
- Per-session criterion for the `COALESCE(…, 0)` columns: was the event type ever
  recorded in that session? Exposed as booleans in the overview view.

**Acceptance:**
- [ ] Each function returns 0 rows on a session that its `.sql` script passes, and finds a seeded discrepancy
- [ ] The overview matches a hand query on 3 sessions (one STATIC, one BEHAVIOR_ADAPTIVE, one aborted)

**Verify:** `pytest backend/tests/test_research_sql.py`; up / down / up.

**Deps:** 0.1. **Scope:** M

### Checkpoint 0
- [ ] Full `pytest` green; migrations clean; show Sebas the clean-up counts and the new statuses

---

## Phase 1: Pre-test, end to end (before the pilot)

### [ ] Task 1.1: Registration options (approved 17 Oct)
**Description:** Sebas approved the table in `plan.md`. Record it in the skill's
`scope-and-roadmap.md` §V1.10. Send the design chat a copy-only note: the
attention question has 5 options, and the inclusion notice says "accepted".

**Acceptance:**
- [x] Sebas approved the options (17 Oct)
- [ ] Options recorded in `scope-and-roadmap.md`; note sent to the design chat

**Deps:** none. **Scope:** XS

### [ ] Task 1.2: Registration rules in the backend (was Task 3b)
**Description:**
- `POST /participants` sets `consent_obtained_at` when consent is true.
- The pre-test POST routes return 409 "consent not recorded" without consent.
- The options from 1.1 become `Literal`s in the schema.
- Callers send consent: `test_pretest_api._participant` and `SessionBootstrap`'s
  dev-participant POST.
- `DEV_UNITY` gets consent with one `UPDATE`, shown first.

**Acceptance:**
- [ ] Created with consent → `consent_obtained_at` is set; without → NULL
- [ ] A pre-test answer without consent → 409, nothing stored
- [ ] An unknown `age_range` → 422
- [ ] Existing tests pass

**Verify:** `docker compose run --rm backend pytest -q`

**Deps:** 1.1. **Scope:** S

### [ ] Task 1.3: Dashboard scaffold and app shell
**Description:**
- `dashboard/`: Vite, React, TS strict, Tailwind, `shadcn init`, TanStack Query, React
  Router and the Fontsource packages.
- `styles/tokens.css` holds the exact values from `design-system.md` (light, dark,
  `prefers-color-scheme`). shadcn's variables are mapped onto the tokens; radius by role.
- `npm run gen:api` (`openapi-typescript`).
- Vite on `127.0.0.1:5173`, with a proxy to `:8000`.
- The shell: a 240 px rail (Sessions, Participants, Pre-test, Data quality), a 16-column
  grid, and routes for every screen that render reserved placeholders.
- Vitest, Testing Library and the Playwright config.
- Delete the root `package.json`, `package-lock.json` and `node_modules/`. Commit
  `.mcp.json`. Add Fontsource to the skill's stack table.

**Acceptance:**
- [ ] `npm run dev` binds to 127.0.0.1 only; no outbound request in the Playwright network log (fonts included)
- [ ] The tokens page renders both themes; contrast pairs as measured in `design-system.md`
- [ ] Generated types include the pretest and participant schemas
- [ ] 5-tell audit: none found

**Verify:** `npm run test`, `npx playwright test` (smoke); a screenshot of the rail against the *Session list* artboard.

**Deps:** none (do before 1.4). First task on `phase/7-research-dashboard`. **Scope:** M

### [ ] Task 1.4: Participant list: `/research/participants` and V1.11
**Description:**
- **Endpoint:** create `research.py` with the first `GET`. Per participant: code,
  `created_at`, pre-test status and `answered`, session count, conditions, last session
  date and accuracy (`null` without answered trials), `previous_japanese_experience`, and
  `flagged_count`.
- **Screen:** V1.11 with:
  - the status bar;
  - filters for code, pre-test status, condition, and "only with notes";
  - the notes column ("Previous Japanese study reported", "Kanji kept with no substitute").

**Acceptance:**
- [ ] The figures match SQL for 3 participants
- [ ] A code opens `/participants/:id` (placeholder until 3.1)
- [ ] The screen checks pass

**Verify:** `pytest tests/test_research_api.py`; Playwright against *V1.11 Participant list* (light and dark).

**Deps:** 1.3. **Scope:** M

### [ ] Task 1.5: Pre-test, pick and register (V1.10)
**Description:**
- **The `/pretest` list** reuses the data from 1.4. Each row shows the status chip and its
  action: Start, Resume or View result.
- **Register:**
  - Part 1 (code + consent) and Part 2 (the five questions, options from 1.1).
  - One "Save registration".
  - Then the inclusion notice, with "Continue to the pre-test" or "Stop here".
- **States:** code already exists (409), consent not confirmed (Save disabled), backend
  offline, participant not found.

**Acceptance:**
- [ ] A new participant can be registered by keyboard only
- [ ] "Yes" or "Prefer not to answer" on Japanese study shows the notice
- [ ] Nothing reveals a code-to-person link

**Verify:** Playwright with `TEST_PRETEST`; against *V1.10 Pick*, *Register* and *States*.

**Deps:** 1.2, 1.4. **Scope:** M

### [ ] Task 1.6: Pre-test, one kanji, done and pause (V1.10)
**Description:**
- **Focus mode:** no rail; the code, "[n] answered" (`aria-live`) and Pause.
- **The kanji** in `kanji-display`.
- **Answers** No / Not sure / Yes, on keys 1, 2 and 3.
- **For Not sure or Yes:** the reading and meaning inputs, Check, and the result pills.
- **The researcher strip** with flip buttons named by action, and "Save and next".
- **Pause** goes back to the list with "Paused at [n] answered".
- **The done screen:** "That's all. Thank you." For the researcher, only the completion
  time, the count and "Open participant page".
- **Errors:** a 409 reloads and shows its notice; a 422 shows its notice; a reload
  resumes.

**Acceptance:**
- [ ] A full pre-test runs by keyboard only
- [ ] The correct reading or meaning, set names and the word "substitute" never appear in the DOM (Playwright check)
- [ ] Pause then Resume continues at the same kanji
- [ ] A double submit in a second tab triggers the 409 notice and the flow continues
- [ ] The DB rows match what was answered

**Verify:** Playwright e2e end to end; `select` on `kanji_pretest_responses` / `kanji_substitutions`; against *V1.10 One kanji*, *Complete* and *States*.

**Deps:** 1.5. **Scope:** M

### Checkpoint A: the pre-test works
- [ ] `TEST_PRETEST` registered and pre-tested through the UI; DB matches; review with Sebas

### [ ] Task 1.7: Sessions require the pre-test (backend; was Task 5a)
**Description:**
- `POST /sessions` returns 409 ("participant must complete the kanji pre-test at
  http://127.0.0.1:5173/pretest first") while `pretest_completed_at` is null.
- `SessionRead.kanji_items` gives the effective set, each substitute in its original's
  position.
- A pytest fixture for a completed participant, used in `test_session_lifecycle.py`,
  `test_invalid_ids.py` and `scripts/ws_smoke_test.py`.
- `DEV_UNITY` completes a pre-test via the API.

**Acceptance:**
- [ ] No pre-test → 409 and no row, on every visit
- [ ] A substituted participant gets the substituted list
- [ ] Full pytest green; `ws_smoke_test.py` runs

**Deps:** Task 3 of the old plan; merge after 1.6. **Scope:** M

### [ ] Task 1.8: Unity uses `kanji_items` (was Task 5b)
**Description:**
- `SessionBootstrap`: on a 409, log one error naming the `/pretest` URL and stop;
  otherwise read `kanji_items` into `SessionContext`.
- `SessionFlowRunner.ResolveSetAndSeed` and `TrialDebugRunner` use the list.
- Log what S5 does with a kanji that has no assembly segments.

**Acceptance:**
- [ ] Unity Play without a pre-test: one clear error, and no flow
- [ ] With a substitution: S5–S8 show the substitute, and `trials.kanji_id` is the substitute
- [ ] Distractors stay within the effective set
- [ ] Phase2TestHarness green

**Verify:** Unity console and harness; Play with low `baselineTimeScale`; a query on `trials`.

**Deps:** 1.7. **Scope:** M

### Checkpoint B: the pre-test feeds the VR loop
- [ ] A participant registered and pre-tested in the portal runs a Unity session with their effective set

---

## Phase 2: Session review

### [ ] Task 2.1: Session list (V1.1)
**Description:**
- **Endpoint:** `GET /research/sessions`, with filters for participant, condition, status
  and date range, built on `v_session_overview`.
- **Screen:**
  - the header counters per condition, plus "not projected";
  - filters;
  - a table with session, participant, condition, visit, recorded, status (ABORTED
    included), trials, adaptations, accuracy and data quality;
  - rows that are not projected are shown, never hidden.

**Acceptance:**
- [ ] The counts match SQL
- [ ] The filters combine
- [ ] A session opens `/sessions/:id`

**Verify:** pytest; Playwright against *Session list*.

**Deps:** 0.2, 0.3, 1.3. **Scope:** M

### [ ] Task 2.2: Session View header and summary (V1.2)
**Description:**
- **Endpoint:** `GET /research/sessions/{id}`.
- **Screen:** the page header with a lead sentence built from the data, the session facts,
  "Where the time went" (state strip, accuracy, behaviour table), and the Adaptations block
  (counts by action, % skipped, outcome bar).
- The S6 profile is a reserved slot. The adaptations block is empty-state for STATIC.

**Acceptance:**
- [ ] The figures match `trial_timeline()` / `v_adaptations` for one BEHAVIOR_ADAPTIVE and one STATIC session
- [ ] Not-recorded values follow the criterion from 0.3

**Verify:** pytest; Playwright against *Session View*.

**Deps:** 2.1. **Scope:** M

### [ ] Task 2.3: Timeline (V1.3)
**Description:**
- **Endpoint:** `GET /research/sessions/{id}/timeline`, all 8 lanes.
- **Screen:** ECharts, with:
  - the lanes in the fixed order;
  - bars and marks;
  - decision → application lines, the cooldown band and the skipped shape;
  - zoom and pan, "Whole session / Only S7", and the legend;
  - `mm:ss` ticks and `mm:ss.SSS` tooltips.

**Acceptance:**
- [ ] The full real F5a session renders without lag
- [ ] A lane with no data says whether it was empty or not recorded

**Verify:** Playwright; a DevTools profile only if it lags.

**Deps:** 2.2. **Scope:** L (split at build time: lanes 1–4, then 5–8)

### [ ] Task 2.4: Trials table and inspector (V1.4)
**Description:**
- **Endpoint:** `GET /research/sessions/{id}/trials?window_n=`.
- **Screen:** a table with the mockup's 12 columns, "Hide tutorial (S2)" and window
  3/4/5, plus the inspector for the selected trial (explanation box included).
- Selection is synced with the timeline in both directions.

**Acceptance:**
- [ ] Clicking a trial in the timeline selects its row, and vice versa
- [ ] S2 is marked and can be filtered
- [ ] The window parameter changes the aggregates

**Verify:** pytest; Playwright against *Session View* (Trials tab).

**Deps:** 2.3. **Scope:** M

### [ ] Task 2.5: Adaptations tab (V1.5)
**Description:**
- **Endpoint:** `GET .../adaptations?include_no_change=`, which is `v_adaptations` joined
  with `adaptation_decisions` for the cooldown, the versions, the indicators and the
  thresholds.
- **Screen:**
  - expandable rows;
  - outcome chips that use shape as well as colour;
  - a "Show decisions with no change" option;
  - the key-value lists exactly as stored.

**Acceptance:**
- [ ] Every decision of the real session is listed
- [ ] An outcome not yet recorded shows "Not recorded"

**Verify:** pytest; Playwright against *V1.5*.

**Deps:** 2.4. **Scope:** M

### [ ] Task 2.6: Plan and execution tab (V1.6)
**Description:**
- **Endpoint:** `GET .../plan`.
- **Screen:**
  - one row per block, with trial squares for completed / started / never shown;
  - the planned, started and completed counts;
  - the seed;
  - min lag achieved / requested;
  - a cut block highlighted;
  - the "Where the session stopped" note.

**Acceptance:**
- [ ] An ABORTED session shows where it stopped
- [ ] A complete session shows no gap

**Verify:** pytest; Playwright against *V1.6*.

**Deps:** 2.4. **Scope:** S

### [ ] Task 2.7: Export CSV menu (V1.9)
**Description:**
- **Endpoint:** `GET .../export.csv?kind=trials|adaptations`. NULL is exported as an
  empty cell, never 0.
- **Screen:** the CTA opens a popover menu with "Trials (CSV)" and "Adaptations (CSV)".
  Adaptations is disabled for STATIC, with its reason.

**Acceptance:**
- [ ] Both files open, and their headers match the API fields
- [ ] Menu by keyboard (Enter, arrows, Esc)

**Verify:** pytest on the CSV; Playwright download.

**Deps:** 2.5. **Scope:** S

### Checkpoint C: session review
- [ ] A real BEHAVIOR_ADAPTIVE F5a session can be rebuilt on screen without pgAdmin; what the UI shows matches `verify_projection` and `verify_adaptation` (0 discrepancies). Review with Sebas

---

## Phase 3: Participant, quality and close

### [ ] Task 3.1: Participant View (V1.8)
**Description:**
- **Endpoint:** `GET /research/participants/{id}`.
- **Screen:**
  - the facts: pre-test, session counts, conditions, flags;
  - "Open the pre-test" while the pre-test is incomplete;
  - the trend across visits, accuracy or response time, with points shaped by condition;
  - "Kanji replaced by the pre-test", including flagged kanji;
  - sessions in order;
  - the Learner Profile as a reserved slot.

**Acceptance:**
- [ ] Substitutions and flags show only here
- [ ] The trend values match `trial_timeline()` per session

**Verify:** pytest; Playwright against *V1.8* (both states of `pretestDone`).

**Deps:** 1.4, 2.1. **Scope:** M

### [ ] Task 3.2: Data quality (V1.7)
**Description:**
- **Endpoint:** `GET /research/quality` over `v_projection_errors` and the `verify_*_fn()`.
- **Screen:**
  - open errors by code;
  - the verification table: check, what it compares, discrepancies, result;
  - the errors to resolve, with a code filter and the event, session, detail and time.

**Acceptance:**
- [ ] After 0.1, the counts match SQL
- [ ] A seeded discrepancy appears as "Needs review"

**Verify:** pytest; Playwright against *V1.7*.

**Deps:** 0.3, 1.3. **Scope:** M

### [ ] Task 3.3: Docs and graph (was Task 6)
**Description:**
- `database/ERD.md` and `schema.sql` cover 0004–0006.
- In the skill:
  - fix the token names in `visualization-rules.md` to match `design-system.md`
    (`--color-headaway`; hints use `--color-lal-high`; no `-open` or `--color-hint`);
  - move the roadmap rows that are now done;
  - add the abort rule to `data-contract.md`.
- Draft lines for the project docs (Plan §9 log; spec §13.2 lazy chain; the ABORTED
  rule), for Sebas.
- `graphify update .`

**Acceptance:**
- [ ] ERD matches the migrations
- [ ] The doc text is handed to Sebas

**Deps:** all. **Scope:** S

### Checkpoint D: v1 done
- [ ] Every screen V1.1–V1.11 is built, with screenshots in light and dark
- [ ] The 5-tell audit is clean
- [ ] Full pytest, Vitest and Playwright green
- [ ] The v1 definition of done in `scope-and-roadmap.md` is met

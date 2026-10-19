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

### [x] Task 0.1: Backup and clean-up (done 17 Oct)
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
- [x] Sebas approved the final SQL and the counts before it ran
- [x] No session older than the scene remains (72 → 49 sessions, 37 → 13 participants). `verify_projection.sql` gives the same result as on the backup: 25 count rows, all from the 3 multi-run evidence sessions (pre-existing; check 2 does not discount duplicates, so Task 0.3's function must)
- [x] Open projection errors: 1,918 → 0

**Verify:** the before/after counts are printed by the script itself; restoring the dump
into a scratch database works.

**Deps:** none. **Scope:** S

### [x] Task 0.2: Abandoned sessions become ABORTED (migration 0005, done 17 Oct)
**Description:**
- SQL function `abort_stale_sessions(p_idle interval DEFAULT '30 minutes') RETURNS int`.
- The backend lifespan runs it at startup and then every 5 min, and logs the count when
  it is above 0. `shortcut:` an in-process loop instead of `pg_cron`.
- Write the up and down SQL.

**Acceptance:**
- [x] An `IN_PROGRESS` session with its last event more than 30 min ago → `ABORTED`; one with a recent event is untouched (with no events, `updated_at` counts)
- [x] `COMPLETED` and `CREATED` sessions are never touched
- [x] A later `PATCH .../state` does not revert `ABORTED` (existing rule, now tested)
- [x] The 31 stale `IN_PROGRESS` sessions in the dev DB became `ABORTED` on the first run; the restarted backend runs the rule at startup (log checked)

**Verify:** pytest with backdated `server_received_at`; migration up / down / up.

**Deps:** 0.1. **Scope:** S

### [x] Task 0.3: Read-side SQL for the portal (migration 0006, done 17 Oct)
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
- [x] Each function returns 0 rows on a session that its `.sql` script passes, and finds a seeded discrepancy. On the dev DB all five return 0 rows; `verify_projection_fn()` no longer counts the 25 duplicate-run rows (an event with an error and no row pointing to it is not expected to project). `verify_reproducibility_fn` returns nothing when the session has no other session with its seed and set (the script reports every block as seen once)
- [x] The overview matches a hand query on 3 sessions (one STATIC, one BEHAVIOR_ADAPTIVE, one aborted): `6eb2bd5c`, `a5748886`, `89ecef07`

**Verify:** `pytest backend/tests/test_research_sql.py`; up / down / up.

**Deps:** 0.1. **Scope:** M

### Checkpoint 0
- [x] Full `pytest` green; migrations clean; show Sebas the clean-up counts and the new statuses (17 Oct: 167 passed; 0006 → 0004 → 0006 clean; 49 sessions, 13 participants, 0 open errors, 0 IN_PROGRESS. Sebas approved and kept the 12 remaining participants besides `DEV_UNITY`)

---

## Phase 1: Pre-test, end to end (before the pilot)

### [x] Task 1.1: Registration options (approved 17 Oct, done 17 Oct)
**Description:** Sebas approved the table in `plan.md`. Record it in the skill's
`scope-and-roadmap.md` §V1.10. Send the design chat a copy-only note: the
attention question has 5 options, and the inclusion notice says "accepted".

**Acceptance:**
- [x] Sebas approved the options (17 Oct)
- [x] Options recorded in `scope-and-roadmap.md` §V1.10 (17 Oct)
- [x] Note sent to the design chat (17 Oct)

**Deps:** none. **Scope:** XS

### [x] Task 1.2: Registration rules in the backend (was Task 3b, done 17 Oct)
**Description:**
- `POST /participants` sets `consent_obtained_at` when consent is true.
- The pre-test POST routes return 409 "consent not recorded" without consent.
- The options from 1.1 become `Literal`s in the schema.
- Callers send consent: `test_pretest_api._participant` and `SessionBootstrap`'s
  dev-participant POST.
- `DEV_UNITY` gets consent with one `UPDATE`, shown first.

**Acceptance:**
- [x] Created with consent → `consent_obtained_at` is set; without → NULL
- [x] A pre-test answer without consent → 409, nothing stored (`/check` too)
- [x] An unknown `age_range` → 422 (and an unknown attention option)
- [x] Existing tests pass (172 passed, 17 Oct)
- [x] `DEV_UNITY` has consent (UPDATE run 17 Oct); every caller that registers participants sends consent

**Verify:** `docker compose run --rm backend pytest -q`

**Deps:** 1.1. **Scope:** S

### [x] Task 1.3: Dashboard scaffold and app shell (done 17 Oct)
**Description:**
- `dashboard/`: Vite, React, TS strict, Tailwind, `shadcn init`, TanStack Query, React
  Router and the Fontsource packages.
- `styles/tokens.css` holds the exact values from `design-system.md` (light, dark,
  `prefers-color-scheme`). shadcn's variables are mapped onto the tokens; radius by role.
- `npm run gen:api` (`openapi-typescript`).
- Vite on `127.0.0.1:5300`, with a proxy to `:8000`.
- The shell: a 240 px rail (Sessions, Participants, Pre-test, Data quality), a 16-column
  grid, and routes for every screen that render reserved placeholders.
- Vitest, Testing Library and the Playwright config.
- Delete the root `package.json`, `package-lock.json` and `node_modules/`. Commit
  `.mcp.json`. Add Fontsource to the skill's stack table.

**Acceptance:**
- [x] `npm run dev` binds to 127.0.0.1 only; no outbound request in the Playwright network log (fonts included). Port 5300, not 5173: Windows reserves 5163–5262 (Sebas, 17 Oct)
- [x] The tokens page renders both themes; contrast pairs as measured in `design-system.md` (two round differently there: 5.95 is written 5.9, 14.35 is written 14.4)
- [x] Generated types include the pretest and participant schemas
- [x] 5-tell audit: none found

**Verify:** `npm run test`, `npx playwright test` (smoke); a screenshot of the rail against the *Session list* artboard.

**Deps:** none (do before 1.4). First task on `phase/7-research-dashboard`. **Scope:** M

### [x] Task 1.4: Participant list: `/research/participants` and V1.11 (done 18 Oct)
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
- [x] The figures match SQL for 3 participants (`DEV_UNITY`, `OBS_01`, `M2_EVIDENCE_20260928_1503`)
- [x] A code opens `/participants/:id` (placeholder until 3.1)
- [x] The screen checks pass (screenshots light and dark, keyboard e2e, NULL as `—` with its reason, no clinical wording, 5-tell audit)

**Verify:** `pytest tests/test_research_api.py`; Playwright against *V1.11 Participant list* (light and dark).

**Deps:** 1.3. **Scope:** M

### [x] Task 1.5: Pre-test, pick and register (V1.10, done 18 Oct)
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
- [x] A new participant can be registered by keyboard only (Playwright, `TEST_PRETEST`, deleted after)
- [x] "Yes" or "Prefer not to answer" on Japanese study shows the notice (an unanswered question is also null, so it shows "not reported" too)
- [x] Nothing reveals a code-to-person link (the code is the only text field)

**Verify:** Playwright with `TEST_PRETEST`; against *V1.10 Pick*, *Register* and *States*.

**Deps:** 1.2, 1.4. **Scope:** M

### [x] Task 1.6: Pre-test, one kanji, done and pause (V1.10, done 18 Oct)
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
- [x] A full pre-test runs by keyboard only
- [x] The correct reading or meaning, set names and the word "substitute" never appear in the DOM (Playwright check against every reading and meaning in `kanji_content.json`, at each kanji and on the done screen)
- [x] Pause then Resume continues at the same kanji
- [x] A double submit in a second tab triggers the 409 notice and the flow continues
- [x] The DB rows match what was answered (`kanji_pretest_responses` row by row; `kanji_substitutions` count against the API)

**Verify:** Playwright e2e end to end; `select` on `kanji_pretest_responses` / `kanji_substitutions`; against *V1.10 One kanji*, *Complete* and *States*.

**Deps:** 1.5. **Scope:** M

### Checkpoint A: the pre-test works
- [x] `TEST_PRETEST` registered and pre-tested through the UI; DB matches; review with Sebas (18 Oct: 17 answers, A 車 -> 米 and B 山 -> 口, nothing flagged; API and list agree; deleted after)

### [x] Task 1.7: Sessions require the pre-test (backend; was Task 5a, done 18 Oct)
**Description:**
- `POST /sessions` returns 409 ("participant must complete the kanji pre-test at
  http://127.0.0.1:5300/pretest first") while `pretest_completed_at` is null.
- `SessionRead.kanji_items` gives the effective set, each substitute in its original's
  position.
- A pytest fixture for a completed participant, used in `test_session_lifecycle.py`,
  `test_invalid_ids.py` and `scripts/ws_smoke_test.py`.
- `DEV_UNITY` completes a pre-test via the API.

**Acceptance:**
- [x] No pre-test → 409 and no row, on every visit (an unknown participant is now 404, not a database error)
- [x] A substituted participant gets the substituted list (create, get, list and state update)
- [x] Full pytest green (181); `ws_smoke_test.py` runs. `DEV_UNITY` completed a pre-test via the API (all No, set unchanged). `test_invalid_ids.py` creates no session, so it needed no fixture

**Deps:** Task 3 of the old plan; merge after 1.6. **Scope:** M

### [ ] Task 1.8: Unity uses `kanji_items` (was Task 5b)
**Description:**
- `SessionBootstrap`: on a 409, log one error naming the `/pretest` URL and stop;
  otherwise read `kanji_items` into `SessionContext`.
- `SessionFlowRunner.ResolveSetAndSeed` and `TrialDebugRunner` use the list.
- Log what S5 does with a kanji that has no assembly segments.

**Acceptance:**
- [x] Unity Play without a pre-test: one clear error, and no flow (Play as `OBS_01`, 19 Oct: one error naming the `/pretest` URL, flow stays in S0, no session row)
- [ ] With a substitution: S5–S8 show the substitute, and `trials.kanji_id` is the substitute (needs a person in S1–S8; logic covered by harness K1–K4)
- [x] Distractors stay within the effective set (harness K4: 20 S7 trials, targets and options only from the effective set)
- [x] Phase2TestHarness green (84/84, with the new K1–K5)

**Verify:** Unity console and harness; Play with low `baselineTimeScale`; a query on `trials`.

**Deps:** 1.7. **Scope:** M

### [ ] Task 1.9: Assembly segments for sets B and C (C1 of `Plan_Fase5a.md` §10)
**Description:**
- Today only set A (and the tutorial's 四) has real segments; every session with set B or
  C assembles all five kanji from placeholder parts. The replan (risk 6) puts this before
  the behavioural dry run at the end of October.
- Cut the 10 kanji of B and C with `tools/assembly_segments.py`: centre lines per group
  in `G`, following the "Assembly" column of `Tabla_Autoria_Kanji_Fase2.md` (山 門 女 手 雨,
  人 足 牛 肉 花). Resolve ambiguous cases from the preview, as with 火 (two near-identical
  symmetric pieces).
- Add the segments to each kanji's asset in Unity, so `AssemblyPlan.For` uses them.
- The group count must stay the contract's `assemblyGroups`: it is part of the set
  balance band (12 ± 2), and the tool refuses a mismatch.
- Found 19 Oct: set A's assets never listed their segments either, so every assembly in
  the DB so far has `segments_authored = false` (85 rows of set A included) although the
  board drew the real PNGs. The tool now writes the list into every kanji's asset it cuts,
  set A and 四 included. Those old rows are not corrected.
- Cut 19 Oct: 10 kanji, 58 PNGs (import settings copied from set A). Where a diagonal
  crosses a bar (女, 肉) the bar stays whole; where a vertical crosses bars (手, 雨, 牛) the
  vertical stays whole, as with 車.

**Acceptance:**
- [ ] `tools/assembly_preview.png` reviewed by Sebas for the 10 kanji
- [ ] Phase2TestHarness green; S5 logs "authored" for every kanji of B and C (harness 84/84 and `AssemblyPlan` authored for the 15 + 四, 19 Oct; the S5 log is checked in Play)
- [ ] One kanji of B and one of C assembled in the headset; each group can be grasped

**Verify:** harness; Play with set B and set C; `assemblies.segment_count` and
`segments_authored = true` in the DB.

**Deps:** none (content). **Scope:** M

### [ ] Task 1.10: Assembly segments for the reserve kanji that can be a first substitute
**Description:**
- The pre-test asks the reserve in rank order (`ranked_substitutes`). Only 10 of the 20
  are the first choice for some original: 土 米 木 耳 口 貝 金 川 水 糸. 日 田 子 目 学 物 茶 are
  only second or later choices, and 馬 魚 鳥 can replace none of the 15 (checked 19 Oct).
- The substitution rule fixes how many groups each reserve kanji has (`assemblyGroups`,
  hand-entered in `tools/kanji_metrics.py` and checked against the balance band), but
  nothing defines which strokes form each group. Define them from the textbook stroke
  order, as for the 15, and record them in the authoring table; then cut and add them as
  in Task 1.9.
- The rest of the reserve only if a real pre-test asks for it. Until then the placeholder
  fallback stays, flagged by `segments_authored = false` and the S5 warning.
- Groups proposed 19 Oct (stroke order; same rules as the 15), cut and pending review.
  For the authoring table in the project docs:

  | Kanji | Groups | Assembly |
  |---|---|---|
  | 土 | 2 | 十, base |
  | 米 | 3 | two dots, cross, two sweeps |
  | 木 | 2 | cross, two sweeps |
  | 耳 | 2 | frame (top bar, two verticals), bars (two inner bars, rising bottom stroke) |
  | 口 | 2 | left, top and right (strokes 1+2), bottom (Sebas, 19 Oct) |
  | 貝 | 2 | 目 box, legs |
  | 金 | 3 | roof, body (三 bars + vertical), two dots |
  | 川 | 3 | one per stroke |
  | 水 | 2 | centre hook, side strokes |
  | 糸 | 2 | 幺 top, 小 bottom |

**Acceptance:**
- [x] Groups of the 10 kanji written down and reviewed by Sebas (19 Oct; 口 regrouped by Sebas)
- [ ] Preview reviewed; harness green; S5 logs "authored" for each of the 10 (harness 84/84 and `AssemblyPlan` authored for all 10, 19 Oct)
- [ ] A participant with a substitution assembles the substitute from real segments

**Verify:** harness; Play with a substituted participant (as in Task 1.8).

**Deps:** 1.9 (same procedure). **Scope:** M

### Checkpoint B: the pre-test feeds the VR loop
- [ ] A participant registered and pre-tested in the portal runs a Unity session with their effective set

### Headset session, Tue 20 Oct: every pending VR check
Everything Phase 1 still needs from the headset, in one sitting. Code is committed
(`a520817`). Quest 2 via Link in the Editor; Inspector changes on `SessionBootstrap`
(`devParticipantCode`, `newSessionKanjiSet`) are temporary: revert them after. Never save
the scene during Play. Restart the backend only between runs, never with `--reload`.

**Run 1: set B with a substitution (Task 1.8, Task 1.9 for B, Checkpoint B)**
- [ ] Portal `/pretest`: register `TEST_VR_B` with consent; answer "Yes" with the right
      reading on one set B kanji (on 18 Oct, 山 → 口), "No" on the rest. Note the substitute
- [ ] `SessionBootstrap`: `devParticipantCode = TEST_VR_B`, `newSessionKanjiSet = B`; Play
      through S5–S8 (low `baselineTimeScale` is fine)
- [ ] S5–S8 show the substitute in the original's place
- [ ] S5: the 4 kept B kanji log "authored" and assemble from real strokes; every group can
      be grasped. A first-choice substitute (口 for 山) also logs "authored" (Task 1.10);
      any other substitute logs the placeholder warning, as expected

**Run 2: set C (Task 1.9 for C)**
- [ ] `devParticipantCode = DEV_UNITY` (pre-test all No, set unchanged), `newSessionKanjiSet = C`;
      Play through S5
- [ ] S5: all 5 C kanji log "authored"; every group can be grasped (look at 花's three
      pieces and 足's foot)

**After both runs, in the DB** (`<id>` = each session id from the Unity log):
- [ ] `select kanji_id, segment_count, segments_authored from assemblies where session_id = '<id>';`
      → `true` for every kanji, the substitute included if it is one of the 10 of Task 1.10
- [ ] `select block_state, kanji_id, count(*) from trials where session_id = '<id>' group by 1, 2 order by 1, 2;`
      → run 1: the substitute appears and its original never does
- [ ] Tick Task 1.8 (substitution), Task 1.9 (headset), Task 1.10 (substitute from real
      segments) and Checkpoint B; delete `TEST_VR_B`
      with Sebas's OK

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

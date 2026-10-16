# Todo: Kanji pre-test (spec §13.2)

Plan: `tasks/plan.md` (decisions of 16 Oct included). Branch off after the
F5a delivery tag. One change per commit, and show Sebas each message first.

## [x] Task 1: Contract carries glyph similarity, and the backend reproduces the substitution table

**Description:** Make `kanji_metrics.py --export` add a `similarity` map: one entry per
unordered pair of experimental + reserve kanji, rounded to 3 decimals. Mount
`kanji_content.json` read-only into the backend container. Add
`backend/app/pretest/rules.py`, which loads the contract and does three things:
- `valid_substitutes(effective_set, original, excluded)`: the three §13.2 conditions plus
  "not used, not KNOWN"
- `best_fit` ranking by the score in plan.md
- regenerate `seed_kanji_items.sql` (the sha changes)

**Done 16 Oct.** The drift test found that 0.1 rounding of `perimetricComplexity` let 学 replace 門 (8.01 % vs the 8 % band), so the contract now exports it with 4 decimals.

**Acceptance criteria:**
- [x] With nothing substituted, `valid_substitutes` returns exactly the contract's `substitutionTable` for all 15 kanji
- [x] With a substitution already in a set, a second candidate is checked against the substituted set (one test with a constructed case)
- [x] Unity still loads the contract (an unknown field is ignored) and Phase2TestHarness passes

**Verification:**
- [x] `docker compose run --rm kanji-tools python tools/kanji_metrics.py --export` green
- [x] `docker compose exec backend pytest tests/test_pretest_rules.py`
- [x] Unity console clean after reimport

**Dependencies:** None

**Files likely touched:** `tools/kanji_metrics.py`, `unity-client/Assets/Resources/kanji_content.json`, `database/seed_kanji_items.sql`, `docker-compose.yml`, `backend/app/pretest/rules.py`, `backend/tests/test_pretest_rules.py`

**Estimated scope:** Medium

## [x] Task 2: Pure chain and auto-grading

**Description:** In `rules.py`, add three functions:
- `classify(self_report, reading_ok, meaning_ok)`
- `next_item(responses)`: primaries in A, B, C contract order. A KNOWN item walks down
  its ranked candidates until one is not KNOWN. It returns `None` when done, together
  with the substitutions and the flagged items.
- `auto_grade(kanji, typed_reading, typed_meaning)`: kana or katakana or Hepburn romaji
  for the reading; any comma-separated meaning variant, case- and space-insensitive.

**Acceptance criteria:**
- [x] All NO: 15 items asked, no substitutions
- [x] KNOWN primary: its best-fit substitute is asked next; KNOWN substitute: the next one; UNKNOWN or PARTIALLY_KNOWN substitute: accepted
- [x] A reserve kanji tested in one set's chain is not asked again in another set, and is never used twice
- [x] Candidates run out: the original stays and is flagged
- [x] `つき`, `ツキ`, `tsuki`, `Tsuki ` all pass for 月; `foot` and `leg` both pass for 足

**Verification:**
- [x] `docker compose exec backend pytest tests/test_pretest_rules.py`

**Dependencies:** Task 1

**Files likely touched:** `backend/app/pretest/rules.py`, `backend/tests/test_pretest_rules.py`

**Estimated scope:** Small

## Checkpoint A
- [ ] All backend tests green (`pytest`); no DB change yet
- [ ] Review the ranking on the real contract with Sebas (print the ranked list per kanji)

## [ ] Task 3: Storage and API

**Description:**
- Migration `0004`: `kanji_pretest_responses` and `kanji_substitutions`, FKs to
  `participants` and `kanji_items`, unique (participant, kanji), plus
  `participants.pretest_completed_at`. Models and schemas.
- `GET /participants/{id}/pretest`: status, the next item (char + id only, never the
  answer), the substitutions and the flags.
- `POST .../pretest/check`: auto-grade only, nothing stored.
- `POST .../pretest/responses`: stores the response and returns the next state. It gets
  409 when the kanji is not the expected next one, and 422 for UNSURE/YES without typed
  fields. The response that completes the chain writes `kanji_substitutions` in the same
  transaction and sets `pretest_completed_at`.

**Acceptance criteria:**
- [ ] A scripted full run (one KNOWN primary, one KNOWN substitute) ends with one substitution row and the expected classifications
- [ ] An out-of-order or repeated POST gets 409 and stores nothing
- [ ] Migration up / down / up is clean

**Verification:**
- [ ] `docker compose exec backend alembic upgrade head`, then `downgrade -1`, then `upgrade head`
- [ ] `docker compose exec backend pytest tests/test_pretest_api.py`

**Dependencies:** Task 2

**Files likely touched:** `backend/alembic/versions/0004_kanji_pretest.py`, `backend/app/models/pretest.py`, `backend/app/schemas/pretest.py`, `backend/app/api/routes/pretest.py`, `backend/tests/test_pretest_api.py`

**Estimated scope:** Medium

## [ ] Task 4: Researcher page

**Description:** `GET /pretest` serves one HTML file. The flow:
1. Pick the participant by `external_code`.
2. The kanji is shown large, with NO / UNSURE / YES buttons.
3. For UNSURE or YES, two inputs (reading, meaning) appear, then **Check**.
4. Two ✓/✗ toggles show the auto result, and the researcher can flip them.
5. **Save** goes to the next kanji.

At the end, a summary of the classifications and substitutions. The target answers are
never on screen.

**Acceptance criteria:**
- [ ] A full pre-test can be done with the keyboard only (Tab / Enter), and buttons have labels (accessibility)
- [ ] A 409 reloads the current state instead of showing a stack trace
- [ ] Reloading the page mid-test resumes at the right kanji

**Verification:**
- [ ] Manual: run a test participant end to end in the browser; then check `select * from kanji_pretest_responses` / `kanji_substitutions`

**Dependencies:** Task 3

**Files likely touched:** `backend/app/static/pretest.html`, `backend/app/main.py`

**Estimated scope:** Small

## Checkpoint B
- [ ] Pre-test done end to end through the page for a test participant
- [ ] DB rows match what was answered
- [ ] Review with Sebas

## [ ] Task 5: Sessions require the pre-test and use the effective set

**Description:**
- **Backend:** `POST /sessions` returns 409 ("participant must complete the kanji
  pre-test at /pretest first") when `pretest_completed_at` is null. `SessionRead` gains
  `kanji_items` (the effective characters of `assigned_kanji_set`, each substitute in
  its original's position). Add a pytest fixture for a participant with a completed
  pre-test, and use it in `test_session_lifecycle.py`, `test_invalid_ids.py` and
  `scripts/ws_smoke_test.py`.
- **Unity:**
  - `SessionBootstrap`: on a 409, log one error with the pre-test URL and stop; otherwise
    read `kanji_items` (Newtonsoft, an array) into `SessionContext`.
  - `SessionFlowRunner.ResolveSetAndSeed` and `TrialDebugRunner` build the set from
    `kanji_items`, and keep `content.Set(name)` only for runs with no session.

Check what S5 does with a kanji that has no assembly segments, and make sure it logs that.

**Acceptance criteria:**
- [ ] Creating a session for a participant without a completed pre-test gets 409 and creates no row (every visit number)
- [ ] A session of a participant with a substitution returns the substituted list
- [ ] Unity Play with a participant without a pre-test: one clear console error naming `/pretest`, and the flow does not start
- [ ] In Play, S5–S8 present the substitute, and `trials.kanji_id` in the DB is the substitute's
- [ ] Distractors stay within the effective set
- [ ] Phase2TestHarness passes

**Verification:**
- [ ] Full `pytest` (the gate touches every test that creates a session); `ws_smoke_test.py` runs
- [ ] Unity: console clean, harness green; Play with a substituted test participant (`baselineTimeScale` low), then `check_loop.sql` / a query on `trials`

**Dependencies:** Task 3 (Task 4 not needed)

**Files likely touched:** `backend/app/schemas/session.py`, `backend/app/api/routes/sessions.py`, `backend/tests/conftest.py`, `test_session_lifecycle.py`, `test_invalid_ids.py`, `scripts/ws_smoke_test.py`; `unity-client/Assets/Scripts/Core/SessionBootstrap.cs` (+ `SessionContext`), `SessionFlowRunner.cs`, `TrialDebugRunner.cs`

**Estimated scope:** Large. Split it at build time into 5a (backend gate, `kanji_items` and test fixtures) and 5b (Unity).

## Checkpoint C: Complete
- [ ] All acceptance criteria met; backend tests and Unity harness green
- [ ] Assembly-gap risk has an owner (plan Open question 1)
- [ ] `DEV_UNITY` has done the pre-test once, so Unity dev Play works again

## [ ] Task 6: Docs and graph

**Description:**
- `database/ERD.md`: the two new tables.
- Draft lines for the project docs (spec §13.2 lazy chain and the multi-substitution
  rule, MER §4 `kanji_pretest` now real, Plan §9 log). These are shown to Sebas; the
  project docs live in claude.ai.
- `graphify update .`

**Acceptance criteria:**
- [ ] ERD matches migration 0004
- [ ] Doc text handed to Sebas

**Dependencies:** Tasks 3, 5

**Estimated scope:** Small

# Data contract

Sources: `database/schema.sql` (readable reference), `database/ERD.md`, the
migrations `backend/alembic/versions/sql/000{2,3,4}_*_up.sql`, and
`database/EVENT_CONTRACT.md`. Original design in `MER_Schema_v1.md` (Project).
**The schema and migrations win over this reference:** check the columns before
writing each endpoint.

## Principles

- `session_events` is the source of truth (D4). Every table in `0002` and `0003`
  is a projection that `project_session()` can rebuild. **The dashboard does not
  read `session_events.payload`.** It uses projected tables, views and
  `trial_timeline()`. Missing data goes into the projection or a view (new
  migration), not into the frontend.
- Every projected row keeps the id of the event it came from (D5):
  `source_event_id`, `started_/answer_/completed_event_id`, `outcome_event_id`.
  The API exposes them.
- Natural trial key `(session_id, trial_id)`, e.g. `S7-007` (D6).
- Time in `session_elapsed_ms` (D7): the `*_elapsed_ms` columns.
- **NULL = not recorded** (D9). The API returns `null`, never a default `0`.
- Plan and execution have no FK between them (D10).

### Watch out: zeros that actually mean "not recorded"

`trial_timeline()` and `v_trial_behavior` apply `COALESCE(..., 0)` to
`head_away_count`, `head_away_ms`, `peripheral_event_count`,
`distractor_dwell_ms`, `dwell_count` and `orienting_count`. In a session recorded
**before** the corresponding event type existed, that 0 means "was not being
recorded", not "did not happen". `DISTRACTOR_INTERACTION` starts on Oct 6
(session `371b2c59`). The backend decides per session whether the data existed
(e.g. at least one event of that type in `session_events`, or the session date)
and sends `null` when it did not. Document the criterion in the endpoint and
cover it with a test.

## Objects used by v1

| Object | Purpose | Notes |
| --- | --- | --- |
| `participants` | List and Participant View | Show `external_code`. `pretest_completed_at` (`0004`) |
| `experiment_sessions` | List, metadata | `condition` (`STATIC`, `BEHAVIOR_ADAPTIVE`, `MULTIMODAL_ADAPTIVE`), `status` (`CREATED`, `IN_PROGRESS`, `COMPLETED`, `ABORTED`), `current_state`, `visit_number`, `assigned_kanji_set`, `random_seed` |
| `session_states` | States lane, per-state duration | `exited_elapsed_ms` is NULL if the session was cut |
| `trial_blocks`, `planned_trials` | Plan vs execution | Up to 5 blocks (S2, S5, S6, S7, S8) |
| `trials` | Trials lane | No `completed_event_id` = open or cut. `kanji_id` is already the effective kanji (the substitute, if any). `cue_trigger`, `proactive_index` (`0003`) |
| `hint_requests` | Hint marks | Stored even when `cues_granted = '{}'` |
| `environment_applications`, `v_environment_intervals` | ESL lane | `valid_to_ms` = next application |
| `peripheral_events` | Peripherals lane | `event_index` does not reset |
| `distractor_interactions` | Distractors lane | `kind` `DWELL` or `ORIENTING`; `onset_elapsed_ms`, `duration_ms`, `object_group`, `trial_id` |
| `head_away_episodes` | Head-away lane | Keeps the thresholds in force |
| `adaptation_decisions` | Decision detail | One per answered trial of an adaptive S7, `NO_CHANGE` included. `learner_state`, `cause`, `confidence`, `action`, `dimension`, `from_level`, `to_level`, `proactive_cues`, `reason_code`, `explanation`, `cooldown_until_trial`, `indicators`/`thresholds` (JSONB), `outcome` |
| `v_adaptations` | Adaptations lane and table | Each decision with what Unity did: `unity_result` (`APPLIED`/`SKIPPED`/NULL = pending or lost), `skip_reason`, `applied_before_trial_id`, `applied_elapsed_ms` |
| `adaptation_applications` | Skips without a decision (`TIMEOUT`) | No FK to the decision |
| `kanji_items` | Kanji character and metadata | 40 rows |
| `kanji_substitutions` | Participant substitutions | `substitute_kanji_id` NULL = KNOWN with no substitute (flagged) |
| `trial_timeline(session, window_n)` | Trials table and summary | `window_n = 3` by default (provisional). F5a columns at the end |
| `projection_errors` | Quality panel | `MISSING_FIELD`, `UNKNOWN_ENUM`, `ORPHAN_EVENT`, `DUPLICATE`, `FK_VIOLATION` |

`indicators` and `thresholds` are JSONB written by the **backend** (not Unity
payload). They can be shown as-is in a detail panel, as key → value, with no
interpretation in the frontend.

Per-trial windows (decided Oct 1): RT, idle and head-away in `[started,
answered)`; peripherals in `[started, completed)`. A distractor counts for the
trial answered at or after it, back to the previous answer of the block (same
attribution as `backend/app/adaptation/trials.py`). The observation window is per
block.

Sessions before Sep 7 are not projected: they appear in the list as "not
projected", they are not hidden.

## v1 endpoints (proposal, `GET` only)

The backend uses no version prefix: routers live at the root (`/sessions`,
`/participants`, `/participants/{id}/pretest`). The dashboard gets a new router,
`backend/app/api/routes/research.py`, with the prefix **`/research`**, so it does
not mix with the endpoints Unity uses.

| Endpoint | Returns |
| --- | --- |
| `GET /research/sessions?participant_id=&condition=&status=&from=&to=` | List with summary, `projected` and `open_projection_errors` |
| `GET /research/sessions/{session_id}` | Metadata + summary (durations, accuracy, RT, hints, head-away, adaptations by action and outcome) |
| `GET /research/sessions/{session_id}/timeline` | All lanes: `states`, `environment`, `trials`, `hints`, `peripherals`, `distractors`, `head_away`, `adaptations` |
| `GET /research/sessions/{session_id}/trials?window_n=3` | `trial_timeline()` rows |
| `GET /research/sessions/{session_id}/adaptations?include_no_change=false` | `v_adaptations` rows + `indicators`/`thresholds` |
| `GET /research/sessions/{session_id}/plan` | Planned vs executed per block |
| `GET /research/sessions/{session_id}/quality` | `projection_errors` + verify results |
| `GET /research/sessions/{session_id}/export.csv?kind=trials\|adaptations` | CSV |
| `GET /research/participants` | V1.11: one row per participant with `external_code`, `created_at`, pre-test status and `answered`, session count, conditions, last session date and accuracy (NULL if no answered trials), `previous_japanese_experience`, `flagged_count` |
| `GET /research/participants/{participant_id}` | Sessions in order, trend, pre-test status, substitutions and flagged kanji |

Rules:
- Responses in `snake_case`, like the database, with Pydantic models in
  `backend/app/schemas/research.py` so they show up in the OpenAPI.
- SQL functions and views are called with `sqlalchemy.text()` from the async
  session (`app.db.session.get_db`). Their logic is not duplicated in Python.
- Frontend types are generated from `http://localhost:8000/openapi.json`.
- Read-only: the router has no `POST/PATCH/DELETE`. A read-only PostgreSQL role is
  the proposal; today the backend uses a single user (`neuroadaptive`).
- Tests in `backend/tests/test_research_api.py` against the existing fixtures
  (`tests/fixtures/projection_session.json`, `prueba_fase_f3_events.json`).

# Event payload contract — v1

Status: **proposed, 8 September 2026.** Governs what Unity puts in the `payload`
of every `SESSION_EVENT` and therefore what lands in `session_events.payload`.

This document is the authority for the payload shape. Spec §11 defines *which*
fields exist and *what they mean*; it does not define the wire format, and this
contract does. Where the two differ, §5 records why.

## 1 · Why this exists before the response system

Phase 2 ships no database migration. All behavioral telemetry goes through the
generic `session_events` log — `event_type VARCHAR(64)` plus `payload JSONB` —
and Phase 3 promotes those rows into the relational tables of the §11 data
contract. That promotion is only possible if every Phase 2 event already carries
the identifiers that will become foreign keys.

The response system is the main emitter of these events and is built next.
Defining the shape first costs hours; defining it afterwards means retrofitting
the most reused component in the project.

There is a second reason, from the Phase 2 step 0. Twice in one day this project
found a contract that the code claimed to honour and did not: the payload sent as
a serialized string under `payload_json`, and the game flow enum serialized by C#
member name. Neither failed loudly, because JSONB accepts anything. **A JSONB
column will never tell you the payload is wrong.** So the contract is enforced in
code (§6) and checked by query (§7), not by convention.

## 2 · Envelope

Unchanged from Phase 1. The WebSocket message carries:

```json
{
  "type": "SESSION_EVENT",
  "event_type": "TRIAL_STARTED",
  "client_timestamp": "2026-09-08T07:10:06.1887742Z",
  "payload": { }
}
```

`event_type` is the vocabulary name from spec §11.1. `client_timestamp` is
ISO-8601 UTC from the Unity client. Everything below concerns `payload`.

## 3 · The context block

**Every payload carries these fields, on every event, without exception.**

| Key | Type | Meaning |
|---|---|---|
| `schema_version` | int | Version of this contract. Currently `1`. |
| `state` | string | Game flow state that produced the event, as the backend enum value (`S7_EXPERIMENTAL_RETRIEVAL`). |
| `session_elapsed_ms` | int | Milliseconds since the session clock zero. |
| `esl` | string | Active Environmental Stimulation Level: `OFF`/`LOW`/`MEDIUM`/`HIGH`/`BASELINE`. |
| `lal` | string | Active Learning Assistance Level, same scale minus `BASELINE`. |

**Events emitted inside a trial additionally carry the trial block:**

| Key | Type | Meaning |
|---|---|---|
| `trial_id` | string | Identifies the trial. See §4.1. |
| `trial_type` | string | `T1_MEANING_TO_KANJI`, `T2_KANJI_TO_MEANING`, `T3_KANJI_TO_READING`. |
| `trial_sequence` | int | 1-based position within the current state's trial sequence. |
| `kanji_id` | string | Stable identifier of the `KanjiLearningItem`. See §4.2. |

`schema_version` is the field that makes the rest survivable. Phase 2 will
change this contract during the week; Phase 3 migrates rows written under
several versions. Without a version stamp, a migration cannot tell which shape a
given row has, and mixed shapes are what turn a migration into archaeology.

`session_elapsed_ms` is present for a Phase 4 reason. The Session Clock is the
common reference that aligns Unity telemetry with EEG windows. Wall-clock
timestamps from two machines drift; an offset from a known zero does not. The
field costs nothing now — Unity already holds the value — and cannot be
reconstructed later for data already collected.

## 4 · Identifiers

### 4.1 `trial_id`

Format: `{state}-{sequence}`, zero-padded to three digits — `S7-007`.

Deterministic rather than a UUID, and deliberately so. Spec §6.1 requires that
the seed and the final trial sequence permit exact session reconstruction; an id
derived from the sequence is itself reconstructable, and it reads correctly in a
query result. Trials occur in five states (S2 tutorial practice, S5 guided association, S6,
S7, S8), so the state prefix is what keeps the sequence unambiguous — and the
`S2-` prefix is what keeps tutorial practice out of the primary analysis
(spec §12 lists S2 performance as "tutorial only").

The id is unique within a session, not globally. Phase 3's relational key is
`(session_id, trial_id)`.

### 4.2 `kanji_id`

The stable id from `kanji_content.json` (generated from `KANJI_IDS` in
`tools/kanji_metrics.py`), not the character itself: `KANJI_YAMA`, not `山`.
Until 15 September it was the `KanjiLearningItem` asset name, so renaming a file
in the Editor silently changed what is a foreign key in Phase 3; it no longer
depends on any file name. Two reasons — an ASCII identifier survives every layer between Unity and a
psql terminal without an encoding question, and the character alone does not say
which set or which authoring revision the item came from.

The character travels too, as `kanji_char`, on events where a human reading the
log needs it: `TRIAL_STARTED` and `ANSWER_SELECTED`.

## 5 · Events

### 5.1 Emitted in Phase 2

| Event | Additional payload fields |
|---|---|
| `STATE_ENTERED` | since 30 Sep: `transition_sound_lead_ms` (int or null) — see §5.9 |
| `TRIAL_SEQUENCE_GENERATED` | `block_state`, `kanji_set`, `seed`, `block_seed`, `seed_raw`, `trial_count`, `min_lag_requested`, `min_lag_achieved`, `distinct_pairs`, `ordering_attempts`, `sequence` — spec §6.1. See §5.8 |
| `TRIAL_STARTED` | `kanji_char`, `options` (ordered list of option ids as presented), `correct_option`, `hint_available` |
| `ANSWER_SELECTED` | `kanji_char`, `selected_option`, `is_correct`, `response_time_ms`, `timed_out` |
| `HINT_REQUESTED` | `hint_type` (array of cue names), `hint_available`, `time_since_trial_start_ms` |
| `TRIAL_COMPLETED` | `is_correct`, `response_time_ms`, `hint_count`, `cues_presented` (array of cue names); since 30 Sep the stimulus fields `feedback_shown`, `feedback_audio_source`, `feedback_audio_ms`, `result_sound`, `result_sound_offset_ms`, `result_sound_ms`, `card_animation` — see §5.9; since 30 Sep (F3.3) also `idle_ms`, `idle_episodes`, `idle_longest_ms` and their thresholds — see §5.10 |
| `KANJI_EXPOSED` | `kanji_id`, `kanji_char`, `exposure_index`, `discovery_type`, `exposure_ms`, `stage_ms` (array, one per derivation stage), `stages_authored`, `audio_played`, `audio_source` (`AUTHORED`, `TTS_PLACEHOLDER`, `NONE`), `assembly` (`RAY` when the assembly events follow; `NOT_IMPLEMENTED` when the scene has no assembly controller, as in the 25 Sep cut-off build) — S5, spec §7.6 |
| `ASSEMBLY_SEGMENT_PLACED` | `kanji_id`, `exposure_index`, `attempt` (1-based, counts right and wrong), `slot_index` (1-based), `segment_id`, `expected_segment_id`, `is_correct`, `selected_ms` and `placed_ms` (from the start of this kanji's assembly), `hint_shown`, `segments_authored` — one per placement attempt, spec §5.3, decision D4 |
| `ASSEMBLY_COMPLETED` | `kanji_id`, `exposure_index`, `duration_ms`, `incorrect_attempts`, `segment_count`, `segments_placed`, `hints_shown`, `row_order` (segment ids left to right as presented), `segments_authored`, `forced_by_researcher` — spec §5.3 |
| `ENVIRONMENT_APPLIED` | `profile_name`, `prop_count`, `mover_count`, `active_props` and `active_movers` (object names), `peripheral_interval_min_ms`, `peripheral_interval_max_ms`, `max_tier`, `seed` (the base seed of the environment), `seed_source` (`SESSION`, `FALLBACK` without a session, `OVERRIDE` in tests), `selection_seed` (derived for this level) — spec §8.1 |
| `PERIPHERAL_EVENT` | `event_index`, `object_name`, `duration_ms` — spec §8.1 |
| `START_SELECTED` | `reaction_ms`, `forced_by_researcher` — S1, spec §7.2 |
| `TUTORIAL_STARTED` | `activities` (array, in order: `CONTROLS_INTRO`, `LOOK_AND_SELECT`, `ASSEMBLY_EXAMPLE` since 30 Sep; only `LOOK_AND_SELECT` in M2), `pool` (kanji ids) — S2, spec §7.3 |
| `TUTORIAL_COMPLETED` | `trials`, `correct`; since 30 Sep also `controls_intro_ms` (-1 if no intro), `targets_hit`, `recentered` (bool: the Menu press was done, not skipped), `controller_callouts` (bool: the trigger and Menu were lit on the participant's controllers), `assembly_example` (kanji id or null) — S2 |
| `SYSTEM_CHECK_COMPLETED` | `headset_active`, `websocket_connected`, `passed`, `forced_by_researcher`, `eeg_checked` — S3, spec §7.4 |
| `BASELINE_STARTED` | `eyes_open_s`, `eyes_closed_s`, `time_scale` — S4, spec §7.5 |
| `BASELINE_COMPLETED` | `eyes_open_ms`, `eyes_closed_ms`, `time_scale`, `valid_duration` — S4 |
| `HEAD_AWAY` | `episode`, `onset_offset_ms`, `yaw_deg`, `pitch_deg`, `limit`, thresholds — since 30 Sep, §5.10 |
| `HEAD_RETURNED` | `episode`, `duration_ms`, `max_abs_yaw_deg`, `max_pitch_up_deg`, `max_pitch_down_deg`, `reason`, thresholds — since 30 Sep, §5.10 |
| `STAGE_INTRO_ACKNOWLEDGED` | `wait_ms`, `forced_by_researcher` — Continue on the announcement before S2, S4, S5, S6, S7 and S8 |
| `VIEW_RECENTERED` | `reason` (`SESSION_START`, `LEFT_MENU_BUTTON`, `KEYBOARD`), `yaw_error_deg`, `offset_m`, `camera_before` ([x,y,z]) — any state |

`options` and `correct_option` on `TRIAL_STARTED` are what make a trial
reconstructable without re-running the generator: they record what the
participant actually saw, in the order they saw it.

`hint_available` records whether assistance existed to be asked for, separately
from whether it was asked. Spec §11 lists "hint requested" and "hint available"
as two fields, and the distinction is the whole point of the on-request model in
§5.5: a participant who asks for help at LAL LOW and gets nothing is a different
observation from one who never asks.

Cue arrays (`hint_type`, `cues_presented`) carry cue names, not a flags integer:
`TARGET_READING_AUDIO`, `VISUAL_ASSOCIATION`, `REVERSE_SEMANTIC_ASSOCIATION`,
`VISUAL_TRANSFORMATION`. A bitmask in JSONB has to be decoded in every query and
cannot be filtered with `payload -> 'cues_presented' ? 'X'`.

### 5.9 Stimulus fields for the EEG analysis (since 30 September)

Phase 4 has to be able to cut or mark every EEG window in which something the
system put there sounded or moved (UI design v1.3, §8; approved 29 Sep). No new
event carries them: `TRIAL_COMPLETED` is emitted after `feedbackSeconds`, when
everything has already sounded, and `STATE_ENTERED` marks the stage boundary.

**Origin of every offset.** The feedback starts in the frame of
`ANSWER_SELECTED`: `ResponseSystemController` emits it and, in the same frame,
shows the feedback and plays the reading. Every `*_offset_ms` below is relative
to the `session_elapsed_ms` of that `ANSWER_SELECTED`.

**`select` rule.** The `select` sound plays in the frame of every
`ANSWER_SELECTED`, always (offset 0). It has no field of its own.

`TRIAL_COMPLETED`:

| Field | Type | Value |
|---|---|---|
| `feedback_shown` | bool | the trial's `ImmediateFeedback` |
| `feedback_audio_source` | string | `AUTHORED`, `TTS_PLACEHOLDER` or `NONE` (same vocabulary as `KANJI_EXPOSED.audio_source`) |
| `feedback_audio_ms` | int | length of the reading clip that sounded in the feedback; 0 if none |
| `result_sound` | string | `CORRECT`, `INCORRECT` or `NONE` |
| `result_sound_offset_ms` | int or null | **measured** offset of the result sound's `PlayOneShot` (planned: `feedback_audio_ms` + 150, or 0 with no reading); null when `result_sound` = `NONE` |
| `result_sound_ms` | int | length of the result clip; 0 if none |
| `card_animation` | string | `CORRECT_POP` or `NONE`; when `CORRECT_POP` it starts at offset 0 and lasts 570 ms |

Rules: `feedback_shown` = false implies `feedback_audio_ms` = 0, `result_sound`
= `NONE` and `card_animation` = `NONE`. The seven fields are built in one place
(`StimulusTelemetry.TrialCompletedFields`) so the rules hold by construction;
harness cases X2 and X3 check them.

`STATE_ENTERED`:

| Field | Type | Value |
|---|---|---|
| `transition_sound_lead_ms` | int or null | how long before this event the `stage` sound started (measured, ≈ 3500). Null on the first state of the session or when it did not sound. Since 30 Sep (UI design P7) the `stage` sound plays when each state ends and the next `STATE_ENTERED` follows 3.5 s later; measured from the frame `stage` was requested (audio output latency not included, same as `result_sound_offset_ms`) |

**Known limit.** The measured offset is the instant Unity asks for the sound.
The headset's audio output latency (DSP buffer and Link) is added afterwards and
is not visible here; it is measured once on the Phase 4 bench and applied as a
constant.

No `schema_version` bump (§5.6 precedent of 29 Sep): the fields are additive,
and rows written before 30 September simply do not have them.

### 5.10 Head away and idle time (Phase 3, F3.3 — since 30 September)

Every threshold here is **provisional, set in the Inspector and marked *to
validate***: the phase test (7–8 October) calibrates them. Each row carries the
values it was measured with, so rows written under different thresholds stay
comparable afterwards.

**Reference.** The angles are those of the head's forward direction relative to
the direction from the head to the centre of the Learning Board, recomputed every
frame from the current head position: yaw is left/right (positive right), pitch
is up/down (positive up). A re-center moves the rig, not the board, so the
reference survives it (the `VIEW_RECENTERED` row marks the discontinuity).

**When.** From the first `STATE_ENTERED` after S0 until the session ends, in every
state, S4 included: Phase 4 needs them wherever there is EEG. Only while the
headset is tracked.

#### `HEAD_AWAY`

Emitted when the head has stayed outside the task band for `min_away_ms`. The
row is written at confirmation, and `onset_offset_ms` says how long before that
the head actually left (≈ −`min_away_ms`), so the episode can be placed exactly.

| Field | Type | Value |
|---|---|---|
| `episode` | int | 1-based counter within the session |
| `onset_offset_ms` | int | ms from the moment the head left the band to this row (negative) |
| `yaw_deg`, `pitch_deg` | float | head angles at confirmation |
| `limit` | string | which limit was crossed first: `YAW`, `PITCH_UP`, `PITCH_DOWN` |
| `yaw_limit_deg`, `pitch_up_limit_deg`, `pitch_down_limit_deg` | float | thresholds in force |
| `min_away_ms` | int | dwell required to confirm |

#### `HEAD_RETURNED`

Emitted when the head is back inside the band (with `hysteresis_deg` of margin)
for `min_return_ms`, or when the episode has to be closed for another reason.

| Field | Type | Value |
|---|---|---|
| `episode` | int | same number as its `HEAD_AWAY` |
| `duration_ms` | int | from the moment the head left the band to the moment it came back |
| `max_abs_yaw_deg`, `max_pitch_up_deg`, `max_pitch_down_deg` | float | extremes reached during the episode |
| `reason` | string | `RETURNED`, `TRACKING_LOST` or `SESSION_END` |
| `hysteresis_deg`, `min_return_ms` | float, int | thresholds in force |

Every `HEAD_AWAY` has exactly one `HEAD_RETURNED` with the same `episode`. Both
carry the trial block when a trial is open, so an episode that starts inside a
trial is attributable to it; an episode may span trials, and the schema splits
it by time.

#### Idle time — fields on `TRIAL_COMPLETED`

Measured only in the response window (from `TRIAL_STARTED` to `ANSWER_SELECTED`).
A frame is idle when the head turns slower than `idle_head_deg_s` **and** every
tracked controller's ray turns slower than `idle_ray_deg_s`; only runs of idle
frames lasting at least `idle_min_ms` count.

| Field | Type | Value |
|---|---|---|
| `idle_ms` | int | total length of the counted idle runs |
| `idle_episodes` | int | how many runs |
| `idle_longest_ms` | int | the longest one |
| `idle_min_ms`, `idle_head_deg_s`, `idle_ray_deg_s` | int, float, float | thresholds in force |

Per-trial head-away time is **not** a field: it is derived in the schema from the
`HEAD_AWAY` / `HEAD_RETURNED` pairs, which stay the single owner of that fact.

No `schema_version` bump (§5.6): two new events and additive fields.

### 5.11 `DISTRACTOR_INTERACTION` (F5a, D5 — since 6 October)

Emitted by `DistractorMonitor` when the environment takes the participant's
attention. It is what lets the estimator tell "the room took it" (lower the
ESL) from "the head went elsewhere" (floor, ceiling, controllers), which
`HEAD_AWAY` alone cannot. Same angle frame as §5.10, and the task region is the
`HEAD_AWAY` band, so the two never disagree about where the task is.

Two kinds:

- **`DWELL`**: the head stays outside the task region and inside the angular
  box of an **active** prop, mover or peripheral widened by
  `box_margin_yaw_deg` and `box_margin_pitch_deg`, for at least `dwell_min_ms`.
  The pitch margin is the wider one: the head stops short of low objects and
  the eyes do the rest. Breaks shorter than `dwell_break_ms`
  do not split it. Emitted when the dwell ends.
- **`ORIENTING`**: within `orienting_window_ms` of a `PERIPHERAL_EVENT`, the head
  turns at least `orienting_min_deg` toward the object (the angular distance
  from the head to it shrinks by that much). Emitted when the window ends. No
  turn, no row: the orienting rate is counted against `PERIPHERAL_EVENT`.

| Field | Type | Value |
|---|---|---|
| `kind` | string | `DWELL` or `ORIENTING` |
| `object_name` | string | the object, as in `ENVIRONMENT_APPLIED` / `PERIPHERAL_EVENT`. For `DWELL`, the one whose box the head was nearest to for longest |
| `object_group` | string | `PROP`, `MOVER` or `PERIPHERAL` |
| `onset_offset_ms` | int | ms from the start (DWELL) or from the peripheral event (ORIENTING) to this row (negative) |
| `duration_ms` | int | DWELL: length of the dwell. ORIENTING: from the peripheral event to the largest turn |
| `peripheral_event_index` | int or null | ORIENTING: the `event_index` of the `PERIPHERAL_EVENT`. Null for DWELL |
| `head_turn_deg` | float | ORIENTING: the turn toward the object. DWELL: the closest the head got to the object's centre |
| `box_distance_deg` | float or null | DWELL: the closest the head got to the object's box (0 = inside). Null for ORIENTING |
| `dwell_min_ms`, `dwell_break_ms`, `box_margin_yaw_deg`, `box_margin_pitch_deg`, `orienting_min_deg`, `orienting_window_ms` | int, int, float, float, float, int | thresholds in force (*to validate*) |

Not trial-scoped; it carries the trial block when a trial is open. The
estimator counts a row for the trial open when it arrives, or for the next
trial of the same state if it arrives during the feedback
(`backend/app/adaptation/trials.py`).

**What it cannot see** (measured 6 October, `Medicion_D7_HeadAway.md`): looks
made with the eyes only, and looks at objects whose head direction stays inside
the task region (19–23° of yaw). The object name is the nearest box, often a
neighbour of the one actually looked at (the eyes do the last few degrees):
use it to read a session, not as a statistic.

Until migration `0003` the row lives only in `session_events`: `project_event`
skips unknown types without an error (§7).

### 5.8 `TRIAL_SEQUENCE_GENERATED` — the plan, not the outcome

Emitted once per block, **before the first trial of that block runs**, carrying
the whole planned sequence: for each entry, `trial_sequence`, `kanji_id`,
`trial_type`, the four `options` in presentation order, and `correct_option`.

Spec §6.1 asks for two things to be stored, not one: *"Random seeds and final
trial sequence are stored to permit exact session reconstruction."* The seed
alone would technically suffice — but only for as long as the generator that
consumed it still exists and still behaves identically. An analysis run six
months from now would depend on today's code. The expanded sequence does not.

**This is not a duplicate of `TRIAL_STARTED`, and the difference matters.**

| | Says |
|---|---|
| `TRIAL_SEQUENCE_GENERATED` | what was **planned** |
| `TRIAL_STARTED` × n | what actually **happened** |

**`seed` and `block_seed` (24 September).** `seed` is the session seed;
`block_seed` is the one this block was actually generated with, derived as
`StableHash("{seed}:block:{state}")` by `TrialSequenceGenerator.BlockSeed`.
Until the S1-S9 chain existed only one block ran per session, and it used the
session seed directly. With S6, S7 and S8 in one session that would make the
three blocks share every derived draw — including the option order of trial *i*
— so a kanji/type pair landing on the same position would put the correct answer
on the same card in every block. Reconstruction needs `block_seed`; the audit
trail needs to see which `seed` it came from. Both travel.

If a session aborts at trial 12 of 20, the two disagree — and that disagreement
*is* the datum: it records where the session was cut. A contract that stored only
one of them could not express it. This is a deliberate exception to the
one-fact-one-place rule that governs the rest of this document, and it is an
exception because the two records answer different questions.

`min_lag_requested` versus `min_lag_achieved` is the same idea applied to the
spacing constraint: the first is policy, the second is what the generator managed
to produce. When they differ, the sequence is still usable but the spacing
guarantee is weaker than intended, and the analysis should know without anyone
having to remember.

`seed_raw` is the seed as `experiment_sessions.random_seed` stores it — a string.
`seed` is the integer it was folded into, by a stable FNV-1a hash rather than
`String.GetHashCode()`, which .NET randomizes per process. Both are recorded
because reconstruction needs to be able to check the folding, not just trust it.

No trial context block: the event belongs to no single trial, it describes all of
them. It is therefore not in the set of events that require an open trial.

### 5.7 The two environmental events

`ENVIRONMENT_APPLIED` is emitted when a profile is **applied**, not when a level
change is requested. A level with no profile is refused and produces no event, so
the absence of the event means the scene did not change — rather than meaning it
might have.

Note what the payload does **not** carry: the level. It already travels in the
context block as `esl`, stamped by `BehaviorTelemetryController` from the same
component that owns it. Repeating it in the payload would put two copies of one
fact in one row, which is the failure this project has now hit five times. The
counts are in the payload precisely because they are *not* derivable from the
level: §8.1 gives ranges, and which value inside the range a session got is
decided by the seed.

`PERIPHERAL_EVENT` records each distraction individually. Phase 5 needs to
correlate a specific peripheral stimulus with what the participant did
immediately afterwards; a stimulus that acted on the session and left no trace is
a variable that cannot be reconstructed. It is deliberately distinct from
`DISTRACTOR_INTERACTION` (reserved, §5.2): this one is the system showing
something, that one is the participant reacting to it.

Neither bumps `schema_version`, by the rule in §5.6: both are new events, and no
existing row's shape changed.

### 5.5 Trial-cycle decisions this contract assumes

Four choices settled on 9 September that the payload shape depends on. Recorded
here because the shape does not explain them on its own.

- **Assistance is granted on request, not automatically.** LAL determines what is
  *available* for a given trial type (spec §9.1); the participant invokes it.
  This is the only reading that makes §11's "hint requested / hint available"
  pair meaningful and that justifies S2 teaching "Request Hint". `HINT_REQUESTED`
  is emitted even when nothing is available — asking and getting nothing is a
  behavioral observation, not a non-event.
- **Selection is commitment.** One step: choosing an option commits it, and the
  response clock stops there and nowhere else (spec §11.1, "participant commits
  to an answer"). A confirm step would put a second decision inside the response
  time.
- **Four options, always.** Chance level 25 %, and one set member is left out of
  each trial so the participant does not answer against a memorized grid of five.
  The count is fixed by the experiment and LAL may never change it (spec §9.3);
  the response system aborts a trial that arrives with a different count.
- **Meanings are shown in English.** They are the T1 prompt and the T2 options,
  so this is the content variable with the largest surface in the study.

### 5.6 A note on not bumping `schema_version`

`hint_available` was added on 9 September, after v1 was already in the database.
The version stays at 1 deliberately: it was added to `TRIAL_STARTED` and
`HINT_REQUESTED`, two events that had never been emitted before that day, so no
existing row's shape changed and no migration can be ambiguous about it.

The rule this sets: bump when an event that already exists in the database
changes shape, not when a new event is defined. Stated so the next person adding
a field does not have to guess which case they are in.

### 5.2 Reserved for Phase 3

`DISTRACTOR_INTERACTION` (still reserved; definition due before 5 October).
`HEAD_AWAY` / `HEAD_RETURNED` and idle time are defined in §5.10 since
30 September. Response-time variability stays derived: the schema computes it
over the observation window, and no event carries it.

### 5.3 Deviation from §11.1 — `ANSWER_CORRECT` / `ANSWER_INCORRECT`

Spec §11.1 lists `ANSWER_SELECTED`, `ANSWER_CORRECT` and `ANSWER_INCORRECT` as
three events. **This contract emits only `ANSWER_SELECTED`, carrying
`is_correct`.**

Three events for one participant action means three rows that can disagree —
an `ANSWER_SELECTED` marked correct with no matching `ANSWER_CORRECT` is a state
the schema permits and nothing prevents. One event with a boolean cannot
contradict itself. Correctness is a property of the answer, not an event in its
own right.

This needs an edit to spec §11.1 to stay true. Flagged rather than done, because
the spec is the source of truth and this document is not. **Confirmed by Sebas on
30 September 2026: they stay derived; the edit goes into spec v1.3.**

### 5.4 Deviation from §11 — naming convention

Spec §11 writes field names in camelCase (`trialId`, `kanjiId`). This contract
uses snake_case. The payload's destination is Postgres columns, the rest of the
schema is snake_case (`session_id`, `client_timestamp`, `server_received_at`),
and a JSONB key that becomes a column should not change convention on the way in.
The spec's camelCase is a field list, not a wire format.

## 6 · How the contract is enforced

Not by documentation. `BehaviorTelemetryController` owns the context and stamps
it; an emitter passes only the fields specific to its event and **cannot omit the
context block, because it never assembles one**.

```csharp
telemetry.SetState(GameFlowState.S7_ExperimentalRetrieval);
telemetry.SetLevels(esl, lal);
telemetry.BeginTrial(new TrialContext(...));

telemetry.Emit(TelemetryEvents.AnswerSelected, new Dictionary<string, object> {
    { "selected_option", optionId },
    { "is_correct", isCorrect },
    { "response_time_ms", rtMs },
});

telemetry.EndTrial();
```

Events emitted between `BeginTrial` and `EndTrial` carry the trial block; events
outside carry only the context block. Emitting a trial-scoped event with no trial
open logs an error naming the event, rather than silently shipping a payload with
no `trial_id`.

## 7 · How it is verified

`database/verify_events.sql` checks the payloads that actually arrived, not the
code that sent them. For the most recent session it reports events missing part
of the context block, trial-scoped events missing part of the trial block, enum
values that are not wire values, and the distribution of `event_type`. Phase 2
acceptance criterion 8 is met when it returns no offending rows.

One of its checks earns its place by catching what the obvious check misses.
A `session_elapsed_ms` of `-1` means the session clock was never installed, and
is trivially detectable. A clock installed with the wrong timezone is not: it
produces a positive, plausible-looking number — 32,400,000 ms is exactly the nine
hours of JST — and passes any "is it -1" filter. So the script also cross-checks
each reported elapsed against the one implied by the backend's own timestamps
(`server_received_at` minus `session_clock_started_at`), flagging disagreements
beyond five seconds. That tolerance covers network latency and queuing; it does
not cover an hour.

The backend does not reject a malformed payload. Losing telemetry because a field
is missing is the wrong trade — the same reasoning as the `STATE_ENTERED`
handler, which logs a warning and keeps the event. Detection belongs in a query
that someone runs, not in a rejection that discards data.

## 8 · Response time

`response_time_ms` is a primary experimental metric, so its definition is part of
the contract rather than an implementation detail.

- **Measured in Unity**, never derived from server timestamps. The difference
  between `client_timestamp` and `server_received_at` is network jitter, which
  M1 measured at 2–20 ms — the same order as the differences the study wants to
  detect.
- **Starts** when the prompt and all options are visible and interactive, not
  when the trial object is created. Presentation and animation time is not
  response time.
- **Stops** at answer commit, not at first touch or gaze.

Open: whether trials time out at all, and after how long. Spec §9.3 forbids LAL
from changing time pressure, but does not say whether a ceiling exists. The
`timed_out` field is in the contract so the shape does not change when the
question is answered; it is `false` in Phase 2.

## 9 · What does not go through this contract

Continuous sampling. Head pose at headset frame rate is roughly 72 samples per
second per session-minute; a 40-minute session would be ~170,000 rows in
`session_events` for one signal, in a table that also holds every discrete event.

`HEAD_AWAY` and `HEAD_RETURNED` are discrete events derived from a continuous
signal, and only the derived events belong here. Where the raw signal goes, if it
is kept at all, is a Phase 3–4 decision alongside the EEG stream — both are
continuous, both need the Session Clock, and they should be solved once rather
than twice.

## 10 · Where the context block comes from

The five context fields have exactly one owner each, and the telemetry
controller **reads** them rather than keeping copies:

| Field | Owner |
|---|---|
| `state` | `GameFlowController` |
| `esl` | `EnvironmentalStimulationController` |
| `lal` | `LearningAssistanceController` |
| `session_elapsed_ms` | `SessionClock` (static, zero installed from the backend) |
| `schema_version` | constant in `TelemetryContract` |

This is not a style preference; it is the fix for two bugs found on 9 September,
both the same shape. `TrialRequest` originally carried its own `state` and its
own `lal`. Those drove behavior — the `trial_id` prefix, and which cue LAL
granted — while the context block stamped separate copies that nothing kept up
to date. The result was payloads contradicting themselves: `state` reading
`S1_WELCOME_ORIENTATION` next to a `trial_id` of `S7-001`, and 19 trials
recorded as `lal: OFF` while the granted cues were the MEDIUM and HIGH rows of
§9.1.

Neither failed. Both would have corrupted the analysis silently — an assistance
study whose recorded assistance level is wrong for every trial. The second one
survived the fix for the first, because that fix only addressed the field that
had been pointed at.

**A value that exists in one place cannot desynchronize.** That is a stronger
guarantee than remembering to synchronize two, and it is why neither field
belongs in `TrialRequest`.

## 11 · Change log

**6 October 2026 (evening) — adjustments after the check session.** A short
headset session (`371b2c59`) checked D7 and D5 together. Two changes, both in
thresholds: `pitch_down_limit_deg` goes from 15 to 22, because fixing card 4
took the head to −18.5° and opened a false `HEAD_AWAY`; and the single
`box_margin_deg` of `DISTRACTOR_INTERACTION` becomes `box_margin_yaw_deg` 3 and
`box_margin_pitch_deg` 6, because a look at the side table kept the head 2–5°
above its box and no `DWELL` was emitted. Rows of that session carry the
earlier field (`box_margin_deg`); it is the only one that does.

**6 October 2026 — `DISTRACTOR_INTERACTION` (F5a, D5).** One new event type
(§5.11), reserved since Phase 3 and emitted from now on by `DistractorMonitor`;
no `schema_version` bump (§5.6). Not projected until migration `0003`.

**6 October 2026 — head-away thresholds from the task region (F5a, D7).** No
field changes. The defaults become `yaw_limit_deg` 24 (was 40),
`pitch_up_limit_deg` 12 (was 40), `pitch_down_limit_deg` 15 (was 35),
`hysteresis_deg` 3 (was 5) and `min_away_ms` 300 (was 500); `min_return_ms`
stays 200. Measured in the headset with two passes of `HeadAngleProbe`
(`Medicion_D7_HeadAway.md`): with the old values almost no look at the room fired
(the windows sit at 26–31° of yaw, the clock at 18–20° of pitch), while every
task fixation (board, cards, Hint, natural reading, scanning the cards) stays
inside the new limits and every head-turned look at the room leaves them. Quick
glances at the window lasted 0.45–0.73 s outside, so 500 ms missed half of them.
Not visible to any head threshold: looks made with the eyes only, and targets
at 19–23° of yaw, which overlap card 4. Still *to validate* with participants;
rows carry the thresholds in force, so rows before and after stay
distinguishable.

**5 October 2026 — pitch-down threshold.** No field changes. The default
`pitch_down_limit_deg` goes from 50 to 35. Measured in the headset: looking at
the floor puts the head at about −41° from the board direction (the eyes do the
rest), so with 50 no `PITCH_DOWN` episode could fire; the card row spans about
−17° to −25°, so 35 keeps a 10° margin below it. Still *to validate* in the
phase test. Rows carry the threshold in force (`pitch_down_limit_deg`), so rows
before and after the change stay distinguishable.

**1 October 2026 — schema v1 (F3.4).** The contract does not change. The
backend now projects every event into the relational tables of schema v1
(migration `0002`, `database/ERD.md`) right after storing it. The projection
reads the fields exactly as this document defines them, so a field renamed
here has to be renamed in `project_event` (PL/pgSQL, in
`backend/alembic/versions/sql/0002_schema_v1_up.sql`) in the same change, or
its rows end in `projection_errors`. `session_events` stays the source of
truth (§7).

**30 September 2026 — stage transition (UI design v1.3, P4/P7).** No new event
types and no `schema_version` bump.

- `STATE_ENTERED.transition_sound_lead_ms` is filled: every state after the
  first is preceded by the `stage` sound and a 3.5 s pause (was 2 s of
  silence), so the value is ≈ 3500. Null on S1. The pause sits before
  `STATE_ENTERED`, so no stage window contains it.
- The assembly plays the shared set: `place` and `incorrect` in the frame of
  `ASSEMBLY_SEGMENT_PLACED`, `done` right after `ASSEMBLY_COMPLETED` (not after
  a forced completion). There is still no hint sound.

**30 September 2026 — Phase 3, F3.3: head away and idle time.** Two new event
types (`HEAD_AWAY`, `HEAD_RETURNED`) and additive fields on `TRIAL_COMPLETED`
(idle time); no `schema_version` bump (§5.6). Definitions and provisional
thresholds in §5.10. `ANSWER_CORRECT` / `ANSWER_INCORRECT` confirmed as derived
(§5.3).

**30 September 2026 — stimulus telemetry for the EEG (UI design v1.3, §8).**
No new event types and no `schema_version` bump: additive fields (§5.9).

- `TRIAL_COMPLETED` gains `feedback_shown`, `feedback_audio_source`,
  `feedback_audio_ms`, `result_sound`, `result_sound_offset_ms`,
  `result_sound_ms` and `card_animation`.
- `STATE_ENTERED` gains `transition_sound_lead_ms`, null until the `stage`
  sound exists.
- Rule: the `select` sound plays in the frame of every `ANSWER_SELECTED`.
- The result sound (`correct` / `incorrect`) plays `feedback_audio_ms` + 150 ms
  after `ANSWER_SELECTED`, only with immediate feedback. `feedbackSeconds` is
  unchanged: the longest reading clip in the contract (魚, 576 ms) ends its
  result sound at 1196 ms of 1500.
- The 30 Sep tutorial entry below listed `TUTORIAL_STARTED.activities` in the
  first demo order; the order since round 2 is `CONTROLS_INTRO`,
  `LOOK_AND_SELECT`, `ASSEMBLY_EXAMPLE` (fixed in §5.1).

**30 September 2026 — tutorial for the demo.** No new event types and no
`schema_version` bump.

- S2 now runs a controls induction, the practice trials and then one worked
  assembly (`KANJI_YON`). `TUTORIAL_STARTED.activities` lists them in order;
  `TUTORIAL_COMPLETED` gains `controls_intro_ms`, `targets_hit`, `recentered`,
  `controller_callouts` and `assembly_example`.
- The worked assembly emits the normal `ASSEMBLY_SEGMENT_PLACED` /
  `ASSEMBLY_COMPLETED` with `state = S2_VR_TUTORIAL` and `exposure_index = 0`.
  Analyses of the learning block filter on `state = S5_STANDARDIZED_LEARNING`.
- `segments_authored` stays `false` for set A: the pieces now show the real
  strokes (images cut by `tools/assembly_segments.py`), but the segment ids and
  their count still come from `assemblyGroups`, not from authored
  `AssemblySegment` assets.

**29 September 2026 — Phase 3, F3.2: environment seeded by the session.** No
`schema_version` bump: new fields on `ENVIRONMENT_APPLIED`, and `seed` keeps its
type.

- `seed` now carries the **session seed** (`SESSION`). Until M2 every row
  carried the same value saved in the scene (`-1058336171`) regardless of the
  session. Rows written before this date must be read with that in mind.
- `seed_source`, `selection_seed`, `active_props` and `active_movers` added. The
  selection is per level (`selection:{LEVEL}`): the same level gives the same room
  anywhere in a session.
- Mover phase and peripheral-event draws also derive from the session seed. That
  is not visible in this row, but `PERIPHERAL_EVENT.object_name` and its timing
  are now reproducible for a given seed.

**28 September 2026 — guided assembly (worked on from 25 September, branch
`m2-assembly`).** No `schema_version` bump: one new event type, and
`ASSEMBLY_COMPLETED` gains fields on an event that had never been emitted.

- `ASSEMBLY_SEGMENT_PLACED`: one row per placement attempt, so the order and
  timing of each piece can be rebuilt (a counter of wrong attempts cannot).
- `ASSEMBLY_COMPLETED` is emitted for the first time. `row_order` makes the
  segment row reconstructible; it is also derivable from `block_seed`.
- `KANJI_EXPOSED.assembly` is `RAY` from this version on.
- Segments without authored content are placeholders, N = `assemblyGroups`
  from the contract; `segments_authored` says which case a row belongs to.

**25 September 2026 — S5 version 1.** No `schema_version` bump (§5.6).

- `KANJI_EXPOSED` is emitted for the first time, so its row now lists the fields
  it actually carries. `audio_source` exists so a TTS placeholder clip is never
  mistaken for a recording; `assembly` says explicitly that version 1 skips the
  step, so its absence does not read as a lost event.
- S5 guided association runs as trials `S5-001`…`S5-005`, one per kanji in set
  order, with their own `TRIAL_SEQUENCE_GENERATED`.
- `STAGE_INTRO_ACKNOWLEDGED`: the self-paced wait before six of the stages.

**24 September 2026 — the S1-S9 chain.** No `schema_version` bump: new event
types and one new field on an existing event, no existing field changed shape
(§5.6).

- `START_SELECTED`, `TUTORIAL_STARTED`, `TUTORIAL_COMPLETED`,
  `SYSTEM_CHECK_COMPLETED`, `BASELINE_STARTED`, `BASELINE_COMPLETED` — names from
  spec §7.2-§7.5. The M2 tutorial is look & select only, so its selections travel
  as ordinary `TRIAL_*` events with `S2-` trial ids instead of `TUTORIAL_SELECT`.
- `VIEW_RECENTERED`: a recenter redefines "forward", which Phase 3's head-away
  metrics measure against.
- `block_seed` on `TRIAL_SEQUENCE_GENERATED` (§5.8).
- §4.2 corrected: it still described `kanji_id` as the asset name, which stopped
  being true on 15 September.

**16 September 2026** — added `TRIAL_SEQUENCE_GENERATED` (§5.8). No
`schema_version` bump: a new event type, not a change to the shape of existing
payloads, which is the rule stated in §5.6.


**v1 — 8 September 2026.** First version. Context block, trial block,
deterministic `trial_id`, the seven Phase 2 events, and the two deviations from
spec §11 recorded in §5.3 and §5.4.

**9 September 2026 — response system.** No version bump; see §5.6.

- `hint_available` added to `TRIAL_STARTED` and `HINT_REQUESTED`.
- Cue arrays documented, with their four names.
- §5.5: the four trial-cycle decisions the payload shape assumes.
- §10: the context block's ownership rule, and the two bugs that produced it.
- `database/verify_trials.sql` added. It checks behavior where
  `verify_events.sql` checks shape: trial completeness, internal coherence
  between `ANSWER_SELECTED` and `TRIAL_COMPLETED`, option well-formedness, the
  T3 audio prohibition, and the granted cues against §9.1 — with the spec table
  transcribed independently of the C# so the check does not share its author's
  reading of the spec.

**11 September 2026 — environmental layer.** No version bump; see §5.6 and §5.7.

- `ENVIRONMENT_APPLIED` and `PERIPHERAL_EVENT` added. Both are new events, so no
  existing row's shape changed.
- `StimulationOrAssistanceLevel` gained `FOCUS` (S8) and `MINIMAL` (S3), which
  Appendix A required and the enum never had. This costs no migration: `esl` and
  `lal` live only in JSONB payloads — there is no Postgres enum for stimulation
  level, and `session_config_snapshots.config` is JSONB too. Checked before
  adding, not assumed.
- `FOCUS` is an **interpretation**, not a fact of the spec. §7.9 describes Focus
  Mode as "environment darkened/neutralized" while §3.3 keeps lighting stable
  across ESL levels and §8.3 puts lighting outside ESL. Implemented as zero props
  and zero peripheral events with lighting untouched, which preserves both
  invariants. Pending confirmation from the MIRAI reviewer; if the answer differs,
  it is one field in one asset.

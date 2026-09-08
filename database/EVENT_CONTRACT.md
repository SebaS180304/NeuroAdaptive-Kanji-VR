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
query result. Trials occur in four states (S5 guided association, S6, S7, S8), so
the state prefix is what keeps the sequence unambiguous.

The id is unique within a session, not globally. Phase 3's relational key is
`(session_id, trial_id)`.

### 4.2 `kanji_id`

The `KanjiLearningItem` asset name, not the character itself: `KANJI_YAMA`, not
`山`. Two reasons — an ASCII identifier survives every layer between Unity and a
psql terminal without an encoding question, and the character alone does not say
which set or which authoring revision the item came from.

The character travels too, as `kanji_char`, on events where a human reading the
log needs it: `TRIAL_STARTED` and `ANSWER_SELECTED`.

## 5 · Events

### 5.1 Emitted in Phase 2

| Event | Additional payload fields |
|---|---|
| `STATE_ENTERED` | — (context block only) |
| `TRIAL_STARTED` | `kanji_char`, `options` (ordered list of option ids as presented), `correct_option` |
| `ANSWER_SELECTED` | `kanji_char`, `selected_option`, `is_correct`, `response_time_ms`, `timed_out` |
| `HINT_REQUESTED` | `hint_type`, `time_since_trial_start_ms` |
| `TRIAL_COMPLETED` | `is_correct`, `response_time_ms`, `hint_count`, `cues_presented` |
| `KANJI_EXPOSED` | `kanji_char`, `discovery_type`, `exposure_ms` — S5 discovery sequence, spec §7.6 |
| `ASSEMBLY_COMPLETED` | `duration_ms`, `incorrect_attempts`, `segment_count` — spec §5.3 |

`options` and `correct_option` on `TRIAL_STARTED` are what make a trial
reconstructable without re-running the generator: they record what the
participant actually saw, in the order they saw it.

### 5.2 Reserved for Phase 3

`HEAD_AWAY`, `HEAD_RETURNED`, `DISTRACTOR_INTERACTION`, and the derived behavior
measures of §11 (idle time, response-time variability in the observation window).
Named here so Phase 2 does not accidentally use the names for something else.

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
the spec is the source of truth and this document is not.

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

## 10 · Change log

**v1 — 8 September 2026.** First version. Context block, trial block,
deterministic `trial_id`, the seven Phase 2 events, and the two deviations from
spec §11 recorded in §5.3 and §5.4.

"""
Trial records for the estimator, built from the session event stream.

The builder is incremental: it is fed events in arrival order (the order of
``session_events.id``) and returns a ``TrialRecord`` at each
``ANSWER_SELECTED``, which is when the backend decides (D1). The live path
and the replay of a recorded session feed it the same events in the same
order, so they produce the same records.

Attribution rules:

- **Time away (D4).** A ``HEAD_AWAY`` episode spans
  ``[onset, onset + duration]``, with ``onset = session_elapsed_ms +
  onset_offset_ms`` and the duration taken from the matching
  ``HEAD_RETURNED``. A trial gets the part of each episode that overlaps
  ``[TRIAL_STARTED, ANSWER_SELECTED]``. An episode still open at the answer
  counts up to the answer. Only episodes already received when the answer
  arrives count: that is all the backend knows when it decides.
- **Effective idle (D4).** ``idle_ms`` minus the time away of the same trial,
  floored at 0. ``idle_ms`` is read from ``ANSWER_SELECTED`` (added to the
  contract for F5a, §2.2) and, in sessions recorded before that change, from
  ``TRIAL_COMPLETED``, which arrives after the answer.
- **Environment events (D5).** ``DISTRACTOR_INTERACTION`` (``DWELL`` /
  ``ORIENTING``) and ``PERIPHERAL_EVENT`` count for the trial that is open when
  they arrive. If they arrive between an answer and the next
  ``TRIAL_STARTED`` (a periphery shown during the feedback, an orienting turn
  emitted 2 s after its periphery), they count for the next trial of the same
  state. Entering a new state drops what was pending.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Mapping

# The states whose trials the estimator uses.
S6_STATE = "S6_GUIDED_PRACTICE_CALIBRATION"
S7_STATE = "S7_EXPERIMENTAL_RETRIEVAL"


@dataclass(frozen=True)
class TrialRecord:
    """One answered trial, as the estimator sees it."""

    trial_id: str
    state: str | None
    trial_sequence: int | None
    trial_type: str
    is_correct: bool
    timed_out: bool
    rt_ms: int
    started_ms: int | None
    answered_ms: int
    idle_ms: int | None
    away_ms: int = 0
    env_dwell_ms: int = 0
    dwell_count: int = 0
    orienting_count: int = 0
    peripheral_count: int = 0
    hint_count: int | None = None
    esl: str | None = None
    lal: str | None = None

    @property
    def phase(self) -> str:
        """``S6`` / ``S7`` / ... from the trial id (``S7-008`` → ``S7``)."""
        return self.trial_id.split("-", 1)[0]

    @property
    def rt_valid(self) -> bool:
        """A timed-out trial has no usable response time."""
        return not self.timed_out and self.rt_ms > 0

    @property
    def idle_eff_ms(self) -> int | None:
        """Idle minus time away within the trial, floored at 0 (D4)."""
        if self.idle_ms is None:
            return None
        return max(0, self.idle_ms - self.away_ms)


@dataclass
class _AwayEpisode:
    onset_ms: int
    end_ms: int | None = None  # None while open


@dataclass
class _EnvCounts:
    dwell_ms: int = 0
    dwell_count: int = 0
    orienting_count: int = 0
    peripheral_count: int = 0

    def add_event(self, event_type: str, payload: Mapping[str, Any]) -> None:
        if event_type == "PERIPHERAL_EVENT":
            self.peripheral_count += 1
            return
        kind = payload.get("kind")
        if kind == "DWELL":
            self.dwell_ms += int(payload.get("duration_ms") or 0)
            self.dwell_count += 1
        elif kind == "ORIENTING":
            self.orienting_count += 1


@dataclass
class _OpenTrial:
    trial_id: str
    started_ms: int | None
    state: str | None
    env: _EnvCounts = field(default_factory=_EnvCounts)


def _int(value: Any) -> int | None:
    return None if value is None else int(value)


class TrialStreamBuilder:
    """Feeds on events in arrival order; returns a record at each answer."""

    def __init__(self) -> None:
        self.state: str | None = None
        self.levels: dict[str, str | None] = {"esl": None, "lal": None}
        self._open: _OpenTrial | None = None
        self._pending_env = _EnvCounts()
        self._episodes: dict[int, _AwayEpisode] = {}
        self._records: dict[str, TrialRecord] = {}
        self._order: list[str] = []

    # -- public -----------------------------------------------------------

    @property
    def records(self) -> list[TrialRecord]:
        """Every answered trial so far, in answer order."""
        return [self._records[t] for t in self._order]

    def feed(self, event_type: str, payload: Mapping[str, Any]) -> TrialRecord | None:
        """Process one event. Returns the new record on ``ANSWER_SELECTED``."""
        handler = getattr(self, f"_on_{event_type.lower()}", None)
        if handler is None:
            if event_type == "DISTRACTOR_INTERACTION":
                self._add_env(event_type, payload)
            return None
        return handler(payload)

    # -- handlers ---------------------------------------------------------

    def _on_state_entered(self, p: Mapping[str, Any]) -> None:
        self.state = p.get("state")
        self.levels = {"esl": p.get("esl"), "lal": p.get("lal")}
        self._open = None
        self._pending_env = _EnvCounts()

    def _on_trial_started(self, p: Mapping[str, Any]) -> None:
        self._open = _OpenTrial(
            trial_id=p["trial_id"],
            started_ms=_int(p.get("session_elapsed_ms")),
            state=self.state,
            env=self._pending_env,
        )
        self._pending_env = _EnvCounts()

    def _on_peripheral_event(self, p: Mapping[str, Any]) -> None:
        self._add_env("PERIPHERAL_EVENT", p)

    def _on_head_away(self, p: Mapping[str, Any]) -> None:
        onset = int(p.get("session_elapsed_ms") or 0) + int(p.get("onset_offset_ms") or 0)
        self._episodes[int(p["episode"])] = _AwayEpisode(onset_ms=onset)

    def _on_head_returned(self, p: Mapping[str, Any]) -> None:
        episode = self._episodes.get(int(p["episode"]))
        if episode is not None and p.get("duration_ms") is not None:
            episode.end_ms = episode.onset_ms + int(p["duration_ms"])

    def _on_answer_selected(self, p: Mapping[str, Any]) -> TrialRecord:
        trial_id = p["trial_id"]
        answered = int(p.get("session_elapsed_ms") or 0)
        open_trial = self._open if self._open and self._open.trial_id == trial_id else None
        started = open_trial.started_ms if open_trial else None
        env = open_trial.env if open_trial else _EnvCounts()
        rt = int(p.get("response_time_ms") or 0)
        if started is None:
            started = answered - rt
        record = TrialRecord(
            trial_id=trial_id,
            state=open_trial.state if open_trial else self.state,
            trial_sequence=_int(p.get("trial_sequence")),
            trial_type=p.get("trial_type") or "UNKNOWN",
            is_correct=bool(p.get("is_correct")),
            timed_out=bool(p.get("timed_out")),
            rt_ms=rt,
            started_ms=started,
            answered_ms=answered,
            idle_ms=_int(p.get("idle_ms")),
            away_ms=self._away_overlap(started, answered),
            env_dwell_ms=env.dwell_ms,
            dwell_count=env.dwell_count,
            orienting_count=env.orienting_count,
            peripheral_count=env.peripheral_count,
            esl=p.get("esl"),
            lal=p.get("lal"),
        )
        self._open = None
        self._records[trial_id] = record
        self._order.append(trial_id)
        return record

    def _on_trial_completed(self, p: Mapping[str, Any]) -> None:
        """Fills idle and hints for sessions recorded before §2.2."""
        record = self._records.get(p.get("trial_id"))
        if record is None:
            return
        updates: dict[str, Any] = {}
        if record.idle_ms is None and p.get("idle_ms") is not None:
            updates["idle_ms"] = int(p["idle_ms"])
        if p.get("hint_count") is not None:
            updates["hint_count"] = int(p["hint_count"])
        if updates:
            self._records[record.trial_id] = replace(record, **updates)

    # -- helpers ----------------------------------------------------------

    def _add_env(self, event_type: str, payload: Mapping[str, Any]) -> None:
        target = self._open.env if self._open is not None else self._pending_env
        target.add_event(event_type, payload)

    def _away_overlap(self, start: int, end: int) -> int:
        total = 0
        for episode in self._episodes.values():
            ep_end = episode.end_ms if episode.end_ms is not None else end
            overlap = min(ep_end, end) - max(episode.onset_ms, start)
            if overlap > 0:
                total += overlap
        return total


def build_trials(events: Iterable[Mapping[str, Any]]) -> list[TrialRecord]:
    """Records of one session from its events, already in arrival order.

    Each event is a mapping with ``event_type`` and ``payload`` (a row of
    ``session_events``). The records reflect every event, including
    ``TRIAL_COMPLETED`` (idle in recorded sessions, hints).
    """
    builder = TrialStreamBuilder()
    for event in events:
        builder.feed(event["event_type"], event.get("payload") or {})
    return builder.records

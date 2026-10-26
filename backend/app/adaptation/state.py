"""
Per-session adaptation state in memory (Planteamiento_Tecnico_F5a.md §2.2).

One ``SessionAdaptationState`` per open session. It is fed every stored
event in arrival order, as the WebSocket stores them, and at each answered S7
trial of an adaptive session it returns the rule engine's decision. The S6
profile is computed once, when S7 is entered; after that each trial adds one
record, and nothing queries ``trial_timeline``.

**Levels in force.** Before deciding, the engine takes the ESL and LAL that
the answer itself reports (the context block of ``ANSWER_SELECTED``). A change
that Unity applied shows up there; one it skipped (``ADAPTATION_SKIPPED``:
timeout, guard) does not, and the engine corrects itself instead of believing
its own decision. This is what ``EngineState.with_levels`` is for.

**Reconnection.** The state holds nothing that is not in ``session_events``:
when the WebSocket reconnects, ``rebuild`` feeds the stored events again and
gets the same state, decisions included (estimator and engine are pure). The
decision id is ``d-<trial_id>`` (one decision per trial), so a rebuilt state
names its decisions exactly as the live one did.

**Outcomes (O4, outcome.py).** Each change waits for the three trials of its
cooldown: at the answer of N+1 the reported level says whether Unity applied
it, and at the answer of N+3 the window N+1…N+3 is classified.
``take_outcomes()`` hands the ``ADAPTATION_OUTCOME`` payloads to the caller;
leaving S7 with a change still open classifies it ``UNCERTAIN``. A rebuild
discards the outcomes it recomputes: they were already stored.

**Version.** A new session runs with the current estimator (and the rules
that go with it); a rebuild keeps the version its stored decisions name, so a
session never changes version halfway (D-F6-59).

STATIC, and every state other than S7, never reaches the estimator
(criterion 5): ``adaptation_allowed`` gates it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from app.adaptation.estimator import (
    DEFAULT_THRESHOLDS,
    ESTIMATOR_VERSION,
    ESTIMATOR_VERSIONS,
    EstimatorResult,
    estimate,
)
from app.adaptation.indicators import window_indicators, window_trials
from app.adaptation.outcome import POST_WINDOW, classify
from app.adaptation.profile import S6Profile, build_profile
from app.adaptation.rules import (
    DEFAULT_CONFIG,
    Decision,
    EngineState,
    adaptation_allowed,
    decide,
    initial_state,
)
from app.adaptation.trials import S7_STATE, TrialStreamBuilder

ANSWER_SELECTED = "ANSWER_SELECTED"
STATE_ENTERED = "STATE_ENTERED"
ADAPTATION_DECISION = "ADAPTATION_DECISION"
ADAPTATION_OUTCOME = "ADAPTATION_OUTCOME"

# The context block copied from the ANSWER_SELECTED that triggered a decision,
# so ADAPTATION_DECISION passes verify_events.sql like any Unity event (§8.3).
CONTEXT_KEYS = (
    "schema_version", "state", "session_elapsed_ms", "esl", "lal",
    "trial_id", "trial_type", "trial_sequence", "kanji_id",
)


@dataclass(frozen=True)
class PendingDecision:
    """A decision ready to send, with what is needed to store it afterwards."""

    decision_id: str
    decision: Decision
    trigger: Mapping[str, Any]   # payload of the ANSWER_SELECTED that produced it

    def message(self) -> dict[str, Any]:
        """The ``DECISION`` message to Unity (§8.1)."""
        d = self.decision
        return {
            "type": "DECISION",
            "decision_id": self.decision_id,
            "trial_id": d.trial_id,
            "action": d.action,
            "dimension": d.dimension,
            "from_level": d.from_level,
            "to_level": d.to_level,
            "proactive_cues": d.proactive_cues,
            "learner_state": d.learner_state,
            "cause": d.cause,
            "confidence": round(d.confidence, 3),
            "reason_code": d.reason_code,
            "explanation": d.explanation,
            "cooldown_until_trial": d.cooldown_until_trial,
        }

    def event_payload(self, decision_latency_ms: float | None) -> dict[str, Any]:
        """Payload of the ``ADAPTATION_DECISION`` row (§8.3)."""
        payload = {k: self.trigger.get(k) for k in CONTEXT_KEYS if k in self.trigger}
        payload.update(self.decision.as_dict())
        estimator = self.decision.estimator or {}
        payload.update({
            "source": "BACKEND",
            "decision_id": self.decision_id,
            "decision_latency_ms": None if decision_latency_ms is None else round(decision_latency_ms, 2),
            "indicators": estimator.get("indicators"),
            "evidence": estimator.get("evidence"),
            "conditions": estimator.get("conditions"),
            "support": estimator.get("support"),
            "estimator_version": estimator.get("estimator_version"),
            "rules_version": self.decision.version,
            "thresholds": {"estimator": DEFAULT_THRESHOLDS.as_dict(), "rules": DEFAULT_CONFIG.as_dict()},
        })
        return payload


@dataclass
class _OpenChange:
    """A change waiting for its post window (O4)."""

    decision: dict[str, Any]
    pre: EstimatorResult
    seq: int
    applied: bool | None = None


def stored_version(events: Iterable[Mapping[str, Any]]) -> str | None:
    """The estimator version of a session's stored decisions, or None if it has none."""
    for event in events:
        if event["event_type"] == ADAPTATION_DECISION:
            version = (event.get("payload") or {}).get("estimator_version")
            if version in ESTIMATOR_VERSIONS:
                return version
    return None


def decision_id_for(trial_id: str | None) -> str:
    """One decision per trial, so the trial names it; rebuilds agree with the live run."""
    return f"d-{trial_id}"


class SessionAdaptationState:
    """Everything the live path needs to decide for one session."""

    def __init__(self, condition: str | None, version: str = ESTIMATOR_VERSION) -> None:
        self.condition = condition
        self.version = version
        self.builder = TrialStreamBuilder()
        self.profile: S6Profile | None = None
        self.engine: EngineState | None = None
        self.decisions: dict[str, Decision] = {}
        self._open: list[_OpenChange] = []
        self._outcomes: list[dict[str, Any]] = []

    @property
    def adaptive(self) -> bool:
        return adaptation_allowed(S7_STATE, self.condition)

    def feed(self, event_type: str, payload: Mapping[str, Any]) -> PendingDecision | None:
        """Process one stored event; returns a decision for an answered adaptive S7 trial."""
        payload = payload or {}
        record = self.builder.feed(event_type, payload)

        if event_type == STATE_ENTERED:
            if payload.get("state") == S7_STATE:
                self._enter_s7(payload)
            elif self._open:
                self._close_open(payload, post=None)     # S7 ended first: UNCERTAIN
            return None

        if record is None or record.phase != "S7" or self.engine is None:
            return None
        if not adaptation_allowed(record.state, self.condition):
            return None

        # the levels Unity reports, not the ones the engine assumed (skips)
        self.engine = self.engine.with_levels(esl=payload.get("esl"), lal=payload.get("lal"))

        trials = self.builder.records
        window = window_indicators(window_trials(trials, record.trial_id), self.profile)
        result = estimate(window, self.profile, version=self.version)
        seq = record.trial_sequence or int(record.trial_id.split("-")[1])
        decision, self.engine = decide(result, seq, record.answered_ms, self.engine)
        self.decisions[record.trial_id] = decision
        pending = PendingDecision(decision_id=decision_id_for(record.trial_id), decision=decision,
                                  trigger=dict(payload))

        # O4: was the last change applied (first trial after it), and is its post window complete?
        for change in self._open:
            if seq == change.seq + 1:
                dim = change.decision.get("dimension")
                reported = payload.get("esl") if dim == "ESL" else payload.get("lal")
                change.applied = reported == change.decision.get("to_level")
        done = [c for c in self._open if seq >= c.seq + POST_WINDOW or c.applied is False]
        if done:
            self._close_open(payload, post=result, which=done)
        if decision.is_change:
            self._open.append(_OpenChange({**decision.as_dict(), "decision_id": pending.decision_id},
                                          result, seq))
        return pending

    def take_outcomes(self) -> list[dict[str, Any]]:
        """``ADAPTATION_OUTCOME`` payloads ready to store, oldest first; empties the list."""
        out, self._outcomes = self._outcomes, []
        return out

    def _close_open(self, trigger: Mapping[str, Any], post: EstimatorResult | None,
                    which: list[_OpenChange] | None = None) -> None:
        which = list(self._open) if which is None else which
        for change in which:
            outcome = classify(change.decision, change.pre, post, applied=change.applied is not False)
            payload = {k: trigger.get(k) for k in CONTEXT_KEYS if k in trigger}
            payload.update(outcome.as_dict())
            payload.update({"source": "BACKEND", "decision_seq": change.seq})
            self._outcomes.append(payload)
            self._open.remove(change)

    def _enter_s7(self, payload: Mapping[str, Any]) -> None:
        if not self.adaptive:
            return
        self.profile = build_profile(self.builder.records)
        started = payload.get("session_elapsed_ms")
        self.engine = initial_state(payload.get("esl"), payload.get("lal"),
                                    None if started is None else int(started))

    @classmethod
    def rebuild(cls, condition: str | None, events: Iterable[Mapping[str, Any]],
                version: str | None = None) -> "SessionAdaptationState":
        """The state after the stored events, e.g. when the WebSocket reconnects."""
        events = list(events)
        state = cls(condition, version or stored_version(events) or ESTIMATOR_VERSION)
        for event in events:
            state.feed(event["event_type"], event.get("payload") or {})
        state.take_outcomes()     # already stored by the live run
        return state

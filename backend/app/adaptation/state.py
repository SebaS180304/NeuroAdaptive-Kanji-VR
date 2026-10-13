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
gets the same state, decisions included (estimator and engine are pure).

STATIC, and every state other than S7, never reaches the estimator
(criterion 5): ``adaptation_allowed`` gates it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from app.adaptation.estimator import DEFAULT_THRESHOLDS, ESTIMATOR_VERSION, estimate
from app.adaptation.indicators import window_indicators, window_trials
from app.adaptation.profile import S6Profile, build_profile
from app.adaptation.rules import (
    DEFAULT_CONFIG,
    RULES_VERSION,
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
            "estimator_version": ESTIMATOR_VERSION,
            "rules_version": RULES_VERSION,
            "thresholds": {"estimator": DEFAULT_THRESHOLDS.as_dict(), "rules": DEFAULT_CONFIG.as_dict()},
        })
        return payload


class SessionAdaptationState:
    """Everything the live path needs to decide for one session."""

    def __init__(self, condition: str | None) -> None:
        self.condition = condition
        self.builder = TrialStreamBuilder()
        self.profile: S6Profile | None = None
        self.engine: EngineState | None = None
        self.decisions: dict[str, Decision] = {}

    @property
    def adaptive(self) -> bool:
        return adaptation_allowed(S7_STATE, self.condition)

    def feed(self, event_type: str, payload: Mapping[str, Any]) -> PendingDecision | None:
        """Process one stored event; returns a decision for an answered adaptive S7 trial."""
        payload = payload or {}
        record = self.builder.feed(event_type, payload)

        if event_type == STATE_ENTERED and payload.get("state") == S7_STATE:
            self._enter_s7(payload)
            return None

        if record is None or record.phase != "S7" or self.engine is None:
            return None
        if not adaptation_allowed(record.state, self.condition):
            return None

        # the levels Unity reports, not the ones the engine assumed (skips)
        self.engine = self.engine.with_levels(esl=payload.get("esl"), lal=payload.get("lal"))

        trials = self.builder.records
        window = window_indicators(window_trials(trials, record.trial_id), self.profile)
        result = estimate(window, self.profile)
        seq = record.trial_sequence or int(record.trial_id.split("-")[1])
        decision, self.engine = decide(result, seq, record.answered_ms, self.engine)
        self.decisions[record.trial_id] = decision
        return PendingDecision(decision_id=f"d-{uuid.uuid4().hex[:12]}", decision=decision, trigger=dict(payload))

    def _enter_s7(self, payload: Mapping[str, Any]) -> None:
        if not self.adaptive:
            return
        self.profile = build_profile(self.builder.records)
        started = payload.get("session_elapsed_ms")
        self.engine = initial_state(payload.get("esl"), payload.get("lal"),
                                    None if started is None else int(started))

    @classmethod
    def rebuild(cls, condition: str | None, events: Iterable[Mapping[str, Any]]) -> "SessionAdaptationState":
        """The state after the stored events, e.g. when the WebSocket reconnects."""
        state = cls(condition)
        for event in events:
            state.feed(event["event_type"], event.get("payload") or {})
        return state

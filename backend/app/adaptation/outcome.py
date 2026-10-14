"""
Outcome of each adaptation, O4 (Planteamiento_Tecnico_F5a.md §9; decided with Sebas on 14 Oct).

**Windows.** *Pre* is the window the change was decided on (trials N−2…N).
*Post* is the three trials of the cooldown, N+1…N+3: the first three played at
the new level. No other change can land there (the cooldown forbids it), the
4-trial tail freeze keeps them inside S7, and they are the D9 window of a LAL
raise, so the outcome measures the change while it is being felt.

**Rule: state + key indicator.** The post window goes through the same
estimator. A state whose confidence is under the engine's 0.5 counts as
``STABLE``, as the rule engine reads it.

Rescue changes (``OVERLOADED``, ``DISENGAGED_*``):

| Post window | Outcome | ``reason_code`` |
| --- | --- | --- |
| ``STABLE`` | ``POSITIVE`` | ``RESOLVED`` |
| the other bad state | ``NEGATIVE`` | ``SWITCHED`` |
| same state, key indicator worse | ``NEGATIVE`` | ``PERSISTED_WORSE`` |
| same state, key indicator better | ``NEUTRAL`` | ``PARTIAL`` |
| same state, no change beyond the dispersion | ``NEUTRAL`` | ``PERSISTED`` |

Returns towards MEDIUM (``STABLE_RETURN``): the point is to remove help or
lower the room without a relapse.

| Post window | Outcome | ``reason_code`` |
| --- | --- | --- |
| ``STABLE``, no drop | ``POSITIVE`` | ``HELD`` |
| ``STABLE``, accuracy or pace dropped beyond the dispersion | ``NEUTRAL`` | ``HELD_WITH_DROP`` |
| ``OVERLOADED`` or ``DISENGAGED`` | ``NEGATIVE`` | ``RELAPSED`` |

``UNCERTAIN``: the change was not applied (the next answer reports the old
level; ``NOT_APPLIED``) or S7 ended before the post window closed
(``INCOMPLETE``).

**Key indicator and "beyond the dispersion"** (*to validate*):

- ``OVERLOADED``: accuracy and pace. Worse = one more error in the window
  (``acc_delta`` down by ≥ 1/3) or ``rt_z`` up by ≥ 1 (one S6 dispersion);
  better = the opposite.
- ``DISENGAGED`` (``ENVIRONMENT`` / ``AWAY``): time away + time on room objects.
  Worse / better = a change of ≥ 1500 ms, the estimator's own threshold.
- ``DISENGAGED`` (``IMPULSIVE``): fast errors. Worse / better = one more / fewer.

Pure, like the estimator: the live path and the replay give the same outcome.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from app.adaptation.estimator import (
    DEFAULT_THRESHOLDS,
    DISENGAGED,
    IMPULSIVE,
    OVERLOADED,
    STABLE,
    EstimatorResult,
)
from app.adaptation.rules import DEFAULT_CONFIG, STABLE_RETURN

OUTCOME_VERSION = "outcome-v1"
POST_WINDOW = 3

POSITIVE = "POSITIVE"
NEUTRAL = "NEUTRAL"
NEGATIVE = "NEGATIVE"
UNCERTAIN = "UNCERTAIN"

ONE_ERROR = 0.3                   # one answer of three (1/3; the indicators are rounded to 3 decimals)
RT_Z_STEP = 1.0                   # one S6 dispersion
DISTRACTION_STEP_MS = DEFAULT_THRESHOLDS.away_ms


@dataclass(frozen=True)
class Outcome:
    decision_id: str | None
    decision_trial_id: str | None
    outcome: str
    reason_code: str
    explanation: str
    pre: dict[str, Any] = field(default_factory=dict)
    post: dict[str, Any] = field(default_factory=dict)
    version: str = OUTCOME_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "decision_trial_id": self.decision_trial_id,
            "outcome": self.outcome,
            "outcome_reason": self.reason_code,
            "outcome_explanation": self.explanation,
            "pre": self.pre,
            "post": self.post,
            "outcome_version": self.version,
        }


def effective_state(result: EstimatorResult | Mapping[str, Any]) -> str:
    """The state as the rule engine reads it: under 0.5 of confidence, STABLE."""
    state, conf = _get(result, "state"), _get(result, "confidence")
    if state != STABLE and conf is not None and conf < DEFAULT_CONFIG.min_confidence:
        return STABLE
    return state


def _get(result: EstimatorResult | Mapping[str, Any], key: str) -> Any:
    return result.get(key) if isinstance(result, Mapping) else getattr(result, key)


def _ind(result: EstimatorResult | Mapping[str, Any]) -> Mapping[str, Any]:
    return _get(result, "indicators") or {}


def _summary(result: EstimatorResult | Mapping[str, Any]) -> dict[str, Any]:
    ind = _ind(result)
    return {
        "state": effective_state(result),
        "estimated_state": _get(result, "state"),
        "cause": _get(result, "cause"),
        "confidence": round(_get(result, "confidence") or 0.0, 3),
        "trial_ids": ind.get("trial_ids"),
        "acc_delta": ind.get("acc_delta"),
        "rt_ratio": ind.get("rt_ratio"),
        "rt_z": ind.get("rt_z"),
        "away_ms": ind.get("away_ms"),
        "env_dwell_ms": ind.get("env_dwell_ms"),
        "fast_errors": ind.get("fast_errors"),
    }


def _num(v: Any, default: float = 0.0) -> float:
    return float(v) if isinstance(v, (int, float)) else default


def _overload_trend(pre: Mapping[str, Any], post: Mapping[str, Any]) -> int:
    """+1 better, -1 worse, 0 within the dispersion (accuracy and pace)."""
    d_acc = _num(post.get("acc_delta")) - _num(pre.get("acc_delta"))
    d_z = _num(post.get("rt_z")) - _num(pre.get("rt_z"))
    if d_acc <= -ONE_ERROR or d_z >= RT_Z_STEP:
        return -1
    if d_acc >= ONE_ERROR or d_z <= -RT_Z_STEP:
        return 1
    return 0


def _distraction_trend(pre: Mapping[str, Any], post: Mapping[str, Any]) -> int:
    pre_ms = _num(pre.get("away_ms")) + _num(pre.get("env_dwell_ms"))
    post_ms = _num(post.get("away_ms")) + _num(post.get("env_dwell_ms"))
    if post_ms - pre_ms >= DISTRACTION_STEP_MS:
        return -1
    if pre_ms - post_ms >= DISTRACTION_STEP_MS:
        return 1
    return 0


def _impulsive_trend(pre: Mapping[str, Any], post: Mapping[str, Any]) -> int:
    d = _num(post.get("fast_errors")) - _num(pre.get("fast_errors"))
    return -1 if d >= 1 else 1 if d <= -1 else 0


def _numbers(post: Mapping[str, Any]) -> str:
    parts = []
    if isinstance(post.get("acc_delta"), (int, float)):
        parts.append(f"accuracy {post['acc_delta']:+.2f} against practice")
    if isinstance(post.get("rt_ratio"), (int, float)):
        parts.append(f"pace {post['rt_ratio']:.2f}× practice")
    away = _num(post.get("away_ms")) + _num(post.get("env_dwell_ms"))
    if away:
        parts.append(f"{away / 1000:.1f} s looking away or at the room")
    return "; ".join(parts)


def classify(
    decision: Mapping[str, Any],
    pre: EstimatorResult | Mapping[str, Any],
    post: EstimatorResult | Mapping[str, Any] | None,
    applied: bool = True,
) -> Outcome:
    """Outcome of one change, from the decision, its window and the post window.

    ``decision`` is the decision as a dict (``Decision.as_dict()`` or the
    ``ADAPTATION_DECISION`` payload), ``pre`` the estimator result it was decided
    on, ``post`` the estimator result of the window ending at N+3 (None when S7
    ended before it closed).
    """
    did, tid = decision.get("decision_id"), decision.get("trial_id")
    reason = decision.get("reason_code")
    pre_s = _summary(pre)

    def out(result: str, code: str, text: str, post_s: dict | None = None) -> Outcome:
        return Outcome(did, tid, result, code, text, pre_s, post_s or {})

    if not applied:
        return out(UNCERTAIN, "NOT_APPLIED", "Uncertain: the change was not applied in Unity.")
    post_ind = _ind(post) if post is not None else {}
    if post is None or (post_ind.get("n") or 0) < POST_WINDOW:
        return out(UNCERTAIN, "INCOMPLETE", "Uncertain: S7 ended before the 3 trials after the change.")

    post_s = _summary(post)
    now = post_s["state"]
    nums = _numbers(post_s)

    if reason == STABLE_RETURN:
        if now != STABLE:
            return out(NEGATIVE, "RELAPSED", f"Negative: {now} again in the 3 trials after going back "
                       f"towards MEDIUM ({nums}).", post_s)
        if _overload_trend(pre_s, post_s) < 0:
            return out(NEUTRAL, "HELD_WITH_DROP", f"Neutral: still stable after going back towards MEDIUM, "
                       f"but accuracy or pace dropped ({nums}).", post_s)
        return out(POSITIVE, "HELD", f"Positive: still stable after going back towards MEDIUM ({nums}).", post_s)

    was = pre_s["state"] if pre_s["state"] in (OVERLOADED, DISENGAGED) else decision.get("learner_state")
    if now == STABLE:
        return out(POSITIVE, "RESOLVED", f"Positive: {was} gone in the 3 trials after the change ({nums}).", post_s)
    if now != was:
        return out(NEGATIVE, "SWITCHED", f"Negative: {now} instead of {was} after the change ({nums}).", post_s)

    if was == OVERLOADED:
        trend = _overload_trend(pre_s, post_s)
    elif pre_s.get("cause") == IMPULSIVE:
        trend = _impulsive_trend(pre_s, post_s)
    else:
        trend = _distraction_trend(pre_s, post_s)
    if trend < 0:
        return out(NEGATIVE, "PERSISTED_WORSE", f"Negative: still {was}, and worse ({nums}).", post_s)
    if trend > 0:
        return out(NEUTRAL, "PARTIAL", f"Neutral: still {was}, but better ({nums}).", post_s)
    return out(NEUTRAL, "PERSISTED", f"Neutral: still {was}, without a clear change ({nums}).", post_s)

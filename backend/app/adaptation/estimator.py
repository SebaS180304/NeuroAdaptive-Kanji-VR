"""
Estimator v1: state, cause and confidence of one window (Planteamiento_Tecnico_F5a.md §4.3).

Readable rules, not a trained model: with two recorded sessions there is
nothing to train on, and every decision has to be explainable.

| State | Condition (thresholds *to validate*) |
| --- | --- |
| ``DISENGAGED`` | ``away_ms`` ≥ 1500 **or** ``env_dwell_ms`` ≥ 1500 **or** ``fast_errors`` ≥ 2 |
| ``OVERLOADED`` | ``slow_errors`` ≥ 2 **or** (``rt_z`` ≥ 2 **and** ``acc_delta`` ≤ −0.34) **or** (``idle_eff_ratio`` ≥ 0.3 **and** ``acc_delta`` ≤ −0.34) |
| ``STABLE`` | None of the above |

- If both hold, ``DISENGAGED`` wins: attention elsewhere explains the
  performance, and acting on difficulty would treat the symptom.
- **Cause** (for D3, only for ``DISENGAGED``): ``ENVIRONMENT`` when the room
  took the attention (``env_dwell_ms`` over its threshold, or more orienting
  turns per peripheral than in S6); ``AWAY`` when only the time away does;
  ``IMPULSIVE`` when only fast errors do.
- **Confidence (0–1)** = coverage × profile reliability × support.
  Coverage is ``n / 3`` (a window not yet full counts less); reliability comes
  from the profile (1.0 with ≥ 6 valid S6 trials, 0.6 with fewer); support
  grows with how many of the state's conditions hold: 1 of 3 → 0.6, 2 → 0.8,
  3 → 1.0, i.e. ``(2 + met) / (2 + total)``. The rule engine ignores states
  with confidence < 0.5, so a single condition is enough with a full window
  and a reliable profile, and not enough with an unreliable one.

  The plan's wording was "proportion of the condition's indicators that hold";
  read literally, one condition of three gives 0.33 and no single-signal state
  could ever act (OBS_01's two slow errors included). The support formula keeps
  the intent (more evidence, more confidence) with a floor. *To validate*.

The idle clause asks for the same accuracy drop as the RT clause (≤ −0.34,
in practice two errors in the window), not just ``acc_delta`` < 0 as in the
plan: with ``< 0`` a single error plus idle was enough (OBS_01, S7-017..019),
and the plan's own check says S7-017 alone must not be. *To validate*.

Pure function of the window and the profile: the same input gives the same
result live and in the replay.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

from app.adaptation.indicators import WindowIndicators
from app.adaptation.profile import S6Profile

ESTIMATOR_VERSION = "behavior-v1"

STABLE = "STABLE"
DISENGAGED = "DISENGAGED"
OVERLOADED = "OVERLOADED"

ENVIRONMENT = "ENVIRONMENT"
AWAY = "AWAY"
IMPULSIVE = "IMPULSIVE"


@dataclass(frozen=True)
class EstimatorThresholds:
    away_ms: int = 1500
    env_dwell_ms: int = 1500
    fast_errors: int = 2
    slow_errors: int = 2
    rt_z: float = 2.0
    acc_drop: float = -0.34              # acc_delta ≤ this, together with rt_z or idle
    idle_eff_ratio: float = 0.3
    full_window: int = 3

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_THRESHOLDS = EstimatorThresholds()


@dataclass(frozen=True)
class Condition:
    """One rule of §4.3, with the values it was checked against."""

    name: str
    met: bool
    value: Any
    threshold: Any

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "met": self.met, "value": self.value, "threshold": self.threshold}


@dataclass(frozen=True)
class EstimatorResult:
    trial_id: str | None
    state: str
    cause: str | None
    confidence: float
    support: float
    disengaged: tuple[Condition, ...]
    overloaded: tuple[Condition, ...]
    indicators: dict[str, Any] = field(default_factory=dict)
    version: str = ESTIMATOR_VERSION

    @property
    def evidence(self) -> tuple[Condition, ...]:
        """The conditions that hold for the state reported."""
        if self.state == DISENGAGED:
            return tuple(c for c in self.disengaged if c.met)
        if self.state == OVERLOADED:
            return tuple(c for c in self.overloaded if c.met)
        return ()

    def as_dict(self) -> dict[str, Any]:
        """Plain dict for ADAPTATION_DECISION and the replay."""
        return {
            "trial_id": self.trial_id,
            "state": self.state,
            "cause": self.cause,
            "confidence": round(self.confidence, 3),
            "support": round(self.support, 3),
            "evidence": [c.name for c in self.evidence],
            "conditions": {
                DISENGAGED: [c.as_dict() for c in self.disengaged],
                OVERLOADED: [c.as_dict() for c in self.overloaded],
            },
            "indicators": self.indicators,
            "estimator_version": self.version,
        }


def _round(value: float | None, digits: int = 3) -> float | None:
    return None if value is None else round(value, digits)


def _support(met: int, total: int) -> float:
    return (2 + met) / (2 + total) if met else 0.0


def estimate(
    window: WindowIndicators,
    profile: S6Profile,
    thresholds: EstimatorThresholds = DEFAULT_THRESHOLDS,
) -> EstimatorResult:
    """State, cause and confidence of one window against the S6 profile."""
    th = thresholds
    acc = window.acc_delta

    disengaged = (
        Condition("away_ms", window.away_ms >= th.away_ms, window.away_ms, th.away_ms),
        Condition("env_dwell_ms", window.env_dwell_ms >= th.env_dwell_ms, window.env_dwell_ms, th.env_dwell_ms),
        Condition("fast_errors", window.fast_errors >= th.fast_errors, window.fast_errors, th.fast_errors),
    )
    overloaded = (
        Condition("slow_errors", window.slow_errors >= th.slow_errors, window.slow_errors, th.slow_errors),
        Condition(
            "rt_z_and_acc_drop",
            window.rt_z is not None and acc is not None
            and window.rt_z >= th.rt_z and acc <= th.acc_drop,
            {"rt_z": _round(window.rt_z, 2), "acc_delta": _round(acc)},
            {"rt_z": th.rt_z, "acc_delta": th.acc_drop},
        ),
        Condition(
            "idle_and_acc_drop",
            window.idle_eff_ratio is not None and acc is not None
            and window.idle_eff_ratio >= th.idle_eff_ratio and acc <= th.acc_drop,
            {"idle_eff_ratio": _round(window.idle_eff_ratio), "acc_delta": _round(acc)},
            {"idle_eff_ratio": th.idle_eff_ratio, "acc_delta": th.acc_drop},
        ),
    )

    d_met = sum(c.met for c in disengaged)
    o_met = sum(c.met for c in overloaded)
    if d_met:
        state, support = DISENGAGED, _support(d_met, len(disengaged))
    elif o_met:
        state, support = OVERLOADED, _support(o_met, len(overloaded))
    else:
        state, support = STABLE, 1.0

    cause = None
    if state == DISENGAGED:
        orienting_up = (
            window.orienting_rate is not None
            and window.orienting_count > 0
            and window.orienting_rate > (profile.orienting_rate_ref or 0.0)
        )
        if disengaged[1].met or orienting_up:
            cause = ENVIRONMENT
        elif disengaged[0].met:
            cause = AWAY
        else:
            cause = IMPULSIVE

    coverage = min(window.n, th.full_window) / th.full_window
    confidence = coverage * profile.reliability * support

    return EstimatorResult(
        trial_id=window.last_trial_id,
        state=state,
        cause=cause,
        confidence=confidence,
        support=support,
        disengaged=disengaged,
        overloaded=overloaded,
        indicators=window.as_dict(),
    )

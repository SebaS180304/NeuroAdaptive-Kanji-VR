"""
Window indicators (Planteamiento_Tecnico_F5a.md §4.2).

Window = the last 3 answered S7 trials. With fewer (S7-001, S7-002) the
indicators are computed over what there is and ``n`` says how many; the rule
engine does not decide before S7-003 anyway (§5.1).

| Indicator | Definition |
| --- | --- |
| ``rt_ratio`` | Median of ``rt / rt_ref[type]`` over the trials with a valid RT |
| ``rt_z`` | ``(rt_ratio - 1) / rt_spread`` |
| ``acc_delta`` | Window accuracy minus ``acc_ref`` |
| ``fast_errors`` | Errors with a trial ``rt_ratio`` < 0.6 (impulsive) |
| ``slow_errors`` | Errors with a trial ``rt_ratio`` > 1.4, plus timeouts (difficulty) |
| ``away_ms`` | Time away in the window (``HEAD_AWAY``, D4) |
| ``env_dwell_ms`` | Dwell on props and movers (``DISTRACTOR_INTERACTION`` ``DWELL``, D5) |
| ``orienting_rate`` | Orienting turns / peripheral events in the window; ``None`` without peripherals |
| ``idle_eff_ratio`` | Median of effective idle / RT, minus ``idle_eff_ref`` |

Thresholds belong to the estimator (§4.3); this module only measures.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Sequence

from app.adaptation.profile import S6Profile
from app.adaptation.trials import TrialRecord

WINDOW_SIZE = 3
WINDOW_PHASE = "S7"
FAST_RATIO = 0.6
SLOW_RATIO = 1.4


@dataclass(frozen=True)
class WindowIndicators:
    trial_ids: tuple[str, ...]
    n: int
    rt_ratio: float | None
    rt_z: float | None
    acc: float
    acc_delta: float | None
    fast_errors: int
    slow_errors: int
    away_ms: int
    env_dwell_ms: int
    orienting_count: int
    peripheral_count: int
    orienting_rate: float | None
    idle_eff_ratio: float | None
    trial_rt_ratios: tuple[float | None, ...]

    @property
    def last_trial_id(self) -> str | None:
        return self.trial_ids[-1] if self.trial_ids else None

    def as_dict(self) -> dict:
        """Plain dict for the ``ADAPTATION_DECISION`` context and logs."""

        def r(value: float | None, digits: int = 3) -> float | None:
            return None if value is None else round(value, digits)

        return {
            "trial_ids": list(self.trial_ids),
            "n": self.n,
            "rt_ratio": r(self.rt_ratio),
            "rt_z": r(self.rt_z, 2),
            "acc": r(self.acc),
            "acc_delta": r(self.acc_delta),
            "fast_errors": self.fast_errors,
            "slow_errors": self.slow_errors,
            "away_ms": self.away_ms,
            "env_dwell_ms": self.env_dwell_ms,
            "orienting_count": self.orienting_count,
            "peripheral_count": self.peripheral_count,
            "orienting_rate": r(self.orienting_rate),
            "idle_eff_ratio": r(self.idle_eff_ratio),
            "trial_rt_ratios": [r(x) for x in self.trial_rt_ratios],
        }


def window_trials(
    trials: Sequence[TrialRecord], upto_trial_id: str | None = None, size: int = WINDOW_SIZE
) -> list[TrialRecord]:
    """The last ``size`` answered S7 trials, up to and including ``upto_trial_id``."""
    s7 = [t for t in trials if t.phase == WINDOW_PHASE]
    if upto_trial_id is not None:
        ids = [t.trial_id for t in s7]
        if upto_trial_id not in ids:
            raise ValueError(f"{upto_trial_id} is not an answered S7 trial")
        s7 = s7[: ids.index(upto_trial_id) + 1]
    return s7[-size:]


def window_indicators(window: Sequence[TrialRecord], profile: S6Profile) -> WindowIndicators:
    """Indicators of one window of trials against the S6 profile."""
    ratios = tuple(profile.rt_ratio(t) for t in window)
    valid_ratios = [x for x in ratios if x is not None]
    rt_ratio = median(valid_ratios) if valid_ratios else None
    rt_z = None if rt_ratio is None else (rt_ratio - 1.0) / profile.rt_spread

    n = len(window)
    acc = (sum(t.is_correct for t in window) / n) if n else 0.0
    acc_delta = None if profile.acc_ref is None or n == 0 else acc - profile.acc_ref

    fast_errors = 0
    slow_errors = 0
    for trial, ratio in zip(window, ratios):
        if trial.is_correct:
            continue
        if trial.timed_out:
            slow_errors += 1
        elif ratio is not None and ratio < FAST_RATIO:
            fast_errors += 1
        elif ratio is not None and ratio > SLOW_RATIO:
            slow_errors += 1

    idle_ratios = [
        t.idle_eff_ms / t.rt_ms for t in window if t.idle_eff_ms is not None and t.rt_valid
    ]
    idle_eff_ratio = None
    if idle_ratios:
        idle_eff_ratio = median(idle_ratios) - (profile.idle_eff_ref or 0.0)

    orienting = sum(t.orienting_count for t in window)
    peripherals = sum(t.peripheral_count for t in window)

    return WindowIndicators(
        trial_ids=tuple(t.trial_id for t in window),
        n=n,
        rt_ratio=rt_ratio,
        rt_z=rt_z,
        acc=acc,
        acc_delta=acc_delta,
        fast_errors=fast_errors,
        slow_errors=slow_errors,
        away_ms=sum(t.away_ms for t in window),
        env_dwell_ms=sum(t.env_dwell_ms for t in window),
        orienting_count=orienting,
        peripheral_count=peripherals,
        orienting_rate=(orienting / peripherals) if peripherals else None,
        idle_eff_ratio=idle_eff_ratio,
        trial_rt_ratios=ratios,
    )


def s7_windows(trials: Sequence[TrialRecord], profile: S6Profile) -> list[WindowIndicators]:
    """One window per answered S7 trial, as the live path computes them."""
    s7_ids = [t.trial_id for t in trials if t.phase == WINDOW_PHASE]
    return [window_indicators(window_trials(trials, tid), profile) for tid in s7_ids]

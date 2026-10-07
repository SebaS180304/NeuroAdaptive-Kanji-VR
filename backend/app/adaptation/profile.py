"""
S6 calibration profile (Planteamiento_Tecnico_F5a.md §4.1, D6).

Computed once per session when S7 starts, over the S6 trials **without the
first one** (S6-002…S6-009): the first trial carries the orientation cost of
the new phase (11.8 s in OBS_01 against ~2.3 s for the rest).

| Field | How |
| --- | --- |
| ``rt_ref[type]`` | Median RT per trial type, without timeouts. A type with fewer than 3 valid trials uses the global median (decided 7 Oct; the plan said 2) |
| ``rt_spread`` | MAD of ``rt / rt_ref[type]``, floored at 0.15 |
| ``acc_ref`` | Proportion correct (a timeout counts as an error) |
| ``idle_eff_ref`` | Median of effective idle / RT |
| ``away_ref_ms`` | Mean time away per trial |
| ``env_dwell_ref_ms`` | Mean environment dwell per trial (D5) |
| ``orienting_rate_ref`` | Orienting turns per peripheral event; ``None`` without peripherals |
| ``reliability`` | 1.0 with ≥ 6 valid trials, 0.6 with fewer (§4.3, confidence) |
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, median
from typing import Sequence

from app.adaptation.trials import TrialRecord

PROFILE_PHASE = "S6"
SKIP_FIRST_TRIALS = 1  # D6
MIN_TRIALS_PER_TYPE = 3  # decided 7 Oct: with 2, one slow S6 trial sets the reference (OBS_01, T3)
SPREAD_FLOOR = 0.15  # D6
RELIABLE_MIN_TRIALS = 6
LOW_RELIABILITY = 0.6


@dataclass(frozen=True)
class S6Profile:
    rt_ref: dict[str, float]
    rt_ref_global: float | None
    rt_spread: float
    rt_spread_raw: float | None
    acc_ref: float | None
    idle_eff_ref: float | None
    away_ref_ms: float
    env_dwell_ref_ms: float
    orienting_rate_ref: float | None
    n_trials: int
    n_valid_rt: int
    reliability: float
    trial_ids: tuple[str, ...] = field(default_factory=tuple)

    def ref_for(self, trial_type: str) -> float | None:
        """The RT reference for a type, falling back to the global median."""
        return self.rt_ref.get(trial_type, self.rt_ref_global)

    def rt_ratio(self, trial: TrialRecord) -> float | None:
        """``rt / rt_ref[type]`` for a trial; ``None`` for a timeout."""
        ref = self.ref_for(trial.trial_type)
        if not trial.rt_valid or not ref:
            return None
        return trial.rt_ms / ref

    def as_dict(self) -> dict:
        """Plain dict for the ``ADAPTATION_DECISION`` context and logs."""
        return {
            "rt_ref": {k: round(v, 1) for k, v in sorted(self.rt_ref.items())},
            "rt_ref_global": None if self.rt_ref_global is None else round(self.rt_ref_global, 1),
            "rt_spread": round(self.rt_spread, 3),
            "acc_ref": None if self.acc_ref is None else round(self.acc_ref, 3),
            "idle_eff_ref": None if self.idle_eff_ref is None else round(self.idle_eff_ref, 3),
            "away_ref_ms": round(self.away_ref_ms, 1),
            "env_dwell_ref_ms": round(self.env_dwell_ref_ms, 1),
            "orienting_rate_ref": (
                None if self.orienting_rate_ref is None else round(self.orienting_rate_ref, 3)
            ),
            "n_trials": self.n_trials,
            "n_valid_rt": self.n_valid_rt,
            "reliability": self.reliability,
        }


def profile_trials(trials: Sequence[TrialRecord]) -> list[TrialRecord]:
    """The S6 trials the profile uses: in answer order, without the first."""
    s6 = [t for t in trials if t.phase == PROFILE_PHASE]
    return s6[SKIP_FIRST_TRIALS:]


def _mad(values: Sequence[float]) -> float | None:
    if not values:
        return None
    centre = median(values)
    return median(abs(v - centre) for v in values)


def build_profile(trials: Sequence[TrialRecord]) -> S6Profile:
    """Profile from the answered trials of a session (any phases; S6 is picked)."""
    used = profile_trials(trials)
    valid = [t for t in used if t.rt_valid]

    rt_ref_global = median(t.rt_ms for t in valid) if valid else None
    by_type: dict[str, list[int]] = {}
    for t in valid:
        by_type.setdefault(t.trial_type, []).append(t.rt_ms)
    rt_ref: dict[str, float] = {}
    for trial_type, rts in by_type.items():
        if len(rts) >= MIN_TRIALS_PER_TYPE:
            rt_ref[trial_type] = float(median(rts))
        elif rt_ref_global is not None:
            rt_ref[trial_type] = float(rt_ref_global)

    ratios = [t.rt_ms / rt_ref[t.trial_type] for t in valid if rt_ref.get(t.trial_type)]
    spread_raw = _mad(ratios)
    spread = max(SPREAD_FLOOR, spread_raw or 0.0)

    idle_ratios = [
        t.idle_eff_ms / t.rt_ms for t in valid if t.idle_eff_ms is not None and t.rt_ms > 0
    ]
    peripherals = sum(t.peripheral_count for t in used)

    return S6Profile(
        rt_ref=rt_ref,
        rt_ref_global=None if rt_ref_global is None else float(rt_ref_global),
        rt_spread=spread,
        rt_spread_raw=spread_raw,
        acc_ref=(sum(t.is_correct for t in used) / len(used)) if used else None,
        idle_eff_ref=median(idle_ratios) if idle_ratios else None,
        away_ref_ms=mean(t.away_ms for t in used) if used else 0.0,
        env_dwell_ref_ms=mean(t.env_dwell_ms for t in used) if used else 0.0,
        orienting_rate_ref=(
            sum(t.orienting_count for t in used) / peripherals if peripherals else None
        ),
        n_trials=len(used),
        n_valid_rt=len(valid),
        reliability=1.0 if len(valid) >= RELIABLE_MIN_TRIALS else LOW_RELIABILITY,
        trial_ids=tuple(t.trial_id for t in used),
    )

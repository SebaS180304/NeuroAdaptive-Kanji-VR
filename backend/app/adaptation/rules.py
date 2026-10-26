"""
Rule engine: from the estimator's state to an action (Planteamiento_Tecnico_F5a.md §5).

``rules-v2`` (D-F6-59) is ``rules-v1`` plus the ``UNDERCHALLENGED`` rows below,
which only ``behavior-v2`` produces; each decision carries the rules version
that goes with its estimator version, so a v1 session replays as ``rules-v1``.

One decision per answered S7 trial, ``NO_CHANGE`` included, so the record also
shows when the system chose not to act and why.

**Constraints (spec §10.2, plan §5.1)**, checked in this order:

| Constraint | Rule | ``reason_code`` when it blocks |
| --- | --- | --- |
| Initial window | No decision before the 3rd S7 trial **and** 20 s since S7 began | ``INITIAL_WINDOW`` |
| Tail freeze | No change applied in the last 4 trials (17–20 of 20): a decision at trial 16 or later would apply before 17 | ``TAIL_FREEZE`` |
| Cooldown | The 3 trials after a change are ``NO_CHANGE`` | ``COOLDOWN`` |
| Confidence | States with confidence < 0.5 are ignored and break the streak | ``LOW_CONFIDENCE`` |
| Hysteresis | The same state in 2 consecutive eligible windows before acting; to return, ``STABLE`` in 2 windows after the cooldown | ``HYSTERESIS`` |
| Level bounds | ESL and LAL stay within LOW…HIGH | ``AT_LIMIT`` |
| One dimension | Every action changes exactly one of ESL or LAL by one step | — |

Windows inside the initial window or the cooldown do not count for the
hysteresis: the first window that counts after a change (trial N+4) holds
only trials played at the new level.

**State → action (D3, plan §5.2):**

| Sustained state | Cause | Action | ``reason_code`` |
| --- | --- | --- | --- |
| ``DISENGAGED`` | ``ENVIRONMENT`` or ``AWAY`` | ESL one step down | ``DISENGAGED_ENVIRONMENT`` / ``DISENGAGED_AWAY`` |
| ``DISENGAGED`` | ``IMPULSIVE`` | ESL one step down; if ESL is already LOW, LAL one step up | ``DISENGAGED_IMPULSIVE`` |
| ``OVERLOADED`` | — | LAL one step up, with proactive cues (D9) | ``OVERLOADED`` |
| ``UNDERCHALLENGED`` (v2) | ``NO_ENVIRONMENT`` | ESL one step up | ``UNDERCHALLENGED_ENVIRONMENT`` |
| ``UNDERCHALLENGED`` (v2) | ``FAST`` | LAL one step down; if LAL is already LOW and ``NO_ENVIRONMENT`` also holds, ESL one step up | ``UNDERCHALLENGED_FAST`` / ``UNDERCHALLENGED_ENVIRONMENT`` |
| ``STABLE`` after a change | — | The dimension the engine moved last, one step back towards MEDIUM | ``STABLE_RETURN`` |
| Any, at the limit | — | ``NO_CHANGE`` | ``AT_LIMIT`` |

A change that makes the task harder (ESL up, LAL down) is never returned by
``STABLE``: only ``DISENGAGED`` or ``OVERLOADED`` undo it, as they act the
other way anyway (D-F6-59).

``IMPULSIVE`` with ESL above LOW lowering the ESL is a reading of the plan,
which only states the ESL-at-LOW row. *To validate.*

**Levels.** The engine keeps the levels it believes are in force, starting
from the ones S7 was entered with, and assumes each change it decides is
applied before the next trial. When Unity skips one (``ADAPTATION_SKIPPED``),
the session state (``state.py``) corrects them with ``with_levels``.

Pure functions: ``decide`` takes the previous ``EngineState`` and returns the
new one, with no clock and no database, so the live path and the replay agree.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Any

from app.adaptation.estimator import (
    AWAY,
    DISENGAGED,
    ENVIRONMENT,
    ESTIMATOR_V1,
    ESTIMATOR_V2,
    FAST,
    IMPULSIVE,
    NO_ENVIRONMENT,
    OVERLOADED,
    STABLE,
    UNDERCHALLENGED,
    EstimatorResult,
)

RULES_V1 = "rules-v1"
RULES_V2 = "rules-v2"
RULES_FOR = {ESTIMATOR_V1: RULES_V1, ESTIMATOR_V2: RULES_V2}
RULES_VERSION = RULES_V2                  # what new sessions run with

S7_STATE = "S7_EXPERIMENTAL_RETRIEVAL"
ADAPTIVE_CONDITIONS = frozenset({"BEHAVIOR_ADAPTIVE", "MULTIMODAL_ADAPTIVE"})

LEVELS = ("LOW", "MEDIUM", "HIGH")
HOME_LEVEL = "MEDIUM"

ESL = "ESL"
LAL = "LAL"

NO_CHANGE = "NO_CHANGE"
CHANGE_ENVIRONMENT = "CHANGE_ENVIRONMENT"
CHANGE_ASSISTANCE = "CHANGE_ASSISTANCE"
ACTION_FOR = {ESL: CHANGE_ENVIRONMENT, LAL: CHANGE_ASSISTANCE}

# reason codes
INITIAL_WINDOW = "INITIAL_WINDOW"
TAIL_FREEZE = "TAIL_FREEZE"
COOLDOWN = "COOLDOWN"
LOW_CONFIDENCE = "LOW_CONFIDENCE"
HYSTERESIS = "HYSTERESIS"
AT_LIMIT = "AT_LIMIT"
STABLE_NO_ACTION = "STABLE"
STABLE_RETURN = "STABLE_RETURN"


@dataclass(frozen=True)
class RuleConfig:
    initial_trials: int = 3
    initial_ms: int = 20_000
    block_size: int = 20
    tail_trials: int = 4
    cooldown_trials: int = 3
    hysteresis_windows: int = 2
    min_confidence: float = 0.5

    @property
    def last_change_trial(self) -> int:
        """Last trial whose decision may still change a level (16 of 20 → 15)."""
        return self.block_size - self.tail_trials - 1

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_CONFIG = RuleConfig()


@dataclass(frozen=True)
class EngineState:
    """What the engine remembers between trials of one S7 block."""

    esl: str = HOME_LEVEL
    lal: str = HOME_LEVEL
    s7_started_ms: int | None = None
    cooldown_until: int = 0                 # trial sequence; NO_CHANGE up to and including it
    streak_state: str | None = None         # state of the current run of eligible windows
    streak_len: int = 0
    moved: tuple[str, ...] = ()             # dimensions the engine eased off MEDIUM, oldest first
    changes: int = 0

    def level(self, dimension: str) -> str:
        return self.esl if dimension == ESL else self.lal

    def with_levels(self, esl: str | None = None, lal: str | None = None) -> "EngineState":
        """The levels actually in force (e.g. after Unity skipped a change)."""
        new = replace(self, esl=esl or self.esl, lal=lal or self.lal)
        moved = tuple(d for d in new.moved if new.level(d) != HOME_LEVEL)
        return replace(new, moved=moved)


def initial_state(esl: str | None, lal: str | None, s7_started_ms: int | None) -> EngineState:
    """State at the start of S7, with the levels S7 was entered with."""
    return EngineState(esl=esl or HOME_LEVEL, lal=lal or HOME_LEVEL, s7_started_ms=s7_started_ms)


@dataclass(frozen=True)
class Decision:
    """One decision per answered S7 trial (the ``DECISION`` message, §8.1)."""

    trial_id: str | None
    trial_sequence: int
    action: str
    dimension: str | None
    from_level: str | None
    to_level: str | None
    proactive_cues: bool
    learner_state: str
    cause: str | None
    confidence: float
    reason_code: str
    explanation: str
    cooldown_until_trial: int | None
    estimator: dict[str, Any] = field(default_factory=dict)
    version: str = RULES_VERSION

    @property
    def is_change(self) -> bool:
        return self.action != NO_CHANGE

    def as_dict(self) -> dict[str, Any]:
        return {
            "trial_id": self.trial_id,
            "trial_sequence": self.trial_sequence,
            "action": self.action,
            "dimension": self.dimension,
            "from_level": self.from_level,
            "to_level": self.to_level,
            "proactive_cues": self.proactive_cues,
            "learner_state": self.learner_state,
            "cause": self.cause,
            "confidence": round(self.confidence, 3),
            "reason_code": self.reason_code,
            "explanation": self.explanation,
            "cooldown_until_trial": self.cooldown_until_trial,
            "rules_version": self.version,
        }


# -- gate ---------------------------------------------------------------------


def adaptation_allowed(state: str | None, condition: str | None) -> bool:
    """Only S7, only in the adaptive conditions (criterion 5: STATIC never adapts).

    The backend does not call the estimator or the engine otherwise; Unity
    checks the same thing in ``IsAdaptationAllowed()``.
    """
    return state == S7_STATE and condition in ADAPTIVE_CONDITIONS


# -- helpers ------------------------------------------------------------------


def _step(level: str, delta: int) -> str | None:
    i = LEVELS.index(level) + delta
    return LEVELS[i] if 0 <= i < len(LEVELS) else None


def _towards_home(level: str) -> int:
    return -1 if LEVELS.index(level) > LEVELS.index(HOME_LEVEL) else 1


def _fmt_ratio(value: Any) -> str:
    return f"{value:.2f}×" if isinstance(value, (int, float)) else "—"


def _evidence_text(result: EstimatorResult) -> str:
    """The conditions that held, in plain words, from the estimator's own record."""
    ind = result.indicators or {}
    parts = []
    for c in result.evidence:
        if c.name == "slow_errors":
            parts.append(f"{c.value} slow errors in the last 3 trials (over 1.4× your practice pace, or timed out)")
        elif c.name == "rt_z_and_acc_drop":
            parts.append(f"answers at {_fmt_ratio(ind.get('rt_ratio'))} your practice pace with "
                         f"{ind.get('acc_delta', 0):+.2f} accuracy")
        elif c.name == "idle_and_acc_drop":
            parts.append(f"long pauses looking at the task ({ind.get('idle_eff_ratio', 0):.2f} of the response "
                         f"time above practice) with {ind.get('acc_delta', 0):+.2f} accuracy")
        elif c.name == "away_ms":
            parts.append(f"{c.value / 1000:.1f} s looking away from the task")
        elif c.name == "env_dwell_ms":
            parts.append(f"{c.value / 1000:.1f} s looking at objects in the room")
        elif c.name == "fast_errors":
            parts.append(f"{c.value} fast wrong answers")
        elif c.name == FAST:
            parts.append(f"answers at {_fmt_ratio(ind.get('rt_ratio'))} your practice pace")
        elif c.name == NO_ENVIRONMENT:
            parts.append(f"no look at the room in {ind.get('peripheral_count', 0)} peripheral events")
    if result.state == UNDERCHALLENGED and parts:
        parts.insert(0, "no errors in the last 3 trials")
    if result.state == DISENGAGED and result.cause == ENVIRONMENT and not any(
        c.name == "env_dwell_ms" for c in result.evidence
    ):
        parts.append(f"turned towards {ind.get('orienting_count', 0)} of {ind.get('peripheral_count', 0)} "
                     f"peripheral events")
    return "; ".join(parts) if parts else "no indicator outside the practice profile"


def _verb(dimension: str, delta: int) -> str:
    name = "the environment" if dimension == ESL else "the assistance"
    return f"{'Raised' if delta > 0 else 'Lowered'} {name}"


# -- decide -------------------------------------------------------------------


def decide(
    result: EstimatorResult,
    trial_sequence: int,
    answered_ms: int | None,
    state: EngineState,
    config: RuleConfig = DEFAULT_CONFIG,
) -> tuple[Decision, EngineState]:
    """The decision for one answered S7 trial and the engine state after it."""
    cfg = config
    seq = trial_sequence

    version = RULES_FOR.get(result.version, RULES_VERSION)

    def no_change(reason: str, text: str, new_state: EngineState) -> tuple[Decision, EngineState]:
        return Decision(
            trial_id=result.trial_id, trial_sequence=seq, action=NO_CHANGE, dimension=None,
            from_level=None, to_level=None, proactive_cues=False, learner_state=result.state,
            cause=result.cause, confidence=result.confidence, reason_code=reason, explanation=text,
            cooldown_until_trial=state.cooldown_until if seq <= state.cooldown_until else None,
            estimator=result.as_dict(), version=version,
        ), new_state

    # 1 · initial window: neither acts nor counts for the hysteresis
    elapsed = None
    if answered_ms is not None and state.s7_started_ms is not None:
        elapsed = answered_ms - state.s7_started_ms
    if seq < cfg.initial_trials or (elapsed is not None and elapsed < cfg.initial_ms):
        return no_change(INITIAL_WINDOW,
                         f"Initial window: {cfg.initial_trials} trials and {cfg.initial_ms // 1000} s of S7 "
                         f"before the first decision.", state)

    # 2 · cooldown: does not count for the hysteresis either
    if seq <= state.cooldown_until:
        return no_change(COOLDOWN, f"Cooldown after the last change, until trial {state.cooldown_until}.", state)

    # 3 · streak of eligible windows (hysteresis)
    if result.confidence < cfg.min_confidence:
        streak_state, streak_len = None, 0
    elif result.state == state.streak_state:
        streak_state, streak_len = result.state, state.streak_len + 1
    else:
        streak_state, streak_len = result.state, 1
    counted = replace(state, streak_state=streak_state, streak_len=streak_len)

    # 4 · tail freeze: keeps tracking, never changes
    if seq > cfg.last_change_trial:
        return no_change(TAIL_FREEZE,
                         f"No changes in the last {cfg.tail_trials} trials of S7.", counted)

    if streak_state is None:
        return no_change(LOW_CONFIDENCE,
                         f"{result.state} with confidence {result.confidence:.2f}, below "
                         f"{cfg.min_confidence:.2f}: ignored.", counted)

    # 5 · what the sustained state asks for
    if result.state == STABLE:
        if not state.moved:
            return no_change(STABLE_NO_ACTION, "Stable at the current levels.", counted)
        dimension = state.moved[-1]
        delta = _towards_home(state.level(dimension))
        reason = STABLE_RETURN
    elif result.state == OVERLOADED:
        dimension, delta, reason = LAL, +1, OVERLOADED
    elif result.state == DISENGAGED:
        reason = f"{DISENGAGED}_{result.cause or AWAY}"
        if result.cause == IMPULSIVE and state.esl == LEVELS[0]:
            dimension, delta = LAL, +1
        else:
            dimension, delta = ESL, -1
    elif result.state == UNDERCHALLENGED:
        no_environment = any(c.name == NO_ENVIRONMENT and c.met for c in result.underchallenged)
        if result.cause == FAST and not (no_environment and state.lal == LEVELS[0]):
            dimension, delta, reason = LAL, -1, f"{UNDERCHALLENGED}_{FAST}"      # LAL at LOW: AT_LIMIT
        else:
            dimension, delta, reason = ESL, +1, f"{UNDERCHALLENGED}_{ENVIRONMENT}"
    else:  # unknown state: never act on it
        return no_change(STABLE_NO_ACTION, f"Unknown state {result.state}.", counted)

    if streak_len < cfg.hysteresis_windows:
        return no_change(HYSTERESIS,
                         f"{result.state} in {streak_len} of the {cfg.hysteresis_windows} consecutive windows "
                         f"needed to act.", counted)

    from_level = state.level(dimension)
    to_level = _step(from_level, delta)
    if to_level is None:
        return no_change(AT_LIMIT,
                         f"{result.state}: {dimension} is already {from_level}.", counted)

    # 6 · change one dimension by one step
    cooldown_until = seq + cfg.cooldown_trials
    moved = tuple(d for d in state.moved if d != dimension)
    harder = (dimension == ESL) == (delta > 0)          # ESL up or LAL down: STABLE never returns it
    if to_level != HOME_LEVEL and not harder:
        moved = moved + (dimension,)
    new_state = replace(
        counted,
        esl=to_level if dimension == ESL else state.esl,
        lal=to_level if dimension == LAL else state.lal,
        cooldown_until=cooldown_until,
        streak_state=None,
        streak_len=0,
        moved=moved,
        changes=state.changes + 1,
    )

    if reason == STABLE_RETURN:
        # Says what held, not "your usual pace": STABLE only means no overload
        # or disengagement condition was met (session 099690e1, S7-012, was
        # STABLE at 4.2x the practice pace because accuracy held).
        ind = result.indicators or {}
        pace = ind.get("rt_ratio")
        acc = ind.get("acc_delta")
        details = []
        if isinstance(pace, (int, float)):
            details.append(f"answers at {pace:.2f}× the practice pace")
        if isinstance(acc, (int, float)):
            details.append(f"{acc:+.2f} accuracy against practice")
        why = (f"{cfg.hysteresis_windows} windows in a row with no sign of overload or disengagement"
               + (f" ({', '.join(details)})" if details else ""))
    else:
        why = _evidence_text(result)
        if reason == f"{DISENGAGED}_{IMPULSIVE}" and dimension == LAL:
            why += "; the environment is already at its minimum"
        elif result.cause == FAST and dimension == ESL:
            why += "; the assistance is already at its minimum"
    explanation = f"{_verb(dimension, delta)} from {from_level} to {to_level}: {why}."

    decision = Decision(
        trial_id=result.trial_id, trial_sequence=seq, action=ACTION_FOR[dimension], dimension=dimension,
        from_level=from_level, to_level=to_level,
        proactive_cues=dimension == LAL and delta > 0,          # D9: only when the assistance goes up
        learner_state=result.state, cause=result.cause, confidence=result.confidence,
        reason_code=reason, explanation=explanation, cooldown_until_trial=cooldown_until,
        estimator=result.as_dict(), version=version,
    )
    return decision, new_state

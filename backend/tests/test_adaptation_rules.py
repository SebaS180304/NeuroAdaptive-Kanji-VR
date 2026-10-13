"""
F5a rule engine v1 (Planteamiento_Tecnico_F5a.md §5).

One test per constraint of spec §10.2 (plan §5.1, criterion 2), each of which
fails if the constraint is violated; one per row of the state → action table
(§5.2, D3); and the replay of the recorded sessions of the F3 phase test. No
database.
"""

import json
from pathlib import Path

import pytest

from app.adaptation.estimator import (
    AWAY,
    DISENGAGED,
    ENVIRONMENT,
    IMPULSIVE,
    OVERLOADED,
    STABLE,
    EstimatorResult,
)
from app.adaptation.replay import replay
from app.adaptation.rules import (
    AT_LIMIT,
    CHANGE_ASSISTANCE,
    CHANGE_ENVIRONMENT,
    COOLDOWN,
    DEFAULT_CONFIG,
    ESL,
    HYSTERESIS,
    INITIAL_WINDOW,
    LAL,
    LOW_CONFIDENCE,
    NO_CHANGE,
    STABLE_RETURN,
    TAIL_FREEZE,
    adaptation_allowed,
    decide,
    initial_state,
)

FIXTURE = Path(__file__).parent / "fixtures" / "prueba_fase_f3_events.json"
OBS_01 = "87761ce6-c74d-4e9c-941f-8c3e0d8a64ad"
OBS_02 = "e550a567-31ba-4b9e-8229-7eefd15360f4"

S7_START = 0
TRIAL_MS = 7_000        # one trial every 7 s: S7-003 answers at 21 s, past the 20 s window


@pytest.fixture(autouse=True)
def _clean_test_participants():
    """Overrides the conftest fixture: these tests do not touch the database."""
    yield


def _result(state=STABLE, cause=None, confidence=1.0, trial=1):
    return EstimatorResult(
        trial_id=f"S7-{trial:03d}", state=state, cause=cause, confidence=confidence, support=1.0,
        disengaged=(), overloaded=(), indicators={},
    )


def _run(states, esl="MEDIUM", lal="MEDIUM", trial_ms=TRIAL_MS, config=DEFAULT_CONFIG):
    """Feed one state per trial (S7-001 onwards); returns the decisions and the final engine state.

    Each item is a state, or a (state, cause) / (state, cause, confidence) tuple.
    """
    engine = initial_state(esl, lal, S7_START)
    decisions = []
    for i, item in enumerate(states, start=1):
        if isinstance(item, str):
            item = (item,)
        state = item[0]
        cause = item[1] if len(item) > 1 else None
        conf = item[2] if len(item) > 2 else 1.0
        d, engine = decide(_result(state, cause, conf, i), i, S7_START + i * trial_ms, engine, config)
        decisions.append(d)
    return decisions, engine


def _changes(decisions):
    return [(d.trial_sequence, d.dimension, d.from_level, d.to_level) for d in decisions if d.is_change]


O = OVERLOADED
S = STABLE
ENV = (DISENGAGED, ENVIRONMENT)


# -- §5.1 · constraints of spec §10.2 ----------------------------------------


def test_no_decision_before_initial_window():
    decisions, _ = _run([O] * 6)
    assert [d.reason_code for d in decisions[:2]] == [INITIAL_WINDOW] * 2
    # S7-003 is the first window that counts, so the earliest change is S7-004
    assert decisions[2].reason_code == HYSTERESIS
    assert _changes(decisions)[0][0] == 4


def test_initial_window_also_needs_20_seconds():
    # 4 s per trial: S7-005 answers at 20 s, the first eligible window
    decisions, _ = _run([O] * 8, trial_ms=4_000)
    assert all(d.reason_code == INITIAL_WINDOW for d in decisions[:4])
    assert decisions[4].reason_code == HYSTERESIS
    assert _changes(decisions)[0][0] == 6


def test_single_dimension():
    decisions, _ = _run([O] * 4 + [ENV] * 8 + [S] * 8)
    for d in decisions:
        if d.is_change:
            assert d.action in (CHANGE_ENVIRONMENT, CHANGE_ASSISTANCE)
            assert d.dimension in (ESL, LAL)
            assert abs("LOW MEDIUM HIGH".split().index(d.to_level)
                       - "LOW MEDIUM HIGH".split().index(d.from_level)) == 1
        else:
            assert d.dimension is None and d.from_level is None and d.to_level is None


def test_cooldown():
    decisions, _ = _run([O] * 4 + [ENV] * 10)
    assert _changes(decisions)[0][0] == 4
    assert [d.reason_code for d in decisions[4:7]] == [COOLDOWN] * 3
    assert all(not d.is_change for d in decisions[4:7])
    assert decisions[3].cooldown_until_trial == 7


def test_cooldown_windows_do_not_count_for_hysteresis():
    decisions, _ = _run([O] * 4 + [ENV] * 10)
    # the first windows after the cooldown are S7-008 and S7-009: acts at 9, not 8
    assert decisions[7].reason_code == HYSTERESIS
    assert _changes(decisions)[1] == (9, ESL, "MEDIUM", "LOW")


def test_hysteresis_no_oscillation():
    # alternating states never sustain one for 2 windows: no change at all
    decisions, _ = _run([O, ENV] * 10)
    assert _changes(decisions) == []
    # one window of a state is never enough
    decisions, _ = _run([S, S, S, O, S, S, O, S, S, O, S, S])
    assert _changes(decisions) == []


def test_hysteresis_return_needs_two_stable_windows_after_cooldown():
    decisions, engine = _run([O] * 4 + [S] * 8)
    assert _changes(decisions) == [(4, LAL, "MEDIUM", "HIGH"), (9, LAL, "HIGH", "MEDIUM")]
    assert decisions[8].reason_code == STABLE_RETURN
    assert engine.lal == "MEDIUM" and engine.moved == ()


def test_low_confidence_is_ignored_and_breaks_the_streak():
    decisions, _ = _run([O, O, O, (O, None, 0.4), O, O])
    assert decisions[3].reason_code == LOW_CONFIDENCE
    assert decisions[4].reason_code == HYSTERESIS      # streak restarted at S7-005
    assert _changes(decisions) == [(6, LAL, "MEDIUM", "HIGH")]


def test_tail_freeze():
    # the state only becomes sustained in the tail: never acts
    decisions, _ = _run([S] * 14 + [O] * 6)
    assert _changes(decisions) == []
    assert [d.reason_code for d in decisions[15:]] == [TAIL_FREEZE] * 5
    # S7-015 is the last trial whose decision may change a level (applied before 16)
    decisions, _ = _run([S] * 13 + [O] * 7)
    assert _changes(decisions) == [(15, LAL, "MEDIUM", "HIGH")]


def test_tail_freeze_leaves_the_proactive_window_inside_s7():
    # D9: the last possible LAL raise (decided at 15) still has trials 16–18 for its cues
    decisions, _ = _run([S] * 13 + [O] * 7)
    last = _changes(decisions)[-1][0]
    assert last + 3 <= DEFAULT_CONFIG.block_size


def test_level_bounds():
    decisions, engine = _run([O] * 20, lal="HIGH")
    assert _changes(decisions) == []
    assert AT_LIMIT in {d.reason_code for d in decisions}
    assert engine.lal == "HIGH"
    decisions, engine = _run([ENV] * 20, esl="LOW")
    assert _changes(decisions) == []
    assert engine.esl == "LOW"


def test_static_never_adapts():
    s7 = "S7_EXPERIMENTAL_RETRIEVAL"
    assert not adaptation_allowed(s7, "STATIC")
    assert not adaptation_allowed(s7, None)
    assert not adaptation_allowed("S6_GUIDED_PRACTICE_CALIBRATION", "BEHAVIOR_ADAPTIVE")
    assert adaptation_allowed(s7, "BEHAVIOR_ADAPTIVE")
    assert adaptation_allowed(s7, "MULTIMODAL_ADAPTIVE")


def test_capacity_is_at_most_three_changes():
    # the worst case for the constraints: a state that always asks for action
    for pattern in ([O] * 20, [ENV] * 20, [O, O, O, O, S, S, S, S, S] * 3):
        decisions, _ = _run(pattern, esl="HIGH", lal="LOW")
        assert len(_changes(decisions)) <= 3


# -- §5.2 · state → action (D3) ----------------------------------------------


@pytest.mark.parametrize("cause", [ENVIRONMENT, AWAY])
def test_disengaged_by_attention_lowers_the_environment(cause):
    decisions, _ = _run([(DISENGAGED, cause)] * 5)
    d = next(d for d in decisions if d.is_change)
    assert (d.action, d.dimension, d.from_level, d.to_level) == (CHANGE_ENVIRONMENT, ESL, "MEDIUM", "LOW")
    assert d.reason_code == f"DISENGAGED_{cause}"
    assert d.proactive_cues is False


def test_impulsive_lowers_the_environment_while_it_can():
    decisions, _ = _run([(DISENGAGED, IMPULSIVE)] * 5)
    d = next(d for d in decisions if d.is_change)
    assert (d.dimension, d.to_level) == (ESL, "LOW")


def test_impulsive_with_environment_at_low_raises_the_assistance():
    decisions, _ = _run([(DISENGAGED, IMPULSIVE)] * 5, esl="LOW")
    d = next(d for d in decisions if d.is_change)
    assert (d.action, d.dimension, d.from_level, d.to_level) == (CHANGE_ASSISTANCE, LAL, "MEDIUM", "HIGH")
    assert d.proactive_cues is True
    assert "already at its minimum" in d.explanation


def test_overloaded_raises_the_assistance_with_proactive_cues():
    decisions, _ = _run([O] * 5)
    d = next(d for d in decisions if d.is_change)
    assert (d.action, d.dimension, d.from_level, d.to_level) == (CHANGE_ASSISTANCE, LAL, "MEDIUM", "HIGH")
    assert d.proactive_cues is True
    assert d.reason_code == OVERLOADED


def test_stable_returns_the_last_moved_dimension_towards_medium():
    # ESL down at 4, LAL up at 9 (after cooldown + 2 windows), then stable: LAL comes back first
    decisions, engine = _run([ENV] * 4 + [O] * 5 + [S] * 6)
    assert _changes(decisions) == [
        (4, ESL, "MEDIUM", "LOW"),
        (9, LAL, "MEDIUM", "HIGH"),
        (14, LAL, "HIGH", "MEDIUM"),
    ]
    returned = decisions[13]
    assert returned.reason_code == STABLE_RETURN and returned.proactive_cues is False
    assert engine.moved == (ESL,)


def test_stable_without_previous_change_does_nothing():
    decisions, _ = _run([S] * 20)
    assert _changes(decisions) == []
    assert all(d.action == NO_CHANGE for d in decisions)


def test_return_never_moves_a_dimension_the_engine_did_not_move():
    # starting off MEDIUM is the condition's choice, not the engine's
    decisions, _ = _run([S] * 20, esl="HIGH", lal="LOW")
    assert _changes(decisions) == []


def test_with_levels_corrects_a_skipped_change():
    decisions, engine = _run([O] * 4)
    assert engine.lal == "HIGH" and engine.moved == (LAL,)
    corrected = engine.with_levels(lal="MEDIUM")     # Unity reported ADAPTATION_SKIPPED
    assert corrected.lal == "MEDIUM" and corrected.moved == ()


def test_decision_serialises_for_the_message():
    decisions, _ = _run([O] * 4)
    d = decisions[3].as_dict()
    assert d["action"] == CHANGE_ASSISTANCE and d["proactive_cues"] is True
    assert d["rules_version"] == "rules-v1"
    assert json.loads(json.dumps(d)) == d


def test_same_input_same_decisions():
    seq = [O] * 4 + [ENV] * 6 + [S] * 10
    a, _ = _run(seq)
    b, _ = _run(seq)
    assert [x.as_dict() for x in a] == [x.as_dict() for x in b]


# -- replay of the recorded sessions -----------------------------------------


@pytest.fixture(scope="module")
def decisions():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    out = {}
    for sid in (OBS_01, OBS_02):
        events = [e for e in data["events"] if e["session_id"] == sid]
        _, rows = replay(events)
        out[sid] = {row["trial"].trial_id: row["decision"] for row in rows}
    return out


def test_obs01_raises_assistance_at_s7_010_and_returns_at_s7_015(decisions):
    d = decisions[OBS_01]
    assert d["S7-009"].reason_code == HYSTERESIS                     # first OVERLOADED window
    assert (d["S7-010"].action, d["S7-010"].to_level) == (CHANGE_ASSISTANCE, "HIGH")
    assert d["S7-010"].proactive_cues is True
    assert "slow errors" in d["S7-010"].explanation
    assert [d[f"S7-{i:03d}"].reason_code for i in (11, 12, 13)] == [COOLDOWN] * 3
    assert (d["S7-015"].reason_code, d["S7-015"].to_level) == (STABLE_RETURN, "MEDIUM")
    assert sum(x.is_change for x in d.values()) == 2


def test_obs01_early_overload_is_not_acted_on(decisions):
    # S7-001..003 read OVERLOADED, but 1–2 are the initial window and S7-004 is STABLE
    d = decisions[OBS_01]
    assert [d[f"S7-{i:03d}"].reason_code for i in (1, 2)] == [INITIAL_WINDOW] * 2
    assert not any(d[f"S7-{i:03d}"].is_change for i in range(1, 10))


def test_obs02_never_changes(decisions):
    assert not any(x.is_change for x in decisions[OBS_02].values())
    assert len(decisions[OBS_02]) == 20

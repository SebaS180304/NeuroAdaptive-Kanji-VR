"""
F5a O4: outcome of each adaptation (app/adaptation/outcome.py; rule decided on 14 Oct).

One test per row of the two tables in outcome.py, plus the replay of OBS_01
and the live path (SessionAdaptationState) on the recordings. No database.
"""

import json
from pathlib import Path

import pytest

from app.adaptation.estimator import (
    AWAY,
    DISENGAGED,
    ENVIRONMENT,
    FAST,
    IMPULSIVE,
    NO_ENVIRONMENT,
    OVERLOADED,
    STABLE,
    UNDERCHALLENGED,
    EstimatorResult,
)
from app.adaptation.estimator import ESTIMATOR_V1
from app.adaptation.outcome import NEGATIVE, NEUTRAL, POSITIVE, UNCERTAIN, classify
from app.adaptation.replay import replay
from app.adaptation.state import ADAPTATION_OUTCOME, SessionAdaptationState

FIXTURE = Path(__file__).parent / "fixtures" / "prueba_fase_f3_events.json"
OBS_01 = "87761ce6-c74d-4e9c-941f-8c3e0d8a64ad"


@pytest.fixture(autouse=True)
def _clean_test_participants():
    """Overrides the conftest fixture: these tests do not touch the database."""
    yield


def _res(state=STABLE, cause=None, confidence=1.0, n=3, **ind):
    indicators = dict(n=n, acc_delta=0.0, rt_ratio=1.0, rt_z=0.0, away_ms=0, env_dwell_ms=0, fast_errors=0)
    indicators.update(ind)
    return EstimatorResult(trial_id="S7-x", state=state, cause=cause, confidence=confidence, support=1.0,
                           disengaged=(), overloaded=(), indicators=indicators)


RAISE = {"decision_id": "d-S7-006", "trial_id": "S7-006", "reason_code": OVERLOADED,
         "learner_state": OVERLOADED, "action": "CHANGE_ASSISTANCE"}
LOWER_ENV = {"decision_id": "d-S7-006", "trial_id": "S7-006", "reason_code": "DISENGAGED_ENVIRONMENT",
             "learner_state": DISENGAGED, "action": "CHANGE_ENVIRONMENT"}
RETURN = {"decision_id": "d-S7-012", "trial_id": "S7-012", "reason_code": "STABLE_RETURN",
          "learner_state": STABLE, "action": "CHANGE_ASSISTANCE"}

PRE_OVER = _res(OVERLOADED, confidence=0.8, acc_delta=-0.54, rt_ratio=1.6, rt_z=4.0)
PRE_ENV = _res(DISENGAGED, ENVIRONMENT, 0.8, away_ms=3000, env_dwell_ms=2000)


# -- rescue changes ----------------------------------------------------------


def test_resolved_is_positive():
    o = classify(RAISE, PRE_OVER, _res(STABLE))
    assert (o.outcome, o.reason_code) == (POSITIVE, "RESOLVED")


def test_switched_is_negative():
    o = classify(RAISE, PRE_OVER, _res(DISENGAGED, ENVIRONMENT, 0.8, away_ms=4000))
    assert (o.outcome, o.reason_code) == (NEGATIVE, "SWITCHED")


def test_overload_persisting_and_worse_is_negative():
    o = classify(RAISE, PRE_OVER, _res(OVERLOADED, confidence=0.8, acc_delta=-0.88, rt_ratio=1.6, rt_z=4.0))
    assert (o.outcome, o.reason_code) == (NEGATIVE, "PERSISTED_WORSE")


def test_overload_persisting_but_better_is_neutral_partial():
    o = classify(RAISE, PRE_OVER, _res(OVERLOADED, confidence=0.8, acc_delta=-0.21, rt_ratio=1.5, rt_z=3.3))
    assert (o.outcome, o.reason_code) == (NEUTRAL, "PARTIAL")


def test_overload_persisting_unchanged_is_neutral():
    o = classify(RAISE, PRE_OVER, _res(OVERLOADED, confidence=0.8, acc_delta=-0.54, rt_ratio=1.6, rt_z=4.4))
    assert (o.outcome, o.reason_code) == (NEUTRAL, "PERSISTED")


def test_distraction_key_indicator_is_time_away_plus_room():
    worse = classify(LOWER_ENV, PRE_ENV, _res(DISENGAGED, AWAY, 0.8, away_ms=6000, env_dwell_ms=600))
    better = classify(LOWER_ENV, PRE_ENV, _res(DISENGAGED, AWAY, 0.8, away_ms=2000, env_dwell_ms=0))
    same = classify(LOWER_ENV, PRE_ENV, _res(DISENGAGED, ENVIRONMENT, 0.8, away_ms=3000, env_dwell_ms=2500))
    assert [o.reason_code for o in (worse, better, same)] == ["PERSISTED_WORSE", "PARTIAL", "PERSISTED"]


def test_impulsive_key_indicator_is_fast_errors():
    pre = _res(DISENGAGED, IMPULSIVE, 0.6, fast_errors=2)
    worse = classify(LOWER_ENV, pre, _res(DISENGAGED, IMPULSIVE, 0.6, fast_errors=3))
    better = classify(LOWER_ENV, pre, _res(DISENGAGED, IMPULSIVE, 0.6, fast_errors=1))
    assert (worse.outcome, better.outcome) == (NEGATIVE, NEUTRAL)


def test_low_confidence_post_state_reads_as_stable():
    # under 0.5 the rule engine ignores a state; the outcome reads it the same way
    o = classify(RAISE, PRE_OVER, _res(OVERLOADED, confidence=0.4))
    assert (o.outcome, o.post["state"], o.post["estimated_state"]) == (POSITIVE, STABLE, OVERLOADED)


# -- harder changes (UNDERCHALLENGED, D-F6-80) --------------------------------

HARDER = {"decision_id": "d-S7-006", "trial_id": "S7-006", "reason_code": "UNDERCHALLENGED_FAST",
          "learner_state": UNDERCHALLENGED, "action": "CHANGE_ASSISTANCE"}
PRE_UC = _res(UNDERCHALLENGED, FAST, 0.75, acc_delta=0.1, rt_ratio=0.79, away_ms=0, env_dwell_ms=0)


def test_harder_change_held_is_positive_resolved():
    o = classify(HARDER, PRE_UC, _res(STABLE, acc_delta=0.0, rt_ratio=0.95))
    assert (o.outcome, o.reason_code) == (POSITIVE, "RESOLVED")


def test_harder_change_too_much_is_negative_switched():
    o = classify(HARDER, PRE_UC, _res(OVERLOADED, confidence=0.8, acc_delta=-0.54, rt_ratio=1.6, rt_z=4.0))
    assert (o.outcome, o.reason_code) == (NEGATIVE, "SWITCHED")


def test_still_underchallenged_is_always_neutral_persisted():
    # no trend: the room getting busier or quieter does not grade a harder change
    for post in (_res(UNDERCHALLENGED, NO_ENVIRONMENT, 0.75, away_ms=0, env_dwell_ms=0),
                 _res(UNDERCHALLENGED, FAST, 0.75, away_ms=0, env_dwell_ms=0, rt_ratio=0.6)):
        o = classify(HARDER, _res(UNDERCHALLENGED, FAST, 0.75, away_ms=2000, env_dwell_ms=2000), post)
        assert (o.outcome, o.reason_code) == (NEUTRAL, "PERSISTED")


# -- returns towards MEDIUM --------------------------------------------------


def test_return_held_is_positive():
    o = classify(RETURN, _res(STABLE, acc_delta=0.12, rt_z=-1.0), _res(STABLE, acc_delta=0.12, rt_z=-0.5))
    assert (o.outcome, o.reason_code) == (POSITIVE, "HELD")


def test_return_held_with_a_drop_is_neutral():
    o = classify(RETURN, _res(STABLE, acc_delta=0.12), _res(STABLE, acc_delta=-0.21))
    assert (o.outcome, o.reason_code) == (NEUTRAL, "HELD_WITH_DROP")


@pytest.mark.parametrize("state,cause", [(OVERLOADED, None), (DISENGAGED, ENVIRONMENT)])
def test_return_relapse_is_negative(state, cause):
    o = classify(RETURN, _res(STABLE), _res(state, cause, 0.8))
    assert (o.outcome, o.reason_code) == (NEGATIVE, "RELAPSED")


# -- uncertain ---------------------------------------------------------------


def test_not_applied_and_incomplete_are_uncertain():
    assert classify(RAISE, PRE_OVER, _res(STABLE), applied=False).reason_code == "NOT_APPLIED"
    assert classify(RAISE, PRE_OVER, None).reason_code == "INCOMPLETE"
    assert classify(RAISE, PRE_OVER, _res(STABLE, n=2)).outcome == UNCERTAIN


def test_outcome_serialises_for_the_event():
    d = classify(RAISE, PRE_OVER, _res(STABLE)).as_dict()
    assert d["decision_id"] == "d-S7-006" and d["outcome"] == POSITIVE
    assert d["outcome_version"] == "outcome-v1"
    assert json.loads(json.dumps(d)) == d


# -- recordings --------------------------------------------------------------


@pytest.fixture(scope="module")
def obs01():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return sorted((e for e in data["events"] if e["session_id"] == OBS_01), key=lambda e: e["id"])


def test_replay_obs01_outcomes(obs01):
    _, rows = replay(obs01, ESTIMATOR_V1)
    out = {r["trial"].trial_id: r["outcome"] for r in rows if r["outcome"] is not None}
    # the LAL raise of S7-010 resolved the overload in S7-011..013
    assert (out["S7-010"].outcome, out["S7-010"].reason_code) == (POSITIVE, "RESOLVED")
    assert out["S7-010"].post["trial_ids"] == ["S7-011", "S7-012", "S7-013"]
    # the return of S7-015 held, with one more error in S7-016..018
    assert (out["S7-015"].outcome, out["S7-015"].reason_code) == (NEUTRAL, "HELD_WITH_DROP")


def test_live_path_marks_a_change_unity_never_applied(obs01):
    # the recording was STATIC: S7-011 still reports LAL MEDIUM after the raise of S7-010
    state = SessionAdaptationState("BEHAVIOR_ADAPTIVE", ESTIMATOR_V1)
    outcomes = []
    for e in obs01:
        state.feed(e["event_type"], e.get("payload") or {})
        outcomes += state.take_outcomes()
    assert len(outcomes) == 1
    o = outcomes[0]
    assert (o["decision_id"], o["outcome"], o["outcome_reason"]) == ("d-S7-010", UNCERTAIN, "NOT_APPLIED")
    assert o["source"] == "BACKEND" and o["trial_id"] == "S7-011"      # context of the answer that closed it


def _applied_copy(events):
    """OBS_01 as if Unity had applied the raise of S7-010 (LAL HIGH from S7-011 on)."""
    out = []
    for e in events:
        p = dict(e.get("payload") or {})
        tid = p.get("trial_id") or ""
        if tid.startswith("S7-") and int(tid[3:]) >= 11:
            p["lal"] = "HIGH"
        out.append({**e, "payload": p})
    return out


def test_live_path_classifies_after_the_cooldown_and_matches_replay(obs01):
    events = _applied_copy(obs01)
    state = SessionAdaptationState("BEHAVIOR_ADAPTIVE", ESTIMATOR_V1)
    outcomes = []
    for e in events:
        state.feed(e["event_type"], e.get("payload") or {})
        outcomes += [(e["payload"].get("trial_id"), o) for o in state.take_outcomes()]
    first = outcomes[0]
    assert first[0] == "S7-013"                                   # answered N+3
    assert (first[1]["outcome"], first[1]["outcome_reason"]) == (POSITIVE, "RESOLVED")


def test_rebuild_does_not_repeat_outcomes(obs01):
    events = _applied_copy(obs01)
    rebuilt = SessionAdaptationState.rebuild("BEHAVIOR_ADAPTIVE", events, ESTIMATOR_V1)
    assert rebuilt.take_outcomes() == []


def test_leaving_s7_with_an_open_change_is_uncertain():
    state = SessionAdaptationState("BEHAVIOR_ADAPTIVE", ESTIMATOR_V1)
    from app.adaptation.state import _OpenChange
    state._open.append(_OpenChange(dict(RAISE), PRE_OVER, 15))
    state.feed("STATE_ENTERED", {"state": "S8_IMMEDIATE_ASSESSMENT", "session_elapsed_ms": 1})
    out = state.take_outcomes()
    assert [(o["outcome"], o["outcome_reason"]) for o in out] == [(UNCERTAIN, "INCOMPLETE")]
    assert ADAPTATION_OUTCOME == "ADAPTATION_OUTCOME"

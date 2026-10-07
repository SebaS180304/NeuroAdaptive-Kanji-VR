"""
F5a estimator v1: state, cause and confidence (Planteamiento_Tecnico_F5a.md §4.3)
and the replay over recorded sessions (§5).

The checks the plan sets on the recorded sessions of the F3 phase test:
OBS_01 (87761ce6) has to read OVERLOADED at S7-009, with S7-011 and S7-017 on
their own not enough; OBS_02 (e550a567) has to stay STABLE throughout. The
rest are synthetic windows for each cause and for the confidence. No database.
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
    estimate,
)
from app.adaptation.indicators import WindowIndicators
from app.adaptation.profile import S6Profile
from app.adaptation.replay import replay

FIXTURE = Path(__file__).parent / "fixtures" / "prueba_fase_f3_events.json"
OBS_01 = "87761ce6-c74d-4e9c-941f-8c3e0d8a64ad"
OBS_02 = "e550a567-31ba-4b9e-8229-7eefd15360f4"


@pytest.fixture(autouse=True)
def _clean_test_participants():
    """Overrides the conftest fixture: these tests do not touch the database."""
    yield


@pytest.fixture(scope="module")
def replays():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    out = {}
    for sid in (OBS_01, OBS_02):
        events = [e for e in data["events"] if e["session_id"] == sid]
        _, rows = replay(events)
        out[sid] = {row["trial"].trial_id: row["result"] for row in rows}
    return out


# -- recorded sessions -------------------------------------------------------


def test_obs01_overloaded_at_s7_009(replays):
    r = replays[OBS_01]
    assert r["S7-009"].state == OVERLOADED
    assert "slow_errors" in [c.name for c in r["S7-009"].evidence]
    assert r["S7-009"].confidence >= 0.5
    assert r["S7-010"].state == OVERLOADED   # the second window: hysteresis can act here


def test_obs01_isolated_errors_are_not_enough(replays):
    r = replays[OBS_01]
    assert r["S7-008"].state == STABLE        # one slow error
    assert r["S7-017"].state == STABLE        # one error plus idle
    assert r["S7-012"].state == STABLE        # S7-011 has left the window's slow pair


def test_obs02_always_stable(replays):
    assert {res.state for res in replays[OBS_02].values()} == {STABLE}


def test_replay_gives_one_result_per_s7_trial(replays):
    assert len(replays[OBS_01]) == 20 and len(replays[OBS_02]) == 20
    assert all(res.version == "behavior-v1" for res in replays[OBS_01].values())


# -- synthetic windows -------------------------------------------------------


def _profile(reliability=1.0, orienting_rate_ref=None):
    return S6Profile(
        rt_ref={"T1": 2000.0}, rt_ref_global=2000.0, rt_spread=0.15, rt_spread_raw=0.1,
        acc_ref=0.875, idle_eff_ref=0.0, away_ref_ms=0.0, env_dwell_ref_ms=0.0,
        orienting_rate_ref=orienting_rate_ref, n_trials=8, n_valid_rt=8, reliability=reliability,
    )


def _window(n=3, **kw):
    base = dict(
        trial_ids=tuple(f"S7-{i:03d}" for i in range(1, n + 1)), n=n, rt_ratio=1.0, rt_z=0.0,
        acc=1.0, acc_delta=0.125, fast_errors=0, slow_errors=0, away_ms=0, env_dwell_ms=0,
        orienting_count=0, peripheral_count=0, orienting_rate=None, idle_eff_ratio=0.0,
        trial_rt_ratios=(1.0,) * n,
    )
    base.update(kw)
    return WindowIndicators(**base)


def test_stable_window():
    r = estimate(_window(), _profile())
    assert (r.state, r.cause, r.confidence) == (STABLE, None, 1.0)
    assert r.evidence == ()


def test_disengaged_by_the_room_is_environment():
    r = estimate(_window(env_dwell_ms=2100, away_ms=2100), _profile())
    assert (r.state, r.cause) == (DISENGAGED, ENVIRONMENT)
    assert r.confidence == pytest.approx(0.8)   # 2 of 3 conditions


def test_away_with_orienting_above_profile_is_environment():
    w = _window(away_ms=1800, orienting_count=2, peripheral_count=2, orienting_rate=1.0)
    assert estimate(w, _profile(orienting_rate_ref=0.5)).cause == ENVIRONMENT
    assert estimate(w, _profile(orienting_rate_ref=1.0)).cause == AWAY


def test_away_alone_is_away():
    r = estimate(_window(away_ms=1600), _profile())
    assert (r.state, r.cause) == (DISENGAGED, AWAY)
    assert r.confidence == pytest.approx(0.6)


def test_fast_errors_alone_are_impulsive():
    r = estimate(_window(fast_errors=2, acc=1 / 3, acc_delta=-0.54), _profile())
    assert (r.state, r.cause) == (DISENGAGED, IMPULSIVE)


def test_disengaged_wins_over_overloaded():
    r = estimate(_window(away_ms=2000, slow_errors=2, acc_delta=-0.54), _profile())
    assert r.state == DISENGAGED
    assert any(c.met for c in r.overloaded)   # recorded, even if not reported


def test_overloaded_by_rt_and_accuracy():
    r = estimate(_window(rt_ratio=1.5, rt_z=3.3, acc_delta=-0.54), _profile())
    assert (r.state, r.cause) == (OVERLOADED, None)
    assert [c.name for c in r.evidence] == ["rt_z_and_acc_drop"]


def test_idle_needs_a_real_accuracy_drop():
    one_error = estimate(_window(idle_eff_ratio=0.5, acc_delta=-0.21), _profile())
    two_errors = estimate(_window(idle_eff_ratio=0.5, acc_delta=-0.54), _profile())
    assert one_error.state == STABLE
    assert two_errors.state == OVERLOADED


def test_confidence_scales_with_window_and_reliability():
    full = estimate(_window(slow_errors=2, acc_delta=-0.54), _profile())
    partial = estimate(_window(n=2, slow_errors=2, acc_delta=-0.54), _profile())
    unreliable = estimate(_window(slow_errors=2, acc_delta=-0.54), _profile(reliability=0.6))
    assert full.confidence == pytest.approx(0.6)
    assert partial.confidence == pytest.approx(0.4)        # below the engine's 0.5
    assert unreliable.confidence == pytest.approx(0.36)


def test_result_serialises_for_the_decision_record():
    d = estimate(_window(away_ms=1600), _profile()).as_dict()
    assert d["state"] == DISENGAGED and d["evidence"] == ["away_ms"]
    assert d["estimator_version"] == "behavior-v1"
    assert json.loads(json.dumps(d)) == d

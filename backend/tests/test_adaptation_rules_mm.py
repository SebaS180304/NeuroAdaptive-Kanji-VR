"""
T2 (tasks/todo.md, Tue 10): rules-v2-mm, the branch of decide() taken only with an EEG window
(Reevaluacion_EEG_Justificacion.md §3.3, D-F6-128, D-F6-174). Without one, decide() is rules-v2 untouched:
test_adaptation_rules.py and the byte-identical replay check that.
"""

import pytest

from app.adaptation.estimator import DISENGAGED, ENVIRONMENT, OVERLOADED, STABLE, EstimatorResult
from app.adaptation.rules import (
    AT_LIMIT,
    COOLDOWN,
    EEG_CONFIRMED,
    EEG_LED,
    EEG_ONLY_ALERT,
    EEG_VETO,
    ESL,
    HYSTERESIS,
    INITIAL_WINDOW,
    LAL,
    MAX_CHANGES,
    NO_CHANGE,
    RULES_V2,
    RULES_V2_MM,
    STABLE_NO_ACTION,
    TAIL_FREEZE,
    decide,
    initial_state,
)

TRIAL_MS = 7_000
ENV = (DISENGAGED, ENVIRONMENT)


@pytest.fixture(autouse=True)
def _clean_test_participants():
    """Overrides the conftest fixture: no database here."""
    yield


def _w(ei=None, theta=None, counted=True) -> dict:
    return {"counted": counted, "non_poor": 3, "clean_s": 9.0,
            "z": {"engagement_index": ei, "theta_fz": theta, "alpha_parietal": 0.0, "theta_beta": None}}


N = _w(ei=0.0, theta=0.0)   # neutral EEG


def _run(items, esl="MEDIUM", lal="MEDIUM"):
    """items: (state or (state, cause), window) per trial from S7-001."""
    engine = initial_state(esl, lal, 0)
    out = []
    for i, (st, window) in enumerate(items, start=1):
        state, cause = st if isinstance(st, tuple) else (st, None)
        result = EstimatorResult(trial_id=f"S7-{i:03d}", state=state, cause=cause, confidence=1.0, support=1.0,
                                 disengaged=(), overloaded=(), indicators={}, underchallenged=())
        d, engine = decide(result, i, i * TRIAL_MS, engine, eeg=window)
        out.append(d)
    return out, engine


def _warm(n=2):
    return [(STABLE, N)] * n   # initial window: trials 1-2


# Coincides / veto / unavailable --------------------------------------------------------------------------------

def test_confirmed_acts_in_one_window() -> None:
    ds, _ = _run(_warm() + [(ENV, _w(ei=-1.2))])
    d = ds[-1]
    assert (d.dimension, d.from_level, d.to_level, d.reason_code) == (ESL, "MEDIUM", "LOW", EEG_CONFIRMED)
    assert d.eeg["effect"] == "CONFIRMED" and d.version == RULES_V2_MM


def test_neutral_keeps_the_two_windows_of_hysteresis() -> None:
    ds, _ = _run(_warm() + [(ENV, N), (ENV, N)])
    assert ds[2].reason_code == HYSTERESIS and ds[3].is_change and ds[3].reason_code == "DISENGAGED_ENVIRONMENT"


def test_confirmed_when_behaviour_would_act_anyway_is_eeg_confirmed() -> None:  # D-F6-174
    ds, _ = _run(_warm() + [(ENV, N), (ENV, _w(ei=-1.0))])
    assert ds[3].is_change and ds[3].reason_code == EEG_CONFIRMED


def test_veto_is_no_change_and_the_vetoed_window_counts_for_the_hysteresis() -> None:  # D-F6-174
    ds, _ = _run(_warm() + [(ENV, _w(ei=+1.0)), (ENV, N)])
    assert (ds[2].action, ds[2].reason_code) == (NO_CHANGE, EEG_VETO)
    assert ds[3].is_change and ds[3].reason_code == "DISENGAGED_ENVIRONMENT"   # 2nd window of the run


def test_overloaded_confirmed_by_theta_raises_assistance_with_cues() -> None:
    ds, _ = _run(_warm() + [(OVERLOADED, _w(theta=+1.3))])
    d = ds[-1]
    assert (d.dimension, d.to_level, d.proactive_cues, d.reason_code) == (LAL, "HIGH", True, EEG_CONFIRMED)


def test_unavailable_is_behaviour_adaptive_and_marked() -> None:
    ds, _ = _run(_warm() + [(ENV, _w(ei=-3.0, counted=False)), (ENV, _w(counted=False))])
    assert ds[2].reason_code == HYSTERESIS
    assert ds[3].reason_code == "DISENGAGED_ENVIRONMENT" and ds[3].eeg["effect"] == "UNAVAILABLE"
    assert ds[3].version == RULES_V2_MM


# Lead (§3.3, D-F6-128, D-F6-174) -------------------------------------------------------------------------------

def test_stable_with_ei_low_twice_leads_lal_one_step_down() -> None:
    ds, engine = _run(_warm() + [(STABLE, _w(ei=-1.6)), (STABLE, _w(ei=-1.8))])
    assert (ds[2].action, ds[2].reason_code) == (NO_CHANGE, EEG_ONLY_ALERT)
    d = ds[3]
    assert (d.dimension, d.from_level, d.to_level, d.reason_code, d.proactive_cues) == (LAL, "MEDIUM", "LOW", EEG_LED, False)
    assert engine.esl == "MEDIUM"


def test_lead_at_low_is_at_limit_without_raising_the_esl() -> None:
    ds, engine = _run(_warm() + [(STABLE, _w(ei=-2.0)), (STABLE, _w(ei=-2.0))], lal="LOW")
    assert (ds[3].action, ds[3].reason_code) == (NO_CHANGE, AT_LIMIT)
    assert ds[3].eeg["effect"] == "LED" and engine.esl == "MEDIUM" and engine.lal == "LOW"


def test_lead_off_medium_leads_instead_of_the_stable_return() -> None:  # D-F6-174
    items = _warm() + [(ENV, N), (ENV, N)] + [(STABLE, N)] * 3 + [(STABLE, _w(ei=-2.0)), (STABLE, _w(ei=-2.0))]
    ds, _ = _run(items)
    assert ds[3].dimension == ESL and ds[3].to_level == "LOW"       # trial 4: ESL down, cooldown to 7
    d = ds[8]                                                       # behaviour alone: STABLE_RETURN of the ESL
    assert (d.dimension, d.to_level, d.reason_code) == (LAL, "LOW", EEG_LED)


def test_a_lead_is_never_returned_by_stable() -> None:  # D-F6-59: a harder change only returns with DISENGAGED/OVERLOADED
    items = _warm() + [(STABLE, _w(ei=-2.0)), (STABLE, _w(ei=-2.0))] + [(STABLE, N)] * 6
    ds, engine = _run(items)
    assert ds[3].reason_code == EEG_LED
    assert [d.reason_code for d in ds[7:]] == [STABLE_NO_ACTION] * 3 and engine.lal == "LOW"


# Constraints unchanged -----------------------------------------------------------------------------------------

def test_confirmed_respects_initial_window_cooldown_and_tail() -> None:
    ds, _ = _run([(ENV, _w(ei=-2.0))] * 2)
    assert {d.reason_code for d in ds} == {INITIAL_WINDOW}
    ds, _ = _run(_warm() + [(ENV, _w(ei=-2.0))] * 4)
    assert ds[2].is_change and [d.reason_code for d in ds[3:6]] == [COOLDOWN] * 3
    ds, _ = _run([(STABLE, N)] * 16 + [(ENV, _w(ei=-2.0))])
    assert ds[16].reason_code == TAIL_FREEZE


def test_confirmed_at_the_limit_is_at_limit() -> None:
    ds, _ = _run(_warm() + [(ENV, _w(ei=-2.0))], esl="LOW")
    assert (ds[2].action, ds[2].reason_code) == (NO_CHANGE, AT_LIMIT)


# The record ----------------------------------------------------------------------------------------------------

def test_the_decision_carries_its_eeg_block() -> None:
    ds, _ = _run(_warm() + [(OVERLOADED, _w(ei=-0.41234, theta=1.23456))])
    block = ds[-1].as_dict()["eeg"]
    assert block == {"counted": True, "non_poor": 3, "clean_s": 9.0, "ei_z": -0.412, "theta_z": 1.235,
                     "alpha_z": 0.0, "effect": "CONFIRMED"}
    assert ds[-1].as_dict()["rules_version"] == RULES_V2_MM


def test_without_eeg_nothing_changes_in_the_record() -> None:
    engine = initial_state("MEDIUM", "MEDIUM", 0)
    result = EstimatorResult(trial_id="S7-003", state=STABLE, cause=None, confidence=1.0, support=1.0,
                             disengaged=(), overloaded=(), indicators={}, underchallenged=())
    d, _ = decide(result, 3, 21_000, engine)
    assert "eeg" not in d.as_dict() and d.version == RULES_V2 and d.eeg is None


def test_an_unknown_state_with_eeg_does_not_act() -> None:
    ds, _ = _run(_warm() + [("SOMETHING_NEW", _w(ei=-3.0))] * 2)
    assert all(not d.is_change for d in ds) and ds[-1].eeg["effect"] == "UNAVAILABLE"


def test_a_lead_at_the_limit_says_the_eeg_asked_for_it() -> None:  # review 10 Nov, item 5
    ds, _ = _run(_warm() + [(STABLE, _w(ei=-2.0)), (STABLE, _w(ei=-2.1))], lal="LOW")
    assert ds[3].reason_code == AT_LIMIT and "EEG: engagement index z -2.10" in ds[3].explanation


# T2 defaults, marked in the code for J5 (review 10 Nov: pinned) -------------------------------------------------

def test_default_2_an_alert_does_not_replace_hysteresis_or_a_stable_return() -> None:
    items = _warm() + [(ENV, N), (ENV, N)] + [(STABLE, N)] * 3 + [(STABLE, _w(ei=-1.2)), (STABLE, _w(ei=-1.2))]
    ds, _ = _run(items)
    assert ds[7].reason_code == HYSTERESIS and ds[7].eeg["effect"] == "ONLY_ALERT"
    assert ds[8].reason_code == "STABLE_RETURN" and ds[8].eeg["effect"] == "ONLY_ALERT"


def test_default_3_low_confidence_blocks_a_lead() -> None:
    engine = initial_state("MEDIUM", "MEDIUM", 0)
    for i, (conf, window) in enumerate([(1.0, N), (1.0, N), (1.0, _w(ei=-2.0)), (0.4, _w(ei=-2.0))], start=1):
        result = EstimatorResult(trial_id=f"S7-{i:03d}", state=STABLE, cause=None, confidence=conf, support=1.0,
                                 disengaged=(), overloaded=(), indicators={}, underchallenged=())
        d, engine = decide(result, i, i * TRIAL_MS, engine, eeg=window)
    assert d.reason_code == "LOW_CONFIDENCE" and d.eeg["effect"] == "LED" and engine.lal == "MEDIUM"


def test_the_stored_block_is_enough_to_lead_after_a_rebuild() -> None:  # review 10 Nov, required item 2 (X1 rebuild)
    from dataclasses import replace

    ds, engine = _run(_warm() + [(STABLE, _w(ei=-1.8))])            # trial 3: the first low window
    rebuilt = replace(engine, last_eeg=ds[-1].as_dict()["eeg"])     # what rebuild gets from the payload
    result = EstimatorResult(trial_id="S7-004", state=STABLE, cause=None, confidence=1.0, support=1.0,
                             disengaged=(), overloaded=(), indicators={}, underchallenged=())
    live, _ = decide(result, 4, 4 * TRIAL_MS, engine, eeg=_w(ei=-1.9))
    again, _ = decide(result, 4, 4 * TRIAL_MS, rebuilt, eeg=_w(ei=-1.9))
    assert live.reason_code == again.reason_code == EEG_LED and live.as_dict() == again.as_dict()


# D-F6-182: at most 3 changes per S7, in both adaptive conditions ----------------------------------------------

def _sustained(eeg):
    """DISENGAGED (environment) the 20 trials, with room to lower the ESL each time (as if the levels came back)."""
    engine, changes, last = initial_state("MEDIUM", "MEDIUM", 0), [], None
    for i in range(1, 21):
        result = EstimatorResult(trial_id=f"S7-{i:03d}", state=DISENGAGED, cause=ENVIRONMENT, confidence=1.0,
                                 support=1.0, disengaged=(), overloaded=(), indicators={}, underchallenged=())
        d, engine = decide(result, i, i * TRIAL_MS, engine, eeg=eeg)
        engine = engine.with_levels(esl="MEDIUM")
        changes += [i] if d.is_change else []
        last = d if d.reason_code == MAX_CHANGES else last
    return changes, last


def test_confirmed_every_window_stops_at_three_changes() -> None:
    changes, blocked = _sustained(_w(ei=-2.0))
    assert changes == [3, 7, 11]                     # the 4th (trial 15) is blocked
    assert blocked.trial_sequence == 15 and blocked.action == NO_CHANGE


def test_behaviour_alone_never_reaches_the_cap() -> None:
    changes, blocked = _sustained(None)
    assert changes == [4, 9, 14] and blocked is None

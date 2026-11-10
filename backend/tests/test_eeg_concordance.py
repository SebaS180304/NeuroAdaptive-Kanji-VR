"""
T1 (tasks/todo.md, Tue 10): app/eeg/concordance.py. What the EEG does in a decision window, one test per row
of Reevaluacion_EEG_Justificacion.md §3.5 (D-F6-128), the lead rule of §3.3 and the defaults of D-F6-174.
"""

import pytest

from app.adaptation.estimator import DISENGAGED, OVERLOADED, STABLE, UNDERCHALLENGED
from app.eeg import concordance as c


def _w(ei=None, theta=None, alpha=None, counted=True) -> dict:
    """A window as window.evaluate() returns it."""
    return {"counted": counted, "non_poor": 3, "clean_s": 9.0,
            "z": {"engagement_index": ei, "theta_fz": theta, "alpha_parietal": alpha, "theta_beta": None}}


# §3.5, one test per row ------------------------------------------------------------------------------------

@pytest.mark.parametrize("state, window, effect", [
    (DISENGAGED, _w(ei=-1.0), c.CONFIRMED),         # EI z <= -1 confirms (both causes: the action is rules')
    (DISENGAGED, _w(ei=+1.0), c.VETO),              # EI z >= +1 vetoes
    (UNDERCHALLENGED, _w(ei=-1.2), c.CONFIRMED),    # EI z <= -1 confirms (both causes)
    (UNDERCHALLENGED, _w(ei=+1.4), c.VETO),         # EI z >= +1 vetoes
    (OVERLOADED, _w(theta=+1.0), c.CONFIRMED),      # frontal theta z >= +1 confirms
    (OVERLOADED, _w(theta=-1.0), c.VETO),           # frontal theta z <= -1 vetoes
    (STABLE, _w(ei=-1.2), c.ONLY_ALERT),            # EI z between -1.5 and -1: alert only
])
def test_each_row_of_3_5(state, window, effect) -> None:
    assert c.effect(state, window, None) == effect


def test_stable_with_ei_low_in_two_windows_in_a_row_leads() -> None:
    assert c.effect(STABLE, _w(ei=-1.5), _w(ei=-2.0)) == c.LED


# §3.2 between -1 and +1, and the index each state reads ---------------------------------------------------

@pytest.mark.parametrize("state, window", [
    (DISENGAGED, _w(ei=-0.9)), (UNDERCHALLENGED, _w(ei=0.99)), (OVERLOADED, _w(theta=0.5)),
    (STABLE, _w(ei=-0.9)), (STABLE, _w(ei=+3.0)),
    (OVERLOADED, _w(ei=-3.0, theta=0.0)),       # OVERLOADED reads theta, never the EI
    (DISENGAGED, _w(ei=0.0, theta=+3.0)),       # and the others never theta
])
def test_neutral(state, window) -> None:
    assert c.effect(state, window, None) == c.NEUTRAL


# Lead (§3.3) and D-F6-174 ----------------------------------------------------------------------------------

def test_one_window_under_minus_1_5_is_only_an_alert() -> None:  # D-F6-174
    assert c.effect(STABLE, _w(ei=-2.5), _w(ei=-0.5)) == c.ONLY_ALERT
    assert c.effect(STABLE, _w(ei=-2.5), None) == c.ONLY_ALERT  # first window of S7


def test_a_previous_window_without_valid_eeg_does_not_lead() -> None:
    assert c.effect(STABLE, _w(ei=-2.0), _w(ei=-2.0, counted=False)) == c.ONLY_ALERT
    assert c.effect(STABLE, _w(ei=-2.0), _w(ei=None)) == c.ONLY_ALERT


def test_only_stable_leads() -> None:
    assert c.effect(DISENGAGED, _w(ei=-2.0), _w(ei=-2.0)) == c.CONFIRMED


# Unavailable (§5.5) ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("state", [DISENGAGED, OVERLOADED, UNDERCHALLENGED, STABLE])
def test_a_window_where_the_eeg_does_not_count_is_unavailable(state) -> None:
    assert c.effect(state, _w(ei=-3.0, theta=3.0, counted=False), None) == c.UNAVAILABLE
    assert c.effect(state, None, None) == c.UNAVAILABLE


def test_the_index_the_state_reads_missing_is_unavailable() -> None:  # reference SD 0 (M5): that index does not count
    assert c.effect(OVERLOADED, _w(ei=-3.0, theta=None), None) == c.UNAVAILABLE
    assert c.effect(DISENGAGED, _w(ei=None, theta=3.0), None) == c.UNAVAILABLE


# Alpha never changes the result (D-F6-129) ----------------------------------------------------------------

@pytest.mark.parametrize("state", [DISENGAGED, OVERLOADED, UNDERCHALLENGED, STABLE])
@pytest.mark.parametrize("ei, theta", [(-2.0, 2.0), (0.0, 0.0), (2.0, -2.0)])
def test_alpha_never_changes_the_result(state, ei, theta) -> None:
    results = {c.effect(state, _w(ei=ei, theta=theta, alpha=a), _w(ei=ei, theta=theta, alpha=a))
               for a in (None, -5.0, 0.0, 5.0)}
    assert len(results) == 1

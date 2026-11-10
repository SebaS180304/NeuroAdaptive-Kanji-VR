"""
What the EEG does in one decision window of MULTIMODAL_ADAPTIVE (Reevaluacion_EEG_Justificacion.md §3.2, §3.3, §3.5;
D-F6-128). Pure: the behavioural state and two windows of window.evaluate() in, one effect out. Which action follows
(ESL or LAL, AT_LIMIT, the hysteresis) is rules-v2-mm's: the EEG decides when an action applies, not which.

| State            | Index read     | Confirms     | Vetoes       |
| DISENGAGED       | EI             | z <= -1      | z >= +1      |
| UNDERCHALLENGED  | EI             | z <= -1      | z >= +1      |
| OVERLOADED       | frontal theta  | z >= +1      | z <= -1      |
| STABLE           | EI             | leads with z <= -1.5 in this window and the previous one; alerts with z <= -1 |
Between -1 and +1 the EEG is neutral. Parietal alpha is never read (D-F6-129). The thresholds are "to validate".
"""

from app.adaptation.estimator import DISENGAGED, OVERLOADED, STABLE, UNDERCHALLENGED

CONFIRMED, VETO, LED, UNAVAILABLE, ONLY_ALERT, NEUTRAL = (
    "CONFIRMED", "VETO", "LED", "UNAVAILABLE", "ONLY_ALERT", "NEUTRAL")

Z_AGREE = 1.0
Z_LEAD = 1.5
EI, THETA = "engagement_index", "theta_fz"


def _z(window: dict | None, index: str) -> float | None:
    """z of the index when the EEG counted in the window (D-F6-127), else None."""
    return window["z"][index] if window and window["counted"] else None


def effect(state: str, window: dict | None, previous: dict | None) -> str:
    """window: this decision's window.evaluate(); previous: the decision before it in S7 (None for the first)."""
    if state == OVERLOADED:
        z = _z(window, THETA)
        if z is None:
            return UNAVAILABLE  # default (T1): the index the state reads did not count (reference SD 0, M5)
        return CONFIRMED if z >= Z_AGREE else VETO if z <= -Z_AGREE else NEUTRAL

    z = _z(window, EI)
    if z is None:
        return UNAVAILABLE
    if state in (DISENGAGED, UNDERCHALLENGED):
        return CONFIRMED if z <= -Z_AGREE else VETO if z >= Z_AGREE else NEUTRAL
    if state == STABLE:
        before = _z(previous, EI)
        if z <= -Z_LEAD and before is not None and before <= -Z_LEAD:
            return LED  # a previous window without valid EEG does not lead (§3.3)
        return ONLY_ALERT if z <= -Z_AGREE else NEUTRAL  # D-F6-174: z <= -1.5 in a single window is only an alert
    return UNAVAILABLE  # an unknown state: the EEG never stops a decision, and rules never act on it

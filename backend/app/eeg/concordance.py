"""
What the EEG does in one decision window of MULTIMODAL_ADAPTIVE (Reevaluacion_EEG_Justificacion.md §3.2, §3.3, §3.5;
D-F6-128). Pure: the behavioural state and two EEG blocks in, one effect out. A block (``block()``) is what the
ADAPTATION_DECISION payload stores, so a rebuilt session state reads the previous window exactly as the live one did. Which action follows
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
EI, THETA = "ei_z", "theta_z"


def _r(z: float | None) -> float | None:
    return None if z is None else round(z, 3)


def block(window: dict) -> dict:
    """window.evaluate() as the decision stores it (payload ``eeg``, without ``effect``); z rounded to 3 decimals."""
    if "z" not in window:  # already a block (the payload of a stored decision, when the state is rebuilt)
        return {k: window.get(k) for k in ("counted", "non_poor", "clean_s", "ei_z", "theta_z", "alpha_z")}
    z = window.get("z") or {}
    return {"counted": window.get("counted"), "non_poor": window.get("non_poor"), "clean_s": window.get("clean_s"),
            "ei_z": _r(z.get("engagement_index")), "theta_z": _r(z.get("theta_fz")),
            "alpha_z": _r(z.get("alpha_parietal"))}


def _z(eeg: dict | None, index: str) -> float | None:
    """z of the index when the EEG counted in the window (D-F6-127), else None."""
    return eeg.get(index) if eeg and eeg.get("counted") else None


def effect(state: str, window: dict | None, previous: dict | None) -> str:
    """window: this decision's block(); previous: the block of the decision before it in S7 (None for the first)."""
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

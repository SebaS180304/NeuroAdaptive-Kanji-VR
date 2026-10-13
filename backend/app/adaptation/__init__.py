"""
Behavioural adaptation (Phase 5a).

Pure functions over the session event stream, with no database or clock
access, so that what the backend decides live can be replayed exactly over a
recorded session (Planteamiento_Tecnico_F5a.md §2.1, principle 3):

- ``trials``: turns the ordered event stream into one ``TrialRecord`` per
  answered trial, with the time away and the environment interactions that
  belong to it (D4, D5).
- ``profile``: the S6 calibration profile of the participant (§4.1, D6).
- ``indicators``: the window indicators over the last answered S7 trials
  (§4.2).

- ``estimator``: state, cause and confidence of each window (§4.3).
- ``rules``: the rule engine, from state to action under the constraints of
  spec §10.2 (§5).
- ``replay``: the estimator and the rule engine over a recorded session, trial
  by trial (``python -m app.adaptation.replay <session>``).

The per-session in-memory state (``state.py``) comes in a later module.
"""

from app.adaptation.estimator import EstimatorResult, estimate
from app.adaptation.indicators import WindowIndicators, window_indicators
from app.adaptation.profile import S6Profile, build_profile
from app.adaptation.rules import Decision, EngineState, adaptation_allowed, decide, initial_state
from app.adaptation.trials import TrialRecord, TrialStreamBuilder, build_trials

__all__ = [
    "Decision",
    "EngineState",
    "EstimatorResult",
    "S6Profile",
    "TrialRecord",
    "TrialStreamBuilder",
    "WindowIndicators",
    "adaptation_allowed",
    "build_profile",
    "build_trials",
    "decide",
    "estimate",
    "initial_state",
    "window_indicators",
]

# Adaptation engine

Code in `backend/app/adaptation/` (behaviour) and `backend/app/eeg/window.py`, `concordance.py` (the EEG's
part). It runs in the backend, at each S7 answer, only in `BEHAVIOR_ADAPTIVE` and `MULTIMODAL_ADAPTIVE`
(`rules.ADAPTIVE_CONDITIONS`). The versions that new sessions run with are `ESTIMATOR_VERSION` and
`RULES_VERSION` (both v2); each decision stores its versions.

## Two dimensions, three levels

| Dimension | Action | What changes in Unity |
| --- | --- | --- |
| `ESL` | `CHANGE_ENVIRONMENT` | the room (environmental stimulation) |
| `LAL` | `CHANGE_ASSISTANCE` | the help shown during the task |

Levels `LOW`, `MEDIUM`, `HIGH`; home level `MEDIUM`.

## From answers to a decision

1. **Calibration profile** (`profile.py`): S6 gives the person's pace per task type, accuracy, idle time
   and reliability. S7 is read against it.
2. **Indicators** (`indicators.py`) over a window of the last trials: pace ratio and its z, accuracy
   against practice, fast and slow answers, head away, dwell, orientation, idle.
3. **Estimator** (`estimator.py`): a state and a cause, with a confidence.
    - States: `STABLE`, `DISENGAGED`, `OVERLOADED`, `UNDERCHALLENGED`.
    - Causes, for example `FAST`, `IMPULSIVE`, `AWAY`, `ENVIRONMENT`, `NO_ENVIRONMENT`.
4. **Rules** (`rules.py`): from the state to an action, or `NO_CHANGE` with its reason:
   `INITIAL_WINDOW` (first trials), `COOLDOWN` (after a change), `HYSTERESIS` (the state must hold),
   `LOW_CONFIDENCE`, `AT_LIMIT`, `MAX_CHANGES`, `TAIL_FREEZE` (end of S7), `STABLE`, `STABLE_RETURN`.
5. **Outcome** (`outcome.py`): each change is judged on the trials after it (for example, the state gone).

`replay.py` runs a recorded session through the same estimator and rules, from the database or from a
JSON export, and with `--xdf` adds the EEG cut from the recording.

## The EEG's part (MULTIMODAL_ADAPTIVE)

- **Does the EEG count in this window** (`window.py`, P7): the epochs that ended at least 1.5 s before the
  answer, inside the 3-trial window from the 3rd S7 trial; at least 2 non-POOR epochs and 5 s of clean
  signal over a span of 15 s or more. If not: `NOT_COUNTED`, the decision is behavioural.
- **The z** of the Engagement Index and theta in Fz against the session's reference (see "EEG pipeline").
- **Concordance** (`concordance.py`), with `Z_AGREE` = 1.0 and `Z_LEAD` = 1.5:
    - `EEG_CONFIRMED`: the EEG agrees with a behavioural change;
    - `EEG_VETO`: the EEG holds a behavioural change back;
    - `EEG_LED`: two windows in a row at or past −1.5 can let the EEG lead;
    - `EEG_ONLY_ALERT`: the EEG alone flags it, no action.
- Every S7 decision of a multimodal session carries an `eeg` block (counted, non-POOR epochs, clean
  seconds, both z, effect) in its event and in `adaptation_decisions`.
- A session counts as multimodal (A-7) if the S4 alpha passes and at least 60 % of the S7 windows count.
  The official figure is what the live engine saw.

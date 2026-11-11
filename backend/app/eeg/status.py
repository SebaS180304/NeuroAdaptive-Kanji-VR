"""
Is the live EEG there at an S7 answer (D-F6-171, D-F6-174; Reevaluación §5.5)? Pure: the backend reads live.py's
heartbeat and the EEG gap from eeg_sessions and asks here.

- Heartbeat fresh, samples flowing: CONNECTED. Fresh, but no sample for LOST_GAP_MS: LOST (cap off, Bluetooth off,
  AURA closed: live.py is alive and says so). Stale or never written: PROCESS_DOWN (a dead process cannot say it).
- Each change is one EEG_STATUS; LOST/PROCESS_DOWN -> CONNECTED is reported as RECOVERED.
- More than 60 s in a row without EEG cancels the EEG for the rest of the session (§5.5): the gap (LOST) or the
  heartbeat's age (PROCESS_DOWN, as D-F6-171 asks the rule to read the same fields).
"""

CONNECTED, LOST, RECOVERED, PROCESS_DOWN = "CONNECTED", "LOST", "RECOVERED", "PROCESS_DOWN"
LOST_OVER_60S, S4_ALPHA_FAILED = "LOST_OVER_60S", "S4_ALPHA_FAILED"   # eeg_sessions.not_counted_reason

HEARTBEAT_STALE_S = 10.0   # D-F6-171 proposal (live.py beats every 2 s); on the J5 freeze list
LOST_GAP_MS = 2_000        # default (X3): live.py pulls every 0.2 s, so 2 s without a sample is a stopped stream; J5
LOST_SESSION_MS = 60_000   # §5.5


def classify(heartbeat_age_s: float | None, gap_ms: int | None) -> str:
    if heartbeat_age_s is None or heartbeat_age_s > HEARTBEAT_STALE_S:
        return PROCESS_DOWN
    return LOST if gap_ms is not None and gap_ms > LOST_GAP_MS else CONNECTED


class Tracker:
    """One per live session: the last status and whether the EEG is cancelled."""

    def __init__(self) -> None:
        self.last: str | None = None
        self.cancelled: str | None = None

    def observe(self, now: str, gap_ms: int | None, heartbeat_age_s: float | None) -> str | None:
        """The EEG_STATUS to write for this observation, or None if nothing changed."""
        # shortcut: seen only at S7 answers, so an outage that starts and ends between two answers counts up to the
        # last answer that saw it (a trial short at most); upgrade: live.py writes the longest gap itself.
        without_ms = (gap_ms or 0) if now == LOST else (heartbeat_age_s or 0) * 1000 if now == PROCESS_DOWN else 0
        if without_ms > LOST_SESSION_MS:
            self.cancelled = self.cancelled or LOST_OVER_60S
        report = None
        if now != self.last:
            report = RECOVERED if now == CONNECTED and self.last in (LOST, PROCESS_DOWN) else now
        self.last = now
        return report

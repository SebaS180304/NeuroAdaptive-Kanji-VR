"""
X2 (tasks/todo.md): replay.py with the EEG. Every S7 decision gets the window an eeg source gives (from an XDF:
the epochs cut as live.py cuts them, D-F6-171), except while EEG_STATUS said the process was down, as live did not
have it either. Without a source the replay is the one it always was. No database.
"""

import json
from pathlib import Path

import pytest

from app.adaptation import replay

FIXTURE = Path(__file__).parent / "fixtures" / "prueba_fase_f3_events.json"
COUNTED = {"counted": True, "non_poor": 4, "clean_s": 9.0,
           "z": {"engagement_index": 0.1, "theta_fz": 0.2, "alpha_parietal": 0.3, "theta_beta": 0.0}}


@pytest.fixture(autouse=True)
def _clean_test_participants():
    """Overrides the conftest fixture: these tests do not touch the database."""
    yield


def _events() -> list[dict]:
    return replay.load_from_file(FIXTURE, "87761ce6")


def _status(after_id: float, status: str, elapsed_ms: int) -> dict:
    return {"id": after_id, "session_id": "87761ce6", "event_type": "EEG_STATUS",
            "payload": {"status": status, "session_elapsed_ms": elapsed_ms}}


def test_without_an_eeg_source_no_decision_has_an_eeg_block() -> None:
    _, rows = replay.replay(_events())
    assert rows and all(r["decision"].eeg is None for r in rows)


def test_with_a_source_every_s7_decision_has_its_window() -> None:
    seen = []

    def source(first_start_ms, decision_ms):
        seen.append((first_start_ms, decision_ms))
        return COUNTED

    _, rows = replay.replay(_events(), eeg_source=source)
    assert len(seen) == len(rows)
    assert all(r["decision"].eeg["counted"] is True for r in rows)
    assert all(lo <= hi for lo, hi in seen)


def test_a_window_while_the_process_was_down_does_not_count() -> None:
    events = _events()
    _, rows = replay.replay(events, eeg_source=lambda *_: COUNTED)
    answered = [r["trial"].answered_ms for r in rows]
    down_at, up_at = answered[3] - 1, answered[6] - 1          # down before the 4th decision, back before the 7th
    # stored at the end, as the backend writes them; the replay reads them by their time
    with_status = events + [_status(10**9, "PROCESS_DOWN", down_at), _status(10**9 + 1, "CONNECTED", up_at)]
    _, rows = replay.replay(with_status, eeg_source=lambda *_: COUNTED)
    counted = [r["decision"].eeg["counted"] for r in rows]
    assert counted[:3] == [True] * 3 and counted[3:6] == [False] * 3 and all(counted[6:])


def test_hitches_over_100_ms_per_state() -> None:
    markers = [(1.0, {"event": "FRAME_HITCH", "duration_ms": 150.0, "state": "S7_EXPERIMENTAL_RETRIEVAL"}),
               (2.0, {"event": "FRAME_HITCH", "duration_ms": 90.0, "state": "S7_EXPERIMENTAL_RETRIEVAL"}),
               (3.0, {"event": "FRAME_HITCH", "duration_ms": 120.0, "state": "S4_EEG_BASELINE"}),
               (4.0, {"event": "STATE_ENTERED", "state": "S8_IMMEDIATE_ASSESSMENT"})]
    assert replay.hitches_per_state(markers) == {"S7_EXPERIMENTAL_RETRIEVAL": (1, 150.0), "S4_EEG_BASELINE": (1, 120.0)}

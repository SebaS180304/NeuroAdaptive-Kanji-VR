"""
X1b (tasks/todo.md): app/eeg/live.py, the pure part. The buffer cuts each finished epoch once, on the session's
grid, with the S3 offset (D-F6-173), and only when the zero-phase filter has signal after it. No LSL, no database.
"""

import numpy as np
import pytest

from app.eeg import epochs, live, preprocess, sync
from app.eeg.baseline import DEFAULT_MONTAGE

SR = 250.0
S3, S4, S6 = "S3_SYSTEM_VALIDATION", "S4_EEG_BASELINE", "S6_GUIDED_PRACTICE_CALIBRATION"


@pytest.fixture(autouse=True)
def _clean_test_participants():
    """Overrides the conftest fixture: no database here."""
    yield


def _signal(seconds: float, seed: int = 0):
    n = int(seconds * SR)
    return np.random.default_rng(seed).normal(0, 5, (n, 8)), 100.0 + np.arange(n) / SR


def _state(t: float, state: str, elapsed_ms: int):
    return (t, {"schema_version": 1, "event": "STATE_ENTERED", "state": state, "esl": "MEDIUM",
                "session_elapsed_ms": elapsed_ms})


def _feed(buf: live.Buffer, x, ts, markers, step_s: float = 0.5):
    """Push the recording in chunks as the inlet would, collecting what the buffer gives at each step."""
    out, n, k = [], int(step_s * SR), 0
    for i in range(0, len(ts), n):
        buf.add(x[i:i + n].tolist(), ts[i:i + n].tolist(), [m for m in markers if ts[i] <= m[0] < ts[i] + step_s])
        buf.sync_if_ready()
        out += buf.new_epochs()
        k += 1
    return out


def test_nothing_is_cut_before_s3_ends() -> None:
    x, ts = _signal(30.0)
    buf = live.Buffer(SR, DEFAULT_MONTAGE)
    assert _feed(buf, x, ts, [_state(100.0, S3, 0)]) == []


def test_each_finished_epoch_once_on_the_session_grid_and_as_offline() -> None:
    x, ts = _signal(60.0)
    markers = [_state(100.0, S3, 0), _state(110.0, S4, 10_000), _state(125.0, S6, 25_000)]
    buf = live.Buffer(SR, DEFAULT_MONTAGE)
    got = _feed(buf, x, ts, markers)
    idx = [e["epoch_index"] for e in got]
    assert idx == list(range(len(idx))) and len(idx) >= 20               # consecutive, none twice
    assert all(e["lsl_start"] + epochs.EPOCH_S <= ts[-1] - live.EDGE_S + 1e-9 for e in got)
    offline = {e["epoch_index"]: e for e in epochs.make_epochs(preprocess.filter_eeg(x, SR), ts, SR, DEFAULT_MONTAGE, markers)}
    for e in got:
        assert e["lsl_start"] == offline[e["epoch_index"]]["lsl_start"]
        assert e["chunk_clean"] == offline[e["epoch_index"]]["chunk_clean"]
        assert e["start_ms"] == offline[e["epoch_index"]]["start_ms"] and e["game_state"] == offline[e["epoch_index"]]["game_state"]


def test_the_s3_offset_is_subtracted_from_the_eeg_stamps(monkeypatch) -> None:  # D-F6-173
    monkeypatch.setattr(sync, "compute", lambda cz, ts, markers: (40.0, None, {"reason": None}))
    x, ts = _signal(40.0)
    buf = live.Buffer(SR, DEFAULT_MONTAGE)
    got = _feed(buf, x, ts, [_state(100.0, S3, 0), _state(110.0, S4, 10_000)])
    assert buf.offset_ms == 40.0
    assert got[0]["lsl_start"] == pytest.approx(ts[0] - 0.040)       # the grid starts at the corrected first stamp


def test_under_three_clear_taps_there_is_no_correction() -> None:  # D-F6-176
    x, ts = _signal(30.0)
    buf = live.Buffer(SR, DEFAULT_MONTAGE)
    got = _feed(buf, x, ts, [_state(100.0, S3, 0), _state(110.0, S4, 10_000)])
    assert buf.offset_ms is None and got[0]["lsl_start"] == pytest.approx(ts[0])

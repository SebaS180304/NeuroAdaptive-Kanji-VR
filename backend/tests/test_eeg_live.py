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


def test_the_epochs_before_a_moment_are_all_cut_only_after_the_filter_wait() -> None:
    # the reference waits for every S6 epoch (centre before S7's entry), not the moment S7 is entered
    x, ts = _signal(60.0)
    buf = live.Buffer(SR, DEFAULT_MONTAGE)
    buf.add(x[:int(40 * SR)].tolist(), ts[:int(40 * SR)].tolist(), [_state(100.0, S3, 0), _state(110.0, S4, 10_000)])
    buf.sync_if_ready()
    cut = buf.new_epochs()
    s7 = 139.5                                            # S7 entered 0.5 s before the last sample
    assert not buf.cut_past(s7)                           # the epoch centred at 138.75 still waits for the filter
    buf.add(x[int(40 * SR):int(45 * SR)].tolist(), ts[int(40 * SR):int(45 * SR)].tolist())
    cut += buf.new_epochs()
    assert buf.cut_past(s7) and max(e["lsl_start"] + 2.5 for e in cut) >= s7 - 2.5


def test_a_live_tail_and_the_whole_xdf_cut_on_the_stored_origin_give_the_same_epochs() -> None:  # G1, D-F6-200 (1)
    x, ts = _signal(60.0)
    markers = [_state(100.0, S3, 0), _state(110.0, S4, 10_000), _state(125.0, S6, 25_000)]
    k = int(3.7 * SR)                                      # LabRecorder started 3.7 s before the live inlet
    live_buf = live.Buffer(SR, DEFAULT_MONTAGE)
    got = _feed(live_buf, x[k:], ts[k:], markers)
    xdf_buf = live.Buffer(SR, DEFAULT_MONTAGE)
    xdf_buf.t0 = live_buf.t0                              # what xdf_source does with eeg_sessions.grid_origin_lsl
    again = {e["epoch_index"]: e for e in _feed(xdf_buf, x, ts, markers)}
    offline = {e["epoch_index"]: e for e in epochs.make_epochs(preprocess.filter_eeg(x, SR), ts, SR, DEFAULT_MONTAGE,
                                                                markers, t0=live_buf.t0)}
    assert live_buf.t0 == pytest.approx(ts[k]) and len(got) >= 20
    for e in got:
        for other in (again, offline):
            assert e["lsl_start"] == pytest.approx(other[e["epoch_index"]]["lsl_start"])
            assert e["chunk_clean"] == other[e["epoch_index"]]["chunk_clean"]


# ---------- CH1c: the persistently bad channel live, as offline (D-F6-216, D-F6-224) ----------

LABELS = [DEFAULT_MONTAGE[f"CH{i + 1}"] for i in range(8)]


def _f3_bad(seconds: float = 150.0):
    x, ts = _signal(seconds)
    on = (ts >= 130.0) & (ts < 190.0)   # 30–90 s after the grid's origin (ts[0] = 100); 10 Hz survives the filter
    x[on, LABELS.index("F3")] += 300.0 * np.sin(2 * np.pi * 10 * ts[on])
    return x, ts


def test_live_finds_the_channel_when_offline_does_and_cuts_without_it() -> None:
    x, ts = _f3_bad()
    markers = [_state(100.0, S3, 0), _state(110.0, S4, 10_000), _state(120.0, S6, 20_000)]
    buf = live.Buffer(SR, DEFAULT_MONTAGE)
    got = _feed(buf, x, ts, markers)
    assert buf.bad == epochs.persistently_bad(preprocess.filter_eeg(x, SR), ts, LABELS, markers, buf.t0) == [("F3", 190.0)]
    assert {e["excluded_channels"] for e in got if e["lsl_start"] >= 190.0} == {"F3"}
    assert {e["excluded_channels"] for e in got if e["lsl_start"] < 190.0} == {None}


def test_live_reference_is_recomputed_without_the_channel_as_offline() -> None:
    x, ts = _f3_bad()
    markers = [_state(100.0, S3, 0), _state(110.0, S4, 10_000), _state(120.0, S6, 20_000)]
    buf = live.Buffer(SR, DEFAULT_MONTAGE)
    got = _feed(buf, x, ts, markers)
    assert buf.reference(got) == epochs.cut_session(preprocess.filter_eeg(x, SR), ts, SR, DEFAULT_MONTAGE, markers, buf.t0)[2]


def test_a_clean_session_has_no_channel_out_live() -> None:
    x, ts = _signal(100.0)
    markers = [_state(100.0, S3, 0), _state(110.0, S4, 10_000)]
    buf = live.Buffer(SR, DEFAULT_MONTAGE)
    got = _feed(buf, x, ts, markers)
    assert buf.bad == [] and {e["excluded_channels"] for e in got} == {None}


def test_the_monitor_reads_the_buffer_without_changing_its_epochs() -> None:   # M1b, D-F6-254
    x, ts = _signal(60.0)
    markers = [_state(100.0, S3, 0), _state(110.0, S4, 10_000)]
    a, b = live.Buffer(SR, DEFAULT_MONTAGE), live.Buffer(SR, DEFAULT_MONTAGE)
    got_a = _feed(a, x, ts, markers)
    got_b, n, prev = [], int(0.5 * SR), None
    for i in range(0, len(ts), n):   # the same feed, with a monitor snapshot after every step
        b.add(x[i:i + n].tolist(), ts[i:i + n].tolist(), [m for m in markers if ts[i] <= m[0] < ts[i] + 0.5])
        b.sync_if_ready()
        got_b += b.new_epochs()
        prev = live.monitor_snapshot(b, prev)
    assert got_a == got_b
    assert [c["label"] for c in prev["channels"]] == LABELS and prev["session_60_uv"] is not None


def test_the_traces_read_the_samples_without_changing_the_epochs() -> None:   # TR2, C1 of EEG (D-F6-301 (5))
    from app.eeg import traces

    x, ts = _signal(60.0)
    markers = [_state(100.0, S3, 0), _state(110.0, S4, 10_000)]
    a, b = live.Buffer(SR, DEFAULT_MONTAGE), live.Buffer(SR, DEFAULT_MONTAGE)
    got_a = _feed(a, x, ts, markers)
    tr, got_b, n = traces.Traces(SR, 8), [], int(0.5 * SR)
    for i in range(0, len(ts), n):   # the same feed, with the traces fed every step as live.run does
        chunk, stamps = x[i:i + n].tolist(), ts[i:i + n].tolist()
        b.add(chunk, stamps, [m for m in markers if ts[i] <= m[0] < ts[i] + 0.5])
        tr.feed(chunk, stamps)
        b.sync_if_ready()
        got_b += b.new_epochs()
    assert got_a == got_b
    assert tr.take_bins() and all(r is not None for r in tr.now_rms())


def test_trace_rows_are_in_session_ms_on_the_markers_clock() -> None:   # TR2
    markers = [_state(100.0, S3, 40_000), _state(110.0, S4, 50_000)]   # session zero at 60.0 s on the markers' clock
    bins = [{"t": 120.025, "min": [-1.0] * 8, "max": [2.0] * 8}, {"t": 120.065, "min": [0.0] * 8, "max": [1.0] * 8}]
    assert live.trace_rows([], markers, None) == []
    rows = live.trace_rows(bins, markers, 25.0)   # EEG 25 ms ahead of the markers (the S3 offset)
    assert [r["t_ms"] for r in rows] == [60_000, 60_040]
    assert rows[0]["mins"] == [-1.0] * 8 and rows[0]["maxs"] == [2.0] * 8
    assert live.trace_rows(bins, [], None) is None   # no session clock yet: the bins wait


def test_the_traces_switch_is_off_by_default(monkeypatch) -> None:   # TR2
    from app.config import Settings

    monkeypatch.delenv("EEG_MONITOR_TRACES", raising=False)
    assert Settings(_env_file=None).eeg_monitor_traces is False
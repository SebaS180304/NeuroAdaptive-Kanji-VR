"""
TR1 (tasks/plan.md; D-F6-293 (5), D-F6-297 (2), D-F6-301 (5)): the monitor's 8-channel traces. A causal filter with its
state kept between pieces, min/max per 40 ms bin and the µV RMS of the last second. Pure; no database.
"""

import numpy as np
import pytest
from scipy.signal import sosfilt, sosfilt_zi

from app.eeg import traces

SR = 250.0
T0 = 1000.0


@pytest.fixture(autouse=True)
def _clean_test_participants():
    """Overrides the conftest fixture: no database here."""
    yield


def _raw(seconds=10.0, seed=0):
    """8 channels of 5 µV noise on a 30 mV offset, as AURA's raw signal."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    return 30_000.0 + rng.normal(0, 5, (n, 8)), T0 + np.arange(n) / SR


def _feed(tr, x, ts, piece):
    return np.vstack([tr.feed(x[i:i + piece], ts[i:i + piece]) for i in range(0, len(x), piece)])


def test_filter_in_pieces_equals_the_whole_signal_at_once():
    x, ts = _raw()
    tr = traces.Traces(SR, 8)
    pieces = _feed(tr, x, ts, 37)  # pieces that do not line up with the bins
    sos = traces.sos(SR)
    whole, _ = sosfilt(sos, x, axis=0, zi=sosfilt_zi(sos)[:, :, None] * x[0][None, None, :])
    np.testing.assert_allclose(pieces, whole, atol=1e-6)


def test_starts_from_the_first_sample_so_the_dc_offset_makes_no_transient():
    x, ts = _raw()
    tr = traces.Traces(SR, 8)
    _feed(tr, x, ts, 50)
    bins = tr.take_bins()
    assert max(abs(b["max"][c]) for b in bins for c in range(8)) < 60  # 5 µV noise, never the 30 mV offset


def test_bins_are_40_ms_min_and_max_and_keep_a_one_sample_spike():
    x, ts = _raw(seconds=2.0)
    x[260, 4] += 5_000.0  # a tap on Cz
    tr = traces.Traces(SR, 8)
    _feed(tr, x, ts, 25)
    bins = tr.take_bins()
    assert len(bins) == 50  # 500 samples / 10 per bin
    assert [round(b["t"], 3) for b in bins[:3]] == [T0, T0 + 0.04, T0 + 0.08]
    assert all(b["min"][c] <= b["max"][c] for b in bins for c in range(8))
    spike = next(b for b in bins if b["t"] <= ts[260] < b["t"] + 0.04)
    others = np.median([b["max"][4] for b in bins if b is not spike])
    assert spike["max"][4] > 1_000 and spike["max"][4] > 50 * others  # the 40 Hz low-pass spreads it; min/max keeps it
    assert tr.take_bins() == []  # each bin once


def test_a_flat_channel_stays_flat():
    x, ts = _raw()
    x[:, 2] = 30_000.0
    tr = traces.Traces(SR, 8)
    _feed(tr, x, ts, 50)
    assert all(b["min"][2] == pytest.approx(0, abs=1e-6) and b["max"][2] == pytest.approx(0, abs=1e-6)
               for b in tr.take_bins())


def test_now_rms_is_the_last_second_of_the_filtered_trace():
    n = int(6 * SR)
    t = np.arange(n) / SR
    x = np.tile(30_000.0 + 20.0 * np.sin(2 * np.pi * 10 * t)[:, None], (1, 8))
    tr = traces.Traces(SR, 8)
    assert tr.now_rms() == [None] * 8  # no data yet
    _feed(tr, x, T0 + t, 25)
    rms = tr.now_rms()
    assert all(r == pytest.approx(20 / np.sqrt(2), rel=0.05) for r in rms)  # 10 Hz is in the 1–40 Hz pass band


def test_60_hz_is_notched_and_45_hz_is_low_passed():
    n = int(6 * SR)
    t = np.arange(n) / SR
    for f in (60.0, 45.0):
        x = np.tile((30_000.0 + 50.0 * np.sin(2 * np.pi * f * t))[:, None], (1, 8))
        tr = traces.Traces(SR, 8)
        _feed(tr, x, T0 + t, 25)
        assert max(tr.now_rms()) < 50 / np.sqrt(2) * 0.5, f

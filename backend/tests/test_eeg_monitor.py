"""
M1b (tasks/plan.md; D-F6-254, D-F6-265): the live monitor's per-channel figures, exactly as the EEG chat's validation
table (F4 Registro, 19 Nov 12:45, point 2). A pure function over live.py's buffer; it never touches the epoch cut.
"""

import numpy as np
import pytest

from app.config import Settings
from app.eeg import monitor

SR = 250.0
LABELS = ["Fp1", "F3", "Fz", "F4", "Cz", "P3", "Pz", "P4"]
T0 = 1000.0


@pytest.fixture(autouse=True)
def _clean_test_participants():
    """Overrides the conftest fixture: no database here."""
    yield


def _raw(seconds=20.0, seed=0):
    """8 channels of 5 µV noise on a 30 mV offset with a slow drift, as AURA's raw signal."""
    n = int(seconds * SR)
    ts = T0 + np.arange(n) / SR
    x = np.random.default_rng(seed).normal(0, 5, (n, 8)) + 30_000 + 200 * np.sin(2 * np.pi * 0.05 * (ts - T0))[:, None]
    return x, ts


@pytest.mark.parametrize("amp,lo,hi", [(10, 9.5, 9.9), (100, 99.3, 99.8), (1000, 999.3, 999.7)])
@pytest.mark.parametrize("hz", [59.5, 60.0, 60.2])
def test_60_hz_amplitude_of_a_sine_as_the_eeg_chat_checked(amp, lo, hi, hz) -> None:
    x, ts = _raw()
    x[:, 2] += amp * np.sin(2 * np.pi * hz * (ts - T0))
    q = monitor.compute(x, ts, SR, LABELS, [], now=ts[-1])
    a = next(c for c in q["channels"] if c["label"] == "Fz")["l60_uv"]
    assert lo - 0.6 <= a <= hi + 0.6   # the chat's ranges, with the 5 µV noise floor added in quadrature


def test_the_filtered_figures_use_the_5_s_ending_2_s_before_now() -> None:   # D-F6-254 (1)
    x, ts = _raw()
    q = monitor.compute(x, ts, SR, LABELS, [], now=ts[-1])
    assert q["window_lsl"] == [pytest.approx(ts[-1] - 7), pytest.approx(ts[-1] - 2)]


def test_rms_share_and_status() -> None:
    x, ts = _raw()
    on = (ts > ts[-1] - 7) & (ts < ts[-1] - 2)
    x[on, 1] += 300 * np.sin(2 * np.pi * 10 * ts[on])          # F3 over 100 µV most of the window: Bad
    x[on, 3] += np.where(np.arange(on.sum()) % 50 < 4, 200 * np.sin(2 * np.pi * 10 * ts[on]), 0)   # F4 a little: OK/Watch
    q = {c["label"]: c for c in monitor.compute(x, ts, SR, LABELS, [], now=ts[-1])["channels"]}
    assert q["F3"]["status"] == "Bad" and q["F3"]["over_pct"] > 20 and q["F3"]["rms_uv"] > 100
    assert q["Pz"]["status"] == "OK" and q["Pz"]["over_pct"] == 0 and 2 < q["Pz"]["rms_uv"] < 4   # 5 µV white noise, 1–40 Hz of 0–125 Hz


def test_a_flat_chunk_is_bad() -> None:
    x, ts = _raw()
    x[:, 6] = 30_000.0   # Pz disconnected: constant over the whole buffer (a short flat stretch rings through the filter)
    pz = next(c for c in monitor.compute(x, ts, SR, LABELS, [], now=ts[-1])["channels"] if c["label"] == "Pz")
    assert pz["flat"] and pz["status"] == "Bad"


def test_missing_samples_read_no_data() -> None:
    x, ts = _raw()
    keep = ~((ts > ts[-1] - 6) & (ts < ts[-1] - 4))   # 2 s gap in the window
    q = monitor.compute(x[keep], ts[keep], SR, LABELS, [], now=ts[-1])
    assert all(c["status"] == "No data" for c in q["channels"])


def test_a_window_inside_the_taps_keeps_the_previous_colour_with_sync_tap() -> None:   # D-F6-254 (2)
    x, ts = _raw()
    prev = monitor.compute(x, ts, SR, LABELS, [], now=ts[-1])
    taps = [(t, {"event": "SYNC_TAP", "phase": "S3"}) for t in np.arange(ts[-1] - 7, ts[-1] - 1.9, 1.0)]
    q = monitor.compute(x, ts, SR, LABELS, taps, now=ts[-1], previous=prev)
    cz = next(c for c in q["channels"] if c["label"] == "Cz")
    assert cz["sync_tap"] and cz["status"] == next(c for c in prev["channels"] if c["label"] == "Cz")["status"]


def test_session_60_hz_and_the_per_channel_mark() -> None:
    x, ts = _raw()
    x[:, :] += 900 * np.sin(2 * np.pi * 60 * (ts - T0))[:, None]   # every channel: session Watch (>= 800 µV)
    x[:, 0] -= 850 * np.sin(2 * np.pi * 60 * (ts - T0))             # Fp1 at 50 µV: under 0.3 x the others
    q = monitor.compute(x, ts, SR, LABELS, [], now=ts[-1])
    assert q["session_60_status"] == "Watch" and q["session_60_uv"] > 800
    marks = {c["label"]: c["mark_60"] for c in q["channels"]}
    assert marks["Fp1"] and not marks["F3"]


def test_the_switch_is_off_by_default(monkeypatch) -> None:
    monkeypatch.delenv("EEG_MONITOR_LIVE", raising=False)
    assert Settings(_env_file=None).eeg_monitor_live is False

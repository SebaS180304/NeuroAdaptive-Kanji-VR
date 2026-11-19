"""
CH1a (tasks/plan.md, Thu 19): epochs.persistently_bad, the persistently bad channel of D-F6-216 with D-F6-224:
> 20 % of a channel's samples over 100 µV in 2 consecutive 30 s bins, bins from the grid origin, ±1 s around each
SYNC_TAP left out of the count, Fp1 never (D-F6-75).
"""

import numpy as np

from app.eeg import epochs

SR = 250.0
LABELS = ["Fp1", "F3", "Fz", "F4", "Cz", "P3", "Pz", "P4"]
T0 = 100.0


def _eeg(seconds: float = 120.0) -> tuple[np.ndarray, np.ndarray]:
    n = int(seconds * SR)
    return np.random.default_rng(0).normal(0, 5, (n, 8)), T0 + np.arange(n) / SR


def _spoil(x, ts, ch, start, seconds, share=0.25):
    """share of the samples of [start, start + seconds) (relative to T0) over 100 µV on channel ch."""
    idx = np.flatnonzero((ts >= T0 + start) & (ts < T0 + start + seconds))
    x[idx[np.arange(len(idx)) % 100 < share * 100], ch] = 300.0   # spread evenly through the span


def _tap(t):
    return (T0 + t, {"event": "SYNC_TAP", "phase": "S3"})


def test_two_consecutive_bins_put_the_channel_out_from_the_end_of_the_second() -> None:
    x, ts = _eeg()
    _spoil(x, ts, 1, 30, 60)   # F3 in bins 1 and 2
    assert epochs.persistently_bad(x, ts, LABELS, [], T0) == [("F3", T0 + 90)]


def test_one_bin_or_two_apart_is_not_persistent() -> None:
    x, ts = _eeg()
    _spoil(x, ts, 1, 0, 30)
    _spoil(x, ts, 1, 60, 30)   # bins 0 and 2, with bin 1 clean between
    assert epochs.persistently_bad(x, ts, LABELS, [], T0) == []


def test_twenty_percent_is_not_over_twenty() -> None:
    x, ts = _eeg()
    _spoil(x, ts, 2, 0, 60, share=0.18)
    assert epochs.persistently_bad(x, ts, LABELS, [], T0) == []


def test_taps_on_cz_are_left_out() -> None:  # D-F6-224 (1): the S3 taps never exclude Cz
    x, ts = _eeg()
    taps = [_tap(s) for s in range(0, 60, 4)]
    for t, _ in taps:   # 1 s of 8 000 µV after each tap: 25 % of each bin, all inside ±1 s
        x[(ts >= t) & (ts < t + 1.0), 4] = 8000.0
    assert (np.abs(x[(ts >= T0) & (ts < T0 + 30), 4]) > 100).mean() > 0.2
    assert epochs.persistently_bad(x, ts, LABELS, taps, T0) == []
    assert epochs.persistently_bad(x, ts, LABELS, [], T0) == [("Cz", T0 + 60)]


def test_bins_start_at_the_grid_origin_not_at_the_first_stamp() -> None:  # D-F6-224 (2)
    x, ts = _eeg()
    _spoil(x, ts, 1, 15, 60, share=0.3)   # 15–75 s: bins of [0,30) [30,60) [60,90) see 15 %, 30 %, 15 %
    assert epochs.persistently_bad(x, ts, LABELS, [], T0) == []
    assert epochs.persistently_bad(x, ts, LABELS, [], T0 + 15) == [("F3", T0 + 15 + 60)]


def test_a_bin_still_open_does_not_count() -> None:  # live: bins close as time passes
    x, ts = _eeg(59.0)
    _spoil(x, ts, 1, 0, 59)
    assert epochs.persistently_bad(x, ts, LABELS, [], T0) == []


def test_two_channels_are_both_returned_in_order_and_fp1_never() -> None:
    x, ts = _eeg()
    _spoil(x, ts, 0, 0, 120)   # Fp1: its own rule (D-F6-75)
    _spoil(x, ts, 6, 30, 60)   # Pz out at 90
    _spoil(x, ts, 2, 0, 60)    # Fz out at 60
    assert epochs.persistently_bad(x, ts, LABELS, [], T0) == [("Fz", T0 + 60), ("Pz", T0 + 90)]


# ---------- CH1b1: what the excluded channel changes in the epochs and the window ----------

from app.eeg import window  # noqa: E402

MONTAGE = {f"CH{i + 1}": label for i, label in enumerate(LABELS)}
CLOCK = [(T0, {"schema_version": 1, "event": "STATE_ENTERED", "state": "S7_EXPERIMENTAL_RETRIEVAL",
               "session_elapsed_ms": 0})]


def _noisy(ch, seconds=120.0):
    x, ts = _eeg(seconds)
    _spoil(x, ts, ch, 0, seconds)
    return x, ts


def test_without_bad_the_epochs_are_as_before() -> None:
    x, ts = _noisy(1)
    assert epochs.make_epochs(x, ts, SR, MONTAGE, CLOCK, t0=T0) == epochs.make_epochs(x, ts, SR, MONTAGE, CLOCK, t0=T0, bad=None)
    assert "excluded_channels" not in epochs.make_epochs(x, ts, SR, MONTAGE, CLOCK, t0=T0)[0]


def test_the_channel_leaves_the_amplitude_check_and_the_indices_from_its_time() -> None:
    x, ts = _noisy(1)   # F3 over 100 µV a quarter of the time: every chunk dropped while it counts
    eps = epochs.make_epochs(x, ts, SR, MONTAGE, CLOCK, t0=T0, bad=[("F3", T0 + 60)])
    before = [e for e in eps if e["lsl_start"] < T0 + 60]
    after = [e for e in eps if e["lsl_start"] >= T0 + 60]
    assert before and all(e["quality"] == "POOR" and e["excluded_channels"] is None for e in before)
    assert after and all(e["quality"] == "GOOD" and e["excluded_channels"] == "F3" for e in after)
    assert all(e["engagement_index"] is not None and e["theta_fz"] is not None for e in after)


def test_fz_out_leaves_theta_unavailable_and_the_ei_with_six() -> None:
    x, ts = _noisy(2)
    eps = [e for e in epochs.make_epochs(x, ts, SR, MONTAGE, CLOCK, t0=T0, bad=[("Fz", T0)])]
    assert all(e["theta_fz"] is None and e["engagement_index"] is not None for e in eps)


def test_a_second_channel_stops_the_eeg_counting_in_the_window() -> None:
    x, ts = _eeg()
    eps = epochs.make_epochs(x, ts, SR, MONTAGE, CLOCK, t0=T0, bad=[("F3", T0 + 30), ("Pz", T0 + 60)])
    assert {e["excluded_channels"] for e in eps if e["lsl_start"] >= T0 + 60} == {"F3,Pz"}
    ref = {"indices": {"engagement_index": {"mean": 0.0, "sd": 1.0}}}
    early = window.evaluate(eps, 20_000, 50_000, ref)
    late = window.evaluate(eps, 80_000, 110_000, ref)
    assert early["counted"] and "fallback" not in early
    assert not late["counted"] and late["fallback"] == "BAD_CHANNELS"

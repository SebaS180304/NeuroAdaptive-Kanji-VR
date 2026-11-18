import numpy as np

from app.eeg import baseline
from app.eeg.s3watch import S3Watch

SR = 250.0


def _signal(seconds, bad=None):
    rng = np.random.default_rng(1)
    x = rng.normal(0, 5, (int(seconds * SR), 8))
    ts = np.arange(len(x)) / SR + 1000.0
    if bad is not None:
        x[:, bad] = rng.normal(0, 300, len(x))
    return x, ts


def _entered(t, state):
    return (t, {"event": "STATE_ENTERED", "state": state})


def _tap(t, i, phase="S3"):
    return (t, {"event": "SYNC_TAP", "phase": phase, "index": i})


def test_a_clear_tap_and_a_missed_one_are_said_with_the_count() -> None:
    x, ts = _signal(20)
    cz = 4
    x[int(10.05 * SR):int(10.15 * SR), cz] += 400   # the strike just after the marker
    markers = [_entered(ts[0], "S3_SYSTEM_VALIDATION"), _tap(ts[0] + 10, 1), _tap(ts[0] + 15, 2)]
    lines = S3Watch(baseline.DEFAULT_MONTAGE).lines(list(x), list(ts), markers, SR)
    assert lines[0].startswith("tap 1/5: clear") and "1 clear so far" in lines[0]
    assert lines[1].startswith("tap 2/5: NOT clear") and "D-F6-197" in lines[1]


def test_each_tap_is_said_once_and_a_tap_after_s3_warns() -> None:
    x, ts = _signal(20)
    w = S3Watch(baseline.DEFAULT_MONTAGE)
    markers = [_tap(ts[0] + 10, 1, phase="S9")]
    assert "outside S3" in w.lines(list(x), list(ts), markers, SR)[0]
    assert w.lines(list(x), list(ts), markers, SR) == []


def test_a_bad_channel_in_s2_is_named_and_fp1_gets_its_own_line() -> None:
    x, ts = _signal(40, bad=1)   # F3
    lines = S3Watch(baseline.DEFAULT_MONTAGE).lines(list(x), list(ts), [_entered(ts[0], "S2_VR_TUTORIAL")], SR)
    assert len(lines) == 1 and lines[0].startswith("WARNING: F3 looks bad") and "D-F6-213" in lines[0]
    x, ts = _signal(40, bad=0)   # Fp1
    lines = S3Watch(baseline.DEFAULT_MONTAGE).lines(list(x), list(ts), [_entered(ts[0], "S2_VR_TUTORIAL")], SR)
    assert "re-seat Fp1" in lines[0]


def test_s4_closes_with_the_tally_and_then_silence() -> None:
    x, ts = _signal(40, bad=1)
    w = S3Watch(baseline.DEFAULT_MONTAGE)
    markers = [_entered(ts[0], "S2_VR_TUTORIAL"), _entered(ts[-1], "S4_EEG_BASELINE")]
    lines = w.lines(list(x), list(ts), markers, SR)
    assert lines[0].startswith("S3 taps: 0/5 clear") and "D-F6-176" in lines[0]
    assert w.lines(list(x), list(ts), markers, SR) == []

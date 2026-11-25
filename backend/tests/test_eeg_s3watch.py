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


def test_the_taps_on_cz_do_not_make_cz_bad() -> None:  # T02, 18 Nov: 5 taps of 5 000-11 000 uV flagged Cz
    x, ts = _signal(40)
    taps = []
    for i, s in enumerate((8, 14, 20, 26, 32), start=1):
        x[int(s * SR):int((s + 0.9) * SR), 4] += 8000   # the controller rests on Cz's housing
        taps.append(_tap(ts[0] + s, i))
    markers = [_entered(ts[0], "S2_VR_TUTORIAL")] + taps
    lines = S3Watch(baseline.DEFAULT_MONTAGE).lines(list(x), list(ts), markers, SR)
    assert not any("Cz looks bad" in line for line in lines)


def _away(t, episode=1, state="S3_SYSTEM_VALIDATION", onset_ms=0):
    return (t, {"event": "HEAD_AWAY", "episode": episode, "state": state, "onset_offset_ms": onset_ms})


def _returned(t, episode=1):
    return (t, {"event": "HEAD_RETURNED", "episode": episode})


def _away_lines(markers, seconds=20):
    x, ts = _signal(seconds)
    w = S3Watch(baseline.DEFAULT_MONTAGE)
    first = w.lines(list(x), list(ts), [(ts[0], m) if t is None else (ts[0] + t, m) for t, m in markers], SR)
    again = w.lines(list(x), list(ts), [(ts[0], m) if t is None else (ts[0] + t, m) for t, m in markers], SR)
    return [l for l in first + again if "HEAD_AWAY" in l]


S3_IN = (None, {"event": "STATE_ENTERED", "state": "S3_SYSTEM_VALIDATION"})


def test_head_away_open_over_10_s_in_s3_warns_once() -> None:  # D-F6-249 (2); T02: visor tilted from S2 to S9
    lines = _away_lines([S3_IN, _away(8.0)])   # open 12 s at the newest stamp
    assert len(lines) == 1
    assert lines[0] == "WARNING: HEAD_AWAY open since S3_SYSTEM_VALIDATION - re-seat the headset before S4 (D-F6-249)"


def test_head_away_under_10_s_or_returned_says_nothing() -> None:
    assert _away_lines([S3_IN, _away(11.0)]) == []                       # open 9 s
    assert _away_lines([S3_IN, _away(2.0), _returned(9.0)]) == []         # back after 7 s


def test_head_away_onset_offset_counts_and_an_s2_episode_still_open_in_s3_warns() -> None:
    assert len(_away_lines([S3_IN, _away(11.0, onset_ms=-2000)])) == 1   # started 2 s before its marker: 11 s
    lines = _away_lines([(None, {"event": "STATE_ENTERED", "state": "S2_VR_TUTORIAL"}),
                         _away(1.0, state="S2_VR_TUTORIAL"), (5.0, S3_IN[1])])
    assert len(lines) == 1 and "since S2_VR_TUTORIAL" in lines[0]


def test_head_away_is_not_watched_before_s3_or_after_s4() -> None:
    s2 = (None, {"event": "STATE_ENTERED", "state": "S2_VR_TUTORIAL"})
    assert _away_lines([s2, _away(1.0, state="S2_VR_TUTORIAL")]) == []   # still S2: nothing yet
    s4 = (5.0, {"event": "STATE_ENTERED", "state": "S4_EEG_BASELINE"})
    assert _away_lines([S3_IN, s4, _away(6.0, state="S4_EEG_BASELINE")]) == []

from app.eeg import autorun


def test_the_xdf_is_closed_only_after_it_stops_growing() -> None:
    # (seconds, bytes): LabRecorder still writing during block 3, then Stop at t=40.
    growing = [(0, 100), (10, 200), (20, 300), (30, 400), (40, 500)]
    assert not autorun.settled(growing, quiet_s=15)
    stopped = growing + [(50, 500), (54, 500)]
    assert not autorun.settled(stopped, quiet_s=15)   # quiet for 14 s only
    assert autorun.settled(stopped + [(56, 500)], quiet_s=15)


def test_a_missing_or_empty_xdf_is_never_closed() -> None:
    assert not autorun.settled([], quiet_s=15)
    assert not autorun.settled([(0, 0), (30, 0)], quiet_s=15)

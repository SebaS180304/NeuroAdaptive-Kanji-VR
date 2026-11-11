"""
X3 (D-F6-171, D-F6-174; Reevaluación §5.5): the EEG fails, the session goes on with behaviour and is marked.
Pure part: heartbeat + gap -> status, the EEG_STATUS changes, and the > 60 s rule.
"""

import pytest

from app.eeg import status


@pytest.fixture(autouse=True)
def _clean_test_participants():
    """Overrides the conftest fixture: no database here."""
    yield


def test_fresh_heartbeat_and_samples_flowing_is_connected() -> None:
    assert status.classify(heartbeat_age_s=1.0, gap_ms=300) == status.CONNECTED


def test_fresh_heartbeat_without_samples_is_lost_not_process_down() -> None:   # cap off, Bluetooth, AURA closed
    assert status.classify(heartbeat_age_s=1.0, gap_ms=5_000) == status.LOST


def test_stale_or_missing_heartbeat_is_process_down() -> None:                  # live.py killed
    assert status.classify(heartbeat_age_s=12.0, gap_ms=300) == status.PROCESS_DOWN
    assert status.classify(heartbeat_age_s=None, gap_ms=None) == status.PROCESS_DOWN


def test_changes_are_reported_once_and_a_return_is_recovered() -> None:
    t = status.Tracker()
    seen = [t.observe(s, gap_ms=g, heartbeat_age_s=1.0) for s, g in
            [(status.CONNECTED, 300), (status.CONNECTED, 300), (status.LOST, 4_000), (status.LOST, 9_000),
             (status.CONNECTED, 200)]]
    assert seen == [status.CONNECTED, None, status.LOST, None, status.RECOVERED]
    assert t.cancelled is None


def test_more_than_60_s_without_eeg_cancels_the_eeg_for_the_session() -> None:
    t = status.Tracker()
    t.observe(status.LOST, gap_ms=61_000, heartbeat_age_s=1.0)
    assert t.cancelled == status.LOST_OVER_60S
    t.observe(status.CONNECTED, gap_ms=200, heartbeat_age_s=1.0)
    assert t.cancelled == status.LOST_OVER_60S                                   # it does not come back


def test_a_dead_process_for_more_than_60_s_cancels_too() -> None:
    t = status.Tracker()
    t.observe(status.PROCESS_DOWN, gap_ms=300, heartbeat_age_s=70.0)
    assert t.cancelled == status.LOST_OVER_60S

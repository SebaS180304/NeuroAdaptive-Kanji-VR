"""
F2c (tasks/plan.md, Fri 6): app/eeg/sync.py. Offset and drift of the sync test (F4 §2.4, D-F6-150)
into eeg_sessions (D-F6-157), with the clear-peak rule and the detail column of D-F6-159 (0012).
"""

import numpy as np
import pytest
from sqlalchemy import text

from app.db.base import AsyncSessionLocal
from app.eeg import sync

SR = 250.0


def _cz(spikes: list[float], seconds: float = 60.0, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """~5 µV noise on Cz with a 300 µV spike at each LSL time in `spikes`; stamps from 100 s on."""
    n = int(seconds * SR)
    ts = 100.0 + np.arange(n) / SR
    x = np.random.default_rng(seed).normal(0, 5, n)
    for t in spikes:
        x[int(round((t - 100.0) * SR))] += 300.0
    return x, ts


def _taps(phase: str, times: list[float]) -> list[tuple[float, dict]]:
    return [(t, {"event": "SYNC_TAP", "phase": phase, "index": i + 1}) for i, t in enumerate(times)]


S3 = [105.0, 108.0, 111.0, 114.0, 117.0]
S9 = [140.0, 143.0, 146.0, 149.0, 152.0]


def test_offset_is_the_median_s3_lag_and_drift_the_s9_median_minus_it() -> None:
    lags3, lags9 = [0.040, 0.044, 0.048, 0.052, 0.200], [0.060, 0.064, 0.068, 0.072, 0.076]
    x, ts = _cz([t + d for t, d in zip(S3, lags3)] + [t + d for t, d in zip(S9, lags9)])
    offset, drift, detail = sync.compute(x, ts, _taps("S3", S3) + _taps("S9", S9))
    assert offset == pytest.approx(48.0, abs=4.1)        # the 200 ms outlier does not move the median
    assert drift == pytest.approx(68.0 - 48.0, abs=8.1)
    assert detail["reason"] is None and len(detail["taps"]) == 10 and all(t["valid"] for t in detail["taps"])
    assert detail["window_ms"] == 500 and detail["k_mad"] == 5.0 and detail["pre_s"] == 2.0  # the rule travels


def test_a_negative_lag_is_kept_with_its_sign() -> None:
    x, ts = _cz([t - 0.030 for t in S3])
    offset, drift, _ = sync.compute(x, ts, _taps("S3", S3))
    assert offset == pytest.approx(-30.0, abs=4.1) and drift is None


def test_a_spike_outside_500_ms_is_not_a_peak() -> None:
    x, ts = _cz([t + 0.7 for t in S3])
    _, _, detail = sync.compute(x, ts, _taps("S3", S3))
    assert not any(t["valid"] for t in detail["taps"])


def test_two_valid_taps_leave_the_columns_empty_with_the_reason() -> None:
    x, ts = _cz([S3[0] + 0.05, S3[1] + 0.05] + [t + 0.05 for t in S9])
    offset, drift, detail = sync.compute(x, ts, _taps("S3", S3) + _taps("S9", S9))
    assert offset is None and drift is None
    assert sum(t["valid"] for t in detail["taps"] if t["phase"] == "S3") == 2
    assert "S3" in detail["reason"] and "2 of 5" in detail["reason"]


def test_s9_short_keeps_the_offset_but_not_the_drift() -> None:
    x, ts = _cz([t + 0.05 for t in S3])
    offset, drift, detail = sync.compute(x, ts, _taps("S3", S3) + _taps("S9", S9))
    assert offset == pytest.approx(50.0, abs=4.1) and drift is None
    assert "S9" in detail["reason"]


def test_no_sync_taps_at_all() -> None:
    x, ts = _cz([])
    offset, drift, detail = sync.compute(x, ts, [(101.0, {"event": "STATE_ENTERED"})])
    assert (offset, drift) == (None, None) and detail["taps"] == [] and "no SYNC_TAP" in detail["reason"]


@pytest.mark.asyncio
async def test_save_writes_the_three_columns(client, pretested) -> None:
    pid = await pretested("TEST_EEG")
    sid = (await client.post("/sessions", json={"participant_id": pid, "condition": "STATIC"})).json()["id"]
    async with AsyncSessionLocal() as db:
        await db.execute(text("INSERT INTO eeg_sessions (session_id, xdf_path) VALUES (:s, 'x.xdf')"), {"s": sid})
        await sync.save(db, sid, 48.0, None, {"reason": "S9: 0 of 5 taps with a clear peak (< 3)", "taps": []})
        await db.commit()
        row = (await db.execute(text("SELECT sync_offset_ms, sync_drift_ms, sync_detail FROM eeg_sessions "
                                     "WHERE session_id = :s"), {"s": sid})).one()
    assert row.sync_offset_ms == 48.0 and row.sync_drift_ms is None and row.sync_detail["reason"].startswith("S9")

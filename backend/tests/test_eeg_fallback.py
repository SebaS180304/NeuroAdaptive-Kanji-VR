"""
X3 with the database: at an S7 answer of MULTIMODAL_ADAPTIVE, _eeg_source reads the heartbeat, the EEG gap and S4,
writes EEG_STATUS when the status changes, and gives a window that does not count, marked with its fallback reason,
whenever the EEG is down or cancelled for the session (D-F6-171, §5.5). The decision is then behavioural.
"""

import json
import math

import pytest
from sqlalchemy import text

from app.api.routes import websocket as ws
from app.db.base import AsyncSessionLocal
from app.eeg import concordance

REF = {"source": "S6", "indices": {k: {"mean": 0.0, "sd": 1.0} for k in
                                   ("engagement_index", "theta_fz", "alpha_parietal", "theta_beta")}}


async def _session(client, pretested, heartbeat_age_s, gap_ms, alpha_passed=True) -> str:
    pid = await pretested("TEST_EEG")
    sid = (await client.post("/sessions", json={"random_seed": "test-seed", "participant_id": pid,
                                                "condition": "MULTIMODAL_ADAPTIVE", "assigned_kanji_set": "A"})).json()["id"]
    async with AsyncSessionLocal() as db:
        await db.execute(text(
            "INSERT INTO eeg_sessions (session_id, xdf_path, reference, alpha_passed, heartbeat_at, eeg_gap_ms) "
            "VALUES (:s, 'x.xdf', CAST(:r AS jsonb), :a, "
            "CASE WHEN CAST(:h AS float) IS NULL THEN NULL ELSE now() - make_interval(secs => CAST(:h AS float)) END, :g) "
            "ON CONFLICT (session_id) DO UPDATE SET reference = EXCLUDED.reference, alpha_passed = EXCLUDED.alpha_passed, "
            "heartbeat_at = EXCLUDED.heartbeat_at, eeg_gap_ms = EXCLUDED.eeg_gap_ms, not_counted_reason = NULL"),
            {"s": sid, "r": json.dumps(REF), "a": alpha_passed, "h": heartbeat_age_s, "g": gap_ms})
        for i, start in enumerate((90_000, 92_500)):
            await db.execute(text(
                "INSERT INTO eeg_epochs (session_id, epoch_index, lsl_start, start_ms, end_ms, chunk_clean, "
                "clean_fraction, quality, engagement_index, theta_fz, alpha_parietal, theta_beta) VALUES "
                "(:s, :i, :l, :a, :b, :c, 1.0, 'GOOD', :e, 1.0, 1.0, 1.0)"),
                {"s": sid, "i": i, "l": start / 1000, "a": start, "b": start + 5000, "c": [True] * 9, "e": math.exp(-2)})
        await db.commit()
    ws._eeg_trackers.clear()
    return sid


async def _window(sid: str, answered_ms: int = 100_000) -> dict:
    return (await ws._eeg_source(sid, answered_ms))("S7-006", 95_000, answered_ms)


async def _statuses(sid: str) -> list[str]:
    async with AsyncSessionLocal() as db:
        return list((await db.execute(text("SELECT payload->>'status' FROM session_events WHERE session_id = :s "
                                           "AND event_type = 'EEG_STATUS' ORDER BY id"), {"s": sid})).scalars())


async def _reason(sid: str):
    async with AsyncSessionLocal() as db:
        return (await db.execute(text("SELECT not_counted_reason FROM eeg_sessions WHERE session_id = :s"),
                                 {"s": sid})).scalar_one()


@pytest.mark.asyncio
async def test_connected_the_window_counts_and_has_no_fallback(client, pretested) -> None:
    sid = await _session(client, pretested, heartbeat_age_s=1.0, gap_ms=300)
    w = await _window(sid)
    assert w["counted"] is True and concordance.block(w)["fallback"] is None
    assert await _statuses(sid) == ["CONNECTED"]


@pytest.mark.asyncio
async def test_stream_stopped_the_window_falls_back_as_lost(client, pretested) -> None:
    sid = await _session(client, pretested, heartbeat_age_s=1.0, gap_ms=8_000)
    w = await _window(sid)
    assert w["counted"] is False and concordance.block(w)["fallback"] == "LOST"
    assert await _statuses(sid) == ["LOST"]


@pytest.mark.asyncio
async def test_live_py_killed_the_window_falls_back_as_process_down(client, pretested) -> None:
    sid = await _session(client, pretested, heartbeat_age_s=15.0, gap_ms=300)
    assert concordance.block(await _window(sid))["fallback"] == "PROCESS_DOWN"
    assert await _statuses(sid) == ["PROCESS_DOWN"]


@pytest.mark.asyncio
async def test_over_60_s_lost_cancels_the_eeg_for_the_rest_of_the_session(client, pretested) -> None:
    sid = await _session(client, pretested, heartbeat_age_s=1.0, gap_ms=61_000)
    assert concordance.block(await _window(sid))["fallback"] == "LOST_OVER_60S"
    assert await _reason(sid) == "LOST_OVER_60S"
    async with AsyncSessionLocal() as db:                                       # the cap comes back
        await db.execute(text("UPDATE eeg_sessions SET eeg_gap_ms = 200 WHERE session_id = :s"), {"s": sid})
        await db.commit()
    ws._eeg_trackers.clear()                                                    # even after a reconnect
    assert concordance.block(await _window(sid, 110_000))["fallback"] == "LOST_OVER_60S"


@pytest.mark.asyncio
async def test_s4_alpha_failed_cancels_the_eeg_for_the_session(client, pretested) -> None:
    sid = await _session(client, pretested, heartbeat_age_s=1.0, gap_ms=300, alpha_passed=False)
    assert concordance.block(await _window(sid))["fallback"] == "S4_ALPHA_FAILED"
    assert await _reason(sid) == "S4_ALPHA_FAILED"


def test_a_window_that_simply_does_not_count_is_marked_not_counted() -> None:
    assert concordance.block({"counted": False, "non_poor": 1, "clean_s": 2.0, "z": {}})["fallback"] == "NOT_COUNTED"

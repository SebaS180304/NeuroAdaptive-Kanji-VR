"""
X1 (tasks/todo.md): the backend reads the live epochs at an S7 answer of MULTIMODAL_ADAPTIVE (D-F6-171) and gives
window.py the window that ends at the answer (D-F6-172, D-F6-177). Needs the database, like test_eeg_reference.
"""

import json
import math

import pytest
from sqlalchemy import text

from app.api.routes.websocket import _eeg_source
from app.db.base import AsyncSessionLocal

REF = {"source": "S6", "indices": {"engagement_index": {"mean": 0.0, "sd": 1.0}, "theta_fz": {"mean": 0.0, "sd": 1.0},
                                   "alpha_parietal": {"mean": 0.0, "sd": 1.0}, "theta_beta": {"mean": 0.0, "sd": 1.0}}}


async def _session_with_epochs(client, pretested, starts):
    pid = await pretested("TEST_EEG")
    sid = (await client.post("/sessions", json={"random_seed": "test-seed", "participant_id": pid,
                                                "condition": "MULTIMODAL_ADAPTIVE"})).json()["id"]
    async with AsyncSessionLocal() as db:
        await db.execute(text("INSERT INTO eeg_sessions (session_id, xdf_path, reference) VALUES (:s, 'x.xdf', "
                              "CAST(:r AS jsonb)) ON CONFLICT (session_id) DO UPDATE SET reference = CAST(:r AS jsonb)"),
                         {"s": sid, "r": json.dumps(REF)})
        for i, start in enumerate(starts):
            await db.execute(text(
                "INSERT INTO eeg_epochs (session_id, epoch_index, lsl_start, start_ms, end_ms, chunk_clean, "
                "clean_fraction, quality, engagement_index, theta_fz, alpha_parietal, theta_beta) VALUES "
                "(:s, :i, :l, :a, :b, :c, 1.0, 'GOOD', :ei, 1.0, 1.0, 1.0)"),
                {"s": sid, "i": i, "l": start / 1000, "a": start, "b": start + 5000, "c": [True] * 9,
                 "ei": math.exp(-2.0)})
        await db.commit()
    return sid


@pytest.mark.asyncio
async def test_the_window_of_the_answer_counts_with_the_epochs_finished_at_it(client, pretested) -> None:
    sid = await _session_with_epochs(client, pretested, [90_000, 92_500, 97_500])   # the last ends after the answer
    source = await _eeg_source(sid, 100_000)
    w = source("S7-006", 95_000, 100_000)
    assert w["counted"] is True and w["non_poor"] == 2 and w["z"]["engagement_index"] == pytest.approx(-2.0)


@pytest.mark.asyncio
async def test_no_epochs_yet_is_a_window_that_does_not_count(client, pretested) -> None:
    sid = await _session_with_epochs(client, pretested, [])
    assert (await _eeg_source(sid, 100_000))("S7-006", 95_000, 100_000)["counted"] is False


@pytest.mark.asyncio
async def test_without_the_answer_time_there_is_no_source() -> None:
    assert await _eeg_source("00000000-0000-0000-0000-000000000000", None) is None


@pytest.mark.asyncio
async def test_a_window_of_75_s_reads_every_epoch_in_it(client, pretested) -> None:  # D-F6-186 (2), D-F6-172
    # three slow trials from 25 s to 100 s: the window starts at the 1st trial, 75 s before the answer
    starts = list(range(25_000, 95_001, 2_500))                     # epochs that end by the answer (100 s)
    sid = await _session_with_epochs(client, pretested, starts)
    w = (await _eeg_source(sid, 100_000))("S7-006", 25_000, 100_000)
    from app.eeg import window
    epochs = [{"start_ms": s, "end_ms": s + 5000, "quality": "GOOD", "chunk_clean": [True] * 9,
               "engagement_index": math.exp(-2.0), "theta_fz": 1.0, "alpha_parietal": 1.0, "theta_beta": 1.0}
              for s in starts]
    assert w["non_poor"] == window.evaluate(epochs, 25_000, 100_000, REF)["non_poor"] == 29

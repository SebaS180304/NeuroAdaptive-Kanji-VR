"""
F4 S2 (tasks/plan.md, L2): one eeg_sessions row per session (migration 0010).
AURA sends no channel labels, so the montage lives here (D-F6-127, P9).
"""

import pytest
from sqlalchemy import text

from app.db.base import AsyncSessionLocal

_MONTAGE = {"CH1": "Fp1", "CH2": "F3", "CH3": "Fz", "CH4": "F4",
            "CH5": "Cz", "CH6": "P3", "CH7": "Pz", "CH8": "P4"}


async def _scalar(query: str, **params):
    async with AsyncSessionLocal() as db:
        return (await db.execute(text(query), params)).scalar_one()


@pytest.mark.asyncio
async def test_a_row_gets_the_fixed_montage_and_goes_with_its_session(client, pretested) -> None:
    pid = await pretested("TEST_EEG")
    sid = (await client.post("/sessions", json={"random_seed": "test-seed", "participant_id": pid, "condition": "STATIC", "assigned_kanji_set": "A"})).json()["id"]
    async with AsyncSessionLocal() as db:
        await db.execute(text("INSERT INTO eeg_sessions (session_id, xdf_path) VALUES (:s, 'x.xdf')"), {"s": sid})
        await db.commit()

    assert await _scalar("SELECT montage FROM eeg_sessions WHERE session_id = :s", s=sid) == _MONTAGE
    assert await _scalar("SELECT stream_info FROM eeg_sessions WHERE session_id = :s", s=sid) == {}

    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM experiment_sessions WHERE id = :s"), {"s": sid})
        await db.commit()
    assert await _scalar("SELECT count(*) FROM eeg_sessions WHERE session_id = :s", s=sid) == 0

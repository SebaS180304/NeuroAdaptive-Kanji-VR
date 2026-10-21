"""
Learner Profile v1 (tasks/plan.md, "Architecture decisions: Learner Profile v1").
One learner_profiles row per participant and format version (migration 0007).
"""

import json

import pytest
from sqlalchemy import text

from app.db.base import AsyncSessionLocal


async def _scalar(query: str, **params):
    async with AsyncSessionLocal() as db:
        return (await db.execute(text(query), params)).scalar_one()


@pytest.mark.asyncio
async def test_a_profile_row_is_one_per_version_and_goes_with_its_participant(pretested) -> None:
    pid = await pretested("TEST_PROFILE")
    async with AsyncSessionLocal() as db:
        await db.execute(text("INSERT INTO learner_profiles (participant_id, profile) "
                              "VALUES (:pid, CAST(:p AS jsonb))"), {"pid": pid, "p": json.dumps({"calibrations": []})})
        await db.commit()

    assert await _scalar("SELECT profile_version FROM learner_profiles WHERE participant_id = :pid", pid=pid) == "v1"
    assert await _scalar("SELECT session_ids FROM learner_profiles WHERE participant_id = :pid", pid=pid) == []

    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM participants WHERE id = :pid"), {"pid": pid})
        await db.commit()
    assert await _scalar("SELECT count(*) FROM learner_profiles WHERE participant_id = :pid", pid=pid) == 0

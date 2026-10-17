"""
Abandoned sessions become ABORTED (tasks/plan.md, Task 0.2): an IN_PROGRESS
session whose last event (or, with no events, its last update) is older than
30 minutes. COMPLETED and CREATED sessions are never touched, and a late state
update does not bring an ABORTED session back.
"""

import pytest
from sqlalchemy import text

from app.db.base import AsyncSessionLocal
from app.services.stale_sessions import abort_stale_sessions


async def _session(client, pid: str, state: str | None) -> str:
    resp = await client.post("/sessions", json={"participant_id": pid, "condition": "STATIC"})
    assert resp.status_code == 201
    sid = resp.json()["id"]
    if state:
        assert (await client.patch(f"/sessions/{sid}/state", json={"new_state": state})).status_code == 200
    return sid


async def _sql(query: str, **params) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(text(query), params)
        await db.commit()


async def _event(sid: str, minutes_ago: int) -> None:
    await _sql("INSERT INTO session_events (session_id, event_type, server_received_at) "
               "VALUES (:sid, 'TEST_EVENT', now() - make_interval(mins => :m))", sid=sid, m=minutes_ago)


async def _status(sid: str) -> str:
    async with AsyncSessionLocal() as db:
        return (await db.execute(text("SELECT status FROM experiment_sessions WHERE id = :sid"),
                                 {"sid": sid})).scalar_one()


@pytest.mark.asyncio
async def test_only_idle_in_progress_sessions_are_aborted(client):
    pid = (await client.post("/participants", json={"external_code": "TEST_STALE", "consent_obtained": True})).json()["id"]

    stale = await _session(client, pid, "S5_STANDARDIZED_LEARNING")
    await _event(stale, 31)

    live = await _session(client, pid, "S5_STANDARDIZED_LEARNING")
    await _event(live, 120)
    await _event(live, 1)                          # the last event is what counts

    quiet = await _session(client, pid, "S1_WELCOME_ORIENTATION")   # no events: falls back to updated_at
    await _sql("UPDATE experiment_sessions SET updated_at = now() - interval '31 minutes' WHERE id = :sid",
               sid=quiet)

    done = await _session(client, pid, "S9_SESSION_SUMMARY")
    await _event(done, 600)
    created = await _session(client, pid, None)
    await _sql("UPDATE experiment_sessions SET updated_at = now() - interval '10 hours' WHERE id = :sid",
               sid=created)

    assert await abort_stale_sessions() >= 2       # other stale dev sessions may be aborted too

    assert await _status(stale) == "ABORTED"
    assert await _status(quiet) == "ABORTED"
    assert await _status(live) == "IN_PROGRESS"
    assert await _status(done) == "COMPLETED"
    assert await _status(created) == "CREATED"

    # A late state from Unity does not revert the abort.
    resp = await client.patch(f"/sessions/{stale}/state", json={"new_state": "S6_GUIDED_PRACTICE_CALIBRATION"})
    assert resp.status_code == 200 and resp.json()["status"] == "ABORTED"


@pytest.mark.asyncio
async def test_running_twice_changes_nothing_the_second_time(client):
    pid = (await client.post("/participants", json={"external_code": "TEST_STALE", "consent_obtained": True})).json()["id"]
    stale = await _session(client, pid, "S5_STANDARDIZED_LEARNING")
    await _event(stale, 45)
    await abort_stale_sessions()
    assert await abort_stale_sessions() == 0

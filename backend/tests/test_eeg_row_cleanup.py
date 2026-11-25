"""
E0 (tasks/plan.md, Thu 19; D-F6-258 (2), D-F6-260 (1)): the eeg_sessions row is still written when the session is
created (autorun, AU2's recording and s3watch hang on it), and the backend deletes it when the session ends
(COMPLETED or ABORTED) without having entered S3. A short visit (S1 → block R → S9) ends with no row; a full session
keeps it; a session aborted in S2 loses it.
"""

import pytest
from sqlalchemy import text

from app.db.base import AsyncSessionLocal
from app.services.stale_sessions import abort_stale_sessions


async def _sql(query: str, **params):
    async with AsyncSessionLocal() as db:
        result = await db.execute(text(query), params)
        await db.commit()
        return result


async def _session_with_row(client, pid: str) -> str:
    resp = await client.post("/sessions", json={"random_seed": "test-seed", "participant_id": pid,
                                                 "condition": "STATIC", "assigned_kanji_set": "A"})
    assert resp.status_code == 201
    sid = resp.json()["id"]
    await _sql("INSERT INTO eeg_sessions (session_id, xdf_path) VALUES (:s, 'C:/x.xdf')", s=sid)  # as POST does with LabRecorder on
    return sid


async def _patch(client, sid: str, state: str) -> None:
    assert (await client.patch(f"/sessions/{sid}/state", json={"new_state": state})).status_code == 200


async def _rows(sid: str) -> int:
    return (await _sql("SELECT count(*) FROM eeg_sessions WHERE session_id = :s", s=sid)).scalar_one()


@pytest.mark.asyncio
async def test_a_short_visit_ends_with_no_row(client, pretested):
    sid = await _session_with_row(client, await pretested("TEST_E0"))
    await _patch(client, sid, "S1_WELCOME_ORIENTATION")
    await _patch(client, sid, "S9_SESSION_SUMMARY")
    assert await _rows(sid) == 0


@pytest.mark.asyncio
async def test_a_full_session_keeps_its_row(client, pretested):
    sid = await _session_with_row(client, await pretested("TEST_E0"))
    await _sql("INSERT INTO session_events (session_id, event_type, payload) VALUES "
               "(:s, 'STATE_ENTERED', CAST('{\"state\": \"S3_SYSTEM_VALIDATION\"}' AS jsonb))", s=sid)
    await _patch(client, sid, "S9_SESSION_SUMMARY")
    assert await _rows(sid) == 1


@pytest.mark.asyncio
async def test_a_session_aborted_in_s2_loses_its_row(client, pretested):
    sid = await _session_with_row(client, await pretested("TEST_E0"))
    await _patch(client, sid, "S2_VR_TUTORIAL")
    await _sql("UPDATE experiment_sessions SET updated_at = now() - interval '31 minutes' WHERE id = :s", s=sid)
    await abort_stale_sessions()
    assert (await _sql("SELECT status FROM experiment_sessions WHERE id = :s", s=sid)).scalar_one() == "ABORTED"
    assert await _rows(sid) == 0

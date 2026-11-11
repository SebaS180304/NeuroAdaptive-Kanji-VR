"""
A3 (D-F6-186 (3)): S9's STATE_ENTERED over the WebSocket closes the session exactly as the PATCH does,
so a lost PATCH cannot leave a finished session without `completed_at` (autorun waits on it).
"""

import asyncio
import uuid

import pytest
from sqlalchemy import text

from app.adaptation import learner_profile
from app.api.routes import websocket as ws
from app.config import get_settings
from app.db.base import AsyncSessionLocal
from app.eeg import labrecorder


class _FakeSocket:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, data: dict) -> None:
        self.sent.append(data)


async def _enter(sid: str, state: str) -> None:
    socket = _FakeSocket()
    await ws._handle_session_event(socket, uuid.UUID(sid), {"type": "SESSION_EVENT", "event_type": "STATE_ENTERED",
                                                             "payload": {"state": state}})
    assert socket.sent[-1]["type"] == "ACK"
    await asyncio.sleep(0.05)  # lets the after-commit tasks run


async def _row(sid: str):
    async with AsyncSessionLocal() as db:
        return (await db.execute(text("SELECT status, current_state, completed_at FROM experiment_sessions "
                                      "WHERE id = :s"), {"s": sid})).one()


@pytest.mark.asyncio
async def test_s9_over_the_websocket_completes_the_session_like_the_patch(client, pretested, monkeypatch) -> None:
    refreshed, sent = [], []

    async def _refresh(ids) -> None:
        refreshed.extend(ids)

    monkeypatch.setattr(learner_profile, "refresh", _refresh)
    monkeypatch.setattr(labrecorder, "send", lambda host, port, cmds, **_: sent.append(cmds))
    pid = await pretested("TEST_WS_CLOSE")
    sid = (await client.post("/sessions", json={"random_seed": "test-seed", "participant_id": pid,
                                                "condition": "STATIC", "assigned_kanji_set": "A"})).json()["id"]

    await _enter(sid, "S5_STANDARDIZED_LEARNING")
    assert (await _row(sid))[0] == "IN_PROGRESS"

    await _enter(sid, "S9_SESSION_SUMMARY")
    status, state, at_s9 = await _row(sid)
    assert (status, state) == ("COMPLETED", "S9_SESSION_SUMMARY") and at_s9 is not None
    assert refreshed == [uuid.UUID(pid)]

    monkeypatch.setattr(get_settings(), "labrecorder_host", "127.0.0.1")
    await _enter(sid, "S10_HCI_SELF_REPORT")
    assert (await _row(sid))[2] == at_s9          # completed_at once
    assert refreshed == [uuid.UUID(pid)]          # profile refreshed once
    assert sent == [["stop"]]


@pytest.mark.asyncio
async def test_late_s9_over_the_websocket_does_not_reopen_an_aborted_session(client, pretested) -> None:
    pid = await pretested("TEST_WS_CLOSE_ABORTED")
    sid = (await client.post("/sessions", json={"random_seed": "test-seed", "participant_id": pid,
                                                "condition": "STATIC", "assigned_kanji_set": "A"})).json()["id"]
    async with AsyncSessionLocal() as db:
        await db.execute(text("UPDATE experiment_sessions SET status = 'ABORTED' WHERE id = :s"), {"s": sid})
        await db.commit()

    await _enter(sid, "S9_SESSION_SUMMARY")
    status, state, completed_at = await _row(sid)
    assert (status, state, completed_at) == ("ABORTED", "S9_SESSION_SUMMARY", None)


@pytest.mark.asyncio
async def test_an_invalid_event_is_logged_with_its_message(caplog) -> None:
    socket = _FakeSocket()
    await ws._handle_session_event(socket, uuid.uuid4(), {"type": "SESSION_EVENT", "event_type": "ANSWER_SELECTED",
                                                          "payload": "S7-009 is not a dict"})
    assert socket.sent[0]["type"] == "ERROR"
    assert "S7-009" in caplog.text and "WARNING" in caplog.text

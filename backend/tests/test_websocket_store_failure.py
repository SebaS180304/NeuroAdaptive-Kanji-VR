"""
A database failure while storing an event must not close the WebSocket: the
handler answers ERROR, logs the raw event and returns. No database.
"""

import uuid

import pytest

from app.api.routes import websocket as ws


@pytest.fixture(autouse=True)
def _clean_test_participants():
    """Overrides the conftest fixture: these tests do not touch the database."""
    yield


class _FakeSocket:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, data: dict) -> None:
        self.sent.append(data)


class _BrokenDb:
    async def __aenter__(self):
        raise ConnectionError("database down")

    async def __aexit__(self, *exc) -> bool:
        return False


@pytest.mark.asyncio
async def test_session_event_store_failure_answers_error(monkeypatch, caplog) -> None:
    monkeypatch.setattr(ws, "AsyncSessionLocal", _BrokenDb)
    socket = _FakeSocket()
    message = {"type": "SESSION_EVENT", "event_type": "ANSWER_SELECTED", "payload": {"trial_id": "S7-004"}}

    await ws._handle_session_event(socket, uuid.uuid4(), message)

    assert socket.sent == [{"type": "ERROR", "detail": "event not stored"}]
    assert "S7-004" in caplog.text   # the raw event survives in the log


@pytest.mark.asyncio
async def test_validation_event_store_failure_answers_error(monkeypatch) -> None:
    monkeypatch.setattr(ws, "AsyncSessionLocal", _BrokenDb)
    socket = _FakeSocket()
    message = {"type": "VALIDATION_EVENT", "component": "UNITY_BACKEND_WS", "status": "OK", "payload": {}}

    await ws._handle_validation_event(socket, uuid.uuid4(), message)

    assert socket.sent == [{"type": "ERROR", "detail": "event not stored"}]

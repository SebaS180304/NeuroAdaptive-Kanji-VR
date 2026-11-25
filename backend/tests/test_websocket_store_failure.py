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


class _FakeDecision:
    trial_id, action, reason_code = "S7-004", "HOLD", "R0"


class _FakePending:
    decision_id = "d-S7-004"
    decision = _FakeDecision()

    def message(self) -> dict:
        return {"type": "DECISION", "decision_id": self.decision_id}

    def event_payload(self, decision_latency_ms) -> dict:
        return {"decision_id": self.decision_id, "decision_latency_ms": decision_latency_ms}


@pytest.mark.asyncio
async def test_decision_store_failure_keeps_socket(monkeypatch, caplog) -> None:
    monkeypatch.setattr(ws, "AsyncSessionLocal", _BrokenDb)
    socket = _FakeSocket()

    await ws._send_decision(socket, uuid.uuid4(), _FakePending(), None)

    assert socket.sent == [{"type": "DECISION", "decision_id": "d-S7-004"}]
    assert "d-S7-004" in caplog.text   # the decision Unity applied survives in the log


@pytest.mark.asyncio
async def test_outcome_store_failure_keeps_socket(monkeypatch, caplog) -> None:
    monkeypatch.setattr(ws, "AsyncSessionLocal", _BrokenDb)

    await ws._store_outcomes(uuid.uuid4(), [{"decision_trial_id": "S7-004", "outcome": "IMPROVED"}])

    assert "S7-004" in caplog.text

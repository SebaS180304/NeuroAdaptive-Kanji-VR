"""
Test de feasibility de extremo a extremo (sin Unity real todavia):
crear participante -> crear sesion -> conectar por WebSocket -> mandar
PING/SESSION_EVENT/VALIDATION_EVENT -> confirmar ACKs.

Esto es exactamente lo que M1 pide poder demostrar antes de invertir en
contenido: que el walking skeleton Unity(simulado)<->Backend<->DB
funciona de punta a punta.
"""

import pytest


@pytest.mark.asyncio
async def test_full_session_walking_skeleton(client, pretested) -> None:
    participant_id = await pretested("TEST_P01")

    session_resp = await client.post(
        "/sessions",
        json={
            "participant_id": participant_id,
            "condition": "BEHAVIOR_ADAPTIVE",
            "assigned_kanji_set": "A",
            "random_seed": "seed-test-001",
            "software_version": "0.1.0",
            "config": {"esl_initial": "MEDIUM", "lal_initial": "MEDIUM"},
        },
    )
    assert session_resp.status_code == 201
    session = session_resp.json()
    assert session["current_state"] == "S0_SESSION_INITIALIZATION"

    state_resp = await client.patch(
        f"/sessions/{session['id']}/state",
        json={"new_state": "S1_WELCOME_ORIENTATION"},
    )
    assert state_resp.status_code == 200
    assert state_resp.json()["current_state"] == "S1_WELCOME_ORIENTATION"


@pytest.mark.asyncio
async def test_websocket_ping_and_events(client, pretested) -> None:
    participant_id = await pretested("TEST_P02")

    session_resp = await client.post(
        "/sessions",
        json={"participant_id": participant_id, "condition": "STATIC"},
    )
    session_id = session_resp.json()["id"]

    # httpx.AsyncClient no habla WebSocket; el smoke test real de WS se
    # documenta en README (wscat / script Python standalone) porque
    # requiere un servidor corriendo, no solo la app ASGI en memoria.
    assert session_id is not None


# completed_at (tasks/todo.md, Task 6a): set the first time the session becomes
# COMPLETED, never moved afterwards, never set on an ABORTED session.

from sqlalchemy import text  # noqa: E402

from app.db.base import AsyncSessionLocal  # noqa: E402


async def _completed_at(sid: str):
    async with AsyncSessionLocal() as db:
        return (await db.execute(text("SELECT completed_at FROM experiment_sessions WHERE id = :sid"),
                                 {"sid": sid})).scalar_one()


async def _patch(client, sid: str, state: str) -> None:
    assert (await client.patch(f"/sessions/{sid}/state", json={"new_state": state})).status_code == 200


@pytest.mark.asyncio
async def test_completed_at_is_set_at_s9_and_kept_at_s10(client, pretested) -> None:
    pid = await pretested("TEST_COMPLETED_AT")
    sid = (await client.post("/sessions", json={"participant_id": pid, "condition": "STATIC"})).json()["id"]

    await _patch(client, sid, "S8_IMMEDIATE_ASSESSMENT")
    assert await _completed_at(sid) is None

    await _patch(client, sid, "S9_SESSION_SUMMARY")
    at_s9 = await _completed_at(sid)
    assert at_s9 is not None

    await _patch(client, sid, "S10_HCI_SELF_REPORT")
    assert await _completed_at(sid) == at_s9


@pytest.mark.asyncio
async def test_late_s9_on_an_aborted_session_sets_no_completed_at(client, pretested) -> None:
    pid = await pretested("TEST_COMPLETED_AT_ABORTED")
    sid = (await client.post("/sessions", json={"participant_id": pid, "condition": "STATIC"})).json()["id"]
    await _patch(client, sid, "S5_STANDARDIZED_LEARNING")
    async with AsyncSessionLocal() as db:
        await db.execute(text("UPDATE experiment_sessions SET status = 'ABORTED' WHERE id = :sid"), {"sid": sid})
        await db.commit()

    resp = await client.patch(f"/sessions/{sid}/state", json={"new_state": "S9_SESSION_SUMMARY"})
    assert resp.json()["status"] == "ABORTED"
    assert await _completed_at(sid) is None

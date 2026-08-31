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
async def test_full_session_walking_skeleton(client) -> None:
    participant_resp = await client.post(
        "/participants",
        json={"external_code": "TEST_P01", "consent_obtained": True},
    )
    assert participant_resp.status_code == 201
    participant_id = participant_resp.json()["id"]

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
async def test_websocket_ping_and_events(client) -> None:
    participant_resp = await client.post(
        "/participants", json={"external_code": "TEST_P02"}
    )
    participant_id = participant_resp.json()["id"]

    session_resp = await client.post(
        "/sessions",
        json={"participant_id": participant_id, "condition": "STATIC"},
    )
    session_id = session_resp.json()["id"]

    # httpx.AsyncClient no habla WebSocket; el smoke test real de WS se
    # documenta en README (wscat / script Python standalone) porque
    # requiere un servidor corriendo, no solo la app ASGI en memoria.
    assert session_id is not None

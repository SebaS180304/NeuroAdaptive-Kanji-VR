"""
WebSocket de sesion: Unity <-> Backend.

Este endpoint es el corazon del "walking skeleton" que M1 (Technical
Feasibility, 28 Aug 2026) pide poder demostrar: que Unity puede
mandarle mensajes al backend por WebSocket, que el backend los
persiste en PostgreSQL, y que el roundtrip de latencia/clock offset es
medible.

Protocolo (Fase 1 - deliberadamente minimo, se expande en Fase 3 con el
vocabulario completo de eventos conductuales de la spec seccion 11.1):

Cliente -> Servidor, mensaje JSON con forma:
    {
        "type": "PING" | "SESSION_EVENT" | "VALIDATION_EVENT",
        "client_timestamp": "2026-08-24T12:00:00.000Z",   # opcional
        "event_type": "STATE_ENTERED",                     # solo SESSION_EVENT
        "component": "UNITY_BACKEND_WS",                   # solo VALIDATION_EVENT
        "status": "OK",                                    # solo VALIDATION_EVENT
        "payload": { ... }
    }

Servidor -> Cliente:
    {"type": "PONG", "server_time": "...", "offset_ms": 12.3}
    {"type": "ACK", "of": "SESSION_EVENT", "id": 123}
    {"type": "ERROR", "detail": "..."}
"""

import json
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.db.base import AsyncSessionLocal
from app.models.session import ExperimentSession
from app.models.system_event import SystemValidationEvent
from app.models.system_event import SessionEvent as SessionEventModel
from app.schemas.event import SessionEventCreate, SystemValidationEventCreate
from app.services.session_clock import now_utc, offset_ms

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/session/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: uuid.UUID) -> None:
    await websocket.accept()

    # Validamos que la sesion exista antes de aceptar telemetria; si Unity
    # se conecta con un session_id invalido, es preferible fallar rapido y
    # explicito en Fase 1 en vez de acumular datos huerfanos.
    async with AsyncSessionLocal() as db:
        session = await db.get(ExperimentSession, session_id)
        if session is None:
            await websocket.send_json({"type": "ERROR", "detail": "unknown session_id"})
            await websocket.close(code=4404)
            return

    logger.info("WS connected for session=%s", session_id)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "ERROR", "detail": "invalid JSON"})
                continue

            msg_type = message.get("type")
            received_at = now_utc()

            if msg_type == "PING":
                client_ts = _parse_timestamp(message.get("client_timestamp"))
                await websocket.send_json(
                    {
                        "type": "PONG",
                        "server_time": received_at.isoformat(),
                        "offset_ms": offset_ms(client_ts, received_at),
                    }
                )

            elif msg_type == "SESSION_EVENT":
                await _handle_session_event(websocket, session_id, message)

            elif msg_type == "VALIDATION_EVENT":
                await _handle_validation_event(websocket, session_id, message)

            else:
                await websocket.send_json(
                    {"type": "ERROR", "detail": f"unknown message type: {msg_type!r}"}
                )

    except WebSocketDisconnect:
        logger.info("WS disconnected for session=%s", session_id)


async def _handle_session_event(websocket: WebSocket, session_id: uuid.UUID, message: dict) -> None:
    try:
        parsed = SessionEventCreate(
            session_id=session_id,
            event_type=message.get("event_type", ""),
            payload=message.get("payload", {}),
            client_timestamp=message.get("client_timestamp"),
        )
    except ValidationError as exc:
        await websocket.send_json({"type": "ERROR", "detail": str(exc)})
        return

    async with AsyncSessionLocal() as db:
        event = SessionEventModel(**parsed.model_dump())
        db.add(event)
        await db.commit()
        await db.refresh(event)

    await websocket.send_json({"type": "ACK", "of": "SESSION_EVENT", "id": event.id})


async def _handle_validation_event(
    websocket: WebSocket, session_id: uuid.UUID, message: dict
) -> None:
    try:
        parsed = SystemValidationEventCreate(
            session_id=session_id,
            component=message.get("component"),
            status=message.get("status"),
            detail=message.get("payload", {}),
            client_timestamp=message.get("client_timestamp"),
        )
    except ValidationError as exc:
        await websocket.send_json({"type": "ERROR", "detail": str(exc)})
        return

    async with AsyncSessionLocal() as db:
        event = SystemValidationEvent(**parsed.model_dump())
        db.add(event)
        await db.commit()
        await db.refresh(event)

    await websocket.send_json({"type": "ACK", "of": "VALIDATION_EVENT", "id": str(event.id)})


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

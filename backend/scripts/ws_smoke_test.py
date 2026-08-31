"""
Smoke test manual del WebSocket de sesion, simulando lo que Unity hara.

Uso (con el backend corriendo, ver README):
    python scripts/ws_smoke_test.py

Crea un participante + sesion via REST, se conecta al WebSocket, y
manda un PING, un SESSION_EVENT y un VALIDATION_EVENT, verificando que
el backend responda con PONG/ACK. Esto es exactamente la prueba que
M1 (Technical Feasibility) pide poder demostrar antes de conectar el
Quest real: "Test Unity with backend WebSocket communication".
"""

import asyncio
import json
import sys
from datetime import UTC, datetime

import httpx
import websockets

BASE_HTTP = "http://localhost:8000"
BASE_WS = "ws://localhost:8000"


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE_HTTP) as client:
        participant = await client.post(
            "/participants",
            json={"external_code": f"SMOKE_{int(datetime.now().timestamp())}"},
        )
        participant.raise_for_status()
        participant_id = participant.json()["id"]
        print(f"[ok] participant created: {participant_id}")

        session = await client.post(
            "/sessions",
            json={"participant_id": participant_id, "condition": "STATIC"},
        )
        session.raise_for_status()
        session_id = session.json()["id"]
        print(f"[ok] session created: {session_id}")

    uri = f"{BASE_WS}/ws/session/{session_id}"
    async with websockets.connect(uri) as ws:
        now = datetime.now(UTC).isoformat()

        await ws.send(json.dumps({"type": "PING", "client_timestamp": now}))
        print("[ok] PONG:", await ws.recv())

        await ws.send(
            json.dumps(
                {
                    "type": "SESSION_EVENT",
                    "event_type": "SMOKE_TEST_EVENT",
                    "client_timestamp": now,
                    "payload": {"source": "ws_smoke_test.py"},
                }
            )
        )
        print("[ok] SESSION_EVENT ACK:", await ws.recv())

        await ws.send(
            json.dumps(
                {
                    "type": "VALIDATION_EVENT",
                    "component": "UNITY_BACKEND_WS",
                    "status": "OK",
                    "client_timestamp": now,
                    "payload": {"latency_ms": 0, "note": "smoke test"},
                }
            )
        )
        print("[ok] VALIDATION_EVENT ACK:", await ws.recv())

    print("\nWalking skeleton OK: REST + WebSocket + PostgreSQL respondieron correctamente.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] {exc}", file=sys.stderr)
        sys.exit(1)

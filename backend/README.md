# NeuroAdaptive VR — Backend

FastAPI async + SQLAlchemy 2.0 + PostgreSQL + WebSocket. This is the
"FastAPI skeleton" required by milestone M1 (Technical Feasibility,
28 Aug 2026): health checks, minimal participant/session CRUD, and the
WebSocket endpoint Unity uses to send telemetry.

## 1. Run everything with Docker (recommended)

```bash
cd NeuroAdaptativeVR
cp backend/.env.example backend/.env
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

Check it:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/db
```

Both should return `{"status": "ok", ...}`.

## 2. Without Docker (local Python)

Requires PostgreSQL 16 running locally.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # set POSTGRES_HOST=localhost if needed
alembic upgrade head
uvicorn app.main:app --reload
```

## 3. Run the full walking skeleton (M1 objective)

If you started with Docker (section 1), the script runs **inside the
container**, which is where `httpx` and `websockets` are installed:

```bash
docker compose exec backend python scripts/ws_smoke_test.py
```

If you started with the local venv (section 2), with the venv active:

```bash
cd backend
python scripts/ws_smoke_test.py
```

> Running `python backend/scripts/ws_smoke_test.py` from the host after
> following section 1 fails with `ModuleNotFoundError: No module named
> 'httpx'`. That is expected: the Docker path installs nothing into the
> host's Python. An earlier version of this README gave the command
> without distinguishing the two paths; corrected 7 September 2026.

The script creates a participant and a session over REST, connects to that
session's WebSocket, sends `PING` / `SESSION_EVENT` / `VALIDATION_EVENT`,
and confirms the backend answers `PONG`/`ACK` — exactly the "Test Unity
with backend WebSocket communication" item from the Phase 1 immediate
actions. With Unity connected, `unity-client/README.md` explains how to do
the same from `SessionCommunicationClient`.

## 4. Automated tests

With Docker:

```bash
docker compose exec backend pytest
```

With the local venv, from `backend/`: `pytest`.

Runs against the database configured in `.env` — make sure you have run
`alembic upgrade head` first.

**These four tests do not cover the WebSocket protocol.**
`test_websocket_ping_and_events` never opens a socket: `httpx.AsyncClient`
does not speak WebSocket, so the test only asserts that the session was
created, as its own comment states. The protocol is exercised by
`ws_smoke_test.py` and by Unity, not by the suite.

## 5. Verification status

**Verified end to end on 25 August 2026** on the development machine, with
Python 3.12 and a real PostgreSQL database. All four tests pass:

- `tests/test_health.py::test_health`
- `tests/test_health.py::test_health_db`
- `tests/test_session_lifecycle.py::test_full_session_walking_skeleton`
- `tests/test_session_lifecycle.py::test_websocket_ping_and_events`

That closes the **"FastAPI skeleton"** and **"WebSocket tested"** M1
deliverables.

Historical note: this backend was originally written in an environment
with no outbound access to PyPI, so the first version of this README
listed `pip install`, `alembic upgrade head` and `pytest` as unconfirmed.
They no longer are. Starting from scratch, the short path is section 1.

## 6. Session WebSocket protocol

Endpoint: `/ws/session/{session_id}`. The session must already exist; the
handler validates it before accepting telemetry and closes with code 4404
otherwise, so an invalid `session_id` fails fast instead of accumulating
orphaned data.

Client → server:

```json
{
  "type": "PING" | "SESSION_EVENT" | "VALIDATION_EVENT",
  "client_timestamp": "2026-08-24T12:00:00.000Z",
  "event_type": "STATE_ENTERED",
  "component": "UNITY_BACKEND_WS",
  "status": "OK",
  "payload": { }
}
```

Server → client:

```json
{"type": "PONG", "server_time": "...", "offset_ms": 12.3}
{"type": "ACK", "of": "SESSION_EVENT", "id": "123"}
{"type": "ERROR", "detail": "..."}
```

Two contract rules worth stating explicitly, because both were bugs before
Phase 2:

- **`payload` is an object, not a string.** A serialized JSON string under
  the key stores an empty payload without raising.
- **An ACK `id` is always a string**, for both event types, even though the
  underlying primary keys are BIGINT and UUID respectively.

On a `STATE_ENTERED`, the handler also updates
`experiment_sessions.current_state` in the same transaction that persists
the event. The event log remains the historical source of truth; the
column is a convenience projection of the last known state, so a payload
that cannot be interpreted logs a warning rather than rejecting the event.
`PATCH /sessions/{id}/state` still exists as a manual tool for the
researcher.

The `state` value must be the enum value in `SCREAMING_SNAKE_CASE`
(`S1_WELCOME_ORIENTATION`), which is what the `game_flow_state` PostgreSQL
type and the Pydantic model validate against — not the C# member name.

## 7. Layout

```
app/
├── main.py                    # FastAPI app, routers, CORS
├── config.py                  # Settings (pydantic-settings, reads .env)
├── db/                        # Async engine, per-request session
├── models/                    # ORM (participants, sessions, events...)
├── schemas/                   # Pydantic (request/response)
├── api/routes/                # health, participants, sessions, websocket
├── services/session_clock.py  # Shared time reference (proposal 5.3)
└── core/logging.py
alembic/                       # Migrations
scripts/ws_smoke_test.py       # Manual WebSocket smoke test
tests/                         # pytest
```

See `../database/ERD.md` for what the schema covers in this phase and what
arrives in later ones.

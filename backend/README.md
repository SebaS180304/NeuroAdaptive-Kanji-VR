# NeuroAdaptive VR — Backend (Fase 1)

FastAPI async + SQLAlchemy 2.0 + PostgreSQL + WebSocket. Este es el
"FastAPI skeleton" que pide el milestone M1 (Technical Feasibility, 28
ago 2026): health checks, CRUD mínimo de participantes/sesiones, y el
endpoint WebSocket que Unity usará para mandar telemetría.

## 1. Levantar todo con Docker (recomendado)

```bash
cd NeuroAdaptativeVR
cp backend/.env.example backend/.env
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

Verificar:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/db
```

Ambos deberían devolver `{"status": "ok", ...}`.

## 2. Alternativa sin Docker (Python local)

Requiere PostgreSQL 16 corriendo localmente.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # ajustar POSTGRES_HOST=localhost si aplica
alembic upgrade head
uvicorn app.main:app --reload
```

## 3. Probar el walking skeleton completo (objetivo de M1)

Con el backend corriendo:

```bash
python scripts/ws_smoke_test.py
```

Esto crea un participante y una sesión vía REST, se conecta al
WebSocket de esa sesión, manda `PING` / `SESSION_EVENT` /
`VALIDATION_EVENT`, y confirma que el backend responde `PONG`/`ACK` —
exactamente la prueba "Test Unity with backend WebSocket
communication" de las acciones inmediatas de Fase 1. Cuando Unity esté
conectado, `unity-client/README.md` explica cómo hacer lo mismo desde
`SessionCommunicationClient`.

## 4. Tests automatizados

```bash
pytest
```

Corre contra la base de datos configurada en `.env` — asegurate de
haber corrido `alembic upgrade head` antes.

## 5. Estado de verificación

**Verificado de punta a punta el 25 de agosto de 2026** en la máquina de
desarrollo, con Python 3.12 y una base PostgreSQL real. Los cuatro tests
pasan:

- `tests/test_health.py::test_health`
- `tests/test_health.py::test_health_db`
- `tests/test_session_lifecycle.py::test_full_session_walking_skeleton`
- `tests/test_session_lifecycle.py::test_websocket_ping_and_events`

Con eso, los entregables **"FastAPI skeleton"** y **"WebSocket probado"**
de M1 están cumplidos.

Nota histórica: este backend se escribió originalmente en un entorno sin
salida a internet para instalar dependencias de PyPI, así que la primera
versión de este README listaba `pip install`, `alembic upgrade head` y
`pytest` como pendientes de confirmar. Ya no lo están. Si vuelves a
levantar el entorno desde cero, el camino corto es la sección 1 (Docker).

## 6. Estructura

```
app/
├── main.py              # App FastAPI, routers, CORS
├── config.py             # Settings (pydantic-settings, lee .env)
├── db/                    # Engine async, sesión por request
├── models/                # ORM (participants, sessions, events...)
├── schemas/               # Pydantic (request/response)
├── api/routes/            # health, participants, sessions, websocket
├── services/session_clock.py  # Referencia temporal común (anteproyecto 5.3)
└── core/logging.py
alembic/                  # Migraciones
scripts/ws_smoke_test.py  # Smoke test manual del WebSocket
tests/                    # pytest
```

Ver `../database/ERD.md` para qué cubre el esquema en esta fase y qué
llega en fases posteriores.

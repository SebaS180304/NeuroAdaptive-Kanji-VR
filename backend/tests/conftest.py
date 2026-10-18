"""
Fixtures de pytest para los tests del walking skeleton.

Requiere una base de datos PostgreSQL accesible (ver README de
backend/): se recomienda correr `docker compose up -d db` y
`alembic upgrade head` antes de `pytest`.
"""

import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.db.base import AsyncSessionLocal
from app.main import app
from app.models.participant import Participant

# external_code fijos que usan los tests de test_session_lifecycle.py. Como
# corren contra la misma base configurada en .env (no una DB de test
# aislada), hay que limpiarlos antes de cada corrida o una segunda
# ejecucion de `pytest` choca con el UNIQUE de external_code (409).
_TEST_EXTERNAL_CODES = ["TEST_P01", "TEST_P02", "TEST_PRETEST", "TEST_PRETEST_NC", "TEST_STALE",
                        "TEST_RESEARCH_1", "TEST_RESEARCH_2", "TEST_RESEARCH_3", "TEST_GATE"]


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def _clean_test_participants():
    async def _delete() -> None:
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(Participant).where(Participant.external_code.in_(_TEST_EXTERNAL_CODES))
            )
            await session.commit()

    await _delete()  # por si quedaron de una corrida anterior interrumpida
    yield
    await _delete()  # deja la DB limpia para la proxima corrida


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def pretested(client):
    """Registers a participant with consent and runs its kanji pre-test through the API.

    Sessions require a completed pre-test (Task 1.7). Every kanji is answered "No"
    except those in `known`, which are answered "Yes" and right, so the pre-test
    tries reserves for them (each reserve gets "No" and becomes the substitute).
    """
    async def make(code: str, known: frozenset[str] | set[str] = frozenset()) -> str:
        resp = await client.post("/participants", json={"external_code": code, "consent_obtained": True})
        assert resp.status_code == 201, resp.text
        pid = resp.json()["id"]
        state = (await client.get(f"/participants/{pid}/pretest")).json()
        while state["next"] is not None:
            item = state["next"]
            body = {"kanji_id": item["kanji_id"], "self_report": "NO"}
            if item["kanji"] in known:
                body = {**body, "self_report": "YES", "typed_reading": "x", "typed_meaning": "x",
                        "reading_correct": True, "meaning_correct": True}
            state = (await client.post(f"/participants/{pid}/pretest/responses", json=body)).json()
        return pid

    return make

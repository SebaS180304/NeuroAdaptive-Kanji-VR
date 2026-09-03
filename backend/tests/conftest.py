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
_TEST_EXTERNAL_CODES = ["TEST_P01", "TEST_P02"]


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

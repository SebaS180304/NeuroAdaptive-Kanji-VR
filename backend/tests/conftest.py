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

from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

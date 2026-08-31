import pytest


@pytest.mark.asyncio
async def test_health(client) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_db(client) -> None:
    response = await client.get("/health/db")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

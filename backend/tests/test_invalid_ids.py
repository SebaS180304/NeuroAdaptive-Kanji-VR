"""
A malformed id in a REST path is rejected with 422 before any query, not a
500 from the database. No database.
"""

import pytest


@pytest.fixture(autouse=True)
def _clean_test_participants():
    """Overrides the conftest fixture: these tests do not touch the database."""
    yield


@pytest.mark.asyncio
@pytest.mark.parametrize("method, path", [
    ("GET", "/sessions/not-a-uuid"),
    ("PATCH", "/sessions/not-a-uuid/state"),
    ("GET", "/participants/not-a-uuid"),
])
async def test_malformed_id_is_422(client, method, path) -> None:
    response = await client.request(method, path, json={"new_state": "S1_WELCOME_ORIENTATION"})
    assert response.status_code == 422

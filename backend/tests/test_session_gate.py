"""
Sessions require the kanji pre-test (tasks/plan.md, Task 1.7): no session is
created for a participant whose pre-test is not complete, on any visit, and a
session reports its effective kanji set, each substitute in its original's place.
"""

import pytest
from sqlalchemy import text

from app.db.base import AsyncSessionLocal
from app.pretest.rules import contract

CODE = "TEST_GATE"


async def _sessions_of(pid: str) -> int:
    async with AsyncSessionLocal() as db:
        return (await db.execute(text("SELECT count(*) FROM experiment_sessions WHERE participant_id = :p"),
                                 {"p": pid})).scalar_one()


@pytest.mark.asyncio
@pytest.mark.parametrize("visit", [1, 2, 3])
async def test_no_session_without_a_completed_pretest(client, visit):
    pid = (await client.post("/participants", json={"external_code": CODE, "consent_obtained": True})).json()["id"]
    resp = await client.post("/sessions", json={"random_seed": "test-seed", "participant_id": pid, "condition": "STATIC",
                                                "assigned_kanji_set": "A", "visit_number": visit})
    assert resp.status_code == 409
    assert "http://127.0.0.1:5300/pretest" in resp.json()["detail"]
    assert await _sessions_of(pid) == 0


@pytest.mark.asyncio
async def test_unknown_participant_is_404(client):
    resp = await client.post("/sessions", json={"random_seed": "test-seed", "participant_id": "00000000-0000-0000-0000-000000000000",
                                                "condition": "STATIC", "assigned_kanji_set": "A"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_completed_pretest_gives_the_set_as_is(client, pretested):
    pid = await pretested(CODE)
    resp = await client.post("/sessions", json={"random_seed": "test-seed", "participant_id": pid, "condition": "STATIC", "assigned_kanji_set": "B"})
    assert resp.status_code == 201
    assert resp.json()["kanji_items"] == contract()["sets"]["B"]


@pytest.mark.asyncio
async def test_a_substituted_participant_gets_the_substituted_list(client, pretested):
    # Known 月 (first kanji of set A): the pre-test tries reserves in rank order; the
    # first one answered "No" becomes the substitute, in 月's position.
    pid = await pretested(CODE, known={"月"})
    state = (await client.get(f"/participants/{pid}/pretest")).json()
    (sub,) = [s for s in state["substitutions"] if s["original"] == "月"]
    expected = [sub["substitute"] if c == "月" else c for c in contract()["sets"]["A"]]

    created = (await client.post("/sessions", json={"random_seed": "test-seed", "participant_id": pid, "condition": "STATIC",
                                                    "assigned_kanji_set": "A"})).json()
    assert created["kanji_items"] == expected
    assert (await client.get(f"/sessions/{created['id']}")).json()["kanji_items"] == expected
    patched = await client.patch(f"/sessions/{created['id']}/state", json={"new_state": "S1_WELCOME_ORIENTATION"})
    assert patched.json()["kanji_items"] == expected
    listed = [s for s in (await client.get("/sessions")).json() if s["id"] == created["id"]]
    assert listed[0]["kanji_items"] == expected


@pytest.mark.asyncio
async def test_an_old_session_without_a_set_reads_with_no_kanji_items(client, pretested):
    # Before D-F6-187 a session could be created without a set; those rows still read, with no list.
    pid = await pretested(CODE)
    async with AsyncSessionLocal() as db:
        sid = (await db.execute(text("INSERT INTO experiment_sessions (participant_id, condition) "
                                     "VALUES (:p, 'STATIC') RETURNING id"), {"p": pid})).scalar_one()
        await db.commit()
    resp = await client.get(f"/sessions/{sid}")
    assert resp.status_code == 200 and resp.json()["kanji_items"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("seed", [None, "", "   "])
async def test_no_session_without_a_seed(client, pretested, seed):  # D-F6-183
    pid = await pretested(CODE)
    body = {"participant_id": pid, "condition": "STATIC", "assigned_kanji_set": "B"}
    if seed is not None:
        body["random_seed"] = seed
    resp = await client.post("/sessions", json=body)
    assert resp.status_code == 422
    assert await _sessions_of(pid) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("kanji_set", [None, "", "D", "a", "AB"])
async def test_no_session_without_a_set(client, pretested, kanji_set):  # D-F6-187
    pid = await pretested(CODE)
    body = {"random_seed": "test-seed", "participant_id": pid, "condition": "STATIC"}
    if kanji_set is not None:
        body["assigned_kanji_set"] = kanji_set
    resp = await client.post("/sessions", json=body)
    assert resp.status_code == 422
    assert await _sessions_of(pid) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("kanji_set", ["A", "B", "C"])
async def test_a_session_with_set_a_b_or_c_is_created(client, pretested, kanji_set):
    pid = await pretested(CODE)
    resp = await client.post("/sessions", json={"random_seed": "test-seed", "participant_id": pid,
                                                "condition": "STATIC", "assigned_kanji_set": kanji_set})
    assert resp.status_code == 201 and resp.json()["assigned_kanji_set"] == kanji_set

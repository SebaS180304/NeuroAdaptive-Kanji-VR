"""
Read-only research router for the dashboard (tasks/plan.md, Task 1.4 onwards).

GET /research/participants (V1.11): one row per participant. Three participants
cover the three pre-test states; the completed one has two sessions, the last of
them projected from the fixture with two answered S5 trials (one correct).
"""

import pytest

from tests.test_projection import _exec, _scalar
from tests.test_research_sql import _projected_session

CODES = ["TEST_RESEARCH_1", "TEST_RESEARCH_2", "TEST_RESEARCH_3"]


async def _register(client, code: str, **fields) -> str:
    resp = await client.post("/participants", json={"external_code": code, "consent_obtained": True, **fields})
    assert resp.status_code == 201
    return resp.json()["id"]


async def _finish_pretest(client, pid: str) -> None:
    """Every kanji known: the pre-test ends with 15 kanji kept and no substitute."""
    state = (await client.get(f"/participants/{pid}/pretest")).json()
    while state["next"] is not None:
        state = (await client.post(f"/participants/{pid}/pretest/responses", json={
            "kanji_id": state["next"]["kanji_id"], "self_report": "YES",
            "typed_reading": "x", "typed_meaning": "x", "reading_correct": True, "meaning_correct": True,
        })).json()


def _row(rows: list[dict], pid: str) -> dict:
    return next(r for r in rows if r["id"] == pid)


@pytest.mark.asyncio
async def test_participant_list_rows(client):
    if await _scalar("SELECT count(*) FROM kanji_items") == 0:
        pytest.skip("kanji_items is empty: apply database/seed_kanji_items.sql")

    fresh = await _register(client, CODES[0], previous_japanese_experience=True)

    started = await _register(client, CODES[1])
    first = (await client.get(f"/participants/{started}/pretest")).json()["next"]["kanji_id"]
    await client.post(f"/participants/{started}/pretest/responses", json={"kanji_id": first, "self_report": "NO"})

    done = await _register(client, CODES[2], previous_japanese_experience=False)
    await _finish_pretest(client, done)
    await _exec("INSERT INTO experiment_sessions (participant_id, condition, created_at) "
                "VALUES (:p, 'BEHAVIOR_ADAPTIVE', now() - interval '1 day')", p=done)
    last = await _projected_session(done)              # STATIC, newest
    await _exec("UPDATE trials SET block_state = 'S5_STANDARDIZED_LEARNING', is_correct = (trial_id = "
                "(SELECT min(trial_id) FROM trials WHERE session_id = :s)) WHERE session_id = :s", s=last)

    resp = await client.get("/research/participants")
    assert resp.status_code == 200
    rows = resp.json()

    assert _row(rows, fresh) | {"created_at": None} == {
        "id": fresh, "external_code": CODES[0], "created_at": None,
        "pretest_status": "NOT_STARTED", "pretest_answered": 0, "pretest_completed_at": None,
        "session_count": 0, "conditions": [], "last_session_at": None, "last_session_accuracy": None,
        "previous_japanese_experience": True, "flagged_count": None,
    }

    row = _row(rows, started)
    assert (row["pretest_status"], row["pretest_answered"], row["flagged_count"]) == ("IN_PROGRESS", 1, None)
    assert row["previous_japanese_experience"] is None

    row = _row(rows, done)
    answered = (await client.get(f"/participants/{done}/pretest")).json()["answered"]   # reserves asked too
    assert (row["pretest_status"], row["pretest_answered"], row["flagged_count"]) == ("COMPLETED", answered, 15)
    assert row["pretest_completed_at"] is not None
    assert row["session_count"] == 2
    assert row["conditions"] == ["STATIC", "BEHAVIOR_ADAPTIVE"]      # enum order, not alphabetical
    assert row["last_session_accuracy"] == 0.5
    last_created = await _scalar("SELECT created_at FROM experiment_sessions WHERE id = :s", s=last)
    assert row["last_session_at"].replace("Z", "+00:00") == last_created.isoformat()


def test_research_router_is_read_only():
    """Skill rule 1: the /research router has GET endpoints only."""
    from app.main import app
    research = [r for r in app.routes if getattr(r, "path", "").startswith("/research")]
    assert research
    for route in research:
        assert route.methods <= {"GET", "HEAD"}, route.path

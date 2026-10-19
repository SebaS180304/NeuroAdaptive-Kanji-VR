"""
Read-only research router for the dashboard (tasks/plan.md, Task 1.4 onwards).

GET /research/participants (V1.11): one row per participant. Three participants
cover the three pre-test states; the completed one has two sessions, the last of
them projected from the fixture with two answered S5 trials (one correct).

GET /research/sessions (V1.1): one row per session, filters combined. A projected
STATIC session and an adaptive one with no events at all.

GET /research/sessions/{id} (V1.2): the summary, checked against trial_timeline()
and v_adaptations on the STATIC fixture session and on the adaptive S7 of
test_projection_adaptation.py.
"""

import pytest

from tests.test_projection import _exec, _scalar
from tests import test_projection_adaptation as adaptive
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


@pytest.mark.asyncio
async def test_session_list_rows_and_filters(client):
    pid = await _register(client, CODES[0])
    static = await _projected_session(pid)
    await _exec("UPDATE experiment_sessions SET status = 'COMPLETED' WHERE id = :s", s=static)
    await _exec("UPDATE trials SET block_state = 'S5_STANDARDIZED_LEARNING', is_correct = (trial_id = "
                "(SELECT min(trial_id) FROM trials WHERE session_id = :s)) WHERE session_id = :s", s=static)
    empty = str(await _scalar("INSERT INTO experiment_sessions (participant_id, condition, status, visit_number, created_at) "
                              "VALUES (:p, 'BEHAVIOR_ADAPTIVE', 'ABORTED', 2, now() - interval '2 days') RETURNING id", p=pid))

    async def ids(**params) -> list[str]:
        resp = await client.get("/research/sessions", params={"participant_id": pid, **params})
        assert resp.status_code == 200
        return [r["session_id"] for r in resp.json()]

    rows = (await client.get("/research/sessions", params={"participant_id": pid})).json()
    assert [r["session_id"] for r in rows] == [str(static), empty]          # newest first
    trials = await _scalar("SELECT count(*) FROM trials WHERE session_id = :s", s=static)
    assert rows[0] | {"created_at": None} == {
        "session_id": str(static), "participant_id": pid, "external_code": CODES[0],
        "condition": "STATIC", "status": "COMPLETED", "visit_number": 1, "created_at": None,
        "projection_status": "PROJECTED", "trial_count": trials, "decision_count": None,
        "accuracy": 0.5, "open_error_count": 0,
    }
    # No events: counts are "not recorded" (None), not zero.
    assert rows[1] | {"created_at": None} == {
        "session_id": empty, "participant_id": pid, "external_code": CODES[0],
        "condition": "BEHAVIOR_ADAPTIVE", "status": "ABORTED", "visit_number": 2, "created_at": None,
        "projection_status": "NO_DATA", "trial_count": None, "decision_count": None,
        "accuracy": None, "open_error_count": 0,
    }

    assert await ids(condition="STATIC") == [str(static)]
    assert await ids(status="ABORTED") == [empty]
    assert await ids(condition="STATIC", status="ABORTED") == []
    yesterday = (await _scalar("SELECT now() - interval '1 day'")).isoformat()
    assert await ids(**{"from": yesterday}) == [str(static)]
    assert await ids(to=yesterday) == [empty]
    assert (await client.get("/research/sessions", params={"status": "PAUSED"})).status_code == 422


@pytest.mark.asyncio
async def test_session_summary_static(client):
    pid = await _register(client, CODES[0])
    sid = await _projected_session(pid)
    resp = await client.get(f"/research/sessions/{sid}")
    assert resp.status_code == 200
    body = resp.json()

    states = await _exec("SELECT state::text, entered_elapsed_ms, exited_elapsed_ms FROM session_states "
                         "WHERE session_id = :s ORDER BY visit_seq", s=sid)
    assert [tuple(x.values()) for x in body["states"]] == [tuple(r) for r in states]
    tl = (await _exec("SELECT count(*), avg(response_time_ms), avg(window_rt_cv), min(block_state)::text, "
                      "max(block_state)::text FROM trial_timeline(:s, 3)", s=sid))[0]
    answered = (await _exec("SELECT avg(response_time_ms), avg(window_rt_cv) FROM trial_timeline(:s, 3) "
                            "WHERE response_time_ms IS NOT NULL", s=sid))[0]
    assert body["trial_count"] == tl[0]
    assert (body["first_block"], body["last_block"]) == (tl[3], tl[4])
    assert body["mean_rt_ms"] == pytest.approx(float(answered[0]))
    assert body["rt_cv_mean"] == (None if answered[1] is None else pytest.approx(float(answered[1])))
    assert body["hint_requests"] == await _scalar("SELECT count(*) FROM hint_requests WHERE session_id = :s", s=sid)
    assert body["condition"] == "STATIC"
    assert body["adaptations"] is None                                     # no decisions recorded
    away = await _scalar("SELECT count(*) FROM session_events WHERE session_id = :s AND event_type = 'HEAD_AWAY'", s=sid)
    if away == 0:
        assert (body["head_away_count"], body["head_away_ms"]) == (None, None)
    else:
        assert body["head_away_count"] == await _scalar(
            "SELECT count(*) FROM head_away_episodes WHERE session_id = :s", s=sid)


@pytest.mark.asyncio
async def test_session_summary_adaptive():
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    await adaptive._exec("DELETE FROM participants WHERE external_code = :c", c=adaptive.PARTICIPANT_CODE)
    sid = await adaptive._new_session()
    await adaptive._insert_and_project(sid, adaptive._events())
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            body = (await client.get(f"/research/sessions/{sid}")).json()
        assert body["states"] == [{"state": "S7_EXPERIMENTAL_RETRIEVAL", "entered_elapsed_ms": 0,
                                   "exited_elapsed_ms": None}]                 # cut: no exit
        assert (body["trial_count"], body["first_block"], body["last_block"]) ==             (3, "S7_EXPERIMENTAL_RETRIEVAL", "S7_EXPERIMENTAL_RETRIEVAL")
        assert body["accuracy"] == pytest.approx(2 / 3)
        assert body["mean_rt_ms"] == 2000
        assert (body["hint_requests"], body["proactive_hints"]) == (0, 1)
        assert (body["head_away_count"], body["head_away_ms"]) == (None, None)   # no HEAD_AWAY event
        assert body["adaptations"] == {
            "decisions": 2, "environment_changes": 0, "assistance_changes": 1, "skipped_by_unity": 1,
            "outcome_positive": 0, "outcome_neutral": 0, "outcome_negative": 0, "outcome_uncertain": 0,
            "outcome_not_recorded": 1,
        }
        v = (await adaptive._exec("SELECT count(*), count(*) FILTER (WHERE action = 'CHANGE_ASSISTANCE') "
                                  "FROM v_adaptations WHERE session_id = :s", s=sid))[0]
        assert (body["adaptations"]["decisions"], body["adaptations"]["assistance_changes"]) == tuple(v)
    finally:
        await adaptive._exec("DELETE FROM participants WHERE external_code = :c", c=adaptive.PARTICIPANT_CODE)


@pytest.mark.asyncio
async def test_session_summary_unknown_id(client):
    assert (await client.get("/research/sessions/00000000-0000-0000-0000-000000000000")).status_code == 404


def test_research_router_is_read_only():
    """Skill rule 1: the /research router has GET endpoints only."""
    from app.main import app
    research = [r for r in app.routes if getattr(r, "path", "").startswith("/research")]
    assert research
    for route in research:
        assert route.methods <= {"GET", "HEAD"}, route.path

"""
BR1 (tasks/plan.md): the data path of block R (D-F6-125, D-F6-190, D-F6-223). A session of visit >= 2 stores
which session it evaluates (deduced: the participant's last COMPLETED session of the previous visit; or given),
and block R's answers are stored and projected without ever reaching the engine.
"""

import json

import pytest
from sqlalchemy import text

from app.adaptation.state import SessionAdaptationState
from app.api.routes.websocket import _project
from app.db.base import AsyncSessionLocal

SR = "SR_DELAYED_RETENTION"


async def _session(client, pid: str, visit: int, kanji_set: str = "A", **extra):
    return await client.post("/sessions", json={"random_seed": "test-seed", "participant_id": pid, "condition": "STATIC",
                                                "assigned_kanji_set": kanji_set, "visit_number": visit, **extra})


async def _status(sid: str, status: str) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(text("UPDATE experiment_sessions SET status = CAST(:st AS session_status) WHERE id = :s"),
                         {"s": sid, "st": status})
        await db.commit()


@pytest.mark.asyncio
async def test_visit_2_evaluates_the_last_completed_visit_1(client, pretested) -> None:
    pid = await pretested("TEST_BR_A")
    done = (await _session(client, pid, 1, "A")).json()["id"]
    await _status(done, "COMPLETED")
    aborted = (await _session(client, pid, 1, "A")).json()["id"]      # later, but not completed
    await _status(aborted, "ABORTED")
    v2 = await _session(client, pid, 2, "B")
    assert v2.status_code == 201, v2.text
    body = v2.json()
    assert body["evaluated_session_id"] == done
    assert body["evaluated_kanji_set"] == "A" and len(body["evaluated_kanji_items"]) == 5
    assert body["kanji_items"] != body["evaluated_kanji_items"]       # block R uses the evaluated set, not B


@pytest.mark.asyncio
async def test_visit_1_evaluates_nothing(client, pretested) -> None:
    pid = await pretested("TEST_BR_B")
    body = (await _session(client, pid, 1)).json()
    assert body["evaluated_session_id"] is None and body["evaluated_kanji_items"] is None


@pytest.mark.asyncio
async def test_without_a_completed_previous_visit_the_session_is_refused(client, pretested) -> None:
    pid = await pretested("TEST_BR_C")
    resp = await _session(client, pid, 2)
    assert resp.status_code == 422 and "evaluated_session_id" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_the_evaluated_session_can_be_given_and_must_be_earlier_and_the_same_participant(client, pretested) -> None:
    pid, other = await pretested("TEST_BR_D"), await pretested("TEST_BR_E")
    mine = (await _session(client, pid, 1, "C")).json()["id"]          # given by hand: need not be COMPLETED
    theirs = (await _session(client, other, 1)).json()["id"]
    ok = await _session(client, pid, 2, "A", evaluated_session_id=mine)
    assert ok.status_code == 201 and ok.json()["evaluated_session_id"] == mine
    assert ok.json()["evaluated_kanji_set"] == "C"
    assert (await _session(client, pid, 2, "A", evaluated_session_id=theirs)).status_code == 422
    later = ok.json()["id"]
    assert (await _session(client, other, 2, "A", evaluated_session_id=later)).status_code == 422


def _ev(event_type: str, ms: int, **fields) -> dict:
    return {"event_type": event_type,
            "payload": {"schema_version": 1, "state": SR, "session_elapsed_ms": ms, "esl": "LOW", "lal": "OFF", **fields}}


BLOCK_R = [
    _ev("STATE_ENTERED", 100),
    _ev("BLOCK_R_RECALL_ENDED", 90_000, elapsed_ms=89_900),
    _ev("BLOCK_R_RECOGNITION_ANSWERED", 95_000, kanji_id="KANJI_TSUKI", seen=True, answer=True, is_correct=True,
        rt_ms=1200, item_sequence=1),
    _ev("TRIAL_STARTED", 100_000, trial_id="SR-001", trial_sequence=1, trial_type="T1_MEANING_TO_KANJI",
        kanji_id="KANJI_TSUKI", options=["KANJI_TSUKI", "KANJI_HI", "KANJI_KI", "KANJI_YAMA"],
        correct_option="KANJI_TSUKI", hint_available=False),
    _ev("ANSWER_SELECTED", 103_000, trial_id="SR-001", selected_option="KANJI_TSUKI", is_correct=True,
        response_time_ms=3000, timed_out=False),
]


@pytest.mark.asyncio
async def test_block_r_answers_are_stored_and_projected_as_their_own_block(client, pretested) -> None:
    pid = await pretested("TEST_BR_F")
    sid = (await _session(client, pid, 1)).json()["id"]
    async with AsyncSessionLocal() as db:
        for ev in BLOCK_R:
            eid = (await db.execute(text("INSERT INTO session_events (session_id, event_type, payload) "
                                         "VALUES (:s, :t, CAST(:p AS jsonb)) RETURNING id"),
                                    {"s": sid, "t": ev["event_type"], "p": json.dumps(ev["payload"])})).scalar()
            await _project(db, eid)
        await db.commit()
        errors = (await db.execute(text("SELECT error_code FROM projection_errors WHERE session_id = :s"),
                                   {"s": sid})).scalars().all()
        trial = (await db.execute(text("SELECT trial_id, block_state::text, is_correct FROM trials WHERE session_id = :s"),
                                  {"s": sid})).one()
    assert errors == []
    assert tuple(trial) == ("SR-001", SR, True)


def test_block_r_never_reaches_the_engine() -> None:
    state = SessionAdaptationState("BEHAVIOR_ADAPTIVE")
    assert all(state.feed(ev["event_type"], ev["payload"]) is None for ev in BLOCK_R)
    assert state.decisions == {}

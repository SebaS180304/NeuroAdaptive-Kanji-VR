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


# ---------- BR3: the free recall form (V1.12, D-F6-226; D-F6-225; D-F6-230 (1)) ----------

async def _visit2(client, pretested, code: str):
    pid = await pretested(code)
    v1 = (await _session(client, pid, 1, "A")).json()["id"]
    await _status(v1, "COMPLETED")
    v2 = (await _session(client, pid, 2, "B")).json()["id"]
    return v1, v2


def _marks(form: dict, marked: dict[str, tuple[bool, bool, int]]) -> dict:
    """marked: kanji_id -> (meaning, reading, order); the rest unmarked."""
    items = [{"kanji_id": k["kanji_id"], "meaning": marked.get(k["kanji_id"], (False, False, None))[0],
              "reading": marked.get(k["kanji_id"], (False, False, None))[1],
              "order": marked.get(k["kanji_id"], (False, False, None))[2], "said": None} for k in form["kanji"]]
    return {"items": items, "anything_else": None}


@pytest.mark.asyncio
async def test_the_form_shows_the_evaluated_sessions_five_kanji_and_nothing_saved_yet(client, pretested) -> None:
    v1, v2 = await _visit2(client, pretested, "TEST_BR_G")
    form = (await client.get(f"/sessions/{v2}/block-r/recall")).json()
    assert form["evaluated_session_id"] == v1 and form["evaluated_kanji_set"] == "A" and form["visit_number"] == 2
    assert [k["kanji"] for k in form["kanji"]] == ["月", "車", "火", "竹", "石"]
    assert form["kanji"][0]["meaning"] and form["kanji"][0]["reading"]        # "Taught as"
    assert form["participant_code"] == "TEST_BR_G" and form["saved"] is None  # never saved = not recorded (D9)
    assert form["board_text"][0].startswith("Last time you learned some kanji.")  # R1 as the VR shows it


@pytest.mark.asyncio
async def test_saving_stores_the_marks_and_a_second_save_replaces_them(client, pretested) -> None:
    _, v2 = await _visit2(client, pretested, "TEST_BR_H")
    form = (await client.get(f"/sessions/{v2}/block-r/recall")).json()
    first, second = form["kanji"][0]["kanji_id"], form["kanji"][3]["kanji_id"]
    body = _marks(form, {first: (True, False, 1), second: (True, True, 2)})
    body["items"][3]["said"] = "bamboo? or tree"
    saved = (await client.post(f"/sessions/{v2}/block-r/recall", json=body)).json()["saved"]
    assert saved["recalled"] == 2 and saved["saved_at"]
    again = (await client.post(f"/sessions/{v2}/block-r/recall", json=_marks(form, {second: (False, True, 1)}))).json()
    assert again["saved"]["recalled"] == 1
    read = (await client.get(f"/sessions/{v2}/block-r/recall")).json()["saved"]
    assert [(i["meaning"], i["reading"], i["order"]) for i in read["items"] if i["kanji_id"] == second] == [(False, True, 1)]
    async with AsyncSessionLocal() as db:
        n = (await db.execute(text("SELECT count(*) FROM session_events WHERE session_id = :s AND event_type = 'BLOCK_R_FREE_RECALL'"),
                              {"s": v2})).scalar_one()
    assert n == 2                                                            # every save kept, the last one wins


@pytest.mark.asyncio
async def test_saved_with_no_marks_is_nothing_recalled_not_never_saved(client, pretested) -> None:
    _, v2 = await _visit2(client, pretested, "TEST_BR_I")
    form = (await client.get(f"/sessions/{v2}/block-r/recall")).json()
    saved = (await client.post(f"/sessions/{v2}/block-r/recall", json=_marks(form, {}))).json()["saved"]
    assert saved is not None and saved["recalled"] == 0


@pytest.mark.asyncio
async def test_the_marks_must_be_the_evaluated_kanji_once_with_a_coherent_order(client, pretested) -> None:
    _, v2 = await _visit2(client, pretested, "TEST_BR_J")
    form = (await client.get(f"/sessions/{v2}/block-r/recall")).json()
    ok = _marks(form, {})
    wrong_kanji = {**ok, "items": ok["items"][:4] + [{**ok["items"][4], "kanji_id": "KANJI_YAMA"}]}
    order_without_mark = _marks(form, {form["kanji"][0]["kanji_id"]: (False, False, 1)})
    mark_without_order = _marks(form, {form["kanji"][0]["kanji_id"]: (True, False, None)})
    for bad in (wrong_kanji, order_without_mark, mark_without_order):
        assert (await client.post(f"/sessions/{v2}/block-r/recall", json=bad)).status_code == 422


@pytest.mark.asyncio
async def test_a_session_without_block_r_has_no_recall_form(client, pretested) -> None:
    pid = await pretested("TEST_BR_K")
    v1 = (await _session(client, pid, 1)).json()["id"]
    assert (await client.get(f"/sessions/{v1}/block-r/recall")).status_code == 409

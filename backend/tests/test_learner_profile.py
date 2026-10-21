"""
Learner Profile v1 (tasks/plan.md, "Architecture decisions: Learner Profile v1").
One learner_profiles row per participant and format version (migration 0007).
"""

import json

import pytest
from sqlalchemy import text

from app.db.base import AsyncSessionLocal


async def _scalar(query: str, **params):
    async with AsyncSessionLocal() as db:
        return (await db.execute(text(query), params)).scalar_one()


@pytest.mark.asyncio
async def test_a_profile_row_is_one_per_version_and_goes_with_its_participant(pretested) -> None:
    pid = await pretested("TEST_PROFILE")
    async with AsyncSessionLocal() as db:
        await db.execute(text("INSERT INTO learner_profiles (participant_id, profile) "
                              "VALUES (:pid, CAST(:p AS jsonb))"), {"pid": pid, "p": json.dumps({"calibrations": []})})
        await db.commit()

    assert await _scalar("SELECT profile_version FROM learner_profiles WHERE participant_id = :pid", pid=pid) == "v1"
    assert await _scalar("SELECT session_ids FROM learner_profiles WHERE participant_id = :pid", pid=pid) == []

    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM participants WHERE id = :pid"), {"pid": pid})
        await db.commit()
    assert await _scalar("SELECT count(*) FROM learner_profiles WHERE participant_id = :pid", pid=pid) == 0


# --- compute (Task 7) ------------------------------------------------------------

from collections import Counter  # noqa: E402

from app.adaptation import learner_profile  # noqa: E402
from app.adaptation.profile import build_profile  # noqa: E402
from app.adaptation.trials import build_trials  # noqa: E402


async def _rows(query: str, **params) -> list[dict]:
    async with AsyncSessionLocal() as db:
        return [dict(r._mapping) for r in await db.execute(text(query), params)]


async def _compute(pid: str) -> dict:
    async with AsyncSessionLocal() as db:
        await learner_profile.compute(db, pid)
        await db.commit()
    rows = await _rows("SELECT session_ids, profile FROM learner_profiles WHERE participant_id = :pid", pid=pid)
    assert len(rows) == 1
    return rows[0]


@pytest.mark.asyncio
async def test_dev_unity_profile_matches_its_completed_sessions() -> None:
    dev = await _rows("SELECT id::text AS id FROM participants WHERE external_code = 'DEV_UNITY'")
    if not dev:
        pytest.skip("no DEV_UNITY in this database")
    pid = dev[0]["id"]
    row = await _compute(pid)
    profile = row["profile"]

    completed = [r["id"] for r in await _rows(
        "SELECT id::text AS id FROM experiment_sessions WHERE participant_id = :pid AND status = 'COMPLETED' "
        "ORDER BY created_at", pid=pid)]
    assert [str(s) for s in row["session_ids"]] == completed          # ABORTED ones are in no part
    assert [c["session_id"] for c in profile["calibrations"]] == completed
    assert [t["session_id"] for t in profile["trend"]] == completed

    # Calibration: the S6 profile the live path builds from the same events.
    for cal in profile["calibrations"]:
        events = await _rows("SELECT id, event_type, payload FROM session_events WHERE session_id = :s ORDER BY id",
                             s=cal["session_id"])
        expected = build_profile(build_trials(events)).as_dict()
        assert {k: cal[k] for k in expected} == expected
        assert cal["n"] == expected["n_trials"]
        assert 0 <= cal["correct"] <= cal["n"]

    # Adaptations: every change of a completed session, once, with its outcome.
    changes = await _rows("""
        SELECT d.session_id::text AS sid, d.decision_id, d.learner_state, d.cause, d.dimension,
               d.outcome, e.payload->>'outcome_reason' AS reason
        FROM adaptation_decisions d JOIN experiment_sessions s ON s.id = d.session_id
        LEFT JOIN session_events e ON e.id = d.outcome_event_id
        WHERE s.participant_id = :pid AND s.status = 'COMPLETED' AND d.action <> 'NO_CHANGE'""", pid=pid)
    groups = profile["adaptations"]
    assert sum(g["count"] for g in groups) == len(changes)
    ids = sorted((sid, d) for g in groups for sid, ds in g["decisions"].items() for d in ds)
    assert ids == sorted((c["sid"], c["decision_id"]) for c in changes)
    for g in groups:
        assert sum(len(ds) for ds in g["decisions"].values()) == g["count"]
        assert sum(g["outcomes"].values()) == g["count"]
        assert {o: sum(r.values()) for o, r in g["outcome_reasons"].items()} == g["outcomes"]
    got = Counter((o, r) for g in groups for o, rs in g["outcome_reasons"].items() for r, n in rs.items() for _ in range(n))
    assert got == Counter((c["outcome"] or "NOT_RECORDED", c["reason"] or "NOT_RECORDED") for c in changes)

    # Trend and NO_CHANGE counts: straight from the schema.
    for t in profile["trend"]:
        s7 = (await _rows("""
            SELECT count(*) AS trials, count(*) FILTER (WHERE is_correct) AS correct,
                   round(avg(response_time_ms)::numeric, 1)::float AS mean_rt
            FROM trials WHERE session_id = :s AND block_state = 'S7_EXPERIMENTAL_RETRIEVAL'""",
                              s=t["session_id"]))[0]
        assert (t["s7_trials"], t["s7_correct"], t["s7_mean_rt_ms"]) == (s7["trials"], s7["correct"], s7["mean_rt"])
        n = (await _rows("SELECT count(*) FILTER (WHERE action = 'NO_CHANGE') AS nc, count(*) AS d "
                         "FROM adaptation_decisions WHERE session_id = :s", s=t["session_id"]))[0]
        if t["condition"] == "STATIC":
            assert t["no_change"] is None and t["decisions_recorded"] is None
        else:
            assert (t["no_change"], t["decisions_recorded"]) == (n["nc"], n["d"] > 0)


async def _session(client, pid: str, condition: str, state: str) -> str:
    sid = (await client.post("/sessions", json={"participant_id": pid, "condition": condition})).json()["id"]
    assert (await client.patch(f"/sessions/{sid}/state", json={"new_state": state})).status_code == 200
    return sid


@pytest.mark.asyncio
async def test_static_aborted_and_unrecorded_sessions(client, pretested) -> None:
    pid = await pretested("TEST_PROFILE")
    static = await _session(client, pid, "STATIC", "S9_SESSION_SUMMARY")
    adaptive = await _session(client, pid, "BEHAVIOR_ADAPTIVE", "S9_SESSION_SUMMARY")   # no decisions: before 0003
    aborted = await _session(client, pid, "BEHAVIOR_ADAPTIVE", "S7_EXPERIMENTAL_RETRIEVAL")
    async with AsyncSessionLocal() as db:
        await db.execute(text("UPDATE experiment_sessions SET status = 'ABORTED' WHERE id = :s"), {"s": aborted})
        await db.commit()

    row = await _compute(pid)
    profile = row["profile"]
    assert [str(s) for s in row["session_ids"]] == [static, adaptive]
    assert profile["adaptations"] == []
    trend = {t["session_id"]: t for t in profile["trend"]}
    assert trend[static]["decisions_recorded"] is None
    assert trend[adaptive]["decisions_recorded"] is False
    assert aborted not in trend


@pytest.mark.asyncio
async def test_a_participant_with_only_aborted_sessions_gets_an_empty_profile(client, pretested) -> None:
    pid = await pretested("TEST_PROFILE")
    sid = await _session(client, pid, "STATIC", "S5_STANDARDIZED_LEARNING")
    async with AsyncSessionLocal() as db:
        await db.execute(text("UPDATE experiment_sessions SET status = 'ABORTED' WHERE id = :s"), {"s": sid})
        await db.commit()

    row = await _compute(pid)
    assert row["session_ids"] == []
    assert row["profile"] == {"calibrations": [], "adaptations": [], "trend": []}


@pytest.mark.asyncio
async def test_check_finds_no_difference_right_after_a_rebuild(pretested) -> None:
    pid = await pretested("TEST_PROFILE")
    await _compute(pid)
    async with AsyncSessionLocal() as db:
        assert await learner_profile.differences(db, pid) == []
        await db.execute(text("UPDATE learner_profiles SET profile = '{}' WHERE participant_id = :pid"), {"pid": pid})
        await db.commit()
        assert await learner_profile.differences(db, pid) != []


# --- triggers (Task 8) -----------------------------------------------------------

from app.services.stale_sessions import abort_stale_sessions  # noqa: E402


async def _stored(pid: str) -> list[dict]:
    return await _rows("SELECT session_ids FROM learner_profiles WHERE participant_id = :pid", pid=pid)


@pytest.mark.asyncio
async def test_reaching_s9_computes_the_profile(client, pretested) -> None:
    pid = await pretested("TEST_PROFILE")
    sid = await _session(client, pid, "STATIC", "S8_IMMEDIATE_ASSESSMENT")
    assert await _stored(pid) == []

    await client.patch(f"/sessions/{sid}/state", json={"new_state": "S9_SESSION_SUMMARY"})
    assert [str(s) for s in (await _stored(pid))[0]["session_ids"]] == [sid]


@pytest.mark.asyncio
async def test_an_abort_by_the_sweep_gives_a_row_without_the_session(client, pretested) -> None:
    pid = await pretested("TEST_PROFILE")
    sid = await _session(client, pid, "STATIC", "S5_STANDARDIZED_LEARNING")
    async with AsyncSessionLocal() as db:
        await db.execute(text("UPDATE experiment_sessions SET updated_at = now() - interval '31 minutes' "
                              "WHERE id = :s"), {"s": sid})
        await db.commit()

    assert await abort_stale_sessions() >= 1
    stored = await _stored(pid)
    assert len(stored) == 1 and stored[0]["session_ids"] == []

    # A late S9 keeps it ABORTED and does not bring it into the profile.
    await client.patch(f"/sessions/{sid}/state", json={"new_state": "S9_SESSION_SUMMARY"})
    assert (await _stored(pid))[0]["session_ids"] == []


@pytest.mark.asyncio
async def test_a_failing_profile_never_fails_the_patch_or_the_sweep(client, pretested, monkeypatch) -> None:
    async def boom(db, participant_id):
        raise RuntimeError("forced")
    monkeypatch.setattr(learner_profile, "compute", boom)

    pid = await pretested("TEST_PROFILE")
    sid = await _session(client, pid, "STATIC", "S8_IMMEDIATE_ASSESSMENT")
    resp = await client.patch(f"/sessions/{sid}/state", json={"new_state": "S9_SESSION_SUMMARY"})
    assert resp.status_code == 200 and resp.json()["status"] == "COMPLETED"

    stale = await _session(client, pid, "STATIC", "S5_STANDARDIZED_LEARNING")
    async with AsyncSessionLocal() as db:
        await db.execute(text("UPDATE experiment_sessions SET updated_at = now() - interval '31 minutes' "
                              "WHERE id = :s"), {"s": stale})
        await db.commit()
    assert await abort_stale_sessions() >= 1


# --- endpoint (Task 9) -----------------------------------------------------------

import uuid  # noqa: E402


@pytest.mark.asyncio
async def test_profile_endpoint_returns_the_stored_row(client, pretested) -> None:
    pid = await pretested("TEST_PROFILE")
    sid = await _session(client, pid, "STATIC", "S9_SESSION_SUMMARY")      # computes it (Task 8)

    resp = await client.get(f"/research/participants/{pid}/profile")
    assert resp.status_code == 200
    body = resp.json()
    assert body["participant_id"] == pid and body["profile_version"] == "v1"
    assert body["session_ids"] == [sid] and body["computed_at"] is not None
    assert [t["session_id"] for t in body["profile"]["trend"]] == [sid]
    assert body["profile"]["trend"][0]["decisions_recorded"] is None
    assert body["profile"]["adaptations"] == []


@pytest.mark.asyncio
async def test_profile_endpoint_without_a_row_or_participant(client, pretested) -> None:
    pid = await pretested("TEST_PROFILE")
    body = (await client.get(f"/research/participants/{pid}/profile")).json()
    assert body == {"participant_id": pid, "profile_version": None, "computed_at": None,
                    "session_ids": [], "profile": None}

    assert (await client.get(f"/research/participants/{uuid.uuid4()}/profile")).status_code == 404


@pytest.mark.asyncio
async def test_profile_endpoint_matches_the_stored_json() -> None:
    """Every field the calculation writes survives the schema (none dropped or renamed)."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    rows = await _rows("SELECT participant_id::text AS pid, profile FROM learner_profiles l "
                       "JOIN participants p ON p.id = l.participant_id WHERE p.external_code = 'DEV_UNITY'")
    if not rows:
        pytest.skip("no DEV_UNITY profile in this database")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get(f"/research/participants/{rows[0]['pid']}/profile")).json()
    assert body["profile"] == rows[0]["profile"]


# --- D-F6-1 (Task 10) ------------------------------------------------------------

from app.adaptation.rules import HOME_LEVEL  # noqa: E402
from app.api.routes import websocket  # noqa: E402


@pytest.mark.asyncio
async def test_the_profile_never_changes_how_a_session_starts(client, pretested) -> None:
    """D-F6-1 (Plan_Fase6 §4): the profile records and summarises; it does not set the
    starting levels "until after the pilot", or STATIC and adaptive would stop starting
    alike. A participant whose profile says raising assistance helped starts the same as
    one with no profile at all."""
    with_profile = await pretested("TEST_PROFILE")
    without = await pretested("TEST_PROFILE_NONE")
    history = {"calibrations": [], "trend": [], "adaptations": [{
        "key": "OVERLOADED.NONE.LAL.UP", "learner_state": "OVERLOADED", "cause": None, "dimension": "LAL",
        "direction": "UP", "count": 3, "outcomes": {"POSITIVE": 3},
        "outcome_reasons": {"POSITIVE": {"RESOLVED": 3}}, "decisions": {}, "last_decided_at": None}]}
    async with AsyncSessionLocal() as db:
        await db.execute(text("INSERT INTO learner_profiles (participant_id, profile) VALUES (:p, CAST(:j AS jsonb))"),
                         {"p": with_profile, "j": json.dumps(history)})
        await db.commit()

    started = {}
    for pid in (with_profile, without):
        resp = await client.post("/sessions", json={"participant_id": pid, "condition": "BEHAVIOR_ADAPTIVE",
                                                    "assigned_kanji_set": "A"})
        assert resp.status_code == 201
        body = resp.json()
        session_id = uuid.UUID(body["id"])
        async with AsyncSessionLocal() as db:
            await websocket._load_adaptation(db, session_id, "BEHAVIOR_ADAPTIVE")
        state = websocket._adaptation.pop(session_id)
        state.feed("STATE_ENTERED", {"state": "S7_EXPERIMENTAL_RETRIEVAL", "session_elapsed_ms": 1000})
        started[pid] = ({k: v for k, v in body.items()
                         if k not in ("id", "participant_id", "created_at", "session_clock_started_at")},
                        (state.engine.esl, state.engine.lal))

    assert started[with_profile] == started[without]
    assert started[with_profile][1] == (HOME_LEVEL, HOME_LEVEL)
    assert not any("level" in k or k in ("esl", "lal") for k in started[with_profile][0])

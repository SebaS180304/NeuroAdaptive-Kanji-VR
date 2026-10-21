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

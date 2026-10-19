"""
Read-only research router for the dashboard (tasks/plan.md, Task 1.4 onwards).

GET /research/participants (V1.11): one row per participant. Three participants
cover the three pre-test states; the completed one has two sessions, the last of
them projected from the fixture with two answered S5 trials (one correct).

GET /research/sessions (V1.1): one row per session, filters combined. A projected
STATIC session and an adaptive one with no events at all.

GET /research/sessions/{id}/timeline (V1.3): the eight lanes on the same two sessions.

GET /research/sessions/{id}/trials (V1.4): trial_timeline() rows with the decision
details of the inspector, on the adaptive S7.

GET /research/sessions/{id}/adaptations (V1.5): the decisions of the adaptive S7, with or
without NO_CHANGE.

GET /research/sessions/{id}/plan (V1.6): planned against executed trials per block, on
the projected fixture, then cut by hand.

GET /research/sessions/{id}/export.csv (V1.9): the trials and adaptations as CSV, headers
equal to the API fields, NULL as an empty cell.

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
        assert [body["head_away_count"], body["head_away_ms"]] == list((await _exec(
            "SELECT sum(head_away_count), sum(head_away_ms) FROM trial_timeline(:s, 3) "
            "WHERE response_time_ms IS NOT NULL", s=sid))[0])


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


@pytest.mark.asyncio
async def test_timeline_lanes_adaptive():
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    await adaptive._exec("DELETE FROM participants WHERE external_code = :c", c=adaptive.PARTICIPANT_CODE)
    sid = await adaptive._new_session()
    await adaptive._insert_and_project(sid, adaptive._events())
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            body = (await client.get(f"/research/sessions/{sid}/timeline")).json()
        assert body["session_end_ms"] == 14600                                   # last event
        assert body["states"] == [{"state": "S7_EXPERIMENTAL_RETRIEVAL", "start_ms": 0, "end_ms": None}]
        assert body["environment"] is None                                       # no ENVIRONMENT_APPLIED
        # LAL from the state entry, then the applied change MEDIUM -> HIGH.
        assert body["assistance"] == [{"level": "MEDIUM", "start_ms": 0, "end_ms": 9600},
                                      {"level": "HIGH", "start_ms": 9600, "end_ms": None}]
        assert body["trials"] == [
            {"trial_id": "S7-001", "block_state": "S7_EXPERIMENTAL_RETRIEVAL", "start_ms": 1000, "end_ms": 4500, "is_correct": True},
            {"trial_id": "S7-002", "block_state": "S7_EXPERIMENTAL_RETRIEVAL", "start_ms": 6000, "end_ms": 9500, "is_correct": False},
            {"trial_id": "S7-003", "block_state": "S7_EXPERIMENTAL_RETRIEVAL", "start_ms": 11000, "end_ms": 14500, "is_correct": True},
        ]
        # Lanes 5-8. No hint was requested; S7-003 started with the proactive cue.
        assert body["hints"] == [{"ms": 11000, "trial_id": "S7-003", "proactive": True}]
        assert body["peripherals"] is None                                       # no PERIPHERAL_EVENT
        onsets = await adaptive._exec("SELECT kind, onset_elapsed_ms, duration_ms FROM distractor_interactions "
                                      "WHERE session_id = :s ORDER BY onset_elapsed_ms", s=sid)
        assert [(d["kind"], d["start_ms"], d["duration_ms"]) for d in body["distractors"]] == [tuple(r) for r in onsets]
        assert [d["kind"] for d in body["distractors"]] == ["DWELL", "ORIENTING"]
        assert body["head_away"] is None                                         # no HEAD_AWAY
        # Changes only (NO_CHANGE is in the V1.5 table). Cooldown until trial 5, which never
        # ran: the band ends with the block's last trial.
        assert body["adaptations"] == [{
            "decision_id": "d-S7-002", "trial_id": "S7-002", "decided_ms": 8000, "action": "CHANGE_ASSISTANCE",
            "dimension": "LAL", "from_level": "MEDIUM", "to_level": "HIGH", "learner_state": "OVERLOADED",
            "unity_result": "APPLIED", "skip_reason": None, "result_ms": 9600, "cooldown_until_ms": 14500,
            "outcome": None,
        }]
    finally:
        await adaptive._exec("DELETE FROM participants WHERE external_code = :c", c=adaptive.PARTICIPANT_CODE)


@pytest.mark.asyncio
async def test_timeline_lanes_static(client):
    pid = await _register(client, CODES[0])
    sid = await _projected_session(pid)
    body = (await client.get(f"/research/sessions/{sid}/timeline")).json()
    env = await _exec("SELECT esl::text, elapsed_ms, valid_to_ms FROM v_environment_intervals "
                      "WHERE session_id = :s ORDER BY elapsed_ms", s=sid)
    assert [tuple(e.values()) for e in body["environment"]] == [tuple(r) for r in env]
    assert len(body["trials"]) == await _scalar("SELECT count(*) FROM trials WHERE session_id = :s", s=sid)
    assert len(body["states"]) == await _scalar("SELECT count(*) FROM session_states WHERE session_id = :s", s=sid)
    empty = str(await _scalar("INSERT INTO experiment_sessions (participant_id, condition) VALUES (:p, 'STATIC') "
                              "RETURNING id", p=pid))
    body = (await client.get(f"/research/sessions/{empty}/timeline")).json()
    assert body == {"session_end_ms": None, "states": None, "environment": None, "assistance": None, "trials": None,
                    "hints": None, "peripherals": None, "distractors": None, "head_away": None, "adaptations": None}
    assert (await client.get("/research/sessions/00000000-0000-0000-0000-000000000000/timeline")).status_code == 404


@pytest.mark.asyncio
async def test_trials_rows_adaptive():
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    await adaptive._exec("DELETE FROM participants WHERE external_code = :c", c=adaptive.PARTICIPANT_CODE)
    sid = await adaptive._new_session()
    await adaptive._insert_and_project(sid, adaptive._events())
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            rows = (await client.get(f"/research/sessions/{sid}/trials")).json()
            assert (await client.get(f"/research/sessions/{sid}/trials", params={"window_n": 9})).status_code == 422
            assert (await client.get("/research/sessions/00000000-0000-0000-0000-000000000000/trials")).status_code == 404
        assert [r["trial_id"] for r in rows] == ["S7-001", "S7-002", "S7-003"]
        tl = await adaptive._exec("SELECT trial_id, window_n, window_accuracy::float, response_time_ms, idle_ms, "
                                  "distractor_dwell_ms FROM trial_timeline(:s, 3) ORDER BY started_elapsed_ms", s=sid)
        assert [(r["trial_id"], r["window_n"], r["window_accuracy"], r["response_time_ms"], r["idle_ms"],
                 r["distractor_dwell_ms"]) for r in rows] == [tuple(x) for x in tl]
        # Not recorded in this session: NULL, not trial_timeline()'s COALESCE zero (data-contract.md).
        assert {(r["head_away_ms"], r["head_away_count"], r["peripheral_event_count"]) for r in rows} == {(None, None, None)}
        no_change, change, none = rows
        assert (no_change["decision_action"], no_change["explanation"]) == ("NO_CHANGE", "Stable at the current levels.")
        assert {k: change[k] for k in ["decision_action", "dimension", "from_level", "to_level", "unity_result",
                                         "applied_before_trial_id", "cooldown_until_trial_id", "outcome", "indicators"]} == {
            "decision_action": "CHANGE_ASSISTANCE", "dimension": "LAL", "from_level": "MEDIUM", "to_level": "HIGH",
            "unity_result": "APPLIED", "applied_before_trial_id": "S7-003", "cooldown_until_trial_id": None,
            "outcome": None, "indicators": {"n": 3},
        }
        assert change["cooldown_until_trial"] == 5                                # trial 5 never ran
        assert none["decision_action"] is None and none["explanation"] is None
        assert none["cue_trigger"] == "PROACTIVE"
        assert [r["completed_elapsed_ms"] for r in rows] == [4500, 9500, 14500]   # the Answer column's "Not completed"
    finally:
        await adaptive._exec("DELETE FROM participants WHERE external_code = :c", c=adaptive.PARTICIPANT_CODE)


@pytest.mark.asyncio
async def test_trials_window_changes_the_aggregates():
    """Five S7 trials, every other one wrong: the window size shows in window_n and the accuracy."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    await adaptive._exec("DELETE FROM participants WHERE external_code = :c", c=adaptive.PARTICIPANT_CODE)
    sid = await adaptive._new_session()
    events = [adaptive._ev("STATE_ENTERED", 0, transition_sound_lead_ms=None)]
    for i in range(5):
        events += adaptive._trial(f"S7-00{i + 1}", i + 1, 1000 + 5000 * i, correct=i % 2 == 0)
    await adaptive._insert_and_project(sid, events)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            got = {n: (await client.get(f"/research/sessions/{sid}/trials", params={"window_n": n})).json() for n in (3, 5)}
        for n, rows in got.items():
            expected = await adaptive._exec("SELECT window_n, window_accuracy::float FROM trial_timeline(:s, :n) "
                                            "ORDER BY started_elapsed_ms", s=sid, n=n)
            assert [(r["window_n"], r["window_accuracy"]) for r in rows] == [tuple(x) for x in expected]
        assert [r["window_n"] for r in got[3]][-1] == 3 and [r["window_n"] for r in got[5]][-1] == 5
    finally:
        await adaptive._exec("DELETE FROM participants WHERE external_code = :c", c=adaptive.PARTICIPANT_CODE)


@pytest.mark.asyncio
async def test_adaptations_rows():
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    await adaptive._exec("DELETE FROM participants WHERE external_code = :c", c=adaptive.PARTICIPANT_CODE)
    sid = await adaptive._new_session()
    await adaptive._insert_and_project(sid, adaptive._events())
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            changes = (await client.get(f"/research/sessions/{sid}/adaptations")).json()
            every = (await client.get(f"/research/sessions/{sid}/adaptations", params={"include_no_change": True})).json()
            assert (await client.get("/research/sessions/00000000-0000-0000-0000-000000000000/adaptations")).status_code == 404
        assert [r["trial_id"] for r in changes] == ["S7-002"]
        assert [r["trial_id"] for r in every] == ["S7-001", "S7-002"]                  # every decision, in time order
        assert len(every) == await adaptive._scalar("SELECT count(*) FROM adaptation_decisions WHERE session_id = :s", s=sid)
        assert {k: changes[0][k] for k in [
            "decision_id", "learner_state", "cause", "confidence", "action", "dimension", "from_level", "to_level",
            "proactive_cues", "reason_code", "explanation", "unity_result", "skip_reason", "applied_before_trial_id",
            "cooldown_until_trial", "cooldown_until_trial_id", "outcome", "estimator_version", "rules_version",
            "indicators", "thresholds"]} == {
            "decision_id": "d-S7-002", "learner_state": "OVERLOADED", "cause": None, "confidence": pytest.approx(0.8),
            "action": "CHANGE_ASSISTANCE", "dimension": "LAL", "from_level": "MEDIUM", "to_level": "HIGH",
            "proactive_cues": True, "reason_code": "OVERLOADED", "explanation": "Raised the assistance from MEDIUM to HIGH.",
            "unity_result": "APPLIED", "skip_reason": None, "applied_before_trial_id": "S7-003",
            "cooldown_until_trial": 5, "cooldown_until_trial_id": None, "outcome": None,
            "estimator_version": "behavior-v1", "rules_version": "rules-v1",
            "indicators": {"n": 3}, "thresholds": {"rules": {"cooldown_trials": 3}},
        }
    finally:
        await adaptive._exec("DELETE FROM participants WHERE external_code = :c", c=adaptive.PARTICIPANT_CODE)


@pytest.mark.asyncio
async def test_plan_complete_then_cut(client):
    pid = await _register(client, CODES[0])
    sid = await _projected_session(pid)
    url = f"/research/sessions/{sid}/plan"
    body = (await client.get(url)).json()
    seed = await _scalar("SELECT block_seed FROM trial_blocks WHERE session_id = :s", s=sid)
    entered = await _scalar("SELECT max(entered_elapsed_ms) FROM session_states WHERE session_id = :s", s=sid)
    assert body == {
        "last_state": "S7_EXPERIMENTAL_RETRIEVAL", "last_state_ms": entered,
        "blocks": [{
            "block_state": "S2_VR_TUTORIAL", "kanji_set": body["blocks"][0]["kanji_set"], "block_seed": str(seed),
            "planned": 2, "started": 2, "completed": 2, "min_lag_requested": 2, "min_lag_achieved": 1,
            "kanji_repeats": True,
            "trials": [{"trial_id": "S2-001", "status": "COMPLETED"}, {"trial_id": "S2-002", "status": "COMPLETED"}],
        }],
    }
    # Cut: S2-002 started with no completion, then never shown at all.
    await _exec("UPDATE trials SET completed_event_id = NULL, completed_elapsed_ms = NULL "
                "WHERE session_id = :s AND trial_id = 'S2-002'", s=sid)
    block = (await client.get(url)).json()["blocks"][0]
    assert (block["planned"], block["started"], block["completed"]) == (2, 2, 1)
    assert [t["status"] for t in block["trials"]] == ["COMPLETED", "STARTED"]
    await _exec("DELETE FROM trials WHERE session_id = :s AND trial_id = 'S2-002'", s=sid)
    block = (await client.get(url)).json()["blocks"][0]
    assert (block["planned"], block["started"], block["completed"]) == (2, 1, 1)
    assert [t["status"] for t in block["trials"]] == ["COMPLETED", "NEVER_SHOWN"]
    # Unity sends -1 when the block repeats no kanji: no lag to measure, not "not recorded".
    await _exec("UPDATE trial_blocks SET min_lag_achieved = -1 WHERE session_id = :s", s=sid)
    block = (await client.get(url)).json()["blocks"][0]
    assert (block["min_lag_achieved"], block["kanji_repeats"]) == (None, False)
    assert (await client.get("/research/sessions/00000000-0000-0000-0000-000000000000/plan")).status_code == 404


@pytest.mark.asyncio
async def test_export_csv():
    import csv
    import io
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.schemas.research import ResearchAdaptation, ResearchTrial

    await adaptive._exec("DELETE FROM participants WHERE external_code = :c", c=adaptive.PARTICIPANT_CODE)
    sid = await adaptive._new_session()
    await adaptive._insert_and_project(sid, adaptive._events())
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            trials = await client.get(f"/research/sessions/{sid}/export.csv", params={"kind": "trials"})
            adaptations = await client.get(f"/research/sessions/{sid}/export.csv", params={"kind": "adaptations"})
            api = (await client.get(f"/research/sessions/{sid}/trials")).json()
            assert (await client.get(f"/research/sessions/{sid}/export.csv", params={"kind": "events"})).status_code == 422
            assert (await client.get("/research/sessions/00000000-0000-0000-0000-000000000000/export.csv",
                                     params={"kind": "trials"})).status_code == 404
        assert trials.headers["content-type"].startswith("text/csv")
        assert trials.headers["content-disposition"] == f'attachment; filename="session-{str(sid)[:8]}-trials.csv"'
        rows = list(csv.DictReader(io.StringIO(trials.text)))
        assert list(rows[0]) == list(ResearchTrial.model_fields)                 # headers are the API fields
        assert [r["trial_id"] for r in rows] == [r["trial_id"] for r in api]
        first = rows[0]
        assert first["head_away_ms"] == ""                                       # NULL: empty, never 0
        assert first["is_correct"] == "true" and first["idle_ms"] == "500"
        assert first["indicators"] == '{"n": 3}'                                 # stored JSON stays JSON
        decisions = list(csv.DictReader(io.StringIO(adaptations.text)))
        assert list(decisions[0]) == list(ResearchAdaptation.model_fields)
        assert [d["trial_id"] for d in decisions] == ["S7-001", "S7-002"]       # NO_CHANGE included
        assert decisions[0]["unity_result"] == "" and decisions[1]["unity_result"] == "APPLIED"
    finally:
        await adaptive._exec("DELETE FROM participants WHERE external_code = :c", c=adaptive.PARTICIPANT_CODE)


def test_research_router_is_read_only():
    """Skill rule 1: the /research router has GET endpoints only."""
    from app.main import app
    research = [r for r in app.routes if getattr(r, "path", "").startswith("/research")]
    assert research
    for route in research:
        assert route.methods <= {"GET", "HEAD"}, route.path

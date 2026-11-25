"""
Read-side SQL for the research portal (migration 0006, tasks/plan.md Task 0.3):
v_session_overview, v_projection_errors and the verify_*_fn() ports of
database/verify_*.sql.

Each function returns no rows on the projected fixture session (the one
test_projection.py uses, which its scripts pass) and finds a discrepancy seeded
by hand in the projected tables. Needs `alembic upgrade head` and
database/seed_kanji_items.sql, like test_projection.py. The rows belong to the
participant RESEARCH_SQL_TEST and are deleted at the end.
"""

import json

import pytest
import pytest_asyncio

from tests.test_projection import FIXTURE, _exec, _insert_and_project, _scalar

PARTICIPANT_CODE = "RESEARCH_SQL_TEST"
FUNCTIONS = ["verify_projection_fn", "verify_adaptation_fn", "verify_trials_fn",
             "verify_assembly_fn", "verify_reproducibility_fn"]


async def _new_session(participant) -> str:
    return await _scalar("INSERT INTO experiment_sessions (participant_id, condition) "
                         "VALUES (:p, 'STATIC') RETURNING id", p=participant)


async def _projected_session(participant) -> str:
    sid = await _new_session(participant)
    events = json.loads(FIXTURE.read_text(encoding="utf-8"))["events"]
    for ev in events:
        if ev["event_type"] == "HINT_REQUESTED":
            ev["payload"]["hint_type"] = []    # spec 9.1: LAL LOW grants no cue, so verify_trials_v1.sql passes
        if ev["event_type"] == "ASSEMBLY_COMPLETED":
            ev["payload"]["forced_by_researcher"] = True    # it places 1 of its 2 segments right
    await _insert_and_project(sid, events)
    return sid


async def _checks(fn: str, sid) -> list[tuple[str, str]]:
    rows = await _exec(f'SELECT "check", detail FROM {fn}(:s)', s=sid)
    return [(r[0], r[1]) for r in rows]


async def _overview(sid) -> dict:
    rows = await _exec("SELECT * FROM v_session_overview WHERE session_id = :s", s=sid)
    return dict(rows[0]._mapping)


@pytest_asyncio.fixture
async def participant():
    if await _scalar("SELECT to_regprocedure('verify_projection_fn(uuid)') IS NULL"):
        pytest.fail("migration 0006 not applied: run `alembic upgrade head`")
    if await _scalar("SELECT count(*) FROM kanji_items") == 0:
        pytest.skip("kanji_items is empty: apply database/seed_kanji_items.sql")
    await _exec("DELETE FROM participants WHERE external_code = :c", c=PARTICIPANT_CODE)
    yield await _scalar("INSERT INTO participants (external_code) VALUES (:c) RETURNING id", c=PARTICIPANT_CODE)
    await _exec("DELETE FROM participants WHERE external_code = :c", c=PARTICIPANT_CODE)


@pytest.mark.asyncio
async def test_a_clean_session_passes_every_check(participant):
    first = await _projected_session(participant)
    second = await _projected_session(participant)   # same seed and set: the reproducibility pair
    for sid in (first, second):
        for fn in FUNCTIONS:
            assert await _checks(fn, sid) == [], fn


@pytest.mark.asyncio
async def test_each_function_finds_a_seeded_discrepancy(participant):
    first = await _projected_session(participant)
    sid = await _projected_session(participant)
    trial = await _scalar("SELECT min(trial_id) FROM trials WHERE session_id = :s", s=sid)

    await _exec("DELETE FROM hint_requests WHERE session_id = :s AND trial_id = :t", s=sid, t=trial)
    await _exec("UPDATE trials SET is_correct = NOT is_correct, cue_trigger = 'PROACTIVE', proactive_index = 1, "
                "options = ARRAY(SELECT o FROM unnest(options) o ORDER BY o DESC) "
                "WHERE session_id = :s AND trial_id = :t", s=sid, t=trial)
    await _exec("UPDATE assemblies SET incorrect_attempts = incorrect_attempts + 1 WHERE session_id = :s", s=sid)

    found = {fn: {c for c, _ in await _checks(fn, sid)} for fn in FUNCTIONS}
    assert {"projection/counts", "projection/values"} <= found["verify_projection_fn"]
    assert found["verify_adaptation_fn"] == {"adaptation/static"}
    assert "trials/consistency" in found["verify_trials_fn"]
    assert found["verify_assembly_fn"] == {"assembly/counts"}
    assert found["verify_reproducibility_fn"] == {"reproducibility/trials"}
    assert await _checks("verify_trials_fn", first) == []        # the other session is untouched


@pytest.mark.asyncio
async def test_projection_counts_skip_events_with_a_projection_error(participant):
    # A DUPLICATE run of the F3 evidence sessions: the event made no row and its error is resolved.
    sid = await _projected_session(participant)
    # A re-projection logs errors against events that did project: those still expect their row.
    projected = await _scalar("SELECT min(id) FROM session_events WHERE session_id = :s AND event_type = 'HINT_REQUESTED'", s=sid)
    await _exec("INSERT INTO projection_errors (event_id, session_id, event_type, error_code, resolved_at) "
                "VALUES (:e, :s, 'HINT_REQUESTED', 'DUPLICATE', now())", e=projected, s=sid)
    event = await _scalar("SELECT max(id) FROM session_events WHERE session_id = :s AND event_type = 'HINT_REQUESTED'", s=sid)
    await _exec("DELETE FROM hint_requests WHERE source_event_id = :e", e=event)
    await _exec("INSERT INTO projection_errors (event_id, session_id, event_type, error_code, resolved_at) "
                "VALUES (:e, :s, 'HINT_REQUESTED', 'DUPLICATE', now())", e=event, s=sid)
    assert await _checks("verify_projection_fn", sid) == []

    await _exec("UPDATE projection_errors SET resolved_at = NULL WHERE event_id = :e", e=event)
    assert [c for c, _ in await _checks("verify_projection_fn", sid)] == ["projection/open_error"]
    errors = await _exec("SELECT error_code, session_elapsed_ms FROM v_projection_errors WHERE event_id = :e", e=event)
    payload_ms = await _scalar("SELECT (payload->>'session_elapsed_ms')::numeric::bigint FROM session_events WHERE id = :e", e=event)
    assert [tuple(r) for r in errors] == [("DUPLICATE", payload_ms)]


@pytest.mark.asyncio
async def test_overview_status_counts_and_accuracy(participant):
    projected = await _projected_session(participant)
    empty = await _new_session(participant)
    raw = await _new_session(participant)
    await _exec("INSERT INTO session_events (session_id, event_type, payload) "
                "VALUES (:s, 'TRIAL_STARTED', '{}')", s=raw)

    row = await _overview(projected)
    assert row["projection_status"] == "PROJECTED"
    assert (row["event_count"], row["trial_count"], row["decision_count"], row["open_error_count"]) == (24, 2, 0, 0)
    assert (row["trials_recorded"], row["answers_recorded"], row["decisions_recorded"]) == (True, True, False)
    assert (row["answered"], row["accuracy"]) == (0, None)        # the fixture trials are S2, not S5-S8

    await _exec("UPDATE trials SET block_state = 'S5_STANDARDIZED_LEARNING', is_correct = (trial_id = "
                "(SELECT min(trial_id) FROM trials WHERE session_id = :s)) WHERE session_id = :s", s=projected)
    row = await _overview(projected)
    assert (row["answered"], row["correct"], float(row["accuracy"])) == (2, 1, 0.5)

    row = await _overview(empty)
    assert (row["projection_status"], row["event_count"], row["trials_recorded"]) == ("NO_DATA", 0, False)
    row = await _overview(raw)
    assert (row["projection_status"], row["event_count"], row["trials_recorded"]) == ("NOT_PROJECTED", 1, True)

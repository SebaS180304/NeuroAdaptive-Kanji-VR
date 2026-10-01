"""
Schema v1 projector (F3.4, migration 0002): project_event / project_session.

What MER_Schema_v1.md §6 asks of pytest: one test per projected event_type,
one of idempotence (projecting twice gives the same rows), plus the error
paths of projection_errors and the derived per-trial behaviour.

The events come from tests/fixtures/projection_session.json, a synthetic
session that follows EVENT_CONTRACT.md as of 30 Sep 2026. They are inserted
straight into session_events and projected the way the WebSocket handler
does it (`_project`, one call per event, in arrival order).

Needs: `alembic upgrade head` and database/seed_kanji_items.sql applied to
the database in backend/.env (the same one the other tests use). The rows
created here belong to the participant PROJ_TEST and are deleted at the end
(sessions, events and projected rows go with it by ON DELETE CASCADE).
"""

import json
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import text

from app.api.routes.websocket import _project
from app.db.base import AsyncSessionLocal

FIXTURE = Path(__file__).parent / "fixtures" / "projection_session.json"
PARTICIPANT_CODE = "PROJ_TEST"


async def _exec(sql: str, **params):
    async with AsyncSessionLocal() as db:
        result = await db.execute(text(sql), params)
        rows = result.fetchall() if result.returns_rows else None
        await db.commit()
        return rows


async def _scalar(sql: str, **params):
    rows = await _exec(sql, **params)
    return rows[0][0]


async def _new_session() -> uuid.UUID:
    participant = await _scalar(
        "INSERT INTO participants (external_code) VALUES (:c) "
        "ON CONFLICT (external_code) DO UPDATE SET external_code = EXCLUDED.external_code "
        "RETURNING id",
        c=PARTICIPANT_CODE,
    )
    return await _scalar(
        "INSERT INTO experiment_sessions (participant_id, condition) "
        "VALUES (:p, 'STATIC') RETURNING id",
        p=participant,
    )


async def _insert_and_project(session_id: uuid.UUID, events: list[dict]) -> list[int]:
    """Insert each event and project it in the same transaction, like the handler."""
    ids = []
    for ev in events:
        async with AsyncSessionLocal() as db:
            event_id = (
                await db.execute(
                    text(
                        "INSERT INTO session_events (session_id, event_type, payload) "
                        "VALUES (:s, :t, CAST(:p AS jsonb)) RETURNING id"
                    ),
                    {"s": session_id, "t": ev["event_type"], "p": json.dumps(ev["payload"])},
                )
            ).scalar()
            await _project(db, event_id)
            await db.commit()
        ids.append(event_id)
    return ids


_SNAPSHOT = """
SELECT md5(string_agg(t, '|' ORDER BY t)) FROM (
    SELECT 'ss' || (x.*)::text t FROM session_states x WHERE session_id = :s
    UNION ALL SELECT 'tb' || (x.*)::text FROM trial_blocks x WHERE session_id = :s
    UNION ALL SELECT 'pt' || (x.*)::text FROM planned_trials x WHERE session_id = :s
    UNION ALL SELECT 'tr' || (x.*)::text FROM trials x WHERE session_id = :s
    UNION ALL SELECT 'hr' || (x.*)::text FROM hint_requests x WHERE session_id = :s
    UNION ALL SELECT 'ea' || (x.*)::text FROM environment_applications x WHERE session_id = :s
    UNION ALL SELECT 'pe' || (x.*)::text FROM peripheral_events x WHERE session_id = :s
    UNION ALL SELECT 'ha' || (x.*)::text FROM head_away_episodes x WHERE session_id = :s
    UNION ALL SELECT 'ke' || (x.*)::text FROM kanji_exposures x WHERE session_id = :s
    UNION ALL SELECT 'as' || (x.*)::text FROM assemblies x WHERE session_id = :s
    UNION ALL SELECT 'aa' || (x.*)::text FROM assembly_attempts x WHERE session_id = :s
) q
"""


@pytest_asyncio.fixture
async def projected():
    """The fixture session, inserted and projected live, fresh for each test.

    Function scope on purpose (1 Oct 2026): a module-scoped async fixture
    runs on its own event loop in pytest-asyncio 0.24, while the engine's
    pooled asyncpg connections belong to the loop of conftest.py, and every
    test errored at setup with "attached to a different loop". Re-projecting
    24 events per test costs well under a second."""
    if await _scalar("SELECT to_regclass('public.trials') IS NULL"):
        pytest.skip("migration 0002 not applied: run `alembic upgrade head`")
    if await _scalar("SELECT count(*) FROM kanji_items") == 0:
        pytest.skip("kanji_items is empty: apply database/seed_kanji_items.sql")

    await _exec("DELETE FROM participants WHERE external_code = :c", c=PARTICIPANT_CODE)
    session_id = await _new_session()
    events = json.loads(FIXTURE.read_text(encoding="utf-8"))["events"]
    await _insert_and_project(session_id, events)
    yield session_id
    await _exec("DELETE FROM participants WHERE external_code = :c", c=PARTICIPANT_CODE)


# One row (or column) per projected event type. The fixture has exactly one
# session of each shape, so every expectation is an exact count.
EXPECTED = [
    ("STATE_ENTERED", "SELECT count(*) FROM session_states WHERE session_id = :s", 4),
    ("TRIAL_SEQUENCE_GENERATED", "SELECT count(*) FROM trial_blocks WHERE session_id = :s", 1),
    ("TRIAL_SEQUENCE_GENERATED/sequence", "SELECT count(*) FROM planned_trials WHERE session_id = :s", 2),
    ("TRIAL_STARTED", "SELECT count(*) FROM trials WHERE session_id = :s", 2),
    ("ANSWER_SELECTED", "SELECT count(answer_event_id) FROM trials WHERE session_id = :s", 2),
    ("TRIAL_COMPLETED", "SELECT count(completed_event_id) FROM trials WHERE session_id = :s", 2),
    ("HINT_REQUESTED", "SELECT count(*) FROM hint_requests WHERE session_id = :s", 2),
    ("ENVIRONMENT_APPLIED", "SELECT count(*) FROM environment_applications WHERE session_id = :s", 2),
    ("PERIPHERAL_EVENT", "SELECT count(*) FROM peripheral_events WHERE session_id = :s", 1),
    ("HEAD_AWAY", "SELECT count(*) FROM head_away_episodes WHERE session_id = :s", 1),
    ("HEAD_RETURNED", "SELECT count(returned_event_id) FROM head_away_episodes WHERE session_id = :s", 1),
    ("KANJI_EXPOSED", "SELECT count(*) FROM kanji_exposures WHERE session_id = :s", 1),
    ("ASSEMBLY_SEGMENT_PLACED", "SELECT count(*) FROM assembly_attempts WHERE session_id = :s", 2),
    ("ASSEMBLY_COMPLETED", "SELECT count(*) FROM assemblies WHERE session_id = :s", 1),
    ("(no errors)", "SELECT count(*) FROM projection_errors WHERE session_id = :s", 0),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("event_type,sql,expected", EXPECTED, ids=[e[0] for e in EXPECTED])
async def test_each_event_type_is_projected(projected, event_type, sql, expected) -> None:
    assert await _scalar(sql, s=projected) == expected


@pytest.mark.asyncio
async def test_values_follow_the_payload(projected) -> None:
    s = projected
    # §5.9: the stage sound lead travels to session_states; null on S1
    leads = await _exec(
        "SELECT state::text, transition_sound_lead_ms, exited_elapsed_ms FROM session_states "
        "WHERE session_id = :s ORDER BY visit_seq", s=s)
    assert leads[0] == ("S1_WELCOME_ORIENTATION", None, 7500)
    assert leads[1][1] == 3507

    t1 = (await _exec(
        "SELECT is_correct, response_time_ms, hint_count, cues_presented, result_sound, "
        "result_sound_offset_ms, card_animation, idle_ms, idle_min_ms, lal::text "
        "FROM trials WHERE session_id = :s AND trial_id = 'S2-001'", s=s))[0]
    assert t1 == (True, 4000, 2, ["TARGET_READING_AUDIO"], "CORRECT", 601, "CORRECT_POP", 1200, 1000, "LOW")

    hints = await _exec(
        "SELECT request_seq, cues_granted FROM hint_requests WHERE session_id = :s ORDER BY request_seq", s=s)
    assert hints == [(1, []), (2, ["TARGET_READING_AUDIO"])]  # §5.5: an empty grant is still a row

    ep = (await _exec(
        "SELECT onset_elapsed_ms, returned_elapsed_ms, limit_crossed, return_reason, yaw_limit_deg "
        "FROM head_away_episodes WHERE session_id = :s", s=s))[0]
    assert ep == (10000, 17000, "YAW", "RETURNED", 40.0)


@pytest.mark.asyncio
async def test_head_away_is_split_by_response_window(projected) -> None:
    # The 7 s episode (10.0-17.0 s) crosses two trials: 3 s fall in the
    # response window of S2-001 (9-13 s) and 1 s in S2-002 (16-19 s).
    rows = await _exec(
        "SELECT trial_id, head_away_ms, peripheral_event_count FROM v_trial_behavior "
        "WHERE session_id = :s ORDER BY trial_id", s=projected)
    assert rows == [("S2-001", 3000, 0), ("S2-002", 1000, 0)]


@pytest.mark.asyncio
async def test_trial_timeline_window(projected) -> None:
    rows = await _exec(
        "SELECT trial_id, is_primary_analysis, env_profile, window_n, window_accuracy::float8, "
        "window_rt_mean::float8, window_head_away_ms FROM trial_timeline(:s)", s=projected)
    assert [r[0] for r in rows] == ["S2-001", "S2-002"]
    assert rows[1][1] is False                      # S2 is tutorial, spec §12
    assert rows[1][2] == "LOW_Studio"
    assert rows[1][3:] == (2, pytest.approx(0.5), pytest.approx(3500.0), 4000)


@pytest.mark.asyncio
async def test_projection_is_idempotent(projected) -> None:
    s = projected
    before = await _scalar(_SNAPSHOT, s=s)
    # live again, event by event ...
    assert await _scalar(
        "SELECT bool_and(project_event(id)) FROM "
        "(SELECT id FROM session_events WHERE session_id = :s ORDER BY id) q", s=s)
    assert await _scalar(_SNAPSHOT, s=s) == before
    # ... and the backfill path, twice
    assert await _scalar("SELECT project_session(:s)", s=s) == 0
    assert await _scalar("SELECT project_session(:s)", s=s) == 0
    assert await _scalar(_SNAPSHOT, s=s) == before


def _ev(event_type: str, ms, **fields) -> dict:
    payload = {"schema_version": 1, "state": "S7_EXPERIMENTAL_RETRIEVAL",
               "session_elapsed_ms": ms, "esl": "LOW", "lal": "LOW"}
    payload.update(fields)
    return {"event_type": event_type, "payload": payload}


_OPTS = ["KANJI_YAMA", "KANJI_KAWA", "KANJI_HI", "KANJI_KI"]


def _started(trial_id: str, seq: int, ms: int, **over) -> dict:
    f = dict(trial_id=trial_id, trial_sequence=seq, trial_type="T1_MEANING_TO_KANJI",
             kanji_id="KANJI_YAMA", options=_OPTS, correct_option="KANJI_YAMA", hint_available=False)
    f.update(over)
    return _ev("TRIAL_STARTED", ms, **f)


@pytest.mark.asyncio
async def test_failures_are_logged_and_events_kept(projected) -> None:
    session_id = await _new_session()
    events = [
        _ev("ANSWER_SELECTED", 100, trial_id="S7-001", selected_option="KANJI_YAMA",
            is_correct=True, response_time_ms=10),                                      # ORPHAN_EVENT
        {"event_type": "STATE_ENTERED",
         "payload": {"schema_version": 1, "state": "S1_WelcomeOrientation",
                     "session_elapsed_ms": 0, "esl": "LOW", "lal": "OFF"}},             # UNKNOWN_ENUM
        _started("S7-001", 1, 200, hint_available=None),                                # MISSING_FIELD
        _started("S7-002", 2, 300, kanji_id="KANJI_NOPE"),                              # FK_VIOLATION
        _started("S7-003", 3, 400),                                                     # ok
        _ev("ANSWER_SELECTED", 500, trial_id="S7-003", selected_option="KANJI_YAMA",
            is_correct=True, response_time_ms=100),                                     # ok
        _ev("ANSWER_SELECTED", 600, trial_id="S7-003", selected_option="KANJI_KI",
            is_correct=False, response_time_ms=200),                                    # DUPLICATE
        _ev("TRIAL_COMPLETED", 700, trial_id="S7-003", hint_count=0, feedback_shown=False,
            feedback_audio_ms=450, result_sound="NONE", card_animation="NONE"),         # CHECK_VIOLATION (§5.9)
        _ev("HEAD_RETURNED", 800, episode=9, duration_ms=10),                           # ORPHAN_EVENT
        _started("S7-003", 3, 900),                                                     # DUPLICATE
        _ev("PERIPHERAL_EVENT", "abc", event_index=0, object_name="x", duration_ms=1),  # BAD_VALUE
    ]
    ids = await _insert_and_project(session_id, events)

    codes = await _exec(
        "SELECT event_id, error_code FROM projection_errors WHERE session_id = :s ORDER BY event_id",
        s=session_id)
    assert [c for _, c in codes] == [
        "ORPHAN_EVENT", "UNKNOWN_ENUM", "MISSING_FIELD", "FK_VIOLATION", "DUPLICATE",
        "CHECK_VIOLATION", "ORPHAN_EVENT", "DUPLICATE", "BAD_VALUE"]
    # every event is stored, projected or not (contract §7)
    assert await _scalar("SELECT count(*) FROM session_events WHERE session_id = :s",
                         s=session_id) == len(ids)
    # the first answer wins; the duplicate did not overwrite it
    assert (await _exec("SELECT selected_option, answer_event_id FROM trials "
                        "WHERE session_id = :s", s=session_id)) == [("KANJI_YAMA", ids[5])]

"""
Migration 0003 (F5a): projection of the adaptation loop and of D5 / D9.

One synthetic S7 of three trials, inserted and projected the way the
WebSocket handler does it (`_project`, one call per event, in arrival order):

- S7-001 answered with idle on ANSWER_SELECTED (§2.2), a DWELL during its
  response and an ORIENTING during its feedback (counts for S7-002, like the
  estimator does), NO_CHANGE decision;
- S7-002 decided CHANGE_ASSISTANCE MEDIUM -> HIGH, applied before S7-003;
- S7-003 with the proactive cue (D9, index 1), and a TIMEOUT skip with no
  decision id.

Needs: `alembic upgrade head` (0003) and database/seed_kanji_items.sql, like
tests/test_projection.py. Rows belong to the participant PROJ0003_TEST and
are deleted at the end.
"""

import json
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text

from app.api.routes.websocket import _project
from app.db.base import AsyncSessionLocal

PARTICIPANT_CODE = "PROJ0003_TEST"
S7 = "S7_EXPERIMENTAL_RETRIEVAL"
OPTS = ["KANJI_YAMA", "KANJI_KAWA", "KANJI_HI", "KANJI_KI"]


async def _exec(sql: str, **params):
    async with AsyncSessionLocal() as db:
        result = await db.execute(text(sql), params)
        rows = result.fetchall() if result.returns_rows else None
        await db.commit()
        return rows


async def _scalar(sql: str, **params):
    return (await _exec(sql, **params))[0][0]


async def _new_session() -> uuid.UUID:
    participant = await _scalar(
        "INSERT INTO participants (external_code) VALUES (:c) "
        "ON CONFLICT (external_code) DO UPDATE SET external_code = EXCLUDED.external_code RETURNING id",
        c=PARTICIPANT_CODE)
    return await _scalar(
        "INSERT INTO experiment_sessions (participant_id, condition) "
        "VALUES (:p, 'BEHAVIOR_ADAPTIVE') RETURNING id", p=participant)


async def _insert_and_project(session_id: uuid.UUID, events: list[dict]) -> list[int]:
    ids = []
    for ev in events:
        async with AsyncSessionLocal() as db:
            event_id = (await db.execute(
                text("INSERT INTO session_events (session_id, event_type, payload) "
                     "VALUES (:s, :t, CAST(:p AS jsonb)) RETURNING id"),
                {"s": session_id, "t": ev["event_type"], "p": json.dumps(ev["payload"])},
            )).scalar()
            await _project(db, event_id)
            await db.commit()
        ids.append(event_id)
    return ids


def _ev(event_type: str, ms: int, lal: str = "MEDIUM", trial: tuple | None = None, **fields) -> dict:
    payload = {"schema_version": 1, "state": S7, "session_elapsed_ms": ms, "esl": "MEDIUM", "lal": lal}
    if trial:
        tid, seq = trial
        payload.update(trial_id=tid, trial_sequence=seq, trial_type="T1_MEANING_TO_KANJI", kanji_id="KANJI_YAMA")
    payload.update(fields)
    return {"event_type": event_type, "payload": payload}


def _trial(tid: str, seq: int, t0: int, lal: str = "MEDIUM", correct: bool = True, **completed) -> list[dict]:
    tr = (tid, seq)
    return [
        _ev("TRIAL_STARTED", t0, lal, tr, options=OPTS, correct_option="KANJI_YAMA", hint_available=True),
        _ev("ANSWER_SELECTED", t0 + 2000, lal, tr, selected_option="KANJI_YAMA" if correct else "KANJI_KI",
            is_correct=correct, response_time_ms=2000, timed_out=False,
            idle_ms=500, idle_episodes=1, idle_longest_ms=500),
        _ev("TRIAL_COMPLETED", t0 + 3500, lal, tr, is_correct=correct, response_time_ms=2000, hint_count=0,
            cues_presented=[], feedback_shown=True, feedback_audio_source="NONE", feedback_audio_ms=0,
            result_sound="NONE", card_animation="NONE", **completed),
    ]


def _decision(tid: str, seq: int, ms: int, action: str = "NO_CHANGE", **f) -> dict:
    base = dict(source="BACKEND", decision_id=f"d-{tid}", trial_id=tid, trial_sequence=seq,
                trial_type="T1_MEANING_TO_KANJI", kanji_id="KANJI_YAMA", action=action,
                dimension=None, from_level=None, to_level=None, proactive_cues=False,
                learner_state="STABLE", cause=None, confidence=1.0, reason_code="STABLE",
                explanation="Stable at the current levels.", cooldown_until_trial=None,
                decision_latency_ms=8.5, estimator_version="behavior-v1", rules_version="rules-v1",
                evidence=[], indicators={"n": 3}, thresholds={"rules": {"cooldown_trials": 3}})
    base.update(f)
    return _ev("ADAPTATION_DECISION", ms, **base)


def _distractor(kind: str, ms: int, duration: int, index: int | None = None) -> dict:
    return _ev("DISTRACTOR_INTERACTION", ms, kind=kind, object_name="WallClock_T3", object_group="PROP",
               onset_offset_ms=-duration, duration_ms=duration, peripheral_event_index=index,
               head_turn_deg=12.0, box_distance_deg=0.0 if kind == "DWELL" else None,
               dwell_min_ms=1000, dwell_break_ms=200, box_margin_yaw_deg=3.0, box_margin_pitch_deg=6.0,
               orienting_min_deg=10.0, orienting_window_ms=2000)


def _events() -> list[dict]:
    t1, t2, t3 = _trial("S7-001", 1, 1000), _trial("S7-002", 2, 6000, correct=False), \
        _trial("S7-003", 3, 11000, lal="HIGH", cue_trigger="PROACTIVE", proactive_index=1)
    return [
        _ev("STATE_ENTERED", 0, transition_sound_lead_ms=None),
        t1[0], _distractor("DWELL", 2500, 1200), t1[1],
        _decision("S7-001", 1, 3000),
        _distractor("ORIENTING", 3800, 600, index=1),          # in the feedback of S7-001
        t1[2],
        t2[0], t2[1],
        _decision("S7-002", 2, 8000, action="CHANGE_ASSISTANCE", dimension="LAL", from_level="MEDIUM",
                  to_level="HIGH", proactive_cues=True, learner_state="OVERLOADED", confidence=0.8,
                  reason_code="OVERLOADED", explanation="Raised the assistance from MEDIUM to HIGH.",
                  cooldown_until_trial=5, evidence=["slow_errors"]),
        t2[2],
        _ev("ADAPTATION_APPLIED", 9600, lal="HIGH", decision_id="d-S7-002", decision_trial_id="S7-002",
            applied_before_trial_id="S7-003", dimension="LAL", from_level="MEDIUM", to_level="HIGH",
            proactive_cues=True, waited_ms=0),
        t3[0], t3[1], t3[2],
        _ev("ADAPTATION_SKIPPED", 14600, lal="HIGH", decision_id=None, decision_trial_id="S7-003",
            reason="TIMEOUT", dimension=None, to_level=None, waited_ms=300),
    ]


@pytest.fixture(autouse=True)
def _clean_test_participants():
    """Overrides the conftest fixture (it cleans other participants)."""
    yield


@pytest_asyncio.fixture
async def session():
    if await _scalar("SELECT to_regclass('public.adaptation_decisions') IS NULL"):
        pytest.skip("migration 0003 not applied: run `alembic upgrade head`")
    if await _scalar("SELECT count(*) FROM kanji_items") == 0:
        pytest.skip("kanji_items is empty: apply database/seed_kanji_items.sql")
    await _exec("DELETE FROM participants WHERE external_code = :c", c=PARTICIPANT_CODE)
    sid = await _new_session()
    await _insert_and_project(sid, _events())
    yield sid
    await _exec("DELETE FROM participants WHERE external_code = :c", c=PARTICIPANT_CODE)


@pytest.mark.asyncio
async def test_no_projection_errors(session) -> None:
    rows = await _exec("SELECT event_type, error_code, detail FROM projection_errors WHERE session_id = :s",
                       s=session)
    assert rows == []


@pytest.mark.asyncio
async def test_decisions_and_applications(session) -> None:
    rows = await _exec(
        "SELECT trial_id, action, dimension, from_level::text, to_level::text, proactive_cues, "
        "unity_result, skip_reason, applied_before_trial_id FROM v_adaptations "
        "WHERE session_id = :s ORDER BY trial_id", s=session)
    assert rows == [
        ("S7-001", "NO_CHANGE", None, None, None, False, None, None, None),
        ("S7-002", "CHANGE_ASSISTANCE", "LAL", "MEDIUM", "HIGH", True, "APPLIED", None, "S7-003"),
    ]
    skip = await _exec("SELECT result, decision_id, decision_trial_id, skip_reason FROM adaptation_applications "
                       "WHERE session_id = :s AND result = 'SKIPPED'", s=session)
    assert skip == [("SKIPPED", None, "S7-003", "TIMEOUT")]   # a TIMEOUT skip needs no decision row


@pytest.mark.asyncio
async def test_trial_fields_d9_and_idle_from_the_answer(session) -> None:
    rows = await _exec("SELECT trial_id, cue_trigger, proactive_index, idle_ms FROM trials "
                       "WHERE session_id = :s ORDER BY trial_id", s=session)
    assert rows == [("S7-001", None, None, 500), ("S7-002", None, None, 500), ("S7-003", "PROACTIVE", 1, 500)]


@pytest.mark.asyncio
async def test_trial_timeline_new_columns(session) -> None:
    rows = await _exec(
        "SELECT trial_id, distractor_dwell_ms, dwell_count, orienting_count, learner_state, decision_action, "
        "adaptation_result, cue_trigger, proactive_index FROM trial_timeline(:s)", s=session)
    assert rows == [
        ("S7-001", 1200, 1, 0, "STABLE", "NO_CHANGE", None, None, None),
        # the ORIENTING arrived during the feedback of S7-001: it counts for S7-002 (trials.py)
        ("S7-002", 0, 0, 1, "OVERLOADED", "CHANGE_ASSISTANCE", "APPLIED", None, None),
        ("S7-003", 0, 0, 0, None, None, "SKIPPED", "PROACTIVE", 1),
    ]


@pytest.mark.asyncio
async def test_outcome_orphan_is_logged(session) -> None:
    await _insert_and_project(session, [
        _ev("ADAPTATION_OUTCOME", 20000, decision_id="d-S7-002", outcome="POSITIVE"),
        _ev("ADAPTATION_OUTCOME", 20100, decision_id="d-NOPE", outcome="NEUTRAL"),
    ])
    assert await _scalar("SELECT outcome FROM adaptation_decisions WHERE session_id = :s AND trial_id = 'S7-002'",
                         s=session) == "POSITIVE"
    assert [r[0] for r in await _exec("SELECT error_code FROM projection_errors WHERE session_id = :s",
                                      s=session)] == ["ORPHAN_EVENT"]


@pytest.mark.asyncio
async def test_projection_is_idempotent(session) -> None:
    snap = """
    SELECT md5(string_agg(t, '|' ORDER BY t)) FROM (
        SELECT 'tr' || (x.*)::text t FROM trials x WHERE session_id = :s
        UNION ALL SELECT 'ad' || (x.*)::text FROM adaptation_decisions x WHERE session_id = :s
        UNION ALL SELECT 'aa' || (x.*)::text FROM adaptation_applications x WHERE session_id = :s
        UNION ALL SELECT 'di' || (x.*)::text FROM distractor_interactions x WHERE session_id = :s) q"""
    before = await _scalar(snap, s=session)
    assert await _scalar("SELECT project_session(:s)", s=session) == 0
    assert await _scalar("SELECT project_session(:s)", s=session) == 0
    assert await _scalar(snap, s=session) == before

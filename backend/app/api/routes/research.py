"""
Research dashboard, read side (skill research-dashboard-conventions). GET only:
the dashboard never writes through this router. Each endpoint reads views or
projected tables with one SQL query; what the screens need and the database lacks
goes into a migration, not into the frontend.
"""

import csv
import io
import json
import math
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db
from app.schemas.research import (
    DataQuality, LearnerProfile, LiveCurrent, LiveSnapshot, LiveTraces, ResearchAdaptation, ResearchParticipant, ResearchParticipantDetail, ResearchSession, ResearchSessionDetail, ResearchTrial, SessionPlan,
    SessionTimeline,
)

router = APIRouter(prefix="/research", tags=["research"])

_PARTICIPANT_COLUMNS = """
SELECT p.id, p.external_code, p.created_at, p.pretest_completed_at,
       CASE WHEN p.pretest_completed_at IS NOT NULL THEN 'COMPLETED'
            WHEN r.answered > 0 THEN 'IN_PROGRESS'
            ELSE 'NOT_STARTED' END AS pretest_status,
       r.answered AS pretest_answered,
       s.session_count, s.conditions,
       last.created_at AS last_session_at, last.accuracy::float AS last_session_accuracy,
       p.previous_japanese_experience,
       CASE WHEN p.pretest_completed_at IS NOT NULL THEN
            (SELECT count(*) FROM kanji_substitutions k
              WHERE k.participant_id = p.id AND k.substitute_kanji_id IS NULL) END AS flagged_count
FROM participants p
CROSS JOIN LATERAL (SELECT count(*) AS answered FROM kanji_pretest_responses x
                    WHERE x.participant_id = p.id) r
CROSS JOIN LATERAL (SELECT count(*) AS session_count,
                           COALESCE(array_agg(DISTINCT e.condition ORDER BY e.condition)::text[], '{}') AS conditions
                    FROM experiment_sessions e WHERE e.participant_id = p.id) s
LEFT JOIN LATERAL (SELECT o.created_at, o.accuracy FROM v_session_overview o
                   WHERE o.participant_id = p.id ORDER BY o.created_at DESC LIMIT 1) last ON TRUE"""

_PARTICIPANTS = text(_PARTICIPANT_COLUMNS + " ORDER BY p.created_at DESC")


@router.get("/participants", response_model=list[ResearchParticipant])
async def list_participants(db: AsyncSession = Depends(get_db)) -> list[dict]:
    return [dict(r._mapping) for r in await db.execute(_PARTICIPANTS)]


_SESSION_COLUMNS = """
SELECT o.session_id, o.participant_id, p.external_code, o.condition, o.status, o.visit_number,
       o.created_at, o.projection_status,
       CASE WHEN o.trials_recorded THEN o.trial_count END AS trial_count,
       CASE WHEN o.decisions_recorded THEN o.decision_count END AS decision_count,
       o.accuracy::float AS accuracy, o.open_error_count,
       (SELECT x.state::text FROM session_states x WHERE x.session_id = o.session_id
         ORDER BY x.visit_seq DESC LIMIT 1) AS last_state"""

_SESSIONS = text(_SESSION_COLUMNS + """
FROM v_session_overview o
JOIN participants p ON p.id = o.participant_id
WHERE (CAST(:participant_id AS uuid) IS NULL OR o.participant_id = :participant_id)
  AND (CAST(:condition AS text) IS NULL OR o.condition::text = :condition)
  AND (CAST(:status AS text) IS NULL OR o.status::text = :status)
  AND (CAST(:from_ AS timestamptz) IS NULL OR o.created_at >= :from_)
  AND (CAST(:to AS timestamptz) IS NULL OR o.created_at <= :to)
ORDER BY o.created_at DESC
""")


@router.get("/sessions", response_model=list[ResearchSession])
async def list_sessions(
    participant_id: uuid.UUID | None = None,
    condition: Literal["STATIC", "BEHAVIOR_ADAPTIVE", "MULTIMODAL_ADAPTIVE"] | None = None,
    status: Literal["CREATED", "IN_PROGRESS", "COMPLETED", "ABORTED"] | None = None,
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    params = {"participant_id": participant_id, "condition": condition, "status": status, "from_": from_, "to": to}
    return [dict(r._mapping) for r in await db.execute(_SESSIONS, params)]


# Aggregates over trial_timeline() shared by the Session View (V1.2) and the Participant
# View (V1.8), so both show the same numbers. ha.recorded: HEAD_AWAY ever appears.
_SUMMARY_JOINS = """
CROSS JOIN LATERAL (
    SELECT min(t.block_state)::text AS first_block, max(t.block_state)::text AS last_block,
           (avg(t.response_time_ms) FILTER (WHERE t.response_time_ms IS NOT NULL))::float AS mean_rt_ms,
           (avg(t.window_rt_cv) FILTER (WHERE t.response_time_ms IS NOT NULL))::float AS rt_cv_mean,
           count(*) FILTER (WHERE t.cue_trigger = 'PROACTIVE') AS proactive_hints,
           sum(t.head_away_count) FILTER (WHERE t.response_time_ms IS NOT NULL) AS head_away_count,
           sum(t.head_away_ms) FILTER (WHERE t.response_time_ms IS NOT NULL) AS head_away_ms
    FROM trial_timeline(o.session_id, 3) t) tl
CROSS JOIN LATERAL (
    SELECT EXISTS (SELECT 1 FROM session_events e
                    WHERE e.session_id = o.session_id AND e.event_type = 'HEAD_AWAY') AS recorded) ha
"""

_HEAD_AWAY = """CASE WHEN ha.recorded THEN COALESCE(tl.head_away_count, 0) END AS head_away_count,
       CASE WHEN ha.recorded THEN COALESCE(tl.head_away_ms, 0) END AS head_away_ms"""

# The 0.3 criterion: a count whose event type never appears in the session is NULL.
_SESSION_DETAIL = text(_SESSION_COLUMNS + """,
       s.assigned_kanji_set AS kanji_set, s.session_clock_started_at AS started_at,
       tl.first_block, tl.last_block, tl.mean_rt_ms, tl.rt_cv_mean,
       CASE WHEN o.trials_recorded THEN
            (SELECT count(*) FROM hint_requests h WHERE h.session_id = o.session_id) END AS hint_requests,
       CASE WHEN o.trials_recorded THEN tl.proactive_hints END AS proactive_hints,
       """ + _HEAD_AWAY + """,
       (SELECT COALESCE(json_agg(json_build_object('state', x.state, 'entered_elapsed_ms', x.entered_elapsed_ms,
                                                   'exited_elapsed_ms', x.exited_elapsed_ms) ORDER BY x.visit_seq), '[]')
          FROM session_states x WHERE x.session_id = o.session_id) AS states,
       CASE WHEN o.decisions_recorded THEN json_build_object(
            'decisions', ad.decisions, 'environment_changes', ad.env, 'assistance_changes', ad.lal,
            'skipped_by_unity', (SELECT count(*) FROM adaptation_applications a
                                  WHERE a.session_id = o.session_id AND a.result = 'SKIPPED'),
            'outcome_positive', ad.pos, 'outcome_neutral', ad.neu, 'outcome_negative', ad.neg,
            'outcome_uncertain', ad.unc, 'outcome_not_recorded', ad.unknown) END AS adaptations
FROM v_session_overview o
JOIN participants p ON p.id = o.participant_id
JOIN experiment_sessions s ON s.id = o.session_id
""" + _SUMMARY_JOINS + """
CROSS JOIN LATERAL (
    SELECT count(*) AS decisions,
           count(*) FILTER (WHERE d.action = 'CHANGE_ENVIRONMENT') AS env,
           count(*) FILTER (WHERE d.action = 'CHANGE_ASSISTANCE') AS lal,
           count(*) FILTER (WHERE d.action <> 'NO_CHANGE' AND d.outcome = 'POSITIVE') AS pos,
           count(*) FILTER (WHERE d.action <> 'NO_CHANGE' AND d.outcome = 'NEUTRAL') AS neu,
           count(*) FILTER (WHERE d.action <> 'NO_CHANGE' AND d.outcome = 'NEGATIVE') AS neg,
           count(*) FILTER (WHERE d.action <> 'NO_CHANGE' AND d.outcome = 'UNCERTAIN') AS unc,
           count(*) FILTER (WHERE d.action <> 'NO_CHANGE' AND d.outcome IS NULL) AS unknown
    FROM v_adaptations d WHERE d.session_id = o.session_id) ad
WHERE o.session_id = :session_id
""")


@router.get("/sessions/{session_id}", response_model=ResearchSessionDetail)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    row = (await db.execute(_SESSION_DETAIL, {"session_id": session_id})).first()
    if row is None:
        raise HTTPException(status_code=404, detail="session not found")
    return dict(row._mapping)


_PARTICIPANT = text(_PARTICIPANT_COLUMNS + " WHERE p.id = :participant_id")

# Oldest first: the table's # and the trend's ticks follow this order.
_PARTICIPANT_SESSIONS = text(_SESSION_COLUMNS + """,
       tl.mean_rt_ms, """ + _HEAD_AWAY + """,
       (p.pretest_completed_at IS NULL OR o.created_at < p.pretest_completed_at) AS before_pretest
FROM v_session_overview o
JOIN participants p ON p.id = o.participant_id""" + _SUMMARY_JOINS + """
WHERE o.participant_id = :participant_id
ORDER BY o.created_at
""")

# Written when the pre-test completes; a NULL substitute is a kanji kept and flagged.
_SUBSTITUTIONS = text("""
SELECT k.set_name, o.kanji_char AS original, s.kanji_char AS substitute
FROM kanji_substitutions k
JOIN kanji_items o ON o.kanji_id = k.original_kanji_id
LEFT JOIN kanji_items s ON s.kanji_id = k.substitute_kanji_id
WHERE k.participant_id = :participant_id
ORDER BY k.set_name, k.original_kanji_id
""")


@router.get("/participants/{participant_id}", response_model=ResearchParticipantDetail)
async def get_participant(participant_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    """Participant View (V1.8): the V1.11 row, the sessions in order and the pre-test result."""
    params = {"participant_id": participant_id}
    row = (await db.execute(_PARTICIPANT, params)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="participant not found")
    return dict(row._mapping) | {
        "sessions": [dict(r._mapping) for r in await db.execute(_PARTICIPANT_SESSIONS, params)],
        "substitutions": [dict(r._mapping) for r in await db.execute(_SUBSTITUTIONS, params)],
    }


@router.get("/participants/{participant_id}/profile", response_model=LearnerProfile)
async def get_learner_profile(participant_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    """The stored Learner Profile v1 (F-PROFILE). Read only: it is computed when a session
    completes or aborts (app/adaptation/learner_profile.py), never here."""
    if (await db.execute(text("SELECT 1 FROM participants WHERE id = :p"), {"p": participant_id})).first() is None:
        raise HTTPException(status_code=404, detail="participant not found")
    row = (await db.execute(text(
        "SELECT profile_version, computed_at, session_ids, profile FROM learner_profiles "
        "WHERE participant_id = :p AND profile_version = 'v1'"), {"p": participant_id})).first()
    empty = {"profile_version": None, "computed_at": None, "session_ids": [], "profile": None}
    return {"participant_id": participant_id, **(dict(row._mapping) if row else empty)}


# The verify_*_fn() of migration 0006, in the order V1.7 lists them.
_CHECKS = ["verify_projection", "verify_adaptation", "verify_trials", "verify_assembly", "verify_reproducibility"]

# shortcut: every open error in one response, paged by the page; page in SQL if open
# errors ever reach the tens of thousands (today 0, 9,810 resolved).
_OPEN_ERRORS = text("""
SELECT id, event_id, session_id, event_type, error_code, detail, session_elapsed_ms
FROM v_projection_errors WHERE resolved_at IS NULL
ORDER BY occurred_at DESC, id DESC
""")

_QUALITY_COUNTS = text("""
SELECT (SELECT count(*) FROM projection_errors WHERE resolved_at IS NOT NULL) AS resolved_errors,
       COALESCE((SELECT json_object_agg(error_code, n) FROM (
           SELECT error_code, count(*) AS n FROM projection_errors
           WHERE resolved_at IS NULL GROUP BY error_code) c), '{}') AS open_by_code
""")

_PROJECTED = text("SELECT session_id FROM v_session_overview WHERE projection_status = 'PROJECTED'")

_NOT_PROJECTED = text("""
SELECT o.session_id, o.participant_id, p.external_code, o.created_at, o.projection_status
FROM v_session_overview o JOIN participants p ON p.id = o.participant_id
WHERE o.projection_status <> 'PROJECTED'
ORDER BY o.created_at DESC
""")


@router.get("/quality", response_model=DataQuality)
async def data_quality(db: AsyncSession = Depends(get_db)) -> dict:
    """Data quality (V1.7): open projection errors, the verify checks over every session,
    and the sessions with no projection."""
    # Called per projected session: with NULL, some functions check only the latest one.
    # shortcut: every check on every session on each request, about 2 s for 45 sessions and
    # more than linear (verify_reproducibility compares seed pairs); cache the result or run
    # one check on demand if the page gets slow after the pilot.
    checks = [{"name": name, "rows": [dict(r._mapping) for r in await db.execute(text(
        f'SELECT v.session_id, v."check", v.detail FROM v_session_overview o '
        f"CROSS JOIN LATERAL {name}_fn(o.session_id) v WHERE o.projection_status = 'PROJECTED' "
        f'ORDER BY o.created_at DESC, v."check"'))]}
        for name in _CHECKS]
    errors = [dict(r._mapping) for r in await db.execute(_OPEN_ERRORS)]
    projected = {r[0] for r in await db.execute(_PROJECTED)}
    dirty = {r["session_id"] for c in checks for r in c["rows"]} | {e["session_id"] for e in errors}
    return dict((await db.execute(_QUALITY_COUNTS)).one()._mapping) | {
        "projected_sessions": len(projected),
        "clean_sessions": len(projected - dirty),
        "checks": checks,
        "open_errors": errors,
        "not_projected": [dict(r._mapping) for r in await db.execute(_NOT_PROJECTED)],
    }


# A lane is NULL when its event type never appears in the session (hints: when no trial
# was recorded, since a request is per trial).
# Assistance has no interval table: LAL is set on each state entry and by each applied
# LAL change, and holds until the next one (runs of the same level are merged).
_TIMELINE = text("""
WITH ev AS (
    SELECT bool_or(e.event_type = 'STATE_ENTERED') AS states,
           bool_or(e.event_type = 'ENVIRONMENT_APPLIED') AS env,
           bool_or(e.event_type = 'TRIAL_STARTED') AS trials,
           bool_or(e.event_type = 'PERIPHERAL_EVENT') AS peripherals,
           bool_or(e.event_type = 'DISTRACTOR_INTERACTION') AS distractors,
           bool_or(e.event_type = 'HEAD_AWAY') AS head_away,
           bool_or(e.event_type = 'ADAPTATION_DECISION') AS decisions,
           max(CASE WHEN jsonb_typeof(e.payload -> 'session_elapsed_ms') = 'number'
                    THEN (e.payload ->> 'session_elapsed_ms')::numeric END)::int AS end_ms
    FROM session_events e WHERE e.session_id = :session_id),
lal AS (
    SELECT ms, level, level IS DISTINCT FROM lag(level) OVER (ORDER BY ms, src) AS changed
    FROM (SELECT x.entered_elapsed_ms AS ms, x.lal::text AS level, 0 AS src FROM session_states x
           WHERE x.session_id = :session_id AND x.lal IS NOT NULL
          UNION ALL
          SELECT a.elapsed_ms, a.lal_after::text, 1 FROM adaptation_applications a
           WHERE a.session_id = :session_id AND a.result = 'APPLIED' AND a.lal_after IS NOT NULL) c),
lal_runs AS (
    SELECT level, ms AS start_ms, lead(ms) OVER (ORDER BY ms) AS end_ms FROM lal WHERE changed)
SELECT EXISTS (SELECT 1 FROM experiment_sessions WHERE id = :session_id) AS found,
       ev.end_ms AS session_end_ms,
       CASE WHEN ev.states THEN (SELECT COALESCE(json_agg(json_build_object(
                'state', x.state, 'start_ms', x.entered_elapsed_ms, 'end_ms', x.exited_elapsed_ms)
                ORDER BY x.visit_seq), '[]') FROM session_states x WHERE x.session_id = :session_id) END AS states,
       CASE WHEN ev.env THEN (SELECT COALESCE(json_agg(json_build_object(
                'level', v.esl, 'start_ms', v.elapsed_ms, 'end_ms', v.valid_to_ms)
                ORDER BY v.elapsed_ms), '[]') FROM v_environment_intervals v WHERE v.session_id = :session_id) END AS environment,
       CASE WHEN EXISTS (SELECT 1 FROM lal_runs) THEN (SELECT json_agg(json_build_object(
                'level', r.level, 'start_ms', r.start_ms, 'end_ms', r.end_ms) ORDER BY r.start_ms) FROM lal_runs r) END AS assistance,
       CASE WHEN ev.trials THEN (SELECT COALESCE(json_agg(json_build_object(
                'trial_id', t.trial_id, 'block_state', t.block_state, 'start_ms', t.started_elapsed_ms,
                'end_ms', t.completed_elapsed_ms, 'is_correct', t.is_correct)
                ORDER BY t.started_elapsed_ms), '[]') FROM trials t WHERE t.session_id = :session_id) END AS trials,
       CASE WHEN ev.trials THEN (SELECT COALESCE(json_agg(json_build_object(
                'ms', h.ms, 'trial_id', h.trial_id, 'proactive', h.proactive) ORDER BY h.ms), '[]')
            FROM (SELECT r.elapsed_ms AS ms, r.trial_id, false AS proactive FROM hint_requests r
                   WHERE r.session_id = :session_id
                  UNION ALL
                  SELECT t.started_elapsed_ms, t.trial_id, true FROM trials t
                   WHERE t.session_id = :session_id AND t.cue_trigger = 'PROACTIVE') h) END AS hints,
       CASE WHEN ev.peripherals THEN (SELECT COALESCE(json_agg(json_build_object(
                'ms', x.elapsed_ms, 'event_index', x.event_index, 'object_name', x.object_name)
                ORDER BY x.elapsed_ms), '[]') FROM peripheral_events x WHERE x.session_id = :session_id) END AS peripherals,
       CASE WHEN ev.distractors THEN (SELECT COALESCE(json_agg(json_build_object(
                'kind', x.kind, 'start_ms', x.onset_elapsed_ms, 'duration_ms', x.duration_ms, 'object_name', x.object_name)
                ORDER BY x.onset_elapsed_ms), '[]') FROM distractor_interactions x WHERE x.session_id = :session_id) END AS distractors,
       CASE WHEN ev.head_away THEN (SELECT COALESCE(json_agg(json_build_object(
                'start_ms', x.onset_elapsed_ms, 'end_ms', x.returned_elapsed_ms, 'limit_crossed', x.limit_crossed)
                ORDER BY x.onset_elapsed_ms), '[]') FROM head_away_episodes x WHERE x.session_id = :session_id) END AS head_away,
       CASE WHEN ev.decisions THEN (SELECT COALESCE(json_agg(json_build_object(
                'decision_id', v.decision_id, 'trial_id', v.trial_id, 'decided_ms', v.decided_elapsed_ms,
                'action', v.action, 'dimension', v.dimension, 'from_level', v.from_level, 'to_level', v.to_level,
                'learner_state', v.learner_state, 'unity_result', v.unity_result, 'skip_reason', v.skip_reason,
                'result_ms', v.applied_elapsed_ms, 'outcome', v.outcome,
                'cooldown_until_ms', CASE WHEN d.cooldown_until_trial IS NOT NULL THEN COALESCE(
                    (SELECT t2.started_elapsed_ms FROM trials t2 WHERE t2.session_id = :session_id
                        AND t2.block_state = t1.block_state AND t2.trial_sequence = d.cooldown_until_trial),
                    (SELECT max(t3.completed_elapsed_ms) FROM trials t3 WHERE t3.session_id = :session_id
                        AND t3.block_state = t1.block_state)) END)
                ORDER BY v.decided_elapsed_ms), '[]')
            FROM v_adaptations v
            JOIN adaptation_decisions d ON d.session_id = v.session_id AND d.decision_id = v.decision_id
            JOIN trials t1 ON t1.session_id = v.session_id AND t1.trial_id = v.trial_id
            WHERE v.session_id = :session_id AND v.action <> 'NO_CHANGE') END AS adaptations
FROM ev
""")


@router.get("/sessions/{session_id}/timeline", response_model=SessionTimeline)
async def get_timeline(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    row = dict((await db.execute(_TIMELINE, {"session_id": session_id})).one()._mapping)
    if not row.pop("found"):
        raise HTTPException(status_code=404, detail="session not found")
    return row


async def _require_session(db: AsyncSession, session_id: uuid.UUID) -> None:
    if not (await db.execute(text("SELECT 1 FROM experiment_sessions WHERE id = :s"), {"s": session_id})).first():
        raise HTTPException(status_code=404, detail="session not found")


# Confidence is a 4-byte real: ::numeric gives the stored 0.8, not its float64 widening
# 0.800000011920929.
# trial_timeline() COALESCEs the head-away, peripheral and dwell columns to 0; here they are
# NULL when their event type never appears in the session (data-contract.md, 0.3 criterion).
_TRIALS = text("""
WITH ev AS (
    SELECT COALESCE(bool_or(e.event_type = 'HEAD_AWAY'), false) AS head_away,
           COALESCE(bool_or(e.event_type = 'PERIPHERAL_EVENT'), false) AS peripherals,
           COALESCE(bool_or(e.event_type = 'DISTRACTOR_INTERACTION'), false) AS distractors
    FROM session_events e WHERE e.session_id = :session_id)
SELECT t.trial_id, t.block_state::text, t.trial_sequence, t.trial_type::text, t.kanji_id, t.kanji_char,
       t.is_primary_analysis, t.started_elapsed_ms, t.completed_elapsed_ms, t.esl::text, t.lal::text, t.env_profile,
       t.prop_count, t.mover_count, t.is_correct, t.response_time_ms, t.timed_out, t.hint_count,
       t.cue_trigger, t.idle_ms,
       CASE WHEN ev.head_away THEN t.head_away_count END AS head_away_count,
       CASE WHEN ev.head_away THEN t.head_away_ms END AS head_away_ms,
       CASE WHEN ev.peripherals THEN t.peripheral_event_count END AS peripheral_event_count,
       CASE WHEN ev.distractors THEN t.distractor_dwell_ms END AS distractor_dwell_ms,
       t.window_n, t.window_accuracy::float, t.window_rt_mean::float, t.window_rt_cv::float,
       t.learner_state, d.cause, t.decision_confidence::numeric::float AS decision_confidence, t.decision_action, d.reason_code, d.explanation,
       d.dimension, d.from_level::text, d.to_level::text, v.unity_result, v.skip_reason,
       v.applied_before_trial_id, d.cooldown_until_trial,
       (SELECT c.trial_id FROM trials c WHERE c.session_id = t.session_id AND c.block_state = t.block_state
           AND c.trial_sequence = d.cooldown_until_trial) AS cooldown_until_trial_id,
       d.outcome, d.estimator_version, d.rules_version, d.indicators, d.thresholds
FROM trial_timeline(:session_id, :window_n) t
CROSS JOIN ev
LEFT JOIN adaptation_decisions d ON d.session_id = t.session_id AND d.trial_id = t.trial_id
LEFT JOIN v_adaptations v ON v.session_id = d.session_id AND v.decision_id = d.decision_id
ORDER BY t.started_elapsed_ms, t.trial_id
""")


@router.get("/sessions/{session_id}/trials", response_model=list[ResearchTrial])
async def list_trials(
    session_id: uuid.UUID,
    window_n: int = Query(3, ge=3, le=5),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    await _require_session(db, session_id)
    rows = await db.execute(_TRIALS, {"session_id": session_id, "window_n": window_n})
    return [dict(r._mapping) for r in rows]


_ADAPTATIONS = text("""
SELECT v.decision_id, v.trial_id, v.decided_elapsed_ms, v.learner_state, v.cause, v.confidence::numeric::float AS confidence, v.action,
       v.dimension, v.from_level::text, v.to_level::text, v.proactive_cues, v.reason_code, v.explanation,
       v.unity_result, v.skip_reason, v.applied_before_trial_id, d.cooldown_until_trial,
       (SELECT c.trial_id FROM trials t JOIN trials c ON c.session_id = t.session_id AND c.block_state = t.block_state
         WHERE t.session_id = v.session_id AND t.trial_id = v.trial_id
           AND c.trial_sequence = d.cooldown_until_trial) AS cooldown_until_trial_id,
       v.outcome, d.estimator_version, d.rules_version, d.indicators, d.thresholds
FROM v_adaptations v
JOIN adaptation_decisions d ON d.session_id = v.session_id AND d.decision_id = v.decision_id
WHERE v.session_id = :session_id AND (:include_no_change OR v.action <> 'NO_CHANGE')
ORDER BY v.decided_elapsed_ms
""")


@router.get("/sessions/{session_id}/adaptations", response_model=list[ResearchAdaptation])
async def list_adaptations(
    session_id: uuid.UUID,
    include_no_change: bool = False,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    await _require_session(db, session_id)
    rows = await db.execute(_ADAPTATIONS, {"session_id": session_id, "include_no_change": include_no_change})
    return [dict(r._mapping) for r in rows]


# Plan and execution are stored apart on purpose (EVENT_CONTRACT.md 5.6): a planned trial
# with no trials row was never shown; one with no completion was started and cut.
_PLAN = text("""
SELECT (SELECT x.state::text FROM session_states x WHERE x.session_id = :session_id
         ORDER BY x.visit_seq DESC LIMIT 1) AS last_state,
       (SELECT x.entered_elapsed_ms FROM session_states x WHERE x.session_id = :session_id
         ORDER BY x.visit_seq DESC LIMIT 1) AS last_state_ms,
       (SELECT COALESCE(json_agg(json_build_object(
            'block_state', b.block_state, 'kanji_set', b.kanji_set, 'block_seed', b.block_seed::text,
            'planned', p.planned, 'started', p.started, 'completed', p.completed,
            'min_lag_requested', b.min_lag_requested,
            'min_lag_achieved', NULLIF(b.min_lag_achieved, -1),
            'kanji_repeats', b.min_lag_achieved IS DISTINCT FROM -1,
            'trials', p.trials) ORDER BY b.block_state), '[]')
        FROM trial_blocks b
        CROSS JOIN LATERAL (
            SELECT count(*) AS planned, count(t.trial_id) AS started, count(t.completed_event_id) AS completed,
                   COALESCE(json_agg(json_build_object('trial_id', pt.trial_id, 'status',
                       CASE WHEN t.trial_id IS NULL THEN 'NEVER_SHOWN'
                            WHEN t.completed_event_id IS NULL THEN 'STARTED' ELSE 'COMPLETED' END)
                       ORDER BY pt.trial_sequence), '[]') AS trials
            FROM planned_trials pt
            LEFT JOIN trials t ON t.session_id = pt.session_id AND t.trial_id = pt.trial_id
            WHERE pt.session_id = b.session_id AND pt.block_state = b.block_state) p
        WHERE b.session_id = :session_id) AS blocks
""")


@router.get("/sessions/{session_id}/plan", response_model=SessionPlan)
async def get_plan(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    await _require_session(db, session_id)
    return dict((await db.execute(_PLAN, {"session_id": session_id})).one()._mapping)


def _cell(value) -> str:
    """CSV cell: NULL is empty, never 0; booleans lower case; stored JSON stays JSON."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


@router.get("/sessions/{session_id}/export.csv")
async def export_csv(
    session_id: uuid.UUID,
    kind: Literal["trials", "adaptations"],
    window_n: int = Query(3, ge=3, le=5),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """The Trials or Adaptations tab as CSV (V1.9): the API's fields as headers, every
    decision included (NO_CHANGE too). Rows go through the API's own model."""
    await _require_session(db, session_id)
    if kind == "trials":
        model = ResearchTrial
        rows = await db.execute(_TRIALS, {"session_id": session_id, "window_n": window_n})
    else:
        model = ResearchAdaptation
        rows = await db.execute(_ADAPTATIONS, {"session_id": session_id, "include_no_change": True})
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(model.model_fields)
    for r in rows:
        values = model.model_validate(dict(r._mapping)).model_dump(mode="json")
        writer.writerow(_cell(v) for v in values.values())
    filename = f"session-{str(session_id)[:8]}-{kind}.csv"
    # utf-8-sig writes the byte order mark: without it Excel reads the file in the Windows
    # code page and kanji turn to mojibake. pandas and R skip it with encoding "utf-8-sig".
    return Response(out.getvalue().encode("utf-8-sig"), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


# ---------- V1.13 Live session monitor (M1a; D-F6-231, D-F6-233, D-F6-234, D-F6-247, D-F6-254) ----------
# One snapshot of what the database already holds, polled by the page. Nothing here is recomputed from the signal:
# the words come from the engine's z of each decision (D-F6-234), the trace from eeg_epochs against the stored
# reference (window.py's count, epoch by epoch). signal_quality stays null until M1b.

_LIVE_TOP = text("""
SELECT s.id::text AS session_id, p.external_code, s.condition::text AS condition, s.assigned_kanji_set AS set,
       s.visit_number AS visit, s.status::text AS status, s.current_state::text AS stage, s.completed_at,
       (SELECT max(st.entered_elapsed_ms) FROM session_states st
         WHERE st.session_id = s.id AND st.state::text = s.current_state::text) AS stage_entered_ms,
       CASE WHEN s.status::text = 'IN_PROGRESS' THEN
         -- D-F6-274 (1): session time now, not the newest event's (S4 sends none for ~105 s). The max anchor
         -- (elapsed minus arrival) keeps an event that waited in Unity's queue from pulling the clock back.
         (SELECT round(max((e.payload ->> 'session_elapsed_ms')::numeric
                           - extract(epoch FROM e.server_received_at) * 1000) + extract(epoch FROM now()) * 1000)::int
            FROM session_events e WHERE e.session_id = s.id AND e.payload ? 'session_elapsed_ms')
       ELSE
         (SELECT (e.payload ->> 'session_elapsed_ms')::int FROM session_events e
           WHERE e.session_id = s.id AND e.payload ? 'session_elapsed_ms' ORDER BY e.id DESC LIMIT 1)
       END AS elapsed_ms
FROM experiment_sessions s JOIN participants p ON p.id = s.participant_id WHERE s.id = :s""")

_LIVE_EEG = text("""
SELECT sync_offset_ms, sync_detail, reference, alpha_ratio, alpha_passed, not_counted_reason, bad_channel,
       bad_channel_from_ms, eeg_gap_ms, EXTRACT(EPOCH FROM now() - heartbeat_at)::float AS heartbeat_age_s,
       monitor, EXTRACT(EPOCH FROM now() - monitor_at)::float AS monitor_age_s, ica
FROM eeg_sessions WHERE session_id = :s""")

_LIVE_DECISIONS = text("""
SELECT trial_id, trial_sequence, decided_elapsed_ms, learner_state, action, dimension, from_level, to_level, esl, lal,
       reason_code, eeg_counted, eeg_ei_z, eeg_theta_z, eeg_effect
FROM adaptation_decisions WHERE session_id = :s ORDER BY trial_sequence DESC, decided_elapsed_ms DESC""")

_LIVE_EVENTS = text("""
SELECT (payload ->> 'session_elapsed_ms')::int AS elapsed_ms, event_type, payload ->> 'trial_id' AS trial_id
FROM session_events WHERE session_id = :s ORDER BY id DESC LIMIT 40""")

_LIVE_TRACE = text("""
SELECT start_ms, engagement_index, theta_fz FROM eeg_epochs
WHERE session_id = :s AND quality <> 'POOR' AND start_ms IS NOT NULL ORDER BY epoch_index""")

_LOOK = {"HEAD_AWAY", "FRAME_HITCH", "EEG_STATUS", "ADAPTATION_SKIPPED"}  # the triangle of V1.13's event console


def _r(value: float | None, digits: int) -> float | None:
    return None if value is None else round(value, digits)


def _band(z: float | None, counted: bool | None) -> str | None:
    """D-F6-234: Low z <= -1, High z >= +1, Normal between; "Not counted" when the window's EEG did not count."""
    if counted is False:
        return "Not counted"
    if z is None:
        return None
    return "Low" if z <= -1 else "High" if z >= 1 else "Normal"


def _live_z(value: float | None, stats: dict | None) -> float | None:
    """z of one epoch's index against the session's reference, as window.py (ln, then mean and SD)."""
    if value is None or not stats or stats.get("mean") is None or not stats.get("sd"):
        return None
    return (math.log(value) - stats["mean"]) / stats["sd"]


_SESSION_EPOCHS = text("""
SELECT epoch_index, start_ms, end_ms, game_state, trial_id, quality, engagement_index, theta_fz, excluded_channels
FROM eeg_epochs WHERE session_id = :s AND start_ms IS NOT NULL ORDER BY epoch_index""")

_SESSION_STAGES = text("""
SELECT payload ->> 'state' AS state, (payload ->> 'session_elapsed_ms')::int AS ms FROM session_events
WHERE session_id = :s AND event_type = 'STATE_ENTERED' ORDER BY id""")

_SESSION_BASELINE = text("""
SELECT (payload ->> 'session_elapsed_ms')::int AS ms, (payload ->> 'eyes_open_s')::float AS open_s,
       (payload ->> 'eyes_closed_s')::float AS closed_s
FROM session_events WHERE session_id = :s AND event_type = 'BASELINE_STARTED' ORDER BY id DESC LIMIT 1""")

_LN_STATES = {"S1_WELCOME_ORIENTATION", "S2_VR_TUTORIAL", "S3_SYSTEM_VALIDATION", "S4_EEG_BASELINE",
              "S6_GUIDED_PRACTICE_CALIBRATION"}
_S4, _S5 = "S4_EEG_BASELINE", "S5_STANDARDIZED_LEARNING"
_ICA_KEYS = ("identified", "corr", "reason", "switched_to_nosound_at", "switch_reason")


async def _session_trace(db: AsyncSession, session_id: uuid.UUID, eeg: dict | None) -> dict:
    """MI (D-F6-277 (3), D-F6-280 (1)): every live epoch on its stage's scale. ln in S1–S4 and S6; in S5 a provisional
    z against S4's eyes-open epochs; from S7 the z against the engine's reference, as window.py. POOR: no value (red);
    S4 eyes closed: grey. Reads only what live.py already wrote: no new EEG computation."""
    from app.eeg import reference

    epochs = [dict(r) for r in (await db.execute(_SESSION_EPOCHS, {"s": session_id})).mappings()]
    stages = [dict(r) for r in (await db.execute(_SESSION_STAGES, {"s": session_id})).mappings()]
    b = (await db.execute(_SESSION_BASELINE, {"s": session_id})).mappings().first()
    # shortcut: the S4 spans from BASELINE_STARTED and its durations (the exact markers travel only by LSL);
    # good to the frame for the display, upgrade if Unity sends EYES_*_START/END to the backend
    opened = (b["ms"], b["ms"] + b["open_s"] * 1000) if b and b["open_s"] is not None else None
    closed = (opened[1], opened[1] + b["closed_s"] * 1000) if opened and b["closed_s"] is not None else None

    def mid(e: dict) -> float:
        return (e["start_ms"] + e["end_ms"]) / 2

    def inside(e: dict, span: tuple | None) -> bool:
        return span is not None and span[0] <= mid(e) < span[1]

    rest = [e for e in epochs if e["game_state"] == _S4 and e["quality"] != "POOR" and inside(e, opened)]
    s4 = {k: reference._stats([e[col] for e in rest]) for k, col in (("ei", "engagement_index"), ("theta", "theta_fz"))}
    ref = ((eeg or {}).get("reference") or {}).get("indices") or {}
    engine = {"ei": ref.get("engagement_index"), "theta": ref.get("theta_fz")}

    def value(e: dict, key: str, col: str) -> float | None:
        v = e[col]
        if e["quality"] == "POOR" or v is None or v <= 0:
            return None
        if e["game_state"] in _LN_STATES:
            return math.log(v)
        return _live_z(v, s4[key] if e["game_state"] == _S5 else engine[key])

    ica = (eeg or {}).get("ica")
    return {
        "stages": stages,
        "eyes_closed_ms": list(closed) if closed else None,
        "ica": None if ica is None else {k: ica.get(k) for k in _ICA_KEYS},
        "epochs": [{"i": e["epoch_index"], "start_ms": e["start_ms"], "state": e["game_state"], "trial_id": e["trial_id"],
                    "valid": e["quality"] != "POOR", "grey": e["game_state"] == _S4 and inside(e, closed),
                    "excluded": e["excluded_channels"], "unit": "ln" if e["game_state"] in _LN_STATES else "z",
                    "ei": value(e, "ei", "engagement_index"), "theta": value(e, "theta", "theta_fz")}
                   for e in epochs],
    }


@router.get("/sessions/{session_id}/live", response_model=LiveSnapshot)
async def live_snapshot(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    top = (await db.execute(_LIVE_TOP, {"s": session_id})).mappings().first()
    if top is None:
        raise HTTPException(status_code=404, detail="session not found")
    eeg = (await db.execute(_LIVE_EEG, {"s": session_id})).mappings().first()
    # REAL columns: rounded as the decision's eeg block stores them (z to 3 decimals, concordance.block)
    decisions = [{**dict(r), "eeg_ei_z": _r(r["eeg_ei_z"], 3), "eeg_theta_z": _r(r["eeg_theta_z"], 3)}
                 for r in (await db.execute(_LIVE_DECISIONS, {"s": session_id})).mappings()]
    events = [{**dict(r), "flag": "decision" if r["event_type"] == "ADAPTATION_DECISION" else
               "look" if r["event_type"] in _LOOK else None}
              for r in (await db.execute(_LIVE_EVENTS, {"s": session_id})).mappings()]
    ref = (eeg or {}).get("reference") or {}
    idx = ref.get("indices") or {}
    trace = [{"start_ms": r["start_ms"], "ei_z": _live_z(r["engagement_index"], idx.get("engagement_index")),
              "theta_z": _live_z(r["theta_fz"], idx.get("theta_fz"))}
             for r in (await db.execute(_LIVE_TRACE, {"s": session_id})).mappings()]
    with_eeg = [d for d in decisions if d["eeg_counted"] is not None]
    last = with_eeg[0] if with_eeg else None
    detail = (eeg or {}).get("sync_detail") or {}
    taps = [t for t in detail.get("taps") or [] if t.get("phase") == "S3"]
    return {
        "generated_at": datetime.now().astimezone(),
        "session": dict(top),
        "sync": None if eeg is None else {
            "clear_taps": sum(1 for t in taps if t.get("valid")) if taps else None, "taps": len(taps) or None,
            "offset_ms": _r(eeg["sync_offset_ms"], 1), "robust_spread_ms": detail.get("spread_ms")},
        "indices": {
            "reference": ({"source": ref.get("source"), "fallback": ref.get("fallback"), "n_epochs": ref.get("n_epochs")}
                          if ref else None),
            "last": None if last is None else {
                "trial_id": last["trial_id"], "counted": last["eeg_counted"],
                "ei_z": last["eeg_ei_z"], "ei_band": _band(last["eeg_ei_z"], last["eeg_counted"]),
                "theta_z": last["eeg_theta_z"], "theta_band": _band(last["eeg_theta_z"], last["eeg_counted"])},
            "windows": {"counted": sum(1 for d in with_eeg if d["eeg_counted"]), "with_eeg": len(with_eeg)},
            "trace": trace,
            "session": await _session_trace(db, session_id, eeg) if get_settings().monitor_live_indices else None},
        "decisions": decisions,
        "events": events,
        "system": None if eeg is None else {k: eeg[k] for k in (
            "heartbeat_age_s", "eeg_gap_ms", "bad_channel", "bad_channel_from_ms", "alpha_ratio", "alpha_passed",
            "not_counted_reason")},
        # M1b: live.py's per-channel figures when EEG_MONITOR_LIVE is on; null otherwise (the page says it waits)
        "signal_quality": None if not eeg or eeg["monitor"] is None else {**eeg["monitor"], "age_s": eeg["monitor_age_s"]},
    }


_TRACE_BINS = text("SELECT t_ms, mins, maxs FROM eeg_trace_bins WHERE session_id = :s AND t_ms > :since ORDER BY t_ms")
_TRACE_TOP = text("""
SELECT montage, bad_channel, traces_now, EXTRACT(EPOCH FROM now() - traces_at)::float AS age_s
FROM eeg_sessions WHERE session_id = :s""")


@router.get("/sessions/{session_id}/live/traces", response_model=LiveTraces)
async def live_traces(session_id: uuid.UUID, since: int = Query(-1, description="session ms of the last bin held"),
                      db: AsyncSession = Depends(get_db)) -> dict:
    """TR (D-F6-301 (5)): what live.py wrote for the traces panel, read only. Off: empty, with the reason."""
    from app.eeg.baseline import DEFAULT_MONTAGE

    if (await db.execute(_LIVE_TOP, {"s": session_id})).first() is None:
        raise HTTPException(status_code=404, detail="session not found")
    eeg = (await db.execute(_TRACE_TOP, {"s": session_id})).mappings().first()
    montage = (eeg or {}).get("montage") or DEFAULT_MONTAGE
    labels = [montage[f"CH{i + 1}"] for i in range(len(montage))]
    stages = [dict(r) for r in (await db.execute(_SESSION_STAGES, {"s": session_id})).mappings()]
    if not get_settings().eeg_monitor_traces:
        return {"on": False, "reason": "Channel traces are off (EEG_MONITOR_TRACES)", "labels": labels, "bins": [],
                "now": None, "stages": stages, "excluded": None}
    bins = [dict(r) for r in (await db.execute(_TRACE_BINS, {"s": session_id, "since": since})).mappings()]
    now = None if not eeg or eeg["traces_now"] is None else {**eeg["traces_now"], "age_s": eeg["age_s"]}
    return {"on": True, "reason": None, "labels": labels, "bins": bins, "now": now, "stages": stages,
            "excluded": (eeg or {}).get("bad_channel")}

@router.get("/live/current", response_model=LiveCurrent)
async def live_current(db: AsyncSession = Depends(get_db)) -> dict:
    # D-F6-270 (3): with more than one IN_PROGRESS (a hung one not yet aborted), the one with the latest event
    row = (await db.execute(text(
        "SELECT s.id::text AS session_id, p.external_code FROM experiment_sessions s "
        "JOIN participants p ON p.id = s.participant_id "
        "LEFT JOIN LATERAL (SELECT max(e.id) AS last FROM session_events e WHERE e.session_id = s.id) ev ON TRUE "
        "WHERE s.status = 'IN_PROGRESS' ORDER BY ev.last DESC NULLS LAST, s.created_at DESC LIMIT 1"))).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="no session in progress")
    return dict(row)

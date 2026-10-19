"""
Research dashboard, read side (skill research-dashboard-conventions). GET only:
the dashboard never writes through this router. Each endpoint reads views or
projected tables with one SQL query; what the screens need and the database lacks
goes into a migration, not into the frontend.
"""

import csv
import io
import json
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.research import (
    ResearchAdaptation, ResearchParticipant, ResearchSession, ResearchSessionDetail, ResearchTrial, SessionPlan,
    SessionTimeline,
)

router = APIRouter(prefix="/research", tags=["research"])

_PARTICIPANTS = text("""
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
                   WHERE o.participant_id = p.id ORDER BY o.created_at DESC LIMIT 1) last ON TRUE
ORDER BY p.created_at DESC
""")


@router.get("/participants", response_model=list[ResearchParticipant])
async def list_participants(db: AsyncSession = Depends(get_db)) -> list[dict]:
    return [dict(r._mapping) for r in await db.execute(_PARTICIPANTS)]


_SESSION_COLUMNS = """
SELECT o.session_id, o.participant_id, p.external_code, o.condition, o.status, o.visit_number,
       o.created_at, o.projection_status,
       CASE WHEN o.trials_recorded THEN o.trial_count END AS trial_count,
       CASE WHEN o.decisions_recorded THEN o.decision_count END AS decision_count,
       o.accuracy::float AS accuracy, o.open_error_count"""

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


# The 0.3 criterion: a count whose event type never appears in the session is NULL.
_SESSION_DETAIL = text(_SESSION_COLUMNS + """,
       s.assigned_kanji_set AS kanji_set, s.session_clock_started_at AS started_at,
       tl.first_block, tl.last_block, tl.mean_rt_ms, tl.rt_cv_mean,
       CASE WHEN o.trials_recorded THEN
            (SELECT count(*) FROM hint_requests h WHERE h.session_id = o.session_id) END AS hint_requests,
       CASE WHEN o.trials_recorded THEN tl.proactive_hints END AS proactive_hints,
       CASE WHEN ha.recorded THEN COALESCE(tl.head_away_count, 0) END AS head_away_count,
       CASE WHEN ha.recorded THEN COALESCE(tl.head_away_ms, 0) END AS head_away_ms,
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
    return Response(out.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})

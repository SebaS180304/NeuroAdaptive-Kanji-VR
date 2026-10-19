"""
Research dashboard, read side (skill research-dashboard-conventions). GET only:
the dashboard never writes through this router. Each endpoint reads views or
projected tables with one SQL query; what the screens need and the database lacks
goes into a migration, not into the frontend.
"""

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.research import ResearchParticipant, ResearchSession, ResearchSessionDetail, SessionTimeline

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


# Assistance has no interval table: LAL is set on each state entry and by each applied
# LAL change, and holds until the next one (runs of the same level are merged).
_TIMELINE = text("""
WITH ev AS (
    SELECT bool_or(e.event_type = 'STATE_ENTERED') AS states,
           bool_or(e.event_type = 'ENVIRONMENT_APPLIED') AS env,
           bool_or(e.event_type = 'TRIAL_STARTED') AS trials,
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
                ORDER BY t.started_elapsed_ms), '[]') FROM trials t WHERE t.session_id = :session_id) END AS trials
FROM ev
""")


@router.get("/sessions/{session_id}/timeline", response_model=SessionTimeline)
async def get_timeline(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    row = dict((await db.execute(_TIMELINE, {"session_id": session_id})).one()._mapping)
    if not row.pop("found"):
        raise HTTPException(status_code=404, detail="session not found")
    return row

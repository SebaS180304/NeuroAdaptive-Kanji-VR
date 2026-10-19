"""
Research dashboard, read side (skill research-dashboard-conventions). GET only:
the dashboard never writes through this router. Each endpoint reads views or
projected tables with one SQL query; what the screens need and the database lacks
goes into a migration, not into the frontend.
"""

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.research import ResearchParticipant, ResearchSession

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


_SESSIONS = text("""
SELECT o.session_id, o.participant_id, p.external_code, o.condition, o.status, o.visit_number,
       o.created_at, o.projection_status,
       CASE WHEN o.trials_recorded THEN o.trial_count END AS trial_count,
       CASE WHEN o.decisions_recorded THEN o.decision_count END AS decision_count,
       o.accuracy::float AS accuracy, o.open_error_count
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

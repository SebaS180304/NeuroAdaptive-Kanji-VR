"""
Research dashboard, read side (skill research-dashboard-conventions). GET only:
the dashboard never writes through this router. Each endpoint reads views or
projected tables with one SQL query; what the screens need and the database lacks
goes into a migration, not into the frontend.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.research import ResearchParticipant

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

"""
Endpoints REST para el ciclo de vida de ExperimentSession.

`create_session` es la implementacion server-side de S0 (Session
Initialization): recibe participante + condicion + kanji set + seed +
versiones, crea la sesion y guarda el config snapshot completo
(spec 7.1: "No participant-facing adaptation. The state establishes
reproducibility and traceability.").
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.session import ExperimentSession, SessionConfigSnapshot
from app.schemas.session import SessionCreate, SessionRead, SessionStateUpdate
from app.services.session_clock import now_utc

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionRead, status_code=201)
async def create_session(
    payload: SessionCreate, db: AsyncSession = Depends(get_db)
) -> ExperimentSession:
    session = ExperimentSession(
        participant_id=payload.participant_id,
        condition=payload.condition,
        assigned_kanji_set=payload.assigned_kanji_set,
        visit_number=payload.visit_number,
        random_seed=payload.random_seed,
        software_version=payload.software_version,
        experiment_config_version=payload.experiment_config_version,
        controller_config_version=payload.controller_config_version,
        session_clock_started_at=now_utc(),
    )
    db.add(session)
    await db.flush()

    snapshot = SessionConfigSnapshot(session_id=session.id, config=payload.config)
    db.add(snapshot)

    await db.flush()
    await db.refresh(session)
    return session


@router.get("", response_model=list[SessionRead])
async def list_sessions(db: AsyncSession = Depends(get_db)) -> list[ExperimentSession]:
    result = await db.execute(
        select(ExperimentSession).order_by(ExperimentSession.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{session_id}", response_model=SessionRead)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)) -> ExperimentSession:
    session = await db.get(ExperimentSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return session


@router.patch("/{session_id}/state", response_model=SessionRead)
async def update_session_state(
    session_id: str, payload: SessionStateUpdate, db: AsyncSession = Depends(get_db)
) -> ExperimentSession:
    session = await db.get(ExperimentSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    session.current_state = payload.new_state
    await db.flush()
    await db.refresh(session)
    return session

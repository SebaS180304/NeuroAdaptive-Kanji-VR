"""
Endpoints REST para el ciclo de vida de ExperimentSession.

`create_session` es la implementacion server-side de S0 (Session
Initialization): recibe participante + condicion + kanji set + seed +
versiones, crea la sesion y guarda el config snapshot completo
(spec 7.1: "No participant-facing adaptation. The state establishes
reproducibility and traceability.").
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adaptation import learner_profile
from app.db.session import get_db
from app.models.participant import Participant
from app.models.pretest import KanjiSubstitution
from app.models.session import (
    ExperimentSession,
    GameFlowState,
    SessionConfigSnapshot,
    SessionStatus,
)
from app.pretest.rules import contract
from app.schemas.session import SessionCreate, SessionRead, SessionStateUpdate
from app.services.session_clock import now_utc

router = APIRouter(prefix="/sessions", tags=["sessions"])

PRETEST_URL = "http://127.0.0.1:5300/pretest"


async def _read(db: AsyncSession, session: ExperimentSession) -> SessionRead:
    """SessionRead plus kanji_items: the assigned set with the participant's substitutes."""
    sets = contract()["sets"]
    items = None
    if session.assigned_kanji_set in sets:
        char_of = {k["id"]: k["kanji"] for k in contract()["kanji"]}
        rows = (await db.execute(select(KanjiSubstitution).where(
            KanjiSubstitution.participant_id == session.participant_id,
            KanjiSubstitution.substitute_kanji_id.is_not(None)))).scalars()
        swap = {char_of[r.original_kanji_id]: char_of[r.substitute_kanji_id] for r in rows}
        items = [swap.get(c, c) for c in sets[session.assigned_kanji_set]]
    return SessionRead.model_validate(session).model_copy(update={"kanji_items": items})


@router.post("", response_model=SessionRead, status_code=201)
async def create_session(
    payload: SessionCreate, db: AsyncSession = Depends(get_db)
) -> SessionRead:
    participant = await db.get(Participant, payload.participant_id)
    if participant is None:
        raise HTTPException(status_code=404, detail="participant not found")
    # Every visit, not only the first: the session must use the participant's effective set.
    if participant.pretest_completed_at is None:
        raise HTTPException(status_code=409,
                            detail=f"participant must complete the kanji pre-test at {PRETEST_URL} first")

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
    return await _read(db, session)


@router.get("", response_model=list[SessionRead])
async def list_sessions(db: AsyncSession = Depends(get_db)) -> list[SessionRead]:
    result = await db.execute(
        select(ExperimentSession).order_by(ExperimentSession.created_at.desc())
    )
    # shortcut: one substitution query per session; batch it if this list grows past a few hundred.
    return [await _read(db, s) for s in result.scalars().all()]


@router.get("/{session_id}", response_model=SessionRead)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> SessionRead:
    session = await db.get(ExperimentSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return await _read(db, session)


def _status_for(state: GameFlowState) -> SessionStatus:
    """El status se DERIVA del estado; no se declara aparte.

    Hasta el 16 de septiembre `status` se quedaba en CREATED durante toda la
    vida de la sesion, porque nadie lo actualizaba nunca. Una sesion completa y
    una abandonada a mitad se veian exactamente igual en la base.

    La alternativa obvia --que Unity mande tambien el status-- pone el mismo
    hecho en dos sitios: el cliente podria decir COMPLETED con current_state en
    S5, y la fila se contradiria a si misma sin que nada fallara. Derivarlo aqui
    hace esa contradiccion imposible en vez de improbable.

    ABORTED no sale de aqui a proposito: no es una funcion del estado, sino de
    que la sesion se interrumpiera. Lo marca el investigador.
    """
    if state == GameFlowState.S0_SESSION_INITIALIZATION:
        return SessionStatus.CREATED
    if state in (GameFlowState.S9_SESSION_SUMMARY, GameFlowState.S10_HCI_SELF_REPORT):
        return SessionStatus.COMPLETED
    return SessionStatus.IN_PROGRESS


@router.patch("/{session_id}/state", response_model=SessionRead)
async def update_session_state(
    session_id: uuid.UUID, payload: SessionStateUpdate, background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> SessionRead:
    session = await db.get(ExperimentSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")

    session.current_state = payload.new_state

    # Una sesion ABORTED no vuelve sola a IN_PROGRESS porque llegue un estado
    # tardio: abortar es una decision del investigador y este endpoint no la
    # revierte.
    if session.status != SessionStatus.ABORTED:
        session.status = _status_for(payload.new_state)
        if session.status == SessionStatus.COMPLETED and session.completed_at is None:
            session.completed_at = now_utc()
            # Runs after get_db commits (D-F6-3); a failure is logged, never returned.
            background.add_task(learner_profile.refresh, [session.participant_id])

    await db.flush()
    await db.refresh(session)
    return await _read(db, session)

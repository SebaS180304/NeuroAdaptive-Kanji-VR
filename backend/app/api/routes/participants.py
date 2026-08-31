from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.participant import Participant
from app.schemas.participant import ParticipantCreate, ParticipantRead

router = APIRouter(prefix="/participants", tags=["participants"])


@router.post("", response_model=ParticipantRead, status_code=201)
async def create_participant(
    payload: ParticipantCreate, db: AsyncSession = Depends(get_db)
) -> Participant:
    existing = await db.execute(
        select(Participant).where(Participant.external_code == payload.external_code)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="external_code already exists")

    participant = Participant(**payload.model_dump())
    db.add(participant)
    await db.flush()
    await db.refresh(participant)
    return participant


@router.get("", response_model=list[ParticipantRead])
async def list_participants(db: AsyncSession = Depends(get_db)) -> list[Participant]:
    result = await db.execute(select(Participant).order_by(Participant.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{participant_id}", response_model=ParticipantRead)
async def get_participant(participant_id: str, db: AsyncSession = Depends(get_db)) -> Participant:
    participant = await db.get(Participant, participant_id)
    if participant is None:
        raise HTTPException(status_code=404, detail="participant not found")
    return participant

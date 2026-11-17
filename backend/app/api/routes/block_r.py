"""
Block R's free recall form (V1.12, D-F6-226; scoring rule D-F6-225). The portal's second and last write
(D-F6-230 (1)): it lives under /sessions, never under /research, which stays read-only.

The researcher marks, for each kanji of the EVALUATED session (D-F6-190), whether the participant recalled its
meaning and its reading, the order of the first mark and what they said. Each save is a BLOCK_R_FREE_RECALL event;
the last one is the recall. Never saved = not recorded (null); saved with no marks = nothing recalled (0), D9.
Nothing here reaches the engine: it decides on S7 trials only.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.sessions import _items
from app.db.session import get_db
from app.models.participant import Participant
from app.models.session import ExperimentSession
from app.models.system_event import SessionEvent
from app.pretest.rules import contract

router = APIRouter(prefix="/sessions", tags=["block-r"])

EVENT = "BLOCK_R_FREE_RECALL"


class RecallItem(BaseModel):
    kanji_id: str
    meaning: bool
    reading: bool
    order: int | None = Field(default=None, ge=1, le=5)   # set on the first mark, null while nothing is marked
    said: str | None = Field(default=None, max_length=500)


class RecallSave(BaseModel):
    items: list[RecallItem]
    anything_else: str | None = Field(default=None, max_length=2000)


class TaughtKanji(BaseModel):
    kanji_id: str
    kanji: str
    meaning: str
    reading: str


class SavedRecall(BaseModel):
    saved_at: datetime
    recalled: int                     # kanji with at least one mark
    items: list[RecallItem]
    anything_else: str | None


class RecallForm(BaseModel):
    session_id: uuid.UUID
    participant_code: str
    visit_number: int
    evaluated_session_id: uuid.UUID
    evaluated_kanji_set: str | None
    learned_at: datetime | None       # when the evaluated session ended (or started, if it has no end)
    kanji: list[TaughtKanji]          # the evaluated set, substitutes in place, in the set's order
    board_text: list[str]             # R1 as the VR shows it (Contenido_UI_Bloque_R.md, kanji_content.json)
    saved: SavedRecall | None


async def _context(db: AsyncSession, session_id: uuid.UUID):
    session = await db.get(ExperimentSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if session.evaluated_session_id is None:
        raise HTTPException(status_code=409, detail="this session has no block R (no evaluated session)")
    evaluated = await db.get(ExperimentSession, session.evaluated_session_id)
    by_char = {k["kanji"]: k for k in contract()["kanji"]}
    chars = await _items(db, evaluated.participant_id, evaluated.assigned_kanji_set) or []
    kanji = [TaughtKanji(kanji_id=by_char[c]["id"], kanji=c, meaning=by_char[c]["meaning"], reading=by_char[c]["targetReading"])
             for c in chars]
    return session, evaluated, kanji


async def _form(db: AsyncSession, session, evaluated, kanji) -> RecallForm:
    code = (await db.execute(select(Participant.external_code).where(Participant.id == session.participant_id))).scalar_one()
    last = (await db.execute(select(SessionEvent.payload).where(
        SessionEvent.session_id == session.id, SessionEvent.event_type == EVENT).order_by(SessionEvent.id.desc()).limit(1))
    ).scalar_one_or_none()
    return RecallForm(session_id=session.id, participant_code=code, visit_number=session.visit_number,
                      evaluated_session_id=evaluated.id, evaluated_kanji_set=evaluated.assigned_kanji_set,
                      learned_at=evaluated.completed_at or evaluated.session_clock_started_at, kanji=kanji,
                      board_text=[contract()["retention"]["texts"][k] for k in ("retention.free_recall.main", "retention.free_recall.sub")],
                      saved=SavedRecall(**last) if last else None)


def _check(body: RecallSave, kanji: list[TaughtKanji]) -> None:
    """The five kanji of the evaluated set, once each; an order exactly on the marked ones, 1..k without repeats."""
    if sorted(i.kanji_id for i in body.items) != sorted(k.kanji_id for k in kanji):
        raise HTTPException(status_code=422, detail="items must be the evaluated session's kanji, once each")
    marked = [i for i in body.items if i.meaning or i.reading]
    if any((i.order is None) == (i.meaning or i.reading) for i in body.items):
        raise HTTPException(status_code=422, detail="order is set on the marked kanji only")
    if sorted(i.order for i in marked) != list(range(1, len(marked) + 1)):
        raise HTTPException(status_code=422, detail="order must be 1..k, one per marked kanji")


@router.get("/{session_id}/block-r/recall", response_model=RecallForm)
async def get_recall(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> RecallForm:
    return await _form(db, *await _context(db, session_id))


@router.post("/{session_id}/block-r/recall", response_model=RecallForm)
async def save_recall(session_id: uuid.UUID, body: RecallSave, db: AsyncSession = Depends(get_db)) -> RecallForm:
    session, evaluated, kanji = await _context(db, session_id)
    _check(body, kanji)
    now = datetime.now(timezone.utc)
    saved = SavedRecall(saved_at=now, recalled=sum(i.meaning or i.reading for i in body.items),
                        items=body.items, anything_else=body.anything_else)
    db.add(SessionEvent(session_id=session.id, event_type=EVENT,
                        payload={**saved.model_dump(mode="json"), "evaluated_session_id": str(evaluated.id)}))
    await db.commit()
    return await _form(db, session, evaluated, kanji)

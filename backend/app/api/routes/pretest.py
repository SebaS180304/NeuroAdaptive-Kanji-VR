"""
Kanji pre-test API (spec 13.2), used by the researcher page before the first visit.

The chain state is recomputed from the stored classifications on every request
(app/pretest/rules.py), so the server keeps no state between calls. Once the
pre-test is complete, its result is read from kanji_substitutions, never
recomputed: a later content change must not move a participant's kanji.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.participant import Participant
from app.models.pretest import KanjiPretestResponse, KanjiSubstitution
from app.pretest.rules import UNKNOWN, auto_grade, chain_state, classify, contract
from app.schemas.pretest import (
    Flagged, PretestAnswer, PretestCheck, PretestGrade, PretestItem, PretestState, Substitution,
)

router = APIRouter(prefix="/participants/{participant_id}/pretest", tags=["pretest"])


def _ids() -> tuple[dict[str, str], dict[str, str]]:
    by_char = {k["kanji"]: k["id"] for k in contract()["kanji"]}
    return by_char, {v: k for k, v in by_char.items()}


async def _participant(db: AsyncSession, participant_id: uuid.UUID, lock: bool = False) -> Participant:
    query = select(Participant).where(Participant.id == participant_id)
    if lock:
        query = query.with_for_update()   # one answer at a time per participant
    participant = (await db.execute(query)).scalar_one_or_none()
    if participant is None:
        raise HTTPException(status_code=404, detail="participant not found")
    return participant


async def _consented(db: AsyncSession, participant_id: uuid.UUID, lock: bool = False) -> Participant:
    """The participant, for a route that writes or grades: no pre-test without recorded consent."""
    participant = await _participant(db, participant_id, lock)
    if not participant.consent_obtained:
        raise HTTPException(status_code=409, detail="consent not recorded")
    return participant


async def _responses(db: AsyncSession, participant_id: uuid.UUID) -> list[KanjiPretestResponse]:
    result = await db.execute(select(KanjiPretestResponse)
                              .where(KanjiPretestResponse.participant_id == participant_id)
                              .order_by(KanjiPretestResponse.seq))
    return list(result.scalars().all())


def _classifications(responses: list[KanjiPretestResponse]) -> dict[str, str]:
    _, char_of = _ids()
    return {char_of[r.kanji_id]: r.classification for r in responses}


async def _state(db: AsyncSession, participant: Participant) -> PretestState:
    responses = await _responses(db, participant.id)
    by_char, char_of = _ids()

    if participant.pretest_completed_at is not None:
        rows = (await db.execute(select(KanjiSubstitution)
                                 .where(KanjiSubstitution.participant_id == participant.id))).scalars().all()
        order = [c for m in contract()["sets"].values() for c in m]
        rows = sorted(rows, key=lambda r: order.index(char_of[r.original_kanji_id]))
        return PretestState(
            completed=True, completed_at=participant.pretest_completed_at,
            answered=len(responses), next=None,
            substitutions=[Substitution(set=r.set_name, original=char_of[r.original_kanji_id],
                                        substitute=char_of[r.substitute_kanji_id])
                           for r in rows if r.substitute_kanji_id is not None],
            flagged=[Flagged(set=r.set_name, original=char_of[r.original_kanji_id])
                     for r in rows if r.substitute_kanji_id is None])

    cs = chain_state(_classifications(responses))
    return PretestState(
        completed=False, completed_at=None, answered=len(responses),
        next=PretestItem(kanji_id=by_char[cs.next], kanji=cs.next) if cs.next else None,
        substitutions=[Substitution(set=s, original=o, substitute=r) for s, o, r in cs.substitutions],
        flagged=[Flagged(set=s, original=o) for s, o in cs.flagged])


@router.get("", response_model=PretestState)
async def get_pretest(participant_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> PretestState:
    return await _state(db, await _participant(db, participant_id))


@router.post("/check", response_model=PretestGrade)
async def check_answer(participant_id: uuid.UUID, payload: PretestCheck,
                       db: AsyncSession = Depends(get_db)) -> PretestGrade:
    """Auto-grade only; nothing is stored. The page shows it for the researcher to review."""
    await _consented(db, participant_id)
    _, char_of = _ids()
    if payload.kanji_id not in char_of:
        raise HTTPException(status_code=422, detail="unknown kanji_id")
    reading_ok, meaning_ok = auto_grade(char_of[payload.kanji_id], payload.typed_reading, payload.typed_meaning)
    return PretestGrade(reading_correct=reading_ok, meaning_correct=meaning_ok)


@router.post("/responses", response_model=PretestState)
async def answer(participant_id: uuid.UUID, payload: PretestAnswer,
                 db: AsyncSession = Depends(get_db)) -> PretestState:
    participant = await _consented(db, participant_id, lock=True)
    if participant.pretest_completed_at is not None:
        raise HTTPException(status_code=409, detail="pre-test already completed")

    responses = await _responses(db, participant.id)
    classifications = _classifications(responses)
    by_char, char_of = _ids()
    expected = chain_state(classifications).next
    if expected is None or payload.kanji_id != by_char[expected]:
        # Double submit, a second tab, or a stale page: the page reloads the state.
        raise HTTPException(status_code=409, detail=f"expected kanji {expected}")

    char = char_of[payload.kanji_id]
    row = KanjiPretestResponse(participant_id=participant.id, kanji_id=payload.kanji_id,
                               seq=len(responses) + 1, self_report=payload.self_report,
                               classification=UNKNOWN)
    if payload.self_report != "NO":
        row.typed_reading, row.typed_meaning = payload.typed_reading, payload.typed_meaning
        row.reading_correct_auto, row.meaning_correct_auto = auto_grade(
            char, payload.typed_reading, payload.typed_meaning)
        row.reading_correct, row.meaning_correct = payload.reading_correct, payload.meaning_correct
        row.classification = classify(payload.self_report, payload.reading_correct, payload.meaning_correct)
    db.add(row)
    classifications[char] = row.classification

    done = chain_state(classifications)
    if done.next is None:
        # The result is written once, in the same transaction as the last answer.
        for s, o, r in done.substitutions:
            db.add(KanjiSubstitution(participant_id=participant.id, set_name=s,
                                     original_kanji_id=by_char[o], substitute_kanji_id=by_char[r]))
        for s, o in done.flagged:
            db.add(KanjiSubstitution(participant_id=participant.id, set_name=s,
                                     original_kanji_id=by_char[o], substitute_kanji_id=None))
        participant.pretest_completed_at = datetime.now(timezone.utc)
    await db.flush()
    return await _state(db, participant)

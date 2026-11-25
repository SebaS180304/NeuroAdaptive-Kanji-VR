"""
Kanji pre-test (spec 13.2). DDL in alembic/versions/sql/0004_kanji_pretest_up.sql.

kanji_id columns carry no ForeignKey here: kanji_items has no ORM model (it is
seeded by SQL), and the database already enforces the reference.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KanjiPretestResponse(Base):
    __tablename__ = "kanji_pretest_responses"

    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("participants.id", ondelete="CASCADE"), primary_key=True
    )
    kanji_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    seq: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    self_report: Mapped[str] = mapped_column(String(8), nullable=False)
    typed_reading: Mapped[str | None] = mapped_column(String(64))
    typed_meaning: Mapped[str | None] = mapped_column(String(64))
    reading_correct_auto: Mapped[bool | None] = mapped_column(Boolean)
    meaning_correct_auto: Mapped[bool | None] = mapped_column(Boolean)
    reading_correct: Mapped[bool | None] = mapped_column(Boolean)
    meaning_correct: Mapped[bool | None] = mapped_column(Boolean)
    classification: Mapped[str] = mapped_column(String(16), nullable=False)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class KanjiSubstitution(Base):
    __tablename__ = "kanji_substitutions"

    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("participants.id", ondelete="CASCADE"), primary_key=True
    )
    set_name: Mapped[str] = mapped_column(String(1), nullable=False)
    original_kanji_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    # NULL = KNOWN with no valid substitute left (flagged).
    substitute_kanji_id: Mapped[str | None] = mapped_column(String(32))

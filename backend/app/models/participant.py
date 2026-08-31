"""
Participant: metadata de screening definida en la seccion 13.1 del
Game Flow v1 Unity Design Specification.

Nota de privacidad: no se guarda nombre ni ningun identificador
directo. `external_code` es el codigo pseudonimizado que el
investigador asigna fuera del sistema (p. ej. "P01"); el mapeo entre
codigo y persona real vive fuera de esta base de datos, como
corresponde a datos de investigacion con participantes humanos.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Participant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "participants"

    external_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)

    # --- Screening metadata (spec 13.1) ---
    age_range: Mapped[str | None] = mapped_column(String(32), nullable=True)
    previous_japanese_experience: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    previous_kanji_experience: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    previous_vr_experience: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    self_rated_attention_difficulty: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # --- Consentimiento (dependencia critica marcada como pendiente de confirmar) ---
    consent_obtained: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_obtained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sessions: Mapped[list["ExperimentSession"]] = relationship(  # noqa: F821
        back_populates="participant", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Participant {self.external_code}>"

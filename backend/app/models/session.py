"""
ExperimentSession + SessionConfigSnapshot.

Corresponde al estado S0 (Session Initialization) del Game Flow v1:
participante, condicion experimental, kanji set asignado, seed
pseudoaleatoria y versiones de configuracion (spec seccion 7.1).

`current_state` refleja en que estado S0-S10 del GameFlowController
esta la sesion; se actualiza via SessionEvent (STATE_ENTERED) desde
Unity por WebSocket. El detalle fino de cada estado (trial data
contract completo, adaptation events, EEG windows) se modela en fases
posteriores -- ver docstring de app/models/__init__.py.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ExperimentalCondition(str, enum.Enum):
    """Seccion 10 del Game Flow v1: las tres condiciones comparten flujo
    y solo difieren en fuentes de datos permitidas para adaptar."""

    STATIC = "STATIC"
    BEHAVIOR_ADAPTIVE = "BEHAVIOR_ADAPTIVE"
    MULTIMODAL_ADAPTIVE = "MULTIMODAL_ADAPTIVE"


class SessionStatus(str, enum.Enum):
    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


class GameFlowState(str, enum.Enum):
    """Estados S0-S10 formales (spec seccion 7)."""

    S0_SESSION_INITIALIZATION = "S0_SESSION_INITIALIZATION"
    S1_WELCOME_ORIENTATION = "S1_WELCOME_ORIENTATION"
    S2_VR_TUTORIAL = "S2_VR_TUTORIAL"
    S3_SYSTEM_VALIDATION = "S3_SYSTEM_VALIDATION"
    S4_EEG_BASELINE = "S4_EEG_BASELINE"
    S5_STANDARDIZED_LEARNING = "S5_STANDARDIZED_LEARNING"
    S6_GUIDED_PRACTICE_CALIBRATION = "S6_GUIDED_PRACTICE_CALIBRATION"
    S7_EXPERIMENTAL_RETRIEVAL = "S7_EXPERIMENTAL_RETRIEVAL"
    S8_IMMEDIATE_ASSESSMENT = "S8_IMMEDIATE_ASSESSMENT"
    S9_SESSION_SUMMARY = "S9_SESSION_SUMMARY"
    S10_HCI_SELF_REPORT = "S10_HCI_SELF_REPORT"


condition_enum = PGEnum(ExperimentalCondition, name="experimental_condition", create_type=True)
status_enum = PGEnum(SessionStatus, name="session_status", create_type=True)
game_flow_state_enum = PGEnum(GameFlowState, name="game_flow_state", create_type=True)


class ExperimentSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "experiment_sessions"

    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("participants.id", ondelete="CASCADE"), nullable=False
    )
    condition: Mapped[ExperimentalCondition] = mapped_column(condition_enum, nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        status_enum, nullable=False, default=SessionStatus.CREATED
    )
    current_state: Mapped[GameFlowState] = mapped_column(
        game_flow_state_enum, nullable=False, default=GameFlowState.S0_SESSION_INITIALIZATION
    )

    # Referencia al set de kanji asignado ("A" / "B" / "C"); el contenido
    # completo de KanjiLearningItem se modela en Fase 2 (M2).
    assigned_kanji_set: Mapped[str | None] = mapped_column(String(8), nullable=True)
    visit_number: Mapped[int] = mapped_column(default=1, nullable=False)
    random_seed: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Versionado para reproducibilidad exacta (spec 7.1)
    software_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    experiment_config_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    controller_config_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Session Clock de referencia (anteproyecto 5.3): el instante que Unity
    # y el WAVEX Adapter usan para sincronizar timestamps.
    session_clock_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    participant: Mapped["Participant"] = relationship(back_populates="sessions")  # noqa: F821
    config_snapshot: Mapped["SessionConfigSnapshot | None"] = relationship(
        back_populates="session", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ExperimentSession {self.id} condition={self.condition}>"


class SessionConfigSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    SESSION_CREATED: config snapshot completo (spec 7.1).

    Se guarda como JSONB flexible a proposito: en Fase 1 todavia no esta
    cerrado el contrato final de configuracion (thresholds, kanji set
    detallado, etc. estan marcados "to validate" en la spec). Esto evita
    reescribir el esquema relacional cada vez que se ajuste un parametro
    durante la validacion piloto.
    """

    __tablename__ = "session_config_snapshots"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiment_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    session: Mapped["ExperimentSession"] = relationship(back_populates="config_snapshot")

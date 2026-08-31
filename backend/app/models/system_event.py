"""
SystemValidationEvent + SessionEvent.

Estas dos tablas son el corazon del "walking skeleton" de la Fase 1:
permiten que Unity mande datos por WebSocket y que efectivamente
queden persistidos en PostgreSQL, cerrando el ciclo Unity -> Backend
-> DB que M1 (Technical Feasibility) pide validar.

- SystemValidationEvent: resultados de S3 (EEG & System Validation) --
  conexion WAVEX, latencia Quest-Backend, calidad de señal, clock
  offset. Es deliberadamente generico (JSONB `detail`) porque los
  umbrales de calidad EEG todavia estan "to validate" (spec seccion 16).

- SessionEvent: event log generico de proposito general para
  telemetria temprana (STATE_ENTERED, WS_PING, etc.). El vocabulario
  de eventos conductuales completo (TRIAL_STARTED, HEAD_AWAY, etc. --
  spec seccion 11.1) se instrumenta formalmente en Fase 3.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ValidationComponent(str, enum.Enum):
    UNITY_BACKEND_WS = "UNITY_BACKEND_WS"
    WAVEX_EEG = "WAVEX_EEG"
    CLOCK_SYNC = "CLOCK_SYNC"
    OTHER = "OTHER"


class ValidationStatus(str, enum.Enum):
    OK = "OK"
    WARNING = "WARNING"
    ERROR = "ERROR"


validation_component_enum = PGEnum(
    ValidationComponent, name="validation_component", create_type=True
)
validation_status_enum = PGEnum(ValidationStatus, name="validation_status", create_type=True)


class SystemValidationEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "system_validation_events"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("experiment_sessions.id", ondelete="CASCADE"), nullable=False
    )
    component: Mapped[ValidationComponent] = mapped_column(validation_component_enum, nullable=False)
    status: Mapped[ValidationStatus] = mapped_column(validation_status_enum, nullable=False)

    # Ej: {"latency_ms": 42, "packet_loss_pct": 0.0, "signal_quality": "ACCEPTABLE",
    #      "clock_offset_ms": 3.1, "message": "WAVEX stream nominal"}
    detail: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Timestamp que reporta el cliente (Unity/WAVEX adapter) vs. el momento
    # en que el backend efectivamente lo recibe -- la diferencia es
    # justamente lo que se usa para estimar latencia/clock offset.
    client_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SessionEvent(TimestampMixin, Base):
    __tablename__ = "session_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("experiment_sessions.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    client_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    server_received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.session import ExperimentalCondition, GameFlowState, SessionStatus


class SessionCreate(BaseModel):
    participant_id: uuid.UUID
    condition: ExperimentalCondition
    assigned_kanji_set: str | None = None
    visit_number: int = 1
    random_seed: str | None = None
    software_version: str | None = None
    experiment_config_version: str | None = None
    controller_config_version: str | None = None
    config: dict = {}


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    participant_id: uuid.UUID
    condition: ExperimentalCondition
    status: SessionStatus
    current_state: GameFlowState
    assigned_kanji_set: str | None
    visit_number: int
    random_seed: str | None
    session_clock_started_at: datetime | None
    created_at: datetime


class SessionStateUpdate(BaseModel):
    """Usado por Unity (o por pruebas manuales) para avanzar current_state."""

    new_state: GameFlowState
    client_timestamp: datetime | None = None

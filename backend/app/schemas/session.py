import uuid
from typing import Literal
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.session import ExperimentalCondition, GameFlowState, SessionStatus


class SessionCreate(BaseModel):
    participant_id: uuid.UUID
    condition: ExperimentalCondition
    assigned_kanji_set: Literal["A", "B", "C"]  # D-F6-187: as the seed, no session without its set
    visit_number: int = 1
    random_seed: str = Field(pattern=r"\S")  # D-F6-183: without it the session cannot be reconstructed
    # D-F6-223: deduced for visit >= 2 when not given (the last COMPLETED session of the previous visit)
    evaluated_session_id: uuid.UUID | None = None
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
    # The effective set: the characters of assigned_kanji_set, each pre-test substitute
    # in its original's position. None when no set is assigned.
    kanji_items: list[str] | None = None
    # Block R (D-F6-190): the session it evaluates and that session's effective set; None on visit 1.
    evaluated_session_id: uuid.UUID | None = None
    evaluated_kanji_set: str | None = None
    evaluated_kanji_items: list[str] | None = None


class SessionStateUpdate(BaseModel):
    """Usado por Unity (o por pruebas manuales) para avanzar current_state."""

    new_state: GameFlowState
    client_timestamp: datetime | None = None

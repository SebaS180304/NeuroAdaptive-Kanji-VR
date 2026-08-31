import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.system_event import ValidationComponent, ValidationStatus


class SystemValidationEventCreate(BaseModel):
    session_id: uuid.UUID
    component: ValidationComponent
    status: ValidationStatus
    detail: dict = {}
    client_timestamp: datetime | None = None


class SystemValidationEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    component: ValidationComponent
    status: ValidationStatus
    detail: dict
    client_timestamp: datetime | None
    received_at: datetime


class SessionEventCreate(BaseModel):
    session_id: uuid.UUID
    event_type: str
    payload: dict = {}
    client_timestamp: datetime | None = None

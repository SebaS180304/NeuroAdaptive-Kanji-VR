"""
Read-only views for the research dashboard (/research). NULL means "not recorded"
or "not known yet", never zero (skill rule 3, D9).
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ResearchParticipant(BaseModel):
    """One row of the participant list (V1.11)."""
    id: uuid.UUID
    external_code: str
    created_at: datetime
    pretest_status: Literal["NOT_STARTED", "IN_PROGRESS", "COMPLETED"]
    pretest_answered: int
    pretest_completed_at: datetime | None
    session_count: int
    conditions: list[Literal["STATIC", "BEHAVIOR_ADAPTIVE", "MULTIMODAL_ADAPTIVE"]]
    last_session_at: datetime | None
    # Answered S5-S8 trials of the last session (v_session_overview); None when none was answered.
    last_session_accuracy: float | None
    previous_japanese_experience: bool | None
    # Kanji kept with no substitute; None until the pre-test is complete.
    flagged_count: int | None


class ResearchSession(BaseModel):
    """One row of the session list (V1.1), from v_session_overview."""
    session_id: uuid.UUID
    participant_id: uuid.UUID
    external_code: str
    condition: Literal["STATIC", "BEHAVIOR_ADAPTIVE", "MULTIMODAL_ADAPTIVE"]
    status: Literal["CREATED", "IN_PROGRESS", "COMPLETED", "ABORTED"]
    visit_number: int
    created_at: datetime
    # NO_DATA: no events; NOT_PROJECTED: events but no session_states rows.
    projection_status: Literal["NO_DATA", "NOT_PROJECTED", "PROJECTED"]
    # None when the event type was never recorded in the session (0.3 criterion), not zero.
    trial_count: int | None
    decision_count: int | None
    # Answered S5-S8 trials; None when none was answered.
    accuracy: float | None
    open_error_count: int

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

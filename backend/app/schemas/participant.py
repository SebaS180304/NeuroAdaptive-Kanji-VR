import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

# Registration options approved by Sebas on 17 Oct (tasks/plan.md); None = "Prefer not to answer".
AgeRange = Literal["18-24", "25-34", "35-44", "45+"]
AttentionDifficulty = Literal["NEVER", "RARELY", "SOMETIMES", "OFTEN", "VERY_OFTEN"]


class ParticipantCreate(BaseModel):
    external_code: str
    age_range: AgeRange | None = None
    previous_japanese_experience: bool | None = None
    previous_kanji_experience: bool | None = None
    previous_vr_experience: bool | None = None
    self_rated_attention_difficulty: AttentionDifficulty | None = None
    consent_obtained: bool = False


class ParticipantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    external_code: str
    age_range: str | None
    previous_japanese_experience: bool | None
    previous_kanji_experience: bool | None
    previous_vr_experience: bool | None
    self_rated_attention_difficulty: str | None
    consent_obtained: bool
    consent_obtained_at: datetime | None
    created_at: datetime

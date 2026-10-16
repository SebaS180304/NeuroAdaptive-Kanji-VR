from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class PretestItem(BaseModel):
    """What the page may show: the kanji only, never its reading or meaning."""
    kanji_id: str
    kanji: str


class Substitution(BaseModel):
    set: str
    original: str
    substitute: str


class Flagged(BaseModel):
    set: str
    original: str


class PretestState(BaseModel):
    completed: bool
    completed_at: datetime | None
    answered: int
    next: PretestItem | None
    substitutions: list[Substitution]
    flagged: list[Flagged]


class PretestCheck(BaseModel):
    kanji_id: str
    typed_reading: str = Field(default="", max_length=64)
    typed_meaning: str = Field(default="", max_length=64)


class PretestGrade(BaseModel):
    reading_correct: bool
    meaning_correct: bool


class PretestAnswer(BaseModel):
    kanji_id: str
    self_report: Literal["NO", "UNSURE", "YES"]
    typed_reading: str = Field(default="", max_length=64)
    typed_meaning: str = Field(default="", max_length=64)
    # The researcher's final verdict (after reviewing the auto-grade).
    reading_correct: bool | None = None
    meaning_correct: bool | None = None

    @model_validator(mode="after")
    def _verdict_matches_self_report(self) -> "PretestAnswer":
        has_verdict = self.reading_correct is not None and self.meaning_correct is not None
        if self.self_report != "NO" and not has_verdict:
            raise ValueError("UNSURE/YES need reading_correct and meaning_correct")
        if self.self_report == "NO" and (self.reading_correct is not None or self.meaning_correct is not None):
            raise ValueError("NO has no prompts, so no verdict")
        return self

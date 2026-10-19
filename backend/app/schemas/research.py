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


class SessionStateVisit(BaseModel):
    """One visit to a Game Flow state, in order (session_states)."""
    state: str
    entered_elapsed_ms: int
    # None when the session was cut in this state.
    exited_elapsed_ms: int | None


class AdaptationSummary(BaseModel):
    """Decisions of the adaptive S7 (v_adaptations, adaptation_applications)."""
    decisions: int
    environment_changes: int
    assistance_changes: int
    # Every SKIPPED application, TIMEOUT skips with no decision id included.
    skipped_by_unity: int
    # Outcomes of the changes (NO_CHANGE has none); not_recorded = no ADAPTATION_OUTCOME yet.
    outcome_positive: int
    outcome_neutral: int
    outcome_negative: int
    outcome_uncertain: int
    outcome_not_recorded: int


class ResearchSessionDetail(ResearchSession):
    """Session View header and summary (V1.2)."""
    kanji_set: str | None
    # When the session clock started; None if it never did.
    started_at: datetime | None
    first_block: str | None
    last_block: str | None
    states: list[SessionStateVisit]
    # Over answered trials (trial_timeline, window of 3); None when none was answered.
    mean_rt_ms: float | None
    rt_cv_mean: float | None
    # None when no trial was recorded.
    hint_requests: int | None
    proactive_hints: int | None
    # During answered trials (trial_timeline). None when the session has no HEAD_AWAY
    # event (0.3 criterion: never recorded, not zero).
    head_away_count: int | None
    head_away_ms: int | None
    # None when no decision was recorded (every STATIC session).
    adaptations: AdaptationSummary | None

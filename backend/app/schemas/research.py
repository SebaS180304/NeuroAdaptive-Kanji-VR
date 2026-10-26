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
    # Last Game Flow state recorded (session_states), not experiment_sessions.current_state,
    # which can disagree with the events. None when no state was projected.
    last_state: str | None


class ParticipantSession(ResearchSession):
    """One row of "Sessions in order" (V1.8), with the Session View's own aggregates."""
    # Over answered trials (trial_timeline, window of 3); None when none was answered.
    mean_rt_ms: float | None
    # None when the session has no HEAD_AWAY event (never recorded, not zero).
    head_away_count: int | None
    head_away_ms: int | None
    # Recorded before the pre-test was completed (or it never was): the default kanji set.
    before_pretest: bool


class PretestSubstitution(BaseModel):
    set_name: str
    original: str
    # None: no valid substitute, the known kanji was kept and flagged.
    substitute: str | None


class ResearchParticipantDetail(ResearchParticipant):
    """Participant View (V1.8). Substitutions are empty until the pre-test is complete."""
    sessions: list[ParticipantSession]
    substitutions: list[PretestSubstitution]


class ProfileCalibration(BaseModel):
    """S6 of one completed session, as the estimator builds it (S6Profile.as_dict())."""
    session_id: str
    rt_ref: dict[str, float]              # by trial type; a fallback type holds the global median
    rt_ref_global: float | None
    rt_spread: float
    acc_ref: float | None
    idle_eff_ref: float | None
    away_ref_ms: float
    env_dwell_ref_ms: float
    orienting_rate_ref: float | None
    n_trials: int
    n_valid_rt: int
    reliability: float
    correct: int                          # S6 correct, of n
    n: int
    fallback_types: list[str]             # fewer than 3 valid trials: the global median is used


class ProfileAdaptationGroup(BaseModel):
    """Changes of completed sessions with the same state, cause, dimension and direction."""
    key: str                              # "<state>.<cause or NONE>.<dimension>.<UP|DOWN>", the V1.5 ?group=
    learner_state: str
    cause: str | None                     # FAST+NO_ENVIRONMENT: UNDERCHALLENGED with both conditions met
    dimension: str
    direction: Literal["UP", "DOWN"]
    count: int
    outcomes: dict[str, int]              # POSITIVE / NEUTRAL / NEGATIVE / UNCERTAIN / NOT_RECORDED
    outcome_reasons: dict[str, dict[str, int]]   # by outcome, the O4 reason (RESOLVED, INCOMPLETE...)
    decisions: dict[str, list[str]]       # session id -> decision ids
    last_decided_at: str | None           # ISO 8601, as stored; orders groups of equal count


class ProfileTrendPoint(BaseModel):
    """One completed session, oldest first."""
    session_id: str
    condition: str
    kanji_set: str | None
    created_at: str                       # ISO 8601, as stored
    s7_trials: int
    s7_correct: int
    s7_mean_rt_ms: float | None
    no_change: int | None                 # None for STATIC: it never adapts
    decisions_recorded: bool | None       # False: adaptive with no decision rows (before 0003)
    rules_version: str | None = None      # rules-v1 / rules-v2 (D-F6-92); None without decisions


class LearnerProfileData(BaseModel):
    calibrations: list[ProfileCalibration]
    adaptations: list[ProfileAdaptationGroup]
    trend: list[ProfileTrendPoint]


class LearnerProfile(BaseModel):
    """The stored Learner Profile v1 (migration 0007). No row yet: profile is None."""
    participant_id: uuid.UUID
    profile_version: str | None
    computed_at: datetime | None
    session_ids: list[uuid.UUID]          # the COMPLETED sessions it covers; ABORTED ones never
    profile: LearnerProfileData | None


class QualityCheckRow(BaseModel):
    """One discrepancy returned by a verify_*_fn()."""
    session_id: uuid.UUID
    check: str
    detail: str | None


class QualityCheck(BaseModel):
    name: str                   # the function without its _fn suffix, as V1.7 shows it
    rows: list[QualityCheckRow]  # empty: the check passes


class QualityError(BaseModel):
    """An open projection error (v_projection_errors)."""
    id: int
    event_id: int
    session_id: uuid.UUID
    event_type: str
    error_code: str
    detail: str | None
    # None when the event carries no session_elapsed_ms.
    session_elapsed_ms: int | None


class UnprojectedSession(BaseModel):
    session_id: uuid.UUID
    participant_id: uuid.UUID
    external_code: str
    created_at: datetime
    projection_status: Literal["NO_DATA", "NOT_PROJECTED"]


class DataQuality(BaseModel):
    """Data quality (V1.7)."""
    projected_sessions: int
    # Projected, with no open error and no discrepancy in any check.
    clean_sessions: int
    open_by_code: dict[str, int]
    resolved_errors: int
    checks: list[QualityCheck]
    open_errors: list[QualityError]
    not_projected: list[UnprojectedSession]


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


class TimelineState(BaseModel):
    state: str
    start_ms: int
    end_ms: int | None          # None: the session stopped in this state


class TimelineLevel(BaseModel):
    level: str
    start_ms: int
    end_ms: int | None          # None: in force until the end of the session


class TimelineTrial(BaseModel):
    trial_id: str
    block_state: str
    start_ms: int
    end_ms: int | None          # None: never completed
    is_correct: bool | None     # None: not answered


class TimelineHint(BaseModel):
    ms: int
    trial_id: str
    proactive: bool             # True: the proactive cue at the trial's start; False: a request


class TimelinePeripheral(BaseModel):
    ms: int
    event_index: int
    object_name: str


class TimelineDistractor(BaseModel):
    kind: Literal["DWELL", "ORIENTING"]
    start_ms: int               # onset
    duration_ms: int
    object_name: str


class TimelineHeadAway(BaseModel):
    start_ms: int               # onset
    end_ms: int | None          # None: no return before the session ended
    limit_crossed: str


class TimelineAdaptation(BaseModel):
    """A decision that changed something (NO_CHANGE is in the Adaptations tab)."""
    decision_id: str
    trial_id: str
    decided_ms: int
    action: str
    dimension: str
    from_level: str | None
    to_level: str
    learner_state: str
    unity_result: Literal["APPLIED", "SKIPPED"] | None   # None: Unity has not answered (pending or lost)
    skip_reason: str | None
    result_ms: int | None       # when Unity applied or skipped it
    # Start of the trial the cooldown runs to; the block's last trial end if that trial never ran.
    cooldown_until_ms: int | None
    outcome: str | None


class SessionTimeline(BaseModel):
    """Lanes of the Session View timeline (V1.3), in session_elapsed_ms.

    A lane is None when its event type never appears in the session (not recorded),
    and an empty list when it was recorded but has nothing to draw.
    """
    session_end_ms: int | None  # the last event; None with no events
    states: list[TimelineState] | None
    environment: list[TimelineLevel] | None
    assistance: list[TimelineLevel] | None
    trials: list[TimelineTrial] | None
    hints: list[TimelineHint] | None
    peripherals: list[TimelinePeripheral] | None
    distractors: list[TimelineDistractor] | None
    head_away: list[TimelineHeadAway] | None
    adaptations: list[TimelineAdaptation] | None


class ResearchTrial(BaseModel):
    """One row of the Trials tab and its inspector (V1.4): trial_timeline() plus the decision."""
    trial_id: str
    block_state: str
    trial_sequence: int | None
    trial_type: str | None
    kanji_id: str | None
    kanji_char: str | None
    is_primary_analysis: bool | None      # False: the S2 tutorial
    started_elapsed_ms: int | None
    completed_elapsed_ms: int | None  # None: not completed (the session ended)
    esl: str | None
    lal: str | None
    env_profile: str | None
    prop_count: int | None
    mover_count: int | None
    is_correct: bool | None
    response_time_ms: int | None
    timed_out: bool | None
    hint_count: int | None
    cue_trigger: str | None
    idle_ms: int | None
    # None when the event type was never recorded in the session (trial_timeline() says 0).
    head_away_count: int | None
    head_away_ms: int | None
    peripheral_event_count: int | None
    distractor_dwell_ms: int | None
    window_n: int | None
    window_accuracy: float | None
    window_rt_mean: float | None
    window_rt_cv: float | None
    # The decision made after this trial (adaptive S7); None when there was none.
    learner_state: str | None
    cause: str | None
    decision_confidence: float | None
    decision_action: str | None
    reason_code: str | None
    explanation: str | None
    dimension: str | None
    from_level: str | None
    to_level: str | None
    unity_result: str | None
    skip_reason: str | None
    applied_before_trial_id: str | None
    cooldown_until_trial: int | None
    cooldown_until_trial_id: str | None   # None when that trial never ran
    outcome: str | None
    estimator_version: str | None
    rules_version: str | None
    indicators: dict | None
    thresholds: dict | None


class ResearchAdaptation(BaseModel):
    """One decision of the Adaptations tab (V1.5): v_adaptations plus adaptation_decisions."""
    decision_id: str
    trial_id: str
    decided_elapsed_ms: int
    learner_state: str
    cause: str | None
    confidence: float
    action: str
    dimension: str | None
    from_level: str | None
    to_level: str | None
    proactive_cues: bool
    reason_code: str
    explanation: str
    unity_result: str | None              # None: Unity has not answered (pending or lost)
    skip_reason: str | None
    applied_before_trial_id: str | None
    cooldown_until_trial: int | None
    cooldown_until_trial_id: str | None   # None when that trial never ran
    outcome: str | None                   # None: not recorded yet
    estimator_version: str | None
    rules_version: str | None
    indicators: dict | None
    thresholds: dict | None


class PlannedTrial(BaseModel):
    trial_id: str
    # COMPLETED, STARTED (no completion: the session was cut) or NEVER_SHOWN.
    status: Literal["COMPLETED", "STARTED", "NEVER_SHOWN"]


class PlanBlock(BaseModel):
    """One generated block: its plan (planned_trials) against what ran (trials)."""
    block_state: str
    kanji_set: str | None
    block_seed: str | None      # a bigint; a string so no client rounds it
    planned: int
    started: int
    completed: int
    min_lag_requested: int | None
    # None with kanji_repeats False: the block repeats no kanji, so there is no lag (Unity sends -1).
    min_lag_achieved: int | None
    kanji_repeats: bool
    trials: list[PlannedTrial]


class SessionPlan(BaseModel):
    """Plan and execution tab (V1.6). Blocks never generated have no row."""
    last_state: str | None
    last_state_ms: int | None   # when the last state was entered
    blocks: list[PlanBlock]

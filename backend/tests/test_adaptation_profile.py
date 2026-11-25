"""
F5a estimator inputs: trial records, S6 profile and window indicators
(Planteamiento_Tecnico_F5a.md §4.1–4.2, D4, D5, D6).

Pure functions, no database: the recorded sessions of the F3 phase test come
from tests/fixtures/prueba_fase_f3_events.json (OBS_01 = 87761ce6, OBS_02 =
e550a567), and the edge cases (time away, environment events, timeouts) from
small synthetic event lists, since the recorded sessions have no HEAD_AWAY in
S6/S7 and no DISTRACTOR_INTERACTION yet.
"""

import json
from pathlib import Path

import pytest

from app.adaptation.indicators import s7_windows, window_indicators, window_trials
from app.adaptation.profile import SPREAD_FLOOR, build_profile
from app.adaptation.trials import S6_STATE, S7_STATE, TrialStreamBuilder, build_trials

FIXTURE = Path(__file__).parent / "fixtures" / "prueba_fase_f3_events.json"
OBS_01 = "87761ce6-c74d-4e9c-941f-8c3e0d8a64ad"
OBS_02 = "e550a567-31ba-4b9e-8229-7eefd15360f4"

T1 = "T1_MEANING_TO_KANJI"
T2 = "T2_KANJI_TO_MEANING"
T3 = "T3_KANJI_TO_READING"


@pytest.fixture(autouse=True)
def _clean_test_participants():
    """Overrides the conftest fixture: these tests do not touch the database."""
    yield


@pytest.fixture(scope="module")
def recorded():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    by_session = {}
    for event in data["events"]:  # already in arrival order (id)
        by_session.setdefault(event["session_id"], []).append(event)
    return {sid: build_trials(events) for sid, events in by_session.items()}


def _by_id(trials):
    return {t.trial_id: t for t in trials}


# -- synthetic event helpers -------------------------------------------------


def _state(state, t=0):
    return ("STATE_ENTERED", {"state": state, "esl": "MEDIUM", "lal": "MEDIUM", "session_elapsed_ms": t})


def _trial(trial_id, start, rt, correct=True, trial_type=T1, timed_out=False, idle=None, seq=None):
    answer = {
        "trial_id": trial_id,
        "trial_type": trial_type,
        "trial_sequence": seq,
        "is_correct": correct,
        "timed_out": timed_out,
        "response_time_ms": rt,
        "session_elapsed_ms": start + rt,
    }
    if idle is not None:
        answer["idle_ms"] = idle
    return [
        ("TRIAL_STARTED", {"trial_id": trial_id, "session_elapsed_ms": start}),
        ("ANSWER_SELECTED", answer),
    ]


def _completed(trial_id, t, idle=0, hints=0):
    return ("TRIAL_COMPLETED", {"trial_id": trial_id, "session_elapsed_ms": t, "idle_ms": idle, "hint_count": hints})


def _build(events):
    return build_trials({"event_type": e, "payload": p} for e, p in events)


# -- recorded sessions -------------------------------------------------------


def test_recorded_sessions_have_all_answered_trials(recorded):
    for sid in (OBS_01, OBS_02):
        trials = recorded[sid]
        assert len(trials) == 52
        assert sum(t.phase == "S6" for t in trials) == 9
        assert sum(t.phase == "S7" for t in trials) == 20
        # Recorded before §2.2: idle comes from TRIAL_COMPLETED.
        assert all(t.idle_ms is not None for t in trials if t.phase in ("S6", "S7"))


def test_profile_skips_first_s6_trial(recorded):
    profile = build_profile(recorded[OBS_01])
    assert profile.trial_ids[0] == "S6-002"
    assert profile.n_trials == 8
    assert "S6-001" not in profile.trial_ids  # the 11.8 s outlier (D6)


def test_profile_obs01_references(recorded):
    profile = build_profile(recorded[OBS_01])
    # T3 has only 2 valid trials (1947, 4580): it uses the global median.
    assert profile.rt_ref == {T1: 2313.0, T2: 2197.0, T3: 2275.5}
    assert profile.rt_ref_global == 2275.5
    assert profile.acc_ref == pytest.approx(7 / 8)  # S6-002 wrong
    assert profile.rt_spread == SPREAD_FLOOR  # raw MAD below the floor
    assert profile.rt_spread_raw < SPREAD_FLOOR
    assert profile.idle_eff_ref == 0.0
    assert profile.reliability == 1.0


def test_profile_obs02_references(recorded):
    profile = build_profile(recorded[OBS_02])
    assert profile.rt_ref == {T1: 2197.0, T2: 2502.0, T3: 4199.0}   # T2: 2 trials, global
    assert profile.acc_ref == 1.0
    assert profile.rt_spread == pytest.approx(profile.rt_spread_raw)
    assert profile.rt_spread > SPREAD_FLOOR
    assert profile.idle_eff_ref == pytest.approx(0.658, abs=0.001)


def test_recorded_sessions_have_no_away_or_env_signal_in_s6_s7(recorded):
    """Their HEAD_AWAY episodes are all in S1/S2/S9; no D5 events yet (§4.3)."""
    for sid in (OBS_01, OBS_02):
        for t in recorded[sid]:
            if t.phase in ("S6", "S7"):
                assert t.away_ms == 0
                assert t.env_dwell_ms == 0 and t.orienting_count == 0


def test_window_is_last_three_s7_trials(recorded):
    trials = recorded[OBS_01]
    assert [t.trial_id for t in window_trials(trials, "S7-009")] == ["S7-007", "S7-008", "S7-009"]
    assert [t.trial_id for t in window_trials(trials, "S7-002")] == ["S7-001", "S7-002"]
    with pytest.raises(ValueError):
        window_trials(trials, "S6-004")


def test_obs01_windows(recorded):
    trials = recorded[OBS_01]
    profile = build_profile(trials)
    windows = {w.last_trial_id: w for w in s7_windows(trials, profile)}
    assert len(windows) == 20

    # S7-001 (6.4 s wrong) and S7-003 (5.5 s wrong): two slow errors.
    w3 = windows["S7-003"]
    assert (w3.n, w3.slow_errors, w3.fast_errors) == (3, 2, 0)
    assert w3.acc_delta == pytest.approx(1 / 3 - 7 / 8)

    # S7-008 / S7-009: errors at 1.55 and 2.05 times the reference (T3 uses
    # the global median: only 2 valid T3 trials in S6). Two slow errors, in
    # S7-009 and again in S7-010: the case §4.3 expects to read as OVERLOADED.
    w9 = windows["S7-009"]
    assert w9.trial_rt_ratios == pytest.approx((2352 / 2197, 3532 / 2275.5, 4661 / 2275.5))
    assert w9.slow_errors == 2
    assert w9.rt_ratio == pytest.approx(3532 / 2275.5)
    assert w9.rt_z == pytest.approx((3532 / 2275.5 - 1) / SPREAD_FLOOR)
    assert windows["S7-010"].slow_errors == 2
    assert windows["S7-008"].slow_errors == 1

    # A window with no errors is at or above the S6 accuracy.
    assert windows["S7-016"].acc_delta == pytest.approx(1 - 7 / 8)
    assert windows["S7-016"].slow_errors == 0


def test_obs02_windows_never_show_errors(recorded):
    trials = recorded[OBS_02]
    profile = build_profile(trials)
    for w in s7_windows(trials, profile):
        assert w.acc_delta == 0.0
        assert w.fast_errors == 0 and w.slow_errors == 0
        assert w.away_ms == 0 and w.env_dwell_ms == 0
        assert w.rt_z < 2


def test_window_depends_only_on_trials_up_to_it(recorded):
    """Live and replay agree: a window never looks ahead (§2.1, principle 3)."""
    trials = recorded[OBS_01]
    profile = build_profile(trials)
    for i, t in enumerate(trials):
        if t.phase != "S7":
            continue
        prefix = trials[: i + 1]
        assert window_indicators(window_trials(prefix), profile) == window_indicators(
            window_trials(trials, t.trial_id), profile
        )


def test_peripheral_during_feedback_counts_for_next_trial(recorded):
    """OBS_01: the periphery of S7-005 fired 180 ms after its answer."""
    by_id = _by_id(recorded[OBS_01])
    assert by_id["S7-005"].peripheral_count == 0
    assert by_id["S7-006"].peripheral_count == 1
    assert by_id["S7-011"].peripheral_count == 1  # fired before its answer


# -- synthetic: profile edge cases -------------------------------------------


def test_type_with_one_valid_trial_uses_global_median():
    events = [_state(S6_STATE)]
    plan = [(T1, 3000), (T1, 2000), (T1, 2200), (T2, 2400), (T2, 2600), (T3, 9000)]
    start = 0
    for i, (trial_type, rt) in enumerate([(T1, 5000)] + plan, start=1):
        events += _trial(f"S6-{i:03d}", start, rt, trial_type=trial_type)
        start += rt + 1500
    profile = build_profile(_build(events))
    assert profile.n_trials == 6
    assert profile.rt_ref_global == 2500.0
    assert profile.rt_ref[T3] == 2500.0  # one T3 trial: global median
    assert profile.rt_ref[T1] == 2200.0


def test_timeouts_are_errors_without_rt():
    events = [_state(S6_STATE)]
    events += _trial("S6-001", 0, 9000)
    for i in range(2, 8):
        events += _trial(f"S6-{i:03d}", i * 10_000, 2000)
    events += _trial("S6-008", 80_000, 10_000, correct=False, timed_out=True)
    events += [_state(S7_STATE, 90_000)]
    events += _trial("S7-001", 100_000, 10_000, correct=False, timed_out=True)
    trials = _build(events)
    profile = build_profile(trials)
    assert profile.n_trials == 7 and profile.n_valid_rt == 6
    assert profile.rt_ref == {T1: 2000.0}
    assert profile.acc_ref == pytest.approx(6 / 7)
    w = window_indicators(window_trials(trials), profile)
    assert w.slow_errors == 1 and w.rt_ratio is None and w.rt_z is None


def test_low_reliability_with_few_valid_trials():
    events = [_state(S6_STATE)]
    for i in range(1, 6):
        events += _trial(f"S6-{i:03d}", i * 10_000, 2000)
    assert build_profile(_build(events)).reliability == 0.6


def test_fast_and_slow_errors_use_per_trial_ratio():
    events = [_state(S6_STATE)]
    for i in range(1, 8):
        events += _trial(f"S6-{i:03d}", i * 10_000, 2000)
    events += [_state(S7_STATE, 80_000)]
    events += _trial("S7-001", 90_000, 1000, correct=False)  # 0.5: fast
    events += _trial("S7-002", 100_000, 3000, correct=False)  # 1.5: slow
    events += _trial("S7-003", 110_000, 1100, correct=True)  # fast but correct
    trials = _build(events)
    w = window_indicators(window_trials(trials), build_profile(trials))
    assert (w.fast_errors, w.slow_errors) == (1, 1)
    assert w.acc == pytest.approx(1 / 3)


# -- synthetic: time away and effective idle (D4) ----------------------------


def test_away_overlap_and_effective_idle():
    events = [_state(S7_STATE)]
    # Trial 1: 10 000 → 16 000. Episode onset 11 000, 2 000 ms.
    events += [("TRIAL_STARTED", {"trial_id": "S7-001", "session_elapsed_ms": 10_000})]
    events += [("HEAD_AWAY", {"episode": 1, "session_elapsed_ms": 11_500, "onset_offset_ms": -500})]
    events += [("HEAD_RETURNED", {"episode": 1, "duration_ms": 2_000, "session_elapsed_ms": 13_000})]
    events += [
        ("ANSWER_SELECTED", {"trial_id": "S7-001", "trial_type": T1, "is_correct": True,
                             "timed_out": False, "response_time_ms": 6_000,
                             "session_elapsed_ms": 16_000, "idle_ms": 3_000})
    ]
    # Feedback: an episode entirely between trials does not count.
    events += [("HEAD_AWAY", {"episode": 2, "session_elapsed_ms": 16_700, "onset_offset_ms": -500})]
    events += [("HEAD_RETURNED", {"episode": 2, "duration_ms": 800, "session_elapsed_ms": 17_000})]
    # Trial 2: 17 500 → 22 500. Episode from 21 000, still open at the answer.
    events += [("TRIAL_STARTED", {"trial_id": "S7-002", "session_elapsed_ms": 17_500})]
    events += [("HEAD_AWAY", {"episode": 3, "session_elapsed_ms": 21_500, "onset_offset_ms": -500})]
    events += [
        ("ANSWER_SELECTED", {"trial_id": "S7-002", "trial_type": T1, "is_correct": True,
                             "timed_out": False, "response_time_ms": 5_000,
                             "session_elapsed_ms": 22_500, "idle_ms": 1_000})
    ]
    t1, t2 = _build(events)
    assert t1.away_ms == 2_000 and t1.idle_eff_ms == 1_000
    assert t2.away_ms == 1_500 and t2.idle_eff_ms == 0  # floored at 0


def test_episode_starting_before_the_trial_counts_from_trial_start():
    events = [_state(S7_STATE)]
    events += [("HEAD_AWAY", {"episode": 1, "session_elapsed_ms": 9_500, "onset_offset_ms": -500})]
    events += _trial("S7-001", 10_000, 4_000, idle=0)
    events += [("HEAD_RETURNED", {"episode": 1, "duration_ms": 3_000, "session_elapsed_ms": 12_000})]
    (t,) = _build(events)
    # Open at the answer (14 000): 9 000 → 14 000 overlaps 10 000 → 14 000.
    assert t.away_ms == 4_000


def test_idle_from_answer_wins_over_trial_completed():
    events = [_state(S7_STATE)] + _trial("S7-001", 0, 3000, idle=1200)
    events += [_completed("S7-001", 4500, idle=9999, hints=1)]
    (t,) = _build(events)
    assert t.idle_ms == 1200 and t.hint_count == 1


def test_builder_returns_record_at_answer():
    builder = TrialStreamBuilder()
    results = [builder.feed(e, p) for e, p in [_state(S7_STATE)] + _trial("S7-001", 0, 2000)]
    assert results[:-1] == [None, None]
    assert results[-1].trial_id == "S7-001"


# -- synthetic: environment interactions (D5) --------------------------------


def _dwell(ms):
    return ("DISTRACTOR_INTERACTION", {"kind": "DWELL", "duration_ms": ms, "object_name": "Clock"})


def _orienting():
    return ("DISTRACTOR_INTERACTION", {"kind": "ORIENTING", "duration_ms": 600, "object_name": "PeripheralEvent_Shelf"})


def _peripheral():
    return ("PERIPHERAL_EVENT", {"object_name": "PeripheralEvent_Shelf", "duration_ms": 1500})


def test_env_events_count_for_open_trial_or_next():
    events = [_state(S6_STATE)]
    for i in range(1, 8):
        events += _trial(f"S6-{i:03d}", i * 10_000, 2000)
    events += [_state(S7_STATE, 80_000)]
    s7_1 = _trial("S7-001", 90_000, 3000)
    events += [s7_1[0], _dwell(1200), _peripheral(), s7_1[1]]
    events += [_orienting()]  # 2 s after the periphery: lands in the feedback
    s7_2 = _trial("S7-002", 95_000, 3000)
    events += [s7_2[0], _dwell(1100), s7_2[1]]
    events += _trial("S7-003", 100_000, 3000)
    trials = _build(events)
    by_id = _by_id(trials)
    assert (by_id["S7-001"].env_dwell_ms, by_id["S7-001"].peripheral_count) == (1200, 1)
    assert by_id["S7-001"].orienting_count == 0
    assert (by_id["S7-002"].env_dwell_ms, by_id["S7-002"].orienting_count) == (1100, 1)

    profile = build_profile(trials)
    assert profile.orienting_rate_ref is None  # no peripherals in S6
    w = window_indicators(window_trials(trials), profile)
    assert w.env_dwell_ms == 2300
    assert (w.orienting_count, w.peripheral_count, w.orienting_rate) == (1, 1, 1.0)


def test_pending_env_events_do_not_cross_states():
    events = [_state(S6_STATE)] + _trial("S6-009", 0, 2000)
    events += [_peripheral(), _orienting()]  # after the last S6 answer
    events += [_state(S7_STATE, 5000)] + _trial("S7-001", 8000, 2000)
    t = _by_id(_build(events))["S7-001"]
    assert (t.peripheral_count, t.orienting_count) == (0, 0)

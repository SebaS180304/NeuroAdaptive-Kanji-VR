"""
O2 (tasks/plan.md, Thu 19): option (2) of D-F6-242, off live (D-F6-246). The task sounds of S6–S8 (select and result)
are no longer trimmed; the stage sound and S5's AUDIO_ONSET stay trimmed (D-F6-255 (1)). A window with >= 1.5 x S6's
sound density neither confirms UNDERCHALLENGED nor leads (D-F6-147 (2)). The current rule stays byte-identical.
"""

import pytest

from app.adaptation.estimator import STABLE, UNDERCHALLENGED
from app.eeg import concordance, epochs, window


@pytest.fixture(autouse=True)
def _clean_test_participants():
    """Overrides the conftest fixture: no database here."""
    yield


def _m(t, event, state, **kw):
    return (t, {"schema_version": 1, "event": event, "state": state, "session_elapsed_ms": int(t * 1000), **kw})


S5, S6, S7 = "S5_STANDARDIZED_LEARNING", "S6_GUIDED_PRACTICE_CALIBRATION", "S7_EXPERIMENTAL_RETRIEVAL"
MARKERS = [
    _m(10.0, "AUDIO_ONSET", S5),
    _m(12.0, "ANSWER_SELECTED", S5, trial_id="S5-001"),
    _m(20.0, "STATE_ENTERED", S6, transition_sound_lead_ms=500),
    _m(30.0, "ANSWER_SELECTED", S6, trial_id="S6-001"),
    _m(31.0, "TRIAL_COMPLETED", S6, trial_id="S6-001", result_sound_offset_ms=300),
    _m(45.0, "STATE_ENTERED", S7),
    _m(50.0, "ANSWER_SELECTED", S7, trial_id="S7-001"),
]


def test_current_trims_every_sound_as_before() -> None:
    assert sorted(epochs.excluded_intervals(MARKERS)) == sorted(epochs.excluded_intervals(MARKERS, rule="current"))
    starts = sorted(a for a, _ in epochs.excluded_intervals(MARKERS))
    assert starts == [10.0, 12.0, 19.5, 30.0, 30.3, 50.0]


def test_nosound_keeps_the_task_sounds_of_s6_to_s8_and_trims_the_rest() -> None:
    starts = sorted(a for a, _ in epochs.excluded_intervals(MARKERS, rule="nosound"))
    assert starts == [10.0, 12.0, 19.5]   # S5 reading, S5 select (not S6–S8), the stage sound into S6


def test_sound_density_of_a_window_against_s6() -> None:
    onsets_ms, s6 = epochs.sound_density(MARKERS)
    assert onsets_ms == [10_000, 12_000, 19_500, 30_000, 30_300, 50_000]
    assert s6 == pytest.approx(2 / 25.0)   # S6 from its entry (20 s) to S7's (45 s): select and result


def _block(ei, dense):
    return concordance.block({"counted": True, "non_poor": 3, "clean_s": 9.0, "z": {"engagement_index": ei},
                              **({"dense": dense} if dense is not None else {})})


def test_a_dense_window_neither_confirms_underchallenged_nor_leads() -> None:
    assert concordance.effect(UNDERCHALLENGED, _block(-2.0, False), None) == concordance.CONFIRMED
    assert concordance.effect(UNDERCHALLENGED, _block(-2.0, True), None) == concordance.UNAVAILABLE
    assert concordance.effect(STABLE, _block(-2.0, False), _block(-2.0, False)) == concordance.LED
    assert concordance.effect(STABLE, _block(-2.0, True), _block(-2.0, False)) == concordance.UNAVAILABLE
    assert "dense" not in _block(-2.0, None)


def test_the_window_reports_density_only_when_asked() -> None:
    eps = [{"start_ms": s, "end_ms": s + 5000, "quality": "GOOD", "chunk_clean": [True] * 9,
            "engagement_index": 1.0, "theta_fz": 0.1, "alpha_parietal": 0.1, "theta_beta": 1.0} for s in range(0, 60_000, 2500)]
    ref = {"indices": {}}
    plain = window.evaluate(eps, 35_000, 52_000, ref)
    assert "dense" not in plain and "sounds_per_s" not in plain
    w = window.evaluate(eps, 35_000, 52_000, ref, sounds=([30_000, 30_300, 50_000], 2 / 25.0))
    assert w["sounds_per_s"] == pytest.approx(1 / 17.0) and w["dense"] is False   # one onset in [35, 52) s
    w = window.evaluate(eps, 28_000, 52_000, ref, sounds=([30_000, 30_300, 50_000], 2 / 25.0))
    assert w["sounds_per_s"] == pytest.approx(3 / 24.0) and w["dense"] is True    # 0.125 >= 1.5 x 0.08


# ---------- the live switch (D-F6-263 (4)): one setting, off by default ----------

from app.config import Settings  # noqa: E402


def test_the_live_rule_is_current_unless_switched_on(monkeypatch) -> None:
    monkeypatch.delenv("EEG_LIVE_RULE", raising=False)
    assert Settings(_env_file=None).eeg_live_rule == "current"
    monkeypatch.setenv("EEG_LIVE_RULE", "nosound")
    assert Settings(_env_file=None).eeg_live_rule == "nosound"
    monkeypatch.setenv("EEG_LIVE_RULE", "ica")
    with pytest.raises(ValueError):
        Settings(_env_file=None)


def test_session_events_give_the_same_sound_density_as_the_lsl_markers() -> None:
    """The backend decides from session_events (session ms), live.py and replay from LSL markers: same onsets."""
    events = [(m["event"], {k: v for k, v in m.items() if k != "event"}) for _, m in MARKERS]
    assert epochs.sound_density(epochs.markers_of_events(events)) == epochs.sound_density(MARKERS)

"""
F5a per-session adaptation state (Planteamiento_Tecnico_F5a.md §2.2): the live
path that the WebSocket feeds, over the recorded sessions of the F3 phase test
replayed as if they had been adaptive. No database.
"""

import json
from pathlib import Path

import pytest

from app.adaptation.rules import CHANGE_ASSISTANCE, COOLDOWN, NO_CHANGE
from app.adaptation.state import SessionAdaptationState

FIXTURE = Path(__file__).parent / "fixtures" / "prueba_fase_f3_events.json"
OBS_01 = "87761ce6-c74d-4e9c-941f-8c3e0d8a64ad"
OBS_02 = "e550a567-31ba-4b9e-8229-7eefd15360f4"


@pytest.fixture(autouse=True)
def _clean_test_participants():
    """Overrides the conftest fixture: these tests do not touch the database."""
    yield


@pytest.fixture(scope="module")
def events():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    out = {}
    for sid in (OBS_01, OBS_02):
        out[sid] = sorted((e for e in data["events"] if e["session_id"] == sid), key=lambda e: e["id"])
    return out


def _feed(condition, evs):
    state = SessionAdaptationState(condition)
    pending = [p for e in evs if (p := state.feed(e["event_type"], e.get("payload") or {})) is not None]
    return state, pending


def test_static_never_reaches_the_estimator(events):
    state, pending = _feed("STATIC", events[OBS_01])
    assert pending == [] and state.engine is None and state.profile is None


def test_one_decision_per_answered_s7_trial(events):
    _, pending = _feed("BEHAVIOR_ADAPTIVE", events[OBS_01])
    ids = [p.decision.trial_id for p in pending]
    assert ids == [f"S7-{i:03d}" for i in range(1, 21)]


def test_obs01_live_path_raises_assistance_at_s7_010(events):
    _, pending = _feed("BEHAVIOR_ADAPTIVE", events[OBS_01])
    d = {p.decision.trial_id: p for p in pending}
    first = next(p for p in pending if p.decision.action != NO_CHANGE)
    assert first.decision.trial_id == "S7-010"
    assert (first.decision.action, first.decision.to_level) == (CHANGE_ASSISTANCE, "HIGH")
    msg = first.message()
    assert msg["type"] == "DECISION" and msg["proactive_cues"] is True and msg["decision_id"].startswith("d-")
    assert d["S7-011"].decision.reason_code == COOLDOWN


def test_a_skipped_change_is_corrected_from_the_reported_levels(events):
    # the recording never applied anything: S7-011 still reports LAL MEDIUM
    state, _ = _feed("BEHAVIOR_ADAPTIVE", events[OBS_01])
    assert state.engine.lal == "MEDIUM" and state.engine.moved == ()


def test_obs02_never_changes(events):
    _, pending = _feed("BEHAVIOR_ADAPTIVE", events[OBS_02])
    assert len(pending) == 20 and all(p.decision.action == NO_CHANGE for p in pending)


def test_rebuild_gives_the_same_state(events):
    evs = events[OBS_01]
    live, pending = _feed("BEHAVIOR_ADAPTIVE", evs)
    cut = next(i for i, e in enumerate(evs) if e["event_type"] == "ANSWER_SELECTED"
               and (e["payload"] or {}).get("trial_id") == "S7-012")
    rebuilt = SessionAdaptationState.rebuild("BEHAVIOR_ADAPTIVE", evs[:cut])
    for e in evs[cut:]:
        rebuilt.feed(e["event_type"], e.get("payload") or {})
    assert rebuilt.engine == live.engine
    assert {k: v.as_dict() for k, v in rebuilt.decisions.items()} == \
           {k: v.as_dict() for k, v in live.decisions.items()}


def test_decision_event_carries_context_and_latency(events):
    _, pending = _feed("BEHAVIOR_ADAPTIVE", events[OBS_01])
    p = next(x for x in pending if x.decision.trial_id == "S7-010").event_payload(12.345)
    for key in ("state", "session_elapsed_ms", "esl", "lal", "trial_id", "trial_sequence"):
        assert key in p
    assert p["source"] == "BACKEND" and p["decision_latency_ms"] == 12.35
    assert p["estimator_version"] == "behavior-v1" and p["rules_version"] == "rules-v1"
    assert "slow_errors" in p["evidence"]
    assert json.loads(json.dumps(p)) == p

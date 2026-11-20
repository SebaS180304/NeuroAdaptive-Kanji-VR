"""
M1a (tasks/plan.md, Thu 19; D-F6-231, D-F6-234, D-F6-247, D-F6-254): the live monitor's read endpoint.
GET /research/sessions/{id}/live gives one snapshot of what the database already holds (V1.13): top bar, sync,
live indices (the word from the last decision's z, the per-epoch trace against the reference), decisions, the event
console and system lines. The per-channel figures (M1b) are null until live.py writes them. GET /research/live/current
gives the newest IN_PROGRESS session. Read-only, as the whole router.
"""

import json
import math

import pytest
import pytest_asyncio

from tests.test_projection_adaptation import S7, _exec, session  # noqa: F401 (the adaptive S7 fixture)

REF = {"source": "S6", "fallback": False, "n_epochs": 18,
       "indices": {"engagement_index": {"mean": 0.0, "sd": 1.0, "n": 18}, "theta_fz": {"mean": -1.0, "sd": 0.5, "n": 18}}}
SYNC = {"spread_ms": 17.8, "taps": [{"phase": "S3", "valid": True}] * 4 + [{"phase": "S3", "valid": False}]}


@pytest_asyncio.fixture
async def live_session(session):  # noqa: F811
    await _exec("UPDATE experiment_sessions SET status = 'IN_PROGRESS', current_state = :st, assigned_kanji_set = 'B', "
                "visit_number = 2 WHERE id = :s", s=session, st=S7)
    await _exec("INSERT INTO eeg_sessions (session_id, xdf_path, sync_offset_ms, sync_detail, alpha_ratio, alpha_passed, "
                "reference, heartbeat_at) VALUES (:s, 'C:/x.xdf', 14.4, CAST(:d AS jsonb), CAST(:a AS jsonb), true, "
                "CAST(:r AS jsonb), now())", s=session, d=json.dumps(SYNC), a=json.dumps({"P3": 4.9}), r=json.dumps(REF))
    for i, (q, ei, th) in enumerate((("GOOD", math.e, math.exp(-0.5)), ("POOR", None, None))):
        await _exec("INSERT INTO eeg_epochs (session_id, epoch_index, lsl_start, start_ms, end_ms, game_state, chunk_clean, "
                    "clean_fraction, quality, engagement_index, theta_fz) VALUES (:s, :i, 0, :st, :en, :g, :c, 1, :q, :ei, :th)",
                    s=session, i=i, st=i * 2500, en=i * 2500 + 5000, g=S7, c=[True] * 9, q=q, ei=ei, th=th)
    return str(session)


@pytest.mark.asyncio
async def test_the_snapshot_has_every_section(client, live_session):
    r = await client.get(f"/research/sessions/{live_session}/live")
    assert r.status_code == 200
    body = r.json()
    top = body["session"]
    assert top["stage"] == S7 and top["external_code"] == "PROJ0003_TEST" and top["set"] == "B" and top["visit"] == 2
    assert 14600 <= top["elapsed_ms"] < 14600 + 5000   # the newest event plus the moments since it arrived
    assert body["sync"] == {"clear_taps": 4, "taps": 5, "offset_ms": 14.4, "robust_spread_ms": 17.8}
    ind = body["indices"]
    assert ind["reference"] == {"source": "S6", "fallback": False, "n_epochs": 18}
    assert ind["last"] == {"trial_id": "S7-002", "counted": True, "ei_z": -0.41, "ei_band": "Normal",
                           "theta_z": 1.23, "theta_band": "High"}
    assert ind["windows"] == {"counted": 1, "with_eeg": 1}
    assert ind["trace"] == [{"start_ms": 0, "ei_z": pytest.approx(1.0), "theta_z": pytest.approx(1.0)}]  # POOR left out
    assert [d["trial_id"] for d in body["decisions"]] == ["S7-002", "S7-001"]                           # newest first
    assert body["decisions"][0]["eeg_effect"] == "CONFIRMED" and body["decisions"][0]["to_level"] == "HIGH"
    ev = body["events"]
    assert ev[0]["event_type"] == "ADAPTATION_SKIPPED" and ev[0]["elapsed_ms"] == 14600 and len(ev) <= 40
    assert all(set(e) == {"elapsed_ms", "event_type", "trial_id", "flag"} for e in ev)
    sysl = body["system"]
    assert sysl["heartbeat_age_s"] is not None and sysl["alpha_passed"] is True and sysl["bad_channel"] is None
    assert body["signal_quality"] is None   # M1b
    assert body["generated_at"]


async def _clock(client, sid: str) -> int:
    return (await client.get(f"/research/sessions/{sid}/live")).json()["session"]["elapsed_ms"]


@pytest.mark.asyncio
async def test_the_clock_keeps_counting_with_no_new_event(client, live_session):   # D-F6-274 (1): T04's S4
    await _exec("UPDATE session_events SET server_received_at = server_received_at - interval '30 seconds' "
                "WHERE session_id = :s", s=live_session)
    assert 14600 + 30_000 <= await _clock(client, live_session) < 14600 + 35_000


@pytest.mark.asyncio
async def test_a_late_event_from_the_queue_does_not_pull_the_clock_back(client, live_session):
    await _exec("INSERT INTO session_events (session_id, event_type, payload) "
                "VALUES (:s, 'VIEW_RECENTERED', '{\"session_elapsed_ms\": 1000}')", s=live_session)
    assert await _clock(client, live_session) >= 14600


@pytest.mark.asyncio
async def test_an_ended_session_shows_its_last_event(client, live_session):
    await _exec("UPDATE experiment_sessions SET status = 'COMPLETED' WHERE id = :s", s=live_session)
    await _exec("UPDATE session_events SET server_received_at = server_received_at - interval '30 seconds' "
                "WHERE session_id = :s", s=live_session)
    assert await _clock(client, live_session) == 14600


@pytest.mark.asyncio
async def test_the_newest_in_progress_session_is_current(client, live_session):
    r = await client.get("/research/live/current")
    assert r.status_code == 200 and r.json() == {"session_id": live_session, "external_code": "PROJ0003_TEST"}


@pytest.mark.asyncio
async def test_with_two_in_progress_the_latest_event_wins(client, live_session):   # D-F6-270 (3)
    other = await _exec("INSERT INTO experiment_sessions (participant_id, condition, status) SELECT participant_id, "
                        "condition, 'IN_PROGRESS' FROM experiment_sessions WHERE id = :s RETURNING id", s=live_session)
    newer = str(other[0][0])   # created after live_session, but with no event: an older hung session wins over it
    assert (await client.get("/research/live/current")).json()["session_id"] == live_session
    await _exec("INSERT INTO session_events (session_id, event_type, payload) VALUES (:s, 'STATE_ENTERED', '{}')", s=newer)
    assert (await client.get("/research/live/current")).json()["session_id"] == newer


@pytest.mark.asyncio
async def test_the_snapshot_says_when_the_session_closed(client, live_session):   # V1.13 sessionEnded (D-F6-270 (4))
    await _exec("UPDATE experiment_sessions SET status = 'COMPLETED', completed_at = now() WHERE id = :s", s=live_session)
    top = (await client.get(f"/research/sessions/{live_session}/live")).json()["session"]
    assert top["status"] == "COMPLETED" and top["completed_at"]


@pytest.mark.asyncio
async def test_an_unknown_session_is_404(client):
    r = await client.get("/research/sessions/00000000-0000-0000-0000-000000000000/live")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_the_per_channel_figures_appear_when_live_py_writes_them(client, live_session):   # M1b
    snap = {"channels": [{"label": "Fp1", "l60_uv": 112.0, "rms_uv": 14.0, "over_pct": 0.8, "status": "OK",
                          "flat": False, "sync_tap": False, "mark_60": False}],
            "session_60_uv": 102.0, "session_60_status": "OK", "window_lsl": [0, 5], "computed_lsl": 7}
    await _exec("UPDATE eeg_sessions SET monitor = CAST(:m AS jsonb), monitor_at = now() WHERE session_id = :s",
                s=live_session, m=json.dumps(snap))
    sq = (await client.get(f"/research/sessions/{live_session}/live")).json()["signal_quality"]
    assert sq["channels"][0]["status"] == "OK" and sq["session_60_uv"] == 102.0 and 0 <= sq["age_s"] < 5

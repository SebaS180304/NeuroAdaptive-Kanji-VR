"""
F4 S3 (tasks/todo.md, M5): app/eeg/reference.py, the person's own reference for the z of each index
(Reevaluacion_EEG_Justificacion.md §4.4.1 step 7 and §5.4; D-F6-73).
"""

import json
import math

import numpy as np
import pytest
from sqlalchemy import text

from app.db.base import AsyncSessionLocal
from app.eeg import epochs, reference

S6 = "S6_GUIDED_PRACTICE_CALIBRATION"
S4 = "S4_EEG_BASELINE"
OPEN_SPAN, CLOSED_SPAN = (200.0, 260.0), (260.0, 305.0)


def _epoch(state: str, value: float, start: float = 0.0, quality: str = "GOOD") -> dict:
    empty = quality == "POOR"
    return {"game_state": state, "quality": quality, "lsl_start": start,
            "engagement_index": None if empty else value, "theta_fz": None if empty else value * 2,
            "alpha_parietal": None if empty else value * 3, "theta_beta": None if empty else value * 4}


def test_the_reference_is_mean_and_sd_of_the_log_over_non_poor_s6_epochs() -> None:
    values = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
    eps = [_epoch(S6, v) for v in values] + [_epoch(S6, 9.9, quality="POOR"), _epoch(S4, 9.9)]
    out = reference.compute(eps, (OPEN_SPAN, CLOSED_SPAN))
    logs = np.log(values)
    assert out["source"] == "S6" and out["n_epochs"] == 6 and out["fallback"] is False
    assert out["indices"]["engagement_index"]["mean"] == pytest.approx(float(logs.mean()))
    assert out["indices"]["engagement_index"]["sd"] == pytest.approx(float(logs.std(ddof=1)))


def test_under_6_s6_epochs_it_falls_back_to_s4_eyes_open_and_says_so() -> None:
    s6 = [_epoch(S6, 0.2 + i / 10) for i in range(5)]
    open_eyes = [_epoch(S4, 0.3 + i / 10, start=205.0 + i * 2.5) for i in range(4)]
    astride = _epoch(S4, 9.9, start=258.0)    # half of it with the eyes closed: not a reference of eyes open
    closed = _epoch(S4, 9.9, start=270.0)
    out = reference.compute(s6 + open_eyes + [astride, closed], (OPEN_SPAN, CLOSED_SPAN))
    assert out["source"] == "S4_EYES_OPEN" and out["fallback"] is True and out["n_epochs"] == 4
    assert out["indices"]["engagement_index"]["mean"] == pytest.approx(float(np.log([0.3, 0.4, 0.5, 0.6]).mean()))


def test_an_index_with_no_spread_does_not_count() -> None:
    out = reference.compute([_epoch(S6, 0.5) for _ in range(6)], (OPEN_SPAN, CLOSED_SPAN))
    assert out["indices"]["engagement_index"]["mean"] == pytest.approx(math.log(0.5))
    assert out["indices"]["engagement_index"]["sd"] is None


def test_without_s6_nor_s4_markers_there_is_no_reference() -> None:
    out = reference.compute([_epoch(S6, 0.3)], None)
    assert out["source"] is None and out["n_epochs"] == 0 and out["indices"] == {}


@pytest.mark.asyncio
async def test_fill_from_xdf_stores_the_reference_of_the_session(client, pretested, monkeypatch) -> None:
    from app.eeg import lsl_reader

    n = 20 * 250
    x, ts = np.random.default_rng(0).normal(0, 5, (n, 8)), 100.0 + np.arange(n) / 250.0
    state = json.dumps({"schema_version": 1, "event": "STATE_ENTERED", "state": S6, "esl": "MEDIUM",
                        "session_elapsed_ms": 1000})
    streams = {"AURA": {"time_series": x, "time_stamps": ts, "info": {"nominal_srate": ["250"]}},
               "UnityMarkers": {"time_series": [[state]], "time_stamps": np.array([100.0])}}
    monkeypatch.setattr(lsl_reader, "load_xdf", lambda _path: streams)
    pid = await pretested("TEST_EEG")
    sid = (await client.post("/sessions", json={"random_seed": "test-seed", "participant_id": pid, "condition": "STATIC"})).json()["id"]
    async with AsyncSessionLocal() as db:
        await db.execute(text("INSERT INTO eeg_sessions (session_id, xdf_path) VALUES (:s, 'x.xdf') "
                              "ON CONFLICT (session_id) DO UPDATE SET xdf_path = 'x.xdf'"), {"s": sid})
        await db.commit()
    await epochs.fill_from_xdf(sid)
    async with AsyncSessionLocal() as db:
        stored = (await db.execute(text("SELECT reference FROM eeg_sessions WHERE session_id = :s"),
                                   {"s": sid})).scalar_one()
    assert stored["source"] == "S6" and stored["indices"]["theta_fz"]["sd"] > 0

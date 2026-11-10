"""
F4 S2 (tasks/plan.md, W4): app/eeg/baseline.py, the S4 eyes-closed test. Alpha with the eyes
closed over alpha with them open in P3, Pz, P4 (Oz if it entered), passes at ≥ 1.2 (D-F6-73, D-F6-75).
"""

import os

import numpy as np
import pytest
from sqlalchemy import text

from app.db.base import AsyncSessionLocal
from app.eeg import baseline, preprocess

SR = 250.0
MONTAGE = {"CH1": "Fp1", "CH2": "F3", "CH3": "Fz", "CH4": "F4", "CH5": "Cz", "CH6": "P3", "CH7": "Pz", "CH8": "P4"}


def _s4(closed_alpha_uv: float, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """20 s eyes open then 20 s eyes closed: noise plus 10 Hz of 2 µV open, `closed_alpha_uv` closed."""
    n = int(40 * SR)
    t = np.arange(n) / SR
    x = np.random.default_rng(seed).normal(0, 3, (n, 8))
    amp = np.where(t < 20, 2.0, closed_alpha_uv)
    x += (amp * np.sin(2 * np.pi * 10 * t))[:, None]
    return x, 1000.0 + t


def test_alpha_goes_up_with_the_eyes_closed_and_passes() -> None:
    x, ts = _s4(8.0)
    r = baseline.alpha_ratio(x, ts, SR, MONTAGE, (1000, 1020), (1020, 1040))
    assert set(r) == {"P3", "Pz", "P4"}
    assert all(v > 4 for v in r.values())
    assert baseline.passed(r)


def test_no_rise_does_not_pass_and_one_channel_is_enough_to_fail() -> None:
    x, ts = _s4(2.0)
    r = baseline.alpha_ratio(x, ts, SR, MONTAGE, (1000, 1020), (1020, 1040))
    assert not baseline.passed(r)
    assert not baseline.passed({"P3": 3.0, "Pz": 1.19, "P4": 3.0})
    assert not baseline.passed({})


def test_oz_enters_when_the_montage_has_it() -> None:
    x, ts = _s4(8.0)
    r = baseline.alpha_ratio(x, ts, SR, {**MONTAGE, "CH1": "Oz"}, (1000, 1020), (1020, 1040))
    assert set(r) == {"Oz", "P3", "Pz", "P4"}


def test_blink_and_amplitude_chunks_are_left_out() -> None:
    x, ts = _s4(8.0)
    x[int(5 * SR):int(6 * SR), 6] += 500  # a 1 s step on Pz with the eyes open: would sink the open alpha
    clean = baseline.alpha_ratio(x, ts, SR, MONTAGE, (1000, 1020), (1020, 1040))
    assert clean["Pz"] > 4


def test_spans_come_from_the_s4_markers() -> None:
    markers = [(10.0, {"event": "EYES_OPEN_START"}), (70.0, {"event": "EYES_OPEN_END"}),
               (70.0, {"event": "EYES_CLOSED_START"}), (115.0, {"event": "EYES_CLOSED_END"})]
    assert baseline.spans(markers) == ((10.0, 70.0), (70.0, 115.0))
    assert baseline.spans(markers[:3]) is None  # S4 not finished


@pytest.mark.asyncio
async def test_save_writes_the_row_and_the_event(client, pretested) -> None:
    pid = await pretested("TEST_EEG")
    sid = (await client.post("/sessions", json={"random_seed": "test-seed", "participant_id": pid, "condition": "STATIC"})).json()["id"]
    async with AsyncSessionLocal() as db:
        await baseline.save(db, sid, {"P3": 4.9, "Pz": 3.6, "P4": 4.0})  # no eeg_sessions row yet
        await db.commit()
        row = (await db.execute(text("SELECT alpha_ratio, alpha_passed FROM eeg_sessions WHERE session_id = :s"),
                                {"s": sid})).one()
        ev = (await db.execute(text("SELECT payload FROM session_events WHERE session_id = :s "
                                    "AND event_type = 'EEG_BASELINE_RESULT'"), {"s": sid})).scalar_one()
    assert row.alpha_ratio == {"P3": 4.9, "Pz": 3.6, "P4": 4.0} and row.alpha_passed is True
    assert ev["passed"] is True and ev["threshold"] == 1.2 and ev["alpha_ratio"]["Pz"] == 3.6


# The 29 Oct recordings live on Sebas's PC only.
_XDF_1 = os.environ.get("EEG_XDF_29OCT_1")


@pytest.mark.skipif(not _XDF_1, reason="set EEG_XDF_29OCT_1 to the 29 Oct XDF 1 (15:27)")
def test_the_29_oct_alpha_block_passes_like_the_summary() -> None:
    from app.eeg import lsl_reader

    aura = lsl_reader.load_xdf(_XDF_1)["AURA"]
    ts = aura["time_stamps"]
    x = preprocess.filter_eeg(aura["time_series"], SR)
    t0 = ts[0]
    # F4 S1 summary: eyes closed ≈ 231–275 s; the 44 s before it as eyes open. Summary: P3 4.9 · Pz 3.6 · P4 4.0.
    r = baseline.alpha_ratio(x, ts, SR, MONTAGE, (t0 + 187, t0 + 231), (t0 + 231, t0 + 275))
    assert baseline.passed(r) and all(v > 2 for v in r.values()), r

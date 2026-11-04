"""
F4 S2 (tasks/plan.md, T1): app/eeg/preprocess.py and app/eeg/epochs.py, table eeg_epochs (0011).
Rules: Reevaluacion_EEG_Justificacion.md §4.4.1 and §5.3 (D-F6-73), FRAME_HITCH and P16 (D-F6-129).
"""

import json
import os

import numpy as np
import pytest
from sqlalchemy import text

from app.db.base import AsyncSessionLocal
from app.eeg import epochs, preprocess

SR = 250.0
MONTAGE = {"CH1": "Fp1", "CH2": "F3", "CH3": "Fz", "CH4": "F4", "CH5": "Cz", "CH6": "P3", "CH7": "Pz", "CH8": "P4"}


def _eeg(seconds: float = 30.0, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Clean filtered-looking EEG: 8 channels of ~5 µV noise, stamps from 100 s on."""
    n = int(seconds * SR)
    return np.random.default_rng(seed).normal(0, 5, (n, 8)), 100.0 + np.arange(n) / SR


def _chunks(eps: list[dict]) -> dict[float, bool]:
    """Every chunk by its start time (rounded), clean or not."""
    return {round(e["lsl_start"] + k, 2): c for e in eps for k, c in enumerate(e["chunk_clean"])}


# ---------- preprocess ----------

def test_the_filter_keeps_alpha_and_removes_dc_and_mains() -> None:
    t = np.arange(int(20 * SR)) / SR
    x = (50000 + 10 * np.sin(2 * np.pi * 10 * t) + 30 * np.sin(2 * np.pi * 60 * t))[:, None] * np.ones((1, 8))
    y = preprocess.filter_eeg(x, SR)[int(2 * SR):-int(2 * SR)]  # away from the edges
    assert abs(y.mean()) < 0.5
    assert 9 < np.sqrt(2) * y[:, 0].std() < 11  # 10 µV of alpha survive; 60 Hz and the offset do not


def test_the_filter_parameters_are_stored_per_session() -> None:
    p = preprocess.filter_params(SR)
    assert p["bandpass_hz"] == [1.0, 40.0] and p["notch_hz"] == 60.0 and p["srate"] == 250.0


def test_relative_power_divides_by_1_to_40_hz_p16() -> None:
    t = np.arange(int(4 * SR)) / SR
    alpha = np.sin(2 * np.pi * 10 * t)
    assert preprocess.relative_power(alpha, SR, preprocess.BANDS["alpha"]) == pytest.approx(1, abs=0.01)
    assert preprocess.relative_power(alpha, SR, preprocess.BANDS["theta"]) < 0.01
    # 45 Hz is outside the denominator: adding it changes nothing.
    with_45 = alpha + np.sin(2 * np.pi * 45 * t)
    assert preprocess.relative_power(with_45, SR, preprocess.BANDS["alpha"]) == pytest.approx(1, abs=0.01)


# ---------- epochs ----------

def test_quality_follows_d_f6_73() -> None:
    assert [epochs.quality(n) for n in (5, 4, 3, 2, 0)] == ["GOOD", "GOOD", "ACCEPTABLE", "POOR", "POOR"]


def test_clean_signal_gives_5_s_epochs_every_2_5_s_all_good() -> None:
    x, ts = _eeg(30)
    eps = epochs.make_epochs(x, ts, SR, MONTAGE, [])
    assert len(eps) == 11
    assert [e["lsl_start"] for e in eps[:3]] == [100.0, 102.5, 105.0]
    assert all(e["quality"] == "GOOD" and e["clean_fraction"] == 1.0 for e in eps)


def test_a_blink_on_fp1_drops_its_chunk_with_200_ms_around() -> None:
    x, ts = _eeg()
    x[int(11.1 * SR), 0] = 150  # Fp1, 0.1 s into the chunk 111–112: the 200 ms pad reaches 110–111
    chunks = _chunks(epochs.make_epochs(x, ts, SR, MONTAGE, []))
    assert chunks[110.0] is False and chunks[111.0] is False and chunks[112.0] is True


def test_fp1_is_not_held_to_the_100_uv_rule_but_index_channels_are() -> None:
    x, ts = _eeg()
    x[int(15.5 * SR), 4] = 120  # Cz
    chunks = _chunks(epochs.make_epochs(x, ts, SR, MONTAGE, []))
    assert chunks[115.0] is False and chunks[116.0] is True


def test_without_fp1_blinks_are_looked_for_in_f3_fz_f4() -> None:
    x, ts = _eeg()
    x[int(20.5 * SR), 2] = 80  # F3, over the blink limit but under the amplitude limit
    oz = {**MONTAGE, "CH1": "Oz"}
    assert _chunks(epochs.make_epochs(x, ts, SR, oz, []))[120.0] is False
    assert _chunks(epochs.make_epochs(x, ts, SR, MONTAGE, []))[120.0] is True


def test_a_flat_channel_drops_the_chunk() -> None:
    x, ts = _eeg()
    x[int(5 * SR):int(6 * SR), 6] = 0.0  # Pz
    assert _chunks(epochs.make_epochs(x, ts, SR, MONTAGE, []))[105.0] is False


def test_a_frame_hitch_over_100_ms_drops_its_chunk_and_one_under_does_not() -> None:
    x, ts = _eeg()
    markers = [(107.5, {"event": "FRAME_HITCH", "duration_ms": 120.0}),
               (112.5, {"event": "FRAME_HITCH", "duration_ms": 80.0})]
    chunks = _chunks(epochs.make_epochs(x, ts, SR, MONTAGE, markers))
    assert chunks[107.0] is False and chunks[112.0] is True


def test_the_second_after_each_sound_onset_is_dropped() -> None:
    x, ts = _eeg(40)
    markers = [
        (110.5, {"schema_version": 1, "event": "STATE_ENTERED", "transition_sound_lead_ms": 3500}),  # stage at 107.0
        (115.0, {"schema_version": 1, "event": "ANSWER_SELECTED", "trial_id": "S6-001"}),           # select at 115.0
        (117.0, {"schema_version": 1, "event": "TRIAL_COMPLETED", "trial_id": "S6-001",
                 "result_sound_offset_ms": 6000}),                                                 # result at 121.0
    ]
    chunks = _chunks(epochs.make_epochs(x, ts, SR, MONTAGE, markers))
    assert chunks[107.0] is False and chunks[108.0] is True
    assert chunks[115.0] is False and chunks[116.0] is True
    assert chunks[121.0] is False and chunks[122.0] is True


def test_an_open_head_away_drops_its_chunks() -> None:
    x, ts = _eeg()
    markers = [(111.0, {"schema_version": 1, "event": "HEAD_AWAY", "episode": 1, "onset_offset_ms": -500}),
               (114.0, {"schema_version": 1, "event": "HEAD_RETURNED", "episode": 1, "duration_ms": 2000}),
               (124.0, {"schema_version": 1, "event": "HEAD_AWAY", "episode": 2, "onset_offset_ms": -500})]
    chunks = _chunks(epochs.make_epochs(x, ts, SR, MONTAGE, markers))
    assert chunks[110.0] is False and chunks[112.0] is False and chunks[113.0] is True  # 110.5–112.5
    assert chunks[125.0] is False  # never returned: open until the end


def test_each_epoch_knows_its_state_trial_esl_and_session_clock() -> None:
    x, ts = _eeg()
    ev = lambda e, t_ms, **kw: {"schema_version": 1, "event": e, "session_elapsed_ms": t_ms, **kw}
    markers = [(101.0, ev("STATE_ENTERED", 61000, state="S6_PRE_ASSESSMENT", esl="MEDIUM")),
               (108.0, ev("TRIAL_STARTED", 68000, state="S6_PRE_ASSESSMENT", esl="MEDIUM", trial_id="S6-001")),
               (113.0, ev("TRIAL_COMPLETED", 73000, state="S6_PRE_ASSESSMENT", esl="MEDIUM", trial_id="S6-001"))]
    eps = epochs.make_epochs(x, ts, SR, MONTAGE, markers)
    first, in_trial, after = eps[0], eps[3], eps[5]  # midpoints 102.5, 110, 115
    assert (first["game_state"], first["esl_level"], first["trial_id"]) == ("S6_PRE_ASSESSMENT", "MEDIUM", None)
    assert in_trial["trial_id"] == "S6-001" and after["trial_id"] is None
    assert (first["start_ms"], first["end_ms"]) == (60000, 65000)


def test_without_markers_there_is_no_session_clock_nor_context() -> None:
    x, ts = _eeg()
    e = epochs.make_epochs(x, ts, SR, MONTAGE, [])[0]
    assert e["start_ms"] is None and e["game_state"] is None


def test_markers_are_read_from_the_xdf_stream() -> None:
    stream = {"time_stamps": np.array([1.0, 2.0]),
              "time_series": [[json.dumps({"event": "FRAME_HITCH", "duration_ms": 60})], ['{"event": "X"}']]}
    assert epochs.markers_of(stream) == [(1.0, {"event": "FRAME_HITCH", "duration_ms": 60}), (2.0, {"event": "X"})]
    assert epochs.markers_of(None) == []


@pytest.mark.asyncio
async def test_save_rewrites_the_epochs_and_the_filter_of_the_session(client, pretested) -> None:
    pid = await pretested("TEST_EEG")
    sid = (await client.post("/sessions", json={"participant_id": pid, "condition": "STATIC"})).json()["id"]
    x, ts = _eeg(20)
    eps = epochs.make_epochs(x, ts, SR, MONTAGE, [])
    async with AsyncSessionLocal() as db:
        await db.execute(text("INSERT INTO eeg_sessions (session_id, xdf_path) VALUES (:s, 'x.xdf')"), {"s": sid})
        await epochs.save(db, sid, eps, preprocess.filter_params(SR))
        await epochs.save(db, sid, eps[:2], preprocess.filter_params(SR))  # a second run replaces the first
        await db.commit()
        rows = (await db.execute(text("SELECT epoch_index, chunk_clean, quality, engagement_index FROM eeg_epochs "
                                      "WHERE session_id = :s ORDER BY epoch_index"), {"s": sid})).all()
        fp = (await db.execute(text("SELECT filter_params FROM eeg_sessions WHERE session_id = :s"),
                               {"s": sid})).scalar_one()
    assert [r.epoch_index for r in rows] == [0, 1]
    assert rows[0].chunk_clean == [True] * 5 and rows[0].quality == "GOOD" and rows[0].engagement_index is None
    assert fp["notch_hz"] == 60.0


# ---------- the 29 Oct recordings (on Sebas's PC only) ----------

_XDF_2 = os.environ.get("EEG_XDF_29OCT_2")
_XDF_3 = os.environ.get("EEG_XDF_29OCT_3")


def _from_xdf(path: str) -> tuple[list[dict], float]:
    from app.eeg import lsl_reader

    aura = lsl_reader.load_xdf(path)["AURA"]
    sr = float(aura["info"]["nominal_srate"][0])
    x = preprocess.filter_eeg(aura["time_series"], sr)
    return epochs.make_epochs(x, aura["time_stamps"], sr, MONTAGE, []), float(aura["time_stamps"][0])


@pytest.mark.skipif(not _XDF_2, reason="set EEG_XDF_29OCT_2 to the 29 Oct XDF 2 (15:41, artifacts)")
def test_the_29_oct_artifact_blocks_are_poor() -> None:
    eps, t0 = _from_xdf(_XDF_2)
    # Hoja_Primera_Colocacion_AURA_27oct.md, recording 2: blinks s 59–62, jaw 80–83, head turns 100–105.
    for name, (a, b) in {"blinks": (59, 62), "jaw": (80, 83), "turns": (100, 105)}.items():
        inside = [e for e in eps if a <= e["lsl_start"] - t0 + 2.5 <= b]
        assert inside and all(e["quality"] == "POOR" for e in inside), name


@pytest.mark.skipif(not _XDF_3, reason="set EEG_XDF_29OCT_3 to the 29 Oct XDF 3 (16:21, S1-S7)")
def test_the_29_oct_session_keeps_most_chunks_clean() -> None:
    eps, _ = _from_xdf(_XDF_3)
    clean = np.mean([c for e in eps for c in e["chunk_clean"]])
    # F4 S1 summary: 81 %. With the 200 ms blink pad of F4 §6 this gives 70 % (75 % without it):
    # finding of 4 Nov, Borrador_Plan_Fase6_9_4nov.md.
    assert 0.65 <= clean <= 0.90

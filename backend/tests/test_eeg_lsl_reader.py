"""
F4 S2 (tasks/plan.md, L3): app/eeg/lsl_reader.py. The XDF and live paths keep LSL's
corrected clock and take only this PC's streams (P9 of D-F6-127).
"""

import os
import types

import pytest
from sqlalchemy import text

from app.db.base import AsyncSessionLocal
from app.eeg import lsl_reader


def _stream(name: str, n: int, host: str = "LaptopSebas1803") -> dict:
    info = {"name": [name], "type": ["EEG"], "hostname": [host], "source_id": [name + "-1"],
            "channel_count": ["8"], "nominal_srate": ["250.0"], "effective_srate": 250.0}
    return {"info": info, "time_stamps": [10.0 + i / 250 for i in range(n)]}


def test_stream_info_keeps_what_eeg_sessions_needs() -> None:
    info = lsl_reader.stream_info(_stream("AURA", 500))
    assert info["channel_count"] == 8 and info["nominal_srate"] == 250.0
    assert info["samples"] == 500 and info["first_ts"] == 10.0 and info["hostname"] == "LaptopSebas1803"


def test_a_session_without_the_marker_stream_is_not_multimodal() -> None:
    assert lsl_reader.missing_streams({"AURA": _stream("AURA", 1)}) == ["UnityMarkers"]
    assert lsl_reader.missing_streams({"AURA": _stream("AURA", 1), "UnityMarkers": _stream("UnityMarkers", 1)}) == []


def test_two_streams_with_one_name_are_refused(monkeypatch) -> None:
    monkeypatch.setattr(lsl_reader.pyxdf, "load_xdf",
                        lambda *a, **k: ([_stream("AURA", 1), _stream("AURA", 1, "OtherPC")], {}))
    with pytest.raises(ValueError):
        lsl_reader.load_xdf("x.xdf")


def test_the_xdf_is_read_on_the_corrected_clock(monkeypatch) -> None:
    seen = {}
    monkeypatch.setattr(lsl_reader.pyxdf, "load_xdf", lambda p, **k: (seen.update(k), ([_stream("AURA", 1)], {}))[1])
    lsl_reader.load_xdf("x.xdf")
    assert seen == {"synchronize_clocks": True, "dejitter_timestamps": True}


def test_the_live_inlet_takes_only_this_pcs_stream(monkeypatch) -> None:
    pylsl = pytest.importorskip("pylsl")
    mine, other = (types.SimpleNamespace(hostname=lambda h=h: h) for h in ("ThisPC", "OtherPC"))
    monkeypatch.setattr(pylsl, "resolve_byprop", lambda *a, **k: [other, mine])
    opened = {}
    monkeypatch.setattr(pylsl, "StreamInlet", lambda s, processing_flags: opened.update(s=s, f=processing_flags))
    lsl_reader.open_local_inlet("AURA", host="ThisPC")
    assert opened["s"] is mine and opened["f"] == pylsl.proc_clocksync | pylsl.proc_dejitter

    monkeypatch.setattr(pylsl, "resolve_byprop", lambda *a, **k: [other])
    with pytest.raises(LookupError):
        lsl_reader.open_local_inlet("AURA", host="ThisPC")


@pytest.mark.asyncio
async def test_save_writes_and_rewrites_the_row(client, pretested) -> None:
    pid = await pretested("TEST_EEG")
    sid = (await client.post("/sessions", json={"random_seed": "test-seed", "participant_id": pid, "condition": "STATIC"})).json()["id"]
    async with AsyncSessionLocal() as db:
        await lsl_reader.save(db, sid, "a.xdf", {"AURA": _stream("AURA", 3)})
        await lsl_reader.save(db, sid, "b.xdf", {"AURA": _stream("AURA", 3), "UnityMarkers": _stream("UnityMarkers", 2)})
        await db.commit()
        row = (await db.execute(text("SELECT xdf_path, stream_info, not_counted_reason FROM eeg_sessions "
                                     "WHERE session_id = :s"), {"s": sid})).one()
    assert row.xdf_path == "b.xdf" and row.not_counted_reason is None
    assert row.stream_info["UnityMarkers"]["samples"] == 2


# The 29 Oct recordings live on Sebas's PC, not in the repo: this one runs only there.
_XDF_1 = os.environ.get("EEG_XDF_29OCT_1")


@pytest.mark.skipif(not _XDF_1, reason="set EEG_XDF_29OCT_1 to the 29 Oct XDF 1 (15:27)")
def test_the_29_oct_recording_1_has_every_sample() -> None:
    aura = lsl_reader.stream_info(lsl_reader.load_xdf(_XDF_1)["AURA"])
    assert (aura["channel_count"], aura["nominal_srate"], aura["samples"]) == (8, 250.0, 70254)


@pytest.mark.asyncio
async def test_fill_from_xdf_reads_the_path_of_the_row(client, pretested, monkeypatch) -> None:
    pid = await pretested("TEST_EEG")
    sid = (await client.post("/sessions", json={"random_seed": "test-seed", "participant_id": pid, "condition": "STATIC"})).json()["id"]
    async with AsyncSessionLocal() as db:
        await db.execute(text("INSERT INTO eeg_sessions (session_id, xdf_path) VALUES (:s, 'C:/EEG/a.xdf')"), {"s": sid})
        await db.commit()
    read = []
    monkeypatch.setattr(lsl_reader, "load_xdf", lambda p: read.append(p) or {"AURA": _stream("AURA", 4)})

    assert await lsl_reader.fill_from_xdf(sid) == ["UnityMarkers"]
    assert read == ["C:/EEG/a.xdf"]
    async with AsyncSessionLocal() as db:
        reason = (await db.execute(text("SELECT not_counted_reason FROM eeg_sessions WHERE session_id = :s"), {"s": sid})).scalar_one()
    assert reason == "missing stream: UnityMarkers"

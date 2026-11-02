"""
F4 S2 (tasks/plan.md, L5): LabRecorder by its remote control socket gives every
session one XDF with a unique name (P9 of D-F6-127). A fake LabRecorder listens here.
"""

import socket
import threading

import pytest
from sqlalchemy import text

from app.config import get_settings
from app.db.base import AsyncSessionLocal
from app.eeg import labrecorder


def test_the_name_is_bids_and_unique_per_session() -> None:
    path = labrecorder.xdf_relpath("TEST_P01", "8efe29d2-0000-4000-8000-000000000000", "BEHAVIOR_ADAPTIVE")
    assert path == ("sub-TESTP01/ses-8efe29d2/eeg/"
                    "sub-TESTP01_ses-8efe29d2_task-BEHAVIORADAPTIVE_run-1_eeg.xdf")


def test_the_backend_only_names_the_file_never_starts() -> None:
    # A remote `start` makes LabRecorder tick every stream on the network (other projects' too).
    cmds = labrecorder.filename_commands("C:/EEG", "a.xdf")
    assert cmds == ["filename {root:C:/EEG} {template:a.xdf}"]


def test_a_missing_labrecorder_is_only_logged() -> None:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]  # nothing listens once closed
    assert labrecorder.send("127.0.0.1", port, ["start"], timeout=0.5) is False


@pytest.fixture
def fake_labrecorder(monkeypatch):
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen()
    received: list[str] = []

    def serve() -> None:
        while True:
            try:
                conn, _ = server.accept()
            except OSError:
                return
            with conn:
                data = b""
                while chunk := conn.recv(4096):
                    data += chunk
                received.extend(data.decode().splitlines())

    threading.Thread(target=serve, daemon=True).start()
    settings = get_settings()
    monkeypatch.setattr(settings, "labrecorder_host", "127.0.0.1")
    monkeypatch.setattr(settings, "labrecorder_port", server.getsockname()[1])
    monkeypatch.setattr(settings, "labrecorder_root", "C:/EEG")
    yield received
    server.close()


@pytest.mark.asyncio
async def test_a_session_names_its_recording_and_stops_it(client, pretested, fake_labrecorder) -> None:
    import asyncio

    pid = await pretested("TEST_EEG")
    sid = (await client.post("/sessions", json={"participant_id": pid, "condition": "STATIC"})).json()["id"]
    for state in ("S9_SESSION_SUMMARY", "S10_HCI_SELF_REPORT", "S10_HCI_SELF_REPORT"):
        await client.patch(f"/sessions/{sid}/state", json={"new_state": state})
    for _ in range(50):  # the fake server reads on its own thread
        if fake_labrecorder.count("stop"):
            break
        await asyncio.sleep(0.02)

    rel = f"sub-TESTEEG/ses-{sid[:8]}/eeg/sub-TESTEEG_ses-{sid[:8]}_task-STATIC_run-1_eeg.xdf"
    assert fake_labrecorder == [f"filename {{root:C:/EEG}} {{template:{rel}}}", "stop"]
    async with AsyncSessionLocal() as db:
        path = (await db.execute(text("SELECT xdf_path FROM eeg_sessions WHERE session_id = :s"), {"s": sid})).scalar_one()
    assert path == f"C:/EEG/{rel}"


@pytest.mark.asyncio
async def test_without_labrecorder_configured_nothing_is_recorded(client, pretested) -> None:
    pid = await pretested("TEST_EEG")
    sid = (await client.post("/sessions", json={"participant_id": pid, "condition": "STATIC"})).json()["id"]
    async with AsyncSessionLocal() as db:
        n = (await db.execute(text("SELECT count(*) FROM eeg_sessions WHERE session_id = :s"), {"s": sid})).scalar_one()
    assert n == 0

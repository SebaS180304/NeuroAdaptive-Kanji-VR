import sys
from pathlib import Path

from app.eeg import recorder

HOST = "LaptopSebas1803"
AURA = {"name": "AURA", "hostname": HOST, "source_id": "aura-1"}
UNITY = {"name": "UnityMarkers", "hostname": HOST, "source_id": "neuroadaptive-unity"}


def test_the_command_records_only_this_pc_and_the_session_path() -> None:
    cmd = recorder.command(r"C:\x\sub-t02_ses-1234abcd.xdf", HOST, cli=Path("cli.exe"))
    assert cmd == ["cli.exe", r"C:\x\sub-t02_ses-1234abcd.xdf",
                   "name='AURA' and hostname='LaptopSebas1803'",
                   "name='UnityMarkers' and hostname='LaptopSebas1803'"]


def test_automatic_only_with_exactly_one_aura_and_one_unity_of_this_pc() -> None:
    other_pc = {"name": "AURA", "hostname": "DESKTOP-T128OTA", "source_id": "AURA_COM5"}
    aura_markers = {"name": "AURA_Markers", "hostname": HOST, "source_id": "m"}
    assert recorder.decide([AURA, UNITY, other_pc, aura_markers], HOST) == (None, [])
    assert "0 AURA" in recorder.decide([UNITY, other_pc], HOST)[0]
    assert "2 AURA" in recorder.decide([AURA, AURA, UNITY], HOST)[0]          # D-F6-197
    assert "reopen Unity" in recorder.decide([AURA, UNITY, UNITY], HOST)[0]   # an earlier Play's outlet
    assert "0 UnityMarkers" in recorder.decide([AURA], HOST)[0]


def test_the_synthetic_aura_records_but_says_so() -> None:
    reason, warns = recorder.decide([dict(AURA, source_id="synthetic-aura"), UNITY], HOST)
    assert reason is None and "synthetic" in warns[0]


def _fake_cli(tmp_path, body: str) -> Path:
    script = tmp_path / "fake_cli.py"
    script.write_text(body, encoding="utf-8")
    return script


def test_stop_sends_enter_and_waits_and_is_safe_twice(tmp_path, monkeypatch) -> None:
    # stands for LabRecorderCLI: writes the file when Enter arrives, like its footers
    script = _fake_cli(tmp_path, "import sys\ninput()\nopen(sys.argv[1], 'w').write('closed')\n")
    monkeypatch.setattr(recorder, "command", lambda path, host: [sys.executable, str(script), path])
    out = tmp_path / "sub" / "x.xdf"
    rec = recorder.Recorder(str(out), HOST, tmp_path / "cli.txt")
    rec.start()
    assert rec.alive()
    assert rec.stop(timeout=20) == 0
    assert out.read_text() == "closed" and not rec.alive()
    assert rec.stop() == 0


def test_no_cli_means_manual(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(recorder, "LABRECORDER_CLI", tmp_path / "missing.exe")
    rec, line = recorder.start_for("1234abcd-0000", str(tmp_path / "x.xdf"), tmp_path, HOST)
    assert rec is None and line.startswith("MANUAL") and "ses-1234abcd" in line


def test_two_aura_at_play_means_manual_and_nothing_starts(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(recorder, "LABRECORDER_CLI", Path(sys.executable))
    monkeypatch.setattr(recorder, "resolve_until_ready", lambda host: [AURA, AURA, UNITY])
    monkeypatch.setattr(recorder.Recorder, "start", lambda self: (_ for _ in ()).throw(AssertionError("started")))
    rec, line = recorder.start_for("1234abcd-0000", str(tmp_path / "x.xdf"), tmp_path, HOST)
    assert rec is None and "2 AURA" in line

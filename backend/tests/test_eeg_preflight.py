from datetime import datetime

from app.eeg import preflight
from app.eeg.preflight import FAIL, OK, WARN

NOW = datetime(2026, 11, 18, 14, 30)
HOST = "LaptopSebas1803"


def _p(name, start="2026-11-18T14:10:00", cmd=""):
    return {"Name": name, "Start": start, "CommandLine": cmd}


READY = [_p("Unity.exe", cmd='Unity.exe -projectpath "C:\\x"'),
         _p("Unity.exe", cmd="Unity.exe -batchMode -name AssetImportWorker0"),
         _p("Aura.exe"), _p("msedge.exe"), _p("LabRecorder.exe")]


def _levels(results):
    return [level for level, _ in results]


def test_a_ready_pc_is_all_ok_and_import_workers_are_not_a_second_editor() -> None:
    assert set(_levels(preflight.check_processes(READY, NOW))) == {OK}


def test_blender_open_fails_and_names_it() -> None:
    out = preflight.check_processes(READY + [_p("blender.exe")], NOW)
    assert (FAIL, "Blender open: close it (D-F6-153)") in out
    assert not any("closed" in text for _, text in out)


def test_unity_missing_twice_open_or_stale() -> None:
    no_unity = [p for p in READY if p["Name"] != "Unity.exe"]
    assert FAIL in _levels(preflight.check_processes(no_unity, NOW))
    assert FAIL in _levels(preflight.check_processes(READY + [READY[0]], NOW))
    stale = [_p("Unity.exe", start="2026-11-18T11:36:00")] + READY[2:]
    assert _levels(preflight.check_processes(stale, NOW))[0] == WARN


def test_missing_aura_software_or_labrecorder_fails() -> None:
    out = preflight.check_processes([p for p in READY if p["Name"] != "Aura.exe"], NOW)
    assert (FAIL, "AURA software not running") in out


def test_the_aura_lsl_connector_counts_as_the_aura_software() -> None:   # Sebas, 26 Nov: AURA_LSL_CONNECTOR.exe
    connector = [p for p in READY if p["Name"] != "Aura.exe"] + [_p("AURA_LSL_CONNECTOR.exe")]
    assert (OK, "AURA software running") in preflight.check_processes(connector, NOW)


def test_lsl_exactly_one_real_local_aura() -> None:
    real = {"name": "AURA", "hostname": HOST, "source_id": "aura-123"}
    other_pc = {"name": "AURA", "hostname": "MSI", "source_id": "x"}
    assert _levels(preflight.check_lsl([real], HOST)) == [OK]
    assert _levels(preflight.check_lsl([], HOST)) == [WARN]
    assert _levels(preflight.check_lsl([real, real], HOST)) == [FAIL]
    synthetic = dict(real, source_id="synthetic-aura")
    assert _levels(preflight.check_lsl([synthetic], HOST)) == [FAIL]
    # another PC's AURA does not count as ours, but says the network is on
    assert _levels(preflight.check_lsl([real, other_pc], HOST)) == [OK, WARN]


def test_network_and_disk() -> None:
    assert preflight.check_network([])[0] == OK
    assert preflight.check_network(["Wi-Fi"])[0] == WARN
    assert preflight.check_disk(50 * 10**9)[0] == OK
    assert preflight.check_disk(10**8)[0] == FAIL


def test_unity_markers_before_play_is_an_earlier_plays_outlet() -> None:
    real = {"name": "AURA", "hostname": HOST, "source_id": "aura-123"}
    stale = {"name": "UnityMarkers", "hostname": HOST, "source_id": "neuroadaptive-unity"}
    assert _levels(preflight.check_lsl([real, stale], HOST)) == [OK, FAIL]

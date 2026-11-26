"""
Pre-session check of this PC (AU1, D-F6-219, D-F6-221): the R3 list of the operator kit as one command.
It only looks, never changes anything (it does not close apps nor turn the network off).

    cd backend
    .venv\\Scripts\\python -m app.eeg.preflight

One line per check, OK / WARN / FAIL; exit 0 only with no FAIL. Manual recording path: LabRecorder's
GUI open is expected (OK); LabRecorderCLI is only looked for, it records from AU2 on.
"""

import csv
import io
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path

OK, WARN, FAIL = "OK", "WARN", "FAIL"
REPO = Path(__file__).resolve().parents[3]
BACKEND = "http://127.0.0.1:8000"
PORTAL = "http://127.0.0.1:5300/pretest"
XDF_ROOT = Path(os.environ.get("LABRECORDER_ROOT", r"C:\Users\drdom\Documents\Pruebas_EEG"))
LABRECORDER_CLI = Path(os.environ.get(
    "LABRECORDER_CLI",
    r"C:\Users\drdom\Downloads\LabRecorder-1.18.0-Win_amd64\LabRecorder-1.18.0-Win_amd64\LabRecorderCLI.exe"))
# each label passes with any of its executables: the AURA software is Aura.exe or, since 26 Nov, AURA_LSL_CONNECTOR.exe
MUST_RUN = {("Aura.exe", "AURA_LSL_CONNECTOR.exe"): "AURA software", ("msedge.exe",): "Edge (portal)",
            ("LabRecorder.exe",): "LabRecorder"}
MUST_BE_CLOSED = {"blender.exe": "Blender", "firefox.exe": "Firefox", "Code.exe": "VS Code",
                  "ChatGPT.exe": "ChatGPT", "codex.exe": "Codex"}  # D-F6-153
UNITY_STALE_MIN = 60  # kit: Unity freshly opened before each session (16 Nov: open 6 h → reopened)
MIN_FREE_GB = 1.0  # one XDF is ≈ 10 MB


def check_processes(procs: list[dict], now: datetime) -> list[tuple[str, str]]:
    """procs: rows with Name, Start (ISO local time) and CommandLine."""
    names = {p["Name"].lower() for p in procs}
    # Unity's asset import workers are Unity.exe too, started with -batchMode
    editors = [p for p in procs if p["Name"].lower() == "unity.exe"
               and "-batchmode" not in (p.get("CommandLine") or "").lower()]
    out = []
    if len(editors) != 1:
        out.append((FAIL, f"Unity Editor: {len(editors)} open, expected exactly 1"))
    else:
        start = datetime.fromisoformat(editors[0]["Start"])
        age = int((now - start).total_seconds() // 60)
        level = WARN if age > UNITY_STALE_MIN else OK
        out.append((level, f"Unity Editor open since {start:%H:%M} ({age} min)"
                    + (": close and reopen it before the session" if level == WARN else "")))
    for exes, label in MUST_RUN.items():
        running = any(exe.lower() in names for exe in exes)
        out.append((OK, f"{label} running") if running else (FAIL, f"{label} not running"))
    for exe, label in MUST_BE_CLOSED.items():
        if exe.lower() in names:
            out.append((FAIL, f"{label} open: close it (D-F6-153)"))
    if not any(exe.lower() in names for exe in MUST_BE_CLOSED):
        out.append((OK, "Blender, Firefox, VS Code, ChatGPT and Codex closed"))
    return out  # the Unity Profiler is a window inside the Editor: it stays a manual kit line


def check_lsl(streams: list[dict], host: str) -> list[tuple[str, str]]:
    """streams: name, hostname and source_id of every LSL stream seen."""
    local_aura = [s for s in streams if s["hostname"] == host and s["name"] == "AURA"]
    others = sorted({s["hostname"] for s in streams if s["hostname"] != host})
    out = []
    if any(s["source_id"] == "synthetic-aura" for s in local_aura):
        out.append((FAIL, "synthetic AURA running on this PC: stop scripts/synthetic_aura.py"))
    elif len(local_aura) > 1:
        out.append((FAIL, f"{len(local_aura)} AURA on this PC: restart the AURA software (D-F6-197)"))
    elif local_aura:
        out.append((OK, "one AURA on this PC"))
    else:
        out.append((WARN, "no AURA on this PC yet: LSL Stream Out on before Play"))
    if any(s["hostname"] == host and s["name"] == "UnityMarkers" for s in streams):
        # Unity keeps its outlet after leaving Play (AU0, 18 Nov): the next Play would show two
        out.append((FAIL, "UnityMarkers already on before Play: an earlier Play's outlet, reopen Unity"))
    if others:
        out.append((WARN, f"LSL streams of other PCs ({', '.join(others)}): network is on"))
    return out


def check_network(adapters_up: list[str]) -> tuple[str, str]:
    if adapters_up:
        return WARN, f"network up ({', '.join(adapters_up)}): turn it off before the cap (D-F6-193)"
    return OK, "network off"


def check_disk(free_bytes: int) -> tuple[str, str]:
    gb = free_bytes / 1e9
    return (OK if gb >= MIN_FREE_GB else FAIL), f"{gb:.0f} GB free for the XDF"


# ---- gathering (the side that touches the PC) ------------------------------------------------

def _ps(command: str) -> str:
    return subprocess.run(["powershell", "-NoProfile", "-Command", command],
                          capture_output=True, text=True, timeout=60).stdout


def _http(url: str) -> tuple[str, str]:
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            return (OK, f"{url} {r.status}") if r.status == 200 else (FAIL, f"{url} {r.status}")
    except OSError as e:
        return FAIL, f"{url} not reached ({e})"


def adapters_up() -> list[str]:
    return _ps("Get-NetAdapter -Physical | Where-Object Status -eq Up | ForEach-Object Name").split()


def gather() -> list[tuple[str, str]]:
    out = [_http(f"{BACKEND}/health"), _http(f"{BACKEND}/health/db"), _http(PORTAL)]

    port = subprocess.run(["docker", "compose", "port", "db", "5432"], cwd=REPO,
                          capture_output=True, text=True, timeout=30).stdout.strip()
    out.append((OK, f"db port {port}") if port == "127.0.0.1:5432"
               else (FAIL, f"db port '{port}', expected 127.0.0.1:5432"))

    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                           capture_output=True, text=True, timeout=30).stdout.strip()
    out.append((OK, "git status clean") if not dirty
               else (FAIL, f"git status: {len(dirty.splitlines())} changed files"))

    rows = _ps("Get-CimInstance Win32_Process | Select-Object Name,"
               "@{n='Start';e={$_.CreationDate.ToString('s')}},CommandLine | ConvertTo-Csv -NoTypeInformation")
    out += check_processes(list(csv.DictReader(io.StringIO(rows))), datetime.now())

    import pylsl
    streams = [{"name": s.name(), "hostname": s.hostname(), "source_id": s.source_id()}
               for s in pylsl.resolve_streams(2.0)]
    out += check_lsl(streams, socket.gethostname())

    out.append(check_network(adapters_up()))

    out.append((OK, f"LabRecorderCLI found ({LABRECORDER_CLI.name})") if LABRECORDER_CLI.is_file()
               else (WARN, f"LabRecorderCLI not at {LABRECORDER_CLI} (needed only from AU2)"))
    try:
        XDF_ROOT.mkdir(parents=True, exist_ok=True)
        tempfile.TemporaryFile(dir=XDF_ROOT).close()
        out.append((OK, f"{XDF_ROOT} writable"))
    except OSError as e:
        out.append((FAIL, f"{XDF_ROOT} not writable ({e})"))
    out.append(check_disk(shutil.disk_usage(XDF_ROOT if XDF_ROOT.exists() else REPO).free))
    return out


def main() -> int:
    results = gather()
    for level, text in results:
        print(f"{level:<4}  {text}")
    fails = sum(level == FAIL for level, _ in results)
    print(f"preflight: {fails} FAIL, {sum(level == WARN for level, _ in results)} WARN")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

"""
Recording by itself at Play (AU2, D-F6-244), with LabRecorderCLI and one LSL query per stream filtered by this
PC's hostname: only this PC's AURA and UnityMarkers go into the file, whatever the network shows (AU0, 18 Nov:
another lab PC's AURA and AURA_Markers stayed out). The CLI records every stream a query matches and has no
"exactly one" check, so the streams are counted here first; anything else → the manual path (LabRecorder's GUI,
Start by hand, D-F6-146, D-F6-197), and the session goes on.
"""

import os
import socket
import subprocess
import time
from pathlib import Path

from app.eeg.preflight import LABRECORDER_CLI

STREAMS = ("AURA", "UnityMarkers")
RESOLVE_S = 15.0  # Unity opens its outlet a moment after POST /sessions

MANUAL_STEPS = ("MANUAL: in LabRecorder press Update, tick the one AURA and UnityMarkers of this PC, "
                "check the file name has ses-{ses}, press Start")


def queries(host: str) -> list[str]:
    return [f"name='{name}' and hostname='{host}'" for name in STREAMS]


def command(path: str, host: str, cli: Path = LABRECORDER_CLI) -> list[str]:
    return [str(cli), path, *queries(host)]


def decide(streams: list[dict], host: str) -> tuple[str | None, list[str]]:
    """streams: name, hostname, source_id of every LSL stream seen. → (why not automatic or None, warnings)."""
    local = [s for s in streams if s["hostname"] == host]
    aura = [s for s in local if s["name"] == "AURA"]
    unity = [s for s in local if s["name"] == "UnityMarkers"]
    warns = []
    if any(s["source_id"] == "synthetic-aura" for s in aura):
        warns.append("WARNING: the AURA of this PC is the synthetic one (no cap)")
    if len(aura) != 1:
        return f"{len(aura)} AURA on this PC, expected exactly 1 (D-F6-197)", warns
    if len(unity) != 1:
        hint = ": an outlet left by an earlier Play, reopen Unity" if len(unity) > 1 else ""
        return f"{len(unity)} UnityMarkers on this PC, expected exactly 1{hint}", warns
    return None, warns


def resolve_until_ready(host: str, wait_s: float = RESOLVE_S) -> list[dict]:
    import pylsl

    deadline = time.monotonic() + wait_s
    while True:
        seen = [{"name": s.name(), "hostname": s.hostname(), "source_id": s.source_id()}
                for s in pylsl.resolve_streams(1.0)]
        names = [s["name"] for s in seen if s["hostname"] == host]
        if all(n in names for n in STREAMS) or time.monotonic() > deadline:
            return seen
        time.sleep(1.0)


class Recorder:
    """One LabRecorderCLI process. Its own output goes to a file next to the autorun log, not to the console."""

    def __init__(self, path: str, host: str, log_path: Path):
        self.path, self.host, self.log_path = path, host, log_path
        self.proc: subprocess.Popen | None = None
        self.started = 0.0

    def start(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        out = open(self.log_path, "a", encoding="utf-8", errors="replace")
        self.proc = subprocess.Popen(command(self.path, self.host), stdin=subprocess.PIPE, stdout=out,
                                     stderr=subprocess.STDOUT, text=True)
        self.started = time.monotonic()

    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def stop(self, timeout: float = 60.0) -> int | None:
        """Enter on its stdin: it writes the footers and closes the file. Safe to call twice."""
        if self.proc is None:
            return None
        if self.proc.poll() is None:
            try:
                self.proc.stdin.write("\n")
                self.proc.stdin.flush()
            except OSError:
                pass
            try:
                self.proc.wait(timeout)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        return self.proc.returncode


def start_for(session_id: str, path: str, log_dir: Path, host: str | None = None) -> tuple[Recorder | None, str]:
    """Starts the recording if this PC shows exactly one AURA and one UnityMarkers. → (recorder, line to print)."""
    host = host or socket.gethostname()
    ses = session_id[:8]
    if not Path(LABRECORDER_CLI).is_file():
        return None, f"{MANUAL_STEPS.format(ses=ses)} - reason: LabRecorderCLI not at {LABRECORDER_CLI}"
    streams = resolve_until_ready(host)
    reason, warns = decide(streams, host)
    for w in warns:
        print(w)
    if reason:
        return None, f"{MANUAL_STEPS.format(ses=ses)} - reason: {reason}"
    rec = Recorder(path, host, log_dir / f"{ses}-labrecordercli.txt")
    rec.start()
    time.sleep(3.0)
    if not rec.alive():  # exit 2: a query matched nothing between resolve and launch
        return None, (f"{MANUAL_STEPS.format(ses=ses)} - reason: LabRecorderCLI exited "
                      f"(code {rec.proc.returncode}, see {rec.log_path})")
    return rec, f"RECORDING (automatic): AURA + UnityMarkers of {host} -> {path}"


def size(path: str) -> int:
    return os.path.getsize(path) if os.path.exists(path) else 0

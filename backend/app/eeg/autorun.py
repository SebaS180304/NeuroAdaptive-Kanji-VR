"""
The operator's EEG steps, run by themselves (D-F6-152). The assistant presses Play and watches the signal in
AURA's software. Since AU2 (D-F6-244) the recording starts and stops by itself (recorder.py); when it cannot,
autorun prints MANUAL with the reason and the operator ticks AURA and UnityMarkers and presses Start as before.

On the PC (outside Docker, D-F6-132), started before Play:
    POSTGRES_HOST=127.0.0.1 python -m app.eeg.autorun
1. waits for a new session: its eeg_sessions row, written by POST /sessions with the XDF path;
2. starts baseline.py for it at once (it buffers until S4 ends, so it is running before S4), and live.py (the live
   EEG path, D-F6-171: epochs, reference and heartbeat while the session runs; stopped when it is COMPLETED);
3. waits for the session to be COMPLETED (S9), stops the recording (or waits for Stop in LabRecorder) and waits
   for the XDF to stop growing;
4. runs lsl_reader, sync (offset and drift, D-F6-157) and epochs on the XDF: epochs needs the offset (D-F6-176).
Everything it and baseline.py print, tracebacks and Python's fatal errors also go to logs/autorun-<time>.log; its
last line says it ended, so a log without that line is a process that died silently (D-F6-179 (2)).
"""

import asyncio
import faulthandler
import os
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from app.eeg import recorder, summary

POLL_S = 2.0
QUIET_S = 15.0  # LabRecorder flushes far more often than this while it records
LOG_DIR = Path("logs")


class _Tee:
    def __init__(self, console, log):
        self.streams = (log, console)  # the log first: a console that fails must not cost the line

    def write(self, s: str) -> int:
        for st in self.streams:
            st.write(s)
            st.flush()  # a death right after a print still leaves it in the file
        return len(s)

    def flush(self) -> None:
        for st in self.streams:
            st.flush()


def open_log(log_dir: Path = LOG_DIR):
    """Mirrors stdout and stderr into a new file and points faulthandler at it. Returns the open file."""
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"autorun-{datetime.now():%Y%m%d-%H%M%S}.log"
    log = open(path, "a", encoding="utf-8")
    sys.stdout, sys.stderr = _Tee(sys.stdout, log), _Tee(sys.stderr, log)
    faulthandler.enable(file=log)
    print(f"log: {path.resolve()}")
    return log


def start_child(args: list[str]) -> tuple[subprocess.Popen, threading.Thread]:
    """Runs args with its output relayed line by line to this console and the log."""
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}  # a pipe is cp1252 on Windows
    child = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
                             encoding="utf-8", errors="replace")
    relay = threading.Thread(target=lambda: [print(line, end="") for line in child.stdout], daemon=True)
    relay.start()
    return child, relay


def settled(history: list[tuple[float, int]], quiet_s: float = QUIET_S) -> bool:
    """(time, size) samples of the XDF: closed once it is not empty and its size held for quiet_s."""
    if not history or history[-1][1] <= 0:
        return False
    t_last, size = history[-1]
    since = t_last
    for t, s in reversed(history):
        if s != size:
            break
        since = t
    return t_last - since >= quiet_s


async def _scalar(sql: str, **params):
    from app.db.base import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        return (await db.execute(text(sql), params)).first()


async def wait_new_session(after) -> tuple[str, str]:
    print("waiting for a new session (Play in Unity)...")
    while True:
        row = await _scalar("SELECT e.session_id, e.xdf_path FROM eeg_sessions e "
                            "JOIN experiment_sessions s ON s.id = e.session_id "
                            "WHERE s.created_at > :t ORDER BY s.created_at DESC LIMIT 1", t=after)
        if row:
            return str(row[0]), row[1]
        await asyncio.sleep(POLL_S)


def recording_lost(rec, path: str) -> None:
    """The automatic recording ended before S9: its part is set aside and the operator goes to the GUI, same path."""
    mm, ss = divmod(int(time.monotonic() - rec.started), 60)
    print(f"RECORDING STOPPED at {mm:02d}:{ss:02d} (LabRecorderCLI exit {rec.proc.returncode}, see {rec.log_path})")
    if os.path.exists(path):
        part = path[:-4] + "_partial.xdf"
        os.replace(path, part)
        print(f"  its part is kept as {part}")
    print("  " + recorder.MANUAL_STEPS.format(ses=Path(path).name.split("_ses-")[-1][:8]) + ", now")


async def wait_completed(session_id: str, baseline: subprocess.Popen, rec=None, path: str = ""):
    """Returns the recorder still recording, or None if there was none or it was lost (manual from then on)."""
    last_check = time.monotonic()
    while not (await _scalar("SELECT 1 FROM experiment_sessions WHERE id = :s AND completed_at IS NOT NULL",
                             s=session_id)):
        if rec is not None and time.monotonic() - last_check >= 10:
            last_check = time.monotonic()
            if not rec.alive():
                recording_lost(rec, path)
                rec = None
        await asyncio.sleep(POLL_S)
    print("session COMPLETED (S9)." + ("" if rec is not None else " Now Stop in LabRecorder."))
    if baseline.poll() is None:  # S4 never ended inside this session
        baseline.terminate()
        print("WARNING: baseline.py had no S4 result; stopped. The alpha ratio is missing.")
    return rec


async def wait_xdf_closed(path: str) -> None:
    history, last_note = [], 0.0
    while not settled(history):
        size = os.path.getsize(path) if os.path.exists(path) else 0
        history.append((time.monotonic(), size))
        if time.monotonic() - last_note > 60:
            print(f"  XDF {size / 1e6:.1f} MB{'' if size else ' (not there yet: Start pressed?)'}; waiting for Stop...")
            last_note = time.monotonic()
        await asyncio.sleep(POLL_S)
    print("XDF closed.")


def start_recording(sid: str, path: str):
    return recorder.start_for(sid, path, LOG_DIR)


def network_up() -> list[str]:
    from app.eeg.preflight import adapters_up

    return adapters_up()


async def main() -> int:
    from datetime import datetime, timezone

    from app.eeg import epochs, lsl_reader, sync

    sid, path = await wait_new_session(datetime.now(timezone.utc))
    print(f"session {sid}\n  LabRecorder file must contain ses-{sid[:8]}: {path}")
    up = network_up()
    if up:
        print(f"WARNING: network up ({', '.join(up)}): turn it off before the cap (D-F6-193)")
    rec, line = start_recording(sid, path)
    print(line)
    how = "automatic (LabRecorderCLI)" if rec else "manual (LabRecorder GUI) - " + line.split("reason: ")[-1]
    print(f"recording: {how}")
    try:
        baseline, _ = start_child([sys.executable, "-m", "app.eeg.baseline", sid])
        live, _ = start_child([sys.executable, "-m", "app.eeg.live", sid])
        still = await wait_completed(sid, baseline, rec, path)
        if rec is not None and still is None:
            how = "automatic, lost mid-session, then manual (LabRecorder GUI)"
        live_csv = None
        try:  # before the stop: fill_from_xdf replaces these rows with the XDF cut (D-F6-240 (4))
            live_csv = await summary.export_live_epochs(sid, LOG_DIR)
        except Exception as e:  # the session's recording matters more than this file
            print(f"WARNING: live epochs not saved ({e})")
        if live is not None and live.poll() is None:  # its rows are replaced by fill_from_xdf below (D-F6-156)
            live.terminate()
        if rec is not None and rec.alive():
            print(f"recording stopped (LabRecorderCLI exit {rec.stop()})")
    finally:  # autorun dying must not leave the file open
        if rec is not None and rec.alive():
            rec.stop()
    await wait_xdf_closed(path)

    try:
        missing = await lsl_reader.fill_from_xdf(sid)
    except lsl_reader.AmbiguousStream as e:  # nothing written: the live epochs and reference stay (D-F6-206)
        print(e)
        return 1
    print("both streams recorded" if not missing else f"NOT multimodal, missing: {', '.join(missing)}")
    if missing:
        return 1
    offset, drift, detail = await sync.fill_from_xdf(sid)
    print(f"sync: offset {offset} ms · drift {drift} ms" + (f" · {detail['reason']}" if detail["reason"] else ""))
    eps = await epochs.fill_from_xdf(sid)
    counts = {q: sum(e["quality"] == q for e in eps) for q in ("GOOD", "ACCEPTABLE", "POOR")}
    print(f"{len(eps)} epochs: {counts}")
    if live_csv is not None:
        try:  # D-F6-281 (2): verify_eeg.sql shows it beside the two A-7 figures
            d = await summary.live_vs_xdf(sid, live_csv)
            print(f"live vs XDF: {d['differ']} of {d['common']} epochs differ ({d['differ_pct']} %) (D-F6-281 (2))")
        except Exception as e:  # a missing count never costs the summary
            print(f"WARNING: live vs XDF not compared ({e})")
    return await summary.write(sid, how, LOG_DIR)


if __name__ == "__main__":
    open_log()
    code = 1
    try:
        code = asyncio.run(main())
    except BaseException:  # Ctrl+C too: the log says how it ended
        traceback.print_exc()
    print(f"autorun ended · exit code {code}")
    sys.exit(code)

"""
The operator's EEG steps, run by themselves (D-F6-152). The assistant only presses Play, ticks AURA and
UnityMarkers and presses Start in LabRecorder, and watches the signal in AURA's software.

On the PC (outside Docker, D-F6-132), started before Play:
    POSTGRES_HOST=127.0.0.1 python -m app.eeg.autorun
1. waits for a new session: its eeg_sessions row, written by POST /sessions with the XDF path;
2. starts baseline.py for it at once (it buffers until S4 ends, so it is running before S4);
3. waits for the session to be COMPLETED (S9) and for the XDF to stop growing (Stop in LabRecorder,
   after block 3, D-F6-148);
4. runs lsl_reader and epochs on the XDF, as the operator did by hand on 5 Nov.
"""

import asyncio
import os
import subprocess
import sys
import time

from sqlalchemy import text

POLL_S = 2.0
QUIET_S = 15.0  # LabRecorder flushes far more often than this while it records


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


async def wait_completed(session_id: str, baseline: subprocess.Popen) -> None:
    while not (await _scalar("SELECT 1 FROM experiment_sessions WHERE id = :s AND completed_at IS NOT NULL",
                             s=session_id)):
        await asyncio.sleep(POLL_S)
    print("session COMPLETED (S9). Now block 3, then Stop in LabRecorder.")
    if baseline.poll() is None:  # S4 never ended inside this session
        baseline.terminate()
        print("WARNING: baseline.py had no S4 result; stopped. The alpha ratio is missing.")


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


async def main() -> int:
    from datetime import datetime, timezone

    from app.eeg import epochs, lsl_reader

    sid, path = await wait_new_session(datetime.now(timezone.utc))
    print(f"session {sid}\n  LabRecorder file must contain ses-{sid[:8]}: {path}")
    baseline = subprocess.Popen([sys.executable, "-m", "app.eeg.baseline", sid])  # same console, its own output
    await wait_completed(sid, baseline)
    await wait_xdf_closed(path)

    missing = await lsl_reader.fill_from_xdf(sid)
    print("both streams recorded" if not missing else f"NOT multimodal, missing: {', '.join(missing)}")
    if missing:
        return 1
    eps = await epochs.fill_from_xdf(sid)
    counts = {q: sum(e["quality"] == q for e in eps) for q in ("GOOD", "ACCEPTABLE", "POOR")}
    print(f"{len(eps)} epochs: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

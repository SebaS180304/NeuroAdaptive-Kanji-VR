"""
The two LSL streams of a session: the raw EEG of the AURA cap and Unity's markers
(Planteamiento_Tecnico_F4.md §2.2; P9 of D-F6-127).

Timestamps always come from LSL's corrected clock (clock sync + dejitter): AURA's
samples arrive in blocks of up to ~100 ms (29 Oct), so the raw block stamps would
smear every marker. Live, the stream is taken only from this PC: on the lab network
other machines publish their own `AURA*` streams (seen on 2 Nov).

The live inlet runs on the PC, outside Docker: the container does not see LSL
streams, with or without KnownPeers (spike of 2 Nov, D-F6-132).
"""

import json
import socket
import uuid

import pyxdf
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

EEG_STREAM = "AURA"
MARKER_STREAM = "UnityMarkers"


def load_xdf(path: str) -> dict[str, dict]:
    """The streams of an XDF by name, on LSL's corrected clock."""
    streams, _ = pyxdf.load_xdf(path, synchronize_clocks=True, dejitter_timestamps=True)
    by_name: dict[str, dict] = {}
    for s in streams:
        name = s["info"]["name"][0]
        if name in by_name:
            # Two streams with one name (e.g. a second PC's AURA) cannot be told apart later.
            raise ValueError(f"{path}: more than one stream named {name!r}")
        by_name[name] = s
    return by_name


def stream_info(stream: dict) -> dict:
    """What eeg_sessions.stream_info keeps of one stream."""
    info, stamps = stream["info"], stream["time_stamps"]
    return {
        "type": info["type"][0],
        "hostname": info["hostname"][0],
        "source_id": info["source_id"][0],
        "channel_count": int(info["channel_count"][0]),
        "nominal_srate": float(info["nominal_srate"][0]),
        "effective_srate": float(info.get("effective_srate", 0) or 0),
        "samples": len(stamps),
        "first_ts": float(stamps[0]) if len(stamps) else None,
        "last_ts": float(stamps[-1]) if len(stamps) else None,
    }


def missing_streams(streams: dict[str, dict]) -> list[str]:
    """Without both streams the session does not count as multimodal (P9)."""
    return [n for n in (EEG_STREAM, MARKER_STREAM) if n not in streams]


async def save(db: AsyncSession, session_id: uuid.UUID | str, xdf_path: str,
               streams: dict[str, dict]) -> None:
    """Writes (or rewrites) the session's eeg_sessions row from its XDF."""
    info = {name: stream_info(s) for name, s in streams.items()}
    missing = missing_streams(streams)
    reason = f"missing stream: {', '.join(missing)}" if missing else None
    await db.execute(text(
        "INSERT INTO eeg_sessions (session_id, xdf_path, stream_info, not_counted_reason) "
        "VALUES (:s, :p, CAST(:i AS jsonb), :r) "
        "ON CONFLICT (session_id) DO UPDATE SET xdf_path = EXCLUDED.xdf_path, "
        "stream_info = EXCLUDED.stream_info, not_counted_reason = EXCLUDED.not_counted_reason"),
        {"s": str(session_id), "p": xdf_path, "i": json.dumps(info), "r": reason})


def open_local_inlet(name: str, timeout: float = 5.0, host: str | None = None):
    """The live inlet of the stream `name` published by this PC, on the corrected clock."""
    import pylsl  # only where the live reader runs (the PC); the container reads XDFs

    host = host or socket.gethostname()
    found = [s for s in pylsl.resolve_byprop("name", name, timeout=timeout) if s.hostname() == host]
    if len(found) != 1:
        raise LookupError(f"{len(found)} LSL streams named {name!r} on {host}; expected 1")
    return pylsl.StreamInlet(found[0], processing_flags=pylsl.proc_clocksync | pylsl.proc_dejitter)


async def fill_from_xdf(session_id: str) -> list[str]:
    """After the session: reads the XDF its eeg_sessions row points at and stores the stream info.
    Returns the missing streams (empty when the session has both)."""
    from app.db.base import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        path = (await db.execute(text("SELECT xdf_path FROM eeg_sessions WHERE session_id = :s"),
                                 {"s": session_id})).scalar_one()
        streams = load_xdf(path)
        await save(db, session_id, path, streams)
        await db.commit()
    return missing_streams(streams)


if __name__ == "__main__":
    # On the PC, after the session (the XDF is on its disk):
    #   POSTGRES_HOST=127.0.0.1 python -m app.eeg.lsl_reader <session_id>
    import asyncio
    import sys

    missing = asyncio.run(fill_from_xdf(sys.argv[1]))
    print("both streams recorded" if not missing else f"NOT multimodal, missing: {', '.join(missing)}")
    sys.exit(1 if missing else 0)

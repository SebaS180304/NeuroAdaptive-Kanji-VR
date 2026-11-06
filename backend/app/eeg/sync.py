"""
Offset and drift of the sync test (F4 §2.4; D-F6-150, D-F6-157, D-F6-159).

In S3 and again in S9 the assistant strikes Cz's housing with a controller's ring and pulls the trigger in
the same movement, 5 times: each pull is a SYNC_TAP marker, each strike a spike on Cz. For each tap:
  - the peak is the largest |Cz − median| within ±500 ms of the marker (filtered signal, zero-phase,
    so the filter does not move it);
  - it is clear when it exceeds 5× the MAD of Cz in the 2 s before that window;
  - its lag is peak time − marker time (positive: the spike comes after the marker).
Offset = median lag of the clear S3 taps; drift = median of S9 − median of S3. With fewer than 3 clear taps
in a phase, what needs it stays empty and the reason goes in sync_detail. F4 §2.4 asks |offset| ≤ 100 ms
and drift < 50 ms; that check is verify_eeg.sql's, not this file's.
"""

import json
import uuid

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

WINDOW_S = 0.5
PRE_S = 2.0
K_MAD = 5.0
MIN_TAPS = 3
PHASES = ("S3", "S9")


def _tap(x: np.ndarray, ts: np.ndarray, t: float) -> dict:
    pre = x[(ts >= t - WINDOW_S - PRE_S) & (ts < t - WINDOW_S)]
    win = (ts >= t - WINDOW_S) & (ts <= t + WINDOW_S)
    if len(pre) < 2 or not win.any():
        return {"valid": False, "lag_ms": None, "peak_uv": None, "mad_uv": None, "why": "outside the recording"}
    med = float(np.median(pre))
    mad = float(np.median(np.abs(pre - med)))
    i = int(np.argmax(np.abs(x[win] - med)))
    peak = float(abs(x[win][i] - med))
    valid = peak > K_MAD * mad
    return {"valid": bool(valid), "lag_ms": round(float(ts[win][i] - t) * 1000, 1) if valid else None,
            "peak_uv": round(peak, 1), "mad_uv": round(mad, 2), "why": None if valid else "no clear peak"}


def compute(cz: np.ndarray, ts: np.ndarray, markers: list[tuple[float, dict]]):
    """cz: filtered Cz in µV; ts: its LSL stamps; markers: UnityMarkers as (LSL time, event).
    Returns (offset_ms, drift_ms, detail) for eeg_sessions."""
    cz, ts = np.asarray(cz, dtype=float), np.asarray(ts, dtype=float)
    taps = [{"phase": m.get("phase"), "index": m.get("index"), "lsl_time": t, **_tap(cz, ts, t)}
            for t, m in markers if m.get("event") == "SYNC_TAP"]
    lags = {p: [d["lag_ms"] for d in taps if d["phase"] == p and d["valid"]] for p in PHASES}
    med = {p: float(np.median(v)) if len(v) >= MIN_TAPS else None for p, v in lags.items()}

    reasons = [] if taps else ["no SYNC_TAP markers in the recording"]
    for p in PHASES:
        if taps and med[p] is None:
            n = sum(d["phase"] == p for d in taps)
            reasons.append(f"{p}: {len(lags[p])} of {n} taps with a clear peak (< {MIN_TAPS})")
    offset = med["S3"]
    drift = round(med["S9"] - med["S3"], 1) if offset is not None and med["S9"] is not None else None
    detail = {"window_ms": int(WINDOW_S * 1000), "pre_s": PRE_S, "k_mad": K_MAD, "min_taps": MIN_TAPS,
              "median_lag_ms": med, "taps": taps, "reason": "; ".join(reasons) or None}
    return offset, drift, detail


async def save(db: AsyncSession, session_id: uuid.UUID | str, offset, drift, detail: dict) -> None:
    await db.execute(text("UPDATE eeg_sessions SET sync_offset_ms = :o, sync_drift_ms = :d, "
                          "sync_detail = CAST(:j AS jsonb) WHERE session_id = :s"),
                     {"s": str(session_id), "o": offset, "d": drift, "j": json.dumps(detail)})


async def fill_from_xdf(session_id: str):
    """After the session, on the PC: Cz and the SYNC_TAP markers of its XDF → eeg_sessions."""
    from app.db.base import AsyncSessionLocal
    from app.eeg import epochs, lsl_reader, preprocess

    async with AsyncSessionLocal() as db:
        path, montage = (await db.execute(text("SELECT xdf_path, montage FROM eeg_sessions WHERE session_id = :s"),
                                          {"s": session_id})).one()
        streams = lsl_reader.load_xdf(path)
        aura = streams[lsl_reader.EEG_STREAM]
        sr = float(aura["info"]["nominal_srate"][0])
        cz = int(next(k for k, v in montage.items() if v == "Cz")[2:]) - 1  # "CH5" → column 4
        x = preprocess.filter_eeg(aura["time_series"], sr)[:, cz]
        result = compute(x, aura["time_stamps"], epochs.markers_of(streams.get(lsl_reader.MARKER_STREAM)))
        await save(db, session_id, *result)
        await db.commit()
    return result


if __name__ == "__main__":
    # On the PC, after epochs:  POSTGRES_HOST=127.0.0.1 python -m app.eeg.sync <session_id>
    import asyncio
    import sys

    offset, drift, detail = asyncio.run(fill_from_xdf(sys.argv[1]))
    print(f"sync: offset {offset} ms · drift {drift} ms" + (f" · {detail['reason']}" if detail["reason"] else ""))

"""
Offset and drift of the sync test (F4 §2.4; D-F6-150, D-F6-157, D-F6-159, D-F6-161, D-F6-173, D-F6-176).

In S3 and again in S9 the assistant strikes Cz's housing with a controller's ring and pulls the trigger in
the same movement, 5 times: each pull is a SYNC_TAP marker, each strike a spike on Cz. On raw Cz, for each tap:
  - the peak is the largest |Cz − median| within ±500 ms of the marker (median of the 2 s before that window);
  - it is clear when it exceeds 5× the MAD of Cz in those 2 s;
  - the onset of the strike is the last point before the peak under max(5 × noise, 10 % of the peak), with
    level and noise (MAD × 1.4826) taken from 400 to 150 ms before the peak (F4 Registro, 6 Nov);
  - its lag is onset time − marker time (positive: the strike comes after the marker). The peak's lag is
    kept in sync_detail and corrects nothing (it carries the ≈ 110 ms the strike takes to rise).
Offset = median lag of the clear S3 taps; drift = median of S9 − median of S3. With fewer than 3 clear taps
in S3 there is no offset; in S9 the offset stays and the session is marked by the reason, without drift.
F4 §2.4 asks spread ≤ 50 ms, drift < 50 ms and |offset| ≤ 250 ms; that check is verify_eeg.sql's, not this file's.
"""

import json
import uuid

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

WINDOW_S = 0.5
PRE_S = 2.0
K_MAD = 5.0
ONSET_FRACTION = 0.1
NOISE_FROM_S, NOISE_TO_S, MAD_TO_SD = 0.4, 0.15, 1.4826
MIN_TAPS = 3
PHASES = ("S3", "S9")


def _tap(x: np.ndarray, ts: np.ndarray, t: float) -> dict:
    empty = {"valid": False, "lag_ms": None, "peak_lag_ms": None, "peak_uv": None, "mad_uv": None}
    pre = x[(ts >= t - WINDOW_S - PRE_S) & (ts < t - WINDOW_S)]
    win = (ts >= t - WINDOW_S) & (ts <= t + WINDOW_S)
    if len(pre) < 2 or not win.any():
        return {**empty, "why": "outside the recording"}
    med = float(np.median(pre))
    mad = float(np.median(np.abs(pre - med)))
    level, stamps = np.abs(x[win] - med), ts[win]
    i = int(np.argmax(level))
    peak = float(level[i])
    seen = {**empty, "peak_uv": round(peak, 1), "mad_uv": round(mad, 2)}
    if peak <= K_MAD * mad:
        return {**seen, "why": "no clear peak"}
    near = x[(ts >= stamps[i] - NOISE_FROM_S) & (ts < stamps[i] - NOISE_TO_S)]
    if len(near) < 2:
        return {**seen, "why": "no onset before the peak"}
    base = float(np.median(near))
    rise = np.abs(x[win] - base)
    noise = MAD_TO_SD * float(np.median(np.abs(near - base)))
    quiet = np.flatnonzero(rise[:i] < max(K_MAD * noise, ONSET_FRACTION * rise[i]))
    if not quiet.size:
        return {**seen, "why": "no onset before the peak"}
    return {**seen, "valid": True, "lag_ms": round(float(stamps[quiet[-1]] - t) * 1000, 1),
            "peak_lag_ms": round(float(stamps[i] - t) * 1000, 1), "why": None}


def compute(cz: np.ndarray, ts: np.ndarray, markers: list[tuple[float, dict]]):
    """cz: raw Cz in µV; ts: its LSL stamps; markers: UnityMarkers as (LSL time, event).
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
    spread = round(float(np.std(lags["S3"] + lags["S9"], ddof=1)), 1) if offset is not None else None
    detail = {"window_ms": int(WINDOW_S * 1000), "pre_s": PRE_S, "k_mad": K_MAD, "onset_fraction": ONSET_FRACTION,
              "onset_noise_window_ms": [int(NOISE_FROM_S * 1000), int(NOISE_TO_S * 1000)],
              "min_taps": MIN_TAPS, "median_lag_ms": med, "spread_ms": spread, "taps": taps,
              "reason": "; ".join(reasons) or None}
    return offset, drift, detail


async def save(db: AsyncSession, session_id: uuid.UUID | str, offset, drift, detail: dict) -> None:
    await db.execute(text("UPDATE eeg_sessions SET sync_offset_ms = :o, sync_drift_ms = :d, "
                          "sync_detail = CAST(:j AS jsonb) WHERE session_id = :s"),
                     {"s": str(session_id), "o": offset, "d": drift, "j": json.dumps(detail)})


async def fill_from_xdf(session_id: str):
    """After the session, on the PC: Cz and the SYNC_TAP markers of its XDF → eeg_sessions."""
    from app.db.base import AsyncSessionLocal
    from app.eeg import epochs, lsl_reader

    async with AsyncSessionLocal() as db:
        path, montage = (await db.execute(text("SELECT xdf_path, montage FROM eeg_sessions WHERE session_id = :s"),
                                          {"s": session_id})).one()
        streams = lsl_reader.load_xdf(path)
        aura = streams[lsl_reader.EEG_STREAM]
        cz = int(next(k for k, v in montage.items() if v == "Cz")[2:]) - 1  # "CH5" → column 4
        x = np.asarray(aura["time_series"], dtype=float)[:, cz]  # raw: the filter smears the strike's onset
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

"""
The S4 eyes-closed test: the proof that the signal is real (D-F6-73, D-F6-75; Reevaluacion §5.4).
Alpha (8–12 Hz) power with the eyes closed over alpha with the eyes open, in P3, Pz and P4 (and Oz
if it entered the montage); the test passes when every one is ≥ 1.2. Power is the mean over the 1 s
chunks of each segment, leaving out chunks with a blink or an amplitude over the epochs.py limits.

Unity marks the segments in the UnityMarkers stream (EYES_OPEN_START/END, EYES_CLOSED_START/END).
The result goes to eeg_sessions (alpha_ratio, alpha_passed) and as an EEG_BASELINE_RESULT session
event, written by this process like the backend writes ADAPTATION_OUTCOME.

Live, on the PC (outside Docker, D-F6-132), started by the operator before S4:
    POSTGRES_HOST=127.0.0.1 python -m app.eeg.baseline <session_id>
It reads both streams of this PC and writes the result when EYES_CLOSED_END arrives.
"""

import json
import uuid

import numpy as np
from scipy.signal import welch
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.eeg import epochs

PARIETAL = ("Oz", "P3", "Pz", "P4")
PASS_RATIO = 1.2
ALPHA_HZ = (8, 12)
# The fixed montage of D-F6-72, as migration 0010 writes it (a session without its eeg_sessions row yet).
DEFAULT_MONTAGE = {"CH1": "Fp1", "CH2": "F3", "CH3": "Fz", "CH4": "F4", "CH5": "Cz", "CH6": "P3", "CH7": "Pz", "CH8": "P4"}
SEGMENTS = ("EYES_OPEN_START", "EYES_OPEN_END", "EYES_CLOSED_START", "EYES_CLOSED_END")


def _alpha(x: np.ndarray, ts: np.ndarray, srate: float, blink: list[int], index: list[int],
           cols: list[int], span: tuple[float, float]) -> np.ndarray | None:
    powers, t = [], span[0]
    while t + 1 <= span[1] + 1e-9:
        lo, hi = np.searchsorted(ts, [t, t + 1])
        t += 1
        seg = x[lo:hi]
        if hi - lo < epochs.MIN_SAMPLES * srate:
            continue
        if (np.abs(seg[:, blink]) > epochs.BLINK_UV).any() or (np.abs(seg[:, index]) > epochs.MAX_UV).any():
            continue
        f, p = welch(seg[:, cols], fs=srate, window="hann", nperseg=hi - lo, axis=0)
        powers.append(p[(f >= ALPHA_HZ[0]) & (f <= ALPHA_HZ[1])].sum(axis=0))
    return np.mean(powers, axis=0) if powers else None


def alpha_ratio(x: np.ndarray, ts: np.ndarray, srate: float, montage: dict,
                open_span: tuple[float, float], closed_span: tuple[float, float]) -> dict[str, float]:
    """x: filtered EEG (samples × channels, µV); spans on the same clock as ts. Label → closed / open."""
    ts = np.asarray(ts, dtype=float)
    labels = [montage[f"CH{i + 1}"] for i in range(x.shape[1])]
    blink = [labels.index("Fp1")] if "Fp1" in labels else [i for i, l in enumerate(labels) if l in ("F3", "Fz", "F4")]
    index = [i for i, l in enumerate(labels) if l != "Fp1"]
    cols = [i for i, l in enumerate(labels) if l in PARIETAL]
    a_open = _alpha(x, ts, srate, blink, index, cols, open_span)
    a_closed = _alpha(x, ts, srate, blink, index, cols, closed_span)
    if a_open is None or a_closed is None:
        return {}  # no clean second in a segment: the test cannot pass
    return {labels[c]: round(float(a_closed[k] / a_open[k]), 2) for k, c in enumerate(cols)}


def passed(ratios: dict[str, float]) -> bool:
    return bool(ratios) and all(v >= PASS_RATIO for v in ratios.values())


def spans(markers: list[tuple[float, dict]]) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """The eyes-open and eyes-closed spans from the S4 markers (the last S4 if it ran twice)."""
    at = {m.get("event"): t for t, m in markers if m.get("event") in SEGMENTS}
    if any(s not in at for s in SEGMENTS):
        return None
    return (at["EYES_OPEN_START"], at["EYES_OPEN_END"]), (at["EYES_CLOSED_START"], at["EYES_CLOSED_END"])


async def save(db: AsyncSession, session_id: uuid.UUID | str, ratios: dict[str, float]) -> bool:
    ok = passed(ratios)
    sid, r = str(session_id), json.dumps(ratios)
    await db.execute(text(
        "INSERT INTO eeg_sessions (session_id, alpha_ratio, alpha_passed) VALUES (:s, CAST(:r AS jsonb), :ok) "
        "ON CONFLICT (session_id) DO UPDATE SET alpha_ratio = EXCLUDED.alpha_ratio, alpha_passed = EXCLUDED.alpha_passed"),
        {"s": sid, "r": r, "ok": ok})
    payload = {"alpha_ratio": ratios, "passed": ok, "threshold": PASS_RATIO, "band_hz": list(ALPHA_HZ)}
    await db.execute(text("INSERT INTO session_events (session_id, event_type, payload) "
                          "VALUES (:s, 'EEG_BASELINE_RESULT', CAST(:p AS json))"),
                     {"s": sid, "p": json.dumps(payload)})
    return ok


async def run_live(session_id: str) -> dict[str, float]:
    """Buffers this PC's AURA and UnityMarkers until EYES_CLOSED_END, then stores the result."""
    from app.db.base import AsyncSessionLocal
    from app.eeg import lsl_reader, preprocess

    eeg_in = lsl_reader.open_local_inlet(lsl_reader.EEG_STREAM)
    mk_in = lsl_reader.open_local_inlet(lsl_reader.MARKER_STREAM)
    srate = eeg_in.info().nominal_srate()
    samples, stamps, markers = [], [], []
    print(f"waiting for S4 ({lsl_reader.EEG_STREAM} at {srate} Hz and {lsl_reader.MARKER_STREAM})...")
    while (s := spans(markers)) is None:
        chunk, ts = eeg_in.pull_chunk(timeout=0.2)
        samples += chunk
        stamps += ts
        m, mts = mk_in.pull_chunk(timeout=0.0)
        markers += [(t, json.loads(v[0])) for v, t in zip(m, mts)]
    while stamps and stamps[-1] < s[1][1]:  # the last samples of the closed segment arrive late
        chunk, ts = eeg_in.pull_chunk(timeout=0.5)
        samples += chunk
        stamps += ts

    async with AsyncSessionLocal() as db:
        montage = (await db.execute(text("SELECT montage FROM eeg_sessions WHERE session_id = :s"),
                                    {"s": session_id})).scalar_one_or_none() or DEFAULT_MONTAGE
        x = preprocess.filter_eeg(np.asarray(samples), srate)
        ratios = alpha_ratio(x, np.asarray(stamps), srate, montage, *s)
        await save(db, session_id, ratios)
        await db.commit()
    return ratios


if __name__ == "__main__":
    import asyncio
    import sys

    r = asyncio.run(run_live(sys.argv[1]))
    print(f"S4 alpha ratio {r} -> {'PASSED' if passed(r) else 'NOT PASSED'} (>= {PASS_RATIO})")

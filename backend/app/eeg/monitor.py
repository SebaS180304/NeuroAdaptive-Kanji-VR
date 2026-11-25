"""
The live monitor's per-channel figures (M1b; D-F6-231 (3), D-F6-254, D-F6-265), exactly as the EEG chat validated them
(Planteamiento_Tecnico_F4.md, Registro 19 Nov 12:45, point 2). Pure: live.py's raw buffer in, one dict out, written to
eeg_sessions.monitor. It reads the same buffer as the epoch cut and never changes it (Buffer.new_epochs() untouched).

  - filtered figures: preprocess.filter_eeg over [now - 17 s, now], using only [now - 7 s, now - 2 s] (the zero-phase
    filter bends the last 1–2 s of the buffer; D-F6-254 (1));
  - RMS of that window; % of its samples over 100 µV, leaving out ±1 s around each SYNC_TAP (D-F6-224); under 1 s left
    → the previous colour with "Sync tap" (D-F6-254 (2));
  - flat: any of the 5 non-overlapping 1 s chunks with peak-to-peak under FLAT_UV; no data: a chunk under MIN_SAMPLES
    of its nominal samples, or no sample for more than 2 s;
  - colour: OK < 5 %, Watch 5–20 % (or the last closed 30 s bin of the grid over 20 %), Bad > 20 % or flat;
  - 60 Hz: Welch on the RAW window ending at now (Hann 2 s, 50 % overlap, density), A = sqrt(2 · Σ_{59..61 Hz} PSD · Δf);
    the session's = median of the 8 (Watch from 800 µV); a channel under 0.3x or over 3x the others' median is marked.
Values are "to validate" as the rest of F4; no rule of the engine reads them.
"""

import numpy as np
from scipy.signal import welch

from app.eeg import epochs, preprocess

SPAN_S, PAD_S, EDGE_S = 5.0, 10.0, 2.0
OK_PCT, BAD_PCT = 5.0, 20.0
SESSION_60_WATCH_UV = 800.0
MARK_LOW, MARK_HIGH = 0.3, 3.0
GAP_S = 2.0


def _line(raw: np.ndarray, srate: float) -> np.ndarray:
    f, p = welch(raw, fs=srate, window="hann", nperseg=int(2 * srate), noverlap=int(srate), axis=0)
    band = (f >= 59) & (f <= 61)
    return np.sqrt(2 * p[band].sum(axis=0) * (f[1] - f[0]))


def compute(x: np.ndarray, ts: np.ndarray, srate: float, labels: list[str], markers: list[tuple[float, dict]],
            now: float, previous: dict | None = None, last_bin_over: dict[str, float] | None = None) -> dict:
    """x: raw EEG (samples x channels, µV); ts: its stamps on the markers' clock; now: the newest stamp.
    previous: the last result (for "Sync tap"); last_bin_over: % over 100 µV per channel in the last closed 30 s bin."""
    x, ts = np.asarray(x, float), np.asarray(ts, float)
    lo, hi = now - SPAN_S - EDGE_S, now - EDGE_S
    seg = (ts >= lo - PAD_S) & (ts <= now)
    enough = seg.sum() > srate  # under 1 s of signal (the start of the buffer): nothing to filter yet
    y = preprocess.filter_eeg(x[seg], srate) if enough else np.empty((0, x.shape[1]))
    tw = ts[seg] if enough else np.empty(0)
    win = (tw >= lo) & (tw < hi)
    yw, tww = y[win], tw[win]

    keep = np.ones(len(tww), bool)
    for t, m in markers:
        if m.get("event") == "SYNC_TAP":
            keep &= np.abs(tww - t) > epochs.TAP_GUARD_S
    tapped = keep.sum() < srate          # under 1 s left outside the taps

    expected = srate * 1.0
    chunks = [(tww >= lo + k) & (tww < lo + k + 1) for k in range(int(SPAN_S))]
    gaps = np.diff(np.concatenate([[lo], tww, [hi]])) if len(tww) else np.array([SPAN_S])
    no_data = any(c.sum() < epochs.MIN_SAMPLES * expected for c in chunks) or gaps.max() > GAP_S

    raw = x[(ts > now - SPAN_S) & (ts <= now)]
    line = _line(raw - raw.mean(axis=0), srate) if len(raw) >= 2 * srate else np.full(x.shape[1], np.nan)
    prev = {c["label"]: c for c in (previous or {}).get("channels", [])}

    out = []
    for i, label in enumerate(labels):
        others = np.delete(line, i)
        ratio = line[i] / np.nanmedian(others) if np.nanmedian(others) > 0 else np.nan
        mark = bool(np.isfinite(ratio) and (ratio < MARK_LOW or ratio > MARK_HIGH))
        l60 = None if not np.isfinite(line[i]) else round(float(line[i]), 1)
        if no_data or not len(yw):
            out.append({"label": label, "l60_uv": l60, "rms_uv": None, "over_pct": None, "status": "No data",
                        "flat": False, "sync_tap": False, "mark_60": mark})
            continue
        col = yw[:, i]
        rms = float(np.sqrt(np.mean((col - col.mean()) ** 2)))
        flat = any(c.any() and np.ptp(col[c]) < epochs.FLAT_UV for c in chunks)
        if tapped:
            p = prev.get(label, {})
            out.append({"label": label, "l60_uv": l60, "rms_uv": round(rms, 1), "over_pct": p.get("over_pct"),
                        "status": p.get("status", "No data"), "flat": flat, "sync_tap": True, "mark_60": mark})
            continue
        over = float(100 * np.mean(np.abs(col[keep]) > epochs.MAX_UV))
        status = ("Bad" if over > BAD_PCT or flat else
                  "Watch" if over >= OK_PCT or (last_bin_over or {}).get(label, 0.0) > BAD_PCT else "OK")
        out.append({"label": label, "l60_uv": l60, "rms_uv": round(rms, 1), "over_pct": round(over, 1),
                    "status": status, "flat": flat, "sync_tap": False, "mark_60": mark})

    session = float(np.nanmedian(line)) if np.isfinite(line).any() else None
    return {"window_lsl": [lo, hi], "computed_lsl": now, "channels": out,
            "session_60_uv": None if session is None else round(session, 1),
            "session_60_status": "Watch" if session is not None and session >= SESSION_60_WATCH_UV else "OK"}

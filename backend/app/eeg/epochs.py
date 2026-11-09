"""
Epochs of a session's EEG and their quality (D-F6-73; Reevaluacion_EEG_Justificacion.md §4.4.1
and §5.3; Planteamiento_Tecnico_F4.md §2.2).

An epoch is 5 s of filtered signal and a new one starts every 2.5 s. Each epoch keeps its nine
1 s chunks, one starting every 0.5 s (D-F6-163), as clean or not, so the decision window can count
every clean second once even when two overlapping epochs share it (P7 of D-F6-127). A chunk is dropped for:
  - a blink: Fp1 over 75 µV, 200 ms around it (F3, Fz and F4 if Fp1 moved to Oz, D-F6-75);
  - amplitude: an index channel (all but Fp1) over 100 µV;
  - a flat index channel, or missing samples;
  - an open HEAD_AWAY;
  - the half second after a sound onset (D-F6-149) (select and reading at ANSWER_SELECTED, the result sound,
    the stage sound before STATE_ENTERED, each S5 reading at AUDIO_ONSET);
  - a FRAME_HITCH over 100 ms (D-F6-129).
Quality is the time the union of clean chunks covers (D-F6-166): GOOD ≥ 4 s, ACCEPTABLE ≥ 3 s, POOR < 3 s.
The "at least 2 clean chunks" of that decision needs no check: 2 chunks cover 2 s at most.

Thresholds are *to validate* (F4 §6). Not here: the IMU (AURA does not send it yet) and
saturation (AURA's range is not known).
"""

import bisect
import json
import math
import statistics
import uuid

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.eeg import features

EPOCH_S, STEP_S, CHUNK_S, CHUNK_STEP_S, CHUNKS = 5.0, 2.5, 1.0, 0.5, 9
BLINK_UV, BLINK_PAD_S = 75.0, 0.2
MAX_UV = 100.0
FLAT_UV = 1.0         # peak to peak in a chunk; proposal, the 29 Oct signal sits at 7–17 µV
MIN_SAMPLES = 0.9     # of a chunk's nominal samples
SOUND_S = 0.5         # rule B, D-F6-149: every sound, every stage, the three conditions
HITCH_MS = 100.0
EPOCHS_VERSION = "rule B (D-F6-149), 9 chunks by time covered (D-F6-163, D-F6-166), S3 offset (D-F6-176)"  # stored with the filter (D-F6-156); bump when a drop rule changes


def covered_s(chunk_clean: list[bool]) -> float:
    """Seconds of the epoch inside at least one clean chunk: overlapping chunks count once."""
    covered, end = 0.0, 0.0
    for k, clean in enumerate(chunk_clean):
        if clean:
            start = k * CHUNK_STEP_S
            covered += CHUNK_S - max(0.0, end - start)
            end = start + CHUNK_S
    return covered


def quality(covered: float) -> str:
    return "GOOD" if covered >= 4 else "ACCEPTABLE" if covered >= 3 else "POOR"


def markers_of(stream: dict | None) -> list[tuple[float, dict]]:
    """The UnityMarkers stream of an XDF as (LSL time, event)."""
    if stream is None:
        return []
    return [(float(t), json.loads(v[0])) for t, v in zip(stream["time_stamps"], stream["time_series"])]


def excluded_intervals(markers: list[tuple[float, dict]]) -> list[tuple[float, float]]:
    """LSL time spans that no clean chunk may touch, from the markers."""
    out, answered, away = [], {}, {}
    for t, m in markers:
        e = m.get("event")
        if e == "FRAME_HITCH" and m.get("duration_ms", 0) > HITCH_MS:
            out.append((t - m["duration_ms"] / 1000, t))  # pushed when the slow frame ends
        elif e == "AUDIO_ONSET":  # each S5 reading (D-F6-138)
            out.append((t, t + SOUND_S))
        elif e == "ANSWER_SELECTED":
            answered[m.get("trial_id")] = t
            out.append((t, t + SOUND_S))
        elif e == "TRIAL_COMPLETED" and m.get("result_sound_offset_ms") is not None and m.get("trial_id") in answered:
            s = answered[m["trial_id"]] + m["result_sound_offset_ms"] / 1000  # relative to ANSWER_SELECTED
            out.append((s, s + SOUND_S))
        elif e == "STATE_ENTERED" and m.get("transition_sound_lead_ms") is not None:
            s = t - m["transition_sound_lead_ms"] / 1000
            out.append((s, s + SOUND_S))
        elif e == "HEAD_AWAY":
            away[m.get("episode")] = t + m.get("onset_offset_ms", 0) / 1000
        elif e == "HEAD_RETURNED" and m.get("episode") in away:
            left = away.pop(m["episode"])
            out.append((left, left + m["duration_ms"] / 1000 if m.get("duration_ms") is not None else t))
    out += [(left, math.inf) for left in away.values()]  # never came back inside the recording
    return out


def _context(markers: list[tuple[float, dict]]):
    """(times, [(state, esl, open trial)]) after each session event, and the session clock origin."""
    times, ctx, offsets, trial = [], [], [], None
    for t, m in markers:
        if "schema_version" not in m:  # FRAME_HITCH and other raw markers carry no session context
            continue
        e = m.get("event")
        if e == "TRIAL_STARTED":
            trial = m.get("trial_id")
        elif e in ("TRIAL_COMPLETED", "STATE_ENTERED"):
            trial = None
        times.append(t)
        ctx.append((m.get("state"), m.get("esl"), trial))
        if m.get("session_elapsed_ms") is not None:
            offsets.append(t - m["session_elapsed_ms"] / 1000)
    return times, ctx, (statistics.median(offsets) if offsets else None)


def make_epochs(x: np.ndarray, ts: np.ndarray, srate: float, montage: dict,
                markers: list[tuple[float, dict]]) -> list[dict]:
    """x: filtered EEG, samples × channels in µV; ts: corrected LSL stamps; montage: CH1… → label."""
    ts = np.asarray(ts, dtype=float)
    labels = [montage[f"CH{i + 1}"] for i in range(x.shape[1])]
    blink_ch = [labels.index("Fp1")] if "Fp1" in labels else [i for i, l in enumerate(labels) if l in ("F3", "Fz", "F4")]
    index_ch = [i for i, l in enumerate(labels) if l != "Fp1"]

    bad = (np.abs(x[:, blink_ch]) > BLINK_UV).any(axis=1)
    pad = int(round(BLINK_PAD_S * srate))
    if pad and bad.any():
        bad = np.convolve(bad, np.ones(2 * pad + 1), mode="same") > 0
    bad |= (np.abs(x[:, index_ch]) > MAX_UV).any(axis=1)
    for a, b in excluded_intervals(markers):
        bad |= (ts >= a) & (ts < b)

    times, ctx, clock0 = _context(markers)
    to_ms = (lambda t: int(round((t - clock0) * 1000))) if clock0 is not None else (lambda t: None)
    min_n = MIN_SAMPLES * srate * CHUNK_S

    out = []
    span = ts[-1] - ts[0] + 1 / srate if len(ts) else 0.0  # the last sample covers 1/srate too
    n = int((span - EPOCH_S) // STEP_S) + 1
    for j in range(max(n, 0)):
        start = float(ts[0] + j * STEP_S)
        flags, clean = [], []
        for k in range(CHUNKS):
            chunk = start + k * CHUNK_STEP_S
            lo, hi = np.searchsorted(ts, [chunk, chunk + CHUNK_S])
            seg = x[lo:hi, index_ch]
            flags.append(bool(hi - lo >= min_n and not bad[lo:hi].any() and (np.ptp(seg, axis=0) >= FLAT_UV).all()))
            if flags[-1]:
                clean.append(x[lo:hi])
        i = bisect.bisect_right(times, start + EPOCH_S / 2) - 1  # the context at the epoch's midpoint
        state, esl, trial = ctx[i] if i >= 0 else (None, None, None)
        covered = covered_s(flags)
        grade = quality(covered)
        out.append({"epoch_index": j, "lsl_start": start, "start_ms": to_ms(start), "end_ms": to_ms(start + EPOCH_S),
                    "game_state": state, "esl_level": esl, "trial_id": trial, "chunk_clean": flags,
                    "clean_fraction": covered / EPOCH_S, "quality": grade,
                    **(features.compute(clean, labels, srate) if grade != "POOR" else features.EMPTY)})
    return out


async def save(db: AsyncSession, session_id: uuid.UUID | str, eps: list[dict], filter_params: dict) -> None:
    """Replaces the session's epochs and stores the filter and the drop rule they were computed with."""
    sid = str(session_id)
    await db.execute(text("DELETE FROM eeg_epochs WHERE session_id = :s"), {"s": sid})
    if eps:
        await db.execute(text(
            "INSERT INTO eeg_epochs (session_id, epoch_index, lsl_start, start_ms, end_ms, game_state, trial_id, "
            "esl_level, chunk_clean, clean_fraction, quality, engagement_index, theta_fz, alpha_parietal, theta_beta) "
            "VALUES (:s, :epoch_index, :lsl_start, :start_ms, :end_ms, :game_state, :trial_id, :esl_level, :chunk_clean, "
            ":clean_fraction, :quality, :engagement_index, :theta_fz, :alpha_parietal, :theta_beta)"),
            [{"s": sid, **e} for e in eps])
    await db.execute(text("UPDATE eeg_sessions SET filter_params = CAST(:f AS jsonb) WHERE session_id = :s"),
                     {"s": sid, "f": json.dumps({**filter_params, "sound_s": SOUND_S, "epochs_version": EPOCHS_VERSION})})


async def fill_from_xdf(session_id: str) -> list[dict]:
    """After the session, on the PC: filters the XDF of its eeg_sessions row and stores its epochs."""
    from app.db.base import AsyncSessionLocal
    from app.eeg import baseline, lsl_reader, preprocess, reference

    async with AsyncSessionLocal() as db:
        path, montage, offset = (await db.execute(text("SELECT xdf_path, montage, sync_offset_ms FROM eeg_sessions "
                                                       "WHERE session_id = :s"), {"s": session_id})).one()
        streams = lsl_reader.load_xdf(path)
        aura = streams[lsl_reader.EEG_STREAM]
        sr = float(aura["info"]["nominal_srate"][0])
        stamps = np.asarray(aura["time_stamps"], dtype=float) - (offset or 0.0) / 1000  # D-F6-176: no offset, no correction
        markers = markers_of(streams.get(lsl_reader.MARKER_STREAM))
        eps = make_epochs(preprocess.filter_eeg(aura["time_series"], sr), stamps, sr, montage, markers)
        await save(db, session_id, eps, {**preprocess.filter_params(sr), "sync_offset_ms": offset})
        await reference.save(db, session_id, reference.compute(eps, baseline.spans(markers)))
        await db.commit()
    return eps


if __name__ == "__main__":
    # On the PC, after lsl_reader:  POSTGRES_HOST=127.0.0.1 python -m app.eeg.epochs <session_id>
    import asyncio
    import collections
    import sys

    eps = asyncio.run(fill_from_xdf(sys.argv[1]))
    print(f"{len(eps)} epochs:", dict(collections.Counter(e["quality"] for e in eps)))

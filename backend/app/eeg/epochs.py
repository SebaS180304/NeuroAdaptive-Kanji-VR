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
import os
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
BAD_BIN_S, BAD_SHARE, BAD_BINS = 30.0, 0.20, 2  # D-F6-216: > 20 % over MAX_UV in 2 consecutive 30 s bins
TAP_GUARD_S = 1.0     # D-F6-224 (1): ±1 s around each SYNC_TAP is not counted (the taps on Cz's housing)
EPOCHS_VERSION = "rule B (D-F6-149), 9 chunks by time covered (D-F6-163, D-F6-166), S3 offset (D-F6-176), bad channel (D-F6-216, D-F6-224)"  # stored with the filter (D-F6-156); bump when a drop rule changes


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


RULES = ("current", "nosound")  # D-F6-246: option (1) live; (2) only offline (fill_from_xdf, replay --rule) until the go/no-go
TASK_SOUND_STATES = ("S6_GUIDED_PRACTICE_CALIBRATION", "S7_EXPERIMENTAL_RETRIEVAL", "S8_IMMEDIATE_ASSESSMENT")


def sound_onsets(markers: list[tuple[float, dict]]) -> list[tuple[float, str, str | None]]:
    """(LSL time, kind, state) of every sound onset: S5 readings (D-F6-138), select and result of a trial, the stage
    sound before STATE_ENTERED (its state is the one entered). As ocul.py's p7_sonidos.sound_onsets."""
    out, answered = [], {}
    for t, m in markers:
        e = m.get("event")
        if e == "AUDIO_ONSET":
            out.append((t, "S5_READING", m.get("state")))
        elif e == "ANSWER_SELECTED":
            answered[m.get("trial_id")] = t
            out.append((t, "SELECT", m.get("state")))
        elif e == "TRIAL_COMPLETED" and m.get("result_sound_offset_ms") is not None and m.get("trial_id") in answered:
            out.append((answered[m["trial_id"]] + m["result_sound_offset_ms"] / 1000, "RESULT", m.get("state")))  # relative to ANSWER_SELECTED
        elif e == "STATE_ENTERED" and m.get("transition_sound_lead_ms") is not None:
            out.append((t - m["transition_sound_lead_ms"] / 1000, "STAGE", m.get("state")))
    return out


def sound_density(markers: list[tuple[float, dict]]) -> tuple[list[int], float | None]:
    """Every sound onset in session ms, and S6's onsets per second (from its STATE_ENTERED to the next one), for the
    density control of option (2) (D-F6-147 (2)). None without an S6."""
    clock0 = _context(markers)[2]
    onsets = [t for t, _, _ in sound_onsets(markers)]
    entered = [(t, m.get("state")) for t, m in markers if m.get("event") == "STATE_ENTERED"]
    s6 = next(((a, b) for (a, s), (b, _) in zip(entered, entered[1:]) if s == TASK_SOUND_STATES[0]), None)
    d6 = None if s6 is None else sum(s6[0] <= t < s6[1] for t in onsets) / (s6[1] - s6[0])
    return ([] if clock0 is None else sorted(int(round((t - clock0) * 1000)) for t in onsets)), d6


def excluded_intervals(markers: list[tuple[float, dict]], rule: str = "current") -> list[tuple[float, float]]:
    """LSL time spans that no clean chunk may touch, from the markers. rule "nosound" (option (2), D-F6-242 (2)) keeps
    the task sounds (select and result) of S6–S8; the stage sound and S5's readings stay trimmed (D-F6-255 (1))."""
    assert rule in RULES, rule
    out = [(s, s + SOUND_S) for s, kind, state in sound_onsets(markers)
           if rule == "current" or kind not in ("SELECT", "RESULT") or state not in TASK_SOUND_STATES]
    away = {}
    for t, m in markers:
        e = m.get("event")
        if e == "FRAME_HITCH" and m.get("duration_ms", 0) > HITCH_MS:
            out.append((t - m["duration_ms"] / 1000, t))  # pushed when the slow frame ends
        elif e == "HEAD_AWAY":
            away[m.get("episode")] = t + m.get("onset_offset_ms", 0) / 1000
        elif e == "HEAD_RETURNED" and m.get("episode") in away:
            left = away.pop(m["episode"])
            out.append((left, left + m["duration_ms"] / 1000 if m.get("duration_ms") is not None else t))
    out += [(left, math.inf) for left in away.values()]  # never came back inside the recording
    return out


def persistently_bad(x: np.ndarray, ts: np.ndarray, labels: list[str], markers: list[tuple[float, dict]],
                     t0: float | None = None) -> list[tuple[str, float]]:
    """Index channels that went persistently bad (D-F6-216, D-F6-224), in the order they did, with the LSL time
    they leave from: the end of their 2nd consecutive bin over the share. Bins of BAD_BIN_S from t0 (the grid
    origin; None = ts[0]); only closed bins count, so live and offline agree. Fp1 keeps its own rule (D-F6-75).
    The caller applies D-F6-216's maximum: the first is excluded, a second means the session's EEG does not count."""
    ts = np.asarray(ts, dtype=float)
    if not len(ts):
        return []
    t0 = float(ts[0]) if t0 is None else t0
    keep = np.ones(len(ts), bool)
    for t, m in markers:
        if m.get("event") == "SYNC_TAP":
            keep &= np.abs(ts - t) > TAP_GUARD_S
    cols = [i for i, l in enumerate(labels) if l != "Fp1"]
    over = np.abs(x[:, cols]) > MAX_UV
    run, out = np.zeros(len(cols), int), {}
    k, dt = 0, (ts[-1] - ts[0]) / (len(ts) - 1) if len(ts) > 1 else 0.0  # the last sample covers one period too
    while t0 + (k + 1) * BAD_BIN_S <= ts[-1] + dt + 1e-9:
        lo, hi = np.searchsorted(ts, [t0 + k * BAD_BIN_S, t0 + (k + 1) * BAD_BIN_S])
        sel = keep[lo:hi]
        share = over[lo:hi][sel].mean(axis=0) if sel.any() else np.zeros(len(cols))
        run = np.where(share > BAD_SHARE, run + 1, 0)
        for c in np.flatnonzero(run >= BAD_BINS):
            out.setdefault(labels[cols[c]], t0 + (k + 1) * BAD_BIN_S)
        k += 1
    return sorted(out.items(), key=lambda kv: kv[1])


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
                markers: list[tuple[float, dict]], t0: float | None = None,
                bad: list[tuple[str, float]] | None = None, rule: str = "current") -> list[dict]:
    """x: filtered EEG, samples × channels in µV; ts: corrected LSL stamps; montage: CH1… → label.
    t0: origin of the epoch grid (default ts[0]). live.py passes the session's first stamp with only the tail of
    its buffer, so each epoch keeps its place and index on the session's grid.
    bad: persistently_bad() (D-F6-216). An epoch that starts at or after a channel's time leaves it out of the
    amplitude and flat checks and of the indices, and says so in excluded_channels; two out → window.py does not
    count the EEG. None = as before, without the key."""
    ts = np.asarray(ts, dtype=float)
    labels = [montage[f"CH{i + 1}"] for i in range(x.shape[1])]
    blink_ch = [labels.index("Fp1")] if "Fp1" in labels else [i for i, l in enumerate(labels) if l in ("F3", "Fz", "F4")]
    index_ch = [i for i, l in enumerate(labels) if l != "Fp1"]

    bad_t = bad
    bad = (np.abs(x[:, blink_ch]) > BLINK_UV).any(axis=1)
    pad = int(round(BLINK_PAD_S * srate))
    if pad and bad.any():
        bad = np.convolve(bad, np.ones(2 * pad + 1), mode="same") > 0
    over = np.abs(x[:, index_ch]) > MAX_UV  # per channel, so an excluded one can leave the check (D-F6-216)
    for a, b in excluded_intervals(markers, rule):
        bad |= (ts >= a) & (ts < b)

    times, ctx, clock0 = _context(markers)
    to_ms = (lambda t: int(round((t - clock0) * 1000))) if clock0 is not None else (lambda t: None)
    min_n = MIN_SAMPLES * srate * CHUNK_S

    out = []
    if not len(ts):
        return out
    t0 = float(ts[0]) if t0 is None else t0
    first = max(0, math.ceil((ts[0] - t0) / STEP_S - 1e-9))  # the first epoch that starts inside ts
    last = int((ts[-1] + 1 / srate - t0 - EPOCH_S) // STEP_S)  # the last sample covers 1/srate too
    for j in range(first, last + 1):
        start = float(t0 + j * STEP_S)
        out_ch = [label for label, t in (bad_t or [])[:2] if start >= t]
        keep = np.array([labels[c] not in out_ch for c in index_ch])
        cols = [c for c, k in zip(index_ch, keep) if k]
        flags, clean = [], []
        for k in range(CHUNKS):
            chunk = start + k * CHUNK_STEP_S
            lo, hi = np.searchsorted(ts, [chunk, chunk + CHUNK_S])
            seg = x[lo:hi, cols]
            flags.append(bool(hi - lo >= min_n and not bad[lo:hi].any() and not over[lo:hi][:, keep].any()
                              and (np.ptp(seg, axis=0) >= FLAT_UV).all()))
            if flags[-1]:
                clean.append(x[lo:hi])
        i = bisect.bisect_right(times, start + EPOCH_S / 2) - 1  # the context at the epoch's midpoint
        state, esl, trial = ctx[i] if i >= 0 else (None, None, None)
        covered = covered_s(flags)
        grade = quality(covered)
        used = [l if l not in out_ch else None for l in labels]  # features finds no column for an excluded one
        extra = {} if bad_t is None else {"excluded_channels": ",".join(out_ch) or None}
        out.append({"epoch_index": j, "lsl_start": start, "start_ms": to_ms(start), "end_ms": to_ms(start + EPOCH_S),
                    "game_state": state, "esl_level": esl, "trial_id": trial, "chunk_clean": flags,
                    "clean_fraction": covered / EPOCH_S, "quality": grade,
                    **(features.compute(clean, used, srate) if grade != "POOR" else features.EMPTY), **extra})
    return out


def cut_session(x: np.ndarray, ts: np.ndarray, srate: float, montage: dict, markers: list[tuple[float, dict]],
                t0: float | None = None, rule: str = "current") -> tuple[list[dict], list[tuple[str, float]], dict]:
    """The whole session's cut with D-F6-216: (epochs, persistently_bad(), reference). x is the filtered EEG of the
    session. A channel out after S6 began → the reference is recomputed with the remaining channels, from a cut with
    that channel out from the start (D-F6-216); out before S6, the session's own epochs already lack it."""
    from app.eeg import baseline, reference

    labels = [montage[f"CH{i + 1}"] for i in range(x.shape[1])]
    bad = persistently_bad(x, ts, labels, markers, t0)
    eps = make_epochs(x, ts, srate, montage, markers, t0=t0, bad=bad, rule=rule)
    s6 = next((t for t, m in markers if m.get("event") == "STATE_ENTERED" and m.get("state") == reference.S6_STATE), math.inf)
    recut = (make_epochs(x, ts, srate, montage, markers, t0=t0, bad=[(bad[0][0], -math.inf)], rule=rule)
             if bad and bad[0][1] > s6 else eps)
    return eps, bad, reference.compute(recut, baseline.spans(markers))


def bad_summary(bad: list[tuple[str, float]], markers: list[tuple[float, dict]]) -> dict:
    """eeg_sessions.bad_channel ("F3", or "F3,Pz" when a 2nd went out and the EEG stopped counting) and the session
    time the first left from (D-F6-216)."""
    if not bad:
        return {"bad_channel": None, "bad_channel_from_ms": None}
    clock0 = _context(markers)[2]
    return {"bad_channel": ",".join(label for label, _ in bad[:2]),
            "bad_channel_from_ms": None if clock0 is None else int(round((bad[0][1] - clock0) * 1000))}


async def save_bad(db: AsyncSession, session_id: uuid.UUID | str, summary: dict) -> None:
    await db.execute(text("UPDATE eeg_sessions SET bad_channel = :c, bad_channel_from_ms = :m WHERE session_id = :s"),
                     {"s": str(session_id), "c": summary["bad_channel"], "m": summary["bad_channel_from_ms"]})


async def save(db: AsyncSession, session_id: uuid.UUID | str, eps: list[dict], filter_params: dict) -> None:
    """Replaces the session's epochs and stores the filter and the drop rule they were computed with."""
    sid = str(session_id)
    await db.execute(text("DELETE FROM eeg_epochs WHERE session_id = :s"), {"s": sid})
    if eps:
        await db.execute(text(
            "INSERT INTO eeg_epochs (session_id, epoch_index, lsl_start, start_ms, end_ms, game_state, trial_id, "
            "esl_level, chunk_clean, clean_fraction, quality, engagement_index, theta_fz, alpha_parietal, theta_beta, "
            "excluded_channels) "
            "VALUES (:s, :epoch_index, :lsl_start, :start_ms, :end_ms, :game_state, :trial_id, :esl_level, :chunk_clean, "
            ":clean_fraction, :quality, :engagement_index, :theta_fz, :alpha_parietal, :theta_beta, :excluded_channels)"),
            [{"s": sid, "excluded_channels": None, **e} for e in eps])
    await db.execute(text("UPDATE eeg_sessions SET filter_params = CAST(:f AS jsonb) WHERE session_id = :s"),
                     {"s": sid, "f": json.dumps({**filter_params, "sound_s": SOUND_S, "epochs_version": EPOCHS_VERSION})})


async def fill_from_xdf(session_id: str) -> list[dict]:
    """After the session, on the PC: filters the XDF of its eeg_sessions row and stores its epochs."""
    from app.db.base import AsyncSessionLocal
    from app.eeg import lsl_reader, preprocess, reference

    async with AsyncSessionLocal() as db:
        path, montage, offset, origin = (await db.execute(text(
            "SELECT xdf_path, montage, sync_offset_ms, grid_origin_lsl FROM eeg_sessions WHERE session_id = :s"),
            {"s": session_id})).one()
        streams = lsl_reader.load_xdf(path)
        aura = streams[lsl_reader.EEG_STREAM]
        sr = float(aura["info"]["nominal_srate"][0])
        stamps = np.asarray(aura["time_stamps"], dtype=float) - (offset or 0.0) / 1000  # D-F6-176: no offset, no correction
        markers = markers_of(streams.get(lsl_reader.MARKER_STREAM))
        # the live grid when live.py stored it (D-F6-200 (1)); null = older sessions, the XDF's first stamp as before
        # EEG_RULE: option (2) only by hand, for D-F6-246's validation; live is always "current" until the go/no-go
        rule = os.environ.get("EEG_RULE", "current")
        eps, bad, ref = cut_session(preprocess.filter_eeg(aura["time_series"], sr), stamps, sr, montage, markers,
                                    t0=origin, rule=rule)
        await save(db, session_id, eps, {**preprocess.filter_params(sr), "sync_offset_ms": offset, "rule": rule})
        await reference.save(db, session_id, ref)
        await save_bad(db, session_id, bad_summary(bad, markers))
        await db.commit()
    return eps


if __name__ == "__main__":
    # On the PC, after lsl_reader:  POSTGRES_HOST=127.0.0.1 python -m app.eeg.epochs <session_id>
    import asyncio
    import collections
    import sys

    eps = asyncio.run(fill_from_xdf(sys.argv[1]))
    print(f"{len(eps)} epochs:", dict(collections.Counter(e["quality"] for e in eps)))

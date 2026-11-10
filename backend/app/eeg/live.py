"""
The live EEG path on the PC (D-F6-171; Planteamiento_Tecnico_F4.md §2.2). Started by autorun next to baseline.py, it
buffers this PC's AURA and UnityMarkers, writes every finished epoch with its indices to eeg_epochs, the reference on
entering S7, and a heartbeat; the backend reads them at each S7 answer of MULTIMODAL_ADAPTIVE (window.py, decide()).
After the session fill_from_xdf replaces these rows (D-F6-156); what the engine saw stays in each decision's payload.

The cut is the offline one (epochs.make_epochs) on the tail of the buffer:
  - nothing is cut until S3 has ended (the first STATE_ENTERED of S4): then sync.compute gives the S3 offset, which
    is subtracted from the EEG stamps from there on (D-F6-173); under 3 clear taps there is no correction (D-F6-176);
  - the grid starts at the first corrected stamp, so each epoch keeps its index on the session's grid;
  - the zero-phase filter runs over the epoch plus PAD_S before it, and an epoch is cut only EDGE_S after its end,
    so the filter has signal on both sides. That wait is part of the arrival margin measured on Wed 11.
"""

import numpy as np

from app.eeg import epochs, preprocess, sync

S4_STATE = "S4_EEG_BASELINE"
PAD_S = 10.0   # filter warm-up before the first pending epoch
EDGE_S = 1.0   # signal needed after an epoch's end before cutting it (the filter is zero-phase)


class Buffer:
    """Samples and markers as they arrive; new_epochs() gives each finished epoch once."""

    def __init__(self, srate: float, montage: dict):
        self.srate, self.montage = srate, montage
        self.x: list[list[float]] = []
        self.ts: list[float] = []
        self.markers: list[tuple[float, dict]] = []
        self.synced = False
        self.offset_ms: float | None = None
        self.sync_result = None
        self.t0: float | None = None
        self.next_index = 0

    def add(self, samples, stamps, markers=()) -> None:
        self.x += samples
        self.ts += stamps
        self.markers += markers

    def sync_if_ready(self) -> bool:
        """Once S3 has ended: the offset of its taps, as sync.py computes it after the session."""
        if self.synced:
            return True
        if not any(m.get("event") == "STATE_ENTERED" and m.get("state") == S4_STATE for _, m in self.markers):
            return False
        cz = int(next(k for k, v in self.montage.items() if v == "Cz")[2:]) - 1
        self.sync_result = sync.compute(np.asarray(self.x, dtype=float)[:, cz], np.asarray(self.ts), self.markers)
        self.offset_ms = self.sync_result[0]
        self.synced = True
        return True

    def new_epochs(self) -> list[dict]:
        if not self.synced or not self.ts:
            return []
        ts = np.asarray(self.ts, dtype=float) - (self.offset_ms or 0.0) / 1000
        if self.t0 is None:
            self.t0 = float(ts[0])
        start = self.t0 + self.next_index * epochs.STEP_S
        ready_until = ts[-1] - EDGE_S
        if start + epochs.EPOCH_S > ready_until:
            return []
        lo = int(np.searchsorted(ts, start - PAD_S))
        x = preprocess.filter_eeg(np.asarray(self.x[lo:], dtype=float), self.srate)
        cut = epochs.make_epochs(x, ts[lo:], self.srate, self.montage, self.markers, t0=self.t0)
        new = [e for e in cut if e["epoch_index"] >= self.next_index
               and e["lsl_start"] + epochs.EPOCH_S <= ready_until + 1e-9]
        if new:
            self.next_index = new[-1]["epoch_index"] + 1
        return new


# -- database (written by the PC; read by the backend at each S7 answer) ---------------------------------------------

_COLUMNS = ("epoch_index", "lsl_start", "start_ms", "end_ms", "game_state", "trial_id", "esl_level", "chunk_clean",
            "clean_fraction", "quality", "engagement_index", "theta_fz", "alpha_parietal", "theta_beta")


async def save_epochs(db, session_id: str, eps: list[dict]) -> None:
    """Each epoch once: a row cut again (it never should be) replaces the old one."""
    from sqlalchemy import text

    cols = ", ".join(_COLUMNS)
    await db.execute(text(
        f"INSERT INTO eeg_epochs (session_id, {cols}) VALUES (:s, {', '.join(':' + c for c in _COLUMNS)}) "
        f"ON CONFLICT (session_id, epoch_index) DO UPDATE SET "
        + ", ".join(f"{c} = EXCLUDED.{c}" for c in _COLUMNS if c != "epoch_index")),
        [{"s": str(session_id), **{c: e[c] for c in _COLUMNS}} for e in eps])


async def heartbeat(db, session_id: str, gap_ms: int | None) -> None:
    from sqlalchemy import text

    await db.execute(text("UPDATE eeg_sessions SET heartbeat_at = now(), eeg_gap_ms = :g WHERE session_id = :s"),
                     {"s": str(session_id), "g": gap_ms})


# -- the loop on the PC ----------------------------------------------------------------------------------------------

S7_STATE = "S7_EXPERIMENTAL_RETRIEVAL"
END_STATE = "S9_SESSION_SUMMARY"   # S7 and S8 are over: nothing left to decide
HEARTBEAT_S = 2.0


async def run(session_id: str) -> list[float]:
    """Until S9: epochs, offset, reference and heartbeat to the database. Returns each epoch's arrival lag (s)."""
    import json
    import time

    import pylsl
    from sqlalchemy import text

    from app.db.base import AsyncSessionLocal
    from app.eeg import baseline, lsl_reader, reference

    eeg_in = lsl_reader.open_local_inlet(lsl_reader.EEG_STREAM)
    mk_in = lsl_reader.open_local_inlet(lsl_reader.MARKER_STREAM)
    srate = eeg_in.info().nominal_srate()
    async with AsyncSessionLocal() as db:
        montage = (await db.execute(text("SELECT montage FROM eeg_sessions WHERE session_id = :s"),
                                    {"s": session_id})).scalar_one_or_none() or baseline.DEFAULT_MONTAGE
    buf, cut, lags, ref_done, last_beat = Buffer(srate, montage), [], [], False, 0.0
    print(f"live: {lsl_reader.EEG_STREAM} at {srate} Hz and {lsl_reader.MARKER_STREAM}; cutting from the end of S3")
    while True:
        samples, stamps = eeg_in.pull_chunk(timeout=0.2)
        values, mstamps = mk_in.pull_chunk(timeout=0.0)
        new_markers = [(t, json.loads(v[0])) for v, t in zip(values, mstamps)]
        buf.add(samples, stamps, new_markers)
        just_synced = not buf.synced and buf.sync_if_ready()
        eps = buf.new_epochs()
        entered = {m.get("state") for _, m in buf.markers if m.get("event") == "STATE_ENTERED"}
        now = pylsl.local_clock()
        write_ref = not ref_done and S7_STATE in entered
        beat = time.monotonic() - last_beat >= HEARTBEAT_S
        if just_synced or eps or write_ref or beat:
            async with AsyncSessionLocal() as db:
                if just_synced:
                    from app.eeg import sync
                    await sync.save(db, session_id, *buf.sync_result)
                    print(f"live: S3 offset {buf.offset_ms} ms" + ("" if buf.offset_ms is not None else " (no correction)"))
                if eps:
                    await save_epochs(db, session_id, eps)
                    cut += eps
                if write_ref:
                    ref = reference.compute(cut, baseline.spans(buf.markers))
                    await reference.save(db, session_id, ref)
                    ref_done = True
                    print(f"live: reference from {ref.get('source')} ({ref.get('n_epochs')} epochs)")
                if beat:
                    gap = None if not buf.ts else int(round((now - buf.ts[-1]) * 1000))
                    await heartbeat(db, session_id, gap)
                    last_beat = time.monotonic()
                await db.commit()
            if eps:  # arrival lag: from the epoch's end (on the inlet's clock) to its row committed
                done = pylsl.local_clock()
                lags += [done - (e["lsl_start"] + epochs.EPOCH_S + (buf.offset_ms or 0.0) / 1000) for e in eps]
        if END_STATE in entered:
            break
    if lags:
        print(f"live: {len(lags)} epochs; arrival after their end: median {np.median(lags):.2f} s, "
              f"max {max(lags):.2f} s")
    return lags


if __name__ == "__main__":
    # On the PC, started by autorun:  POSTGRES_HOST=127.0.0.1 python -m app.eeg.live <session_id>
    import asyncio
    import sys

    asyncio.run(run(sys.argv[1]))

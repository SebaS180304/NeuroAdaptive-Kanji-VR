"""
The live EEG path on the PC (D-F6-171; Planteamiento_Tecnico_F4.md §2.2). Started by autorun next to baseline.py, it
buffers this PC's AURA and UnityMarkers, writes every finished epoch with its indices to eeg_epochs, the reference on
entering S7, and a heartbeat; the backend reads them at each S7 answer of MULTIMODAL_ADAPTIVE (window.py, decide()).
After the session fill_from_xdf replaces these rows (D-F6-156); what the engine saw stays in each decision's payload.

The cut is the offline one (epochs.make_epochs) on the tail of the buffer:
  - nothing is cut until S3 has ended (the first STATE_ENTERED of S4): then sync.compute gives the S3 offset, which
    is subtracted from the EEG stamps from there on (D-F6-173); under 3 clear taps there is no correction (D-F6-176);
  - the grid starts at the first corrected stamp, so each epoch keeps its index on the session's grid; that origin is
    stored once (eeg_sessions.grid_origin_lsl) and fill_from_xdf and replay --xdf cut on it (D-F6-200 (1));
  - the zero-phase filter runs over the epoch plus PAD_S before it, and an epoch is cut only EDGE_S after its end,
    so the filter has signal on both sides. That wait is part of the arrival margin measured on Wed 11;
  - the persistently bad channel (D-F6-216, D-F6-224): each 30 s bin of the grid is filtered once it closes (PAD_S
    before, EDGE_S after) and epochs.persistently_bad runs over the closed bins, so an epoch that starts after a
    channel's time is cut without it, as fill_from_xdf cuts it;
  - rule "ica", option (3) live (D-F6-275, D-F6-276): before S6 the epochs are cut as option (2); once the buffer has
    EDGE_S past S6's entry the ICA is fitted on S4 -> S6 (filtered over [S4 - PAD_S, S6 + EDGE_S], a fixed span, so the
    fit does not depend on how the samples arrived) and every epoch centred in S6 or later is cut on the corrected
    signal without the blink rule; those epochs wait for the model. Not identified, a failed fit, or Fp1 out before
    S6 -> option (2) for the session; a channel out before S6 is left out of the fit; one out after S6 -> option (2)
    from its time to the end, no refit (D-F6-253 (2), D-F6-276 (2)).
"""

import time

import numpy as np

from app.eeg import epochs, preprocess, s3watch, sync

S4_STATE = "S4_EEG_BASELINE"
S6_STATE = "S6_GUIDED_PRACTICE_CALIBRATION"
PAD_S = 10.0   # filter warm-up before the first pending epoch
EDGE_S = 1.0   # signal needed after an epoch's end before cutting it (the filter is zero-phase)


class Buffer:
    """Samples and markers as they arrive; new_epochs() gives each finished epoch once."""

    def __init__(self, srate: float, montage: dict, ica_model: dict | None = None):
        self.srate, self.montage = srate, montage
        self.x: list[list[float]] = []
        self.ts: list[float] = []
        self.markers: list[tuple[float, dict]] = []
        self.synced = False
        self.offset_ms: float | None = None
        self.sync_result = None
        self.t0: float | None = None
        self.next_index = 0
        self.rule = "current"  # D-F6-246: live.run never changes it; replay --rule sets it for the validation
        self.labels = [montage[f"CH{i + 1}"] for i in range(len(montage))]
        self.bins_x: list[np.ndarray] = []
        self.bins_ts: list[np.ndarray] = []
        self.bad: list[tuple[str, float]] = []
        # rule "ica": the S6 fit, or why there is none; a stored one (fill_from_xdf, D-F6-276 (1)) is used, never refitted
        self.ica: dict | None = None
        self._stored_ica = ica_model

    @property
    def effective_rule(self) -> str:
        """The rule the session's S6-S9 run with: "ica" only while the ICA holds (D-F6-276 (2))."""
        if self.rule != "ica":
            return self.rule
        holds = self.ica is not None and self.ica.get("identified") and "switched_to_nosound_at" not in self.ica
        return "ica" if holds else "nosound"

    def _s6(self) -> float | None:
        return next((t for t, m in self.markers if m.get("event") == "STATE_ENTERED" and m.get("state") == S6_STATE), None)

    def _fit_ica(self, ts: np.ndarray, s6: float) -> dict:
        from app.eeg import ica

        out = [c for c, t in self.bad if t <= s6]
        if "Fp1" in out:
            return {"identified": False, "reason": "Fp1 out before S6"}
        keep = [i for i, label in enumerate(self.labels) if label not in out]
        s4 = next((t for t, m in self.markers if m.get("event") == "STATE_ENTERED" and m.get("state") == S4_STATE), ts[0])
        lo, hi = np.searchsorted(ts, [s4 - PAD_S, s6 + EDGE_S])
        try:  # live.py never stops for the ICA: any failure is option (2), with its reason (D-F6-253 (2))
            began = time.perf_counter()
            y = preprocess.filter_eeg(np.asarray(self.x[lo:hi], dtype=float)[:, keep], self.srate)
            model = ica.fit(y, ts[lo:hi], [self.labels[i] for i in keep], self.markers)
            model["fit_s"] = round(time.perf_counter() - began, 3)
        except Exception as e:  # noqa: BLE001
            return {"identified": False, "reason": f"fit failed: {type(e).__name__}: {e}"}
        return {**model, "channels": [self.labels[i] for i in keep]}

    def _corrected(self, x: np.ndarray) -> np.ndarray:
        from app.eeg import ica

        keep = [self.labels.index(c) for c in self.ica["channels"]]
        y = x.copy()
        y[:, keep] = ica.apply(x[:, keep], self.ica)
        return y

    def _ica_step(self, ts: np.ndarray) -> float | None:
        """Fits once S6's entry + EDGE_S has arrived, and switches to option (2) at a channel out after S6.
        Returns S6's entry (None before it)."""
        s6 = self._s6()
        if s6 is None:
            return None
        if self.ica is None and ts[-1] >= s6 + EDGE_S:
            self.ica = dict(self._stored_ica) if self._stored_ica is not None else self._fit_ica(ts, s6)
        if self.ica and self.ica.get("identified") and "switched_to_nosound_at" not in self.ica:
            after = [(c, t) for c, t in self.bad if t > s6]
            if after:
                self.ica["switched_to_nosound_at"], self.ica["switch_reason"] = after[0][1], f"{after[0][0]} out after S6"
        return s6

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

    def _close_bins(self, ts: np.ndarray) -> None:
        """Filters every bin that has closed (with EDGE_S after it) and re-runs the detector on them."""
        closed = False
        while self.t0 + (len(self.bins_x) + 1) * epochs.BAD_BIN_S + EDGE_S <= ts[-1]:
            a = self.t0 + len(self.bins_x) * epochs.BAD_BIN_S
            lo, hi = np.searchsorted(ts, [a - PAD_S, a + epochs.BAD_BIN_S + EDGE_S])
            y = preprocess.filter_eeg(np.asarray(self.x[lo:hi], dtype=float), self.srate)
            inside = (ts[lo:hi] >= a) & (ts[lo:hi] < a + epochs.BAD_BIN_S)
            self.bins_x.append(y[inside])
            self.bins_ts.append(ts[lo:hi][inside])
            closed = True
        if closed:
            self.bad = epochs.persistently_bad(np.concatenate(self.bins_x), np.concatenate(self.bins_ts), self.labels,
                                               self.markers, self.t0)

    def reference(self, cut: list[dict]) -> dict:
        """The session's reference from the epochs cut so far, as epochs.cut_session: a channel out after S6 began →
        recomputed from the whole buffer cut without it (D-F6-216)."""
        from app.eeg import baseline, reference

        s6 = next((t for t, m in self.markers if m.get("event") == "STATE_ENTERED" and m.get("state") == reference.S6_STATE),
                  np.inf)
        if self.bad and self.bad[0][1] > s6:
            ts = np.asarray(self.ts, dtype=float) - (self.offset_ms or 0.0) / 1000
            x = preprocess.filter_eeg(np.asarray(self.x, dtype=float), self.srate)
            cut = epochs.make_epochs(x, ts, self.srate, self.montage, self.markers, t0=self.t0,
                                     bad=[(self.bad[0][0], -np.inf)], rule=self.effective_rule)
        elif self.effective_rule == "ica":  # D-F6-276 (1): the reference and S4's fallback carry the matrix
            ts = np.asarray(self.ts, dtype=float) - (self.offset_ms or 0.0) / 1000
            x = preprocess.filter_eeg(self._corrected(np.asarray(self.x, dtype=float)), self.srate)
            cut = epochs.make_epochs(x, ts, self.srate, self.montage, self.markers, t0=self.t0, bad=self.bad, rule="ica")
        return reference.compute(cut, baseline.spans(self.markers))

    def cut_past(self, t: float) -> bool:
        """Every epoch centred before t (a marker's time, as make_epochs assigns states) has been cut."""
        return self.t0 is not None and self.t0 + self.next_index * epochs.STEP_S + epochs.EPOCH_S / 2 >= t

    def new_epochs(self) -> list[dict]:
        if not self.synced or not self.ts:
            return []
        ts = np.asarray(self.ts, dtype=float) - (self.offset_ms or 0.0) / 1000
        if self.t0 is None:
            self.t0 = float(ts[0])
        self._close_bins(ts)
        start = self.t0 + self.next_index * epochs.STEP_S
        ready_until = ts[-1] - EDGE_S
        if start + epochs.EPOCH_S > ready_until:
            return []
        lo = int(np.searchsorted(ts, start - PAD_S))
        raw = np.asarray(self.x[lo:], dtype=float)
        rule = "nosound" if self.rule == "ica" else self.rule  # rule "ica": option (2) until the S6 fit
        cut = epochs.make_epochs(preprocess.filter_eeg(raw, self.srate), ts[lo:], self.srate, self.montage, self.markers,
                                 t0=self.t0, bad=self.bad, rule=rule)
        s6 = self._ica_step(ts) if self.rule == "ica" else None

        def late(e: dict) -> bool:
            return s6 is not None and e["lsl_start"] + epochs.EPOCH_S / 2 >= s6

        if self.ica and self.ica.get("identified"):
            fixed = {e["epoch_index"]: e for e in epochs.make_epochs(
                preprocess.filter_eeg(self._corrected(raw), self.srate), ts[lo:], self.srate, self.montage, self.markers,
                t0=self.t0, bad=self.bad, rule="ica")}
            until = self.ica.get("switched_to_nosound_at", np.inf)
            cut = [fixed[e["epoch_index"]] if late(e) and e["lsl_start"] < until else e for e in cut]
        new = []
        for e in cut:
            if e["epoch_index"] < self.next_index:
                continue
            if e["lsl_start"] + epochs.EPOCH_S > ready_until + 1e-9 or (late(e) and self.ica is None):
                break  # in order: an epoch centred in S6 waits for the model, and so do the ones after it
            new.append(e)
        if new:
            self.next_index = new[-1]["epoch_index"] + 1
        return new


def cut_recording(x: np.ndarray, ts: np.ndarray, srate: float, montage: dict, markers: list[tuple[float, dict]],
                  grid_origin: float | None = None, rule: str = "current", ica_model: dict | None = None,
                  chunk_s: float = 0.5) -> tuple[list[dict], "Buffer"]:
    """A whole recording through Buffer, fed in chunk_s pieces with the markers up to each piece, as live.run feeds it:
    the epochs and the buffer (offset, channel out, ICA, reference). replay --xdf and fill_from_xdf with rule "ica"
    (D-F6-276 (1)). grid_origin: eeg_sessions.grid_origin_lsl; a stored ica_model is used, never refitted."""
    buf = Buffer(srate, montage, ica_model=ica_model)
    buf.rule, buf.t0 = rule, grid_origin
    step, mk, cut = max(1, int(srate * chunk_s)), 0, []
    for i in range(0, len(ts), step):
        hi = ts[min(i + step, len(ts)) - 1]
        j = mk
        while j < len(markers) and markers[j][0] <= hi:
            j += 1
        buf.add(x[i:i + step].tolist(), ts[i:i + step].tolist(), markers[mk:j])
        mk = j
        buf.sync_if_ready()
        cut += buf.new_epochs()
    return cut, buf


# -- the live monitor's per-channel figures (M1b, D-F6-254, D-F6-265): a read of the buffer, never the epoch cut ------

MONITOR_EVERY_S = 2.5
MONITOR_TAIL_S = 17.0  # monitor.compute filters [now - 17 s, now]


def monitor_snapshot(buf: "Buffer", previous: dict | None) -> dict:
    """monitor.compute on the tail of the buffer, on the markers' clock (the S3 offset once known)."""
    from app.eeg import monitor

    n = int(MONITOR_TAIL_S * buf.srate) + 1
    ts = np.asarray(buf.ts[-n:], dtype=float) - (buf.offset_ms or 0.0) / 1000
    last_bin = None
    if buf.bins_x:  # % over 100 µV of the last closed 30 s bin, for the Watch of D-F6-231 (3)
        last_bin = {label: float(100 * np.mean(np.abs(buf.bins_x[-1][:, i]) > epochs.MAX_UV))
                    for i, label in enumerate(buf.labels)}
    return monitor.compute(np.asarray(buf.x[-n:], dtype=float), ts, buf.srate, buf.labels, buf.markers,
                           now=float(ts[-1]), previous=previous, last_bin_over=last_bin)


TRACES_EVERY_S = 0.25
TRACES_KEEP_S = 30.0  # eeg_trace_bins keeps only this much per session: the panel shows 20 s (D-F6-297 (3))


def trace_rows(bins: list[dict], markers: list[tuple[float, dict]], offset_ms: float | None) -> list[dict] | None:
    """TR's bins in session ms on the markers' clock (S3 offset applied, so taps and stage lines fall in place).
    None while no marker gives the session clock yet: the caller keeps the bins until it does."""
    zero = epochs._context(markers)[2]
    if zero is None:
        return None
    shift = (offset_ms or 0.0) / 1000
    return [{"t_ms": int(round((b["t"] - shift - zero) * 1000)), "mins": b["min"], "maxs": b["max"]} for b in bins]


def tap_ms(markers: list[tuple[float, dict]]) -> list[int]:
    """The S3 SYNC_TAP markers in session ms: they travel only by LSL, so live.py hands them to the traces panel."""
    zero = epochs._context(markers)[2]
    return [] if zero is None else [int(round((t - zero) * 1000)) for t, m in markers if m.get("event") == "SYNC_TAP"]


async def save_traces(db, session_id: str, rows: list[dict], rms: list[float | None], taps: list[int] = ()) -> None:
    import json

    from sqlalchemy import text

    if rows:
        await db.execute(text("INSERT INTO eeg_trace_bins (session_id, t_ms, mins, maxs) VALUES (:s, :t, :mins, :maxs) "
                              "ON CONFLICT DO NOTHING"),
                         [{"s": str(session_id), "t": r["t_ms"], "mins": r["mins"], "maxs": r["maxs"]} for r in rows])
        await db.execute(text("DELETE FROM eeg_trace_bins WHERE session_id = :s AND t_ms < :keep"),
                         {"s": str(session_id), "keep": rows[-1]["t_ms"] - int(TRACES_KEEP_S * 1000)})
    now = {"rms_uv": [None if r is None else round(r, 1) for r in rms], "t_ms": rows[-1]["t_ms"] if rows else None,
           "taps": list(taps)}
    await db.execute(text("UPDATE eeg_sessions SET traces_now = CAST(:n AS jsonb), traces_at = now() WHERE session_id = :s"),
                     {"s": str(session_id), "n": json.dumps(now)})


async def save_monitor(db, session_id: str, snapshot: dict) -> None:
    import json

    from sqlalchemy import text

    await db.execute(text("UPDATE eeg_sessions SET monitor = CAST(:m AS jsonb), monitor_at = now() WHERE session_id = :s"),
                     {"s": str(session_id), "m": json.dumps(snapshot)})


# -- database (written by the PC; read by the backend at each S7 answer) ---------------------------------------------

_COLUMNS = ("epoch_index", "lsl_start", "start_ms", "end_ms", "game_state", "trial_id", "esl_level", "chunk_clean",
            "clean_fraction", "quality", "engagement_index", "theta_fz", "alpha_parietal", "theta_beta", "excluded_channels")


async def save_epochs(db, session_id: str, eps: list[dict]) -> None:
    """Each epoch once: a row cut again (it never should be) replaces the old one."""
    from sqlalchemy import text

    cols = ", ".join(_COLUMNS)
    await db.execute(text(
        f"INSERT INTO eeg_epochs (session_id, {cols}) VALUES (:s, {', '.join(':' + c for c in _COLUMNS)}) "
        f"ON CONFLICT (session_id, epoch_index) DO UPDATE SET "
        + ", ".join(f"{c} = EXCLUDED.{c}" for c in _COLUMNS if c != "epoch_index")),
        [{"s": str(session_id), **{c: e.get(c) for c in _COLUMNS}} for e in eps])


async def save_origin(db, session_id: str, t0: float) -> None:
    """The grid origin, once: offline cuts on it so its epochs keep the live index and start (D-F6-200 (1))."""
    from sqlalchemy import text

    await db.execute(text("UPDATE eeg_sessions SET grid_origin_lsl = :t WHERE session_id = :s AND grid_origin_lsl IS NULL"),
                     {"s": str(session_id), "t": t0})


async def save_ica(db, session_id: str, model: dict) -> None:
    """Rule "ica": the S6 fit or why there is none, and a later switch to option (2) (D-F6-276)."""
    import json

    from sqlalchemy import text

    await db.execute(text("UPDATE eeg_sessions SET ica = CAST(:m AS jsonb) WHERE session_id = :s"),
                     {"s": str(session_id), "m": json.dumps(model)})


def ica_line(model: dict) -> str:
    """autorun's console line for the operator (D-F6-275 (1), D-F6-276 (2))."""
    if model.get("switched_to_nosound_at") is not None:
        return f"ICA dropped: {model['switch_reason']}; option (2) to the end of the session (D-F6-276 (2))"
    if model.get("identified"):
        return (f"ICA identified (corr {model['corr']:.2f}, component {model['component']}, "
                f"{len(model['channels'])} channels, {model.get('fit_s', 0):.1f} s)")
    return f"ICA not identified ({model.get('reason')}): option (2) for this session (D-F6-253 (2))"


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
    from app.config import get_settings

    buf, cut, lags, ref_done, last_beat, origin_done = Buffer(srate, montage), [], [], False, 0.0, False
    buf.rule = get_settings().eeg_live_rule  # D-F6-263: "current" until switched on in backend/.env
    monitor_on, last_monitor, monitor_prev = get_settings().eeg_monitor_live, 0.0, None  # M1b, off unless switched on
    from app.eeg import traces
    tr = traces.Traces(srate, len(buf.labels)) if get_settings().eeg_monitor_traces else None  # TR, off unless on
    last_traces = 0.0
    bad_saved: list = []
    ica_saved: dict | None = None
    watch = s3watch.S3Watch(montage)
    print(f"live: {lsl_reader.EEG_STREAM} at {srate} Hz and {lsl_reader.MARKER_STREAM}; cutting from the end of S3; "
          f"EEG rule {buf.rule}")
    while True:
        samples, stamps = eeg_in.pull_chunk(timeout=0.2)
        values, mstamps = mk_in.pull_chunk(timeout=0.0)
        new_markers = [(t, json.loads(v[0])) for v, t in zip(values, mstamps)]
        buf.add(samples, stamps, new_markers)
        if tr is not None and samples:  # its own filter state; Buffer and its epochs are untouched (C1)
            tr.feed(samples, stamps)
        for line in watch.lines(buf.x, buf.ts, buf.markers, srate):  # S2–S3 warnings for the operator (AU3)
            print(f"live: {line}")
        just_synced = not buf.synced and buf.sync_if_ready()
        eps = buf.new_epochs()
        entered = {m.get("state"): t for t, m in buf.markers if m.get("event") == "STATE_ENTERED"}
        now = pylsl.local_clock()
        # the reference waits for the last S6 epochs (cut EDGE_S after their end), as fill_from_xdf has them all
        write_ref = not ref_done and S7_STATE in entered and buf.cut_past(entered[S7_STATE])
        beat = time.monotonic() - last_beat >= HEARTBEAT_S
        write_origin = not origin_done and buf.t0 is not None
        write_bad = buf.bad != bad_saved
        write_monitor = monitor_on and len(buf.ts) > 0 and time.monotonic() - last_monitor >= MONITOR_EVERY_S
        write_ica = buf.ica is not None and buf.ica != ica_saved  # the S6 fit, then a switch to (2) if any
        trace_out = None
        if tr is not None and time.monotonic() - last_traces >= TRACES_EVERY_S:
            trace_out = trace_rows(tr.bins, buf.markers, buf.offset_ms)  # None: no session clock yet, bins wait
            if trace_out is not None:
                tr.take_bins()
            last_traces = time.monotonic()
        if write_bad and ref_done:  # out after the reference was written: recomputed without it (D-F6-216)
            write_ref = True
        if just_synced or eps or write_ref or beat or write_origin or write_bad or write_monitor or write_ica or trace_out is not None:
            async with AsyncSessionLocal() as db:
                if just_synced:
                    from app.eeg import sync
                    await sync.save(db, session_id, *buf.sync_result)
                    print(f"live: S3 offset {buf.offset_ms} ms" + ("" if buf.offset_ms is not None else " (no correction)"))
                if write_origin:
                    await save_origin(db, session_id, buf.t0)
                    origin_done = True
                if eps:
                    await save_epochs(db, session_id, eps)
                    cut += eps
                if write_bad:
                    await epochs.save_bad(db, session_id, epochs.bad_summary(buf.bad, buf.markers))
                    bad_saved = list(buf.bad)
                    print(f"live: persistently bad channel {', '.join(c for c, _ in buf.bad)} (D-F6-216)")
                if write_ica:
                    await save_ica(db, session_id, buf.ica)
                    ica_saved = dict(buf.ica)
                    print(f"live: {ica_line(buf.ica)}")
                if write_ref:
                    ref = buf.reference(cut)
                    await reference.save(db, session_id, ref)
                    ref_done = True
                    print(f"live: reference from {ref.get('source')} ({ref.get('n_epochs')} epochs)")
                if write_monitor:  # a separate read of the buffer: the epoch cut above is untouched (D-F6-254)
                    monitor_prev = monitor_snapshot(buf, monitor_prev)
                    await save_monitor(db, session_id, monitor_prev)
                    last_monitor = time.monotonic()
                if trace_out is not None:  # display only, outside new_epochs(), like M1b
                    await save_traces(db, session_id, trace_out, tr.now_rms(), tap_ms(buf.markers))
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

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

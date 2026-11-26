"""
The monitor's 8-channel traces (TR1; D-F6-293 (5), D-F6-297 (2), D-F6-301 (5)). Display only: it reads the samples
live.py already receives (no second LSL inlet) and nothing of the analysis or the engine reads what it gives.

  - a causal filter with its state kept between pieces (sosfilt with zi): high-pass 1 Hz (Butterworth 2), notch 60 Hz
    always on (Q 30), low-pass 40 Hz (Butterworth 4). Its state starts at the first sample, so AURA's DC offset makes
    no transient;
  - min and max per 40 ms bin (10 samples at 250 Hz), never an average, so a one-sample tap survives;
  - "Now": each channel's µV RMS of the last second of the filtered trace (D-F6-297 (2)); None with no data.
"""

from collections import deque

import numpy as np
from scipy.signal import butter, iirnotch, sosfilt, sosfilt_zi, tf2sos

BIN_S = 0.04
NOW_S = 1.0
HP_HZ, LP_HZ, NOTCH_HZ, NOTCH_Q = 1.0, 40.0, 60.0, 30.0


def sos(srate: float) -> np.ndarray:
    hp = butter(2, HP_HZ, btype="highpass", fs=srate, output="sos")
    notch = tf2sos(*iirnotch(NOTCH_HZ, NOTCH_Q, fs=srate))
    lp = butter(4, LP_HZ, btype="lowpass", fs=srate, output="sos")
    return np.vstack([hp, notch, lp])


class Traces:
    """feed() pieces of raw samples (samples x channels, µV) with their stamps and get them filtered; take_bins() gives each closed bin once."""

    def __init__(self, srate: float, n_channels: int):
        self.srate, self.n = srate, n_channels
        self.sos = sos(srate)
        self.zi: np.ndarray | None = None
        self.per_bin = max(1, int(round(BIN_S * srate)))
        self.pending_x: list[np.ndarray] = []  # filtered samples of the bin being filled
        self.pending_t: float | None = None
        self.bins: list[dict] = []
        self.tail: deque = deque(maxlen=int(round(NOW_S * srate)))  # the last second, filtered

    def feed(self, samples, stamps) -> np.ndarray:
        x = np.asarray(samples, dtype=float).reshape(-1, self.n)
        if not len(x):
            return x
        if self.zi is None:
            self.zi = sosfilt_zi(self.sos)[:, :, None] * x[0][None, None, :]
        y, self.zi = sosfilt(self.sos, x, axis=0, zi=self.zi)
        self.tail.extend(y)
        for row, t in zip(y, stamps):
            if self.pending_t is None:
                self.pending_t = float(t)
            self.pending_x.append(row)
            if len(self.pending_x) == self.per_bin:
                block = np.asarray(self.pending_x)
                self.bins.append({"t": self.pending_t, "min": block.min(axis=0).tolist(),
                                  "max": block.max(axis=0).tolist()})
                self.pending_x, self.pending_t = [], None
        return y

    def take_bins(self) -> list[dict]:
        out, self.bins = self.bins, []
        return out

    def now_rms(self) -> list[float | None]:
        if not self.tail:
            return [None] * self.n
        y = np.asarray(self.tail)
        return np.sqrt(np.mean(y ** 2, axis=0)).tolist()

"""
The indices of an epoch, from its clean 1 s chunks (Reevaluacion_EEG_Justificacion.md §4.4.1 to §4.4.4;
D-F6-73, D-F6-129). Per chunk a Hann periodogram on 1 Hz bins; the epoch's spectrum is their mean.
  - Engagement Index: beta / (alpha + theta) per channel, averaged over the channels present of the 7;
  - theta on Fz, over the 1–40 Hz total;
  - parietal alpha over its total, averaged over P3, Pz, P4 (stored only, D-F6-129);
  - theta / beta per channel, averaged over the 7 (stored only, D-F6-73).
Plain ratios: the log of §4.4.1 belongs to the z against the reference.
"""

import numpy as np
from scipy.signal import welch

from app.eeg.preprocess import BANDS, TOTAL

EI_CHANNELS = ("F3", "Fz", "F4", "Cz", "P3", "Pz", "P4")
PARIETAL = ("P3", "Pz", "P4")
EMPTY = {"engagement_index": None, "theta_fz": None, "alpha_parietal": None, "theta_beta": None}


def compute(chunks: list[np.ndarray], labels: list[str], srate: float) -> dict[str, float | None]:
    """chunks: the clean ones, samples × channels in µV; labels: the channel of each column."""
    n = int(srate)
    p = np.mean([welch(c[:n], fs=srate, window="hann", nperseg=len(c[:n]), nfft=n, axis=0)[1] for c in chunks], axis=0)
    f = np.fft.rfftfreq(n, 1 / srate)

    def power(band: tuple[int, int]) -> np.ndarray:
        return p[(f >= band[0]) & (f <= band[1])].sum(axis=0)

    theta, alpha, beta, total = power(BANDS["theta"]), power(BANDS["alpha"]), power(BANDS["beta"]), power(TOTAL)

    def mean(values: np.ndarray, channels: tuple[str, ...]) -> float | None:
        cols = [i for i, label in enumerate(labels) if label in channels]
        return float(values[cols].mean()) if cols else None

    return {"engagement_index": mean(beta / (alpha + theta), EI_CHANNELS),
            "theta_fz": mean(theta / total, ("Fz",)),
            "alpha_parietal": mean(alpha / total, PARIETAL),
            "theta_beta": mean(theta / beta, EI_CHANNELS)}

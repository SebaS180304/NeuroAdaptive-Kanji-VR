"""
The backend's filter on AURA's raw stream (D-F6-12): 1–40 Hz band-pass and a 60 Hz notch,
zero-phase, with the parameters stored per session in eeg_sessions.filter_params.
Also the relative-power helper of P16 (D-F6-129): band power over 1–40 Hz, from 1 Hz Welch bins
(Reevaluacion_EEG_Justificacion.md §4.4.1, steps 4–5).
"""

import numpy as np
from scipy.signal import butter, filtfilt, iirnotch, sosfiltfilt, welch

BANDPASS_HZ = (1.0, 40.0)
NOTCH_HZ = 60.0
NOTCH_Q = 30.0
ORDER = 4

# Inclusive 1 Hz bins (§4.4.1); beta 13–22 Hz (D-F6-73).
BANDS = {"theta": (4, 7), "alpha": (8, 12), "beta": (13, 22)}
TOTAL = (1, 40)  # P16


def filter_params(srate: float) -> dict:
    return {"bandpass_hz": list(BANDPASS_HZ), "bandpass": f"butterworth order {ORDER}, zero-phase",
            "notch_hz": NOTCH_HZ, "notch_q": NOTCH_Q, "srate": float(srate)}


def filter_eeg(x: np.ndarray, srate: float) -> np.ndarray:
    """samples × channels, in µV. AURA's raw stream carries offsets of tens of thousands of µV:
    the mean goes first so the filter's edges do not ring with it."""
    x = np.asarray(x, dtype=float)
    x = x - x.mean(axis=0)
    y = sosfiltfilt(butter(ORDER, BANDPASS_HZ, btype="bandpass", fs=srate, output="sos"), x, axis=0)
    b, a = iirnotch(NOTCH_HZ, NOTCH_Q, fs=srate)
    return filtfilt(b, a, y, axis=0)


def relative_power(x: np.ndarray, srate: float, band: tuple[int, int]) -> np.ndarray:
    """Power in `band` over power in 1–40 Hz, per channel (Welch, 1 s Hann window)."""
    f, p = welch(x, fs=srate, window="hann", nperseg=int(srate), axis=0)

    def power(lo: int, hi: int) -> np.ndarray:
        return p[(f >= lo) & (f <= hi)].sum(axis=0)

    return power(*band) / power(*TOTAL)

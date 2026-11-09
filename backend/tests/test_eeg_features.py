"""
F4 S3 (tasks/todo.md, M4): app/eeg/features.py, the indices of an epoch.
Formulas: Reevaluacion_EEG_Justificacion.md §4.4.1 to §4.4.4 (D-F6-73, D-F6-129).
"""

import numpy as np
import pytest

from app.eeg import epochs, features

SR = 250.0
LABELS = ["Fp1", "F3", "Fz", "F4", "Cz", "P3", "Pz", "P4"]
MONTAGE = {f"CH{i + 1}": label for i, label in enumerate(LABELS)}


def _chunk(theta: float = 10.0, alpha: float = 20.0, beta: float = 30.0) -> np.ndarray:
    """1 s, 8 channels: three sines on whole 1 Hz bins, so their power is amplitude² in each band."""
    t = np.arange(int(SR)) / SR
    signal = theta * np.sin(2 * np.pi * 6 * t) + alpha * np.sin(2 * np.pi * 10 * t) + beta * np.sin(2 * np.pi * 18 * t)
    return np.tile(signal[:, None], (1, 8))


def test_the_indices_follow_the_formulas() -> None:
    out = features.compute([_chunk(), _chunk()], LABELS, SR)
    assert out["engagement_index"] == pytest.approx(900 / (100 + 400), rel=0.01)   # beta / (alpha + theta)
    assert out["theta_fz"] == pytest.approx(100 / 1400, rel=0.01)                  # theta over 1-40 Hz
    assert out["alpha_parietal"] == pytest.approx(400 / 1400, rel=0.01)
    assert out["theta_beta"] == pytest.approx(100 / 900, rel=0.01)


def test_a_lost_channel_averages_the_rest() -> None:
    chunk = _chunk()
    chunk[:, LABELS.index("Cz")] = _chunk(beta=60.0)[:, 0]     # Cz alone has another EI
    with_cz = features.compute([chunk], LABELS, SR)["engagement_index"]
    without = features.compute([chunk], [lab if lab != "Cz" else "Oz" for lab in LABELS], SR)["engagement_index"]
    assert without == pytest.approx(900 / 500, rel=0.01)       # Oz is not one of the 7 channels
    assert with_cz == pytest.approx((6 * 900 / 500 + 3600 / 500) / 7, rel=0.01)


def _alpha_eeg(seconds: float = 12.0) -> tuple[np.ndarray, np.ndarray]:
    t = np.arange(int(seconds * SR)) / SR
    noise = np.random.default_rng(0).normal(0, 1, (len(t), 8))
    return 20 * np.sin(2 * np.pi * 10 * t)[:, None] + noise, 100.0 + t


def test_only_clean_chunks_enter_the_spectrum() -> None:
    x, ts = _alpha_eeg()
    plain = epochs.make_epochs(x, ts, SR, MONTAGE, [])[0]["engagement_index"]
    burst = x.copy()
    inside = (ts >= 101.0) & (ts < 101.5)
    burst[inside] += 50 * np.sin(2 * np.pi * 18 * ts[inside])[:, None]
    sound = [(101.0, {"event": "AUDIO_ONSET"})]
    assert epochs.make_epochs(burst, ts, SR, MONTAGE, [])[0]["engagement_index"] > 2 * plain   # the burst does matter
    assert epochs.make_epochs(burst, ts, SR, MONTAGE, sound)[0]["engagement_index"] < 2 * plain


def test_a_poor_epoch_has_no_indices() -> None:
    x, ts = _alpha_eeg()
    x[(ts >= 100.0) & (ts < 104.0), 4] = 0.0                   # Cz flat: at most 1 s left in the first epoch
    eps = epochs.make_epochs(x, ts, SR, MONTAGE, [])
    assert eps[0]["quality"] == "POOR" and eps[0]["engagement_index"] is None and eps[0]["theta_fz"] is None
    assert eps[-1]["quality"] != "POOR" and eps[-1]["engagement_index"] is not None

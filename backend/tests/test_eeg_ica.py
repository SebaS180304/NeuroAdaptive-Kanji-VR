"""
O3 (tasks/plan.md, Thu 19): option (3) of D-F6-242, offline only (D-F6-263 (2)): FastICA fitted on S4–S5 as ocul.py v2
(D-F6-255 (3)), the ocular component identified only with corr >= 0.7 and its largest weight on Fp1 (D-F6-242 (3));
not identified → option (2) for the session (D-F6-253 (2)); after the ICA, no blink rule (D-F6-252 (2)).
"""

import numpy as np
import pytest

from app.eeg import epochs, ica

SR = 250.0
LABELS = ["Fp1", "F3", "Fz", "F4", "Cz", "P3", "Pz", "P4"]
MONTAGE = {f"CH{i + 1}": l for i, l in enumerate(LABELS)}
T0 = 100.0


@pytest.fixture(autouse=True)
def _clean_test_participants():
    """Overrides the conftest fixture: no database here."""
    yield


def _state(t, state):
    return (T0 + t, {"schema_version": 1, "event": "STATE_ENTERED", "state": state, "session_elapsed_ms": int(t * 1000)})


MARKERS = [_state(0, "S4_EEG_BASELINE"), _state(60, "S5_STANDARDIZED_LEARNING"), _state(120, "S6_GUIDED_PRACTICE_CALIBRATION")]


def _mixed(seconds=150.0, blinks=True, seed=0):
    """8 channels = background sources mixed into all of them + (optionally) a blink source with weight 1 on Fp1, less behind."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    ts = T0 + np.arange(n) / SR
    x = rng.laplace(0, 4, (n, 8)) @ rng.uniform(0.5, 1.5, (8, 8))   # background sources spread over every channel
    if blinks:
        b = np.zeros(n)
        for c in rng.uniform(1, seconds - 1, int(seconds / 3)):   # one blink every ~3 s, 300 ms wide, 150 µV
            b += 150 * np.exp(-0.5 * ((ts - T0 - c) / 0.06) ** 2)
        x += np.outer(b, [1.0, 0.45, 0.4, 0.35, 0.15, 0.05, 0.05, 0.05])
    return x, ts


def test_the_ocular_component_is_found_and_removed() -> None:
    x, ts = _mixed()
    model = ica.fit(x, ts, LABELS, MARKERS)
    assert model["identified"] and model["corr"] >= 0.7 and model["top_channel"] == "Fp1"
    y = ica.apply(x, model)
    assert np.abs(y[:, 0]).max() < 0.5 * np.abs(x[:, 0]).max()   # the blinks leave Fp1


def test_without_blinks_nothing_is_identified() -> None:
    x, ts = _mixed(blinks=False)
    model = ica.fit(x, ts, LABELS, MARKERS)
    assert not model["identified"] and model["reason"]


def test_with_ica_a_blink_on_fp1_no_longer_drops_the_chunk() -> None:
    x, ts = np.random.default_rng(1).normal(0, 5, (int(30 * SR), 8)), T0 + np.arange(int(30 * SR)) / SR
    x[(ts > T0 + 10) & (ts < T0 + 10.2), 0] = 90.0   # over the 75 µV blink threshold, under the 100 µV amplitude one
    clean = lambda eps: sum(sum(e["chunk_clean"]) for e in eps)
    assert clean(epochs.make_epochs(x, ts, SR, MONTAGE, MARKERS, t0=T0, rule="ica")) > \
        clean(epochs.make_epochs(x, ts, SR, MONTAGE, MARKERS, t0=T0, rule="nosound"))


def test_not_identified_the_session_runs_with_option_2() -> None:
    x, ts = _mixed(blinks=False)
    eps, bad, ref, model = epochs.cut_session_ica(x, ts, SR, MONTAGE, MARKERS, T0)
    assert not model["identified"]
    assert eps == epochs.cut_session(x, ts, SR, MONTAGE, MARKERS, T0, rule="nosound")[0]

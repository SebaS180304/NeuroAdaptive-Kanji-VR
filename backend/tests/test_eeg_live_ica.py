"""
I1 (tasks/plan.md, Fri 20 night; D-F6-275, D-F6-276): option (3) live in live.Buffer, rule "ica". Before S6 the
epochs are cut as option (2); at S6's entry (+ EDGE_S) the ICA is fitted on S4 → S6 and every epoch centred in S6 or
later is cut on the corrected signal, without the blink rule. Not identified, a failed fit, Fp1 out before S6, or a
channel out after S6 → option (2) (D-F6-253 (2), D-F6-276 (2)). The reference carries the matrix. No LSL, no database.
"""

import numpy as np
import pytest

from app.eeg import baseline, epochs, ica, live, preprocess, reference
from app.eeg.baseline import DEFAULT_MONTAGE

SR = 250.0
LABELS = [DEFAULT_MONTAGE[f"CH{i + 1}"] for i in range(8)]
S3, S4, S5, S6, S7 = ("S3_SYSTEM_VALIDATION", "S4_EEG_BASELINE", "S5_STANDARDIZED_LEARNING",
                      "S6_GUIDED_PRACTICE_CALIBRATION", "S7_EXPERIMENTAL_RETRIEVAL")
T_S6 = 230.0


@pytest.fixture(autouse=True)
def _clean_test_participants():
    """Overrides the conftest fixture: no database here."""
    yield


def _state(t: float, state: str):
    return (t, {"schema_version": 1, "event": "STATE_ENTERED", "state": state, "esl": "MEDIUM",
                "session_elapsed_ms": int((t - 100.0) * 1000)})


MARKERS = [_state(100.0, S3), _state(110.0, S4), _state(170.0, S5), _state(T_S6, S6), _state(290.0, S7)]


def _session(seconds: float = 260.0, blinks: bool = True, seed: int = 0):
    """Background sources over every channel plus a blink source on Fp1 (less behind), as test_eeg_ica._mixed."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    ts = 100.0 + np.arange(n) / SR
    x = rng.laplace(0, 4, (n, 8)) @ rng.uniform(0.5, 1.5, (8, 8))
    if blinks:
        b = np.zeros(n)
        for c in rng.uniform(1, seconds - 1, int(seconds / 3)):
            b += 150 * np.exp(-0.5 * ((ts - 100.0 - c) / 0.06) ** 2)
        x += np.outer(b, [1.0, 0.45, 0.4, 0.35, 0.15, 0.05, 0.05, 0.05])
    return x, ts


def _f3_out(x, ts, lo: float, hi: float):
    on = (ts >= lo) & (ts < hi)
    x = x.copy()
    x[on, LABELS.index("F3")] += 300.0 * np.sin(2 * np.pi * 10 * ts[on])
    return x


def _feed(buf: live.Buffer, x, ts, markers=MARKERS, step_s: float = 0.5):
    out, n = [], int(step_s * SR)
    for i in range(0, len(ts), n):
        buf.add(x[i:i + n].tolist(), ts[i:i + n].tolist(), [m for m in markers if ts[i] <= m[0] < ts[i] + step_s])
        buf.sync_if_ready()
        out += buf.new_epochs()
    return out


def _ica_buffer(**kw) -> live.Buffer:
    buf = live.Buffer(SR, DEFAULT_MONTAGE, **kw)
    buf.rule = "ica"
    return buf


def _by_index(eps):
    return {e["epoch_index"]: e for e in eps}


def _late(e) -> bool:
    return e["lsl_start"] + epochs.EPOCH_S / 2 >= T_S6


def test_identified_corrects_from_s6_and_cuts_option_2_before() -> None:
    x, ts = _session()
    buf = _ica_buffer()
    got = _feed(buf, x, ts)
    assert buf.ica["identified"] and buf.ica["channels"] == LABELS and buf.effective_rule == "ica"
    fixed = _by_index(epochs.make_epochs(preprocess.filter_eeg(ica.apply(x, buf.ica), SR), ts, SR, DEFAULT_MONTAGE,
                                         MARKERS, t0=buf.t0, rule="ica"))
    plain = _by_index(epochs.make_epochs(preprocess.filter_eeg(x, SR), ts, SR, DEFAULT_MONTAGE, MARKERS, t0=buf.t0,
                                         rule="nosound"))
    assert any(_late(e) for e in got) and any(not _late(e) for e in got)
    for e in got:
        assert e["chunk_clean"] == (fixed if _late(e) else plain)[e["epoch_index"]]["chunk_clean"]
    late_clean = np.mean([e["clean_fraction"] for e in got if _late(e)])
    assert late_clean > np.mean([plain[e["epoch_index"]]["clean_fraction"] for e in got if _late(e)])  # blinks gone


def test_without_an_ocular_component_the_session_runs_with_option_2() -> None:
    x, ts = _session(blinks=False)
    buf = _ica_buffer()
    got = _feed(buf, x, ts)
    assert not buf.ica["identified"] and buf.ica["reason"] and buf.effective_rule == "nosound"
    plain = _by_index(epochs.make_epochs(preprocess.filter_eeg(x, SR), ts, SR, DEFAULT_MONTAGE, MARKERS, t0=buf.t0,
                                         rule="nosound"))
    assert all(e["chunk_clean"] == plain[e["epoch_index"]]["chunk_clean"] for e in got)


def test_a_fit_that_raises_falls_back_to_option_2_without_stopping(monkeypatch) -> None:
    def boom(*_a, **_k):
        raise ValueError("no convergence")
    monkeypatch.setattr(ica, "fit", boom)
    x, ts = _session()
    buf = _ica_buffer()
    got = _feed(buf, x, ts)
    assert not buf.ica["identified"] and buf.ica["reason"] == "fit failed: ValueError: no convergence"
    assert any(_late(e) for e in got) and buf.effective_rule == "nosound"


def test_the_same_model_and_reference_whatever_the_chunk_size() -> None:
    # The epochs themselves can differ in a chunk near a threshold with any rule: each live cut filters up to the newest
    # sample, so how the samples arrived moves the filter's tail (G1, 244/246 in T04). The ICA adds no such dependence.
    x, ts = _session()
    runs = []
    for step in (0.2, 0.5, 1.3):
        buf = _ica_buffer()
        got = _feed(buf, x, ts, step_s=step)
        runs.append(([e["epoch_index"] for e in got], buf.ica["unmixing"], buf.reference(got),
                     {e["epoch_index"]: e["chunk_clean"] for e in got}))
    assert runs[0][:3] == runs[1][:3] == runs[2][:3]
    for other in runs[1:]:
        same = sum(other[3][i] == runs[0][3][i] for i in runs[0][3])
        assert same >= 0.97 * len(runs[0][3])


def test_the_reference_carries_the_matrix() -> None:
    x, ts = _session()
    buf = _ica_buffer()
    got = _feed(buf, x, ts)
    eps = epochs.make_epochs(preprocess.filter_eeg(ica.apply(x, buf.ica), SR), ts, SR, DEFAULT_MONTAGE, MARKERS,
                             t0=buf.t0, rule="ica")
    assert buf.reference(got) == reference.compute(eps, baseline.spans(MARKERS))


def test_a_stored_model_gives_the_same_epochs_without_refitting(monkeypatch) -> None:
    x, ts = _session()
    first = _ica_buffer()
    got = _feed(first, x, ts)
    monkeypatch.setattr(ica, "fit", lambda *_a, **_k: pytest.fail("refitted"))
    again = _ica_buffer(ica_model=first.ica)
    assert [e["chunk_clean"] for e in _feed(again, x, ts)] == [e["chunk_clean"] for e in got]
    assert again.ica == first.ica


# ---------- the channel out (D-F6-276 (2), D-F6-216) ----------

def test_a_channel_out_before_s6_is_left_out_of_the_fit() -> None:
    x, ts = _session()
    x = _f3_out(x, ts, 130.0, 190.0)              # 2nd bad bin ends at 190 < S6 (230)
    buf = _ica_buffer()
    got = _feed(buf, x, ts)
    assert buf.bad[0] == ("F3", 190.0)
    assert buf.ica["identified"] and buf.ica["channels"] == [l for l in LABELS if l != "F3"]
    assert len(buf.ica["unmixing"]) == 7 and buf.effective_rule == "ica"
    assert {e["excluded_channels"] for e in got if _late(e)} == {"F3"}


def test_fp1_out_before_s6_runs_the_session_with_option_2(monkeypatch) -> None:
    # the detector never marks Fp1 (its own rule, D-F6-75): this guards D-F6-276 (2) all the same
    monkeypatch.setattr(epochs, "persistently_bad", lambda *_a, **_k: [("Fp1", 150.0)])
    x, ts = _session()
    buf = _ica_buffer()
    _feed(buf, x, ts)
    assert not buf.ica["identified"] and buf.ica["reason"] == "Fp1 out before S6" and buf.effective_rule == "nosound"


def test_a_channel_out_after_s6_switches_to_option_2_to_the_end_without_refitting() -> None:
    x, ts = _session(seconds=300.0)
    x = _f3_out(x, ts, 250.0, 310.0)              # bins from t0 = 100: 250–280 and 280–310 bad → out from 310 > S6
    buf = _ica_buffer()
    got = _feed(buf, x, ts)
    assert buf.bad[0] == ("F3", 310.0)
    assert buf.ica["identified"] and buf.ica["switched_to_nosound_at"] == 310.0 and buf.ica["switch_reason"] == "F3 out after S6"
    assert buf.effective_rule == "nosound" and len(buf.ica["unmixing"]) == 8   # the S6 fit, kept as it was
    plain = _by_index(epochs.make_epochs(preprocess.filter_eeg(x, SR), ts, SR, DEFAULT_MONTAGE, MARKERS, t0=buf.t0,
                                         bad=buf.bad, rule="nosound"))
    after = [e for e in got if e["lsl_start"] >= 310.0]
    assert after and all(e["chunk_clean"] == plain[e["epoch_index"]]["chunk_clean"] for e in after)
    assert buf.reference(got) == epochs.cut_session(preprocess.filter_eeg(x, SR), ts, SR, DEFAULT_MONTAGE, MARKERS,
                                                    buf.t0, rule="nosound")[2]

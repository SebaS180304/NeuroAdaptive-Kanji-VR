"""
Option (3) of D-F6-242: ICA fitted on S4–S5. Live in live.Buffer behind EEG_LIVE_RULE=ica (D-F6-275, D-F6-276); offline
in epochs.cut_session_ica. The fit and the choice of the ocular component copy ocul.py v2 lines 152–157 (D-F6-255 (3)):
FastICA of one component per channel given (8; 7 with a channel out before S6, D-F6-276 (2))
(whiten='unit-variance', random_state=0, max_iter=1000) on the filtered signal from S4's start to S5's end;
k = argmax(|corr(source_i, Fp1)| x |A[Fp1, i]| / sum_c |A[c, i]|), corr on the fit span. It counts as identified only
with corr >= 0.7 and its largest |A[c, k]| on Fp1 (D-F6-242 (3)); ocul.py only prints that, the backend decides on it:
not identified → the session is not corrected and runs with option (2) (D-F6-253 (2)).
"""

import numpy as np
from sklearn.decomposition import FastICA

MIN_CORR = 0.7
S4, S5 = "S4_EEG_BASELINE", "S5_STANDARDIZED_LEARNING"


def _fit_span(markers: list[tuple[float, dict]]) -> tuple[float, float] | None:
    """LSL time of S4's entry and of the entry after S5 (as ocul.py's span('S4')[0][0], span('S5')[0][1])."""
    entered = [(t, m.get("state")) for t, m in markers if m.get("event") == "STATE_ENTERED"]
    a = next((t for t, s in entered if s == S4), None)
    b = next((t2 for (t1, s), (t2, _) in zip(entered, entered[1:]) if s == S5), None)
    return (a, b) if a is not None and b is not None and b > a else None


def fit(x: np.ndarray, ts: np.ndarray, labels: list[str], markers: list[tuple[float, dict]]) -> dict:
    """x: filtered EEG, samples x channels. The model as JSON-friendly lists, with why it is or is not identified."""
    span = _fit_span(markers)
    if span is None:
        return {"identified": False, "reason": "no S4–S5 span in the markers"}
    sl = (ts >= span[0]) & (ts < span[1])
    fp1 = labels.index("Fp1")
    n = x.shape[1]
    model = FastICA(n, whiten="unit-variance", random_state=0, max_iter=1000)
    model.fit(x[sl])
    a = model.mixing_
    src = model.transform(x[sl])
    corr = [abs(float(np.corrcoef(src[:, i], x[sl, fp1])[0, 1])) for i in range(n)]
    share = [abs(a[fp1, i]) / np.abs(a[:, i]).sum() for i in range(n)]
    k = int(np.argmax([c * f for c, f in zip(corr, share)]))
    top = labels[int(np.argmax(np.abs(a[:, k])))]
    identified = corr[k] >= MIN_CORR and top == "Fp1"
    reason = None if identified else (f"corr with Fp1 {corr[k]:.2f} < {MIN_CORR}" if corr[k] < MIN_CORR
                                      else f"largest weight on {top}, not Fp1")
    return {"identified": identified, "reason": reason, "component": k, "corr": round(corr[k], 4), "top_channel": top,
            "fit_span_lsl": list(span), "mean": model.mean_.tolist(), "unmixing": model.components_.tolist(),
            "mixing": a.tolist()}


def apply(x: np.ndarray, model: dict) -> np.ndarray:
    """x without the ocular component: sources of x with component k set to 0, mixed back (ocul.py line 157)."""
    mean, w, a = (np.asarray(model[k]) for k in ("mean", "unmixing", "mixing"))
    src = (x - mean) @ w.T
    src[:, model["component"]] = 0.0
    return src @ a.T + mean

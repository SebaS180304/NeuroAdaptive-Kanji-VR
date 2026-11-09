"""
Does the EEG count in a decision window, and with which z (Planteamiento_Tecnico_F4.md §2.2)?
The same definition as verify_eeg.sql (D-F6-162) and, later, the live path and replay.py.

The window ends at the answer of its 3rd trial, where the decision is taken (D-F6-177), and reaches back over its
3 trials or 15 s, whichever is longer (D-F6-151). An epoch is in it by its centre and only if it had finished at the
answer (D-F6-172). The EEG counts with >= 2 non-POOR epochs and >= 5 s of clean chunks, each second once (D-F6-127).
z of an index = mean over the non-POOR epochs of (ln index - mean) / SD of the session's reference (§4.4.1).
"""

import math
import statistics

from app.eeg.epochs import EPOCH_S
from app.eeg.reference import INDICES

MIN_SPAN_MS = 15_000
MIN_NON_POOR = 2
MIN_CLEAN_S = 5.0
CENTRE_MS = int(EPOCH_S * 500)
CHUNK_MS = 1000


def _clean_s(eps: list[dict]) -> float:
    spans = sorted((e["start_ms"] + k * 4000 // (len(e["chunk_clean"]) - 1),) * 2 for e in eps
                   for k, clean in enumerate(e["chunk_clean"]) if clean)
    covered, end = 0, None
    for start, _ in spans:
        covered += CHUNK_MS - (max(0, end - start) if end is not None else 0)
        end = start + CHUNK_MS
    return covered / 1000


def _z(eps: list[dict], name: str, ref: dict) -> float | None:
    stats = ref["indices"].get(name)
    values = [e[name] for e in eps if e[name] is not None]
    if not stats or stats["sd"] is None or not values:
        return None
    return statistics.fmean((math.log(v) - stats["mean"]) / stats["sd"] for v in values)


def evaluate(eps: list[dict], first_start_ms: int, decision_ms: int, ref: dict) -> dict:
    """eps: the session's epochs; first_start_ms: start of the window's 1st trial; decision_ms: answer of its 3rd."""
    lo = min(first_start_ms, decision_ms - MIN_SPAN_MS)
    inside = [e for e in eps if e["start_ms"] is not None and lo <= e["start_ms"] + CENTRE_MS <= decision_ms
              and e["end_ms"] <= decision_ms]
    usable = [e for e in inside if e["quality"] != "POOR"]
    clean_s = _clean_s(inside)
    return {"counted": len(usable) >= MIN_NON_POOR and clean_s >= MIN_CLEAN_S, "non_poor": len(usable), "clean_s": clean_s,
            "z": {name: _z(usable, name, ref) for name in INDICES}}

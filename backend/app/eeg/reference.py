"""
The person's own reference for the z of each index (Reevaluacion_EEG_Justificacion.md §4.4.1 step 7 and §5.4;
D-F6-73): mean and SD of ln(index) over the non-POOR epochs of S6. With fewer than 6 of them, the epochs of S4
with the eyes open, and the session says so. Stored in eeg_sessions.reference.
"""

import json
import math
import statistics
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.eeg.epochs import EPOCH_S

S6_STATE, S4_STATE = "S6_GUIDED_PRACTICE_CALIBRATION", "S4_EEG_BASELINE"
MIN_EPOCHS = 6
INDICES = ("engagement_index", "theta_fz", "alpha_parietal", "theta_beta")
MIN_SD = 1e-6  # in ln units; real spreads are near 0.2. Below this a z would only be noise over noise.
NONE = {"source": None, "fallback": False, "n_epochs": 0, "indices": {}}


def _stats(values: list[float | None]) -> dict:
    logs = [math.log(v) for v in values if v is not None]
    sd = statistics.stdev(logs) if len(logs) >= 2 else 0.0
    return {"mean": statistics.fmean(logs) if logs else None, "sd": sd if sd >= MIN_SD else None, "n": len(logs)}


def compute(eps: list[dict], s4_spans: tuple | None) -> dict:
    """eps: the session's epochs; s4_spans: baseline.spans(markers), on the clock of lsl_start, or None."""
    usable = [e for e in eps if e["quality"] != "POOR"]
    chosen, source = [e for e in usable if e["game_state"] == S6_STATE], "S6"
    if len(chosen) < MIN_EPOCHS:
        if s4_spans is None:
            return NONE
        lo, hi = s4_spans[0]  # whole epochs inside: one that overlaps the closed segment is not a reference of eyes open
        chosen = [e for e in usable if e["game_state"] == S4_STATE and lo <= e["lsl_start"] and e["lsl_start"] + EPOCH_S <= hi]
        source = "S4_EYES_OPEN"
    if not chosen:
        return NONE
    return {"source": source, "fallback": source != "S6", "n_epochs": len(chosen),
            "indices": {name: _stats([e[name] for e in chosen]) for name in INDICES}}


async def save(db: AsyncSession, session_id: uuid.UUID | str, ref: dict) -> None:
    await db.execute(text("UPDATE eeg_sessions SET reference = CAST(:r AS jsonb) WHERE session_id = :s"),
                     {"s": str(session_id), "r": json.dumps(ref)})

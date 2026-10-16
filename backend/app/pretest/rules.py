"""
Kanji pre-test substitution rules (spec §13.2).

The contract's substitutionTable answers "which reserve kanji may replace e in
the NOMINAL set". A participant can know two kanji of one set, and then the
second substitute has to fit the set that already holds the first. So the three
§13.2 conditions are re-applied here, to the participant's effective set, with
the same data and thresholds as tools/kanji_metrics.py (which exports them).
test_pretest_rules checks that, with nothing substituted, this reproduces the
exported table exactly.
"""

import functools
import itertools
import json
from pathlib import Path

# Same relative path in the repo and in the backend container (docker-compose
# mounts unity-client/Assets/Resources read-only at /unity-client/...).
CONTENT_PATH = (Path(__file__).resolve().parents[3]
                / "unity-client" / "Assets" / "Resources" / "kanji_content.json")

# Band name in rules.bands -> field of a kanji record.
_BAND_FIELDS = {"strokes": "strokes", "morae": "morae",
                "groups": "assemblyGroups", "readings": "commonReadings"}


@functools.cache
def contract() -> dict:
    return json.loads(CONTENT_PATH.read_text(encoding="utf-8"))


@functools.cache
def _kanji() -> dict[str, dict]:
    return {k["kanji"]: k for k in contract()["kanji"]}


def _sim(a: str, b: str) -> float:
    s = contract()["similarity"]
    return s[a + b] if a + b in s else s[b + a]


@functools.cache
def _reference_perim() -> float:
    sets = contract()["sets"].values()
    return sum(_total(m, "perimetricComplexity") for m in sets) / len(sets)


def _total(members, field: str) -> float:
    k = _kanji()
    return sum(k[c][field] for c in members)


def _hard_clash(a: str, b: str) -> bool:
    ka, kb = _kanji()[a], _kanji()[b]
    return (ka["targetReading"] == kb["targetReading"]
            or ka["meaning"] == kb["meaning"]
            or _sim(a, b) > contract()["rules"]["simMaxPair"])


def _in_band(members: list[str]) -> bool:
    rules = contract()["rules"]
    for name, band in rules["bands"].items():
        if name == "readings" and not rules["substitution"]["applyReadingsBand"]:
            continue
        if abs(_total(members, _BAND_FIELDS[name]) - band["centre"]) > band["tolerance"]:
            return False
    ref = _reference_perim()
    if abs(100.0 * (_total(members, "perimetricComplexity") - ref) / ref) > rules["perimetricTolerancePct"]:
        return False
    sims = [_sim(a, b) for a, b in itertools.combinations(members, 2)]
    return max(sims) <= rules["simMaxPair"] and sum(sims) / len(sims) <= rules["simMaxMean"]


def valid_substitutes(set_name: str, effective: list[str], original: str,
                      excluded=frozenset()) -> list[str]:
    """Reserve kanji that may replace `original` in `effective`, in reserve order.

    `effective` is the participant's set as it stands (earlier substitutions
    applied); `excluded` holds reserve kanji that are known or already used.
    """
    k = _kanji()
    delta = contract()["rules"]["substitution"]
    rest = [c for c in effective if c != original]
    out = []
    for r in contract()["reserve"]:
        if r in excluded or r in effective:
            continue
        if any(_hard_clash(r, x) for x in rest):
            continue
        if abs(k[r]["strokes"] - k[original]["strokes"]) > delta["deltaStrokes"]:
            continue
        if abs(k[r]["morae"] - k[original]["morae"]) > delta["deltaMorae"]:
            continue
        if not _in_band(rest + [r]):
            continue
        out.append(r)
    return out


def _distance_to_nominal(set_name: str, members: list[str]) -> float:
    """How far a set sits from the nominal one, in units of each band's tolerance."""
    rules = contract()["rules"]
    nominal = contract()["sets"][set_name]
    d = sum(abs(_total(members, _BAND_FIELDS[n]) - _total(nominal, _BAND_FIELDS[n]))
            / rules["bands"][n]["tolerance"] for n in ("strokes", "morae", "groups"))
    p, p0 = _total(members, "perimetricComplexity"), _total(nominal, "perimetricComplexity")
    return d + abs(100.0 * (p - p0) / p0) / rules["perimetricTolerancePct"]


def ranked_substitutes(set_name: str, effective: list[str], original: str,
                       excluded=frozenset()) -> list[str]:
    """valid_substitutes, best fit first (closest to the nominal set); ties keep reserve order."""
    def with_r(r):
        return [r if c == original else c for c in effective]
    return sorted(valid_substitutes(set_name, effective, original, excluded),
                  key=lambda r: _distance_to_nominal(set_name, with_r(r)))

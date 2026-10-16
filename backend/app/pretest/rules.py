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
import re
from dataclasses import dataclass, field
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


# --------------------------------------------------------------------------- #
# Classification and the substitution chain
# --------------------------------------------------------------------------- #

UNKNOWN, PARTIALLY_KNOWN, KNOWN = "UNKNOWN", "PARTIALLY_KNOWN", "KNOWN"


def classify(self_report: str, reading_ok: bool, meaning_ok: bool) -> str:
    """Spec 13.2. NO skips the prompts, so it is UNKNOWN whatever else came in."""
    if self_report == "NO":
        return UNKNOWN
    return (UNKNOWN, PARTIALLY_KNOWN, KNOWN)[int(reading_ok) + int(meaning_ok)]


@dataclass
class ChainState:
    next: str | None                                        # kanji to ask now; None = done
    substitutions: list[tuple[str, str, str]] = field(default_factory=list)  # (set, original, substitute)
    flagged: list[tuple[str, str]] = field(default_factory=list)            # (set, KNOWN kept: no substitute left)


def chain_state(responses: dict[str, str]) -> ChainState:
    """Where the pre-test stands, recomputed from the classifications so far.

    Primaries in contract order; a KNOWN one is followed by its ranked
    substitutes until one is not KNOWN. Deterministic: the same responses always
    give the same next kanji and the same substitutions.
    shortcut: greedy per kanji -- an early substitute can block a later one in the
    same set, which then gets flagged; search jointly if flags show up in practice.
    """
    state = ChainState(next=None)
    used: set[str] = set()
    known = {c for c, v in responses.items() if v == KNOWN}
    for name, members in contract()["sets"].items():
        effective = list(members)
        for i, e in enumerate(members):
            if e not in responses:
                state.next = e
                return state
            if responses[e] != KNOWN:
                continue
            for r in ranked_substitutes(name, effective, e, excluded=used | known):
                if r not in responses:
                    state.next = r
                    return state
                effective[i] = r          # tested and not KNOWN (KNOWN is excluded)
                used.add(r)
                state.substitutions.append((name, e, r))
                break
            else:
                state.flagged.append((name, e))
    return state


# --------------------------------------------------------------------------- #
# Auto-grading. The researcher can overrule both results on the page.
# --------------------------------------------------------------------------- #

_ROWS = {
    "": "あいうえお", "k": "かきくけこ", "s": "さしすせそ", "t": "たちつてと",
    "n": "なにぬねの", "h": "はひふへほ", "m": "まみむめも", "y": "や ゆ よ",
    "r": "らりるれろ", "w": "わ   を", "g": "がぎぐげご", "z": "ざじずぜぞ",
    "d": "だぢづでど", "b": "ばびぶべぼ", "p": "ぱぴぷぺぽ",
}
_IRREGULAR = {"し": "shi", "ち": "chi", "つ": "tsu", "ふ": "fu", "じ": "ji",
              "ぢ": "ji", "づ": "zu", "を": "o", "ん": "n"}
_KANA = {k: c + v for c, row in _ROWS.items() for k, v in zip(row, "aiueo") if k != " "}
_KANA.update(_IRREGULAR)
# Kunrei / Nihon-shiki spellings a participant may type, folded to Hepburn.
# Lookbehinds keep Hepburn input intact ("shu" must not become "sfu").
_TO_HEPBURN = [(r"sy", "sh"), (r"ty", "ch"), (r"[zj]y", "j"), (r"si", "shi"),
               (r"ti", "chi"), (r"tu", "tsu"), (r"(?<![sc])hu", "fu"), (r"zi", "ji")]


def _hiragana(s: str) -> str:
    return "".join(chr(ord(ch) - 0x60) if "ァ" <= ch <= "ヶ" else ch for ch in s)


def _romaji(kana: str) -> str:
    out, i = "", 0
    while i < len(kana):
        ch, nxt = kana[i], kana[i + 1] if i + 1 < len(kana) else ""
        if ch == "っ":
            out += "@"                      # doubles the next consonant below
        elif nxt in "ゃゅょ" and nxt:
            base = _KANA[ch]
            stem = base[:-1] if base in ("shi", "chi", "ji") else base[:-1] + "y"
            out += stem + {"ゃ": "a", "ゅ": "u", "ょ": "o"}[nxt]
            i += 1
        else:
            out += _KANA[ch]
        i += 1
    return "".join(("t" if out[j + 1:j + 3] == "ch" else out[j + 1]) if c == "@" else c
                   for j, c in enumerate(out))


def _fold_romaji(s: str) -> str:
    for a, b in _TO_HEPBURN:
        s = re.sub(a, b, s)
    return s


def _clean(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())


def auto_grade(char: str, typed_reading: str, typed_meaning: str) -> tuple[bool, bool]:
    k = _kanji()[char]
    target = _hiragana(k["targetReading"])
    reading = _hiragana(_clean(typed_reading or ""))
    reading_ok = bool(reading) and (reading == target
                                    or _fold_romaji(reading) == _romaji(target))

    meaning = (typed_meaning or "").lower().strip()
    for article in ("a ", "an ", "the ", "to "):
        meaning = meaning.removeprefix(article)
    meaning_ok = bool(meaning) and _clean(meaning) in {_clean(m) for m in k["meaning"].split(",")}
    return reading_ok, meaning_ok

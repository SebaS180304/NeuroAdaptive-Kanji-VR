#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kanji_optimizer.py — EXACT search for the best split of kanji into three sets.

NeuroAdaptive VR Kanji project, Phase 2.
Reference documents:
    claude/Metricas_Dificultad_Kanji_Fase2.md
    claude/Tabla_Autoria_Kanji_Fase2.md
Companion: kanji_metrics.py (verifies a given split; this one finds the best).

────────────────────────────────────────────────────────────────────────────
THE PROBLEM
────────────────────────────────────────────────────────────────────────────
Choose 15 kanji from a universe of ~36 and split them into three sets of 5
such that the three are as equivalent as possible in difficulty, satisfying
the hard design constraints, and leaving a reserve pool that is usable.

The space is C(36,15) · 15!/(5!³·3!) ≈ 7·10¹⁴ splits. Brute force is not an
option, and neither is a heuristic without a guarantee: the split defines the
experimental manipulation, so we need to know that the result is OPTIMAL,
not just good.

────────────────────────────────────────────────────────────────────────────
HOW IT IS SOLVED
────────────────────────────────────────────────────────────────────────────
Decomposition into two stages, both exact:

  Stage 1 · Enumerate the FEASIBLE sets of 5.
      DFS over combinations with:
        · per-kanji incompatibility bitmask (reading, meaning, semantic
          cluster or shape collision) → the conflict filter is an integer
          AND, O(1)
        · incremental partial sums
        · suffix band bounds: at each node the minimum and maximum sum
          reachable with the remaining kanji is known, and the node is pruned
          if the band is already unreachable (precomputed tables, O(1) per
          check)

  Stage 2 · Find the best DISJOINT triple of feasible sets.
      Branch and bound with an admissible lower bound and a spatial index:
        · the balance objective is Σ_m w_m·(max−min) over the three sets,
          and for every pair (a,b):   J(a,b,c) ≥ Σ_m w_m·|v_a,m − v_b,m|
          i.e. the weighted L1 distance between the vectors of a and b
          is an ADMISSIBLE LOWER BOUND on the objective of the full triple
        · scaling each coordinate by its weight, that bound is literally
          an L1 distance → a k-d tree (scipy, p=1) answers "give me all
          sets at distance < J*" in sublinear time
        · within each query the candidates are traversed in order of
          increasing bound, so the first candidate that does not improve
          cuts off the rest of the branch at once
        · the query radius shrinks every time the incumbent improves
        · symmetry breaking: minidx(a) < minidx(b) < minidx(c) is required,
          so each triple is visited once instead of six times
        · the incumbent is seeded by directed construction, to start with a
          small radius even under hard triple constraints
        · the constraints that depend on the triple (continuity) are also
          applied vectorized inside the traversal, not only on acceptance
      When it finishes, the optimum is PROVEN: everything pruned had a lower
      bound ≥ the feasible incumbent. With --time-limit the traversal can be
      cut short: the result is then still valid but is marked as
      not proven.

  Optional verification · CP-SAT backend (OR-Tools) with the equivalent
      integer model. Enabled only if the library is installed.

────────────────────────────────────────────────────────────────────────────
THE TWO CONSTRAINTS THAT ARE NOT OBVIOUS
────────────────────────────────────────────────────────────────────────────
1. SUBSTITUTABILITY (§13.2 of the spec). The reserve pool exists to
   replace items the participant already knows. Optimizing only the sets
   uses up the clean kanji and leaves an unusable reserve. Here it is
   required that EACH of the 15 experimental kanji has at least one valid
   substitute in the leftovers, of comparable complexity. Without this the
   optimum is a trap: perfect sets that cannot be run.

2. CONTINUITY (--keep-current K). The unconstrained global optimum
   replaces almost all of the current design, which is correct but is a
   different study. With K, the request is for the best split that keeps at
   least K of the 15 current kanji, which is the question that can actually
   be taken to a meeting.

Usage:
    python3 kanji_optimizer.py                      # global optimum
    python3 kanji_optimizer.py --keep-current 10    # the best gradual change
    python3 kanji_optimizer.py --top 10
    python3 kanji_optimizer.py --allow-contextual   # allows 私
    python3 kanji_optimizer.py --cpsat
    python3 kanji_optimizer.py --sweep              # continuity/quality curve
    python3 kanji_optimizer.py --keep-current 15    # re-split the current 15

Requirements: pillow, numpy, scipy. No network. OR-Tools optional.
"""

from __future__ import annotations

import argparse
import heapq
import itertools
import json
import random
import sys
import time
from dataclasses import dataclass, field
from math import comb

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.spatial import cKDTree

from kanji_metrics import (DEFAULT_FONT as METRICS_FONT, KANJI as METRICS_KANJI,
                           SETS as METRICS_SETS)

# The same face kanji_metrics measures on, and Unity renders on the board: the
# repository's NotoSansCJKjp-Regular.otf. Until 29 September this was the
# system .ttc, so the optimizer and the verifier measured different faces.
DEFAULT_FONT = str(METRICS_FONT)
CACHE_FILE = ".kanji_glyph_cache.json"
SET_SIZE = 5
N_SETS = 3


# ═══════════════════════════════════════════════════════════════════════════
# 1 · DATA
# ═══════════════════════════════════════════════════════════════════════════
# Verified against Basic Kanji Book Vol. 1 (Bonjinsha), lessons 1, 2, 6 and 7
# — the four "Kanji made from pictures" units, the only ones whose four-stage
# derivation format matches the discovery mechanic of the spec. Left out are
# lessons 3 (numbers), 4 (signs) and 5 (combination of meanings).
#
# imageability: 1–5, how well a concrete object anchors the meaning. It is
# the only dimension that cannot be automated. The values below are
# PROVISIONAL, to be replaced by those from the MIRAI reviewer.

@dataclass(frozen=True)
class Kanji:
    char: str
    reading: str
    meaning: str
    strokes: int
    morae: int
    groups: int          # assembly segmentation groups (2–4)
    readings: int        # number of common readings of the character
    cluster: str         # semantic cluster, for the T2 distractors
    lesson: str          # lesson in the book
    imageability: int    # 1–5, provisional
    discovery: str = "picture"   # picture | sign | compound | context
    excluded: bool = False       # out of the official pool, no matter what


# Each discovery kind is a different mechanism that has to be built in
# Unity. Mixing them has a development cost and breaks the uniformity of the
# instruction across items, so by default only the pictographic ones are in.
DISCOVERY_KINDS = {
    "picture":  "object → simplified shape → kanji (L1, L2, L6, L7)",
    "sign":     "abstract sign → kanji (L4) — needs a spatial mechanic",
    "compound": "two known kanji → kanji (L5) — needs a joining mechanic",
    "context":  "no derivation; anchored in context of use",
}


# The shared columns -- reading, strokes, morae, assembly groups, number of
# readings, meaning, lesson -- come from kanji_metrics.KANJI, the single
# table the content contract is exported from. Until 29 September 2026 this
# file kept its own copy, and the two had already drifted: 足 was "leg" here
# and "leg, foot" there. Only what the optimizer adds lives below.
#
# OPTIMIZER_FIELDS: character -> (semantic cluster, imageability 1-5,
#                                 discovery kind, excluded from the pool)
#
# The ORDER of this table is the order of UNIVERSE, and that order is the
# kanji index the search uses to break symmetry. Keep it stable, or the same
# inputs can return a different one of several equally good splits.
OPTIMIZER_FIELDS: dict[str, tuple[str, int, str, bool]] = {
    # -- Lesson 1 · Kanji made from pictures -1- --------------------------
    "日": ("celeste",   5, "picture", False),
    "月": ("celeste",   5, "picture", False),
    "木": ("planta",    5, "picture", False),
    "山": ("terreno",   5, "picture", False),
    "川": ("terreno",   5, "picture", False),
    "田": ("terreno",   4, "picture", False),
    "人": ("person",    5, "picture", False),
    "口": ("body",      4, "picture", False),
    "車": ("objeto",    5, "picture", False),
    "門": ("objeto",    5, "picture", False),
    # -- Lesson 2 · Kanji made from pictures -2- --------------------------
    # 生 is not modelled: none of its readings works for the kanji alone, and
    # it is out of the official pool.
    "火": ("elemento",  5, "picture", False),
    "水": ("elemento",  5, "picture", False),
    "金": ("objeto",    4, "picture", False),
    "土": ("terreno",   3, "picture", False),
    "子": ("person",    5, "picture", False),
    "女": ("person",    5, "picture", False),
    "学": ("abstracto", 2, "picture", False),
    # 先 is OUT of the official pool (decision of 8 September). Kept in the
    # model only to evaluate earlier splits; never eligible.
    "先": ("abstracto", 2, "picture", True),
    # -- Lesson 6 · Kanji made from pictures -3- --------------------------
    "目": ("body",      4, "picture", False),
    "耳": ("body",      3, "picture", False),
    "手": ("body",      5, "picture", False),
    "足": ("body",      4, "picture", False),
    "雨": ("elemento",  4, "picture", False),
    "竹": ("planta",    5, "picture", False),
    "米": ("planta",    4, "picture", False),
    "貝": ("animal",    5, "picture", False),
    "石": ("terreno",   5, "picture", False),
    "糸": ("objeto",    4, "picture", False),
    # -- Lesson 7 · Kanji made from pictures -4- --------------------------
    # 字 and 文 left out: abstract meanings, no object to anchor them in the
    # Object/Association Area.
    "魚": ("animal",    5, "picture", False),
    "鳥": ("animal",    5, "picture", False),
    "馬": ("animal",    5, "picture", False),
    "牛": ("animal",    5, "picture", False),
    "肉": ("comida",    4, "picture", False),
    "花": ("planta",    5, "picture", False),
    "物": ("abstracto", 1, "picture", False),
    "茶": ("comida",    4, "picture", False),
    # -- Lesson 4 · Kanji made from SIGNS ---------------------------------
    # Four-stage derivation, but from an abstract sign, not an object.
    # Eligible only with --discovery sign. 大, 小, 半 and 分 are out because
    # they are adjectives or verbs with okurigana; 何 because it is a
    # question word.
    "本": ("objeto",    5, "sign", False),
    "中": ("abstracto", 3, "sign", False),
    "上": ("abstracto", 2, "sign", False),
    "下": ("abstracto", 2, "sign", False),
    "力": ("abstracto", 2, "sign", False),
    # -- Lesson 5 · Kanji made from a COMBINATION OF THE MEANINGS ---------
    # Derived by joining kanji the participant already knows (林 = 木+木,
    # 岩 = 山+石). In VR that is a joining mechanic, not a transformation: a
    # third mechanism. In exchange, most of the three-mora readings the pool
    # lacks live here. Eligible with --discovery compound. 明, 休 and 好 are
    # out because they are adjectives or verbs with okurigana.
    "男": ("person",    5, "compound", False),
    "体": ("body",      4, "compound", False),
    "林": ("planta",    5, "compound", False),
    "畑": ("terreno",   4, "compound", False),
    "岩": ("terreno",   5, "compound", False),
    "森": ("planta",    5, "compound", False),
    "間": ("abstracto", 2, "compound", False),
    # -- No derivation ----------------------------------------------------
    # 私 is in Lesson 2 but NOT in its pictographic derivation table. Always
    # in the model to evaluate earlier splits, eligible only with
    # --discovery context.
    "私": ("abstracto", 1, "context", False),
}


def _build_universe() -> list[Kanji]:
    missing = [c for c in OPTIMIZER_FIELDS if c not in METRICS_KANJI]
    if missing:
        raise SystemExit(f"kanji_metrics.KANJI has no row for: {' '.join(missing)}")
    out = []
    for ch, (cluster, imageability, discovery, excluded) in OPTIMIZER_FIELDS.items():
        k = METRICS_KANJI[ch]
        out.append(Kanji(ch, k.reading, k.meaning, k.strokes, k.morae, k.groups,
                         k.readings, cluster, k.lesson, imageability,
                         discovery, excluded))
    return out


UNIVERSE: list[Kanji] = _build_universe()

# The split in force, for comparison: the official sets of kanji_metrics
# (fixed on 8 September, D1-D4), not a copy of them. Until 29 September this
# was still the pre-8-September split (日山車女学 / 月川門子私 / 木田人金先).
CURRENT = [list(METRICS_SETS[tag]) for tag in ("A", "B", "C")]
CURRENT_FLAT = [c for s in CURRENT for c in s]


# ═══════════════════════════════════════════════════════════════════════════
# 2 · GEOMETRIC METRICS
# ═══════════════════════════════════════════════════════════════════════════

class Glyphs:
    """Renders glyphs and computes the two geometric metrics.

    Perimetric complexity  C = P²/A  (Pelli, Burns, Farell & Moore-Page 2006).
    Graphic confusability  Pearson correlation between smoothed maps.

    Both depend on the typeface, so the on-disk cache carries the font path
    in the key: changing the font invalidates it automatically.
    """

    def __init__(self, font_path: str, cache_path: str = CACHE_FILE):
        self.font_path = font_path
        self.cache_path = cache_path
        self.big = ImageFont.truetype(font_path, 512)
        self.small = ImageFont.truetype(font_path, 256)
        self._perim: dict[str, float] = {}
        self._vec: dict[str, np.ndarray] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        try:
            with open(self.cache_path, encoding="utf-8") as fh:
                blob = json.load(fh)
            if blob.get("font") == self.font_path:
                self._perim = blob.get("perim", {})
        except (OSError, ValueError):
            pass

    def save_cache(self) -> None:
        try:
            with open(self.cache_path, "w", encoding="utf-8") as fh:
                json.dump({"font": self.font_path, "perim": self._perim}, fh)
        except OSError:
            pass

    def _ink(self, ch: str, font, pad: int) -> np.ndarray:
        size = font.size + 2 * pad
        img = Image.new("L", (size, size), 255)
        ImageDraw.Draw(img).text((pad, pad), ch, font=font, fill=0)
        return np.array(img) < 128

    def perim(self, ch: str) -> float:
        if ch not in self._perim:
            ink = self._ink(ch, self.big, 64)
            area = int(ink.sum())
            if area == 0:
                raise ValueError(f"the font has no glyph for {ch!r}")
            p = int(np.logical_xor(ink[:, :-1], ink[:, 1:]).sum()
                    + np.logical_xor(ink[:-1, :], ink[1:, :]).sum())
            self._perim[ch] = p * p / area
        return self._perim[ch]

    def _shape(self, ch: str, blur: float = 4.0) -> np.ndarray:
        if ch not in self._vec:
            ink = 255.0 * self._ink(ch, self.small, 40)
            ys, xs = np.where(ink > 0)
            crop = ink[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
            im = (Image.fromarray(crop.astype(np.uint8))
                  .resize((128, 128)).filter(ImageFilter.GaussianBlur(blur)))
            v = np.asarray(im, dtype=float).ravel()
            v -= v.mean()
            self._vec[ch] = v / np.linalg.norm(v)
        return self._vec[ch]

    def similarity_matrix(self, chars: list[str]) -> np.ndarray:
        M = np.stack([self._shape(c) for c in chars])
        return M @ M.T


# ═══════════════════════════════════════════════════════════════════════════
# 3 · MODEL
# ═══════════════════════════════════════════════════════════════════════════

# Metrics balanced across sets. The weight says how much one point of
# relative imbalance in that metric counts.
#   morae weighs more: it is the dimension where the current design fails and
#   the one that directly affects trial T3.
#   sim is the mean confusability within the set: if one set is more
#   self-confusable than another, its T1/T2 trials are harder.
METRIC_WEIGHTS: dict[str, float] = {
    "strokes":  1.0,
    "perim":    1.0,
    "morae":    1.5,
    "groups":   0.5,
    "readings": 0.5,
    "sim":      1.0,
}

BANDS: dict[str, tuple[float, float]] = {   # (centre, tolerance) per set
    "strokes":  (25.0, 2.0),
    "morae":    (10.0, 1.0),
    "groups":   (12.0, 2.0),
    "readings": (13.0, 2.0),
}

SIM_MAX_PAIR = 0.55       # no pair within a set above this
SIM_MAX_MEAN = 0.12       # mean similarity within a set
MAX_PER_CLUSTER = 1       # kanji of the same semantic cluster per set
QUALITY_WEIGHT = 0.35     # weight of the absolute term (3D anchoring and confusion)
SUBST_STROKE_TOL = 2      # a substitute is valid if it differs by ≤ this in strokes


@dataclass
class Model:
    kanji: list[Kanji]
    n: int
    sim: np.ndarray
    perim: np.ndarray
    incompatible: list[int] = field(default_factory=list)   # hard + cluster
    hard_clash: list[int] = field(default_factory=list)     # reading/meaning/shape
    selectable: np.ndarray = field(default_factory=lambda: np.array([]))
    is_current: np.ndarray = field(default_factory=lambda: np.array([]))
    strokes: np.ndarray = field(default_factory=lambda: np.array([]))
    metric_cols: dict[str, np.ndarray] = field(default_factory=dict)
    suffix_min: dict[str, np.ndarray] = field(default_factory=dict)
    suffix_max: dict[str, np.ndarray] = field(default_factory=dict)
    scale: dict[str, float] = field(default_factory=dict)
    index: dict[str, int] = field(default_factory=dict)


def build_model(kanji: list[Kanji], allowed: set[str], g: Glyphs) -> Model:
    n = len(kanji)
    chars = [k.char for k in kanji]
    sim = g.similarity_matrix(chars)
    perim = np.array([g.perim(c) for c in chars])

    m = Model(kanji=kanji, n=n, sim=sim, perim=perim,
              index={k.char: i for i, k in enumerate(kanji)})
    m.selectable = np.array([(k.discovery in allowed) and not k.excluded
                             for k in kanji])
    m.is_current = np.array([k.char in CURRENT_FLAT for k in kanji])
    m.strokes = np.array([k.strokes for k in kanji])

    # ── incompatibilities ──────────────────────────────────────────────────
    # HARD: they break a trial type.
    #   same reading       → two identical options in T3
    #   same meaning       → two identical options in T1 and T2
    #   shape > threshold  → T1 and T2 become almost undecidable
    # SOFT (semantic cluster): the T2 distractors become ambiguous.
    #   It is the "tree versus bamboo" objection turned into a rule. It counts
    #   for forming sets, but not for judging whether a substitute is valid.
    m.incompatible = [0] * n
    m.hard_clash = [0] * n
    for i, j in itertools.combinations(range(n), 2):
        a, b = kanji[i], kanji[j]
        hard = (a.reading == b.reading
                or a.meaning == b.meaning
                or sim[i, j] > SIM_MAX_PAIR)
        soft = MAX_PER_CLUSTER == 1 and a.cluster == b.cluster
        if hard:
            m.hard_clash[i] |= 1 << j
            m.hard_clash[j] |= 1 << i
        if hard or soft:
            m.incompatible[i] |= 1 << j
            m.incompatible[j] |= 1 << i

    m.metric_cols = {
        "strokes":  np.array([k.strokes for k in kanji], dtype=float),
        "perim":    perim,
        "morae":    np.array([k.morae for k in kanji], dtype=float),
        "groups":   np.array([k.groups for k in kanji], dtype=float),
        "readings": np.array([k.readings for k in kanji], dtype=float),
    }

    # Suffix tables for the DFS pruning bounds:
    #   suffix_min[name][i, r] = sum of the r SMALLEST values among kanji[i:]
    #   suffix_max[name][i, r] = sum of the r LARGEST values among kanji[i:]
    # Relaxation (ignores incompatibilities), so the bound is valid and O(1).
    for name, col in m.metric_cols.items():
        lo = np.zeros((n + 1, SET_SIZE + 1))
        hi = np.zeros((n + 1, SET_SIZE + 1))
        for i in range(n + 1):
            tail = np.sort(col[i:])
            for r in range(1, SET_SIZE + 1):
                lo[i, r] = tail[:r].sum() if len(tail) >= r else np.inf
                hi[i, r] = tail[-r:].sum() if len(tail) >= r else -np.inf
        m.suffix_min[name] = lo
        m.suffix_max[name] = hi

    for name, col in m.metric_cols.items():
        m.scale[name] = max(SET_SIZE * float(col.mean()), 1e-9)
    m.scale["sim"] = 1.0
    return m


# ═══════════════════════════════════════════════════════════════════════════
# 4 · STAGE 1 — ENUMERATION OF FEASIBLE SETS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class FeasibleSet:
    mask: int
    members: tuple[int, ...]
    vec: np.ndarray           # weighted, normalized metric vector
    quality: float            # absolute term ≥ 0 (lower = better)
    sim_mean: float
    sim_max: float
    raw: dict[str, float]
    minidx: int
    n_current: int            # how many of its 5 are in the current design


def enumerate_feasible(m: Model, verbose: bool = True) -> list[FeasibleSet]:
    out: list[FeasibleSet] = []
    cols = m.metric_cols
    stats = {"nodes": 0, "pruned_band": 0, "rejected_band": 0, "rejected_sim": 0}
    band_names = list(BANDS)
    iu = np.triu_indices(SET_SIZE, 1)

    def band_reachable(sums: dict[str, float], start: int, slots: int) -> bool:
        for name in band_names:
            centre, tol = BANDS[name]
            if slots == 0:
                if abs(sums[name] - centre) > tol:
                    return False
                continue
            if (sums[name] + m.suffix_min[name][start, slots] > centre + tol
                    or sums[name] + m.suffix_max[name][start, slots] < centre - tol):
                return False
        return True

    def emit(members: tuple[int, ...], mask: int, sums: dict[str, float]) -> None:
        # Final band validation. band_reachable() only checks that the band
        # is still REACHABLE with the remaining kanji; the complete set has
        # to be verified here.
        for name, (centre, tol) in BANDS.items():
            if abs(sums[name] - centre) > tol:
                stats["rejected_band"] += 1
                return
        idx = list(members)
        pair = m.sim[np.ix_(idx, idx)][iu]
        smean, smax = float(pair.mean()), float(pair.max())
        if smean > SIM_MAX_MEAN:
            stats["rejected_sim"] += 1
            return
        raw = dict(sums)
        raw["sim"] = smean
        vec = np.array([METRIC_WEIGHTS[k] * raw[k] / m.scale[k]
                        for k in METRIC_WEIGHTS])
        img = float(np.mean([m.kanji[i].imageability for i in idx]))
        # Absolute quality: additive per set and ≥ 0, which is what keeps
        # the stage 2 lower bound valid.
        quality = QUALITY_WEIGHT * ((5.0 - img) / 4.0 + max(smax, 0.0))
        out.append(FeasibleSet(mask, members, vec, quality, smean, smax, raw,
                               min(members), int(m.is_current[idx].sum())))

    def dfs(start: int, chosen: tuple[int, ...], mask: int, blocked: int,
            clusters: frozenset[str], sums: dict[str, float]) -> None:
        stats["nodes"] += 1
        slots = SET_SIZE - len(chosen)
        if slots == 0:
            emit(chosen, mask, sums)
            return
        if not band_reachable(sums, start, slots):
            stats["pruned_band"] += 1
            return
        if m.n - start < slots:
            return
        for i in range(start, m.n - slots + 1):
            if not m.selectable[i] or blocked >> i & 1:
                continue
            k = m.kanji[i]
            if MAX_PER_CLUSTER == 1 and k.cluster in clusters:
                continue
            dfs(i + 1, chosen + (i,), mask | (1 << i),
                blocked | m.incompatible[i], clusters | {k.cluster},
                {name: sums[name] + cols[name][i] for name in cols})

    dfs(0, (), 0, 0, frozenset(), {name: 0.0 for name in cols})

    if verbose:
        n_sel = int(m.selectable.sum())
        print(f"  nodes explored        {stats['nodes']:>10,}")
        print(f"  pruned by band        {stats['pruned_band']:>10,}")
        print(f"  out of band           {stats['rejected_band']:>10,}")
        print(f"  discarded by sim.     {stats['rejected_sim']:>10,}")
        print(f"  feasible sets         {len(out):>10,}"
              f"   of C({n_sel},{SET_SIZE}) = {comb(n_sel, SET_SIZE):,}")
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 5 · OBJECTIVE AND TRIPLE CONSTRAINTS
# ═══════════════════════════════════════════════════════════════════════════

def balance_only(a: FeasibleSet, b: FeasibleSet, c: FeasibleSet) -> float:
    V = np.stack([a.vec, b.vec, c.vec])
    return float((V.max(axis=0) - V.min(axis=0)).sum())


def objective(a: FeasibleSet, b: FeasibleSet, c: FeasibleSet) -> float:
    """Σ_m w_m·(max−min)/scale  +  Σ_s quality(s)."""
    return balance_only(a, b, c) + a.quality + b.quality + c.quality


def substitutability(m: Model, sets: list[FeasibleSet]) -> tuple[bool, list[str]]:
    """Does each experimental kanji have a valid substitute in the leftovers?

    A leftover kanji r can replace e within set S if:
      · |strokes(r) − strokes(e)| ≤ SUBST_STROKE_TOL  (§13.2: comparable
        complexity)
      · r has no hard clash with any member of S except, at most, e itself
        — because after the substitution e is no longer there.
    Returns (satisfied, list of kanji without a substitute).
    """
    used = 0
    for s in sets:
        used |= s.mask
    leftovers = [i for i in range(m.n) if not (used >> i & 1)]
    orphans: list[str] = []
    for s in sets:
        for e in s.members:
            rest = s.mask & ~(1 << e)
            ok = False
            for r in leftovers:
                if abs(int(m.strokes[r]) - int(m.strokes[e])) > SUBST_STROKE_TOL:
                    continue
                if m.hard_clash[r] & rest:
                    continue
                ok = True
                break
            if not ok:
                orphans.append(m.kanji[e].char)
    return (not orphans), orphans


# ═══════════════════════════════════════════════════════════════════════════
# 6 · STAGE 2 — EXACT BRANCH AND BOUND
# ═══════════════════════════════════════════════════════════════════════════

def seed_incumbent(sets, masks, V, Q, ncur, accept, anchors=400, width=24,
                   seed=0) -> tuple[float, tuple[int, int, int] | None]:
    """Initial upper bound via directed construction.

    It matters more than it seems: if the incumbent starts at infinity, so does
    the radius of the first k-d tree query, the ball returns everything and
    the branch and bound degenerates into brute force. With hard constraints
    on the triple (continuity, substitutability) random sampling almost
    never hits a valid triple, so here one is built on purpose:

      · anchors are traversed by descending continuity and ascending
        quality, which is where the solutions satisfying --keep live
      · for each anchor the `width` nearest disjoint sets under the L1
        bound are taken, and for each pair the `width` nearest to the midpoint
      · the best triple that passes `accept` is returned

    It guarantees nothing; only a small, feasible initial radius.
    """
    n = len(sets)
    if n < N_SETS:
        return float("inf"), None
    best, best_tri = float("inf"), None
    order = np.lexsort((Q, -ncur))[:anchors]
    for i in order:
        i = int(i)
        free = np.flatnonzero((masks & masks[i]) == 0)
        if free.size == 0:
            continue
        d = np.abs(V[free] - V[i]).sum(axis=1) + Q[free]
        near = free[np.argsort(d)[:width]]
        for j in near:
            j = int(j)
            free2 = np.flatnonzero((masks & (masks[i] | masks[j])) == 0)
            if free2.size == 0:
                continue
            lo = np.minimum(V[i], V[j])
            hi = np.maximum(V[i], V[j])
            J = ((np.maximum(V[free2], hi) - np.minimum(V[free2], lo)).sum(axis=1)
                 + Q[i] + Q[j] + Q[free2])
            for pos in np.argsort(J)[:width]:
                k = int(free2[pos])
                if J[pos] >= best:
                    break
                tri = tuple(sorted((i, j, k)))
                if accept(tri):
                    best, best_tri = float(J[pos]), tri
                    break
    return best, best_tri


def search(sets: list[FeasibleSet], accept, top: int = 1, verbose: bool = True,
           time_limit: float = 0.0, keep: int = 0):
    """Exact branch and bound over disjoint triples that satisfy `accept`.

    `accept(tri) -> bool` filters constraints that depend on the whole triple
    (substitutability, continuity). The incumbent only takes values from
    accepted triples, so the pruning remains correct.

    Returns (results, proven). `proven` is False only if `time_limit` ran
    out before the traversal finished: in that case the best result is
    still valid, but no longer has an optimality guarantee.
    """
    n = len(sets)
    if n < N_SETS:
        return [], True

    masks_np = np.array([s.mask for s in sets], dtype=np.uint64)
    V = np.stack([s.vec for s in sets])
    Q = np.array([s.quality for s in sets])
    ncur = np.array([s.n_current for s in sets])
    minidx = np.array([s.minidx for s in sets])
    qmin = float(Q.min())
    max_ncur = int(ncur.max()) if ncur.size else 0
    tree = cKDTree(V)

    heap: list[tuple[float, tuple[int, int, int]]] = []

    def push(J: float, tri: tuple[int, int, int]) -> float:
        if any(t == tri for _, t in heap):
            return incumbent     # the seeded triple, found again by the traversal
        heapq.heappush(heap, (-J, tri))
        while len(heap) > top:
            heapq.heappop(heap)
        return -heap[0][0] if len(heap) == top else incumbent

    incumbent, seed_tri = seed_incumbent(sets, masks_np, V, Q, ncur, accept)
    if seed_tri is not None:
        heapq.heappush(heap, (-incumbent, seed_tri))
    # With --top N the radius must be the N-th best, not the best: until the
    # heap holds N triples, nothing may be pruned by the seed. Before 29
    # September the seed's value was used as the radius from the start, so
    # when the seed happened to be the optimum (it is built near the split in
    # force, which is now the optimum) the "next best" list came out empty.
    if top > 1 and len(heap) < top:
        incumbent = float("inf")

    stats = {"anchors": 0, "pairs": 0, "triples": 0, "rejected": 0}
    t0 = time.time()
    proven = True

    # Traverse the best-quality sets first: finds good incumbents
    # earlier and shrinks the radius as soon as possible.
    for ai in np.argsort(Q):
        if time_limit and time.time() - t0 > time_limit:
            proven = False
            break
        stats["anchors"] += 1
        r_a = incumbent - Q[ai] - 2.0 * qmin
        if r_a <= 0:
            continue
        nb = np.fromiter(tree.query_ball_point(V[ai], r=r_a, p=1), dtype=np.int64)
        if nb.size == 0:
            continue
        ok = (minidx[nb] > minidx[ai]) & ((masks_np[nb] & masks_np[ai]) == 0)
        if keep:
            # continuity, vectorized: with the best possible third set,
            # can K still be reached?
            ok &= (ncur[ai] + ncur[nb] + max_ncur) >= keep
        nb = nb[ok]
        if nb.size == 0:
            continue
        lb = np.abs(V[nb] - V[ai]).sum(axis=1) + Q[nb] + Q[ai] + qmin
        order = np.argsort(lb)
        nb, lb = nb[order], lb[order]
        nb_set = set(nb.tolist())

        for pos in range(nb.size):
            if lb[pos] >= incumbent:
                break            # sorted: the rest cannot improve either
            bi = int(nb[pos])
            stats["pairs"] += 1
            r_b = incumbent - Q[ai] - Q[bi] - qmin
            if r_b <= 0:
                continue
            nc = np.fromiter(
                (x for x in tree.query_ball_point(V[bi], r=r_b, p=1) if x in nb_set),
                dtype=np.int64)
            if nc.size == 0:
                continue
            ab = masks_np[ai] | masks_np[bi]
            ok = (minidx[nc] > minidx[bi]) & ((masks_np[nc] & ab) == 0)
            if keep:
                ok &= (ncur[ai] + ncur[bi] + ncur[nc]) >= keep
            nc = nc[ok]
            if nc.size == 0:
                continue
            lo = np.minimum(V[ai], V[bi])
            hi = np.maximum(V[ai], V[bi])
            J = ((np.maximum(V[nc], hi) - np.minimum(V[nc], lo)).sum(axis=1)
                 + Q[ai] + Q[bi] + Q[nc])
            stats["triples"] += int(nc.size)
            for gi in np.argsort(J):
                if J[gi] >= incumbent:
                    break
                tri = (int(ai), bi, int(nc[gi]))
                if not accept(tri):
                    stats["rejected"] += 1
                    continue
                incumbent = push(float(J[gi]), tri)

    if verbose:
        print(f"  anchors traversed     {stats['anchors']:>10,} of {n:,}")
        print(f"  pairs evaluated       {stats['pairs']:>10,}")
        print(f"  triples evaluated     {stats['triples']:>10,}")
        print(f"  triples rejected      {stats['rejected']:>10,}"
              f"   (substitutability / continuity)")
        print(f"  search time           {time.time() - t0:>10.1f} s")
        if not proven:
            print("  ⚠ time limit reached: the result is valid "
                  "but optimality is NOT proven")
    return sorted(((-j, t) for j, t in heap)), proven


# ═══════════════════════════════════════════════════════════════════════════
# 7 · OPTIONAL CP-SAT BACKEND
# ═══════════════════════════════════════════════════════════════════════════

def verify_with_cpsat(m: Model, best_balance: float, scale: int = 10_000) -> str:
    """Equivalent integer model, as a second opinion on the optimum.

    It covers the linear part of the objective (everything except the
    similarity and quality terms, which are quadratic in the decision
    variables), so its optimum is a LOWER BOUND on the full balance.
    """
    try:
        from ortools.sat.python import cp_model
    except ImportError:
        return ("OR-Tools not installed — verification skipped "
                "(pip install ortools)")

    mod = cp_model.CpModel()
    sel = [i for i in range(m.n) if m.selectable[i]]
    x = {i: [mod.NewBoolVar(f"x{i}_{s}") for s in range(N_SETS)] for i in sel}

    for i in sel:
        mod.AddAtMostOne(x[i])
    for s in range(N_SETS):
        mod.Add(sum(x[i][s] for i in sel) == SET_SIZE)
    for i, j in itertools.combinations(sel, 2):
        if m.incompatible[i] >> j & 1:
            for s in range(N_SETS):
                mod.Add(x[i][s] + x[j][s] <= 1)
    for s in range(N_SETS - 1):     # symmetry breaking by minimum index
        for i in sel:
            mod.Add(sum(x[j][s] for j in sel if j <= i) >= x[i][s + 1])

    terms = []
    for name, w in METRIC_WEIGHTS.items():
        if name == "sim":
            continue
        col = m.metric_cols[name]
        coef = {i: int(round(scale * w * col[i] / m.scale[name])) for i in sel}
        sums = []
        for s in range(N_SETS):
            v = mod.NewIntVar(0, scale * 200, f"{name}{s}")
            mod.Add(v == sum(coef[i] * x[i][s] for i in sel))
            sums.append(v)
            if name in BANDS:
                centre, tol = BANDS[name]
                unit = scale * w / m.scale[name]
                mod.Add(v >= int((centre - tol) * unit))
                mod.Add(v <= int((centre + tol) * unit))
        mx = mod.NewIntVar(0, scale * 200, f"mx_{name}")
        mn = mod.NewIntVar(0, scale * 200, f"mn_{name}")
        mod.AddMaxEquality(mx, sums)
        mod.AddMinEquality(mn, sums)
        terms.append(mx - mn)

    mod.Minimize(sum(terms))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 180.0
    solver.parameters.num_search_workers = 8
    st = solver.Solve(mod)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return "CP-SAT found no feasible solution"
    lb = solver.ObjectiveValue() / scale
    tag = "optimal" if st == cp_model.OPTIMAL else "feasible"
    ok = "consistent" if lb <= best_balance + 1e-6 else "INCONSISTENT"
    return (f"CP-SAT ({tag}) on the linear relaxation of the balance: {lb:.4f}. "
            f"The balance of the optimum found is {best_balance:.4f}. "
            f"Relaxation ≤ full must hold → {ok}.")


# ═══════════════════════════════════════════════════════════════════════════
# 8 · REPORT
# ═══════════════════════════════════════════════════════════════════════════

def describe(m: Model, sets: list[FeasibleSet], label: str = "") -> None:
    hdr = (f"{'Set':<4}{'kanji':<9}{'strokes':>7}{'C_perim':>9}{'morae':>7}"
           f"{'groups':>8}{'read.':>7}{'sim_med':>9}{'sim_max':>9}{'img':>6}")
    print(hdr)
    print("-" * len(hdr))
    for tag, s in zip("ABC", sets):
        img = np.mean([m.kanji[i].imageability for i in s.members])
        chars = "".join(m.kanji[i].char for i in s.members)
        print(f"{tag:<4}{chars:<9}{s.raw['strokes']:>7.0f}{s.raw['perim']:>9.0f}"
              f"{s.raw['morae']:>7.0f}{s.raw['groups']:>8.0f}"
              f"{s.raw['readings']:>7.0f}{s.sim_mean:>+9.3f}"
              f"{s.sim_max:>+9.3f}{img:>6.1f}")
    print(f"{'':<13}", end="")
    for name, width in (("strokes", 7), ("perim", 9), ("morae", 7),
                        ("groups", 8), ("readings", 7)):
        vals = [s.raw[name] for s in sets]
        print(f"{'Δ' + format(max(vals) - min(vals), '.0f'):>{width}}", end="")
    sims = [s.sim_mean for s in sets]
    print(f"{'Δ' + format(max(sims) - min(sims), '.3f'):>9}")
    kinds: dict[str, int] = {}
    for s in sets:
        for i in s.members:
            kinds[m.kanji[i].discovery] = kinds.get(m.kanji[i].discovery, 0) + 1
    mech = " ".join(f"{k}×{v}" for k, v in sorted(kinds.items()))
    keep = sum(s.n_current for s in sets)
    print(f"  mechanisms: {mech}")
    print(f"  balance {balance_only(*sets):.4f}   quality "
          f"{sum(s.quality for s in sets):.4f}   objective {objective(*sets):.4f}"
          f"   keeps {keep}/15   {label}")


def report_reserve(m: Model, sets: list[FeasibleSet]) -> None:
    used = 0
    for s in sets:
        used |= s.mask
    leftovers = [i for i in range(m.n) if not (used >> i & 1) and m.selectable[i]]
    exp = [i for s in sets for i in s.members]

    print(f"{'K':<3}{'reading':>9}{'st':>4}{'mo':>4}{'lesson':>9}"
          f"{'worst sim':>10}   can substitute for")
    for r in sorted(leftovers, key=lambda i: (m.kanji[i].strokes, m.kanji[i].char)):
        targets = []
        for s in sets:
            for e in s.members:
                if abs(int(m.strokes[r]) - int(m.strokes[e])) > SUBST_STROKE_TOL:
                    continue
                if m.hard_clash[r] & (s.mask & ~(1 << e)):
                    continue
                targets.append(m.kanji[e].char)
        worst = max((m.sim[r, e] for e in exp), default=0.0)
        k = m.kanji[r]
        shown = "".join(targets) if targets else "— none"
        print(f"{k.char:<3}{k.reading:>9}{k.strokes:>4}{k.morae:>4}"
              f"{k.lesson:>9}{worst:>+10.3f}   {shown}")

    ok, orphans = substitutability(m, sets)
    if ok:
        print("\n  all experimental kanji have a valid substitute")
    else:
        print(f"\n  NO SUBSTITUTE: {' '.join(orphans)}")


def as_feasible(m: Model, chars: list[str]) -> FeasibleSet | None:
    try:
        idx = tuple(sorted(m.index[c] for c in chars))
    except KeyError:
        return None
    raw = {name: float(m.metric_cols[name][list(idx)].sum())
           for name in m.metric_cols}
    pair = m.sim[np.ix_(list(idx), list(idx))][np.triu_indices(len(idx), 1)]
    raw["sim"] = float(pair.mean())
    vec = np.array([METRIC_WEIGHTS[k] * raw[k] / m.scale[k] for k in METRIC_WEIGHTS])
    img = float(np.mean([m.kanji[i].imageability for i in idx]))
    q = QUALITY_WEIGHT * ((5.0 - img) / 4.0 + max(float(pair.max()), 0.0))
    mask = 0
    for i in idx:
        mask |= 1 << i
    return FeasibleSet(mask, idx, vec, q, float(pair.mean()), float(pair.max()),
                       raw, min(idx), int(m.is_current[list(idx)].sum()))


def violations(m: Model, s: FeasibleSet) -> list[str]:
    out = []
    for name, (centre, tol) in BANDS.items():
        if abs(s.raw[name] - centre) > tol:
            out.append(f"{name} {s.raw[name]:.0f} (band {centre:.0f}±{tol:.0f})")
    if s.sim_mean > SIM_MAX_MEAN:
        out.append(f"sim mean {s.sim_mean:+.3f} (max {SIM_MAX_MEAN})")
    if s.sim_max > SIM_MAX_PAIR:
        out.append(f"sim max {s.sim_max:+.3f} (max {SIM_MAX_PAIR})")
    clusters = [m.kanji[i].cluster for i in s.members]
    dup = {c for c in clusters if clusters.count(c) > 1}
    if dup:
        out.append(f"repeated cluster: {', '.join(sorted(dup))}")
    return out


# ═══════════════════════════════════════════════════════════════════════════

def solve(m: Model, feasible: list[FeasibleSet], keep: int, subst: bool,
          top: int, verbose: bool = True, time_limit: float = 0.0):
    # Cheap continuity pruning before the B&B: a set is only useful if, with
    # two perfect partners, it can still reach K.
    max_cur = max((s.n_current for s in feasible), default=0)
    pool = feasible
    if keep:
        pool = [s for s in feasible if s.n_current + 2 * max_cur >= keep]
        if verbose and len(pool) < len(feasible):
            print(f"  preselection by continuity: {len(pool):,} of "
                  f"{len(feasible):,} sets")

    def accept(tri) -> bool:
        a, b, c = (pool[i] for i in tri)
        if keep and a.n_current + b.n_current + c.n_current < keep:
            return False
        if subst and not substitutability(m, [a, b, c])[0]:
            return False
        return True

    res, proven = search(pool, accept, top=top, verbose=verbose,
                         time_limit=time_limit, keep=keep)
    return pool, res, proven


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--font", default=DEFAULT_FONT)
    ap.add_argument("--top", type=int, default=5,
                    help="how many splits to report (the first is the optimum)")
    ap.add_argument("--keep-current", type=int, default=0, metavar="K",
                    help="require keeping at least K of the 15 current kanji")
    ap.add_argument("--discovery", nargs="+", default=["picture"],
                    choices=sorted(DISCOVERY_KINDS), metavar="TIPO",
                    help="allowed discovery mechanisms: "
                         + ", ".join(DISCOVERY_KINDS))
    ap.add_argument("--allow-contextual", action="store_true",
                    help="shortcut to add 'context' to --discovery (allows 私)")
    ap.add_argument("--no-substitutability", action="store_true",
                    help="do not require each kanji to have a substitute in the reserve")
    ap.add_argument("--sweep", action="store_true",
                    help="continuity ↔ quality curve for several K")
    ap.add_argument("--sweep-points", type=int, nargs="+",
                    default=[0, 5, 8, 10, 12, 13, 14, 15], metavar="K",
                    help="K values for the sweep")
    ap.add_argument("--time-limit", type=float, default=90.0, metavar="S",
                    help="seconds per search; 0 = no limit (default 90)")
    ap.add_argument("--cpsat", action="store_true",
                    help="second opinion with OR-Tools CP-SAT, if installed")
    args = ap.parse_args()

    try:
        g = Glyphs(args.font)
    except OSError:
        print(f"Could not open the font: {args.font}", file=sys.stderr)
        return 2

    t0 = time.time()
    allowed = set(args.discovery)
    if args.allow_contextual:
        allowed.add("context")
    m = build_model(UNIVERSE, allowed, g)
    g.save_cache()
    subst = not args.no_substitutability

    by_kind = {k: sum(1 for x in UNIVERSE
                      if x.discovery == k and not x.excluded)
               for k in DISCOVERY_KINDS}
    print(f"Universe: {int(m.selectable.sum())} eligible kanji of {m.n} "
          f"in Basic Kanji Book Vol. 1")
    for kind, desc in DISCOVERY_KINDS.items():
        mark = "✓" if kind in allowed else " "
        print(f"  [{mark}] {kind:<9} {by_kind[kind]:>2} kanji · {desc}")
    excl = [x.char for x in UNIVERSE if x.excluded]
    if excl:
        print(f"  out of the official pool: {' '.join(excl)} (plus 生, not modelled)")
    print(f"Constraints: bands §5 · cluster ≤{MAX_PER_CLUSTER}/set · "
          f"sim pair ≤{SIM_MAX_PAIR} · sim mean ≤{SIM_MAX_MEAN}"
          f"{' · substitutability' if subst else ''}"
          f"{f' · keep ≥{args.keep_current}' if args.keep_current else ''}\n")

    print("Stage 1 · enumeration of feasible sets")
    feasible = enumerate_feasible(m)
    print()
    if not feasible:
        print("No set satisfies the constraints.")
        return 1

    # ── continuity sweep ───────────────────────────────────────────────────
    if args.sweep:
        print("Continuity ↔ quality curve")
        print("How much it costs, in balance, to keep K kanji from the current design.\n")
        print(f"{'keeps ≥':>11}{'objective':>10}{'balance':>9}{'':>3}  split")
        print("-" * 74)
        base = None
        for K in args.sweep_points:
            pool, res, proven = solve(m, feasible, K, subst, 1, verbose=False,
                                      time_limit=args.time_limit)
            if not res:
                print(f"{K:>11}{'—':>10}{'—':>9}     no feasible solution")
                continue
            J, tri = res[0]
            ss = [pool[i] for i in tri]
            if base is None:
                base = J
            chars = " ".join("".join(m.kanji[i].char for i in s.members) for s in ss)
            mark = "  " if proven else " ~"
            print(f"{K:>11}{J:>10.4f}{balance_only(*ss):>9.4f}{mark:>3}  {chars}"
                  f"  (+{100 * (J - base) / base:.0f} %)")
        print("\n  ~ = time limit reached, optimality not proven")
        print(f"\ntotal {time.time() - t0:.1f} s")
        return 0

    print("Stage 2 · branch and bound over disjoint triples")
    pool, results, proven = solve(m, feasible, args.keep_current, subst,
                                  max(1, args.top), time_limit=args.time_limit)
    print()
    if not results:
        print("No split satisfies all the constraints. "
              "Try a lower --keep-current or --no-substitutability.")
        return 1

    J, tri = results[0]
    best = [pool[i] for i in tri]
    print("═" * 78)
    print("OPTIMAL SPLIT")
    print("═" * 78)
    describe(m, best, "← proven optimum" if proven else "← best found (no proof)")
    print()

    if len(results) > 1:
        print(f"The next {len(results) - 1} best:\n")
        for rank, (Jk, trik) in enumerate(results[1:], start=2):
            ss = [pool[i] for i in trik]
            chars = "  ".join("".join(m.kanji[i].char for i in s.members) for s in ss)
            keep = sum(s.n_current for s in ss)
            print(f"  {rank:>2}. {chars}   objective {Jk:.4f}"
                  f"  (+{100 * (Jk - J) / J:.1f} %)  keeps {keep}/15")
        print()

    print("─" * 78)
    print("COMPARISON WITH THE CURRENT SPLIT")
    print("─" * 78)
    cur = [as_feasible(m, s) for s in CURRENT]
    if all(c is not None for c in cur):
        describe(m, cur, "← current design")
        cJ = objective(*cur)
        print(f"  the optimum improves the objective by {100 * (cJ - J) / cJ:.1f} %")
        for tag, s in zip("ABC", cur):
            v = violations(m, s)
            if v:
                print(f"  set {tag} violates: {'; '.join(v)}")
        ok, orphans = substitutability(m, cur)
        if not ok:
            print(f"  no substitute in reserve: {' '.join(orphans)}")
    print()

    print("─" * 78)
    print("DERIVED RESERVE POOL")
    print("─" * 78)
    report_reserve(m, best)
    print()

    if args.cpsat:
        print("─" * 78)
        print("SECOND OPINION")
        print("─" * 78)
        print("  " + verify_with_cpsat(m, balance_only(*best)))
        print()

    print(f"total {time.time() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

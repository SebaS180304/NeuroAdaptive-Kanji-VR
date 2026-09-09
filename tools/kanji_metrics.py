#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kanji_metrics.py — verificación de balance de los sets experimentales de kanji.

Proyecto NeuroAdaptive VR Kanji, Fase 2.
Documento de referencia: claude/Metricas_Dificultad_Kanji_Fase2.md

Qué hace
--------
Calcula seis métricas de dificultad sobre los sets A/B/C y comprueba que cada
set cae dentro de las bandas de tolerancia acordadas. Devuelve código de salida
1 si alguna banda se sale, para poder correrlo en CI o en un pre-commit.

    python3 kanji_metrics.py            # tabla + veredicto
    python3 kanji_metrics.py --pool     # además, matriz de colisiones del pool
    python3 kanji_metrics.py --font RUTA.ttc

Métricas
--------
1. Trazos                  — dato de contenido (KANJI[k].strokes)
2. Complejidad perimétrica — P²/A sobre el glifo renderizado (Pelli et al. 2006)
3. Moras de la lectura     — dato de contenido
4. Grupos de ensamblaje    — dato de contenido
5. Nº de lecturas comunes  — dato de contenido
6. Confusabilidad gráfica  — correlación de Pearson entre mapas suavizados

Las métricas 2 y 6 dependen de la tipografía. Usar la fuente definitiva del
Learning Board antes de congelar los sets.

Requisitos: pillow, numpy. Sin red.
"""

from __future__ import annotations
import argparse, itertools, os, pathlib, sys
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

DEFAULT_FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

# Raiz del repositorio. KANJI_REPO_ROOT gana si esta definida; si no, se deduce
# de la ubicacion de este script, que vive en tools/.
#
# La variable existe para el caso del contenedor: dentro de Docker el script se
# ve en /repo/tools/ solo si el bind mount ocurrio. Cuando no ocurre --Docker
# Desktop sin permiso de file sharing sobre la carpeta, tipicamente-- la
# deduccion apunta a un /repo vacio y el fallo aparece como un "no such file or
# directory" que no dice nada de la causa real.
REPO_ROOT = pathlib.Path(
    os.environ.get("KANJI_REPO_ROOT") or pathlib.Path(__file__).resolve().parent.parent
).resolve()

# El contrato de contenido se genera DIRECTAMENTE donde Unity lo consume.
# No se genera aqui y se copia alla: dos copias del mismo hecho es exactamente
# la divergencia que Planteamiento_Fase2_M2.md documenta cuatro veces.
# Assets/Resources/ y no StreamingAssets/ porque Resources.Load<TextAsset> es
# sincrono e identico en Editor, Quest Link y un build de Android; en
# StreamingAssets el archivo vive dentro del APK y hay que leerlo con
# UnityWebRequest, con codigo distinto segun plataforma.
DEFAULT_EXPORT = REPO_ROOT / "unity-client" / "Assets" / "Resources" / "kanji_content.json"


# --------------------------------------------------------------------------- #
# Contenido
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Kanji:
    reading: str        # lectura objetivo
    strokes: int
    morae: int
    groups: int         # grupos de segmentación de ensamblaje
    readings: int       # nº de lecturas comunes del carácter
    meaning: str
    lesson: str = ""    # lección de Basic Kanji Book Vol.1; "P" = lección pictográfica


KANJI: dict[str, Kanji] = {
    # --- set A --- (todos L1/L2, pictográficos)
    "日": Kanji("ひ",    4, 1, 2, 4, "sun",      "L1-P"),
    "山": Kanji("やま",  3, 2, 2, 2, "mountain",  "L1-P"),
    "車": Kanji("くるま", 7, 3, 3, 2, "car",    "L1-P"),
    "女": Kanji("おんな", 3, 3, 3, 4, "woman",    "L2-P"),
    "学": Kanji("ガク",  8, 2, 3, 2, "study",  "L2-P"),
    # --- set B ---
    "月": Kanji("つき",  4, 2, 2, 3, "moon",     "L1-P"),
    "川": Kanji("かわ",  3, 2, 3, 2, "river",      "L1-P"),
    "門": Kanji("もん",  8, 2, 2, 2, "gate",   "L1-P"),
    "子": Kanji("こ",    3, 1, 2, 3, "child",     "L2-P"),
    "私": Kanji("わたし", 7, 3, 2, 2, "I",       "L2"),   # en L2 pero SIN derivación
    # --- set C ---
    "木": Kanji("き",    4, 1, 2, 3, "tree",    "L1-P"),
    "田": Kanji("た",    5, 1, 2, 2, "rice field",  "L1-P"),
    "金": Kanji("きん",  8, 2, 3, 3, "gold",      "L2-P"),
    "人": Kanji("ひと",  2, 2, 2, 3, "person",  "L1-P"),
    "先": Kanji("さき",  6, 2, 2, 2, "ahead",  "L2-P"),
    # --- reserva y candidatos verificados contra el libro ---
    "口": Kanji("くち",  3, 2, 2, 2, "mouth",     "L1-P"),
    "火": Kanji("ひ",    4, 1, 3, 2, "fire",    "L2-P"),
    "水": Kanji("みず",  4, 2, 2, 2, "water",     "L2-P"),
    "土": Kanji("つち",  3, 2, 2, 2, "ground",   "L2-P"),
    "目": Kanji("め",    5, 1, 2, 2, "eye",      "L6-P"),
    "耳": Kanji("みみ",  6, 2, 2, 2, "ear",    "L6-P"),
    "手": Kanji("て",    4, 1, 2, 2, "hand",     "L6-P"),
    "足": Kanji("あし",  7, 2, 3, 3, "leg",      "L6-P"),
    "雨": Kanji("あめ",  8, 2, 3, 2, "rain",   "L6-P"),
    "竹": Kanji("たけ",  6, 2, 2, 2, "bamboo",    "L6-P"),
    "米": Kanji("こめ",  6, 2, 3, 3, "rice",    "L6-P"),
    "貝": Kanji("かい",  7, 2, 2, 2, "shellfish",   "L6-P"),
    "石": Kanji("いし",  5, 2, 2, 2, "stone",   "L6-P"),
    "糸": Kanji("いと",  6, 2, 2, 2, "thread",     "L6-P"),
    "牛": Kanji("うし",  4, 2, 2, 2, "cow",     "L7-P"),
    "肉": Kanji("にく",  6, 2, 2, 1, "meat",    "L7-P"),
    "花": Kanji("はな",  7, 2, 3, 2, "flower",     "L7-P"),
    "物": Kanji("もの",  8, 2, 3, 3, "thing",     "L7-P"),
    "魚": Kanji("さかな", 11, 3, 3, 2, "fish",     "L7-P"),
    "鳥": Kanji("とり", 11, 2, 3, 2, "bird",      "L7-P"),
    "馬": Kanji("うま", 10, 2, 3, 2, "horse",  "L7-P"),
    "中": Kanji("なか",  4, 2, 2, 3, "middle",   "L4"),   # signo, no pictográfico
    "本": Kanji("ほん",  5, 2, 2, 2, "book",    "L4"),
    "上": Kanji("うえ",  3, 2, 2, 5, "above",   "L4"),
    "下": Kanji("した",  3, 2, 2, 5, "below",    "L4"),
    "力": Kanji("ちから", 2, 3, 2, 3, "power",   "L4"),
    "茶": Kanji("ちゃ",  9, 2, 3, 2, "tea",       "L7-P"),
    # Lección 5, "combination of the meanings": tercer mecanismo de
    # descubrimiento (unión de dos kanji conocidos), no pictográfico.
    "男": Kanji("おとこ", 7, 3, 2, 3, "man",   "L5"),
    "体": Kanji("からだ", 7, 3, 2, 2, "body",   "L5"),
    "林": Kanji("はやし", 8, 3, 2, 2, "grove", "L5"),
    "畑": Kanji("はたけ", 9, 3, 2, 1, "field",    "L5"),
    "岩": Kanji("いわ",  8, 2, 2, 2, "rock",     "L5"),
    "森": Kanji("もり", 12, 2, 3, 2, "forest",   "L5"),
    "間": Kanji("あいだ", 12, 3, 2, 3, "interval", "L5"),
    # NO están en Basic Kanji Book Vol.1: 刀 (espada), 虫 (insecto).
    # FUERA DEL POOL OFICIAL (8 de septiembre): 先 y 生. 先 se conserva arriba
    # solo para poder evaluar el reparto vigente; 生 no se modela.
}

# ── CONFIGURACIÓN OFICIAL ───────────────────────────────────────────────────
# Fijada el 8 de septiembre de 2026 (decisiones D1–D4 del registro en
# claude/Metricas_Dificultad_Kanji_Fase2.md §12).
#   D1: bandas de tolerancia en lugar de "25 trazos exactos"
#   D2: solo kanji pictográficos — sin lecciones 4 (signos) ni 5 (compuestos)
#   D3: contenido libre; no hay assets encargados
#   D4: óptimo global sobre los 35 pictográficos elegibles
# Reemplaza a 日山車女学 / 月川門子私 / 木田人金先.
SETS: dict[str, list[str]] = {
    "A": ["月", "車", "火", "竹", "石"],
    "B": ["山", "門", "女", "手", "雨"],
    "C": ["人", "足", "牛", "肉", "花"],
}

# Los 20 pictográficos que no entraron. Todos sirven como reserva.
RESERVE = ["日", "木", "川", "田", "口", "土", "子", "水", "目", "米",
           "糸", "耳", "貝", "学", "物", "金", "茶", "馬", "魚", "鳥"]

# Pares con sustitución restringida: reserva -> únicos kanji que puede reemplazar.
# La colisión ひ sigue siendo la única de lectura del pool, pero cambió de lado:
# ahora 火 es experimental y 日 es reserva, así que la restricción se invierte.
RESTRICTED = {
    "日": {"火"},   # colisión de lectura (ひ) — rompe T3
}

# Bandas de tolerancia (§5 del documento de métricas)
BANDS = {
    "strokes":   (25, 2),      # centro, tolerancia
    "morae":     (10, 1),
    "groups":    (12, 2),
    "readings":  (13, 2),
}
PERIM_TOLERANCE_PCT = 8.0      # respecto a la media de los tres sets
SIM_MAX = 0.55                 # similitud gráfica máxima dentro de un set
SIM_MEAN_MAX = 0.12            # similitud gráfica media dentro de un set

# ── Regla de sustitución (decisión D5) ──────────────────────────────────────
# Un kanji de reserva r puede reemplazar a un experimental e dentro del set S
# si y solo si se cumplen las tres condiciones. La tabla no se escribe a mano:
# se DERIVA de los datos con substitution_table(), y Unity la consume desde el
# JSON que produce --export.
#
#   1. Sin colisión dura con los cuatro que quedan (S menos e): ni misma
#      lectura, ni mismo significado, ni forma por encima de SIM_MAX. Si r
#      choca con alguno de los cuatro, la sustitución rompe un tipo de trial.
#   2. Complejidad comparable, ítem a ítem (spec §13.2).
#   3. El set resultante sigue dentro de banda: un participante con
#      sustituciones tiene que estar estudiando un set tan equilibrado como el
#      nominal, o sus datos no son comparables con los del resto.
SUBST_DELTA_STROKES = 2        # |trazos(r) − trazos(e)| máximo
SUBST_DELTA_MORAE = 1          # |moras(r) − moras(e)| máximo
SUBST_READINGS_TOL = 3         # banda de lecturas relajada SOLO al sustituir
# Por qué 3 y no 2: con la banda nominal (13±2) el kanji 女 se queda sin ningún
# sustituto válido, porque aporta 4 lecturas y ningún candidato de trazos
# parecidos las compensa. El nº de lecturas es el más débil de los seis
# indicadores y el único que produce ese agujero; relajarlo a ±3 da entre 3 y 9
# sustitutos a cada uno de los quince. Es una relajación deliberada y acotada,
# no un descuido: queda anotada aquí porque afecta a la comparabilidad de los
# participantes que reciban sustituciones.


# --------------------------------------------------------------------------- #
# Regla de sustitución, derivada de los datos
# --------------------------------------------------------------------------- #

def hard_clash(g: "Glyphs", a: str, b: str) -> str | None:
    """Colisión que rompe un tipo de trial si a y b coinciden en un set."""
    if KANJI[a].reading == KANJI[b].reading:
        return f"lectura {KANJI[a].reading}"
    if KANJI[a].meaning == KANJI[b].meaning:
        return f"significado {KANJI[a].meaning}"
    sim = g.similarity(a, b)
    if sim > SIM_MAX:
        return f"forma {sim:+.3f}"
    return None


def set_in_band(g: "Glyphs", members: list[str], reference_perim: float,
                readings_tol: int) -> str | None:
    """Devuelve el nombre de la primera banda incumplida, o None."""
    for name, (centre, tol) in BANDS.items():
        t = readings_tol if name == "readings" else tol
        if abs(sum(getattr(KANJI[k], name) for k in members) - centre) > t:
            return name
    p = sum(g.perimetric_complexity(k) for k in members)
    if abs(100.0 * (p - reference_perim) / reference_perim) > PERIM_TOLERANCE_PCT:
        return "perim"
    sims = [g.similarity(a, b) for a, b in itertools.combinations(members, 2)]
    if max(sims) > SIM_MAX:
        return "sim_max"
    if float(np.mean(sims)) > SIM_MEAN_MAX:
        return "sim_mean"
    return None


def substitution_table(g: "Glyphs") -> dict[str, dict[str, list[str]]]:
    """Para cada set y cada kanji, qué kanji de reserva pueden reemplazarlo.

    Esta es la tabla que Unity debe aplicar como restricción dura. Nadie la
    escribe: sale de los datos de KANJI, SETS y RESERVE. Cambiar un kanji
    regenera la tabla, que es justo lo que evita que la regla se desactualice
    sin que nadie se entere.
    """
    ref = float(np.mean([sum(g.perimetric_complexity(k) for k in v)
                         for v in SETS.values()]))
    table: dict[str, dict[str, list[str]]] = {}
    for name, members in SETS.items():
        table[name] = {}
        for e in members:
            rest = [x for x in members if x != e]
            valid = []
            for r in RESERVE:
                if any(hard_clash(g, r, x) for x in rest):
                    continue
                if abs(KANJI[r].strokes - KANJI[e].strokes) > SUBST_DELTA_STROKES:
                    continue
                if abs(KANJI[r].morae - KANJI[e].morae) > SUBST_DELTA_MORAE:
                    continue
                if set_in_band(g, rest + [r], ref, SUBST_READINGS_TOL):
                    continue
                valid.append(r)
            table[name][e] = valid
    return table


def export_content(g: "Glyphs", path: str, stream=None) -> dict:
    """Escribe el contrato de contenido que consumen los ScriptableObjects.

    Una sola fuente de verdad para los kanji, el reparto, la reserva y la tabla
    de sustitución. `Planteamiento_Fase2_M2.md` §0.4 documenta cuatro
    divergencias entre documentos y repositorio; este archivo existe para no
    añadir la quinta.
    """
    import json
    table = substitution_table(g)

    def record(ch: str, role: str, set_name: str | None) -> dict:
        k = KANJI[ch]
        return {
            "kanji": ch,
            "meaning": k.meaning,
            "targetReading": k.reading,
            "strokes": k.strokes,
            "morae": k.morae,
            "assemblyGroups": k.groups,
            "commonReadings": k.readings,
            "discoveryType": "Pictographic",
            "textbookLesson": k.lesson,
            "role": role,
            "experimentalSet": set_name,
            "perimetricComplexity": round(g.perimetric_complexity(ch), 1),
        }

    blob = {
        "schemaVersion": 1,
        "generatedBy": "kanji_metrics.py --export",
        "font": g.font_path if hasattr(g, "font_path") else None,
        "note": ("Generado, no escrito a mano. Regenerar tras cualquier cambio "
                 "en KANJI, SETS o RESERVE."),
        "rules": {
            "bands": {k: {"centre": v[0], "tolerance": v[1]}
                      for k, v in BANDS.items()},
            "perimetricTolerancePct": PERIM_TOLERANCE_PCT,
            "simMaxPair": SIM_MAX,
            "simMaxMean": SIM_MEAN_MAX,
            "substitution": {
                "deltaStrokes": SUBST_DELTA_STROKES,
                "deltaMorae": SUBST_DELTA_MORAE,
                "readingsTolerance": SUBST_READINGS_TOL,
            },
            "distractors": "within-set, seeded, 4 options (spec 6.1, 9.3)",
        },
        "sets": {n: list(v) for n, v in SETS.items()},
        "reserve": list(RESERVE),
        "substitutionTable": table,
        "kanji": ([record(c, "Experimental", n)
                   for n, v in SETS.items() for c in v]
                  + [record(c, "Reserve", None) for c in RESERVE]),
    }
    # "-" escribe a stdout. Es la salida que no depende de ningun montaje:
    # el shell del host redirige, asi que funciona aunque el contenedor no vea
    # el repositorio.
    if str(path) == "-":
        out = stream or sys.stdout
        json.dump(blob, out, ensure_ascii=False, indent=2)
        out.write("\n")
        return blob

    target = pathlib.Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(blob, fh, ensure_ascii=False, indent=2)
    return blob


# --------------------------------------------------------------------------- #
# Métricas geométricas
# --------------------------------------------------------------------------- #

class Glyphs:
    """Renderiza y cachea glifos. Una instancia por tipografía."""

    def __init__(self, font_path: str):
        self.font_path = font_path
        self.big = ImageFont.truetype(font_path, 512)
        self.small = ImageFont.truetype(font_path, 256)
        self._perim: dict[str, float] = {}
        self._vec: dict[str, np.ndarray] = {}

    def _ink(self, ch: str, font, pad: int) -> np.ndarray:
        size = font.size + 2 * pad
        img = Image.new("L", (size, size), 255)
        ImageDraw.Draw(img).text((pad, pad), ch, font=font, fill=0)
        return np.array(img) < 128

    def perimetric_complexity(self, ch: str) -> float:
        """C = P² / A. P = aristas tinta/fondo (4-conectividad), A = área de tinta."""
        if ch not in self._perim:
            ink = self._ink(ch, self.big, 64)
            area = int(ink.sum())
            if area == 0:
                raise ValueError(f"la fuente no tiene glifo para {ch!r}")
            perim = int(np.logical_xor(ink[:, :-1], ink[:, 1:]).sum()
                        + np.logical_xor(ink[:-1, :], ink[1:, :]).sum())
            self._perim[ch] = perim * perim / area
        return self._perim[ch]

    def _shape_vector(self, ch: str, blur: float = 4.0) -> np.ndarray:
        """Mapa 128×128 recortado, suavizado, centrado y normalizado."""
        if ch not in self._vec:
            ink = 255.0 * self._ink(ch, self.small, 40)
            ys, xs = np.where(ink > 0)
            crop = ink[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
            im = (Image.fromarray(crop.astype(np.uint8))
                  .resize((128, 128))
                  .filter(ImageFilter.GaussianBlur(blur)))
            v = np.asarray(im, dtype=float).ravel()
            v -= v.mean()
            self._vec[ch] = v / np.linalg.norm(v)
        return self._vec[ch]

    def similarity(self, a: str, b: str) -> float:
        """Correlación de Pearson entre los mapas. 1 = idéntico, 0 = sin relación."""
        return float(self._shape_vector(a) @ self._shape_vector(b))


# --------------------------------------------------------------------------- #
# Evaluación
# --------------------------------------------------------------------------- #

def evaluate_set(g: Glyphs, members: list[str]) -> dict:
    pairs = list(itertools.combinations(members, 2))
    sims = [g.similarity(a, b) for a, b in pairs]
    worst = max(zip(sims, pairs)) if pairs else (0.0, ("", ""))
    return {
        "members": "".join(members),
        "strokes": sum(KANJI[k].strokes for k in members),
        "perim": sum(g.perimetric_complexity(k) for k in members),
        "morae": sum(KANJI[k].morae for k in members),
        "groups": sum(KANJI[k].groups for k in members),
        "readings": sum(KANJI[k].readings for k in members),
        "sim_max": worst[0],
        "sim_max_pair": "/".join(worst[1]),
        "sim_mean": float(np.mean(sims)) if sims else 0.0,
    }


def check_bands(results: dict[str, dict]) -> list[str]:
    """Devuelve la lista de violaciones. Vacía = todo dentro de banda."""
    failures = []
    mean_perim = float(np.mean([r["perim"] for r in results.values()]))
    for name, r in results.items():
        for key, (centre, tol) in BANDS.items():
            if abs(r[key] - centre) > tol:
                failures.append(
                    f"Set {name}: {key} = {r[key]} fuera de {centre}±{tol}")
        dev = 100.0 * (r["perim"] - mean_perim) / mean_perim
        if abs(dev) > PERIM_TOLERANCE_PCT:
            failures.append(
                f"Set {name}: complejidad perimétrica {dev:+.1f}% "
                f"fuera de ±{PERIM_TOLERANCE_PCT:.0f}%")
        if r["sim_max"] > SIM_MAX:
            failures.append(
                f"Set {name}: par {r['sim_max_pair']} en {r['sim_max']:+.3f} "
                f"supera el máximo {SIM_MAX}")
        if r["sim_mean"] > SIM_MEAN_MAX:
            failures.append(
                f"Set {name}: similitud media {r['sim_mean']:+.3f} "
                f"supera el máximo {SIM_MEAN_MAX}")
    return failures


def check_discovery() -> list[str]:
    """Uniformidad del mecanismo de descubrimiento.

    El spec asume una secuencia objeto → forma simplificada → kanji. Solo los
    kanji de las lecciones 'Kanji made from pictures' (L1, L2, L6, L7) traen esa
    derivación en el libro. Cualquier otro exige un mecanismo aparte, que es una
    decisión de diseño, no un descuido: por eso se avisa, no se falla.
    """
    notes = []
    for k in [x for ks in SETS.values() for x in ks] + RESERVE:
        lesson = KANJI[k].lesson
        if not lesson.endswith("-P"):
            notes.append(f"{k} ({lesson or 'sin lección'}) no es pictográfico "
                         f"— necesita su propio mecanismo de descubrimiento")
    return notes


def check_reading_collisions() -> list[str]:
    """Colisiones de lectura y de significado que de verdad pueden ocurrir.

    Una colisión solo rompe un trial si los dos kanji pueden aparecer en la
    MISMA sesión, y una sesión enseña un set. Así que hay dos casos:
      · dentro de un set → error duro, el set no es válido
      · reserva contra un set → solo válido si RESTRICTED lo cubre, porque el
        de reserva únicamente puede entrar reemplazando al que choca
    Dos kanji experimentales en sets DISTINTOS nunca coinciden, así que su
    colisión no es un problema (sí una nota para el análisis entre visitas).
    """
    problems = []

    def clash(a: str, b: str) -> str | None:
        if KANJI[a].reading == KANJI[b].reading:
            return f"lectura {KANJI[a].reading}"
        if KANJI[a].meaning == KANJI[b].meaning:
            return f"significado '{KANJI[a].meaning}'"
        return None

    for name, members in SETS.items():
        for a, b in itertools.combinations(members, 2):
            what = clash(a, b)
            if what:
                problems.append(f"{what}: {a}/{b} dentro del set {name} ← SIN RESTRICCIÓN")

    for r in RESERVE:
        for name, members in SETS.items():
            for e in members:
                what = clash(r, e)
                if what:
                    allowed = e in RESTRICTED.get(r, set())
                    note = " (cubierta por RESTRICTED)" if allowed else " ← SIN RESTRICCIÓN"
                    problems.append(f"{what}: {r}/{e} (reserva vs set {name}){note}")
    return problems


def check_shape_collisions(g: Glyphs, threshold: float = 0.62) -> list[str]:
    """Igual que las de lectura, pero en el canal visual (rompe T1 y T2)."""
    problems = []
    for name, members in SETS.items():
        for a, b in itertools.combinations(members, 2):
            s = g.similarity(a, b)
            if s > threshold:
                problems.append(f"forma {s:+.3f}: {a}/{b} dentro del set {name} ← SIN RESTRICCIÓN")
    for r in RESERVE:
        for name, members in SETS.items():
            for e in members:
                s = g.similarity(r, e)
                if s > threshold:
                    allowed = e in RESTRICTED.get(r, set())
                    note = " (cubierta por RESTRICTED)" if allowed else " ← SIN RESTRICCIÓN"
                    problems.append(f"forma {s:+.3f}: {r}/{e} (reserva vs set {name}){note}")
    return problems


# --------------------------------------------------------------------------- #

def check_repo_root(target: str) -> str | None:
    """Devuelve un diagnostico si la ruta de exportacion no parece del repositorio.

    Existe porque el modo de fallo mas probable --el bind mount del contenedor
    no ocurrio-- se manifiesta como un error de archivo inexistente que no
    menciona el montaje por ningun lado. Un mensaje que dice "vi esto y esperaba
    aquello" ahorra la media hora de adivinar en que capa esta el problema.
    """
    if target == "-":
        return None

    markers = ["tools", "unity-client", "database"]
    missing = [m for m in markers if not (REPO_ROOT / m).is_dir()]
    if not missing:
        return None

    try:
        seen = sorted(p.name for p in REPO_ROOT.iterdir())[:12] or ["(vacio)"]
    except OSError as exc:
        seen = [f"(no se pudo listar: {exc})"]

    return (
        f"REPO_ROOT es {REPO_ROOT} y no parece la raiz del repositorio.\n"
        f"  faltan: {', '.join(missing)}\n"
        f"  contiene: {', '.join(seen)}\n"
        "\n"
        "  Si esto corre en Docker, lo mas probable es que el bind mount no\n"
        "  ocurriera: revisa que la carpeta del proyecto este compartida en\n"
        "  Docker Desktop > Settings > Resources > File sharing.\n"
        "\n"
        "  Salidas alternativas:\n"
        "    --export -                        escribe el JSON a stdout\n"
        "    KANJI_REPO_ROOT=/otra/ruta        fija la raiz a mano"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--font", default=DEFAULT_FONT, help="ruta a una fuente CJK")
    ap.add_argument("--pool", action="store_true",
                    help="listar además los pares más confundibles del pool")
    ap.add_argument("--export", nargs="?", const=str(DEFAULT_EXPORT), metavar="ARCHIVO",
                    help="escribir el contrato de contenido JSON para Unity. "
                         f"Sin argumento: {DEFAULT_EXPORT.relative_to(REPO_ROOT)}")
    ap.add_argument("--subst", action="store_true",
                    help="imprimir la tabla de sustitución derivada")
    args = ap.parse_args()

    # El JSON va por el stdout real; todo lo demas, por stderr.
    real_stdout = sys.stdout
    if args.export == "-":
        sys.stdout = sys.stderr

    try:
        g = Glyphs(args.font)
    except OSError:
        print(f"No se pudo abrir la fuente: {args.font}", file=sys.stderr)
        return 2

    results = {name: evaluate_set(g, ks) for name, ks in SETS.items()}
    mean_perim = float(np.mean([r["perim"] for r in results.values()]))

    print(f"{'Set':<5}{'kanji':<9}{'trazos':>7}{'C_perim':>9}{'Δ%':>7}"
          f"{'moras':>7}{'grupos':>8}{'lect.':>7}{'sim_max':>9}{'sim_med':>9}")
    print("-" * 84)
    for name, r in results.items():
        dev = 100.0 * (r["perim"] - mean_perim) / mean_perim
        print(f"{name:<5}{r['members']:<9}{r['strokes']:>7}{r['perim']:>9.0f}"
              f"{dev:>+7.1f}{r['morae']:>7}{r['groups']:>8}{r['readings']:>7}"
              f"{r['sim_max']:>+9.3f}{r['sim_mean']:>+9.3f}")

    print()
    notes = check_discovery()
    if notes:
        print("Mecanismo de descubrimiento:")
        for n in notes:
            print(f"  {n}")
        print()

    collisions = check_reading_collisions() + check_shape_collisions(g)
    if collisions:
        print("Colisiones detectadas:")
        for c in collisions:
            print(f"  {c}")
        print()

    if args.pool:
        universe = [k for ks in SETS.values() for k in ks] + RESERVE
        top = sorted(((g.similarity(a, b), a, b)
                      for a, b in itertools.combinations(universe, 2)),
                     reverse=True)[:12]
        print("Pares más confundibles del pool:")
        for s, a, b in top:
            print(f"  {a}/{b}  {s:+.3f}")
        print()

    table = substitution_table(g)
    if args.subst or args.export:
        print("Tabla de sustitución derivada (kanji ← reserva admisible):")
        for name, rows in table.items():
            for e, valid in rows.items():
                mark = "" if valid else "   ← SIN SUSTITUTO"
                print(f"  {name} {e}  ({len(valid):>2}) {''.join(valid)}{mark}")
        print()

    if args.export:
        problem = check_repo_root(args.export)
        if problem:
            print(f"\nNo se exporto nada.\n\n  {problem}\n", file=sys.stderr)
            return 2
        export_content(g, args.export, stream=real_stdout)
        if args.export != "-":
            print(f"Contrato de contenido escrito en {args.export}\n")

    orphans = [e for rows in table.values() for e, v in rows.items() if not v]

    failures = check_bands(results)
    unrestricted = [c for c in collisions if "SIN RESTRICCIÓN" in c]
    if failures or unrestricted or orphans:
        print("FUERA DE BANDA:")
        for o in orphans:
            print(f"  {o} no tiene ningún sustituto válido en la reserva")
        for f in failures:
            print(f"  {f}")
        for c in unrestricted:
            print(f"  colisión sin restricción declarada — {c}")
        return 1

    print("Todos los sets dentro de banda; todas las colisiones restringidas; "
          "todos los kanji con sustituto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

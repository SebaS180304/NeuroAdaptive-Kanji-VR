#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kanji_optimizer.py — búsqueda EXACTA del mejor reparto de kanji en tres sets.

Proyecto NeuroAdaptive VR Kanji, Fase 2.
Documentos de referencia:
    claude/Metricas_Dificultad_Kanji_Fase2.md
    claude/Tabla_Autoria_Kanji_Fase2.md
Compañero: kanji_metrics.py (verifica un reparto dado; esto busca el mejor).

────────────────────────────────────────────────────────────────────────────
EL PROBLEMA
────────────────────────────────────────────────────────────────────────────
Elegir 15 kanji de un universo de ~36 y repartirlos en tres sets de 5 tales
que los tres sean lo más equivalentes posible en dificultad, cumpliendo las
restricciones duras del diseño, y dejando un pool de reserva que sirva.

El espacio es C(36,15) · 15!/(5!³·3!) ≈ 7·10¹⁴ repartos. La fuerza bruta no
es opción, y una heurística sin garantía tampoco: el reparto define la
manipulación experimental, así que interesa saber que el resultado es ÓPTIMO,
no solo bueno.

────────────────────────────────────────────────────────────────────────────
CÓMO SE RESUELVE
────────────────────────────────────────────────────────────────────────────
Descomposición en dos etapas, ambas exactas:

  Etapa 1 · Enumerar los sets de 5 FACTIBLES.
      DFS sobre combinaciones con:
        · bitmask de incompatibilidad por kanji (colisión de lectura,
          significado, clúster semántico o forma) → el filtro de conflictos
          es un AND de enteros, O(1)
        · sumas parciales incrementales
        · cotas de banda por sufijo: en cada nodo se conoce la suma mínima y
          máxima alcanzable con los kanji que quedan, y se poda si la banda
          ya es inalcanzable (tablas precalculadas, O(1) por chequeo)

  Etapa 2 · Encontrar el mejor trío DISJUNTO de sets factibles.
      Branch and bound con cota inferior admisible e índice espacial:
        · el objetivo de balance es Σ_m w_m·(max−min) sobre los tres sets,
          y para todo par (a,b):   J(a,b,c) ≥ Σ_m w_m·|v_a,m − v_b,m|
          es decir, la distancia L1 ponderada entre los vectores de a y b
          es una COTA INFERIOR ADMISIBLE del objetivo del trío completo
        · escalando cada coordenada por su peso, esa cota es literalmente
          una distancia L1 → un k-d tree (scipy, p=1) responde "dame todos
          los sets a distancia < J*" en tiempo sublineal
        · dentro de cada consulta los candidatos se recorren en orden de
          cota creciente, de modo que el primer candidato que no mejora
          corta el resto de la rama de golpe
        · el radio de consulta encoge cada vez que mejora el incumbente
        · ruptura de simetría: se exige minidx(a) < minidx(b) < minidx(c),
          así cada trío se visita una vez en vez de seis
        · el incumbente se siembra por construcción dirigida, para arrancar
          con radio pequeño incluso bajo restricciones duras del trío
        · las restricciones que dependen del trío (continuidad) se aplican
          además vectorizadas dentro del recorrido, no solo al aceptar
      Al terminar, el óptimo está PROBADO: todo lo podado tenía cota
      inferior ≥ al incumbente factible. Con --time-limit el recorrido puede
      cortarse: entonces el resultado sigue siendo válido pero se marca como
      no demostrado.

  Verificación opcional · backend CP-SAT (OR-Tools) con el modelo entero
      equivalente. Se activa solo si la librería está instalada.

────────────────────────────────────────────────────────────────────────────
LAS DOS RESTRICCIONES QUE NO SON OBVIAS
────────────────────────────────────────────────────────────────────────────
1. SUSTITUIBILIDAD (§13.2 del spec). El pool de reserva existe para
   reemplazar ítems que el participante ya conoce. Optimizar solo los sets
   consume los kanji limpios y deja una reserva inservible. Aquí se exige
   que CADA uno de los 15 kanji experimentales tenga al menos un sustituto
   válido en el sobrante, de complejidad comparable. Sin esto el óptimo es
   una trampa: sets perfectos que no se pueden ejecutar.

2. CONTINUIDAD (--keep-current K). El óptimo global sin restricciones
   reemplaza casi todo el diseño vigente, lo cual es correcto pero es otro
   estudio. Con K se pide el mejor reparto que conserve al menos K de los 15
   kanji actuales, que es la pregunta que de verdad se puede llevar a una
   reunión.

Uso:
    python3 kanji_optimizer.py                      # óptimo global
    python3 kanji_optimizer.py --keep-current 10    # el mejor cambio gradual
    python3 kanji_optimizer.py --top 10
    python3 kanji_optimizer.py --allow-contextual   # admite 私
    python3 kanji_optimizer.py --cpsat
    python3 kanji_optimizer.py --sweep              # curva continuidad/calidad
    python3 kanji_optimizer.py --keep-current 15    # re-repartir los 15 actuales

Requisitos: pillow, numpy, scipy. Sin red. OR-Tools opcional.
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

DEFAULT_FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
CACHE_FILE = ".kanji_glyph_cache.json"
SET_SIZE = 5
N_SETS = 3


# ═══════════════════════════════════════════════════════════════════════════
# 1 · DATOS
# ═══════════════════════════════════════════════════════════════════════════
# Verificados contra Basic Kanji Book Vol. 1 (Bonjinsha), lecciones 1, 2, 6 y 7
# — las cuatro unidades "Kanji made from pictures", las únicas cuyo formato de
# derivación en cuatro etapas coincide con la mecánica de descubrimiento del
# spec. Fuera quedan las lecciones 3 (números), 4 (signos) y 5 (combinación de
# significados).
#
# imageability: 1–5, qué tan bien un objeto concreto ancla el significado. Es
# la única dimensión que no se puede automatizar. Los valores de abajo son
# PROVISIONALES, a sustituir por los del revisor de MIRAI.

@dataclass(frozen=True)
class Kanji:
    char: str
    reading: str
    meaning: str
    strokes: int
    morae: int
    groups: int          # grupos de segmentación de ensamblaje (2–4)
    readings: int        # nº de lecturas comunes del carácter
    cluster: str         # clúster semántico, para los distractores de T2
    lesson: str          # lección del libro
    imageability: int    # 1–5, provisional
    discovery: str = "picture"   # picture | sign | compound | context
    excluded: bool = False       # fuera del pool oficial, pase lo que pase


# Cada tipo de descubrimiento es un mecanismo distinto que hay que construir en
# Unity. Mezclarlos tiene coste de desarrollo y rompe la uniformidad de la
# instrucción entre ítems, así que por defecto solo entran los pictográficos.
DISCOVERY_KINDS = {
    "picture":  "objeto → forma simplificada → kanji (L1, L2, L6, L7)",
    "sign":     "signo abstracto → kanji (L4) — necesita mecánica espacial",
    "compound": "dos kanji conocidos → kanji (L5) — necesita mecánica de unión",
    "context":  "sin derivación; se ancla en contexto de uso",
}


UNIVERSE: list[Kanji] = [
    # ── Lección 1 · Kanji made from pictures −1− ───────────────────────────
    # ATENCION: esta tabla DUPLICA los campos compartidos de KANJI en
    # kanji_metrics.py -- lectura, trazos, moras, grupos, lecturas, significado,
    # leccion-- y anade dos propios: cluster semantico e imageabilidad.
    #
    # Dos copias del mismo hecho, mantenidas a mano. El 9 de septiembre los
    # significados se tradujeron al ingles en los dos archivos por separado,
    # que es exactamente la operacion que esto obliga a repetir cada vez.
    #
    # ARREGLO PENDIENTE: importar KANJI de kanji_metrics y dejar aqui solo una
    # tabla lateral {caracter: (cluster, imageabilidad)}. No se hizo hoy porque
    # el cambio toca el nucleo del optimizador y merece su propia verificacion,
    # no ir de paquete con una traduccion.
    Kanji("日", "ひ",    "sun",       4, 1, 2, 4, "celeste",   "L1-P", 5),
    Kanji("月", "つき",  "moon",      4, 2, 2, 3, "celeste",   "L1-P", 5),
    Kanji("木", "き",    "tree",     4, 1, 2, 3, "planta",    "L1-P", 5),
    Kanji("山", "やま",  "mountain",   3, 2, 2, 2, "terreno",   "L1-P", 5),
    Kanji("川", "かわ",  "river",       3, 2, 3, 2, "terreno",   "L1-P", 5),
    Kanji("田", "た",    "rice field",   5, 1, 2, 2, "terreno",   "L1-P", 4),
    Kanji("人", "ひと",  "person",   2, 2, 2, 3, "person",   "L1-P", 5),
    Kanji("口", "くち",  "mouth",      3, 2, 2, 2, "body",    "L1-P", 4),
    Kanji("車", "くるま", "car",     7, 3, 3, 2, "objeto",    "L1-P", 5),
    Kanji("門", "もん",  "gate",    8, 2, 2, 2, "objeto",    "L1-P", 5),
    # ── Lección 2 · Kanji made from pictures −2− ───────────────────────────
    # 生 excluido: ninguna de sus lecturas funciona con el kanji aislado.
    Kanji("火", "ひ",    "fire",     4, 1, 3, 2, "elemento",  "L2-P", 5),
    Kanji("水", "みず",  "water",      4, 2, 2, 2, "elemento",  "L2-P", 5),
    Kanji("金", "きん",  "gold",       8, 2, 3, 3, "objeto",    "L2-P", 4),
    Kanji("土", "つち",  "ground",    3, 2, 2, 2, "terreno",   "L2-P", 3),
    Kanji("子", "こ",    "child",      3, 1, 2, 3, "person",   "L2-P", 5),
    Kanji("女", "おんな", "woman",     3, 3, 3, 4, "person",   "L2-P", 5),
    Kanji("学", "ガク",  "study",   8, 2, 3, 2, "abstracto", "L2-P", 2),
    # 先 EXCLUIDO del pool oficial (decisión del 8 de septiembre). Se conserva
    # en el modelo solo para poder evaluar el reparto vigente; nunca elegible.
    Kanji("先", "さき",  "ahead",   6, 2, 2, 2, "abstracto", "L2-P", 2,
          "picture", True),
    # 生 EXCLUIDO: ninguna de sus lecturas funciona con el kanji aislado, y
    # además sale del pool oficial. No se incluye ni para comparar.
    # ── Lección 6 · Kanji made from pictures −3− ───────────────────────────
    Kanji("目", "め",    "eye",       5, 1, 2, 2, "body",    "L6-P", 4),
    Kanji("耳", "みみ",  "ear",     6, 2, 2, 2, "body",    "L6-P", 3),
    Kanji("手", "て",    "hand",      4, 1, 2, 2, "body",    "L6-P", 5),
    Kanji("足", "あし",  "leg",       7, 2, 3, 3, "body",    "L6-P", 4),
    Kanji("雨", "あめ",  "rain",    8, 2, 3, 2, "elemento",  "L6-P", 4),
    Kanji("竹", "たけ",  "bamboo",     6, 2, 2, 2, "planta",    "L6-P", 5),
    Kanji("米", "こめ",  "rice",     6, 2, 3, 3, "planta",    "L6-P", 4),
    Kanji("貝", "かい",  "shellfish",    7, 2, 2, 2, "animal",    "L6-P", 5),
    Kanji("石", "いし",  "stone",    5, 2, 2, 2, "terreno",   "L6-P", 5),
    Kanji("糸", "いと",  "thread",      6, 2, 2, 2, "objeto",    "L6-P", 4),
    # ── Lección 7 · Kanji made from pictures −4− ───────────────────────────
    # 茶, 字 y 文 excluidos: sin lectura kun natural en aislado, o abstractos.
    Kanji("魚", "さかな", "fish",      11, 3, 3, 2, "animal",    "L7-P", 5),
    Kanji("鳥", "とり",  "bird",      11, 2, 3, 2, "animal",    "L7-P", 5),
    Kanji("馬", "うま",  "horse",  10, 2, 3, 2, "animal",    "L7-P", 5),
    Kanji("牛", "うし",  "cow",      4, 2, 2, 2, "animal",    "L7-P", 5),
    Kanji("肉", "にく",  "meat",     6, 2, 2, 1, "comida",    "L7-P", 4),
    Kanji("花", "はな",  "flower",      7, 2, 3, 2, "planta",    "L7-P", 5),
    Kanji("物", "もの",  "thing",      8, 2, 3, 3, "abstracto", "L7-P", 1),
    Kanji("茶", "ちゃ",  "tea",        9, 2, 3, 2, "comida",    "L7-P", 4),
    # 字 (じ) y 文 (ぶん) descartados: significados abstractos, sin objeto que
    # los ancle en la Object/Association Area.

    # ── Lección 4 · Kanji made from SIGNS ──────────────────────────────────
    # Derivación de cuatro etapas, pero desde un signo abstracto, no desde un
    # objeto. Elegibles solo con --discovery sign. 大, 小, 半 y 分 quedan fuera
    # por ser adjetivos o verbos con okurigana; 何 por ser palabra interrogativa.
    Kanji("本", "ほん",  "book",     5, 2, 2, 2, "objeto",    "L4",   5, "sign"),
    Kanji("中", "なか",  "middle",    4, 2, 2, 3, "abstracto", "L4",   3, "sign"),
    Kanji("上", "うえ",  "above",    3, 2, 2, 5, "abstracto", "L4",   2, "sign"),
    Kanji("下", "した",  "below",     3, 2, 2, 5, "abstracto", "L4",   2, "sign"),
    Kanji("力", "ちから", "power",    2, 3, 2, 3, "abstracto", "L4",   2, "sign"),

    # ── Lección 5 · Kanji made from a COMBINATION OF THE MEANINGS ──────────
    # Se derivan uniendo kanji que el participante ya conoce (林 = 木+木,
    # 岩 = 山+石). En VR eso es una mecánica de unión, no de transformación:
    # tercer mecanismo. A cambio, aquí viven casi todas las lecturas de tres
    # moras que le faltan al pool. Elegibles con --discovery compound.
    # 明, 休 y 好 quedan fuera por ser adjetivos o verbos con okurigana.
    Kanji("男", "おとこ", "man",    7, 3, 2, 3, "person",   "L5",   5, "compound"),
    Kanji("体", "からだ", "body",    7, 3, 2, 2, "body",    "L5",   4, "compound"),
    Kanji("林", "はやし", "grove",  8, 3, 2, 2, "planta",    "L5",   5, "compound"),
    Kanji("畑", "はたけ", "field",     9, 3, 2, 1, "terreno",   "L5",   4, "compound"),
    Kanji("岩", "いわ",  "rock",      8, 2, 2, 2, "terreno",   "L5",   5, "compound"),
    Kanji("森", "もり",  "forest",   12, 2, 3, 2, "planta",    "L5",   5, "compound"),
    Kanji("間", "あいだ", "interval", 12, 3, 2, 3, "abstracto", "L5",   2, "compound"),

    # ── Sin derivación ─────────────────────────────────────────────────────
    # 私 está en la Lección 2 pero NO en su tabla de derivación pictográfica.
    # Se incluye siempre en el modelo para poder evaluar el diseño vigente,
    # pero solo es elegible con --discovery context.
    Kanji("私", "わたし", "I",        7, 3, 2, 2, "abstracto", "L2",   1, "context"),
]

# El reparto vigente, para comparar.
CURRENT = [["日", "山", "車", "女", "学"],
           ["月", "川", "門", "子", "私"],
           ["木", "田", "金", "人", "先"]]
CURRENT_FLAT = [c for s in CURRENT for c in s]


# ═══════════════════════════════════════════════════════════════════════════
# 2 · MÉTRICAS GEOMÉTRICAS
# ═══════════════════════════════════════════════════════════════════════════

class Glyphs:
    """Renderiza glifos y calcula las dos métricas geométricas.

    Complejidad perimétrica  C = P²/A  (Pelli, Burns, Farell & Moore-Page 2006).
    Confusabilidad gráfica   correlación de Pearson entre mapas suavizados.

    Ambas dependen de la tipografía, así que la caché en disco lleva la ruta de
    la fuente en la clave: cambiar de fuente la invalida sola.
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
                raise ValueError(f"la fuente no tiene glifo para {ch!r}")
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
# 3 · MODELO
# ═══════════════════════════════════════════════════════════════════════════

# Métricas que se equilibran entre sets. El peso dice cuánto pesa un punto de
# desbalance relativo de esa métrica.
#   morae pesa más: es la dimensión donde el diseño actual falla y la que
#   afecta directamente al trial T3.
#   sim es la confusabilidad media dentro del set: si un set es más
#   auto-confundible que otro, sus trials T1/T2 son más difíciles.
METRIC_WEIGHTS: dict[str, float] = {
    "strokes":  1.0,
    "perim":    1.0,
    "morae":    1.5,
    "groups":   0.5,
    "readings": 0.5,
    "sim":      1.0,
}

BANDS: dict[str, tuple[float, float]] = {   # (centro, tolerancia) por set
    "strokes":  (25.0, 2.0),
    "morae":    (10.0, 1.0),
    "groups":   (12.0, 2.0),
    "readings": (13.0, 2.0),
}

SIM_MAX_PAIR = 0.55       # ningún par dentro de un set por encima de esto
SIM_MAX_MEAN = 0.12       # similitud media dentro de un set
MAX_PER_CLUSTER = 1       # kanji del mismo clúster semántico por set
QUALITY_WEIGHT = 0.35     # peso del término absoluto (anclaje 3D y confusión)
SUBST_STROKE_TOL = 2      # un sustituto vale si difiere ≤ esto en trazos


@dataclass
class Model:
    kanji: list[Kanji]
    n: int
    sim: np.ndarray
    perim: np.ndarray
    incompatible: list[int] = field(default_factory=list)   # duro + clúster
    hard_clash: list[int] = field(default_factory=list)     # lectura/sig./forma
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

    # ── incompatibilidades ─────────────────────────────────────────────────
    # DURAS: rompen un tipo de trial.
    #   misma lectura      → dos opciones idénticas en T3
    #   mismo significado  → dos opciones idénticas en T1 y T2
    #   forma > umbral     → T1 y T2 quedan casi indecidibles
    # BLANDA (clúster semántico): los distractores de T2 se vuelven ambiguos.
    #   Es la objeción "árbol contra bambú" convertida en regla. Cuenta para
    #   formar sets, pero no para juzgar si un sustituto es válido.
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

    # Tablas de sufijo para las cotas de poda del DFS:
    #   suffix_min[name][i, r] = suma de los r valores MENORES entre kanji[i:]
    #   suffix_max[name][i, r] = suma de los r valores MAYORES entre kanji[i:]
    # Relajación (ignora incompatibilidades), así que la cota es válida y O(1).
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
# 4 · ETAPA 1 — ENUMERACIÓN DE SETS FACTIBLES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class FeasibleSet:
    mask: int
    members: tuple[int, ...]
    vec: np.ndarray           # vector métrico ponderado y normalizado
    quality: float            # término absoluto ≥ 0 (menor = mejor)
    sim_mean: float
    sim_max: float
    raw: dict[str, float]
    minidx: int
    n_current: int            # cuántos de sus 5 están en el diseño vigente


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
        # Validación final de bandas. band_reachable() solo comprueba que la
        # banda siga siendo ALCANZABLE con los kanji que faltan; el set
        # completo hay que verificarlo aquí.
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
        # Calidad absoluta: aditiva por set y ≥ 0, que es lo que mantiene
        # válida la cota inferior de la etapa 2.
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
        print(f"  nodos explorados      {stats['nodes']:>10,}")
        print(f"  podados por banda     {stats['pruned_band']:>10,}")
        print(f"  fuera de banda        {stats['rejected_band']:>10,}")
        print(f"  descartados por sim.  {stats['rejected_sim']:>10,}")
        print(f"  sets factibles        {len(out):>10,}"
              f"   de C({n_sel},{SET_SIZE}) = {comb(n_sel, SET_SIZE):,}")
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 5 · OBJETIVO Y RESTRICCIONES DEL TRÍO
# ═══════════════════════════════════════════════════════════════════════════

def balance_only(a: FeasibleSet, b: FeasibleSet, c: FeasibleSet) -> float:
    V = np.stack([a.vec, b.vec, c.vec])
    return float((V.max(axis=0) - V.min(axis=0)).sum())


def objective(a: FeasibleSet, b: FeasibleSet, c: FeasibleSet) -> float:
    """Σ_m w_m·(max−min)/escala  +  Σ_s calidad(s)."""
    return balance_only(a, b, c) + a.quality + b.quality + c.quality


def substitutability(m: Model, sets: list[FeasibleSet]) -> tuple[bool, list[str]]:
    """¿Tiene cada kanji experimental un sustituto válido en el sobrante?

    Un kanji r del sobrante puede reemplazar a e dentro del set S si:
      · |trazos(r) − trazos(e)| ≤ SUBST_STROKE_TOL  (§13.2: complejidad
        comparable)
      · r no choca duro con ningún miembro de S salvo, como mucho, el propio e
        — porque tras la sustitución e ya no está.
    Devuelve (cumple, lista de kanji sin sustituto).
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
# 6 · ETAPA 2 — BRANCH AND BOUND EXACTO
# ═══════════════════════════════════════════════════════════════════════════

def seed_incumbent(sets, masks, V, Q, ncur, accept, anchors=400, width=24,
                   seed=0) -> tuple[float, tuple[int, int, int] | None]:
    """Cota superior inicial mediante construcción dirigida.

    Importa más de lo que parece: si el incumbente arranca en infinito, el
    radio de la primera consulta al k-d tree también, la bola devuelve todo y
    el branch and bound degenera en fuerza bruta. Con restricciones duras
    sobre el trío (continuidad, sustituibilidad) un muestreo aleatorio casi
    nunca acierta un trío válido, así que aquí se construye a propósito:

      · las anclas se recorren por continuidad descendente y calidad
        ascendente, que es donde viven las soluciones que cumplen --keep
      · para cada ancla se toman los `width` sets disjuntos más cercanos en
        la cota L1, y para cada par los `width` más cercanos al punto medio
      · se devuelve el mejor trío que pase `accept`

    No da garantía de nada; solo un radio inicial pequeño y factible.
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
    """Branch and bound exacto sobre tríos disjuntos que cumplen `accept`.

    `accept(tri) -> bool` filtra restricciones que dependen del trío entero
    (sustituibilidad, continuidad). El incumbente solo toma valores de tríos
    aceptados, así que la poda sigue siendo correcta.

    Devuelve (resultados, probado). `probado` es False solo si se agotó
    `time_limit` antes de cerrar el recorrido: en ese caso el mejor resultado
    sigue siendo válido, pero deja de tener garantía de optimalidad.
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
        heapq.heappush(heap, (-J, tri))
        while len(heap) > top:
            heapq.heappop(heap)
        return -heap[0][0] if len(heap) == top else incumbent

    incumbent, seed_tri = seed_incumbent(sets, masks_np, V, Q, ncur, accept)
    if seed_tri is not None:
        heapq.heappush(heap, (-incumbent, seed_tri))

    stats = {"anchors": 0, "pairs": 0, "triples": 0, "rejected": 0}
    t0 = time.time()
    proven = True

    # Recorrer los sets de mejor calidad primero: encuentra buenos incumbentes
    # antes y encoge el radio cuanto antes.
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
            # continuidad, vectorizada: con el mejor tercer set posible,
            # ¿todavía se puede alcanzar K?
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
                break            # ordenado: el resto tampoco puede mejorar
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
        print(f"  anclas recorridas     {stats['anchors']:>10,} de {n:,}")
        print(f"  pares evaluados       {stats['pairs']:>10,}")
        print(f"  tríos evaluados       {stats['triples']:>10,}")
        print(f"  tríos rechazados      {stats['rejected']:>10,}"
              f"   (sustituibilidad / continuidad)")
        print(f"  tiempo de búsqueda    {time.time() - t0:>10.1f} s")
        if not proven:
            print("  ⚠ límite de tiempo alcanzado: el resultado es válido "
                  "pero la optimalidad NO está demostrada")
    return sorted(((-j, t) for j, t in heap)), proven


# ═══════════════════════════════════════════════════════════════════════════
# 7 · BACKEND CP-SAT OPCIONAL
# ═══════════════════════════════════════════════════════════════════════════

def verify_with_cpsat(m: Model, best_balance: float, scale: int = 10_000) -> str:
    """Modelo entero equivalente, como segunda opinión sobre el óptimo.

    Cubre la parte lineal del objetivo (todo menos los términos de similitud
    y calidad, que son cuadráticos en las variables de decisión), así que su
    óptimo es una COTA INFERIOR del balance completo.
    """
    try:
        from ortools.sat.python import cp_model
    except ImportError:
        return ("OR-Tools no instalado — verificación omitida "
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
    for s in range(N_SETS - 1):     # ruptura de simetría por índice mínimo
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
        return "CP-SAT no encontró solución factible"
    lb = solver.ObjectiveValue() / scale
    tag = "óptimo" if st == cp_model.OPTIMAL else "factible"
    ok = "coherente" if lb <= best_balance + 1e-6 else "INCOHERENTE"
    return (f"CP-SAT ({tag}) sobre la relajación lineal del balance: {lb:.4f}. "
            f"El balance del óptimo hallado es {best_balance:.4f}. "
            f"Debe cumplirse relajación ≤ completo → {ok}.")


# ═══════════════════════════════════════════════════════════════════════════
# 8 · REPORTE
# ═══════════════════════════════════════════════════════════════════════════

def describe(m: Model, sets: list[FeasibleSet], label: str = "") -> None:
    hdr = (f"{'Set':<4}{'kanji':<9}{'trazos':>7}{'C_perim':>9}{'moras':>7}"
           f"{'grupos':>8}{'lect.':>7}{'sim_med':>9}{'sim_max':>9}{'img':>6}")
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
    print(f"  mecanismos: {mech}")
    print(f"  balance {balance_only(*sets):.4f}   calidad "
          f"{sum(s.quality for s in sets):.4f}   objetivo {objective(*sets):.4f}"
          f"   conserva {keep}/15   {label}")


def report_reserve(m: Model, sets: list[FeasibleSet]) -> None:
    used = 0
    for s in sets:
        used |= s.mask
    leftovers = [i for i in range(m.n) if not (used >> i & 1) and m.selectable[i]]
    exp = [i for s in sets for i in s.members]

    print(f"{'K':<3}{'lectura':>9}{'tr':>4}{'mo':>4}{'lección':>9}"
          f"{'peor sim':>10}   puede sustituir a")
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
        shown = "".join(targets) if targets else "— ninguno"
        print(f"{k.char:<3}{k.reading:>9}{k.strokes:>4}{k.morae:>4}"
              f"{k.lesson:>9}{worst:>+10.3f}   {shown}")

    ok, orphans = substitutability(m, sets)
    if ok:
        print("\n  todos los kanji experimentales tienen sustituto válido")
    else:
        print(f"\n  SIN SUSTITUTO: {' '.join(orphans)}")


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
            out.append(f"{name} {s.raw[name]:.0f} (banda {centre:.0f}±{tol:.0f})")
    if s.sim_mean > SIM_MAX_MEAN:
        out.append(f"sim media {s.sim_mean:+.3f} (máx {SIM_MAX_MEAN})")
    if s.sim_max > SIM_MAX_PAIR:
        out.append(f"sim máx {s.sim_max:+.3f} (máx {SIM_MAX_PAIR})")
    clusters = [m.kanji[i].cluster for i in s.members]
    dup = {c for c in clusters if clusters.count(c) > 1}
    if dup:
        out.append(f"clúster repetido: {', '.join(sorted(dup))}")
    return out


# ═══════════════════════════════════════════════════════════════════════════

def solve(m: Model, feasible: list[FeasibleSet], keep: int, subst: bool,
          top: int, verbose: bool = True, time_limit: float = 0.0):
    # Poda barata de continuidad antes del B&B: un set solo sirve si, con dos
    # compañeros perfectos, todavía puede alcanzar K.
    max_cur = max((s.n_current for s in feasible), default=0)
    pool = feasible
    if keep:
        pool = [s for s in feasible if s.n_current + 2 * max_cur >= keep]
        if verbose and len(pool) < len(feasible):
            print(f"  preselección por continuidad: {len(pool):,} de "
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
                    help="cuántos repartos reportar (el primero es el óptimo)")
    ap.add_argument("--keep-current", type=int, default=0, metavar="K",
                    help="exigir conservar al menos K de los 15 kanji actuales")
    ap.add_argument("--discovery", nargs="+", default=["picture"],
                    choices=sorted(DISCOVERY_KINDS), metavar="TIPO",
                    help="mecanismos de descubrimiento admitidos: "
                         + ", ".join(DISCOVERY_KINDS))
    ap.add_argument("--allow-contextual", action="store_true",
                    help="atajo para añadir 'context' a --discovery (admite 私)")
    ap.add_argument("--no-substitutability", action="store_true",
                    help="no exigir que cada kanji tenga sustituto en la reserva")
    ap.add_argument("--sweep", action="store_true",
                    help="curva continuidad ↔ calidad para varios K")
    ap.add_argument("--sweep-points", type=int, nargs="+",
                    default=[0, 5, 8, 10, 12, 13, 14, 15], metavar="K",
                    help="valores de K del barrido")
    ap.add_argument("--time-limit", type=float, default=90.0, metavar="S",
                    help="segundos por búsqueda; 0 = sin límite (default 90)")
    ap.add_argument("--cpsat", action="store_true",
                    help="segunda opinión con OR-Tools CP-SAT, si está instalado")
    args = ap.parse_args()

    try:
        g = Glyphs(args.font)
    except OSError:
        print(f"No se pudo abrir la fuente: {args.font}", file=sys.stderr)
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
    print(f"Universo: {int(m.selectable.sum())} kanji elegibles de {m.n} "
          f"en Basic Kanji Book Vol. 1")
    for kind, desc in DISCOVERY_KINDS.items():
        mark = "✓" if kind in allowed else " "
        print(f"  [{mark}] {kind:<9} {by_kind[kind]:>2} kanji · {desc}")
    excl = [x.char for x in UNIVERSE if x.excluded]
    if excl:
        print(f"  fuera del pool oficial: {' '.join(excl)} (más 生, no modelado)")
    print(f"Restricciones: bandas §5 · clúster ≤{MAX_PER_CLUSTER}/set · "
          f"sim par ≤{SIM_MAX_PAIR} · sim media ≤{SIM_MAX_MEAN}"
          f"{' · sustituibilidad' if subst else ''}"
          f"{f' · conservar ≥{args.keep_current}' if args.keep_current else ''}\n")

    print("Etapa 1 · enumeración de sets factibles")
    feasible = enumerate_feasible(m)
    print()
    if not feasible:
        print("Ningún set cumple las restricciones.")
        return 1

    # ── barrido de continuidad ─────────────────────────────────────────────
    if args.sweep:
        print("Curva continuidad ↔ calidad")
        print("Cuánto cuesta, en balance, conservar K kanji del diseño actual.\n")
        print(f"{'conserva ≥':>11}{'objetivo':>10}{'balance':>9}{'':>3}  reparto")
        print("-" * 74)
        base = None
        for K in args.sweep_points:
            pool, res, proven = solve(m, feasible, K, subst, 1, verbose=False,
                                      time_limit=args.time_limit)
            if not res:
                print(f"{K:>11}{'—':>10}{'—':>9}     sin solución factible")
                continue
            J, tri = res[0]
            ss = [pool[i] for i in tri]
            if base is None:
                base = J
            chars = " ".join("".join(m.kanji[i].char for i in s.members) for s in ss)
            mark = "  " if proven else " ~"
            print(f"{K:>11}{J:>10.4f}{balance_only(*ss):>9.4f}{mark:>3}  {chars}"
                  f"  (+{100 * (J - base) / base:.0f} %)")
        print("\n  ~ = límite de tiempo alcanzado, optimalidad no demostrada")
        print(f"\ntotal {time.time() - t0:.1f} s")
        return 0

    print("Etapa 2 · branch and bound sobre tríos disjuntos")
    pool, results, proven = solve(m, feasible, args.keep_current, subst,
                                  max(1, args.top), time_limit=args.time_limit)
    print()
    if not results:
        print("No existe reparto que cumpla todas las restricciones. "
              "Prueba con --keep-current menor o --no-substitutability.")
        return 1

    J, tri = results[0]
    best = [pool[i] for i in tri]
    print("═" * 78)
    print("REPARTO ÓPTIMO")
    print("═" * 78)
    describe(m, best, "← óptimo demostrado" if proven else "← mejor hallado (sin prueba)")
    print()

    if len(results) > 1:
        print(f"Los siguientes {len(results) - 1} mejores:\n")
        for rank, (Jk, trik) in enumerate(results[1:], start=2):
            ss = [pool[i] for i in trik]
            chars = "  ".join("".join(m.kanji[i].char for i in s.members) for s in ss)
            keep = sum(s.n_current for s in ss)
            print(f"  {rank:>2}. {chars}   objetivo {Jk:.4f}"
                  f"  (+{100 * (Jk - J) / J:.1f} %)  conserva {keep}/15")
        print()

    print("─" * 78)
    print("COMPARACIÓN CON EL REPARTO VIGENTE")
    print("─" * 78)
    cur = [as_feasible(m, s) for s in CURRENT]
    if all(c is not None for c in cur):
        describe(m, cur, "← diseño actual")
        cJ = objective(*cur)
        print(f"  el óptimo mejora el objetivo en {100 * (cJ - J) / cJ:.1f} %")
        for tag, s in zip("ABC", cur):
            v = violations(m, s)
            if v:
                print(f"  set {tag} incumple: {'; '.join(v)}")
        ok, orphans = substitutability(m, cur)
        if not ok:
            print(f"  sin sustituto en reserva: {' '.join(orphans)}")
    print()

    print("─" * 78)
    print("POOL DE RESERVA DERIVADO")
    print("─" * 78)
    report_reserve(m, best)
    print()

    if args.cpsat:
        print("─" * 78)
        print("SEGUNDA OPINIÓN")
        print("─" * 78)
        print("  " + verify_with_cpsat(m, balance_only(*best)))
        print()

    print(f"total {time.time() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_board_font.py — extrae la cara japonesa del .ttc de Noto y la deja en
el repositorio como la fuente única del Learning Board.

Proyecto NeuroAdaptive VR Kanji, Fase 2.

Por qué existe
--------------
`kanji_metrics.py` calcula complejidad perimétrica y confusabilidad gráfica
**renderizando los glifos**, así que los números describen una tipografía
concreta. Unity dibuja el kanji que ve el participante con otra. Si no son la
misma forma, el número que va al revisor de MIRAI describe algo que nadie ve.

Hasta hoy la fuente de las métricas era `NotoSansCJK-Regular.ttc` del paquete
Debian dentro de la imagen. Eso tiene dos problemas para Unity:

1. Es una **colección** (.ttc) con varias caras — JP, KR, SC, TC, HK. PIL abre
   el índice 0 por omisión y TMP hace lo suyo; que coincidan es una suposición,
   y este proyecto lleva cinco divergencias causadas por suposiciones de esa
   forma.
2. Vive en el sistema de archivos de la imagen, no en el repositorio, así que
   Unity no puede alcanzarla.

Este script rompe la ambigüedad: extrae **una cara concreta, por índice
explícito, verificando su nombre**, y la escribe en el repositorio. A partir de
ahí ese archivo es la fuente única: `kanji_metrics.py` lo usa por omisión y
Unity genera su TMP_FontAsset del mismo archivo.

Uso
---
    docker compose run --rm kanji-tools python tools/extract_board_font.py
    docker compose run --rm kanji-tools python tools/extract_board_font.py --list

Salida: unity-client/Assets/Fonts/NotoSansCJKjp-Regular.otf

Licencia: Noto es SIL Open Font License 1.1 — redistribuible, se versiona.
"""

from __future__ import annotations
import argparse, hashlib, pathlib, sys

from fontTools.ttLib import TTCollection, TTFont

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
DEFAULT_OUT = REPO_ROOT / "unity-client" / "Assets" / "Fonts" / "NotoSansCJKjp-Regular.otf"

# La cara que queremos. Se comprueba contra el nombre real: si el paquete Debian
# reordena las caras en una version futura, esto falla en vez de exportar coreano
# en silencio.
EXPECTED_FAMILY_SUBSTRING = "Noto Sans CJK JP"

# Pool tutorial de la spec 4.2. No esta en kanji_metrics porque no participa de
# las metricas, pero sí se dibuja en el board.
TUTORIAL = "一二三四五"


def face_name(font: TTFont) -> str:
    """nameID 4 = full font name; nameID 1 = family."""
    name_table = font["name"]
    for nid in (4, 1):
        rec = name_table.getDebugName(nid)
        if rec:
            return rec
    return "(sin nombre)"


def required_characters() -> set[str]:
    """Todo lo que el Learning Board tiene que poder dibujar."""
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import kanji_metrics as km

    chars: set[str] = set(km.KANJI.keys())
    chars |= set(TUTORIAL)
    # La lectura objetivo es kana; el significado, latino. `readings` es un
    # conteo, no una lista: no se itera.
    for k in km.KANJI.values():
        chars |= set(k.reading)
        chars |= set(k.meaning)
    chars |= set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,/()-?")
    return {c for c in chars if c.strip()}


def covered(font: TTFont, chars: set[str]) -> tuple[set[str], set[str]]:
    cmap = font.getBestCmap()
    have = {c for c in chars if ord(c) in cmap}
    return have, chars - have


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=DEFAULT_SOURCE, help="ruta al .ttc de Noto CJK")
    ap.add_argument("--index", type=int, default=0, help="indice de la cara a extraer")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="archivo .otf de salida")
    ap.add_argument("--list", action="store_true",
                    help="solo enumera las caras del .ttc y sale")
    args = ap.parse_args()

    src = pathlib.Path(args.source)
    if not src.exists():
        print(f"No existe la fuente de origen: {src}", file=sys.stderr)
        print("Se esperaba el .ttc que fija tools/Dockerfile. Si el paquete "
              "fonts-noto-cjk cambio de ruta, corregir el Dockerfile y este "
              "valor por defecto juntos.", file=sys.stderr)
        return 2

    collection = TTCollection(str(src))
    print(f"Origen : {src}")
    print(f"Caras  : {len(collection.fonts)}")
    for i, f in enumerate(collection.fonts):
        mark = " <-- seleccionada" if i == args.index and not args.list else ""
        print(f"  [{i:2d}] {face_name(f)}{mark}")

    if args.list:
        return 0

    if not 0 <= args.index < len(collection.fonts):
        print(f"Indice {args.index} fuera de rango.", file=sys.stderr)
        return 2

    face = collection.fonts[args.index]
    name = face_name(face)
    if EXPECTED_FAMILY_SUBSTRING not in name:
        print(f"\nLa cara [{args.index}] se llama '{name}', y se esperaba que "
              f"contuviera '{EXPECTED_FAMILY_SUBSTRING}'.", file=sys.stderr)
        print("Esto significa que el orden de caras del .ttc cambio. NO se "
              "exporta: exportar la cara equivocada produciria metricas de una "
              "tipografia y glifos de otra, que es justo lo que este script "
              "existe para impedir.", file=sys.stderr)
        print("Correr con --list, identificar el indice de la cara JP y pasarlo "
              "con --index.", file=sys.stderr)
        return 1

    chars = required_characters()
    have, missing = covered(face, chars)
    print(f"\nCobertura: {len(have)}/{len(chars)} caracteres del estudio")
    if missing:
        print(f"FALTAN {len(missing)}: {''.join(sorted(missing))}", file=sys.stderr)
        print("Una fuente que no cubre todo el contenido deja tofu en el board.",
              file=sys.stderr)
        return 1

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    face.save(str(out))

    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"\nEscrito : {out}")
    print(f"Tamano  : {out.stat().st_size} bytes")
    print(f"SHA-256 : {digest}")
    print("\nEste archivo es ahora la fuente unica del Learning Board:")
    print("  - kanji_metrics.py lo usa por omision (DEFAULT_FONT)")
    print("  - Unity genera su TMP_FontAsset del mismo archivo")
    print("Si cambia, hay que regenerar ambos en el mismo commit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

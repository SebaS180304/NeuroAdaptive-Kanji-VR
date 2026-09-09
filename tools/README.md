# tools/

Content tooling for the experimental kanji sets. Two scripts and one generated
artifact.

Design decisions and the reasoning behind the sets live in
`claude/Metricas_Dificultad_Kanji_Fase2.md` (Claude Project). This README covers
how to run them and where the output goes.

## The one rule

**`unity-client/Assets/Resources/kanji_content.json` is generated, never edited
by hand, and exists in exactly one place.**

It is not produced here and copied into Unity — it is written directly where
Unity reads it. Two copies of the same fact is the failure this project has hit
five times: three stale documents in August, `verify_m1.sql` querying a column
that never existed, the game flow enum serialized two ways, and on 9 September a
`state` and a `lal` that each existed twice and disagreed.

Regenerate it in the same commit that changes any kanji.

## kanji_metrics.py — verifier and exporter

Computes six difficulty metrics over sets A/B/C, checks them against the
tolerance bands, verifies reading/meaning/shape collisions, derives the
substitution table, and exports the content contract.

**Run it through Docker**, from the repository root:

```bash
docker compose run --rm kanji-tools python tools/kanji_metrics.py            # verify only
docker compose run --rm kanji-tools python tools/kanji_metrics.py --export   # verify + write the JSON
docker compose run --rm kanji-tools python tools/kanji_metrics.py --subst    # substitution table
docker compose run --rm kanji-tools python tools/kanji_metrics.py --pool     # most confusable pairs
```

The service sits behind the `tools` profile, so `docker compose up` does not
start it — it is a one-shot container, not a service. The first run builds the
image.

This is not a convenience. **The perimetric-complexity and graphical-similarity
metrics are computed by rendering the glyphs, so they depend on the typeface**:
the same script with a different font gives different numbers and can flip a
band check. Pinning the font — and the Pillow and numpy versions — inside an
image is what makes the result reproducible for anyone, now or in a year, and
what makes the numbers defensible if this work is published.

It also makes the rule above achievable. The development machine is Windows and
has neither the dependencies nor the font at the path the script expects;
without the container, "regenerate in the same commit" would be an instruction
nobody on the team could follow.

Running it directly with a local Python works if you have Pillow, numpy and a
CJK font, but **pass `--font` pointing at the same Noto Sans CJK JP** or the
numbers will not match what is in the JSON.

`--export` with no argument writes to the Unity path above. Passing a path is
possible but there is no reason to: a second location is a second copy.

**Exit code 1 if anything is out of band, so it can run in CI or a pre-commit
hook.** That is the point — an error caught when the kanji changes costs
minutes; caught during analysis it costs the study.

Metrics depend on the typeface: recalculate with the final Learning Board font
before freezing the sets, by changing `DEFAULT_FONT` and the font package in
`tools/Dockerfile` together — not by passing `--font` once and forgetting.

## kanji_optimizer.py — searcher

Where the verifier checks a given split, this one finds the best split with a
proof of optimality, over every three-way partition of the eligible pictographic
kanji.

```bash
docker compose run --rm kanji-tools python tools/kanji_optimizer.py
```

scipy is in the image. OR-Tools is not: the optional CP-SAT cross-check would
need adding it to `tools/Dockerfile`. That cross-check is still pending, and it
matters more than it sounds — the current verification of the optimizer shares
the geometric-metrics code with `kanji_metrics.py`, so it is not fully
independent.

Division of labour: **the optimizer proposes, the verifier disposes.** Since the
verifier runs on every change, a split the optimizer recommends and the verifier
rejects is a bug in the model, not a difference of opinion.

## Known duplication, not yet fixed

The optimizer carries its own copy of the 49-kanji table instead of importing
`KANJI` from `kanji_metrics`. The shared columns — reading, strokes, morae,
groups, readings, meaning, lesson — are maintained twice; the optimizer adds two
of its own, semantic cluster and imageability.

On 9 September the meanings were translated to English in both files separately.
That is the cost, and it recurs on every content change.

The fix is to import `KANJI` and leave a side table of
`{character: (cluster, imageability)}` here. It was not done in the same pass as
the translation because it touches the optimizer's core and deserves its own
verification rather than riding along with a rename.

## What Unity does with the JSON

`Resources.Load<TextAsset>("kanji_content")` — synchronous, and identical in the
Editor, over Quest Link, and in an Android build. `StreamingAssets/` was the
other candidate and was rejected: there the file lives inside the APK and has to
be read through `UnityWebRequest`, which means asynchronous loading and a
different code path per platform for a 15 KB file.

`KanjiContentController` consumes it: the sets, the reserve pool, the per-kanji
records, and `substitutionTable[set][kanji]` for pre-test replacement. If the
pre-test marks an item KNOWN and its substitute list is empty, that is a
configuration error rather than a runtime case to handle — `kanji_metrics.py`
fails if any experimental kanji is left without a substitute, so it should never
reach a build.

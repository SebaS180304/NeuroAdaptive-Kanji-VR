# Implementation Plan: Kanji pre-test and per-participant substitution (spec §13.2)

## Overview
Before the first visit, the researcher runs a pre-test on a web page served by the
backend. For each primary kanji (sets A, B, C in contract order) the participant answers
**NO / UNSURE / YES**. UNSURE and YES lead to two typed prompts (target reading, meaning).
The answers are auto-checked, and the researcher can flip either result before saving:

| Answer | Classification | Effect |
| --- | --- | --- |
| NO, or neither prompt correct | `UNKNOWN` | stays in the set |
| exactly one of reading / meaning correct | `PARTIALLY_KNOWN` ("barely known") | stays in the set |
| both correct | `KNOWN` | replaced: its best-fit valid reserve kanji is tested next, and so on down the ranking until one is `UNKNOWN` or `PARTIALLY_KNOWN` |

The result is a per-participant table of substitutions. Every session of that participant
then gets its **effective** kanji list, and Unity uses that list instead of the
nominal set.

Previous plan (S4 baseline visuals) archived in `tasks/archive/s4_baseline_*.md`; its
open items are the headset check and the checkpoint boxes.

## Architecture Decisions
- **Researcher web page, not VR.** There is no VR keyboard, and typing kana or romaji on
  a PC is the easy route. One static HTML file with vanilla JS, served by FastAPI. No
  frontend framework.
- **The backend owns the chain logic as a pure function.**
  `next_item(contract, responses) -> item | None` is recomputed from the stored responses
  on every request. It is deterministic, needs no server-side session state, and can be
  unit-tested without a DB. A POST for anything other than the expected next kanji gets
  **409** (double submit, two tabs).
- **Lazy chain (decided 16 Oct):** reserve kanji are tested only when they are next in
  line. Results are cached per participant, so a reserve kanji is asked once at most even
  if it is a candidate in several sets. This deviates from the spec §13.2 wording
  ("screened against the 15 primary and 20 reserve"), so it needs a line in the Plan §9
  log and in the spec.
- **Substitution validity is recomputed against the *effective* set.** The exported
  `substitutionTable` assumes one substitution per set with the other four nominal. With
  two KNOWN kanji in one set, the second substitute has to be checked against the first.
  The backend therefore re-applies the three §13.2 conditions to the current effective
  set, plus two more: the candidate is not already used in any set of this participant,
  and it is not KNOWN.
  - Needed data: per-kanji metrics (already in the contract) and **pairwise glyph
    similarity** (new; exported by `kanji_metrics.py --export` as a `similarity` map).
  - Drift guard: a backend test applies the same rules with zero prior substitutions and
    must reproduce the contract's `substitutionTable` exactly.
- **"Fits the most" = closest to the nominal set (approved 16 Oct):**
  `score = Σ |total(S') − total(S)| / tol` over strokes, morae and groups, plus perimetric
  % deviation / 8. Lowest score wins; ties are broken by reserve order.
- **Single source of the contract.** docker-compose mounts
  `unity-client/Assets/Resources/kanji_content.json` read-only into the backend container.
  No copy goes in `backend/`.
- **Auto-grading:**
  - Reading: accepted as hiragana, katakana or Hepburn romaji, built from targetReading
    with a small kana table.
  - Meaning: case- and space-insensitive, against any comma-separated variant of the
    contract meaning ("leg, foot").
  - The researcher's final booleans are stored next to the auto ones, so how often the
    researcher overrode is measurable.
  - The page **never shows the target answer** to the participant: a PARTIALLY_KNOWN item
    stays in the set, and showing its answer would teach it.
- **Storage:**
  - `kanji_pretest_responses`, one row per participant × kanji: the self-report, the typed
    text, auto and final correctness, and the classification.
  - `kanji_substitutions`, written once in the same transaction as the response that
    completes the chain.
  - Once completed, the pre-test cannot be edited (no endpoint for it), so a session's
    effective list never changes under it.
- **No pre-test, no session (decided 16 Oct).** `participants.pretest_completed_at` is
  set by the response that completes the chain. `POST /sessions` returns **409**
  ("participant must complete the kanji pre-test at /pretest first") while it is null.
  This applies to every visit, not only the first.
  - Consequences: tests and `ws_smoke_test.py` need a participant with a completed
    pre-test (a fixture). The Unity dev participant `DEV_UNITY` has to do the pre-test
    once through the page. Participants already in the DB (the phase-test ones) cannot
    get new sessions.
- **Unity change is small.** `SessionRead` gains `kanji_items` (effective characters, each
  substitute in its original's position so the seeded order is preserved).
  `SessionFlowRunner.ResolveSetAndSeed` / `TrialDebugRunner` use `kanji_items` when
  present, and `content.Set(name)` only for runs with no session. On a 409,
  `SessionBootstrap` logs one clear error with the pre-test URL and does not start the
  flow.

## Dependency graph
```
kanji_metrics.py --export (+similarity) ──► kanji_content.json ──► compose mount
        │
        └─► pretest rules (pure: validity, ranking, chain, grading)
                    │
                    ├─► migration 0004 + models + /participants/{id}/pretest API
                    │           │
                    │           └─► researcher page /pretest
                    │
                    └─► SessionRead.kanji_items ──► Unity SessionBootstrap → runners
```

## Task List
See `tasks/todo.md`.
- Phase 1, pure logic (no DB): Tasks 1–2 → Checkpoint A
- Phase 2, pre-test end to end: Tasks 3–4 → Checkpoint B
- Phase 3, sessions use the result: Task 5 → Checkpoint C
- Task 6: docs and graph

## Risks and Mitigations
| Risk | Impact | Mitigation |
| --- | --- | --- |
| **Reserve kanji have no assembly segments.** Only set A and 四 do (`tools/assembly_segments.py` G table), so a substituted kanji breaks S5 assembly | High | Out of scope here; content task before the dry run (Open question 1). Task 5 checks what S5 does with a missing segment and logs it, so it does not fail silently |
| Backend validity rules drift from `kanji_metrics.py` | Med | Test that reproduces `substitutionTable` exactly from the exported data |
| Greedy chain: an early substitution in a set can block a later one | Low | Logged as `shortcut:`; if a set runs out, the item stays KNOWN and is flagged |
| The session gate breaks existing callers (tests, smoke script, Unity dev Play) | Med | A pytest fixture for a completed participant; one pre-test for `DEV_UNITY`; a clear 409 message |
| Contract regeneration changes the sha in `seed_kanji_items.sql` | Low | Regenerate the seed in the same commit (`tools/kanji_seed_sql.py`) |
| Today is the F5a delivery day | Med | Work on a new branch after the `phase5a-delivery-2026-10-16` tag; touch no adaptation thresholds |

## Decisions (16 Oct)
- Best-fit score: approved as defined above.
- KNOWN kanji with no valid substitute left: it stays in the set and the participant is
  flagged; inclusion follows the MIRAI criterion (spec §13.1).
- No completed pre-test: the backend refuses the session (409) and points to `/pretest`.

## Open Questions
1. Assembly segments for the 20 reserve kanji: who draws the centre lines, and when?
2. Meanings are checked in English (the contract language). Will participants answer in
   English?

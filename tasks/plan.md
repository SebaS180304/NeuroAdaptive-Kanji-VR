# Implementation Plan: week of 26 – 30 Oct 2026 (VR complete, MIRAI presentation)

Written 26 Oct 2026. **Aligned up to: D-F6-99** (`Estado_Actual.md`). **Approved by Sebas, 26 Oct**; B4 and A2 extended with D-F6-89 to D-F6-92 the same evening.
The M3 week's plan is archived in `tasks/archive/fase6_m3_{plan,todo}.md`. Its open items
are carried over here or dropped as listed in the last section.

## Sources of truth
- **`Claude outputs/docs_proyecto/Estado_Actual.md` (the board) comes first.** A decision
  exists only with a number in its §4.
- `Plan_Fases_Replan_7oct.md` §9: the week by day (D-F6-62 to D-F6-66).
- `Guion_Presentacion_MIRAI_30oct.md` §3.3: shots V1–V8, what each needs on Wed 28, and the
  fallback when it is missing.
- `Nota_Entrega_M3_MIRAI.md` §3 item 5: MANU's answers.
- Owners of the inputs: UI/UX designs the hints and the C3 sequence
  (`Diseno_UI_Kanji_Studio_v1.md`, D-F6-63, D-F6-64). Modelado 3D or Contenido produces the
  intermediate shapes and the images (D-F6-30 flow, validated by Sebas). Sebas provides the
  rice-field image (D-F6-86).

## Week rules
- **Priority is the presentation on Fri 30** (D-F6-66). The hints and C3 of set A must be in
  the video. Nothing else (E, set B, the demo scene) may take hours away from them.
- One commit per change, in English. Each message is shown to Sebas first (message file in
  Downloads). Nothing goes on `main`.
- The backend restarts only between runs, never with the headset on. Apply migrations
  **before** restarting (D-F6-79).
- **Every task ends with a stop for Sebas** (the "Stop" line). The next task that depends on
  it does not start until Sebas has seen it.
- Each day ends with a draft `Claude outputs/Borrador_Plan_Fase6_9_<date>.md` that contains
  "Dudas para PM" or "Sin dudas".
- From Fri 30 (D-F6-62) Unity gets fixes only. Content arriving through an integrated flow
  can still go in.

## Dependency graph

```
A1 findings §3 ──► criteria (F5a 8, F6 6) ──► STOP: Sebas sends the M3 note

A2a commits (0009, v2) ─► A2b apply 0009 ─► restart backend ─► A2c O4 fix
                                                     └─► A2d portal (phrase + colour) ─► STOP: v2 run in the headset

UI/UX hint + C3 design ─┐
3D/Contenido shapes ────┼─► B4 set A hints + C3 ─► B5 demo scene (Wed pm) ─► STOP: recording Thu am
images (Sebas OK) ──────┘           └─► B6 captures (Wed pm)

E1 silhouettes/curtains/wind (Tue) ─► re-measure + harness ─► STOP: Sebas approves in headset
E2 rice field (image by Thu pm) ─► STOP: Sebas sees it in headset

A3 set B kanji (when 3D delivers) ─┐
C7 hints + C3 sets B, C ───────────┴─► C8 validation run + freeze (Fri 30, after the talk)
```

## Architecture decisions
- **rules-v2 stays versioned** (done, uncommitted). New sessions run v2 once 0009 is applied
  and the backend restarts. Replay and rebuild use each session's stored version.
- **O4 for an `UNDERCHALLENGED` change (D-F6-80)** uses the rescue table, with one
  difference. If the state is still `UNDERCHALLENGED` after the change, the outcome is always
  `NEUTRAL / PERSISTED`. Today `classify()` would fall into `_distraction_trend` and could
  return `PARTIAL` or `PERSISTED_WORSE`. The fix is a branch of about one line plus its test.
- **Portal for `UNDERCHALLENGED` (D-F6-81, D-F6-92).**
  - The phrase is the definitive one from `Contenido_UI_F-PROFILE.md` §3.8 (template §3.1, clauses §3.2, actions §3.3, outcome labels §3.4). It was delivered on 26 Oct, so the provisional step is skipped. The short state name is "Low challenge (estimated)".
  - The colour is the only provisional part: an existing neutral token until web design defines one. **Defined (D-F6-96):** `--color-state-underchallenged` (Slate), task A2e.
  - The origin line (§3.7) adds "{x} of them could also raise difficulty (rules-v2)." only when a participant has sessions under both rule versions. That needs the rules version of each session in the profile JSON. The rules version is already stored with each decision, so this is read-only, without a migration.
- **Hints and C3 follow `Diseno_UI_Kanji_Studio_v1.md` §9–§11** (delivered 26 Oct). The cue slot and the C3 crossfade already exist with placeholders (`KanjiLearningItem`, `StudioTrialPresenter`).
  - **Hints (§9):** zone A image and zone B strip on the `BoardCanvas`, with 250 ms fade-in, still until the answer, and gone at `ANSWER_SELECTED`. The audio cue becomes a speaker chip (D-F6-89). The text chip goes only where the real image exists (§9.6).
  - **C3 (§10, D-F6-90):** grows from 5.5 s to 7.8 s and ends with the summary strip. The strip is the same layout as the full shape hint. If time runs short, the strip is the one part that can be dropped (back to 5.5 s).
  - **Telemetry (D-F6-91), no new events:** `asset_source` (`AUTHORED` / `PLACEHOLDER`) of the visual hint next to `cue_type`; `asset_source` of each C3 stage; start and duration of the strip in `KANJI_EXPOSED`. The event contract is updated in the same commit.
  - **Assets:** 4 per kanji (P, F1, F2, M; §11.1), 20 for set A, from Modelado 3D and validated by Sebas.
- **The demo scene is a separate scene that is not in the build list** (D-F6-84). Its states
  are set in the Inspector before Play. No experiment code reads it.
- **The rice field is a static textured quad or panel** behind each window, sized to the
  window frame from the eye at 1.60 m. It is not part of the ESL and does not change the
  lighting (D-F6-86). It records whether it is final or a placeholder.
- **Contrast of the peripherals against the rice field (D-F6-93): ≥ 2.7:1**, today's contrast
  against the sky. Measure it from the eye camera in Unity with the same method before and
  after the image goes in: the WCAG ratio of mean relative luminance, silhouette or animal
  pixels against the background pixels around them, at each event's resting pose. If a
  peripheral falls short, only its material colour changes (darker or lighter). The colour is
  the same in every condition and level, and timing, path and shape stay as they are.

## Task list (detail in `tasks/todo.md`)

### A · Last week's leftovers (first)
- [x] A1: findings §3 with MANU's answers; close F5a criterion 8 and F6 criterion 6. **Stop:** Sebas sends the M3 note
- [ ] A2: rules-v2 live: (a) two commits, (b) 0009 then restart, (c) O4 fix, (d) portal phrase and colour; `reason_code` is already D-F6-82. **Stop:** a v2 run in the headset
- [ ] A2e: portal closing (D-F6-96): the `--color-state-underchallenged` token now; the "Not recorded" badge when web design writes it into `design-system.md`; closes F6 criterion 4b. **Stop:** Sebas sees V1.5 and V1.8 in light and dark
- [x] A3: set B kanji objects (D-F6-43), when Modelado 3D delivers. **Stop:** Sebas sees them in S5 in the headset → 27 Oct: integrated, seen and approved in S5

### B · Presentation (Wed 28)
- [ ] B4: set A hints (D-F6-63) and C3 (D-F6-64), chips removed where a real hint exists. **Blocked by** the UI/UX design and the shapes from Modelado 3D. **Stop:** Sebas sees them in the headset
- [ ] B5: demo scene with Unity cameras, outside the build (D-F6-84), shots V1–V8. Plan B: eye view only. **Stop:** recording on Thu 29 morning
- [ ] B6: captures of Unity and the portal for the deck (Wed 28 afternoon). **Stop:** Sebas has the files

### E · Environment adjustments (D-F6-85, D-F6-86); hours never taken from B4
- [ ] E1 (Tue 27): silhouettes closer, curtains drawn further, stronger wind, and one silhouette always in HIGH with the side alternated by the seed (D-F6-99, once UI/UX writes it in `Diseno_Sala_ESL.md`); re-measure angles, `DWELL`, `HEAD_AWAY`, X17, harness. **Stop:** Sebas approves the values in the headset
- [ ] E2 (by Thu 29 pm): rice-field background fitted to the player camera; silhouettes ≥ 2.7:1 against it (D-F6-93, done). E2b: animals "no worse than with the sky" at each position, measured at ESL HIGH; only the window bird and the butterfly change (D-F6-97). **Stop:** Sebas approves the background, the silhouettes and the animals in the headset

### C · Thu 29 and Fri 30
- [ ] C7: hints and C3 for sets B and C (a declared placeholder is allowed). **Stop:** Sebas sees them in the headset
- [ ] C8: Fri 30 after the presentation: full validation run, then the function freeze (D-F6-62, D-F6-66). **Stop:** Sebas confirms the freeze

### D · Noted only, not planned yet
- F4 Unity pieces: the LSL marker output and the new S3 step (D-F6-74), from Mon 2 Nov, as an exception to the freeze.
- Lure kanji (D-F6-71): only if MIRAI approves on Fri 30 (A-11); an exception to the freeze, before 13 Nov.

## Checkpoints
- **Mon 26 evening:** A1 delivered; the A2a messages shown.
- **Tue 27 evening:** A2 live with a v2 run; E1 approved in the headset; harness green.
- **Wed 28 night:** B4 for set A in the headset; B5 ready or plan B declared; B6 delivered.
- **Thu 29 morning:** the video build is frozen for recording (no commits until it is recorded).
- **Fri 30:** C8 run clean (`verify_*` with 0 discrepancies, 72 Hz); freeze declared.

## Risks and Mitigations
| Risk | Impact | Mitigation |
| --- | --- | --- |
| UI/UX design or the 3D shapes for set A arrive late on Wed | High (V5 and V6 are mandatory) | **Cut-off Wed 28 at 12:00 (D-F6-87).** Prepare the loading path and the chip switch beforehand with the placeholders, so integration is then only adding assets. If they are missing at 12:00, V5 is dropped from the video, V6 is recorded with a hint requested with *Hint*, and integration continues afterwards with a declared placeholder |
| The backend is restarted before 0009 | Med | A2b runs the migration first and checks `\d adaptation_decisions` before restarting |
| v2 has never run live, only in replay | Med | The A2 stop is a full run in the headset with `verify_*` |
| E1 changes MEDIUM motion and the peripheral angles again | Med | Re-measure E13, X13 and the D7 probe in the same task. Declare it in spec v1.4 (D-F6-85) |
| Sebas has to validate a lot (hints, shapes, E1, set B) during F4 S1 | High | The B and C sets and the reserve are "if there is time" (D-F6-66). They never block set A |
| A commit on Thu morning breaks the video build | High | Freeze on Thu morning until the recording is done |

## What happens to the open items of the M3 plan
- Task 11b, Checkpoint D and the definitive `UNDERCHALLENGED` colour: only if time is left, within 16–20 Nov at the earliest (D-F6-83).
- Tasks 13, 14, 16 and 32: done (MANU `678b7806`, run `2dd53450`, tags D-F6-78). Task 15 becomes A1.
- Task 17 / R-6: the change list is done. The full spec v1.4 document is written by PM on 2–6 Nov, and development reviews it (D-F6-88).
- A-2 (a hint requested inside the O4 window): still open with Sebas.

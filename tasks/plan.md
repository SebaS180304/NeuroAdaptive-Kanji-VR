# Implementation Plan: week of 26 – 30 Oct 2026 (VR complete, MIRAI presentation)

Written 26 Oct 2026. **Aligned up to: D-F6-104** (`Estado_Actual.md`). **Approved by Sebas, 26 Oct**; B4 and A2 extended with D-F6-89 to D-F6-92 the same evening. **Revised Tue 27 Oct** (not yet approved): E1 follows the §10.4 rule (D-F6-100, D-F6-101; D-F6-99 is gone), B4b gets the new C3 times (D-F6-103, D-F6-104), new B4c (SDF morph) and new S1 (spec change rows).
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

Tue 27 (design §9–§11 is in; images are not):
B4a hints with placeholders ─┐
B4b C3 crossfade (7.8 s) ────┴─► Wed 28: 20 set A images (cut-off 12:00) ─► STOP: Sebas sees them in headset
                                         └─► B5 demo scene (Wed pm) ─► STOP: recording Thu am
                                         └─► B6 captures (Wed pm)
B4b ─► B4c SDF morph, one kanji (needs 16-bit SDFs, question 14) ─► STOP by Thu 29 18:00, else crossfade stays

E1 silhouettes/curtains/wind + §10.4 rule ─► STOP (before 16:45 or after 18:00) ─► re-measure (angles, DWELL,
   HEAD_AWAY, X17, D7 probe in MEDIUM) + harness ─► S1 spec rows (D-F6-85 row needs the approved values)

A3 set B kanji ✅ (ad19b05, seen in S5)
C7 hints + C3 sets B, C ─► C8 validation run + freeze (Fri 30, after the talk)
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
  - **C3 (§10, D-F6-90, D-F6-103):** 7.8 s per kanji with one timetable for crossfade and morph: object shrinks while F1 fades in (0–0.5 s), F1 still 1.8 s, transition 800 ms, F2 still 1.8 s, transition 800 ms, kanji from 5.7 s, summary strip in at 6.0 s (300 ms fade), out at 7.5 s (300 ms). Both transitions use *smootherstep* w = 6u⁵ − 15u⁴ + 10u³ over 0.8 s (§10.1); in the crossfade w is B's opacity. If time runs short, the strip is the one part that can be dropped.
  - **Telemetry (D-F6-91, D-F6-104), no new events:** `asset_source` (`AUTHORED` / `PLACEHOLDER`) of the visual hint next to `cue_type`; `asset_source` of each C3 stage; start and duration of the strip and **`c3_transition` (`CROSSFADE` / `SDF_MORPH`)** in `KANJI_EXPOSED`. The event contract is updated in the same commit.
  - **SDF morph (D-F6-103, B4c)** sits behind the crossfade: one shader blends two 512² R16F fields, d(t) = (1 − w)·d_A + w·d_B, ink where d < 0, edge AA with `fwidth`, colour `#F4F1EA`, no outline. The kanji field comes from the board glyph in the same box, and at w = 1 the glyph swaps in on the same frame. **Per set, never per kanji:** a session's five `KANJI_EXPOSED` all carry the same `c3_transition`. A set switch (serialized, off by default) chooses it; if one pair fails a §10.1 check, the whole set stays on crossfade.
- **ESL selection rule (§10.4, D-F6-100, D-F6-101)** replaces the plain tier draw only for the clock and the movers:
  - `WallClock_T3`, `OutsideFigureLeft_T3`, `OutsideFigureRight_T3` go to tier 2; keys keep their names.
  - MEDIUM: the `selection:MEDIUM` generator picks the curtain side; the silhouette is the opposite window. Props: 3 × T1 + clock always + 0–2 other T2 (total 4–6).
  - HIGH: MEDIUM's movers plus the other curtain (3 movers), silhouette side derived from MEDIUM's draw, not HIGH's. Props: 3 × T1 + clock + rest of T2, then T3 (total 7–10).
  - Done inside `EnvironmentalStimulationController.ActivateGroup` as the smallest branch that fixes the clock and the mover pair; the `ESL_*.asset` ranges stay. `ENVIRONMENT_APPLIED` already lists `active_movers`, so no new telemetry.
  - The silhouette walks 8 s and hides 5 s for as long as the level lasts, hidden by a wall, not by its curtain. Its pause is the only thing Sebas may tune at the stop.
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
- [x] B4a (Tue 27, real set A images): hints: §9 zones and cells, audio indicator (D-F6-89), `asset_source` next to `cue_type` (D-F6-91); the chip goes only where the image is `AUTHORED`
- [x] B4b (Tue 27, real set A forms): C3 crossfade with the §10 times (800 ms, 1.8 s, strip 6.0–7.8 s, D-F6-90), *smootherstep* (§10.1), `c3_transition` in `KANJI_EXPOSED` (D-F6-104)
- [ ] B4 (Wed 28): the 20 real set A images go in (cut-off 12:00, D-F6-87; if missing, V5 leaves the video and V6 uses a requested hint). **Stop:** Sebas sees them in the headset
- [ ] B4c (Wed 28, after B4b, own task): SDF morph on one test kanji, three §10.1 checks, then per set. **Stop:** Sebas sees it in the headset by **Thu 29 18:00**, else the crossfade stays (D-F6-103)
- [ ] B5: demo scene with Unity cameras, outside the build (D-F6-84), shots V1–V8. Plan B: eye view only. **Stop:** recording on Thu 29 morning
- [ ] B6: captures of Unity and the portal for the deck (Wed 28 afternoon). **Stop:** Sebas has the files

### E · Environment adjustments (D-F6-85, D-F6-86); hours never taken from B4
- [x] E1 (Tue 27, first): silhouettes closer (torso up), curtains drawn 25 % / 40 %, wind 9 / 12 cm, and the §10.4 rule (D-F6-100, D-F6-101): clock and silhouettes at tier 2, MEDIUM = clock + one curtain + opposite silhouette, HIGH = clock + both curtains + that silhouette; new harness case and E3. Re-measure angles, `DWELL`, `HEAD_AWAY`, X17, and the clock–picture `DWELL` in MEDIUM with the D7 probe (D-F6-102); check the silhouette hides behind a wall. **Stop (one, before 16:45 or after 18:00):** Sebas approves the values and the continuous silhouette in MEDIUM; its pause is tuned if it distracts too much
- [ ] E2 (by Thu 29 pm): rice-field background fitted to the player camera; silhouettes ≥ 2.7:1 against it (D-F6-93, done). E2b: animals "no worse than with the sky" at each position, measured at ESL HIGH; only the window bird and the butterfly change (D-F6-97). **Stop:** Sebas approves the background, the silhouettes and the animals in the headset

### C · Thu 29 and Fri 30
- [ ] C7: hints and C3 for sets B and C (a declared placeholder is allowed). **Stop:** Sebas sees them in the headset
- [ ] C8: Fri 30 after the presentation: full validation run, then the function freeze (D-F6-62, D-F6-66). **Stop:** Sebas confirms the freeze

### S · Spec change list (mine, `Claude outputs/Cambios_Spec_v1_4.md`)
- [ ] S1: rows for D-F6-85, D-F6-86, D-F6-97, D-F6-98, D-F6-100, D-F6-101, D-F6-103 and D-F6-104, with the two declarations (MEDIUM changes; the butterfly is seen less against the rice field). Row 17 is corrected by D-F6-102 (the clock is now in MEDIUM). The D-F6-85 row waits for the E1 values. **Stop:** Sebas reads it before PM takes it (D-F6-88)

### D · Noted only, not planned yet
- F4 Unity pieces: the LSL marker output and the new S3 step (D-F6-74), from Mon 2 Nov, as an exception to the freeze.
- Lure kanji (D-F6-71): only if MIRAI approves on Fri 30 (A-11); an exception to the freeze, before 13 Nov.

## Checkpoints
- **Mon 26 evening:** A1 delivered; the A2a messages shown.
- **Tue 27, one headset stop before 16:45 or after 18:00** (Sebas is on the cap 17:00–18:00): E1 values and the MEDIUM silhouette approved. A3 needs no stop (seen in S5 on 26 Oct).
- **Tue 27 evening (19:00 cut):** E1 committed with the re-measurements and harness green; B4a and B4b on placeholders with harness green; S1 rows written except D-F6-85 if the stop slips; day draft with questions or "Sin dudas".
- **Wed 28 12:00:** set A image cut-off (D-F6-87).
- **Wed 28 night:** B4 for set A in the headset; B5 ready or plan B declared; B6 delivered; B4c on one kanji if the 16-bit fields exist.
- **Thu 29 18:00:** B4c approved or dropped (crossfade stays).
- **Thu 29 morning:** the video build is frozen for recording (no commits until it is recorded).
- **Fri 30:** C8 run clean (`verify_*` with 0 discrepancies, 72 Hz); freeze declared.

## Risks and Mitigations
| Risk | Impact | Mitigation |
| --- | --- | --- |
| UI/UX design or the 3D shapes for set A arrive late on Wed | High (V5 and V6 are mandatory) | **Cut-off Wed 28 at 12:00 (D-F6-87).** Prepare the loading path and the chip switch beforehand with the placeholders, so integration is then only adding assets. If they are missing at 12:00, V5 is dropped from the video, V6 is recorded with a hint requested with *Hint*, and integration continues afterwards with a declared placeholder |
| The backend is restarted before 0009 | Med | A2b runs the migration first and checks `\d adaptation_decisions` before restarting |
| v2 has never run live, only in replay | Med | The A2 stop is a full run in the headset with `verify_*` |
| E1 changes MEDIUM motion and the peripheral angles again | Med | Re-measure E13, X13 and the D7 probe in the same task. Declare it in spec v1.4 (D-F6-85, D-F6-100) |
| The E1 stop misses both windows (before 16:45, after 18:00) | Med | E1 goes first today. The rule commit does not wait for the stop (decided, D-F6-101); only the values and the pause do |
| The SDF fields are not 16-bit by Wed (the script is in Modelado 3D's folder) | Low (crossfade is the base) | Question 14 for PM. B4c does not start without R16F fields; the Thu 18:00 cut decides |
| A morph pair fails a §10.1 check | Low | Fix that field's spread, or the whole set stays on crossfade (never mixed in a set) |
| Sebas has to validate a lot (hints, shapes, E1, set B) during F4 S1 | High | The B and C sets and the reserve are "if there is time" (D-F6-66). They never block set A |
| A commit on Thu morning breaks the video build | High | Freeze on Thu morning until the recording is done |

## What happens to the open items of the M3 plan
- Task 11b, Checkpoint D and the definitive `UNDERCHALLENGED` colour: only if time is left, within 16–20 Nov at the earliest (D-F6-83).
- Tasks 13, 14, 16 and 32: done (MANU `678b7806`, run `2dd53450`, tags D-F6-78). Task 15 becomes A1.
- Task 17 / R-6: the change list is done. The full spec v1.4 document is written by PM on 2–6 Nov, and development reviews it (D-F6-88).
- A-2 (a hint requested inside the O4 window): still open with Sebas.

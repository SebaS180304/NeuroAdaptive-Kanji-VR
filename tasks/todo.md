# Todo: week of 26 – 30 Oct (VR complete, MIRAI presentation)

Plan: `tasks/plan.md`. Previous list: `tasks/archive/fase6_m3_todo.md`.
**Aligned up to: D-F6-104** · plan approved by Sebas, 26 Oct; B4 and A2 extended with D-F6-89 to D-F6-92; **revised Tue 27** (E1 with §10.4, B4b with the D-F6-103 times, new B4c and S1; waiting for Sebas's OK) (`Estado_Actual.md`, the board; it wins over this list).

**Tue 27 order:** E1 → headset stop (before 16:45 or after 18:00; Sebas on the cap 17:00–18:00) → B4a → B4b → S1. Cut at 19:00 with the day draft.
Every commit gets a message file in Downloads, is shown to Sebas first, and holds one change.
Every task ends with a **Stop**: Sebas sees the result before the next dependent task starts.

---

## A · Last week's leftovers (first)

### [x] A1: Phase-test findings §3 and criteria evidence (Mon 26)
- [ ] `Claude outputs/Hallazgos_Prueba_Fase_F5a.md` §3: replace "Pendiente" with MANU's five answers (`Nota_Entrega_M3_MIRAI.md` §3 item 5). Cross each answer with the data:
  - "noticed the props and the bird" → the block changes and the peripherals in §1;
  - "no hints appeared" → 0 `HINT_REQUESTED`, LAL never rose;
  - "confuses look-alike kanji (月/火)" → a new finding for the pilot, linked to D-F6-71.
- [ ] Per-trial notes from the paper sheet (`Prueba_Fase_23oct_Consentimiento_y_Observacion.pdf`, pp. 3–4): read them. If the sheet has none, declare "sin notas por trial".
- [ ] §2: move or add findings if the answers change them, and close the classification.
- [ ] `Evidencia_Criterios_F5a.md` criterion 8 and `Evidencia_Criterios_F6.md` criterion 6: 🟡 → ✅, citing §3.
- [ ] Headers "Alineado hasta: D-F6-86".
**Verify:** the three docs agree with each other and with the M3 note §3. **Scope:** XS (docs only)
→ Done 26 Oct (docs, gitignored, no commit). §3 has MANU's five answers crossed with the data. The repo PDF is the blank template, so it is declared that there are no per-trial notes. New finding P5 (look-alike kanji, linked to D-F6-71). F5a criterion 8 and F6 criterion 6 are ✅.
**Stop:** Sebas sends the M3 note.

### [x] A2: rules-v2 live (D-F6-59, D-F6-79 to D-F6-82)
Order matters: (a) → (b) → (c) and (d) → run.
- [x] (a) Two commits, with the messages already shown on 26 Oct: `feat(db)` migration 0009 with `schema.sql`, then `feat(adaptation)` behavior-v2/rules-v2 with tests and `EVENT_CONTRACT.md`. pytest 227/227 before each.
- [x] (b) Between runs, headset off: `alembic upgrade head` → check `\d adaptation_decisions` (VARCHAR(16), new CHECKs) and `SELECT count(*) FROM v_adaptations` (180) → **only then** restart the backend.
- [x] (c) O4 (D-F6-80): in `outcome.classify()`, still `UNDERCHALLENGED` after the change → always `NEUTRAL / PERSISTED` (no trend). `STABLE` → `RESOLVED` and the other states → `SWITCHED` already work. Add 3 tests (one per row). Update the docstring table and `Planteamiento_Tecnico_F5a.md` §5.3.
- [x] (d) Portal (D-F6-81, D-F6-92):
  - `profileText.ts` gets the **definitive** `UNDERCHALLENGED` phrase from `Contenido_UI_F-PROFILE.md` §3.8. Use the §3.1 template, the §3.2 clauses (FAST, NO_ENVIRONMENT, both), the §3.3 actions (LAL down, ESL up) and the §3.4 outcome labels ("Held after", "Still low challenge after"). §3.5 and §3.6 apply as they are.
  - `EstimatedState.tsx` shows the short name "Low challenge (estimated)" where the state has visible text, with the enum in the tooltip. The colour comes from an existing neutral token and is marked provisional until web design defines it (D-F6-81).
  - The §3.7 origin line gets "{x} of them could also raise difficulty (rules-v2)." only when the participant has both `rules-v1` and `rules-v2` sessions. The profile endpoint carries each session's rules version (from `adaptation_decisions.rules_version`, read only, no migration).
  - Vitest: the phrase for each clause and action, the origin line with mixed, v1-only and v2-only participants, and the short name. pytest: the endpoint field.
- [x] `reason_code` `UNDERCHALLENGED_ENVIRONMENT` with the LAL at LOW (D-F6-82): already in the code. Only check that the test exists.
→ 26 Oct, **stop passed**: v2 run `add29817` (`DEV_UNITY`, set A): 20/20 decisions `behavior-v2`/`rules-v2`; S7-009 `UNDERCHALLENGED_FAST` LAL MEDIUM→LOW `APPLIED`, O4 `NEUTRAL/PERSISTED`; then `AT_LIMIT`; `verify_*` 0; ≈ 71 fps S5–S8 (start-up hitches S1 0.9 s, S2 1.8 s; S7 worst 223 ms, watch in C8).
→ 26 Oct: `0e912ac` (0009), `0653424` (v2). 0009 applied at 07:33 UTC with no session `IN_PROGRESS`: VARCHAR(16), new CHECKs, `v_adaptations` 180 rows. Backend restarted and running `behavior-v2` / `rules-v2`; restarted again for (d). (c) and (d): pytest 231/231, Vitest 136/136, `tsc` clean. The "both" groups are split by `evidence` (`FAST+NO_ENVIRONMENT`, §3.2). Profiles recomputed `--all`, `--check` 0 differences.
**Verify:** pytest and Vitest green; `graphify update .`.
**Stop:** a v2 run in the headset (S1 → S9, set A, `BEHAVIOR_ADAPTIVE`). Each decision has `estimator_version = behavior-v2`, `verify_adaptation` and `verify_projection` show 0 discrepancies, and the session looks right in the portal. Any `UNDERCHALLENGED` change shows the §3.8 phrase. MANU's profile (v1 only) keeps its origin line unchanged.
**Scope:** M (two commits: backend O4 + profile field; dashboard phrase, name and origin line)

### [x] A2e: Portal closing (D-F6-96)
Source: `design-system.md`, written by web design.
- [x] **Colour, now:** add `--color-state-underchallenged` to `dashboard/src/styles/tokens.css` (`#565B62` light, `#9AA0A8` dark, as in the design-system row). Put it in `STATE_DOT` of `EstimatedState.tsx` and remove the provisional comment. Check the other places that draw state colours: the timeline's estimated-state lane and its legend.
  - The token is in `Claude outputs/design-handoff/design-system.md` (row of 26 Oct, 16:45) but **not yet in the skill's copy** (`.claude/skills/research-dashboard-conventions/references/design-system.md`, last changed 21 Oct). Both are web design's; I only tell Sebas, and never edit either.
- [x] **"Not recorded" badge, only once it is in `design-system.md`:** D-F6-16 form, validated on canvas v41 (V1.8, Tweak `manySessions`): 1 px dotted border, no fill, no mark, at the end of the badge row. It replaces the `983aaa7` form in `LearnerProfile.tsx` (the comment at the badge). Until web design writes it, nothing is applied (CLAUDE.md: visual values only from the design system).
- [x] Vitest: state dot class for `UNDERCHALLENGED`, and the badge's class. Playwright `participants.spec.ts` green. Captures of V1.5 and V1.8 in light and dark.
- [x] `Evidencia_Criterios_F6.md` criterion 4b: drop "(badge pendiente de validar)" and cite the commit.
→ 26 Oct: `2236741` syncs the skill's `design-system.md` from design-handoff (Sebas). The token is in `tokens.css` (three blocks) and `STATE_DOT`. The timeline tooltip uses `stateLabel` ("Low challenge (estimated)"). The badge already had the validated form; `OutcomeChip.test.tsx` now pins it. Contrast tests: 6.9 / 6.4 / 6.5 as in design-system.md. Vitest 141/141, `tsc` clean. Playwright 38/40: two failures not caused by this change. `quality.spec` times out because `/research/quality` takes ≈ 20 s. `sessions.spec:125` assumes the newest adaptive session has changes, and ABUDSITO `77a6c8af` (23 Oct) has none.
**Verify:** Vitest, `tsc`, Playwright green; the token's contrast as stated in its row.
**Stop:** Sebas sees V1.5 (a v2 session) and V1.8 (MANU and a participant with "Not recorded") in light and dark.
**Deps:** the colour can go any time; the badge waits for web design. It never takes hours from B4. **Scope:** S (two commits: colour; badge)

→ 26 Oct: **stop passed**. Sebas checked V1.5 (`add29817`) and V1.8 (`DEV_UNITY`, MANU) and everything looks right.

### [x] A3: Set B kanji objects (D-F6-43): when Modelado 3D delivers 山 門 女 手 雨
- [x] Only with all five FBX in `KanjiLessonAssets/NN_*/export/` (all five or none, as in D-F6-26).
- [x] Integrate them the way set A was integrated (Task 23 of the archived list): `object_source = BLENDER_FBX`. Use the harness case for poses and S5 approach.
**Verify:** harness green; one capture per object from the eye.
**Stop:** Sebas sees set B in S5 in the headset.
→ Done: menu «Integrar objetos del set B», harness X18 (envelopes per FICHA, no animation, no rotated child; 07 門's leaves stay shut) and X18b (set C still PLACEHOLDER), 95/95. Eye captures checked: 09 手 palm to the player, thumb on their left; 08 女 nose only. **Seen and approved by Sebas in S5.**
**Deps:** the delivery. Never ahead of B4. **Scope:** S

---

## B · Presentation (D-F6-66, Wed 28)

### [ ] B4: Set A visual hints (D-F6-63) and C3 (D-F6-64)
**Blocked by:** the UI/UX design (how each hint looks per trial type and level, the C3 sequence) and the intermediate shapes and images from Modelado 3D or Contenido, validated by Sebas (D-F6-30). Until they arrive, only the prep steps run. **Cut-off: Wed 28 at 12:00 (D-F6-87).** If they are missing by then, V5 is dropped, V6 uses a hint requested with *Hint*, and B4 continues after the video with a declared placeholder.
Design: `Diseno_UI_Kanji_Studio_v1.md` §9–§11 (delivered 26 Oct). Assets: P, F1, F2 and M per kanji (§11.1), 20 for set A.

**Tue 27:** B4a and B4b run end to end on placeholders (labelled boxes in the exact zones and times), so on Wed only the 20 PNGs are dropped in and the cells flip to `AUTHORED`. Files: `StudioTrialPresenter.cs` (zones, chip, indicator), `S5LearningBlockController.cs` + `KanjiDiscoveryController.cs` (C3), `TelemetryContract.cs`, `database/EVENT_CONTRACT.md`, `Phase2TestHarness.cs`.

**B4a · Hints (D-F6-63, D-F6-89, D-F6-91), one commit**
- [x] Prep (Tue 27, with placeholders): the per-kanji asset path (`A_月_P.png`, …) and the `BoardCanvas` zones:
  - zone A image (−560, 60), 320 × 320 u;
  - zone B strip (−150, −270): 4 boxes of 150 u with arrows, plus the "?" box;
  - audio indicator (330, −370), 120 × 90 u.
  Box style, ink and colours as §9.2–§9.3.
- [x] Cells per §9.1:
  - T1 HIGH: partial strip, object → F1 → ? → ?;
  - T2 HIGH: M in zone A;
  - T3 MEDIUM: P in zone A;
  - T3 HIGH: full strip in zone B, zone A empty.
  LOW and OFF are unchanged. A request and the proactive cue (D9) show the same thing.
- [x] Timing (§9.4): 250 ms fade-in on the request frame or on `TRIAL_STARTED`; still until the answer; gone at `ANSWER_SELECTED` without a fade.
- [x] Audio indicator (D-F6-89): a speaker icon chip with no text or sound, visible from the audio start until 300 ms after it ends. It replaces the "reading audio" chip in audio-only cells and sits next to the image in HIGH.
- [x] Text chip (§9.6): hidden only in cells whose image is `AUTHORED`. A cell still on a placeholder keeps its current chip.
- [x] Telemetry (D-F6-91): `asset_source` (`AUTHORED` / `PLACEHOLDER`) of the visual hint next to `cue_type`, in every trial with a hint. Update `EVENT_CONTRACT.md` and the projection or `verify_*` if they read cue fields.
- [x] Harness: zones inside the canvas and clear of the Hint button; the chip/indicator rule per cell; `asset_source` per cell; no motion between fade-in and answer.
→ 27 Oct: done **with the real set A images** (Sebas: Modelado 3D finished the 20; COORDINACION_27oct.md §0, all «Referencia aprobada»). Menu «Integrar pistas del set A» copies only `A_NN_CODE_{P,F1,F2,M}.png` (for 車 the `A_02_KURUMA_*`; the `A_01_` and `A_03_` drafts in `pistas/` are not taken) to `Art/KanjiLessonAssets/Hints/`, imports them as sprites (1024, no mipmaps, HQ compression) and assigns them to new `KanjiLearningItem` fields (P is the existing `visualAssociationSprite`). Cell logic in `HintCells` (pure); drawing in `StudioTrialPresenter` (zone A, strip with ? / glyph, speaker chip from `SpeakerSprite`, 250 ms fade, hidden at the answer and in `Clear`). `ITrialPresenter.ShowCue` takes the target. `TRIAL_COMPLETED.cue_asset_source` (AUTHORED / PLACEHOLDER / null), `EVENT_CONTRACT.md`. Harness X20 (cells, set A AUTHORED, KANJI_HITO PLACEHOLDER, zones in the board, strip ends at x 240): 99/99. Edit-mode render from the eye checked (meaning link, partial strip, speaker chip); full strip glyph and the fade not seen yet: headset.

**B4b · C3 crossfade with the summary strip (D-F6-64, D-F6-90, D-F6-91, D-F6-103, D-F6-104), one commit**
- [ ] §10 timeline (27 Oct version, the same for crossfade and morph), from the moment the object is back on the board:
  - 0.0–0.5 s: the object shrinks 1 → 0 (ease in-out) while F1 fades in;
  - 0.5–2.3 s F1 still (1.8 s) → **2.3–3.1 s transition (800 ms)** → 3.1–4.9 s F2 still → **4.9–5.7 s transition** → kanji still from 5.7 s;
  - the strip fades in at **6.0 s** (300 ms), stays until 7.5 s, fades out (300 ms);
  - S5 continues at 7.8 s. The same in every condition and level.
- [ ] Curve (§10.1): *smootherstep* w = 6u⁵ − 15u⁴ + 10u³, u = (t − t₀) / 0.8 s, clamped; B's opacity = w, A's = 1 − w. Outside the two 800 ms windows nothing animates.
- [ ] Rule 9: no sound; ink of each form ≤ 1.5× the kanji's area; form colour `#F4F1EA` and the glyph's stroke.
- [ ] Telemetry in `KANJI_EXPOSED`: `asset_source` per stage; the strip's start and duration; **`c3_transition` = `CROSSFADE`** (D-F6-104). A missing form keeps its placeholder with the same times and records `PLACEHOLDER`. `EVENT_CONTRACT.md` §5 in the same commit; check the projection only stores the payload (no migration expected; if one is needed, stop and tell Sebas).
- [ ] Harness: stage times add to 7.8 s with the transitions at 2.3 and 4.9 s; w(0) = 0, w(0.5) = 0.5, w(1) = 1 and monotonic; the strip is the same layout as the full shape hint; `c3_transition` present; S5 ≈ +12 s over the 23 Oct run.
- [ ] If time runs short, the strip is the one part that can be dropped, and Sebas is told.

**B4 · Wed 28: real set A images (cut-off 12:00, D-F6-87)**
- [ ] Drop the 20 validated PNGs (P, F1, F2, M per kanji) into the B4a/B4b paths; the matching cells flip to `AUTHORED` and lose their chip. Any image missing at 12:00 stays a declared `PLACEHOLDER`; if C3 forms are missing, V5 leaves the video and V6 is recorded with a hint requested with *Hint*.
- [ ] Check §9.2's zone A width note (prompt text beyond x −380 → zone A at 280 u) with the real images.

**Verify:** harness green; captures from the eye of a T3 HIGH strip, a T2 HIGH scene, the audio indicator (V6) and one C3 with the strip (V5).
**Stop:** Sebas sees them in the headset (Wed 28).
**Scope:** M + M (two commits on Tue) + S (assets on Wed)

### [ ] B4c: SDF morph for C3 (D-F6-103, D-F6-104): Wed 28, after B4b, its own task
**Blocked by:** 16-bit fields (512², one channel R16F, spread ≥ 25 % = 128 px, kanji from the board glyph in the same box). `tools/png_a_sdf.py` lives in Modelado 3D's folder and today writes 8-bit PNG with a 32 px range (question 14 for PM: who adjusts it).
- [ ] One test kanji only (proposed: 月, the smoothest F2 → kanji per Modelado 3D's guides). Import its three fields (F1, F2, kanji) as R16F, no compression, no mipmaps.
- [ ] Shader: d(t) = (1 − w)·d_A + w·d_B, ink where d < 0, edge AA with `fwidth(d)`, colour `#F4F1EA`, opacity 1, no outline/shadow/glow; the same *smootherstep* and windows as B4b; at w = 1 swap to the TMP glyph on the same frame.
- [ ] The three §10.1 checks at w = 0, 0.25, 0.5, 0.75, 1: (1) ink area between 70 % of the smaller form and 1.5× the kanji; (2) last frame within 1 px of the board glyph, from an eye capture; (3) no isolated blob smaller than the stroke. Results in the day draft.
- [ ] Switch **per set** (serialized, off by default): all five kanji of a set use the same transition; `c3_transition` = `SDF_MORPH` in every `KANJI_EXPOSED` of that session. Harness: one value per session; the times still add to 7.8 s.
- [ ] Only if Sebas approves the test kanji: the other four set A fields, the same checks, then the set switch on.
**Stop:** Sebas sees the test kanji in the headset. **Cut: Thu 29 18:00**; if not approved, the crossfade stays and the morph is a later improvement. The video uses the morph only if it is approved before the Thu morning recording.
**Scope:** M (shader + material + switch + harness)

### [ ] B5: Demo scene with Unity cameras, outside the build (D-F6-84): Wed 28 afternoon, **after** B4
- [ ] A new scene, not in Build Settings. It contains the room prefab and the cameras for shots V1–V8 (`Guion_Presentacion_MIRAI_30oct.md` §3.3).
- [ ] States fixed before Play from the Inspector: ESL level, kanji, trial, adaptation before and after (V7, with `UNDERCHALLENGED` if A2 is live).
- [ ] Opening card: "demonstration scene".
- [ ] Plan B, if it is not ready by Wed night: the eye view only. Tell Sebas which shots fall back.
**Verify:** the build scene list is unchanged; the harness is green.
**Stop:** the recording on Thu 29 morning, with the build frozen until it is done.
**Scope:** S

### [ ] B6: Captures for the deck (Wed 28 afternoon)
- [ ] Unity: the room at the 3 ESL levels, the animals, S5 approach, a set A hint and C3 (if B4 is done).
- [ ] Portal: the session decisions and the Learner Profile (MANU `678b7806`, and a v2 session if A2 has run). The provisional phrase is visible and declared.
**Stop:** Sebas has the files (folder in `Claude outputs/`). **Scope:** XS

---

## C · Thu 29 and Fri 30

### [ ] C7: Hints and C3 for sets B and C
- [ ] Same path as B4. A missing asset stays a declared placeholder (`asset_source`).
**Stop:** Sebas sees them in the headset. **Deps:** B4, assets. **Scope:** S

### [ ] C8: Validation run and function freeze: Fri 30, **after** the presentation (D-F6-62, D-F6-66)
- [ ] Whole harness green.
- [ ] Run S1 → S9 in the headset at 72 Hz with `verify_*` 0 discrepancies, rules-v2, the hints and C3 of set A, and the E1/E2 changes.
- [ ] Declare the freeze. From here on, Unity gets fixes only.
**Stop:** Sebas confirms the freeze. **Scope:** XS (no code)

---

## F · For another day (not this week's plan)

### [ ] F1: Two Playwright tests that fail on today's data (found 26 Oct, A2e)
- [ ] `tests/e2e/quality.spec.ts`: `/research/quality` takes ≈ 20 s with 54 projected sessions; the page waits 5 s. Look at the query first (a slow check or a missing index), not at the test's timeout.
- [ ] `tests/e2e/sessions.spec.ts:125`: it takes the newest completed adaptive session and expects the Adaptations table, but ABUDSITO `77a6c8af` (23 Oct) has 0 changes and the tab shows its empty text. Pick a session that has changes (and skip when none has), or test the empty text too.
**Verify:** `npx playwright test` 40/40. **Scope:** S (backend query + one test). It never takes hours from B4.

## D · Noted only, not planned yet
- F4 Unity pieces: the LSL marker output and the new S3 step (D-F6-74), from Mon 2 Nov, as an exception to the freeze.
- Lure kanji (D-F6-71): only if MIRAI approves on Fri 30 (A-11).

---

## E · Environment adjustments (D-F6-85, D-F6-86): never at the expense of B4

### [x] E1: Silhouettes, curtains, wind and the §10.4 rule (Tue 27, first task of the day)
Sources: D-F6-85, D-F6-100, D-F6-101, D-F6-102; `Diseno_Sala_ESL.md` §10.4 (replaces D-F6-99) and §10.5. Files: `EnvironmentalStimulationController.cs`, `EnvironmentProp` tiers in the room scene, `EnvironmentMotion.cs` (silhouette path), `CurtainWind.cs` + shader, `Phase2TestHarness.cs`, `PeripheralContrast.cs`, `LayoutOfRecord`.

**E1a · Values to try (two each, chosen live in Play mode, committed only after the stop)**
- [x] Read the current values first: silhouette path (distance behind the sill), curtain sheet extents, `CurtainWind` A = 0.06 m.
- [x] Silhouettes closer to the window until torso and head show above the sill (two distances).
- [x] Curtains drawn toward the walls by **25 %** and **40 %** of the sheet width.
- [x] Wind A = **0.09 m** and **0.12 m**; ripple, gust, alpha 0.90, ≤ 0.5 Hz and no opacity motion unchanged (D-F6-61). The harness limit "A ≤ 0.06" becomes the approved A.
→ 27 Oct: ready for the stop with `EnvironmentValuesPreview` (keys L level, S distance, D lowered ground, C curtains, W wind; nothing saved). Read: silhouette root z 7.5, walk from |x| 3.7 outward 2.18 m in 8 s, pause 5 s; sheet |x| 2.22–3.17 under a bar to 3.49; A 0.06. Geometry (eye (0, 1.60, 0), wall z 3.96, open half |x| 1.65–2.48, sill y 0.69): **today the walk starts in view** (|x| 3.7 is inside the open half at 7.5 m; only a curtain hid it). Options: z 5.5 → sill cuts the figure at 0.34 m, walk |x| 1.97 → 4.15, visible ≈ 5.5 s; z 4.8 → cuts at 0.50 m, |x| 1.68 → 3.86, ≈ 4.9 s. **Torso up (cut ≈ 0.65 m) is not reachable by distance alone** with the sill at 0.69 m and the eye at 1.60 m; D lowers the outside ground (−0.31 m at 5.5, −0.15 m at 4.8) as a proposal. Curtains 40 % hang 6 cm past the bar end.

**E1b · §10.4 selection rule (D-F6-101), its own commit; it does not wait for the stop**
- [x] `WallClock_T3`, `OutsideFigureLeft_T3`, `OutsideFigureRight_T3`: `tier` 3 → 2. Keys unchanged; `max_tier` unchanged (MEDIUM 2, HIGH 3).
- [x] MEDIUM: clock always + 3 × T1 + 0–2 of the other four T2 (4–6 props); movers = one curtain (side from `selection:MEDIUM`) + the silhouette of the **opposite** window, one draw.
- [x] HIGH: clock always, then the rest of T2 and T3 in today's order (7–10 props); movers = both curtains + MEDIUM's silhouette (derived from the MEDIUM draw, so S7 going MEDIUM → HIGH never switches sides).
- [x] LOW, FOCUS, MINIMAL, BASELINE and the peripheral draw unchanged.
- [x] Silhouette in MEDIUM and HIGH: 8 s walk, 5 s hidden, for as long as the level lasts.
- [x] Harness: **E3** reads 11 props · T1×3, T2×5, T3×3 and 4 movers · T2×4; **new case** over 200 seeds: MEDIUM = clock + exactly one curtain + one silhouette on opposite sides, HIGH ⊇ MEDIUM with 3 movers, same seed → same side, both sides ≈ half each. E7, E8b, E11 stay green.
→ 27 Oct: done. Tiers set in the scene; the clock has `EnvironmentProp.alwaysOn`; movers follow a fixed order (`MoverOrder`) from one seeded draw per session (`EnvironmentSeed` "movers"), profiles MEDIUM 2 / HIGH 3. E3 pins the tiers; E14: 200 seeds, curtain left 98 / right 102. Harness 96/96. X17 at HIGH moves because HIGH's actives changed: window bird left 2.38 → 2.35 (still ≥ sky), butterfly left 1.56 → 1.14 (listed, not gated, D-F6-98); re-measured in E1c.

**Stop (one, before 16:45 or after 18:00):** in the headset, Sebas picks the silhouette distance, the curtain draw and the wind, and watches the continuous silhouette in MEDIUM while looking at the board. If it distracts too much, only its 5 s pause changes (the value goes to the draft for UI/UX's §10.4).

**E1c · After the stop: commit the approved values and re-measure**
- [x] The silhouette starts, pauses and ends **hidden by architecture** (the wall between board and window, or the paper half), never by its curtain (in MEDIUM its curtain is off). If it pops in or out anywhere in the cycle, fix its path, not the draw.
- [x] E13 angles (D-F6-33), `DWELL` boxes (silhouettes now in MEDIUM), `HEAD_AWAY` region with the D7 probe, X9/X13, `LayoutOfRecord`. Note every difference > 1° with its cause.
- [x] **X17** at the new silhouette distance: ≥ 2.7:1; if a silhouette drops, change its colour, not its position (§10.5).
- [x] **D7 probe in MEDIUM (D-F6-102):** the share of clock looks that land on the Fuji picture when the draw includes it (same 2°–6° sweep as row 17).
- [x] Results table in the day draft; UI/UX documents the approved values in §10 (tell Sebas).
→ 27 Oct: **stop passed** (Sebas): silhouettes at 5.5 m on flat ground, curtains 25 %, wind 12 cm, pause 5 s, continuous silhouette in MEDIUM approved. In the scene: silhouette roots (∓1.972, 0, 5.5), walk start behind the wall on the board side; curtain roots |x| 2.9301 (manifest + `CurtainWind.DrawMeters`, also applied by `JapaneseRoomIntegration`); `CurtainWind.Amplitude` 0.12 on `M_Curtain_Wind`. `EnvironmentValuesPreview` deleted. Harness 98/98:
  - **X19 (new):** both silhouettes start, pause and end hidden by architecture (red before: today's path started in view); visible at 31/39 points of the walk; centre mid-walk ±29.1°, outside the HEAD_AWAY yaw limit.
  - **E13:** curtains h [−43.0, −33.0] (was [−40.5, −30.4]), v [−13.7, 4.1]; silhouettes h [−39.0, −17.6] (was [−39.5, −24.7]), v [−15.9, −1.9] (was [−11.1, −1.4]); mirrored on the right. All other rows unchanged. X11 knows the curtain draw.
  - **X17:** measured mid-walk (the start is now hidden). `#34363B` gave 3.46 / 2.67:1 → `#303237` (smallest step that passes) 3.59 / 2.78:1. Animals at HIGH: window birds 2.38 / 1.53, cat 1.67 / 1.29 (was 1.38 / 1.24), shelf 1.19, butterfly 1.56 / 2.03.
  - **X12b (new, D-F6-102):** looks 2–6° short of the clock over 200 seeds. MEDIUM (picture active in 50/200): clock 58 %, picture 17 %, **left curtain 13 %**, floor lamp 12 %. HIGH (picture in 194/200): picture 65 %, clock 34 %, curtain 1 %.
  - X13: wind 0–12 cm, 0 at the bar.

**Verify:** harness green; eye captures at MEDIUM and HIGH.
**Scope:** M (E1b one commit; E1a/E1c one commit of values + harness)

### [ ] S1: Spec v1.4 change rows (`Claude outputs/Cambios_Spec_v1_4.md`, mine)
- [ ] Header "Alineado hasta: D-F6-104"; read the file just before writing and keep the rest.
- [ ] New rows: **D-F6-85** (closer silhouettes, curtains drawn, wind A; values after the E1 stop; **declares MEDIUM motion and peripheral visibility change vs 23 Oct**), **D-F6-86** (static rice field, same in every condition, not part of the ESL), **D-F6-97** (contrast: silhouettes ≥ 2.7:1 with `#34363B`, animals no worse than with the sky, window birds darkened), **D-F6-98** (**the butterfly is seen less against the rice field**: 1.56 / 2.03 vs 5.7:1; sky and field sessions not compared per animal), **D-F6-100 + D-F6-101** (clock and silhouettes to tier 2, §10.4 selection; **MEDIUM changes**, so S6 and S7 change and earlier sessions are not comparable in the ESL; MIRAI asked on Fri 30, A-11), **D-F6-103 + D-F6-104** (C3 crossfade base, SDF morph only if approved by Thu 18:00, `c3_transition`, not a stroke-by-stroke morph).
- [ ] Row 17 corrected by D-F6-102 (grouping in MEDIUM and HIGH; MEDIUM probe result). Row 21 gets the approved wind A. §2 table: rice field final; set B objects final (`ad19b05`); hints/C3 per `asset_source`.
- [ ] Also C3 7.8 s with strip (D-F6-90) and hint telemetry (D-F6-91): the board says they are declared in v1.4 and no row has them yet.
**Stop:** Sebas reads it; PM takes it for the full spec (D-F6-88). **Scope:** XS (doc)

### [x] E2: Rice-field background (D-F6-86): when Sebas sends the image, by Thu 29 afternoon at the latest
- [x] A static unlit panel behind each window. It is sized and placed so that, seen from the eye at 1.60 m, the horizon sits at eye height and the image fills the window frame. Same in every condition and ESL level. The room lighting is unchanged.
- [x] Record whether the image is final or a placeholder (in the integration and the day draft).
- [x] Harness: the panel is present, it has no collider, and it is outside the `DWELL` and `HEAD_AWAY` boxes.
- [x] **Contrast (D-F6-93), ≥ 2.7:1:**
  1. **Baseline, before the image goes in.** From the eye camera at 1.60 m, capture each peripheral at its resting pose against the current sky:
     - silhouette;
     - bird at its 3 positions;
     - cat at both windows;
     - butterfly at both windows.
     Ratio = (L_light + 0.05) / (L_dark + 0.05), with L the mean relative luminance (linear sRGB) of the figure pixels and of a background ring around it. This checks that the method reproduces the 2.7:1 known for the sky.
  2. **With the rice field:** the same captures and the same ratio. Write a table per peripheral and position: sky, rice field, and pass or fail.
  3. **If one fails:** change only its material colour (darker against a light field, lighter against a dark one) until it reaches ≥ 2.7:1. Keep the same colour in every condition and level. Timing, path, shape and alpha stay as they are. Re-measure.
  4. Harness: a case with the approved colours per peripheral, plus the ratio table in the day draft.
→ 26 Oct: image final (Sebas), `arrozal_v1.png` 2172 × 724, panel 20 × 6.667 m at z 10, horizon 1.60 m, UVs turned back 180°, X16. Contrast (`PeripheralContrast`, X17): the method gives 2.80 / 2.62 for the silhouettes against the sky. Against the field: silhouettes 1.23 / 1.04 → `#34363B` (`M_Silueta_Arrozal`) 3.26 / 2.87. The animals were already 1.2–2.7 against the sky; their rule is question 10 for PM in the 26 Oct draft, and nothing is changed for them. Harness 93/93.
- [x] **E2b · Animals, "no worse than with the sky" (D-F6-97):**
  → 26 Oct: measured at HIGH (seed 20260909, level and actives put back), repeatable to two decimals. Sky / field: window birds 1.37 / 1.26 and 1.48 / 1.25 → own materials ×0.38 linear (`*_Arrozal`, window birds only) 2.38 / 1.53; cat 1.20 / 1.38 and 1.18 / 1.24 (passes); shelf bird 1.19 (unchanged). **Butterfly: 5.73 / 5.70 against the sky at HIGH, 1.56 / 2.03 against the field; even black it would reach only ≈ 3.4 / 4.4, so the rule cannot be met (question 12 for PM).** X17 gates silhouettes, window birds and cat; butterfly listed. Harness 93/93.
  1. `PeripheralContrast.Measure()` sets the ESL to **HIGH** first and puts the previous level back afterwards, so the curtains and props behind each animal are the same in every run (question 11). Re-measure the **sky baseline** the same way (sky panel swapped in only while measuring), so both columns use the same scene.
  2. Targets per position: rice-field ratio ≥ sky ratio. Window birds (left, right) and butterflies (left, right) only. The cat already passes (check it still does at HIGH). The shelf bird does not change.
  3. Adjust only as much as needed, in a material of its own like `M_Silueta_Arrozal` (the FBX materials are read-only):
     - **butterfly:** body and wings darker (figure 0.07 against a lighter field);
     - **bird:** one colour for both windows. Left wants a darker bird (field lighter than the bird) and right a lighter one (field darker), so first test a common brightness scale on both plumage materials. **If no single colour passes both windows, stop and tell Sebas:** the options are a colour per window or keeping one side as measured, and that is his call.
     Same colour in every condition and level.
  4. Harness X17: silhouettes ≥ 2.7:1, plus window birds and butterflies ≥ their sky value (stored in the case), measured at HIGH; the cat listed.
- [ ] After approval, UI/UX documents the colours in `Diseno_Sala_ESL.md` §10 (D-F6-93, D-F6-97). Tell Sebas.
**Verify:** harness green; captures from the eye of each peripheral against the field.
**Stop:** Sebas approves the background, the silhouettes and the animals in the headset (D-F6-97). → 26 Oct: **seen and approved** with `PeripheralPreview` (ESL held at HIGH, every animal and both silhouettes in turn). Butterfly left as it is and declared (D-F6-98, closes question 12). Pending only: UI/UX documents §10. **Scope:** S → M (with the contrast step)

# Todo: week of 26 – 30 Oct (VR complete, MIRAI presentation)

Plan: `tasks/plan.md`. Previous list: `tasks/archive/fase6_m3_todo.md`.
**Aligned up to: D-F6-97** · plan approved by Sebas, 26 Oct; B4 and A2 extended with D-F6-89 to D-F6-92 (`Estado_Actual.md`, the board; it wins over this list).
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

### [ ] A3: Set B kanji objects (D-F6-43): when Modelado 3D delivers 山 門 女 手 雨
- [ ] Only with all five FBX in `KanjiLessonAssets/NN_*/export/` (all five or none, as in D-F6-26).
- [ ] Integrate them the way set A was integrated (Task 23 of the archived list): `object_source = BLENDER_FBX`. Use the harness case for poses and S5 approach.
**Verify:** harness green; one capture per object from the eye.
**Stop:** Sebas sees set B in S5 in the headset.
**Deps:** the delivery. Never ahead of B4. **Scope:** S

---

## B · Presentation (D-F6-66, Wed 28)

### [ ] B4: Set A visual hints (D-F6-63) and C3 (D-F6-64)
**Blocked by:** the UI/UX design (how each hint looks per trial type and level, the C3 sequence) and the intermediate shapes and images from Modelado 3D or Contenido, validated by Sebas (D-F6-30). Until they arrive, only the prep steps run. **Cut-off: Wed 28 at 12:00 (D-F6-87).** If they are missing by then, V5 is dropped, V6 uses a hint requested with *Hint*, and B4 continues after the video with a declared placeholder.
Design: `Diseno_UI_Kanji_Studio_v1.md` §9–§11 (delivered 26 Oct). Assets: P, F1, F2 and M per kanji (§11.1), 20 for set A.

**B4a · Hints (D-F6-63, D-F6-89, D-F6-91), one commit**
- [ ] Prep (Tue 27, with placeholders): the per-kanji asset path (`A_月_P.png`, …) and the `BoardCanvas` zones:
  - zone A image (−560, 60), 320 × 320 u;
  - zone B strip (−150, −270): 4 boxes of 150 u with arrows, plus the "?" box;
  - audio indicator (330, −370), 120 × 90 u.
  Box style, ink and colours as §9.2–§9.3.
- [ ] Cells per §9.1:
  - T1 HIGH: partial strip, object → F1 → ? → ?;
  - T2 HIGH: M in zone A;
  - T3 MEDIUM: P in zone A;
  - T3 HIGH: full strip in zone B, zone A empty.
  LOW and OFF are unchanged. A request and the proactive cue (D9) show the same thing.
- [ ] Timing (§9.4): 250 ms fade-in on the request frame or on `TRIAL_STARTED`; still until the answer; gone at `ANSWER_SELECTED` without a fade.
- [ ] Audio indicator (D-F6-89): a speaker icon chip with no text or sound, visible from the audio start until 300 ms after it ends. It replaces the "reading audio" chip in audio-only cells and sits next to the image in HIGH.
- [ ] Text chip (§9.6): hidden only in cells whose image is `AUTHORED`. A cell still on a placeholder keeps its current chip.
- [ ] Telemetry (D-F6-91): `asset_source` (`AUTHORED` / `PLACEHOLDER`) of the visual hint next to `cue_type`, in every trial with a hint. Update `EVENT_CONTRACT.md` and the projection or `verify_*` if they read cue fields.
- [ ] Harness: zones inside the canvas and clear of the Hint button; the chip/indicator rule per cell; `asset_source` per cell; no motion between fade-in and answer.

**B4b · C3 with the summary strip (D-F6-64, D-F6-90, D-F6-91), one commit**
- [ ] §10 timeline, starting when the object is back on the board:
  - 0–0.5 s: the object shrinks while F1 fades in;
  - F1 2.0 s → 0.5 s crossfade → F2 2.0 s → 0.5 s crossfade → kanji;
  - the strip fades in at 5.8 s (300 ms), stays until 7.5 s, fades out (300 ms);
  - S5 continues at 7.8 s.
  The same in every condition and level.
- [ ] Rule 9: no sound; ink of each form ≤ 1.5× the kanji's area; form colour and stroke as the glyph.
- [ ] Telemetry: `asset_source` per stage, plus the strip's start and duration in `KANJI_EXPOSED`. A missing form keeps its placeholder with the same times and records `PLACEHOLDER`.
- [ ] Harness: the stage times add up to 7.8 s; the strip is the same layout as the full shape hint; S5 is ≈ +12 s over the 23 Oct run.
- [ ] If time runs short, the strip is the one part that can be dropped (back to 5.5 s, §10), and Sebas is told.

**Verify:** harness green; captures from the eye of a T3 HIGH strip, a T2 HIGH scene, the audio indicator (V6) and one C3 with the strip (V5).
**Stop:** Sebas sees them in the headset (Wed 28).
**Scope:** M + M (two commits)

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

### [ ] E1: Silhouettes, curtains and wind (Tue 27)
- [ ] Read the current values in Unity: the silhouette path (distance behind the sill), the curtain sheet extents, and `CurtainWind.Amplitude` = 0.06 m.
- [ ] Proposals to try in the headset (two values each, so Sebas can choose):
  - silhouette path moved toward the window until torso and head show above the sill;
  - curtains gathered toward the walls by 25 % and 40 % of the sheet width;
  - wind A = 0.09 m and 0.12 m, with the ripple and gust unchanged. Keep everything else from D-F6-61: alpha 0.90, ≤ 0.5 Hz, no opacity motion.
- [ ] After approval: E13 angles (D-F6-33), the `DWELL` boxes, the D7 probe for `HEAD_AWAY`, X9/X13 and the shader/harness limit (`at most 0.06` → the approved A). Note every difference > 1° with its cause. UI/UX then documents §10.
**Verify:** harness green; captures from the eye.
**Stop:** Sebas approves the values in the headset.
**Scope:** M

### [ ] E2: Rice-field background (D-F6-86): when Sebas sends the image, by Thu 29 afternoon at the latest
- [x] A static unlit panel behind each window. It is sized and placed so that, seen from the eye at 1.60 m, the horizon sits at eye height and the image fills the window frame. Same in every condition and ESL level. The room lighting is unchanged.
- [x] Record whether the image is final or a placeholder (in the integration and the day draft).
- [x] Harness: the panel is present, it has no collider, and it is outside the `DWELL` and `HEAD_AWAY` boxes.
- [ ] **Contrast (D-F6-93), ≥ 2.7:1:**
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
- [~] **E2b · Animals, "no worse than with the sky" (D-F6-97):**
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
**Stop:** Sebas approves the background, the silhouettes and the animals in the headset (D-F6-97). → 26 Oct: **seen and approved** with `PeripheralPreview` (ESL held at HIGH, every animal and both silhouettes in turn). Pending: butterfly (question 12), and UI/UX documents §10. **Scope:** S → M (with the contrast step)

# Todo: week of 26 – 30 Oct (VR complete, MIRAI presentation)

Plan: `tasks/plan.md`. Previous list: `tasks/archive/fase6_m3_todo.md`.
**Aligned up to: D-F6-88** · plan approved by Sebas, 26 Oct (`Estado_Actual.md`, the board; it wins over this list).
Every commit gets a message file in Downloads, is shown to Sebas first, and holds one change.
Every task ends with a **Stop**: Sebas sees the result before the next dependent task starts.

---

## A · Last week's leftovers (first)

### [ ] A1: Phase-test findings §3 and criteria evidence (Mon 26)
- [ ] `Claude outputs/Hallazgos_Prueba_Fase_F5a.md` §3: replace "Pendiente" with MANU's five answers (`Nota_Entrega_M3_MIRAI.md` §3 item 5). Cross each answer with the data:
  - "noticed the props and the bird" → the block changes and the peripherals in §1;
  - "no hints appeared" → 0 `HINT_REQUESTED`, LAL never rose;
  - "confuses look-alike kanji (月/火)" → a new finding for the pilot, linked to D-F6-71.
- [ ] Per-trial notes from the paper sheet (`Prueba_Fase_23oct_Consentimiento_y_Observacion.pdf`, pp. 3–4): read them. If the sheet has none, declare "sin notas por trial".
- [ ] §2: move or add findings if the answers change them, and close the classification.
- [ ] `Evidencia_Criterios_F5a.md` criterion 8 and `Evidencia_Criterios_F6.md` criterion 6: 🟡 → ✅, citing §3.
- [ ] Headers "Alineado hasta: D-F6-86".
**Verify:** the three docs agree with each other and with the M3 note §3. **Scope:** XS (docs only)
**Stop:** Sebas sends the M3 note.

### [ ] A2: rules-v2 live (D-F6-59, D-F6-79 to D-F6-82)
Order matters: (a) → (b) → (c) and (d) → run.
- [ ] (a) Two commits, with the messages already shown on 26 Oct: `feat(db)` migration 0009 with `schema.sql`, then `feat(adaptation)` behavior-v2/rules-v2 with tests and `EVENT_CONTRACT.md`. pytest 227/227 before each.
- [ ] (b) Between runs, headset off: `alembic upgrade head` → check `\d adaptation_decisions` (VARCHAR(16), new CHECKs) and `SELECT count(*) FROM v_adaptations` (180) → **only then** restart the backend.
- [ ] (c) O4 (D-F6-80): in `outcome.classify()`, still `UNDERCHALLENGED` after the change → always `NEUTRAL / PERSISTED` (no trend). `STABLE` → `RESOLVED` and the other states → `SWITCHED` already work. Add 3 tests (one per row). Update the docstring table and `Planteamiento_Tecnico_F5a.md` §5.3.
- [ ] (d) Portal (D-F6-81): `profileText.ts` gets a neutral phrase for `UNDERCHALLENGED`, with a code comment marking it provisional until `Contenido_UI_F-PROFILE.md`. `EstimatedState.tsx` gets a neutral colour from an existing token (no new colour). Vitest gets a case for each.
- [ ] `reason_code` `UNDERCHALLENGED_ENVIRONMENT` with the LAL at LOW (D-F6-82): already in the code. Only check that the test exists.
**Verify:** pytest and Vitest green; `graphify update .`.
**Stop:** a v2 run in the headset (S1 → S9, set A, `BEHAVIOR_ADAPTIVE`). Each decision has `estimator_version = behavior-v2`, `verify_adaptation` and `verify_projection` show 0 discrepancies, and the session looks right in the portal. Any `UNDERCHALLENGED` change shows the provisional phrase and colour.
**Scope:** M (backend 2 files + tests, dashboard 2 files + tests)

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
- [ ] Prep (Tue 27, with placeholders): read the current hint slot and the C3 crossfade (`KanjiLearningItem`, `StudioTrialPresenter`). Prepare a per-kanji path for real assets, with `asset_source` real or placeholder in the telemetry. Add a switch that hides the "Hint · …" chip only in cells with a real visual hint; the telemetry still logs which hint was given.
- [ ] Hints: picture, meaning link and shape for 月 車 火 竹 石. **None may reveal the answer** (§9.1).
- [ ] C3: object → two intermediate shapes → kanji. Same duration in every condition, no flashes (rule 9).
- [ ] Harness: a case for hint assets present, chip hidden only where real, `asset_source` per kanji, and the C3 duration.
**Verify:** harness green; captures of one hint (V6) and one C3 (V5) from the eye.
**Stop:** Sebas sees them in the headset (Wed 28).
**Scope:** M (if it grows past 5 files, split hints and C3 into two commits)

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
- [ ] A static unlit panel behind each window. It is sized and placed so that, seen from the eye at 1.60 m, the horizon sits at eye height and the image fills the window frame. Same in every condition and ESL level. The room lighting is unchanged.
- [ ] Record whether the image is final or a placeholder (in the integration and the day draft).
- [ ] Harness: the panel is present, it has no collider, and it is outside the `DWELL` and `HEAD_AWAY` boxes.
**Stop:** Sebas sees it in the headset. **Scope:** S

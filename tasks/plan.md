# Implementation Plan: week of 16 – 20 Nov 2026 (dry run → unfreeze → pilot ready)

Written Mon 16 Nov 2026; **updated Wed 25 Nov 12:30, aligned up to D-F6-286 (T05 at 15:30; no code 15:15–17:30; `config.py` commit after 17:30; export ready ≈ 16:50). Before: 11:35, aligned up to D-F6-283 (kit approved; only (c) failing → find the cause, (3) if removed; every `.env` change with `docker compose up -d backend`; `config.py` comment after 15:30). Before: 11:20, aligned up to D-F6-282 (Tue 24 not worked; T05 today 13:30–14:45 with (3) live, processing and go/no-go 14:45–15:30; V1 of ≈ 4 candidates Thu 26 / Fri 27; ethics v1.5 and consent v1.4 approved). Before: Fri 20 Nov night, aligned up to D-F6-281 (G approved with T03's finding declared; S next; then V, RT if time, MI):** before: aligned up to D-F6-280 (I1 approved; the threshold epoch counted in G, `new_epochs()` untouched; MI after S):** before: aligned up to D-F6-279: the section "Fri 20 night · ICA live behind `EEG_LIVE_RULE=ica`" approved (D-F6-276) with the channel out and the LSL simulation; I1 → I2 → G → S, one commit and a Stop each**. Before: aligned up to D-F6-275. Before: Fri 20 15:20, aligned up to D-F6-272. Before: Thu 19 Nov 12:40, aligned up to D-F6-255 (13:10: `ocul.py` v2, OV tolerances, component selection; 12:41 OK with D-F6-251 to D-F6-254): today's plan is the section "Thu 19 · day plan (D-F6-246 to D-F6-255)"; waits for Sebas's OK before `/build`**. Before: Tue 17 Nov 17:05, aligned up to D-F6-233: the T01 test moves to Wed 18 11:00–12:00, BR3 (and BR4 if time) this afternoon, AU1 on Wed, AU4/AU0/M0/M1 plan on Fri (D-F6-232; monitor D-F6-231/233)**. Before: Tue 17 14:55: test with the cap at 17:00, participant T01 (D-F6-228); S2 only on visit 1 (D-F6-229); two portal writes, T01's data kept as a test (D-F6-230) · **Sebas's OK for `/build`**. Before: Tue 17, aligned up to D-F6-227 (X8 with the five kanji and the BR2 Editor Stop today; BR3 with V1.12: D-F6-226; CH1 with D-F6-224; no presentation on Fri 20: D-F6-227). Before: 16 Nov night, aligned up to D-F6-221 · approved (D-F6-221); Tue 17 09:00: D-F6-222 (automation in two parts, manual recording for the pilot start: D-F6-221; one S6 threshold: D-F6-220; bad channel: D-F6-216; sync: D-F6-217; S6 and reference: D-F6-218; session automation: D-F6-219, **proposal waiting for Sebas's OK**; two `AURA`: D-F6-206; two-visit test: D-F6-207; block R inputs: D-F6-208; end of the free recall: D-F6-212; one bad channel: D-F6-213; sync spread: D-F6-214). **Approved by Sebas (16 Nov). No code today; `/build` starts Tue 17 after V4 and U0.**
Last week's plan is archived in `tasks/archive/semana_9nov_{plan,todo}.md`; its open items are carried over in the last section.

## Sources of truth
- **`Claude outputs/docs_proyecto/Estado_Actual.md` first:** §1 rows "Semana 16–20 nov" and "Lun 16 (agenda)"; §4 D-F6-198 (freeze), D-F6-200 (grid phase), D-F6-204 (week), D-F6-206 (two `AURA`), D-F6-125, D-F6-190, D-F6-207 and D-F6-208 (block R), D-F6-202 and D-F6-222 (X8); §1 rows "Mar 17 (agenda)" and "Estado mar 17, 16:00"; D-F6-223 to D-F6-227.
- Today's operator kit: `Claude outputs/Borrador_Plan_Fase6_9_13nov.md` (today's times, docs only).
- `Checklist_Congelamiento_Reglas_12nov.md` (frozen values), `Consentimiento_Protocolo_Sesion_v1.md` Parts B and C (session steps, block R in the visits).

## Week rules
- **Rules stay frozen until V4 on Tue 17** (D-F6-198, D-F6-204). Until then: no code; findings recorded, not fixed.
- After the unfreeze, still **no rule value changes** (D-F6-200 (1) says so explicitly); a rule change needs its own number.
- One change per commit, message shown first; nothing on main. `graphify update .` after code. Backend changes go live with `docker compose restart backend`, between sessions; **a `backend/.env` change needs `docker compose up -d backend`** (D-F6-283 (2)).
- Each task ends with a **Stop** (Sebas's OK). Every day closes with `tasks/` up to date and the draft with "Dudas para PM" or "Sin dudas · <date>".
- Participants appear **only by code** (D-F6-205), in the draft, the database and commits. **The dry-run participant's data is kept:** the dry run is visit 1 of the block R test (D-F6-207).
- **Block R inputs (D-F6-208, D-F6-223, D-F6-226):** all three real since Tue 17: UI/UX's texts (`Contenido_UI_Bloque_R.md`) and Content's 5 new kanji per set (`Metricas_…` §16.7) in `kanji_content.json`; web design's V1.12 recall form, validated, built in BR3. No placeholders left.
- **Free recall (D-F6-212):** the researcher ends part 1 when the participant says they are done; **≈ 2 min is only a guide, no clock** in the VR or the portal. The researcher says *"Anything else you remember?"* once, when the participant goes quiet; never repeats, corrects or hints.
- **EEG quality:** a bad channel is handled by protocol (D-F6-213) until CH1 (D-F6-216, D-F6-224) enters on Thu 19.

## Dependency graph

```
Mon 16  V2 dry run = visit 1 (kit) ──► V3 analysis ──► XDF to EEG chat
                                            │
Tue 17                                      ▼
        V4 close ──► U0 unfreeze ──► G1 grid origin (D-F6-200 (1)) ──► G2 two AURA (D-F6-206)
                                                                          │
                                                                          ▼
                     ──► S1 sync: S3 taps only, robust spread (D-F6-217) ──► S6 15 trials + reference min 15 (D-F6-218)
                     ──► BR0 design ──► BR1 data ──► BR2 block R in VR (Editor Stop)
        15:15 BR2 Editor Stop ✔ ──► 15:30 X8 ✔ ──► C0 ✔ ──► (17:00 test cancelled, D-F6-232) ──► BR3 portal recall, V1.12 ──► BR4 if time
Wed 18  until 10:15 what is left ──► 10:15 code closed ──► 10:30 R3 ──► 10:50 network off ──► 11:00–12:00 T1 test with the cap, T01
                     ──► afternoon: T2 analysis (G1, S1, S6 first real check, export) ──► BR4 if missing ──► AU1
Thu 19               BR6 last check of the inputs ──► 12:00 BR7 visit 2 test, dry-run participant (D-F6-207)
                     ──► CH1 bad-channel rule (D-F6-216, D-F6-224), proved on the dry-run XDF on this PC
Fri 20               AU4 end-of-session, tested on the dry run and on T01 ──► AU0 ──► afternoon M0 (portal served by nginx) ──► /plan of M1, no code
                     go/no-go (PM / Sebas) ◄── everything above · no presentation, no video (D-F6-227)
Sat 21 – Mon 23      Sebas away: no rehearsal, no buffer
Tue 24 morning       what did not finish on Fri 20 ──► afternoon: first participant, **manual recording** (today's kit) + AU1 and AU4
later in the pilot   AU2 + AU3 + AU6 rehearsal with Sebas on a day without a participant; pass → automated recording from then on (sessions labelled by recording path)
```

G1 and G2 go first on Tue: both touch `fill_from_xdf` and are small. S1 and S6 are small and touch the same EEG files, so they follow G2 while that code is fresh; their Unity part shares BR2's Editor Stop. Block R has a hard date (visit 2 on Thu 19). CH1 goes after BR7 (D-F6-216) and before the automation, which reuses its measure in the S3 warning. X8 is content only and closes Tue with all five kanji (Sebas approved the 20 hints at 14:40). BR2's Editor Stop goes after X8, so Sebas sees block R and the new objects in one sitting. The automation (D-F6-219, D-F6-221) is split: AU1 and AU4 do not change how a session is recorded, so they enter from Tue 24; AU2/AU3 change the recording and wait for a full rehearsal with Sebas on a pilot day without a participant.

## Tasks

### Mon 16 · dry run = visit 1 (D-F6-204, D-F6-207) · no code

| When | Task | Stop | Network |
| --- | --- | --- | --- |
| 14:30 → 14:50 | **R3** PC ready (kit list); Blender closed 14:45 | Sebas sees it ticked | on |
| 14:50 | Network off (kit step 1) | — | **off** |
| 15:00 → ≈ 16:45 | **V2** dry run: same external participant, code only, set A, `MULTIMODAL_ADAPTIVE`, T1–T3 lures, consent v1.1. At the end Sebas asks them back for **Thu 19**, without mentioning memory questions (D-F6-207) | written offline (Notas sin red) | off until *both streams recorded* |
| when `autorun` ends | **V3** analysis; XDF to the EEG chat | Sebas | on |

**V3** (read-only on the database):
- Read «Notas sin red», step 12 answers, `autorun` log, Unity console.
- The four SQL of kit §8. `verify_eeg.sql` complete; **A-7 from the live engine** with the XDF figure beside it and the grid-phase cause declared (D-F6-200 (2)); `replay --xdf` matches the stored decisions; **3rd sync measurement for A-23** (one-frame `SYNC_TAP` delay declared); every `EEG_LED` one by one.
- **Data for A-24, not a decision:** S6 length, number of reference epochs, reference source.
- Note the dry-run **session id and participant code** for BR7 (it is the session visit 2 evaluates).
- XDF and the `eeg_export` (as E1) handed to the EEG chat.
- **Done when:** every check has a line in the draft's Registro; findings say "blocks the pilot yes/no". Nothing fixed.

### Tue 17 · close, unfreeze, EEG fixes, block R

**V4 · close of the dry run (first thing).** F4 S3 criterion met or not, with evidence; findings listed with owner; draft with Dudas or "Sin dudas". **Stop:** Sebas's OK = the condition for U0.

**U0 · lift the freeze (D-F6-204).** Docs only. `git diff eeg-rules-freeze-2026-11-12 -- backend unity-client` shows no code change; note "freeze lifted at <time>, after V4". The tag stays as the reference for "rules as frozen". **Stop.**

**G1 · one epoch grid for live and offline (D-F6-200 (1)).** No rule value changes.
- What exists: `live.Buffer` sets `t0` at the first corrected stamp it sees; `make_epochs(..., t0=)` already takes an origin; `fill_from_xdf` (`epochs.py:175`) and `replay.xdf_source` start from the XDF's first stamp; `verify_eeg.sql` only reads `eeg_epochs`, so it follows `fill_from_xdf`.
- Change: migration **0018** adds `eeg_sessions.grid_origin_lsl` (double, null); `live.py` writes `t0` once, when set; `fill_from_xdf` and `xdf_source` pass it as `t0` when not null, otherwise today's behaviour (old sessions unchanged, declared).
- Tests: an XDF whose first sample is earlier than `t0` gives the **same `epoch_index` and `lsl_start`** offline as live; null origin = today's output; `rules-v2` replay byte-identical (C5), `decide()` untouched.
- Limit: no past session stored an origin, and visit 2 has no cap, so the first real check is the first pilot session (declared).
- **Done when:** tests green, migration up/down, restart, `/health`; `fill_from_xdf` on the dry-run session gives the same rows as before (null origin). **Stop.**

**G2 · two `AURA` streams in the XDF (D-F6-206).**
- Rule: keep the `AURA` whose hostname is **this PC** (same rule as `open_local_inlet`). Two `AURA` from this PC → **do not fill**: the session keeps its live epochs (as `a8e825e0`) and the log says so. Never choose by sample count.
- Where: only `lsl_reader.load_xdf` (today it raises `ValueError` on any repeated name). It keeps the stream whose `info.hostname` is this PC when a name repeats; two from this PC still raise, with their own message. Its four callers (`lsl_reader.fill_from_xdf`, `epochs.fill_from_xdf`, `sync.fill_from_xdf`, `replay.xdf_source`) need no change beyond logging that raise as "not filled, live epochs kept". The PC hostname is passed in, as `open_local_inlet` does, so the container can be tested.
- Tests: one local + one foreign `AURA` → the local one; two local → no fill, live epochs untouched, log line; one `AURA` → today's behaviour.
- Check: `a8e825e0` (two `AURA` on 12 Nov) run through the new pick; result noted (fill or not, and why). **Stop.**

**S1 · sync for the pilot (D-F6-217).**
- `sync.py`: spread = **MAD × 1.4826 of the clear S3 lags** (today `np.std` of S3 + S9 lags, `sync.py:82`); `verify_eeg.sql` block 2 reads the same field, labelled "robust spread". S9 is no longer expected: no S9 taps → drift empty with reason "no S9 taps (D-F6-217)", not an error (D-F6-176 already allows a session without drift).
- Unity: `SessionFlowRunner` stops running the S9 sync test (`if (eegStep) yield return RunSyncTest("S9")`, line 910); the T key in S9 is then logged and ignored, like other keys out of state. Kit and Part B: no taps in S9.
- Tests: robust spread on fixed lags (one outlier does not move it as `std` does); no S9 → drift empty with the reason. Check: `65af2fe4` recomputed gives **≈ 17.8 ms** (the EEG chat's figure); old sessions recomputed only for the report, beside the old values.
- **Stop** (the Unity part is seen at BR2's Editor Stop).

**S6 · longer S6 and one S6 threshold (D-F6-218, D-F6-220). Lengthening S6 is configuration only, no Unity code (confirmed in D-F6-220).**
- The number of S6 trials is the serialized field `s6Trials` of `SessionFlowRunner` (default 9, `SessionFlowRunner.cs:91`; value 9 in `JapaneseLearningStudio.unity:5275`). `TrialSequenceGenerator.Build` takes any count: with **15 it builds the full cross, 5 kanji × 3 types, one each**, lures in half the trials by the seed (D-F6-131). Nothing else assumes 9 (`profile.py` uses S6-002 onward).
- Measured: `65af2fe4` had 9 S6 trials in 48 s (≈ 5.3 s each, a fast participant). **15 trials ≈ 80 s or more**: meets ≥ 75 s. 12 would give ≈ 64 s, short.
- Changes: `s6Trials: 15` in the scene (one serialized value; scene commit, no C#) and the reference minimum **15 non-POOR epochs** in `reference.py` (`MIN_EPOCHS = 6` → 15); below that, S4 eyes open, marked (D-F6-73). The session gets ≈ 30–40 s longer.
- Tests: `reference.compute` with 14 and 15 non-POOR epochs; harness: an S6 plan of 15 with the full cross; `verify_eeg.sql` run on the three sessions above. Unity part seen at BR2's Editor Stop.
- **One threshold for the reference and A-7 (D-F6-220):** S6 with ≥ 15 non-POOR epochs → reference S6; fewer → reference S4 eyes open, marked. That part **chooses the reference, it never fails the session**: a multimodal session is valid when S4's eyes-closed test passes and the EEG counts in ≥ 60 % of the S7 windows.
- `verify_eeg.sql`:
  - **block 4** "S6 → reference": S6 non-POOR / epochs, threshold **15**, and the reference actually used (`eeg_sessions.reference ->> 'source'`, S6 or S4 eyes open with its fallback mark, and `n_epochs`). Its check column says `S6` or `S4 (fallback)`, never `SHORT`.
  - **block 7** A-7: `VALID` = S4 alpha passes AND P7 ≥ 60 %; the `s6.n >= 6` condition is removed; the row shows `s6_non_poor` and the **reference used** beside it, as information. Heading text updated to D-F6-220.
  - Check: on `65af2fe4` block 4 says `S4 (fallback)` with 22 epochs and block 7 stays NOT VALID for P7 0/18 (not for S6); on `742ec49a` and `07343b5d` A-7 is recomputed and any change from the old rule is noted.
- `reference.py` and `verify_eeg.sql` use the same 15; one constant in Python, the SQL says "15 (reference.MIN_EPOCHS)" beside it.
- **Stop.**

**BR0 · block R design, read-only (≈ 45 min).** Read D-F6-125, D-F6-131/181 (lure rules apply to block R), D-F6-187/190, D-F6-207/208/212, consent Part B step 8 and Part C, `Contenido_UI_Bloque_R.md`, `Metricas_…` §16 (5 new kanji per set), `design-system.md` V1.12, spec v1.4 if it covers R. Output: one page in the draft: states, events, tables, which inputs are real and which are placeholders.
- **End of the free recall (D-F6-212), mechanism chosen here: a researcher key in Unity, `R`**, added to the five letter keys of D-F6-158 (`ResearcherKeys` and `ResearcherKeyActs` in `SessionFlowRunner`). It acts only during block R part 1, logs `BLOCK_R_RECALL_ENDED` with the elapsed time, and starts part 2; outside part 1 it is logged and ignored, like the others. **Why a key and not the portal:** it reuses the existing pattern (no new endpoint, no backend → Unity push), works offline like every other operator action, and the recall form stays independent (it can be saved during or after the visit). Before S4 the researcher may touch the PC, so moving from Edge to the Game view is allowed. **G** still force-advances any wait, as today.
- No timer of any kind for part 1: no countdown in the VR, no clock in the portal.
- **Stop:** Sebas approves the mechanism before BR1.

**BR1 · data path.** Migration **0019**: the session row keeps **which session it evaluates** (D-F6-190 (2)); visit 4 gets visit 3's set (D-F6-190 (1)); block R answers stored as events with their trial kind (and `BLOCK_R_RECALL_ENDED`, D-F6-212, accepted by the event schema), never read by `decide()` or the window code. Validation: the evaluated session belongs to the same participant and is earlier. Tests. **Stop.**

**BR2 · block R in VR, between S2 and S3.** Part 1 free recall: instruction screen (UI/UX text) and a waiting screen with **no timer**, ended by the researcher's `R` (D-F6-212). Part 2 yes/no recognition with 10 kanji (5 seen, 5 new from §16, placeholder only if missing). Part 3: 15 multiple-choice trials T1–T3 with lures, no feedback, no hints, from the evaluated session's set. Texts from `Contenido_UI_Bloque_R.md` (placeholder only if missing). EditMode test for `ResearcherKeyActs(R)`. Harness test like X7; seen in the Editor with Sebas. Unity commit says "block R, exception D-F6-125". **Stop in the Editor** (Tue evening, or Wed around the workshop).

**Done by 16:00 (board, "Estado mar 17, 16:00"):** V4 (OK), U0 (12:32), G1 `676e3d9`, G2 `c34f596`, S1 `f7fe91c`/`1639b3a`, S6 `0196bbf`/`6932465`, BR0 (D-F6-223), BR1 `68adc7f`, BR2 `9adf8a0`/`3fd8870`, harness poses `2aaa81f`; 439 backend tests, harness 117/117.

**Tue 17 from 14:55 · test with the cap at 17:00 (D-F6-228).** External participant **T01**, not in the study: `MULTIMODAL_ADAPTIVE`, set A, visit 1 (no block R). Times:

| When | What | Stop / condition |
| --- | --- | --- |
| until 15:15 | This plan | Sebas's OK |
| 15:15 | **BR2 Editor Stop** with Sebas (below) | Sebas's OK |
| 15:30 → 16:15 | **X8**, the five kanji (below) | **Cut-off 16:15:** if X8 is not committed with the harness all PASS, it is set aside without a commit (`git stash -u -m "X8 wip"`) and resumes after the test |
| 16:15 | **C0 · code closed** | `git status` clean; `docker compose restart backend` and `/health`; Unity closed and opened again; nothing changes until T2 ends |
| 16:30 | **R3** of the kit (as on 16 Nov) | Sebas sees it ticked |
| 16:50 | Network off | — |
| 17:00 | ~~T1 · the test session~~ **cancelled at 16:54; moves to Wed 18, 11:00–12:00 (D-F6-232)** | — |
| after | **BR3**, and **BR4** if time (D-F6-232 (1)); the backend may be restarted again today | each with its Stop |

**X8 · content 31–35, the five kanji (D-F6-222, D-F6-202), 15:30 → 16:15.** Content, exception to the VR freeze (D-F6-62, D-F6-122); no rule touched. Same path as X7 (`e8d784a`, `cb64881`). ≈ 1 h.
- **Sebas's OK, recorded:** the 20 hints of 31 金, 32 茶, 33 馬, 34 魚 and 35 鳥 approved by Sebas, Registro of `Tabla_Autoria_Kanji_Fase2.md`, 17 Nov 14:40 (`docs_proyecto/`). The five FBX are in `KanjiLessonAssets/NN_*/export/`, approved (D-F6-222).
- **What counts as a hint:** only `NN_*/pistas/R_NN_CODE_{P,F1,F2,M}.png` (the menu copies those exact names). The PNGs named by ChatGPT that are still in `pistas/` (today: `32_CHA/pistas/Taburete de madera con cojín azul grisáceo.png`) and `_originales/` are not copied.
- **What changes:** `SetAObjectsIntegration.cs` gets `Reserve4` = (`KANJI_KIN`, `31_KANE`), (`KANJI_CHA`, `32_CHA`), (`KANJI_UMA`, `33_UMA`), (`KANJI_SAKANA`, `34_SAKANA`), (`KANJI_TORI`, `35_TORI`) and the menu "Integrar objetos y pistas de la reserva 31-35" (priority 309): `Integrate("R", Reserve4)` + `IntegrateHints("R", Reserve4)`, all or none like a set (D-F6-26). **Orientation:** 31 and 32 face the player; 33, 34 and 35 are side-on, already oriented in their FBX; **none gets the root turn** (the −90° X of 02, 14, 18 and 19 stays only for those). FBX, `.meta`, prefabs, hints and the `KANJI_*.asset` links come from the menu, never by hand.
- **Harness:** `X18r4` checks the five against their FICHA envelopes in Unity axes, within 1 cm, centred pivot, no collider, no animation, `BLENDER_FBX`: 31 (0.24, 0.22, 0.14) · 32 (0.24, 0.20, 0.18) · 33 (0.279, 0.254, 0.090) · 34 (0.28, 0.14, 0.08) · 35 (0.24, 0.18, 0.08). X20 counts **35/35** AUTHORED. X18b and X20 lose their PLACEHOLDER example (`KANJI_KIN`): no content kanji is left without object and images, so both use an in-memory `KanjiLearningItem` without them, which tests the same code path.
- **32 茶 fps (6 706 tris, 3–5× the reserve), after T2 (Play only, no code):** with the headset over Link, in Play (nothing saved), 32's prefab where S5 shows the object, 60 s, then 31's (278 tris) in the same place; `FrameRateLog` gives mean fps and frames > 20 ms for each. Result in the draft. If 32 drops frames that 31 does not, Sebas decides (decimate in Modelado, or keep it: 32 is reserve and only shows through a pre-test substitution).
- **How it is tested:** harness **all PASS, count before → after (117/117 → 118/118)**; the five seen on the board in the Editor with the fps check, after T2.
- **Commit:** `content(unity): reserve 31-35 objects and hints (X8, D-F6-222)`, with the count and the five; then `tasks/` and the draft. **Stop:** the 16:15 cut-off; Sebas sees the five after T2.
- **Done, Tue 17 15:30 · `f4ca615`:** the five entered (31 金, 32 茶, 33 馬, 34 魚, 35 鳥): 5 FBX, 5 prefabs, 20 `R_` hints, the 5 `KANJI_*.asset` links; no ChatGPT-named PNG, no scene change. Harness **117/117 → 118/118** (RED first: X18r4 and X20 failed before the menu ran). The PLACEHOLDER example of X18b and X20 is the tutorial's `KANJI_ICHI` (simpler than an in-memory item; same code path). Left for after T2: 32 茶's fps and the five in the headset.

**BR2 Editor Stop, with Sebas, 15:15 (before X8) · done:** both passes OK in the headset and in the data (`7a74e704` visit 2, `42c7f2ff` short visit `COMPLETED`); `SIM_BR2` deleted with Sebas's OK.

**BR2 Editor Stop, as planned.** In Play, Editor with the headset over Link, network off, a test participant (deleted after with Sebas's OK, as `SIM_1311`):
- **Visit 2:** a visit 2 session for that participant, evaluated session deduced from its completed visit 1 (or given by hand, D-F6-223). Unity runs S1 → SR → S3: R0 → R1 free recall with no cards and no clock → **`R`** ends it (and `R` pressed before R1 or in R2 is logged and ignored) → yes/no 10 → 15 trials `SR-*` without feedback or hints → R9 → S3.
- **Short visit:** `shortVisit` ticked (the Thu 19 path): S1 → SR → S9 with the closing text R9'; the session ends `COMPLETED`.
- **Checked after, read-only:** `BLOCK_R_RECALL_ENDED` once with its `elapsed_ms`, 10 `BLOCK_R_RECOGNITION_ANSWERED`, 15 `trials` rows `SR-001`…`SR-015`, nothing in `adaptation_decisions`.
- The Unity parts of S1 (no S9 taps) and S6 (15 trials) are seen in the same sitting.
- **Stop:** Sebas's OK. Anything to change is written down and fixed in BR4, not before the test (code closes at 16:15).

**C0 · code closed, 16:15 (done 16:33; again on Wed 18 at 10:15, as C0b below).** `git status` clean (X8 committed or stashed); `docker compose restart backend`, `/health`; `alembic current` = 0019; Unity closed and opened again (scene from disk, nothing dirty). From here nothing is changed or restarted until T2 has finished (D-F6-153).

**T1 · test session with the cap, Wed 18 11:00–12:00 (D-F6-228, D-F6-232).** T01: consent v1.3 on its own sheet (not the group sheet), pre-test in the portal (a session needs it); before S3 move the head and cough (D-F6-216), a red channel before S4 is fixed (D-F6-213); R3 with Blender, ChatGPT, Firefox and VS Code closed (D-F6-153); set A, `MULTIMODAL_ADAPTIVE`, visit 1, kit of 16 Nov line by line (R3 at 16:30, network off at 16:50, `autorun` before S3, 5 taps in S3 and **none in S9**, D-F6-217). **At S9, before LabRecorder's Stop:** the live epochs are copied, read-only, to `Claude outputs/eeg_export_17nov/live_epochs.csv` (`\copy (SELECT * FROM eeg_epochs WHERE session_id = …) TO …`), because `autorun`'s `fill_from_xdf` replaces them with the recording's (D-F6-156). **Done when:** S1 → S9, `autorun` exit 0, *both streams recorded*. **Stop:** Sebas writes it offline.

**T2 · after the test, the first real check of G1, S1 and S6.** Read-only on the database; the recording never leaves this PC.
- `autorun` log, the **four SQL** of the kit; `replay --xdf` matches the stored decisions (run on this PC: the container does not see the PC's hostname, G2).
- **G1:** `eeg_sessions.grid_origin_lsl` is not null; for every epoch in both, the live CSV and the rows `fill_from_xdf` wrote have the **same `epoch_index` and `lsl_start`** (and the same `chunk_clean`). The count of epochs only in one of the two is noted.
- **S1:** `sync_detail.spread_rule` = "MAD x 1.4826, every clear tap", robust spread ≤ 50 ms, 0 S9 taps, drift empty with the reason "no S9 taps (D-F6-217)"; `verify_eeg.sql` block 2 says "corrected, no drift measured".
- **S6:** 15 S6 trials in `trials` (full cross 5 × 3); `verify_eeg.sql` block 4 says which reference was chosen (S6 with ≥ 15 non-POOR, or S4 fallback, marked) and block 7 gives A-7 (S4 alpha and P7 ≥ 60 %).
- **Export for the EEG chat**, as on 16 Nov: `Claude outputs/eeg_export_17nov/` with `eeg_sessions`, `eeg_epochs`, `adaptation_decisions`, `eeg_status`, `channels_30s.csv`, `live_epochs.csv` and a README; **the XDF is not copied** (it stays in `Pruebas_EEG\sub-T01\`).
- Then the 32 茶 fps check of X8 (and X8 itself if it was stashed).
- **T01's data (D-F6-230 (2)):** kept in the database like the dry run, marked as a test by its code (`T##`, never `P##`, D-F6-228) and out of the pilot analysis; deleted only if T01 asks (consent v1.3).
- **Done when:** each check has a line in the draft with its figure; findings say "blocks the pilot yes/no". **Stop:** Sebas.


### Tue 17 afternoon · BR3, then BR4 if time (D-F6-232 (1)); BR5 drafted

**BR3 · free recall in the portal, V1.12 (D-F6-226).** Before building: the `research-dashboard-conventions` skill and V1.12 in `Claude outputs/design-handoff/design-system.md` (validated 17 Nov 14:37), with its artboards in `design-handoff/block-r/`.
- **What changes:** backend `POST /sessions/{id}/block-r/recall` (per kanji of the evaluated session: meaning yes/no, reading yes/no, order of first mark, "What they said"; the "Anything else" text; saved time) stored as a `BLOCK_R_FREE_RECALL` event, a new save replacing the old for reading; `GET` of the same path returns the last save or `null` (never saved = not recorded; saved with no marks = nothing recalled, D9). Writes go in `sessions`, not in `/research`, which stays read-only: the portal's second and last write (D-F6-230 (1), rule 1 of the skill). Frontend: the V1.12 screen (focus mode, opened from a session with block R), states `marking`, `saved`, `nothingRecalled`, `saveError`; the five kanji of the **evaluated** session with *Taught as*; Meaning and Reading toggles with `aria-pressed`; *Order* set on the first mark.
- **What counts (D-F6-225), V1.12's text word for word:** *"Meaning: the meaning or a clear synonym, in any language. Reading: the Japanese reading, said close enough to recognise. Anything you're unsure about goes in "What they said", without a mark. There is no mark for a partial answer."*
- **No clock and nothing that paces the 2 minutes** (D-F6-212). The form never moves the VR: that is the `R` key (D-F6-223).
- **How it is tested:** backend tests (save, save again replaces, nothing recalled ≠ never saved, only the evaluated session's kanji, a session without block R → 409); Vitest for the toggles, the order and the four states; Playwright smoke: open, mark two, save, reload, the marks and the time are there; save failure keeps the marks. The 5-tell audit of the skill.
- **Stop:** Sebas sees it against the artboard.

**BR4 · short visit end to end (≈ 1 h; the path was built in BR2).** The flow D-F6-207 asks for on Thu, and the one visit 4 uses (D-F6-125): **S1 → SR → S9, no S2 (D-F6-229)**, no cap.
- **What changes:** only what the BR2 Stop found; and that the short session closes `COMPLETED` and `learner_profile` ignores `SR-*` trials (test).
- **How it is tested:** in the Editor with a test participant (deleted after with Sebas's OK): portal → create visit 2 with the evaluated session → Play → block R with the recall marked in the BR3 form while it runs → S9; then the SQL of BR7 on that session.
- **Stop.**

**BR5 · Thu kit (docs) · drafted Tue 17 15:35 in the 17 Nov draft; Sebas reads it.** In the draft: PC list, network off (D-F6-193), **S1 → block R → close, no S2 (D-F6-229)**; how to create visit 2 (participant code from V3; evaluated session = the dry run `65af2fe4`, deduced or given by hand, D-F6-223; `shortVisit` ticked), S1 with the D-F6-203 sentence, block R steps for the operator (R1: the participant recalls aloud, the researcher marks in V1.12 with the *What counts* of D-F6-225; when they go quiet, *"Anything else you remember?"* once; when they say they are done, Game view in front and **`R`**; no clock, ≈ 2 min only as a guide; never repeat, correct or hint, D-F6-212), **debriefing at the end** (consent Part B step 3, D-F6-192: no visit 4 for this participant), close, the SQL after. **Stop:** Sebas reads it.

### Wed 18 · T01 at 11:00, then T01's analysis and AU1 (D-F6-232 (2)) · AI workshop: if its time clashes with 11:00–12:00, Sebas says so and the test moves

| When | What | Stop / condition |
| --- | --- | --- |
| until 10:15 | What is left of Tue (BR3 or BR4) | each with its Stop |
| 10:15 | **C0b · code closed:** commits done, `git status` clean, `docker compose restart backend` and `/health`, `alembic current` at head, Unity closed and opened again | nothing changes until T2 ends |
| 10:30 | **R3** of the kit | Sebas sees it ticked |
| 10:50 | Network off (D-F6-193) | — |
| 11:00–12:00 | **T1** with T01 (above, D-F6-228 otherwise unchanged) | Sebas writes it offline |
| afternoon | **T2** (above) → **BR4** if it did not finish on Tue → **AU1** | each with its Stop |

**AU1 · pre-session check, Wed 18 afternoon (moved from Fri 20, D-F6-232 (2)).** As in the automation section below; tested on this PC as it is after T2.

### Repo documentation for whoever inherits the project (D-F6-287) · plan, **waits for Sebas's OK before `/build`**

**Audience:** a developer bringing the project up from scratch. English. **Only** `.md`, `mkdocs.yml`, `requirements-docs.txt` and `database/schema.sql`. No code, no restarts, no participant data, no names, no XDF (D-F6-192). **Paused 15:15–17:30 (T05) and during every pilot visit** (D-F6-153); it goes on at night. Not a pilot requirement.

**Found (25 Nov, read-only):** root README 15 Oct, `backend/` 1 Oct, `tools/` 28 Sep, `unity-client/` 7 Sep, none mentioning the EEG; no README in `dashboard/` or `database/`; no `docs/`. `database/schema.sql` is the hand-kept Spanish copy up to migration 0009 (27 Oct); the base is at **0023**. `database/ERD.md` and `EVENT_CONTRACT.md` exist and are reused, not copied. Brand: `design-system.md` §Brand (Lagoon `#0B6A73`, Night `#0F1115`, Light Lagoon `#3FB7C2`, Paper `#F9F8F6`, Saffron `#F2A93B`, Ink `#14171C`); SVGs in `dashboard/public/brand/`.

**Order (dependencies):** B3 schema first (the data-model page and the database README describe it) → B1 site → B2 READMEs (they link to site pages). **One commit per block**, message shown first; `graphify update .` after each.

#### B3 · `database/schema.sql` regenerated from the base (≈ 20 min) · commit 1
- `docker compose exec -T db pg_dump --schema-only --no-owner --no-privileges -U neuroadaptive neuroadaptive_vr` (reads the catalogue only; no rows, so no participant data), with a short English header: source (pg_dump at migration 0023, date), "do not edit by hand, regenerate with this command after each migration".
- **Acceptance:** `alembic_version` = 0023 recorded in the header; every table of 0001–0023 present (`eeg_sessions.ica`, `live_vs_xdf`, `head_away_episodes`, …); `git diff --stat` shows only this file; no `COPY`/`INSERT` in it.
- **Check:** `Select-String "COPY |INSERT INTO"` empty; table count = `\dt` count.

#### B1 · MkDocs Material site in `docs/` (≈ 4–5 h, nights) · commit 2
- `mkdocs.yml` at the root, `requirements-docs.txt` (`mkdocs-material` pinned; nothing in the backend's requirements). Built **offline**: Material's built-in `offline` plugin, `font: false` (system fonts, no Google Fonts), no Mermaid from a CDN (diagrams as text/tables or SVG). `database/ERD.md` and `EVENT_CONTRACT.md` pulled in with `pymdownx.snippets`, a single source.
- Pages (minimum of D-F6-287): `index.md` overview and architecture (Unity ↔ backend ↔ Postgres ↔ portal/monitor, AURA → LSL → `live.py`/LabRecorder); `install.md` from scratch (Docker, Postgres, backend `.venv`, portal, Unity with Quest 2 over Link, AURA over LSL, LabRecorder/`LabRecorderCLI`); `session.md` (preflight, autorun, monitor, kit; pointer to the operator kits, no participant data); `eeg.md` (epochs and chunks, reference S6/S4, ICA at S6, rules (1)–(3), `replay`, `fill_from_xdf`, `verify_eeg.sql`); `adaptation.md` (estimator, rules, EEG block, decisions); `data-model.md` (ERD, event contract, schema, verify scripts); `env.md` (every `backend/.env` variable, defaults from `config.py`, **change → `docker compose up -d backend`, no session running**, D-F6-283 (2)); `testing.md` (pytest, Unity harness, Vitest, Playwright); `troubleshooting.md` (stale `UnityMarkers`, two `AURA`, `restart` not reloading `.env`, preflight FAILs, HEAD_AWAY, FRAME_HITCH…).
- **Acceptance:** `mkdocs build --strict` with no warnings; built HTML has no `https://` asset (fonts, scripts, CSS) outside links in the text; opens from `file://` with the network off; logo and palette as §Brand; every command in `install.md` / `env.md` checked against the repo (compose file, `config.py`, `package.json`), not from memory.
- **Check:** strict build; `Select-String` on `site/` for `fonts.googleapis|unpkg|cdn.jsdelivr`; privacy grep below.

#### B2 · READMEs (≈ 2 h) · commit 3
- Update root, `backend/`, `unity-client/`, `tools/`; new `dashboard/README.md` and `database/README.md`. Each: what lives there, how to run/test it, link to the site page; facts only where the code confirms them (graphify first, then the lines it points to).
- **Acceptance:** each command runs as written in a dry read (paths exist, scripts exist in `package.json`/compose); no stale phase text (F1 "walking skeleton" etc. removed or marked history).

**Privacy check, every block:** no `P0`/`T0` participant code tied to data, no session UUIDs, no person names, no XDF paths with `sub-` folders; grep for `sub-|ses-|[0-9a-f]{8}-[0-9a-f]{4}` and the team's names before each commit.

**Checkpoints:** after B3 (Sebas sees the diff header) · after B1 (Sebas opens the site offline) · after B2 · each a **Stop**.

**Questions (also in the 25 Nov draft, «Dudas para PM»):**
1. **Brand needs two non-`.md` files:** Material only takes custom hex colors through CSS, and the logo must be inside `docs/`. Allow `docs/stylesheets/brand.css` (the six §Brand colors, nothing else) and a copy of `andon_icon_light.svg`/`andon_favicon_light_32.svg` in `docs/assets/`? Without them: Material's nearest named palette (teal/amber) and no logo.
2. **Built site (`site/`):** not committed; built on demand to a folder outside the repo (`mkdocs build -d <path>`), since adding `site/` to `.gitignore` is outside the allowed files. Or allow that one `.gitignore` line?
3. **Installing MkDocs** needs the network once (`pip install -r requirements-docs.txt` into its own venv outside the repo). Only at night, with no session.

### Wed 25 · T05 with option (3) live and the pilot's start (D-F6-282, D-F6-286) · no code 15:15–17:30

D-F6-282 moves Tue 24's dates (D-F6-274 (6), D-F6-275 (4), D-F6-281 (3)) to today. Development's part, in order:
1. **T05 kit (morning, done 11:20):** `EEG_LIVE_RULE=ica` in `backend\.env`; backend **recreated** with `docker compose up -d backend` (`restart` keeps the container's old env: it said `current` after restart); `/health/db` ok; rule `ica` in the container and on the PC. `preflight` run: the FAILs left are the operator's (AURA, Edge, LabRecorder, apps to close) and Unity's WARN; re-run right before T05.
2. **15:15–17:30 no code (D-F6-286).** 14:30–15:25 PC and `preflight` with no FAIL. T05 15:30–16:45 (Sebas operates, team volunteer, D-F6-249/264/278). 16:45–17:30: `autorun`, `replay --rule ica`, `verify_eeg.sql`, `ocul.py` v3, and the export `Claude outputs/eeg_export_25nov_T05/` (EEG Registro 25 Nov 11:30 point 2; no XDF; `export.sql` and `hitches.py` prepared and tested on T04 at 11:35; ready ≈ 16:50). The EEG chat reviews with D-F6-281 (3); go/no-go of (3). Not passed → `EEG_LIVE_RULE=nosound` + `docker compose up -d backend` before the first participant, declared. **Only (c) failing (D-F6-283 (1)):** find the cause with `autorun` and the `FRAME_HITCH` before the first participant; removed → the pilot runs with (3), `live_vs_xdf` watched on the first participant; not found → (2), declared.
3. **After 17:30 (D-F6-283 (2), D-F6-286):** one commit, the comment of `backend/app/config.py:43–44` says `docker compose up -d backend` (not «restart») for a `.env` change. Rule for every `.env` change from now on (`EEG_LIVE_RULE`, `EEG_MONITOR_LIVE`): `up -d`, with no session running. Comment only: no test; `graphify update .`.
4. **Afternoon, if time and outside sessions:** MI (monitor live indices, D-F6-280) behind a switch that is off, own plan and Sebas's OK first. The Latin square order, sets, agenda and V1 kit (D-F6-282 (5)) are not development's.

### Fri 20 night · ICA live behind `EEG_LIVE_RULE=ica` (D-F6-275, D-F6-276) · approved (D-F6-276); I1 → I2 → G → S, a Stop and a commit each

**Added by D-F6-276:** (2) the channel out, in I1; (3) the full LSL simulation, task S after G. (4) `backend/.env` stays `current` until Tue 24. D-F6-277 (the monitor's live indices with (3)) is built only with the validated design, after this, behind a switch; not for Tue 24. D-F6-279 (1) done before I1: AURA publishes no quality nor impedance over LSL (see the draft).

**Board:** D-F6-275 (pilot rule = option (3) live, automatic fallback to (2), gate off-session, Tue 24 T05 as the final gate; changes D-F6-263 (2) and (3)); EEG chat's proposal in `Planteamiento_Tecnico_F4.md`, Registro 20 nov 16:30. Order of tonight (5): clock (done, `4245152`) → **this** → the monitor's live indices only with a validated design (D-F6-274 (2)–(5)); the indices never delay this. Development works off-session (D-F6-251); nothing with the cap.

**What exists.**
- `ica.fit` / `ica.apply` (`app/eeg/ica.py`): the `ocul.py` selection, `scikit-learn` 1.9.1.
- Offline only: `replay --rule ica` and `epochs.cut_session_ica`. Both fit on the **whole XDF filtered in one pass** and correct the **whole session**.
- `config.eeg_live_rule` accepts `current | nosound`. `live.Buffer.rule` is set from it, and the backend's `websocket.py` adds the sound density only for `nosound`.
- **Measured tonight on this PC** (`ica.fit` on the whole filtered XDF): T01 0.23 s, identified (corr 0.97); T03 0.33 s, not (0.40); T03b 0.26 s, not (0.56); T04 0.11 s, identified (0.79). So the fit can run inside live.py's loop, well under the 2 s of D-F6-275 (4).

**The one design choice: live cannot see the whole XDF.** At S6's entry live.py only has what arrived so far. So the live definition is:
1. **Before S6:** epochs cut as option (2) (`nosound`, blink rule on). The ICA does not exist yet; these epochs feed no decision.
2. **At S6's entry:** once the buffer has `EDGE_S` past S6's entry, fit on S4's entry → S6's entry, filtered over [S4 − `PAD_S`, S6 + `EDGE_S`]. This is a fixed span, so the fit does not depend on how the samples arrived in chunks. Epochs whose centre is in S6 or later are held until the model exists (≈ 1 s plus the fit).
3. **Identified (corr ≥ 0.7 and top weight Fp1):** every epoch whose centre is in S6 or later is cut on the corrected signal, without the blink rule, keeping the task sounds of S6–S8 (rule `ica`, as offline). **Not identified, or the fit raises:** the same session goes on with `nosound`, and the reason and the correlation are kept. live.py never stops for the ICA.
4. **Reference (at S7, as today):** recomputed from the whole buffer with the final rule, the ICA applied to all of it (as offline and as `Buffer.reference` already does with a channel out). So the S4 eyes-open fallback reference is corrected too.
5. **`replay --rule ica` and `fill_from_xdf` run the same `Buffer` path**, no whole-XDF fit. `fill_from_xdf` reuses the model live stored (no refit), so the after-session rows keep what the engine saw. `cut_session_ica` stays only as the offline reference for the gate.

**Consequence, declared:** the fit's input now differs from `ocul.py` v3 and today's `replay --rule ica` (a filter over the span instead of the whole XDF). The gate compares against them **with the D-F6-255 tolerances** (same component, corr within 0.02, A-7 within ±1 window), not byte for byte.

**I1 · `Buffer` with rule `ica` (≈ 2 h).**
- Where: `live.Buffer` only. `new_epochs()` gets the model applied to its segment, nothing else (D-F6-275 (2)); `make_epochs`, `window`, `decide()` and the frozen rules are not touched.
- What: the 5 points above. `Buffer(model=…)` takes a stored model and does not refit. `buf.ica` holds the model or the reason.
- Tests (synthetic signal with a blink source on Fp1):
  - identified → S6+ epochs corrected, earlier ones `nosound`;
  - no ocular source → `nosound` with the reason;
  - a fit that raises → `nosound`, no exception;
  - the same epochs, model and reference with 3 chunk sizes;
  - the reference is corrected;
  - a stored model gives the same epochs without refitting.
- **Channel out (D-F6-276 (2)), with synthetic tests:**
  - out **before S6** (other than Fp1): the ICA is fitted without it (7 components) and applied to the channels left;
  - **Fp1** out before S6: the session goes on with `nosound`, marked;
  - out **after S6**: from that channel's time to the end the session is `nosound`, marked with the reason and the time, no refit; the reference is recomputed with `nosound` and the channels left (D-F6-216).
- **Done (`dc9b71b`, approved by Sebas).** Finding accepted (D-F6-280 message): a live epoch can differ in one chunk near a threshold with any rule; G counts them, `new_epochs()` is not touched.
- **Stop.**

**I2 · switch, storage and the after-session path (≈ 1.5 h).**
- `config.eeg_live_rule`: `current | nosound | ica`, comment updated.
- Migration **0022**: `eeg_sessions.ica jsonb` (up and down) with `identified`, `reason`, `corr`, `component`, `top_channel`, fit span, fit seconds and the matrices.
- `live.run`: saves `buf.ica` once it exists and prints `live: ICA identified (corr 0.79, component 6, 0.1 s)` or `live: ICA not identified (corr 0.40 < 0.7): option (2) for this session (D-F6-253 (2))`.
- `websocket.py`: the sound density for `nosound` **and** `ica` (options (2) and (3) both carry it, as `replay` already does).
- `fill_from_xdf` and `replay --rule ica` through the `Buffer` path.
- Tests: config accepts `ica`; migration up/down; `websocket` passes the sounds with `ica`; `fill_from_xdf` with a stored model gives live's epochs; existing replay tests unchanged.
- **Stop.**

**G · gate, off-session, no database writes (≈ 45 min) (D-F6-275 (3)).** A read-only script in the scratchpad (never in the repo), on the XDFs of **T01, T03, T03b and T04**, read in place:
- (a) **Simulated live:** `Buffer` fed with chunks like `live.run`'s pulls (variable, ≈ 0.2 s, markers at their own stamps) gives **the same epochs, reference, model and decisions** as `replay --rule ica`.
- (b) Identified in **T01 and T04**, the same component as `ocul.py` v3 and corr within 0.02 (0.97, 0.79). **Fallback to (2) in T03 and T03b**, with the reason.
- (c) A-7 within ±1 window of v3 and of tonight's backend: T01 18/18, T04 18/18; T03 5/18 and T03b 6/18 with (2).
- (d) Fit time < 2 s and the held S6 epochs released within `EDGE_S` + the fit.
- (e) pytest all green (531 → ?), Unity harness PASS (no Unity change, 119/119).
- **If G does not pass tonight, Tue 24 starts with (2), as D-F6-263.** `backend/.env` stays as it is: `EEG_LIVE_RULE=current` until Tue 24.

**G · done (D-F6-281 (1)):** approved with T03's finding declared (an S6 epoch at the 15-epoch minimum of the reference; 6 EEG effects differ, no action nor level; the same without the ICA).

**S · full simulation over LSL, after G (D-F6-276 (3), ≈ 1 h).** Needs AURA's software and Unity closed: live.py refuses two local `AURA` or `UnityMarkers`. For each of T01, T03, T03b and T04: a test session in the database (its own participant code, `MULTIMODAL_ADAPTIVE`, an `eeg_sessions` row with the montage); the XDF pushed through two LSL outlets (`AURA` and `UnityMarkers`, the XDF's stamps) at 10× into `live.run` with `rule=ica` passed in the process only (`.env` stays `current`). AURA's software and Unity closed meanwhile, so only these outlets exist on this PC. **Done when:** `live.run`'s `eeg_epochs`, its `eeg_sessions.ica` and reference equal G's simulated live for the same XDF; the ICA line printed; the fit < 2 s. Then the test sessions are deleted in one transaction (counts before and after in the draft). A script in the scratchpad, never in the repo. **Stop.**

**V · `verify_eeg.sql`, the live and XDF figures side by side (D-F6-281 (2)), after S.** Official = what the engine saw live (decisions, EEG effect, A-7, reference used); per-epoch indices for analysis = `fill_from_xdf`. verify_eeg already prints A-7 from `adaptation_decisions` and from `eeg_epochs`; it adds how many epochs differ between the live cut and the XDF one. `fill_from_xdf` replaces the live rows, so `autorun` counts them from `live_epochs.csv` (saved before the Stop) against the new rows and stores the count in `eeg_sessions` (migration 0023); verify_eeg reads it. Tests; one commit. **Stop.**

**RT · «reference at threshold» (D-F6-281 (5)), only if time is left after V.** A read-only flag in `eeg_sessions` when S6 ends within ±1 of the 15-epoch minimum; `new_epochs()` untouched. **Stop.**

**After the pilot, with its own number (D-F6-281 (6)):** a causal filter with state between chunks, the same live, in `replay` and in `fill_from_xdf`. Not in the pilot.

**MI · the monitor's live indices (D-F6-277, D-F6-280), only after S (and V), behind a switch that is off.** Validated design: V1.13 *Live indices for the whole session* in the skill's `design-system.md` once Diseño web marks it *Validated (D-F6-280)*, and the files in `design-handoff/monitor/`; texts from `Contenido_UI_Monitor_Indices.md` (subtitle «For viewing only. Decisions use 3-trial windows from S7.», tab title with the state first). It reads `eeg_epochs` and `eeg_sessions` only, no new EEG computation (D-F6-277 (1)). Its own plan before //build; not for Tue 24.

**After G (code close for Tue 24):** commit per piece, `graphify update .`, backend restarted. **Kit line for Tue 24**, before T05: in `backend\.env`, `EEG_LIVE_RULE=ica`, then `docker compose restart backend`. `autorun`'s first lines say which rule it runs with and, at S6, whether the ICA was identified.

**Watch (D-F6-275 (6), does not block):** from the first exports, theta at Fz in the epochs the ICA recovers against the clean ones (T04 +0.67 SD), and how many sessions fall back to (2). The `ocul.py` line already gives both.

**Out of this plan:** the monitor's live indices (D-F6-274 (2)–(5)) wait for the EEG chat's list and the validated design. An «ICA identified / option (2)» line on the monitor is also design (System section), so it waits too.

### Fri 20 evening · the monitor's clock (D-F6-274 (1)) · OK from Sebas; C1 done in `4245152`

**Board:** D-F6-274 (1) (clock stuck; development diagnoses and fixes it now, without waiting for the rest). (2)–(5), the live indices all session, wait for the EEG chat's proposal and the validated design: **not in this plan.** (6) live check on Tue 24.

**Diagnosis (read-only, on T04 `dd1f75af`).**
- The backend's `session.elapsed_ms` (`_LIVE_TOP`, `research.py:494–497`) is the `session_elapsed_ms` of the **newest event**, not the time now.
- The page (`useClock`, `LiveMonitor.tsx:312`) adds `now − dataUpdatedAt` to it, and `dataUpdatedAt` resets on **every poll (`POLL_MS` = 1 s)**. So whenever no event arrives the clock counts one second, jumps back to the last event, and repeats.
- T04: `BASELINE_STARTED` at 123.2 s (**2:03**), then **105 s with no event** until S5. The clock showed 2:03 → 2:04 → 2:03… for all of S4, which is what Sebas saw. The same happens, shorter, in every gap: 16–26 s in S2–S3, ≈ 23 s between S5 trials.

**Fix (backend only, one query; the page does not change).**
- `elapsed_ms` = session time **now**, anchored on the events: `max(session_elapsed_ms − server_received_at in ms)` over the session's events, plus `now()` in ms, while the session is `IN_PROGRESS`. Once it has ended it stays as today (the last event).
- Why the max: an event that waited in Unity's queue (sent late) has a smaller anchor and cannot pull the clock back. Taking only the newest event would.
- The page keeps adding `now − dataUpdatedAt` between polls, now on a base that moves. Same PC, same clock for the database and Edge.
- Not touched: `live.py`, `s3watch.py`, the engine, the database schema, Unity, `/live/current`.
- Known limit: if Unity dies while the session is still `IN_PROGRESS`, the clock keeps counting until the backend aborts it. That is honest (time since the start), and the System lines (heartbeat, latest event) already say it.

**Task C1 · the clock follows the time now (≈ 30 min).**
- `_LIVE_TOP`: the new `elapsed_ms` (anchor + `now()`, only `IN_PROGRESS`), rounded to an int, as the response model asks.
- Tests in `test_research_live.py`:
  - the existing `elapsed_ms == 14600` becomes "≈ newest event + time since it arrived";
  - an event received 30 s ago gives ≈ +30 s;
  - a late event (old elapsed, received now) does not pull the clock back;
  - a `COMPLETED` session gives the last event, as today.
- **Check on T04, read-only:** the same anchor computed with `now()` replaced by the times of S4 (every 10 s from 2:05 to 3:50) has to give a clock that moves with them, never 2:03–2:04.
- **Done when:** backend pytest green (count before → after), Vitest and `tsc` unchanged, one commit, `graphify update .`, `docker compose restart backend` (no session today), `/health/db` ok.
- **Commit (shown first):** `fix(research): live monitor clock counts the time now, not the newest event (D-F6-274 (1))`.
- **Stop.** The live proof is the Tue 24 check (D-F6-274 (6)): the clock must keep moving through S4.

**T04's processing (D-F6-274):** already done before this plan. `ocul.py` v3 is in `Claude outputs/eeg_export_20nov_T04/ocul_T04_v3.txt`, with the backend `replay` of (1)/(2)/(3) (0/18 · 3/18 · 18/18, equal to v3) and the README for the EEG chat. Nothing left but to tell the EEG chat.

### Fri 20 · logo, Player Settings and monitor access (D-F6-268 to D-F6-272) · plan, waits for Sebas's OK

**Board:** D-F6-268 (two ways into the monitor), D-F6-269 (logo in the portal, Unity's Player Settings, the Form), D-F6-270 (windows, Export CSV, latest event, *session ended*, «Sync tap», «—»), D-F6-271 (one plan, three parts; **limits (2)**: only the portal and Player Settings, nothing in `live.py`, `s3watch.py`, the engine, the database or Unity's scenes and scripts; **gate (3) at 16:15 per part**), D-F6-272 (V1.13 access and the new V1.13 states validated as drawn; build even though `design-system.md` still says *Pending*).
**Sources:** `Claude outputs/design-handoff/design-system.md` (77 156 bytes; «Brand», «V1.13 Live session monitor», «V1.13 access»), copied first over the skill's `references/design-system.md`; `design-handoff/brand/`; `design-handoff/monitor/` (`MonitorAccess*.dc.html`, `Accesos_monitor_*.png`); `docs_proyecto/Contenido_UI_Monitor_Accesos.md` (§1, §2, §3, §3.1).

**Found while planning (read-only):** `Application.productName` is used. `SessionCommunicationClient.cs:324` writes the unsent-event queue under `Application.persistentDataPath` (it depends on `companyName`/`productName`) in a built player; in the Editor, where the sessions run, it uses the project folder. Nothing else (LSL stream names, log paths) reads it. **By the rule of D-F6-269 (2), B is the icon only; `productName` stays «NeuroAdaptive Kanji VR».**

**Dependency graph:**
```
copy design-system.md to the skill ──► A logo (portal) ──┐
                                    └► C access + V1.13 states (portal) ──┼──► npm run build ──► gate 16:15 per part ──► close (D-F6-269 (4))
B icon in Player Settings (Unity) ──► Play S0–S2 ─────────────────────────┘
Form header PNG (design-handoff/brand/, no code): any time before the close
```
A and C both touch the rail (`AppShell.tsx`): A first (rail header), then C (the rail item), so each commit stays its own.

#### A · Logo in the portal (D-F6-269 (1), «Brand») · ≈ 15 min · 1 commit
- **Favicon:** `andon_favicon_light_32.svg`, `andon_favicon_dark_32.svg` and the 180 px apple-touch PNGs into `dashboard/public/brand/`; `index.html` links the light and dark SVGs with `media="(prefers-color-scheme: …)"` and the apple-touch PNG. The SVGs are the source; nothing redrawn.
- **Rail header:** the 32 px icon (`andon_icon_light_32.png` / `_dark_32.png` by theme) **above** «NeuroAdaptive VR» (Newsreader 500, 22/28); the rail keeps 240 px; `alt=""` (the name follows as text).
- **Not** on participant screens (pre-test, free recall; D-F6-117) and not on V1.13's no-session state (drawn without it).
- **Check:** Vitest (the rail shows the icon as decorative), `npm run build`, harness PASS; the rail in light and dark at 1440 × 900.

#### B · Unity, Player Settings only (D-F6-269 (2)) · ≈ 15 min + Play · 1 commit
- **Icon only:** `andon_icon_light_1024.png` into `unity-client/Assets/Branding/` (its `.meta`, texture type Default), set as the default icon (Editor command through the Unity MCP, `PlayerSettings.SetIcons`). **`productName` not changed** (finding above). No scene, script or content touched: the commit holds `ProjectSettings.asset` and the Branding files only.
- **Check:** harness PASS and **a Play in the Editor from S0 to S2 without errors** (D-F6-271 (3)). It needs someone to press Start in S1 to reach S2: **Sebas, ≈ 2 min, no headset**; otherwise I Play to S1 and read the console, and say S2 was not reached. Then **Unity reopened** (a Play leaves a `UnityMarkers` outlet).

#### C · Monitor access and the new V1.13 states (D-F6-270, D-F6-272) · ≈ 30 min · 1 commit
- **Backend, read only (`/research`, no schema change):** `GET /research/live/current` follows **the IN_PROGRESS session with the latest event** (D-F6-270 (3)) and returns `external_code` (rail tooltip); `/research/sessions/{id}/live` adds `completed_at` («closed at {hh:mm:ss}»). Test: two IN_PROGRESS sessions → the one with the newer event.
- **Rail entry (§1):** second item under Sessions, «Live monitor», signal icon `M1.5 8.5h3l1.5-4 3 7 1.5-3h4`; at the end of the pill an 8 px dot `#3FB7C2` + «Live» with a running session, an empty ring without one or when the backend does not answer; accessible names and tooltips from §1. Opens `/monitor` in the same window; never disabled; polls `live/current` every 5 s.
- **Session view (§2):** only while `IN_PROGRESS`, «Open live monitor» outline pill in place of Export CSV, `target="_blank" rel="noopener"`, signal icon + external-window mark, tooltip and accessible name from §2; closed sessions keep Export CSV and show nothing in its place.
- **V1.13 `sessionEnded` (§3.1):** on `/monitor/<id>` once the session is no longer IN_PROGRESS: banner «This session has ended» + «Session {id8} closed at {hh:mm:ss}. Its data is in the session view.» + «Open session view» (same window); the panels keep their last data in the stale style (`--color-bg`, 1 px dashed `--color-border-strong`). `/monitor` without an id goes back to «Waiting for a new session».
- **V1.13 `syncTap`:** «Sync tap» in `caption`, `--color-text-muted`, right after the status word (today « · Sync tap» in body text), and design-system's sentence at the end of the rule under the table. **«—» on `autorun`:** already shown; checked.
- **Check:** Vitest (rail live / none, link only on IN_PROGRESS, Export CSV hidden while running, *session ended* banner, Sync tap caption), pytest for `live/current`, `npm run build`, harness PASS; screenshots at 1440 × 900 against `Accesos_monitor_claro.png` and the *sessionEnded* state.

#### Form header PNG (D-F6-269 (3)) · ≈ 10 min · no commit (design-handoff is not in the repo)
- `design-handoff/brand/andon_form_header_1600x400.png`: the «Brand» logo (icon + «NeuroAdaptive VR», Newsreader 500, clear space ¼ of the icon height, Ink on Paper), rendered from the validated SVG and the bundled font with the portal's Playwright; 1600 × 400, the Form header's ratio. Sebas places it in the Form.

#### Gate at 16:15 (D-F6-271 (3)) and close (D-F6-269 (4))
- Each part: its commit with tests green, `npm run build` and harness PASS; B also the Play S0–S2. **A part not passed at 16:15 is reverted (`git revert` of its commit); the others stay.** Nothing is fixed after 16:15.
- Close: `git status` clean, backend and `dashboard` restarted (the new `dist`), Unity reopened, `EEG_LIVE_RULE=current`, `EEG_MONITOR_LIVE=false`, `preflight` without code FAILs.

### Thu 19 · day plan (D-F6-246 to D-F6-255) · waits for Sebas's OK before `/build`

**Board:** D-F6-249 (2) (HEAD_AWAY warning, before 13:40), D-F6-216 and D-F6-224 (CH1), D-F6-246 (options (2) and (3), off live), D-F6-247 (M0, M1 plan, M1 in the background), D-F6-248 and §1 "Jue 19 (agenda)", D-F6-250 (non-evaluable session, for OV). **Priority:** H1 (HEAD_AWAY) → CH1 → D-F6-246 → M0 → M1 plan → M1. BR7 is now 14:00 (D-F6-248); BR6 and BR7 stay as below.

**Time I actually have on the PC today (no work during T03 / T04, D-F6-153, D-F6-248):**

| Slot | Window | Ends with |
| --- | --- | --- |
| A | ≈ 12:30 (OK) – **13:40** | code closed: commit, `git status` clean, backend restarted, Unity reopened |
| B | **15:45 – 16:30** (after T03's `autorun`, export, `ocul.py`) | **16:15** cut of `live.py` for T04; **16:30** code closed |
| C | after **18:40** (T04's processing and `ocul.py` done) | the board says leftovers go to Fri 20 morning; evening only if Sebas says so (question 1) |

A + B ≈ 2 h. The work asked is ≈ 10 h (H1 ≈ 30 min, CH1 ≈ 4 h, D-F6-246 ≈ 4 h, M0 ≈ 1 h, M1 plan ≈ 30 min). So, being honest about it: **H1 takes the first half of slot A; CH1 most likely does not enter T03, and enters T04 only if it is whole by 16:30**; D-F6-246 and M0 happen in slot C or Fri 20 morning; M1's `live.py` does not make T04 (D-F6-247 (5) gate: EEG validation by 16:00, T03's XDF only from 15:40, replay on T02 and T03 before 16:15). Nothing is lost by that: the test sessions run the current rule live (D-F6-241 (2)) and CH1 and the options are re-computed from every XDF afterwards.

**How the gates stay safe:** every slice below is a commit that is inert until its wiring commit. Only the wiring commits (CH1c, and later M1's `live.py`) change what runs live. At each code close, whatever is not whole stays as inert commits (tests green) or in `git stash`; never half-wired.

#### Dependency graph

```
H1 s3watch HEAD_AWAY warning (13:40, for T03)

CH1a bad_channel() pure ──► CH1b offline (make_epochs, features, window, reference, fill_from_xdf, replay, mig. 0020)
                                   │
                                   └──► CH1c live.Buffer wiring (live = offline) ──► T04 only if whole by 16:30
                                   │
                                   ▼
O2 option (2): no task-sound trim S6–S8 + density (epochs, window, concordance) ─┐
O3 option (3): ICA S4–S5 (+ O2), matrix in eeg_sessions  ◄── questions 2–4      ├─► OV validation on T01, T02, T03, T04 vs ocul.py
                                                                                 ┘
M0 nginx serves dashboard/dist (plan above, port 5300)  ──► M1 plan (no code) ──► M1 page + endpoint (background) ──► M1 live.py (later)
                                                                ▲
                                           EEG chat validates the live formulas (D-F6-247 (3))
```

#### H1 · HEAD_AWAY warning in `s3watch.py` (D-F6-249 (2)) · slot A, first, ≈ 30 min

- **What:** in `S3Watch.lines`, between S3 entered and S4 entered, an open `HEAD_AWAY` episode (no `HEAD_RETURNED` with its `episode`) whose start (`t + onset_offset_ms`, as `epochs.excluded_intervals`) is more than **10 s** before the newest EEG stamp → once per episode: `WARNING: HEAD_AWAY open since <state> — re-seat the headset before S4 (D-F6-249)`, `<state>` = the marker's `state` (an episode opened in S2 and still open counts). Reads only the markers already in the buffer; no rule, threshold or recording change (as D-F6-245). Silent from S4 on, as today. Module docstring gets the line.
- **Tests** (`tests/test_eeg_s3watch.py`, the existing synthetic helpers): open 11 s in S3 → one line, said once; open 9 s → nothing; returned at 8 s → nothing; opened in S2, still open in S3 → the line with S2; open after S4 → nothing. Full pytest (468 → 473).
- **Done when:** pytest green, Unity harness PASS (no Unity change; D-F6-249 asks for it), one commit `feat(eeg): HEAD_AWAY warning in S3 (D-F6-249)`, `graphify update .`. **If it is not committed by 13:40, T03 runs with the protocol only** (D-F6-249 (2)); it then goes in slot B for T04.
- Kit line for the operator (draft, not the kit): if the line shows, re-seat the headset and repeat the S3 taps before S4.

#### CH1 · persistently bad channel (D-F6-216, D-F6-224) · slots A and B

Rule and tests as in the CH1 paragraph below (unchanged). Split into three commits:

- **CH1a · the detector, pure (slot A after H1, ≈ 45 min; else slot B).** `epochs.bad_channel(x, ts, labels, markers, t0) -> (label, from_t) | None` and `bad_count`: 30 s bins from `t0` (`grid_origin_lsl`; null → `ts[0]`, as the grid), share of samples > `MAX_UV` per index channel with **±1 s around each `SYNC_TAP` left out** (reuse `s3watch.TAP_GUARD_S`, move the constant to `epochs.py` so both read one value), first channel over 20 % in two consecutive bins → out from the end of the 2nd bin; Fp1 never; 2nd channel → `too_many=True`. **Tests:** one bin / two bins / Cz with 5 taps / bins at the stored origin / two channels / Fp1. Inert: nothing calls it.
- **CH1b · offline path (slot A if time, else B, ≈ 1.5 h).** `make_epochs(..., bad=None)`: the channel leaves the amplitude and flat checks from `from_t`; `features.compute` drops it from `EI_CHANNELS`, theta `None` if Fz; `window.evaluate`: `too_many` → `counted=False` with fallback `BAD_CHANNELS`; `reference.compute`: out after S6 → the S6 (or S4) epochs re-cut with the channel out, then recomputed; migration **0020** `eeg_sessions.bad_channel`, `bad_channel_from_ms`; `concordance.block` carries `bad_channel`. `fill_from_xdf` and `replay.xdf_source` compute it on the whole filtered XDF. Bump `EPOCHS_VERSION`. **Tests:** above + `rules-v2` byte-identical; full pytest (468 now).
- **CH1c · live (slot B, ≈ 1 h).** `live.Buffer` filters each 30 s bin once it closes (with `PAD_S` and `EDGE_S` as for epochs), keeps the counts, passes `bad` to `make_epochs`, writes 0020's columns once, and re-writes the reference if the channel goes out after S6. **Test:** live = offline on the same synthetic signal; `replay --xdf` on T02 with CH1 = `fill_from_xdf`.
- **Gate for T04 (Sebas, 19 Nov 13:15; the same condition D-F6-247 (5) puts on `live.py`):** CH1b2 and CH1c enter T04 only if, by **16:30**: pytest green, harness PASS, **`replay.py --xdf` on T02 and T03 gives the same epochs and decisions as before CH1 (no channel excluded)**, and **the dry-run XDF (`65af2fe4`) excludes F3**. Otherwise T04 runs without CH1 and CH1 goes on in slot C. If CH1 and M1 compete for slot B, CH1 goes first (D-F6-247). If T02 or T03 does flag a channel, that is a finding to report, not a reason to change the rule: CH1 stays out of T04.
- **Gate (D-F6-248):** CH1 enters T03 only if CH1a–c are committed with pytest and the harness in PASS at 13:40 (not expected); else T04 if whole at 16:30; else Fri 20 first thing. **Dry-run proof** (P7 and A-7 with F3 out, beside 0/18) in slot C, read-only; `fill_from_xdf` on `65af2fe4` only with Sebas's OK.

#### O2 · option (2), off live (D-F6-246, D-F6-242 (2), D-F6-147 (2)) · slot C

- **Switch:** `epochs.RULE` ∈ `current` | `nosound` | `nosound_ica`, from `EEG_RULE` (default `current`); `fill_from_xdf` reads it, `replay` gets `--rule`; **`live.Buffer` passes `current` explicitly**, so the env var cannot reach the live path until the go/no-go. `EPOCHS_VERSION` carries the rule.
- **Epochs:** with `nosound`, `excluded_intervals` stops trimming `ANSWER_SELECTED` and the result sound **in S6–S8**; **the stage sound and S5's `AUDIO_ONSET` stay trimmed** (D-F6-242 (2), D-F6-255 (1): what `ocul.py` v2 does).
- **Density:** `window.evaluate` adds `sounds_per_s` of the window and of S6 (same sound events the rule no longer trims); `dense = window ≥ 1.5 × S6`. `concordance.effect`: with `dense`, UNDERCHALLENGED never `CONFIRMED` and STABLE never `LED` (→ `UNAVAILABLE`, as D-F6-147 (2)). The key is absent with `current`, so today's blocks and decisions stay byte-identical.
- **Tests:** a task sound in S7 trimmed with `current`, kept with `nosound`; S5 and stage sounds kept trimmed; dense window → no confirm, no lead; `current` byte-identical on `rules-v2` and on a stored mm session.

#### O2 done (`67e6265`, 17:35) and OV of option (2)

| Session | `ocul.py` v2, (2): A-7 · S6 · dense | Backend `replay --rule nosound`: A-7 · S6 · dense | Within D-F6-255 (2)? |
| --- | --- | --- | --- |
| T01 `0077f47d` | 0/18 · 0 · 9/18 | 0 · 0 · 9 | ✅ |
| T02 `fffc578f` | 0/18 · 0 · 0/18 | 0 · 0 · 0 | ✅ |
| T03 `6bcae154` | 7/18 · 15 · 0/18 | 5 · 14 · 0 | S6 ✅ (±1), dense ✅, **A-7 ✗ (−2)** |
| T03b `2c453b02` | 9/18 · 4 · 4/18 | 6 · 4 · 4 | S6 ✅, dense ✅, **A-7 ✗ (−3)** |

The A-7 gap is not option (2)'s: with the current rule T03b is already 7/18 in `ocul.py` against 2/18 in the backend (T03: 2 and 2). `ocul.py` cuts from the XDF's first sample without the S3 offset and clips each window's clean seconds to the window, while the backend cuts on the live grid (`grid_origin_lsl`) with the offset. To the EEG chat; on a threshold the backend's figure counts (D-F6-255 (2)). With `current`, epochs and decisions byte-identical to `33c2895` on the four sessions.

#### O3 · option (3), off live · slot C · answered by D-F6-252, D-F6-253, D-F6-255 (3)

- **Dependency:** `scikit-learn==1.9.1` in `backend/requirements.txt`, the version `ocul.py` runs with on this PC (Python 3.13.6, the scratchpad venv); image rebuilt with the network, in slot C (D-F6-251).
- **Fit, copied from `ocul.py` v2 (lines 152–157):** `FastICA(8, whiten='unit-variance', random_state=0, max_iter=1000)` on the filtered signal from S4's start to S5's end; sources = `transform` of the whole session; corr_i = |corr(source_i, Fp1)| on the fit span; frac_i = |A[Fp1, i]| / Σ_c |A[c, i]|; **k = argmax(corr_i × frac_i)**; corrected = sources with k set to 0, `@ A.T + mean_`.
- **Identified** (D-F6-242 (3)): corr_k ≥ 0.7 and the largest |A[c, k]| is Fp1's. `ocul.py` only prints this; the backend decides on it: not identified → the session is not corrected and runs with option (2), with the reason and the corr in `eeg_sessions` (D-F6-253 (2)).
- **After the ICA, no blink rule** (Fp1 > 75 µV off); amplitude ±100 µV on the corrected signal, the other rules unchanged (D-F6-252 (2)).

- `app/eeg/ica.py`: FastICA, 8 components, fitted on the filtered S4–S5 span (as `ocul.py`: `whiten='unit-variance'`, `random_state=0`); ocular component = max |corr| with Fp1; **identified only if corr ≥ 0.7 and its largest weight is on Fp1** (D-F6-242 (3)); applied to the whole session; matrix, mean, component, corr in `eeg_sessions.ica` (jsonb, migration 0021, or inside 0020 if CH1b is not committed yet). Then O2's epochs.
- **Tests:** synthetic blink source mixed into 8 channels → found, corr ≥ 0.7, removed; no blink source → not identified, epochs = option (2)'s, reason stored; with ICA, a 90 µV Fp1 blink no longer drops a chunk.

#### OV · validation (D-F6-246) · slot C or Fri 20 morning

`replay --xdf --rule <r>` on **T01, T02, T03, T04**, XDFs read in place on the PC (copied to the container's `/tmp` and deleted after, as V3), against **`ocul.py` v2** (`ocul_19nov.zip`, D-F6-255 (1)). Per session and rule: A-7, non-POOR S6 epochs, the windows ≥ 1.5 × S6's sound density and, for (3), the component and its corr with Fp1.
- **Pass (D-F6-255 (2)):** same component; corr within **0.02**; A-7 within **±1 window**; S6 within **±1 epoch**. Expected causes of a difference: filter (`filtfilt` with notch first vs `sosfiltfilt`), grid (`grid_origin_lsl` vs first stamp), the S3 offset, `FLAT_UV`. **A session right on a threshold** (S6 = 15 or A-7 = 11/18) is noted, and the backend's figure on the `grid_origin_lsl` grid is the one that counts.
- **`ocul.py` v2 so far (13:05, this PC, scikit-learn 1.9.1; `Claude outputs/eeg_export_19nov/`):** T01: (1) 0/18 · 0; (2) 0/18 · S6 **0** (v1: 1) · 9/18 dense; (3) 18/18 · 38 · component 4, corr 0.97 (Fp1). T02: unchanged from v1 (not evaluable, D-F6-250). T03 and T04: v2 after each session (15:40, 18:15). Only aggregates leave the PC (D-F6-192). **D-F6-250:** per session, the share of S6–S8 covered by causes that do not depend on the rule (open `HEAD_AWAY`, recording gaps / equipment), the same for the three options; **≥ 50 % → "not evaluable"**, declared, out of the minimum of 3 and the "2 of 3" (T02 out, 100 %; T01 in, 0 %; T02 without HEAD_AWAY only descriptive). Pytest and the harness in PASS. **Stop:** the table to Sebas and the EEG chat for D-F6-242 on Fri 20.

#### E0 · `eeg_sessions` row only for sessions that reach S3 (D-F6-258 (2)) · slot C, before M0 · **how: waits for PM (draft 19 Nov, question 6)**

- **Found while planning (15:05):** `autorun` finds a new session *by its `eeg_sessions` row* (`autorun.py:97`) and starts the recording from it (AU2, `xdf_path`); `s3watch` checks channels from S2. Creating the row at S3 would start the recording at S3 and lose S1–S2: a change in how sessions are recorded (D-F6-221, D-F6-244).
- **Recommended (no recording change):** the row is still written by `POST /sessions`; when a session turns `COMPLETED` (or `ABORTED`) without a `STATE_ENTERED` of S3, the backend deletes its `eeg_sessions` row (no XDF, no epochs). End result as D-F6-258 asks: only sessions that reached S3 keep a row; the visit 4 of the pilot leaves none. Test: a short visit (S1 → SR → S9) ends with no row; a full session keeps it; an aborted session in S2 loses it.
- **Alternative:** Unity sends `shortVisit` in `POST /sessions` and the backend skips the row (and the LabRecorder name) for it. Touches Unity and the API contract.
- Done today: BR7's row deleted by hand (D-F6-258 (1), 15:03; session, 80 events and 15 trials kept).

#### M0 · as planned above (Wed 18 section) · slot C or Fri 20 morning

Port **5300** (recommended there; confirm). M0.2 restarts the backend: never inside 16:30–18:40.

#### M1 · plan, then page and endpoint in the background (D-F6-247 (2)–(5))

- **M1-plan (≈ 30 min, docs only, slot C):** read `Dashboard_Feature_Monitor_En_Vivo.md`, V1.13 handoff, D-F6-231/233/234 and the EEG chat's validated formulas; write the `/plan` (endpoint shape, page sections, what `live.py` must add per channel). **Stop:** Sebas's OK.
- **M1 code** only after the plan's OK and the EEG validation; page and endpoint first (read-only, no recording change, D-F6-128, D-F6-198). **`live.py` for T04: not expected** (gate above); it goes in a later session with replay on T02 and T03 unchanged.

#### Done in slot A (12:41–12:51)
- **H1** `66a93c2`: live in T03 (s3watch runs inside `live.py`, started by `autorun` per session).
- **CH1a** `3a591a3` and **CH1b1** `9ef14d8`: inert (nobody passes `bad`). CH1b split: **CH1b2** = migration 0020 (`eeg_sessions.bad_channel`, `bad_channel_from_ms`, `eeg_epochs.excluded_channels`), storage in `epochs.save` / `live.save_epochs` / websocket's `_EPOCH_COLUMNS`, `concordance.block` with `bad_channel`, reference re-cut if out after S6, `fill_from_xdf` and replay; not started before T03 to keep the schema unchanged before a cap session.
- pytest 468 → 483; harness 119/119 at each commit.

#### Done 13:15–13:25 (D-F6-256: slot B brought forward)
- **CH1b2** `fb3fad7`: migration 0020 applied on this PC's database; `epochs.cut_session` (detector + reference recut if out after S6) used by `fill_from_xdf`; `excluded_channels` stored live and offline and read by the decision; `bad_channel` in the window and the eeg block only when a channel is out.
- **CH1c** `74ea726`: `live.Buffer` filters each closed 30 s bin and runs the detector; `Buffer.reference`; `live.run` stores `bad_channel` and rewrites the reference if the channel goes out after it was written; `replay.xdf_source` through the same Buffer. Fix found on the way: a bin counts as closed with its last sample (one period), live and offline.
- **Gate (D-F6-256) met:** replay in the container, code before CH1 vs now: T01 and T02 identical (epochs and decisions, byte for byte, no channel out); dry run `65af2fe4`: F3 out from 336 s (S5); non-POOR S5 8 → 41, S6/S7/S8 2/3/2; the EEG still counts in 0 of 20 S7 windows (other causes, as V3). **CH1 enters T03.**
- pytest 491; harness 119/119 at each commit. `live.run`'s database loop has no unit test: T03 is its first real run (the console says `persistently bad channel …` if one goes out).

#### M1 · live session monitor, V1.13 (D-F6-231, D-F6-233, D-F6-234, D-F6-247, D-F6-254) · plan, **waits for Sebas's OK before any M1 code**

**Inputs read (19 Nov, 17:30):** `Dashboard_Feature_Monitor_En_Vivo.md` §2 and §4; the validated mockup `Claude outputs/design-handoff/monitor/` (1440 × 900, light and dark); the EEG chat's validation table (F4 Registro, 19 Nov 12:45, point 2, adopted whole by D-F6-254); the skill `research-dashboard-conventions` (read-only, rule 2: the frontend never reads `session_events.payload`; rule 9: backend restarts only between sessions).

**What already exists and is only read:** stage, clock and ids (`experiment_sessions`, `session_states`); events (`session_events`, projected **in the backend** into one line each, with the routine/flag mark of the mockup); decisions (`adaptation_decisions` + their `eeg` block: `eeg_ei_z`, `eeg_theta_z`, `counted`, `effect`, `bad_channel`); per-epoch trace (`eeg_epochs`, z against `eeg_sessions.reference`, non-POOR only, EI with the 6 or 7 channels the engine used); sync, S4 alpha, reference, excluded channel and `live.py`'s heartbeat (`eeg_sessions`).

**What does not exist:** the per-channel figures (60 Hz, RMS, % > 100 µV, flat, no data, 60 Hz of the session and the per-channel 60 Hz mark). They are computed only by the EEG chat's table, nothing invented.

**Dependency graph:**
```
M1a endpoint GET /research/sessions/{id}/live (+ /research/live/current) ── M1c page /monitor (polls 1 s)
M1b app/eeg/monitor.py (pure) + migration 0021 eeg_sessions.monitor ── wired in live.run (not in Buffer.new_epochs) ──┘
```

- **M1a · read endpoint, no new data (≈ 1.5 h).** `GET /research/sessions/{id}/live`: one JSON snapshot with a `generated_at`. Sections as V1.13: top bar, sync, live indices (the words from the last decision: Low ≤ −1, Normal, High ≥ +1, "Not counted", "Reference after S6"; the per-epoch trace), adaptation decisions (newest first, with ESL/LAL), the event console (last 40 lines, projected in the backend), system (`live.py` heartbeat age, excluded channel and its time, S4 alpha) and `signal_quality: null` until M1b. Plus `GET /research/live/current`, which gives the id of the newest `IN_PROGRESS` session. NULL stays NULL (`—`). **Tests:** a stored session (T03 `6bcae154`, as a fixture-free read test on the DB, and a synthetic one in pytest) gives every section; no `IN_PROGRESS` → 404; every field read from projected tables.
- **M1b · per-channel figures in `live.py` (≈ 2 h).** A pure `app/eeg/monitor.py`, exactly as the validation table: filtered with `preprocess.filter_eeg` over [t − 17 s, t], using only [t − 7 s, t − 2 s]; RMS; % > 100 µV without ±1 s around each `SYNC_TAP` (shared `TAP_GUARD_S`), with "Sync tap" holding the previous colour under 1 s left; flat when any non-overlapping 1 s chunk has peak-to-peak < `FLAT_UV`; no data under `MIN_SAMPLES`; the colour (OK < 5 %, Watch 5–20 % or the last closed 30 s bin > 20 %, Bad > 20 % or flat); 60 Hz from Welch on the **raw** window ending at t (Hann 2 s, 50 %, √(2 Σ 59–61 Hz PSD Δf)); session 60 Hz = median (Watch ≥ 800 µV); per-channel ratio < 0.3 or > 3 → mark. Migration **0021** `eeg_sessions.monitor jsonb` + `monitor_at`; `live.run` writes it every 2.5 s, **without touching `Buffer.new_epochs()`** (D-F6-254). **Tests:** sines of 10/100/1 000 µV at 59.5/60/60.2 Hz with offset and drift → within the EEG chat's figures; a flat channel; a tap-only window keeps its colour with "Sync tap"; the 2 s edge used. **Gate (D-F6-247 (5)):** `replay --xdf` on T02 and T03 gives the same epochs and decisions as before, byte for byte; harness PASS; enters a capped session only with Sebas's OK.
- **M1c · page `/monitor` (≈ 3 h).** One screen, 1440 × 900, no scroll, light and dark, portal tokens only (Lagoon, amber and vermilion with shape and word, D-F6-231 (4)); `/monitor` follows `live/current`, `/monitor/:sessionId` pins one. TanStack Query `refetchInterval: 1000` (no WebSocket: M0's nginx proxies no WS); each section shows its update time and "No data for [n] s" when its source stops. Signal quality shows "Waiting for live.py" while `signal_quality` is null. **Checks:** Playwright at 1440 × 900 against the two mockup PNGs (a session replayed into the DB, nothing faked on screen: rule 8); `tsc -b`; the 5-tell audit (design-rules §5) reported to Sebas.
- **Order:** M1a → M1c (useful already without per-channel figures) → M1b. Each slice its commit; backend restart only between sessions (rule 9); **nothing of M1 enters a capped session without Sebas's OK** (D-F6-247 (5)).
- **Out of M1:** commands from the portal (M2); LabRecorder's and `autorun`'s own status lines (the mockup's "Recording…" and "Running, last line…"): `autorun` writes nothing to the database today. The System section shows the recording path only if the session's summary has it; otherwise `—`. To be asked if Sebas wants it (a small `autorun` write, a recording change: needs a number).

#### Checkpoints
- **13:40:** H1 in (or T03 on protocol only, said to Sebas); commits green, `git status` clean, backend restarted, Unity reopened; Sebas told what entered (expected: H1, maybe CH1a; nothing else live).
- **16:15 / 16:30:** CH1c in or out of T04, said out loud; code closed.
- **End of day:** `tasks/` and the 19 Nov draft (how T03 and T04 were recorded, CH1 status, Dudas or "Sin dudas · 19 nov").

#### Questions (also in the 19 Nov draft, "Dudas para PM")
1. **Evening slot today after 19:00?** Without it, O2, O3, OV and M0 all fall to Fri 20 morning, around two cap sessions, before the go/no-go. Recommend yes, for O2 + OV at least.
2. **Option (3) needs FastICA.** Recommend adding `scikit-learn` (pinned) to `backend/requirements.txt`, the same library `ocul.py` uses, so the figures reproduce; the backend image rebuild needs the network, so it happens in slot C, not during a session. The alternative (FastICA in numpy) avoids the dependency but will not reproduce `ocul.py`'s numbers.
3. **Blink rejection after the ICA.** `ocul.py`'s "ICA S4–S5 + sin recortar sonidos" turns the Fp1 > 75 µV blink drop off; D-F6-242 (3) does not say. Follow `ocul.py`?
4. **A session where the ocular component is not identified** (corr < 0.7 or not on Fp1): option (3) falls back to (2) in that session, or the session counts as "(3) fails"? (Matters for D-F6-242's "in all sessions".)

### Thu 19 · BR6, BR7 and the CH1 rule (detail, still valid; BR7 now 14:00, D-F6-248)

**BR6 · last check of the inputs (morning, ≈ 15 min).** The three are real since Tue (D-F6-223, D-F6-226): texts and new kanji in `kanji_content.json` (`retention`), V1.12 in the portal. What changes: nothing, unless something changed in `docs_proyecto/` since Tue (then the export again, no code). How it is tested: harness all PASS; each input marked real in the draft. **Stop.**

**BR7 · visit 2 test, 12:00 (D-F6-207).** Same participant as the dry run (P01), code only; 3 days after visit 1. Short visit: S1 → block R on set A → R9' → debriefing → close, no S2 (D-F6-229) (≈ 20 min, no cap). **Done when (read-only SQL after):** the visit 2 row points at `65af2fe4`; `BLOCK_R_RECALL_ENDED` once; 10 yes/no; 15 `SR-*` trials; the recall saved in V1.12; nothing from block R in `adaptation_decisions`; findings recorded. If P01 cannot come: Fri 20 morning, last resort Mon 23 with the interval declared. **Stop.**

**CH1 · persistently bad channel (D-F6-216, D-F6-224), after BR7.** Rule values numbered; one implementation for live, replay and `fill_from_xdf`.
- Rule: a channel is persistently bad when **> 20 % of its samples exceed 100 µV in 2 consecutive 30 s bins**; from then to the end of the session it leaves the amplitude criterion and the indices. **At most 1 channel per session** (a 2nd → the session's EEG does not count). **Fz** out → theta frontal `UNAVAILABLE`, Engagement Index with the other 6. **Fp1 keeps its own rule** (D-F6-75), never this one. Out after S6 → the reference is recomputed with the remaining channels.
- **D-F6-224:** (1) the count **leaves out ±1 s around every `SYNC_TAP`**, so the S3 taps never exclude Cz (worst case in the developer's sessions 22 % → 7 %); (2) **the 30 s bins start at the grid origin** (`grid_origin_lsl`, G1), the same live, in `replay.py` and in `fill_from_xdf`; with a null origin (every session before G1, the dry run included) they start where the epoch grid starts today, the XDF's first stamp. Threshold, maximum of 1 channel and the rest of D-F6-216 do not change.
- Where: one function in `epochs.py` that walks 30 s bins from the grid origin and returns `(channel, from_t)`; `make_epochs` drops that channel from the amplitude check from `from_t`; `features.py` uses `EI_CHANNELS` minus it, and theta `None` if Fz; `reference.py` recomputes with the same channels. `live.Buffer` runs the same function on what it has (bins close as time passes), so live and offline agree. Migration **0020**: `eeg_sessions.bad_channel`, `bad_channel_from_ms`; the decision's `eeg` block carries `bad_channel`.
- Tests: synthetic stream with F3 over 100 µV in 25 % of two bins → excluded from the end of the 2nd bin, not before; one bin only → not excluded; Cz with 5 taps in a bin (> 20 % only inside ±1 s of each `SYNC_TAP`) → not excluded; bins start at the stored origin, not at the XDF's first stamp; two channels → session not counted; Fz → theta `UNAVAILABLE`; Fp1 never excluded; live = offline on the same signal; `rules-v2` byte-identical (C5).
- **Proof on the dry run, on this PC (D-F6-216):** XDF copied into the backend container's `/tmp` (same PC, as in V3) and deleted after; `replay --xdf` and a dry recompute (no write) give **P7 and A-7 with F3 excluded**, beside today's 0/18. `fill_from_xdf` re-run on `65af2fe4` only with Sebas's OK (it rewrites its epochs).
- Size ≈ 4–5 h. If it does not finish on Thu, it goes first on Fri 20, before AU1/AU4: the pilot needs it. **Stop.**

**Session automation (D-F6-219): separate section below.** Waits for Sebas's OK; never during a session.

### Fri 20 · AU4, AU0, M0 and the plan of M1, then go/no-go · no presentation, no video (D-F6-227)
- **AU4 · end of session**, as in the automation section, **tested on the dry run `65af2fe4` and on T01's session** (SQL and summary read-only; processing re-run only with Sebas's OK). **Stop.**
- **AU0 · `LabRecorderCLI` spike**, as in the automation section. **Stop.**
- **M0 moved to Wed 18 afternoon (D-F6-235); planned below, waits for Sebas's OK before `//build`.**

### Wed 18 evening · D-F6-239 Unity fixes (exception to the freeze) and D-F6-240 `ocul.py` · plan, waits for Sebas's OK

Order: U1 → U2a (Content validates) → U2b → one Editor Stop for both → commit each → E1 whenever Sebas passes the script (no Unity, can run while Content reviews). **M0 after this if time is left; otherwise Fri 20 (D-F6-239).** Tutorial kanji (一 二 三 五) stay out.

**U1 · the green of a completed KA stays green (≈ 20 min, one file).** `StudioTrialPresenter.cs` only.
- A `bool _assemblyComplete`: set in `ShowAssemblyComplete` (`:1430`); cleared in `HideAssemblySlots` (`:1258`) and in `ShowAssembly` next to `_assemblyActive = true` (`:1099`, both modes pass there), so the next trial starts clean.
- `PaintSlot` (`:1186`) returns first thing when `_assemblyComplete`. That one guard covers both modes, because `PaintSegmentSlot` is reached only through `PaintSlot` (`:1188`), and covers every caller: hover relays (`:1237`, `:1352`), the flash end (`:1182`), the pulse (`:1414`, `:1423`).
- Tested: harness all PASS, count unchanged; Editor with 学 (placeholder mode, until U2b lands) and 月 (image mode): place the last piece, sweep the ray over every slot during the 1.6 s green → it stays green; the next trial's slots paint normally.

**U2a · groups of the 10 reserve kanji: proposal for Content (no script run).** Count per kanji is fixed by `assemblyGroups` in `kanji_content.json`; the script refuses a mismatch. Groups follow stroke order, like the 10 reserve kanji of 19 Oct.

| Kanji | `id` | Strokes | Groups | Proposed groups (slot order) |
| --- | --- | --- | --- | --- |
| 日 sun | `KANJI_NICHI` | 4 | 2 | **frame** (left, top-right fold, bottom) · **middle bar** |
| 田 rice field | `KANJI_TA` | 5 | 2 | **frame** (口 outer box) · **十 cross** inside |
| 子 child | `KANJI_KO` | 3 | 2 | **了** (fold and hooked vertical, strokes 1–2) · **一** (bar, stroke 3) |
| 目 eye | `KANJI_ME` | 5 | 2 | **frame** (left, top-right fold, bottom) · **two inner bars** |
| 学 study | `KANJI_GAKU` | 8 | 3 | **⺍ three dots** · **冖 cover** · **子** |
| 物 thing | `KANJI_MONO` | 8 | 3 | **牜 cow radical** · **勹 hook** · **two inner sweeps** (rest of 勿) |
| 茶 tea | `KANJI_CHA` | 9 | 3 | **艹 grass** · **人 roof and bar** · **朩 bottom** |
| 馬 horse | `KANJI_UMA` | 10 | 3 | **vertical and three bars** · **hooked frame** (bottom bar and hook) · **灬 four dots** |
| 魚 fish | `KANJI_SAKANA` | 11 | 3 | **ク head** · **田 body** · **灬 four dots** |
| 鳥 bird | `KANJI_TORI` | 11 | 3 | **ノ and the box** (top, eye bar) · **bar and hooked frame** · **灬 four dots** |

- Asked of Content: per kanji, OK or a different split (same group count, or say if `assemblyGroups` must change, which is a contract change and needs a number). Open points I'd flag: 日 and 目 could also split "left side · the rest"; in 鳥 the eye bar could go with the body.
- Stop: no script run until Content's answer is in the draft.

**U2b · cut and write (≈ 1–1.5 h).** `tools/assembly_segments.py`: the 10 entries in `G` (centre lines placed by hand on the 512 px glyph), the 10 ids in `IDS`, `OVR` boxes where a stroke must stay whole (田's cross, 馬's vertical, 物's 牜 vertical). Iterate on `tools/assembly_preview.png` until every group is whole and no stray pixels; then the run writes `Resources/assembly/{ID}_FULL/SEG{n}/SEG{n}_CARD.png` and lists the segments in the 10 `.asset` files. The 26 kanji already cut are re-written by the same run: their PNGs must come out byte-identical (`git status` shows only the 10 new kanji's files + preview + script).
- Harness: a new check, **every non-tutorial kanji (35) has authored segments with as many as `assemblyGroups`**, so a placeholder in S5 cannot come back silently. Count before → +1, all PASS.
- Editor: an S5 where 学 appears (pre-test substitute, as in T01): console says authored, board shows the pieces, cards read; U1's green holds on 学 too.

**Editor Stop (Sebas, ≈ 10 min):** 学 and 月 in S5, green held while sweeping the ray. Then two commits, Unity body says "exception D-F6-239": `fix(unity): completed assembly stays green (D-F6-239)` and `feat(content): assembly segments for the 10 reserve kanji (D-F6-239)`. `graphify update .`.

**E1 · `ocul.py` on T01's XDF (D-F6-240 (1), ≈ 20 min once the script is here).**
- Sebas passes the script from the EEG chat. I read it whole before running it (what it reads, what it writes, any network or file output).
- Input: `C:\Users\drdom\Documents\Pruebas_EEG\sub-t01\ses-0077f47d\eeg\sub-t01_ses-0077f47d_task-multimodaladaptive_run-1_eeg.xdf`, read in place, never copied into the repo or `Claude outputs/`.
- Dependencies: `mne` is not in the backend venv nor in the container. If the script needs it, a throwaway venv in the session scratchpad (`pip install mne pyxdf`), not `backend/requirements.txt`. Run with `python -I` from outside the script's folder.
- Output: only the aggregate figures (blinks per minute, % of the task each rule covers, the ICA recovery in S4–S5, whatever the script prints as summary) go into the 18 Nov draft and the chat. No per-sample or per-epoch output leaves the PC; any file the script writes stays in the scratchpad.
- D-F6-240 (2)–(4) are protocol and kit lines (Fp1 check in S3, per-session report, `live_epochs.csv` before Stop): kit text for AU5, no code today.

### Wed 18 · M0 · the portal served by `docker compose up` (D-F6-231 (5), D-F6-235) · plan, waits for Sebas's OK

**Found while planning (read-only, 18 Nov 14:30):**
- The portal calls the API as `/api/...` and Vite strips `/api` (`dashboard/src/api/client.ts`, `vite.config.ts`). So nginx proxies **`/api/` → `http://backend:8000/`** with the prefix stripped, not `/sessions`, `/participants` and `/research` as the line above said.
- **`dashboard/dist` dates from 22 Oct**: it lacks V1.10 changes, V1.12 (BR3) and everything since. Serving it as it is would show an old portal. M0 builds it first (`npm run build`, which also runs `tsc -b`). `dist` stays gitignored; compose serves what was last built.
- `nginx:alpine` is already on this PC (no pull, works offline). Today the portal is the Vite dev server on `127.0.0.1:5300` (strict port).
- The pages use client-side routes (`/pretest`, `/sessions/<id>`…): nginx must fall back to `index.html`.

**Decision for Sebas (recommendation first):**
1. **nginx on `127.0.0.1:5300` (recommended).** The kit, `preflight` (AU1), the Playwright `baseURL` and Edge's bookmarks stay the same. `npm run dev` only for portal development, after `docker compose stop dashboard` (both want 5300).
2. Another port (e.g. `127.0.0.1:5310`). Dev server and nginx can run together, but the kit, `preflight` and Playwright change.

**Dependency graph:** `npm run build` → `dist/` ──► nginx config + compose service ──► from-scratch check (compose, ports, Playwright) ──► kit/doc lines.

**M0.1 · nginx serves the built portal, `/api` to the backend (one vertical slice, ≈ 30 min).**
- Files: `dashboard/nginx.conf` (new), `docker-compose.yml` (service `dashboard`).
- Service: `image: nginx:alpine`; `ports: "127.0.0.1:5300:80"` (127.0.0.1 only, like db, backend and pgadmin: no auth, participant data, D-F6-186); volumes `./dashboard/dist:/usr/share/nginx/html:ro` and `./dashboard/nginx.conf:/etc/nginx/conf.d/default.conf:ro`; `depends_on: backend`; `restart: unless-stopped`.
- Config: `location /api/ { proxy_pass http://backend:8000/; }`; `location / { try_files $uri $uri/ /index.html; }`; `index.html` with `Cache-Control: no-cache` (a rebuild shows at once); hashed assets cached. No outside hosts (fonts are already bundled, rule 7). No WebSocket proxy: the portal uses none today (M1 adds it if it needs it).
- **Acceptance:** `npm run build` exit 0; `docker compose up -d dashboard` → `curl.exe -s -o NUL -w "%{http_code}" http://127.0.0.1:5300/pretest` = 200, `/sessions/0077f47d-…` = 200 (fallback), `/api/health` = `{"status":"ok"}`, `/api/research/...` returns data; `docker compose port dashboard 80` = `127.0.0.1:5300`.

**M0.2 · from scratch and the smoke (≈ 20 min, only between sessions: it restarts the backend).**
- `docker compose down` (**never `-v`**: it deletes the database volume) → `docker compose up -d` → `db`, `backend`, `pgadmin`, `dashboard` up; `docker compose ps` shows every published port on `127.0.0.1`, none on `0.0.0.0`.
- With `npm run dev` stopped: `npx playwright test` from `dashboard/` (Playwright reuses whatever answers on 5300 = nginx). All specs pass, or each failure is explained.
- `python -m app.eeg.preflight`: the portal line is still OK.
- **Acceptance:** all of the above; Edge opens `http://127.0.0.1:5300/pretest` with the current portal (V1.12 recall form present).

**M0.3 · docs (≈ 10 min, no code).** A comment in `docker-compose.yml` (rebuild `dist` after a dashboard change; dev server needs `docker compose stop dashboard`). One line in the skill's `stack-and-structure.md` (how the portal is served). The kit line (R3: "portal from `docker compose up`, no `npm run dev`") goes into the draft for AU5, not into the kit itself.

**Checkpoint:** after M0.2, **Stop**: Sebas opens the portal in Edge from nginx. Commits: one for M0.1 (feat), one for M0.3 (docs), each message shown first.

**Risks:** (1) BR7 is tomorrow at 12:00 and uses V1.12. If anything is wrong, `docker compose stop dashboard` + `npm run dev` puts back today's way in 1 min. (2) A stale `dist` serves an old portal without saying so: the build is a kit step after any portal change. (3) M0.2 restarts the backend: never during a session (skill rule 9).

**Out of M0:** building `dist` inside Docker (Node image, network), HTTPS, auth, the WebSocket proxy for M1.
- **`/plan` of M1, no code (D-F6-231, D-F6-233):** the live monitor V1.13 (per-channel figures in `live.py`, a read-only endpoint, the page), to build during the pilot on a day without a participant, with AU2, AU3 and AU6. **Stop:** Sebas's OK on the plan.
- **Go/no-go** of the pilot (PM, Sebas); the M4 note is PM's. This chat hands in: what is live (G1, G2, S1, S6, block R with V1.12, CH1, X8, AU1, AU4), BR7's and T01's results, open findings, `tasks/` and the draft up to date.

### Wed 18 evening · AU0, AU2, AU3, AU4 before T02 (D-F6-244) · plan, waits for Sebas's OK

**D-F6-244 changes D-F6-221 (2)–(3) for today:** the four pieces go in now, before T02, and **T02 is the first capped rehearsal (AU6)**; Thu 19 and Fri 20 sessions too. The pilot starts automated on Tue 24 only if this week's sessions go well; otherwise manual (D-F6-221 (1)). M0 stays Fri 20. The task text in "Session automation" below still holds; this section says what changes in it, how each piece is tested without a cap, the order and the cut-off.

**Order and time (≈ 5–6 h of work):** AU0 (≈ 45 min) → **gate** → AU2 (≈ 2 h) → AU4 (≈ 1.5 h) → AU3 (≈ 1.5 h) → backend tests, Unity harness, commits, code closed, T02 kit (≈ 30 min). After an OK at ≈ 18:30 that ends near midnight. **Cut-off, set by Sebas with T02's time:** what is not committed with all tests green 45 min before T02 stays out of T02 (`git stash`), and T02 runs with what is in. After AU0 the pieces are independent: AU4 and AU3 do not need AU2.

**Kept, and checked by the script (D-F6-244):**
- **D-F6-146:** the file name carries the session id: the recorder starts only after Play created the session, with `xdf_path` from `eeg_sessions` (the same BIDS path as today). `autorun` prints the path and, at the end, checks the XDF it reads is that one.
- **D-F6-193:** the network is never touched. `autorun` warns if a physical adapter is up at Play and again at the end of S2; the host filter keeps other PCs' streams out of the file either way.
- **D-F6-197:** exactly one `AURA` of this PC before recording; two → no automatic recording, manual path. Taps: AU3 says `k/5 clear` after S3 and asks to repeat below 3.
- **D-F6-217:** 5 taps in S3, none in S9: AU3 counts S3's taps and warns on a tap after S3; `sync.py` keeps the robust spread.
- **D-F6-240:** (2) Fp1 gets its own line in AU3's S3 check (continuously over ≈ 100 µV with eyes open → "re-seat Fp1 and the foam before S4"); (3) the summary gives the % of POOR per state and per rule now, and blinks per minute once `ocul.py`'s count is folded in; (4) **`live_epochs.csv` is exported by `autorun` itself when the session turns COMPLETED, before the recording stops** (AU4), on both paths.

**Manual fallback (D-F6-244 (2)), the same for every failure:** LabRecorder's GUI stays open on every session, not started. If `autorun` does not print `RECORDING (automatic): AURA + UnityMarkers of LaptopSebas1803 → <path>` within 15 s of Play, it prints `MANUAL: Update, tick the one AURA and UnityMarkers, check ses-<8> in the name, Start` with the reason, Sebas does today's steps and the session goes on; `autorun` then waits for the GUI's file as today. Each session's recording path (automatic / manual and why) goes into the summary, the log and the draft.

**If AU0 fails (D-F6-244 (3)):** AU2 is not built and recording stays manual (today's kit); AU3 and AU4 are built and enter T02.

**AU0 · `LabRecorderCLI` with a host filter (≈ 45 min, no cap).** On this PC: `backend/scripts/synthetic_aura.py` (`AURA`), Unity in Play in the Editor without the headset (`UnityMarkers`, as in the 17:26 check) and a dummy `AURA_Markers` outlet; network on.
- The CLI with `name='AURA' and hostname='LaptopSebas1803'` and `name='UnityMarkers' and hostname='LaptopSebas1803'` into a scratch folder, Enter after 60 s. **Pass:** `pyxdf.load_xdf` reads exactly those two streams (no `AURA_Markers`), both with samples, file closed.
- **Negative test**, because the other PC may not be streaming: the same query with `hostname='MSI'` matches nothing and the CLI exits without a file (proves the filter acts). If MSI is on, its `AURA` must be absent from the pass file.
- `hostname` refused → try `source_id`. Nothing works → **stop and tell Sebas: AU2 out.** The test `DEV_UNITY` session and the scratch file are deleted after, with Sebas's OK.

**AU2 · `autorun` records (≈ 2 h).** A new `app/eeg/recorder.py` (CLI command line, start, stop) and changes in `autorun.py`:
- after `wait_new_session`: resolve on this PC, retrying up to 15 s, one `AURA` and one `UnityMarkers`; synthetic or two `AURA` → manual path with the reason (the check is `preflight.check_lsl`, reused); network up → WARN.
- launch `LabRecorderCLI` with the session's path and the two queries, stdin open; print the RECORDING line; every 10 s check the process is alive and the file grows. If it exits early → `RECORDING STOPPED at mm:ss` and the manual steps; Sebas starts the GUI on a `run-2` path that `autorun` prints, and `fill_from_xdf` reads that one (the CLI's partial file is kept).
- at COMPLETED: AU4's live export first, then Enter to the CLI, wait for it to exit and `wait_xdf_closed` as today. In `finally`, Enter is sent if the CLI still runs, so the file is never left open.
- **Tests (pytest):** the command line for a session; the one-local-AURA decision; the stop and `finally` paths with a fake recorder process. **Without a cap:** synthetic AURA + Unity Play in the Editor: Play → RECORDING line → 2 min → exit Play → Ctrl+C on `autorun` → file closed, `load_xdf` shows the two streams. A second run with two synthetic `AURA` → MANUAL line, nothing recorded.

**AU4 · end of session (≈ 1.5 h).** In `autorun.py`, plus `app/eeg/summary.py`:
- at COMPLETED: `live_epochs.csv` from `eeg_epochs` (read-only) into `backend/logs/<session>-live_epochs.csv` (D-F6-240 (4)); then the stop; then today's `lsl_reader` → `sync` → `epochs`.
- the four SQL through `docker compose exec -T db psql`: `database/verify_eeg.sql`, `verify_adaptation.sql`, `verify_projection.sql`, and `p0_j3_fallback_check.sql` (copied into `database/` from `Claude outputs/`), each to `backend/logs/<session>-<name>.txt`.
- a summary, printed and saved (`<session>-summary.txt`): recording path, Play → S9, accuracy per state, A-7 live and from the XDF, sync (offset, robust spread, k/5 taps), S4 alpha, S6 source and epochs, Fp1 and POOR % per state, decisions and changes, any FAIL/OUT/SHORT line of the SQL. Exit 0 only if every step ran.
- **Tests:** the summary from fixed rows; the export query. **Without a cap:** the SQL and the summary on T01 `0077f47d`, read-only, no re-processing; they must match the 18 Nov analysis (5/5 taps, 35.7 ms, A-7 0/18, 243/292 POOR).

**AU3 · warnings in S3 (≈ 1.5 h).** In `live.py`, which already reads both streams from Play and computes S3's offset:
- per `SYNC_TAP` in S3: `tap n/5: clear (peak µV)` or `NOT clear` (`sync._tap`); after S3: `S3 taps k/5`, and with `k < 3` → `WARNING: repeat taps before S4`; a tap after S3 → `WARNING: tap outside S3 (D-F6-217)`.
- from S2 to the end of S3, every 10 s, the share of the last 30 s over 100 µV per channel; over 20 % → `WARNING: <ch> looks bad, fix before S4`; Fp1 continuously high → the D-F6-240 (2) line. From S4 on, only errors are printed (D-F6-153).
- **Tests:** synthetic signals (clear and unclear tap, a flat channel, a noisy one). **Without a cap:** T01's XDF fed as live, as `replay --xdf` does: 5/5 clear, as measured; the same with F3 replaced by noise → the warning.

**After the build:** backend pytest all green (count before → after), Unity harness PASS (no Unity change expected: 119/119), one commit per piece, `graphify update .`, `git status` clean, backend restarted, Unity reopened, `preflight`, and the T02 kit with the automated steps and the manual fallback boxed.

## Session automation (D-F6-219) · approved in two parts (D-F6-221)

**D-F6-221:** Sebas is away Sat 21 – Mon 23, so there is no rehearsal before the pilot. (1) The pilot **starts on Tue 24 with manual recording** (today's kit). (2) **AU1 and AU4 on Fri 20 morning**, tested on the dry-run XDF on this PC; they enter from Tue 24 because they do not change how a session is recorded. **AU0 only if time is left** on Fri 20; if the host filter does not work, recording stays manual. (3) **AU2 and AU3 wait** for a pilot day without a participant, with a full rehearsal (AU6) with Sebas; if it passes, recording switches from then on and the sessions are labelled by how they were recorded; with no such day, the whole pilot is manual. (4) What does not finish on Fri 20 goes to **Tue 24 morning**; the first participant is Tue 24 afternoon. AU5 (kit) follows the part that is live: on Fri 20 only AU1 and AU4 enter the manual kit.

**Goal:** Play starts the recording and the EEG processes by itself; when the session ends, the recording stops and the processing, the four SQL and a summary run, with as few manual steps as possible. What D-F6-146, D-F6-193, D-F6-197 and D-F6-217 fixed stays, now checked by the script.

### Finding first: LabRecorder's remote control cannot pick streams by name

From LabRecorder's source (installed version 1.18.0, `Downloads\LabRecorder-1.18.0-Win_amd64`): the remote socket accepts only `start`, `stop`, `update`, `filename {…}`, `select all` and `select none` (`tcpinterface.cpp`, which has `// TODO: select /deselect streams`). And its remote **`start` calls `selectAllStreams()` before recording** (`rcsStartRecording` in `mainwindow.cpp`). So by remote control LabRecorder records **every stream it sees**: with the network off, this PC's `AURA`, `UnityMarkers` and also `AURA_Markers`; with the network on, the other lab PC's streams too (its `AURA` among them). That is why `labrecorder.py` today sends only `filename` and leaves Start to the operator.

**Proposal: record with `LabRecorderCLI.exe`**, which ships in the same folder. It takes one LSL query per stream, records **every** stream that matches each query, and stops when it reads Enter on its standard input. `autorun` would launch it with two queries, `name='AURA' and hostname='LaptopSebas1803'` and `name='UnityMarkers' and hostname='LaptopSebas1803'`, so only those two are recorded whatever the network shows. It uses the same recording library as the GUI (same clock offsets in the XDF). Limits, read in its source: it resolves the streams **once** and exits (code 2) if a query matches nothing, and it has no "exactly one" check, so two local `AURA` would both be recorded. The script covers both (AU2). The `hostname` field is not shown in its README and is the first thing AU0 tests.

LabRecorder's GUI stays installed as the **fallback**: if `LabRecorderCLI` cannot start, `autorun` says so and the operator does today's manual steps (Update, tick the two streams, Start).

### Scope

| In | Out |
| --- | --- |
| A pre-session check command (R3) | Turning the network off or on (manual, D-F6-193; the script only reports it) |
| `autorun` starts everything and records with `LabRecorderCLI` when Play creates the session | Starting Unity, Play or the AURA software |
| Exactly one `AURA` of this PC checked before recording | Driving LabRecorder's GUI (not needed on the automated path) |
| Warnings in S3, before S4: a channel going bad, taps not clear | Reading the AURA software's own red/blue colours (not on LSL; the script uses the signal, D-F6-216's measure) |
| At the end: stop, file closed, processing, the four SQL, a summary | Any change to the rules or to Unity |

### Tasks

**AU0 · spike: `LabRecorderCLI` with the synthetic AURA (≈ 1 h; no participant, no session) · only if time is left on Fri 20 (D-F6-221).** Synthetic AURA and a test `UnityMarkers` outlet on this PC, network on so the lab PC's `AURA` is visible. Launch with the two queries into a test folder; Enter after 60 s. **Done when:** the XDF has exactly the two local streams (not `MSI`'s `AURA`, not `AURA_Markers`), `load_xdf` reads it, the file is closed; the query syntax that works is written down. If `hostname` is not accepted, try `source_id`; if nothing selects by host, **stop and tell Sebas**: the fallback is the manual GUI kit. **Stop.**

**AU1 · pre-session check, `python -m app.eeg.preflight` (≈ 2 h) · Wed 18 afternoon, after T2 (D-F6-232).** On the manual path: LabRecorder's GUI running is expected (OK), not a WARN; `LabRecorderCLI` is not checked until AU2. One command, one line per check (OK / WARN / FAIL), exit 0 only with no FAIL:
- backend `/health` and `/health/db`; db port `127.0.0.1:5432`; portal `/pretest` 200.
- `git status` clean.
- processes: one Unity Editor and its start time (restarted?), AURA software and Edge running; Blender, Firefox, VS Code, ChatGPT/Codex closed; LabRecorder's GUI running = WARN "manual path".
- LSL on this PC: exactly one `AURA`; synthetic off; streams of other hosts = WARN (network on).
- network adapters up = WARN "turn the network off before the cap" (never changes them).
- `LabRecorderCLI.exe` found; `Pruebas_EEG` writable; free disk.
Done when it gives the same verdicts as today's manual R3 on this PC, in both states (all good / Blender open). Tests: each check a small function; processes parsed from `tasklist /FO CSV` (no new dependency: `psutil` is not installed).

**AU2 · `autorun` records (≈ 3 h) · waits for a pilot day without a participant (D-F6-221 (3)).** After `wait_new_session`: (1) resolve on this PC exactly one `AURA` and one `UnityMarkers` (retry up to 10 s while Unity opens its outlet); two `AURA` → **no recording, loud message, manual path** (D-F6-197); (2) network up → WARN, recording continues (the host filter already excludes other PCs; privacy stays D-F6-193's manual step); (3) create the folder and launch `LabRecorderCLI` with the session's BIDS path (`labrecorder.xdf_relpath`, as today) and the two queries, stdin kept open; (4) watch it: file growing, process alive; if it exits early, say so with the time and print the manual steps. On `session COMPLETED`: send Enter, wait for the process to end and the file to close (today's `wait_xdf_closed`). In `finally`, if `autorun` fails it still sends Enter, so the file is never left open. Tests: the command line built for a session; the "exactly one AURA" decision; the stop path with a fake recorder process.

**AU3 · warnings in S3, before S4 (≈ 2–3 h) · waits with AU2 (D-F6-221 (3)).** `live.py` already reads both streams from Play. It adds, in `autorun`'s console:
- after each `SYNC_TAP` of S3: `tap n/5: clear (peak µV)` or `NOT clear`; after the 5th: `S3 taps: k/5 clear` and, with k < 3, `WARNING: repeat taps before S4` (D-F6-197).
- from S2 to the end of S3, every 10 s: D-F6-216's measure per channel over the last 30 s; a channel over 20 % → `WARNING: <ch> looks bad (x % > 100 µV), fix before S4` (protocol of D-F6-213/216). It only warns; the rule acts in CH1's code.
Done when, on the dry-run XDF fed as live (as `replay --xdf` does), the tap lines match V3's 10/10, and a version with F3 broken before S4 raises the warning. Tests on synthetic signals.

**AU4 · end of session (≈ 2 h) · Fri 20, tested on the dry run and on T01 (D-F6-232).** On the manual path the operator still presses Stop; `autorun` keeps waiting for the file to close (as today). After the file closes: `lsl_reader` → `sync` → `epochs` (today); then the **four SQL** of kit §8 (`verify_eeg`, `verify_adaptation`, `verify_projection`, `p0_j3_fallback_check`) through `docker compose exec`, each saved to `backend/logs/<session>-<name>.txt`; then a **summary** printed and saved (`<session>-summary.txt`): Play → S9 duration, accuracy per state, A-7 live and from the XDF, sync (offset, robust spread), S4 alpha, S6 source and epochs, bad channel if any, decisions and changes, any FAIL/OUT/SHORT line from the SQL. On the manual path the summary ends by reminding to close LabRecorder's GUI; with `LabRecorderCLI` (later) it has already exited. Exit 0 only if every step ran. Tests: the summary from fixed rows. **Proof on the dry run, on this PC:** the four SQL and the summary on `65af2fe4` (read-only); the processing step re-run on it only with Sebas's OK, because it rewrites the dry run's epochs (after G1, S1, CH1 they differ from Monday's).

**AU5 · kit (docs, ≈ 1 h).** The operator kit for the automated path: `preflight` → network off → `autorun` → Play → S3 (read the warnings) → S9 → summary. The manual GUI steps stay as a boxed fallback.

**AU6 · rehearsal with Sebas, no participant (a pilot day without a participant, ≈ 1 h; not Mon 23, D-F6-221).** Synthetic AURA and headset, a full S1–S9 session with `autorun` doing everything; the session deleted after with Sebas's OK. **Done when:** XDF with exactly the two streams, the four SQL and the summary written, no manual step except Play, the network and the S3 keys. **Go/no-go:** pass → automated recording from the next session, with each session's recording path written down; fail or no such day → the whole pilot manual.

### Estimate and calendar

**Part 1 (D-F6-221): Fri 20 morning, ≈ 4–5 h:** AU1 2 h → AU4 2 h → kit lines for both (≈ 30 min) → AU0 1 h only if time is left. Leftovers → Tue 24 morning, before the first participant in the afternoon.
**Part 2, later in the pilot, ≈ 7 h:** AU2 3 h, AU3 2–3 h, AU5 for the automated path 1 h, AU6 1 h with Sebas on a day without a participant (and AU0 first if not done).
The pilot does not depend on part 2.

### Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| `LabRecorderCLI` does not accept a host filter | High: it would record foreign streams | AU0 tests it first; if no syntax works, the plan stops there and the GUI kit stays |
| The recording tool changes during the pilot | Med | Only after AU6 with Sebas on a day without a participant; every session labelled by recording path (D-F6-221 (3)) |
| AU1 or AU4 not finished on Fri 20 | Med | Tue 24 morning (D-F6-221 (4)); the manual kit works without them |
| AU4 re-run on the dry run rewrites its epochs | Low | SQL and summary read-only; processing re-run only with Sebas's OK |
| `autorun` dies mid-session and the recorder keeps recording, or the file is left open | Med | Enter sent in `finally`; the kit says how to stop it by hand (Enter in its window); `pyxdf` reads a file without its footer |
| Streams not up when Play creates the session (the CLI resolves once) | Med | `autorun` resolves first with retries and launches the CLI only when both are there; preflight checks AURA before Play |
| A warning tempts touching the PC after S4 | Med | Warnings only in S2–S3; from S4 only errors are printed (D-F6-153) |
| Network left on | Med | Reported by preflight and `autorun`; recording is safe by host filter; privacy stays the operator's step (D-F6-193) |
| Sebas away Sat 21 – Mon 23, no buffer before the pilot | Med | Part 1 only on Fri 20; nothing that changes recording before the pilot (D-F6-221) |

## Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| The dry run brings a pilot blocker | High | Recorded in V3 with "blocks yes/no"; fixed only after U0 and with a number |
| Block R does not fit Tue–Wed (largest piece, Wed has the workshop) | High | Nothing else enters Tue–Wed; slices in order BR1 → BR2 → BR4 are the minimum for Thu; BR3 can fall back to recall noted on paper and typed after (declared) |
| A channel loses contact mid-session in the pilot (as F3 on 16 Nov) | High | Protocol of D-F6-213: fix any red channel before S4; a loss from S4 to S8 is accepted and declared; the behavioural fallback covers the session (proved in `65af2fe4`); the rule of D-F6-216 and D-F6-224 enters with CH1 on Thu 19 |
| Visit 2 participant cannot come Thu | Med | Fri 20 morning, then Mon 23 with the interval declared (D-F6-207) |
| G1 changes the epochs A-24 is decided on | Med | Old sessions keep the null origin = today's cut; V3 figures labelled with their grid |
| G2 drops a session's offline epochs | Low | Only with two local `AURA`; the live epochs stay and the log says why (D-F6-206) |
| 32 茶 (6 706 tris) drops frames in the headset | Low | Measured in X8 against 31; it only shows through a substitution; Sebas decides |
| CH1 does not finish on Thu | Med | First thing on Fri 20, before AU1/AU4 |
| 15 S6 trials make each visit ≈ 40 s longer | Low | Inside the 1 h 15 blocks of D-F6-209 |

## Open items
- Questions 1–5 of 16 Nov closed (D-F6-206 to D-F6-208, D-F6-213, D-F6-214).
- PM question of 16 Nov night closed by D-F6-220 (one threshold, 15; S6 chooses the reference, it does not fail A-7).
- Week plan and automation approved (D-F6-221).
- Rest of the week (X8, BR2 Stop, BR3–BR7, CH1, Fri 20) as updated on Tue 17 at 16:00: **waiting for Sebas's OK**.

## Carried over from last week
- Audit (D-F6-186, after the dry run): Unity dead code (5 Phase-1 stubs and `XRTrackingProbe`, 253 lines, with their `.meta`; unused events); own `ADAPTATION_SKIPPED` reason for a refused ESL change. Not before the pilot unless block R is done.
- Later, unchanged: B4c SDF morph (D-F6-115); two Playwright tests failing on the 26 Oct data; set A M images in the headset; trial-level theta from the XDF (F4 §5); components rule of §16.3 in `check_lures` and classic pairs for the reserve (Content).

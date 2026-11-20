# Todo: week of 16 – 20 Nov 2026 (dry run → unfreeze → pilot ready)

Plan in `tasks/plan.md`. Aligned up to **D-F6-281** (Fri 20 19:10): G approved, option (3) confirmed for the pilot; official = what the engine saw live; T05's criterion fixed; reference-at-threshold flag after S if time; causal filter after the pilot. Before: **D-F6-280** (Fri 20): I1 approved; G counts the threshold epochs; the monitor's live indices validated, built after S behind a switch that is off. Before: **D-F6-279** (Fri 20 17:30): ICA plan approved with the channel out and the LSL simulation (D-F6-276); live indices with (3) only with the validated design (D-F6-277); foam on Fp1 (D-F6-278, PM); AURA's streams listed (D-F6-279 (1)). Before: **D-F6-275** (Fri 20): the pilot starts with option (3) live and an automatic fallback to (2); tonight I1 → I2 → G off-session; Tue 24 T05 is the final gate. Before: **D-F6-274** (Fri 20 17:50): T05 moves to Tue 24; the rest of Fri 20 is the monitor; clock fixed now (C1, `4245152`); live indices all session wait for the EEG chat's proposal and the validated design; Tue 24 morning live check with (2), M1b and the new indices. Before: D-F6-233 (Tue 17 17:05). **Approved (D-F6-221).** **Approved by Sebas (16 Nov). No code today; `/build` starts Tue 17 after V4 and U0 (D-F6-198, D-F6-204).**
Each code task: tests, commit (message shown first), `graphify update .`, Stop.

---

## Mon 16 · dry run = visit 1 · no code

### [x] R3 · PC ready (14:30–14:50) · redone 18:03 for the retry
- [ ] Kit list «R3 · PC ready» in `Borrador_Plan_Fase6_9_13nov.md`: synthetic off (`LaptopSebas1803 []`), `/health`, port 5432, portal in Edge, Unity freshly opened, LabRecorder, `git status` clean, materials and batteries.
- [ ] 14:45 Blender closed; 14:50 network off.
- [ ] **Stop:** Sebas sees it ticked.

### [x] V2 · dry run (15:00, offline) · first try aborted and deleted; retry 18:06, `65af2fe4`
- [ ] Same external participant, **code only**; consent v1.1 in two copies; set A, `MULTIMODAL_ADAPTIVE`, T1–T3 lures (declared); kit line by line, D-F6-203 sentence in S1–S2.
- [ ] At the end: Sebas asks them back on **Thu 19**, without mentioning memory questions (D-F6-207).
- [ ] **Done when:** S1–S10, XDF with both streams, `autorun` exit 0; network back on at *both streams recorded*.
- [ ] **Stop:** Sebas writes it offline (Notas sin red, observation sheet, step 12).

### [x] V3 · analysis (when `autorun` ends) · done 16 Nov, `65af2fe4`
- [ ] Notes, step 12, `autorun` log, Unity console read.
- [ ] Four SQL (kit §8); A-7 live with the XDF figure beside it and the grid-phase cause (D-F6-200 (2)); replay matches; 3rd A-23 measurement (one-frame `SYNC_TAP` delay declared); every `EEG_LED`.
- [ ] A-24 data noted (S6 length, reference epochs, source), not decided.
- [ ] Dry-run session id and participant code noted for BR7. Participant data kept (D-F6-207).
- [ ] XDF + export to the EEG chat.
- [ ] Each finding: what, where, blocks the pilot yes/no. Nothing fixed.
- [ ] **Stop.**

## Tue 17 · close, unfreeze, EEG fixes, block R

### [x] V4 · close of the dry run · Sebas's OK 17 Nov
- [ ] F4 S3 criterion met or not, with evidence; findings with owner; draft with Dudas or "Sin dudas · 17 nov".
- [ ] **Stop:** Sebas's OK.

### [x] U0 · lift the freeze (D-F6-204) · docs only · lifted 12:32, no code diff since the tag
- [ ] `git diff eeg-rules-freeze-2026-11-12 -- backend unity-client` shows no code change; "freeze lifted at <time>" in the draft.
- [ ] **Stop.**

### [x] G1 · grid origin live = offline (D-F6-200 (1)) · no rule values change · 427 tests; `65af2fe4` 410/410 identical
- [ ] Migration 0018: `eeg_sessions.grid_origin_lsl` (null allowed), up and down.
- [ ] `live.py` writes `t0` once; `epochs.fill_from_xdf` and `replay.xdf_source` pass it as `t0` when not null.
- [ ] Tests: offline epochs = live epochs (index and start) when the XDF starts before `t0`; null origin = today's output; `rules-v2` replay byte-identical.
- [ ] Restart between sessions, `/health`; `fill_from_xdf` on the dry-run session unchanged (null origin).
- [ ] **Stop.**

### [x] G2 · two `AURA` in the XDF (D-F6-206) · 432 tests; `a8e825e0`: two local → not filled
- [ ] `lsl_reader.load_xdf`: repeated name → keep the stream whose hostname is this PC; two from this PC → raise with its own message (never choose by sample count).
- [ ] Callers log that raise as "not filled, live epochs kept"; live epochs untouched.
- [ ] Tests: local + foreign → local; two local → no fill; one → today's behaviour.
- [ ] `a8e825e0` run through the new pick; result noted.
- [ ] **Stop.**

### [x] S1 · sync for the pilot (D-F6-217) · robust spread over every clear tap (board's 17.8 ms); harness 114/114; Unity seen at BR2's Stop
- [ ] `sync.py`: robust spread (MAD × 1.4826 of the clear S3 lags); no S9 taps → drift empty with reason "no S9 taps (D-F6-217)".
- [ ] `verify_eeg.sql` block 2 reads the robust spread.
- [ ] Unity: no S9 sync test (`SessionFlowRunner.cs:910`); kit and Part B without S9 taps.
- [ ] Tests; `65af2fe4` recomputed ≈ 17.8 ms. **Stop** (Unity seen at BR2's Editor Stop).

### [x] S6 · S6 of 15 trials, one threshold of 15 (D-F6-218, D-F6-220) · configuration, no Unity code · harness 114/114; no A-7 change on the three sessions
- [ ] `s6Trials: 15` in `JapaneseLearningStudio.unity` (full cross 5 × 3); `reference.py` `MIN_EPOCHS` 6 → 15.
- [ ] Tests: reference with 14 / 15 non-POOR; harness S6 plan of 15.
- [ ] `verify_eeg.sql` block 4: threshold 15 and the reference used (S6 / S4 fallback, epochs), never `SHORT`. Block 7: A-7 = S4 alpha AND P7 ≥ 60 %; no S6 condition; reference shown as information (D-F6-220).
- [ ] Run on `65af2fe4`, `742ec49a`, `07343b5d`; changes against the old rule noted. **Stop.**

### [x] BR0 · block R design, read-only · approved (D-F6-223)
- [ ] D-F6-125, D-F6-131/181, D-F6-187/190, D-F6-207/208, consent Parts B/C read.
- [ ] Inputs checked in the mirror: `Contenido_UI_Bloque_R.md`, 5 new kanji per set (§16), V1.12 (validated or not); real vs placeholder listed.
- [ ] End of free recall (D-F6-212): researcher key **`R`** in `SessionFlowRunner` (as D-F6-158), only in part 1, logs `BLOCK_R_RECALL_ENDED`; no clock anywhere.
- [ ] One page in the draft: states, events, tables. **Stop:** Sebas approves the mechanism.

### [x] BR1 · block R data (migration 0019) · 439 tests; trials SR-001..
- [ ] Evaluated session stored (D-F6-190 (2)); visit 4 with visit 3's set (D-F6-190 (1)); answers and `BLOCK_R_RECALL_ENDED` as events, outside `decide()` and the window code.
- [ ] Validation: same participant, earlier session. Tests. **Stop.**

### [x] BR2 · block R in VR (between S2 and S3) · harness 117/117; Editor Stop with Sebas pending
- [ ] Part 1: instructions + waiting screen, **no timer**, ended by `R` (D-F6-212). Part 2: yes/no with 10 kanji (5 seen, 5 new from §16). Part 3: 15 MC trials T1–T3 with lures; no feedback, no hints; evaluated session's set. Texts from `Contenido_UI_Bloque_R.md`; placeholders only for what is missing.
- [ ] EditMode test: `R` acts only in part 1.
- [ ] Harness test; seen in the Editor with Sebas; commit body "block R, exception D-F6-125". **Stop.**

### Tue 17 timetable: 15:15 BR2 Stop ✔ · 15:30 X8 ✔ · 16:15 code closed ✔ (16:33) · 17:00 T1 cancelled → Wed 18 11:00 (D-F6-232) · afternoon BR3, BR4 if time

### [x] BR2 Editor Stop · with Sebas, 15:15 · both passes OK (`7a74e704`, `42c7f2ff`); SIM_BR2 deleted with Sebas's OK
- [ ] Test participant; visit 2 (evaluated session deduced or by hand): S1 → SR (R0, R1 + `R`, yes/no 10, 15 `SR-*`, R9) → S3; `R` outside R1 ignored.
- [ ] `shortVisit`: S1 → SR → S9 with R9'; session `COMPLETED`.
- [ ] Read-only SQL: 1 `BLOCK_R_RECALL_ENDED`, 10 yes/no, 15 `SR-*` trials, nothing in `adaptation_decisions`. S1 (no S9 taps) and S6 (15 trials) seen too.
- [ ] Test participant deleted with Sebas's OK. **Stop:** Sebas's OK; changes go to BR4.

### [x] X8 · content 31–35, the five (D-F6-222, D-F6-202) · `f4ca615` · harness 117/117 → 118/118 · fps of 32 and the headset look after T2
- [ ] Sebas's OK recorded: the 20 hints approved, Registro of `Tabla_Autoria_Kanji_Fase2.md`, 17 Nov 14:40.
- [ ] Only `R_NN_CODE_{P,F1,F2,M}.png`; ChatGPT-named PNGs in `pistas/` (e.g. 32's "Taburete…") and `_originales/` not copied.
- [ ] `Reserve4` (KIN/31_KANE, CHA/32_CHA, UMA/33_UMA, SAKANA/34_SAKANA, TORI/35_TORI) + menu "reserva 31-35"; 31–32 facing, 33–35 side-on as in the FBX; no root turn on any.
- [ ] Harness: `X18r4` with the five FICHA envelopes; X20 35/35 AUTHORED; X18b/X20 PLACEHOLDER example on an in-memory item. **All PASS, 117/117 → 118/118.**
- [ ] Commit with the five and the count. **16:15 not done → `git stash -u -m "X8 wip"`, resume after T2.**
- [ ] After T2: 32 茶 fps in the headset against 31 (`FrameRateLog`, 60 s each, Play only); the five seen with Sebas.

### [x] C0 · code closed, 16:15 · done 16:33 (backend restarted, `/health`, 0019; Unity reopened by Sebas)
- [ ] `git status` clean; backend restarted, `/health`; `alembic current` 0019; Unity closed and reopened. Nothing changes until T2 ends.

### [x] C0b · code closed, Wed 18 10:15 · done 12:16 (`707ec34`, backend restarted, 0019), T01 moved to 12:15 (D-F6-238)
- [ ] Commits done, `git status` clean; backend restarted, `/health`; `alembic current` at head; Unity closed and reopened.

### [x] T1 · test with the cap, Wed 18 (13:02–13:15, D-F6-238) · `0077f47d` · T01, MULTIMODAL_ADAPTIVE, set A, visit 1 (D-F6-228, D-F6-232)
- [ ] Wed 10:30 R3; 10:50 network off; consent and pre-test in the portal; kit line by line; 5 taps in S3, none in S9.
- [ ] At S9, before LabRecorder's Stop: live `eeg_epochs` to `Claude outputs/eeg_export_17nov/live_epochs.csv` (read-only).
- [ ] Consent v1.3 on its own sheet; move head and cough before S3 (D-F6-216); red channel fixed before S4 (D-F6-213).
- [ ] **Done when:** S1 → S9, `autorun` exit 0, both streams. **Stop:** Sebas writes it offline.

### [x] T2 · Wed 18 afternoon · done 13:40; live_epochs.csv not exported before Stop (G1 live compare lost); 243/292 POOR, Fp1 suspect; see 18 Nov draft
- [ ] `autorun` log; the four SQL; `replay --xdf` on this PC matches the decisions.
- [ ] G1: `grid_origin_lsl` set; live CSV = `fill_from_xdf` rows (`epoch_index`, `lsl_start`, `chunk_clean`).
- [ ] S1: robust spread ≤ 50 ms, 0 S9 taps, drift empty "no S9 taps (D-F6-217)".
- [ ] S6: 15 S6 trials; block 4 reference chosen; block 7 A-7.
- [ ] `eeg_export_17nov/` as on 16 Nov (+ `live_epochs.csv`), no XDF.
- [ ] T01 kept as a test (code `T##`), out of the pilot analysis; deleted only if T01 asks (D-F6-230 (2)). **Stop:** Sebas.

## Tue 17 afternoon · BR3, BR4 if time (D-F6-232) · BR5 drafted

### [x] BR3 · free recall in the portal, V1.12 (D-F6-226) · `2752994` backend, `31e9585` dashboard · Stop: Sebas against the artboard
- [ ] Read the `research-dashboard-conventions` skill and V1.12 (`design-handoff/design-system.md`, `design-handoff/block-r/`).
- [ ] Backend `POST`/`GET /sessions/{id}/block-r/recall` (event `BLOCK_R_FREE_RECALL`; last save wins; never saved = null, saved with no marks = nothing recalled). `/research` stays read-only.
- [ ] V1.12 screen: the evaluated session's five kanji, Meaning/Reading toggles, order on first mark, "What they said", "Anything else", four states; *What counts* of D-F6-225 word for word; no clock (D-F6-212); never moves the VR.
- [ ] Tests: backend (save, replace, nothing ≠ never, 409 without block R), Vitest, Playwright smoke; 5-tell audit. **Stop:** Sebas against the artboard.

### [x] BR4 · short visit end to end (path built in BR2) · Tue 17 with Sebas (`840361fa`); order fix in V1.12; SIM_BR4 deleted with Sebas's OK
- [ ] What the BR2 Stop found; short session closes `COMPLETED`; `learner_profile` ignores `SR-*` (test).
- [ ] Editor, test participant: portal → visit 2 → Play → block R with the recall marked in V1.12 → S9; BR7's SQL on it; participant deleted with Sebas's OK. **Stop.**

### [ ] BR5 · Thu kit (docs) · drafted Tue 17 15:35 in `Borrador_Plan_Fase6_9_17nov.md`; waits for Sebas to read it (and BR3/BR4)
- [ ] S1 → block R → close, no S2 (D-F6-229); PC list, network off (D-F6-193), visit 2 creation (P01, evaluated `65af2fe4`, `shortVisit`), S1 + D-F6-203 sentence, block R steps (V1.12 with D-F6-225; "Anything else you remember?" once; `R` when they are done; no clock, D-F6-212), **debriefing at the end** (Part B step 3, D-F6-192), close, SQL after.
- [ ] **Stop:** Sebas reads it.

## Wed 18 · 10:15 C0b · 10:30 R3 · 10:50 network off · 11:00 T1 · afternoon T2, BR4 if missing, AU1
- [x] AI workshop clash: T01 moved to 12:15 (D-F6-238) and ran.

## Fri 20 · before T04: logo, Player Settings, monitor access (D-F6-268 to D-F6-272) · **waits for Sebas's OK** · gate 16:15 per part
- [x] `64da886` · Copy `design-handoff/design-system.md` (77 156 bytes) over the skill's `references/design-system.md`.
- [x] **A** · `dfbea59` 15:19 · favicon (light/dark SVG + apple-touch), rail header icon above the name; no participant screen. Vitest, build, harness. **Commit.**
- [x] **B** · `f752579` 15:29 · Play S1 > S2 > S3 (`f5123492`), 0 errors · icon only in Player Settings (`Assets/Branding/andon_icon_light_1024.png`); `productName` unchanged (`persistentDataPath`, `SessionCommunicationClient.cs:324`). Harness, **Play S0–S2** (Sebas presses Start), Unity reopened. **Commit.**
- [x] **C** · `5acb6bc` 15:24 · pytest 528, Vitest 160 · `live/current` by latest event + `external_code`; `/live` + `completed_at`; rail «Live monitor» (dot / ring, §1 tooltips); «Open live monitor» on IN_PROGRESS instead of Export CSV (§2); V1.13 *session ended* (§3.1) and «Sync tap» caption. pytest, Vitest, build, harness. **Commit.**
- [x] Form header PNG: `design-handoff/brand/andon_form_header_1600x400.png` (no commit).
- [x] Nothing reverted: A, B, C passed. 16:15: a part not passed → `git revert`; close: backend and dashboard restarted, Unity reopened, `EEG_LIVE_RULE=current`, `EEG_MONITOR_LIVE=false`.

## Thu 19 · BR7 at 14:00, T03, T04; CH1 → D-F6-246 → M0 → M1 (D-F6-246 to D-F6-248)

### [ ] BR6 · last check of the inputs (morning)
- [ ] Nothing changed in `docs_proyecto/` since Tue (else the export again); harness all PASS; inputs marked real. **Stop.**

### [ ] BR7 · visit 2 test, **14:00** (D-F6-207, D-F6-248)
- [ ] P01, code only; short visit: S1 → block R on set A → R9' → debriefing → close, no S2 (D-F6-229).
- [ ] **Done when:** visit 2 points at `65af2fe4`; 1 recall end, 10 yes/no, 15 `SR-*`, recall saved in V1.12; nothing in `adaptation_decisions`; findings recorded.
- [ ] Cannot come → Fri 20 morning; last resort Mon 23, interval declared. **Stop.**

### Thu 19 day plan (D-F6-246 to D-F6-255) · **waits for Sebas's OK** · slots A 12:30–13:40, B 15:45–16:30 (`live.py` cut 16:15), C after 18:40 if Sebas says so
- [x] **H1** · `66a93c2` · `s3watch.py`: in S3, `HEAD_AWAY` open > 10 s → once `HEAD_AWAY open since <state> — re-seat the headset before S4`. Tests (11 s / 9 s / returned / opened in S2 / after S4); pytest, harness PASS, commit. **By 13:40, else T03 on protocol only.** *Slot A first.*
- [x] **CH1a** · `3a591a3` · `epochs.persistently_bad()` pure: 30 s bins from `grid_origin_lsl`, ±1 s around `SYNC_TAP` out (one shared guard constant), > 20 % in 2 bins, Fp1 never, 2nd channel → too many. Tests (one bin / two bins / Cz taps / origin / two channels / Fp1). Inert commit. *Slot A.*
- [x] **CH1b1** · `9ef14d8` · `make_epochs(bad=)`: channel out of amplitude/flat/indices from its time, Fz → theta None, `excluded_channels`; two out → window `BAD_CHANNELS`. Inert (bad=None everywhere). pytest 483, harness 119/119.
- [x] **CH1b2** · `fb3fad7` · migration 0020 applied (0019 → 0020), `cut_session`, `bad_summary`/`save_bad`, storage and read of `excluded_channels`, block `bad_channel` only when out. pytest 488. Was: slot B: callers apply max 1 + reference re-cut if after S6; offline: `make_epochs(bad=)`, EI without it, Fz → theta None, 2 → not counted (`BAD_CHANNELS`), reference re-cut if after S6, migration 0020, `bad_channel` in the block, `fill_from_xdf` + replay, `EPOCHS_VERSION`. `rules-v2` byte-identical; pytest all green. *Slot A/B.*
- [x] **CH1 gate (now for T03, D-F6-256), 13:25** · container replay, before (`66a93c2`) vs now: T01 and T02 byte-identical epochs and decisions, no channel out; dry run excludes F3 from 336 s (S5), EEG still 0/20 windows counted. **CH1 enters T03.** Was: gate for T04, 16:30 · pytest + harness PASS; `replay --xdf` on T02 and T03 = same epochs and decisions as before (no channel out); dry-run XDF excludes F3. Else T04 without CH1, CH1 to slot C. CH1 before M1 in slot B.
- [x] **CH1c** · `74ea726` · Buffer per closed bin, `Buffer.reference`, `live.run` stores the channel and rewrites the reference, replay through the Buffer. pytest 491, harness 119/119. Was: `live.Buffer` per closed bin; live = offline test; replay T02 = fill. Enters T04 only if CH1a–c whole + harness PASS at 16:30, else Fri 20 first. *Slot B.*
- [ ] **13:40 / 16:30 code closed:** commit, `git status` clean, backend restarted, Unity reopened; say what entered. **Stop.**
- [x] **V2 of `ocul.py`** (D-F6-255 (1)) on T01 and T02, 13:05 · `eeg_export_19nov/` · T01 (2) S6 1 → 0, rest equal; T02 unchanged.
- [x] **`ocul.py` v2 on T03** · two sessions: `6bcae154` → `eeg_export_19nov_T03/`, `2c453b02` → `eeg_export_19nov_T03b/` (READMEs with the preliminary diagnosis). False start `40583d6f` (IN_PROGRESS, 97 KB XDF) waits for Sebas's OK to delete.
- [ ] **T04 → Fri 20** (Sebas, 17:15); `ocul.py` v2 after it.
- [x] **O2** · `67e6265` · pytest 496, harness 119/119; `current` byte-identical on T01, T02, T03, T03b. OV of (2): S6 and dense within tolerance on all four; A-7 −2 (T03) and −3 (T03b) against `ocul.py`, already present with the current rule (implementation, not option (2)) → EEG chat. Was: `EEG_RULE` / `--rule` (live always `current`); no task-sound trim S6–S8, **stage sound and S5 `AUDIO_ONSET` stay trimmed**; `sounds_per_s` + `dense` (≥ 1.5 × S6) → no UNDERCHALLENGED confirm, no STABLE lead; `current` byte-identical. *Slot C.*
- [x] **(2) live switch** · `a53e0c6` · `EEG_LIVE_RULE` (default current); on/off steps in the 19 Nov draft for Tue 24.
- [x] **A-7 gap, T03b** (D-F6-264 (2)) · the grid alone explains 2 → 7; offset, clipping: none; numbers in the draft.
- [x] **O3** · `11f6cf6` · validated against ocul.py v2 (component and corr on all four; A-7/S6 on T01, T02). Was: `scikit-learn==1.9.1`; `ica.py` as `ocul.py` v2 (k = argmax corr × Fp1 share, `max_iter=1000`, S4 start–S5 end); identified if corr ≥ 0.7 and top weight Fp1, else option (2) with reason + corr in `eeg_sessions`; no blink rule after ICA (D-F6-252, D-F6-253, D-F6-255 (3)). *Slot C, after OV of (2).*
- [ ] **OV** · replay each rule on T01, T02, T03, T04 vs `ocul.py` **v2**; pass = same component, corr ±0.02, A-7 ±1 window, S6 ±1 epoch; on a threshold the backend's figure counts (D-F6-255 (2)); (A-7, S6 non-POOR, ICA corr); differences in the draft; aggregates only; D-F6-250 column (≥ 50 % of S6–S8 rule-independent → not evaluable: T02 out, T01 in). **Stop:** table for D-F6-242.
- [ ] **CH1 proof** on the dry run (P7, A-7 with F3 out vs 0/18), read-only.
- [x] **D-F6-258 (1)** · 15:03 · BR7's `eeg_sessions` row deleted (1 row; session `338c6948` COMPLETED, 80 events, 15 trials kept).
- [x] **E0** · `4ab4e6c` · 3 tests; pytest 505. Was: `eeg_sessions` row only if the session reaches S3 (D-F6-258 (2)), with its test · slot C before M0 · **how waits for PM (question 6)**: recommended, delete the row at COMPLETED/ABORTED without S3 (recording untouched).
- [x] **M0** · `befd53d`, `f2dc879` · nginx on 127.0.0.1:5300; Playwright 51/53 (data). Was: as the M0 section below (port 5300). Never 16:30–18:40.
- [x] **D-F6-260 (2)** · 17:27 · false start `40583d6f` deleted (session, 3 events, `eeg_sessions` row in cascade; XDF folder `sub-T03/ses-40583d6f/`). T03 keeps `6bcae154` and `2c453b02`.
- [x] **M1-plan** · written in `tasks/plan.md` (M1a endpoint → M1c page → M1b per-channel figures, gate D-F6-247 (5)). **Stop: Sebas's OK before M1 code.**
- [x] **M1a** · `0ba74b4` · endpoint `/research/sessions/{id}/live` + `/research/live/current`; checked on T03; pytest 508.
- [x] **`ocul.py` v3 (D-F6-266)** · 18:25, in `Claude outputs/ocul_v3/`; T01/T03/T03b outputs in their folders; T03b and T01 match the backend, T03 (1) 5 vs 2 (likely the 84 ms S3 offset, to the EEG chat). From T04: v3. Was: when the EEG chat leaves `ocul_19nov_v3.zip`: read its diff, run on T01, T03 and T03b with each `grid_origin_lsl` (from `eeg_sessions`), before T04 and outside the sessions; outputs in each export folder. From T04, v3. Not in Downloads at 18:22.
- [x] **M1c** · `0a5e6ed` · Was: (page `/monitor`) **→ Fri 20 morning**, outside the cap sessions; System's LabRecorder/autorun lines `—` until PM answers question 8.
- [ ] **autorun / LabRecorder status in the monitor** (D-F6-265 (1), question 8 yes) · not done: its gate needs a full synthetic S1–S9 session operated in the Editor (with Sebas); plan in the 19 Nov draft. Tomorrow: today's autorun.
- [x] **M1b** · `3187555` · gate met (T02/T03 byte-identical) · EEG_MONITOR_LIVE off · Was: (per-channel figures, migration 0021, gate D-F6-247 (5)) **→ Fri 20 morning**.
- [ ] Was: `/plan` of M1 from the validated EEG formulas, no code. **Stop.** Then page + endpoint in the background; `live.py` not in T04.
- [ ] Draft 19 Nov: H1 in T03 or not; kit line (re-seat, repeat taps); Dudas 1–4 (evening slot, scikit-learn, blinks after ICA, component not found), recording path of T03/T04, CH1 status.

## Session automation (D-F6-219, D-F6-221) · never during a session · pilot starts with **manual recording**

**Part 1 · Fri 20 morning (leftovers → Tue 24 morning):** AU1 → AU4 → kit lines → AU0 only if time is left.
**Part 2 · a pilot day without a participant, with Sebas:** AU2, AU3, AU5, AU6.

### [ ] AU0 · spike `LabRecorderCLI` + synthetic AURA (≈ 1 h) · Fri 20
- [ ] Two queries by name and host; network on (`MSI`'s `AURA` visible); XDF has only the two local streams; query syntax written down. No host filter works → stop, manual kit stays. **Stop.**

### [x] AU1 · `python -m app.eeg.preflight` · `c9c38df`, 450 tests; real run 6 FAIL 3 WARN, all true; kit line with AU5
- [ ] Services, port, portal, `git status`, processes (`tasklist`), one local `AURA`, synthetic off, network reported (WARN), `LabRecorderCLI`, disk. Same verdicts as manual R3. Tests.

### [ ] AU2 · `autorun` records with `LabRecorderCLI` (≈ 3 h) · part 2
- [ ] Exactly one local `AURA` and `UnityMarkers` (retry 10 s); two `AURA` → no recording, manual path; network up → WARN.
- [ ] Launch with the BIDS path; watch; Enter at `session COMPLETED`; Enter in `finally`; file closed. Tests.

### [ ] AU3 · S3 warnings (≈ 2–3 h) · part 2
- [ ] Per tap clear / not clear; < 3 clear → "repeat taps before S4"; channel > 20 % over 100 µV in the last 30 s → "fix before S4". Nothing printed from S4 but errors. Checked on the dry-run XDF fed as live.

### [ ] AU4 · end of session (≈ 2 h) · Fri 20; tested on `65af2fe4` and on T01's session (SQL + summary read-only; processing re-run only with Sebas's OK)
- [ ] Processing, the four SQL to `backend/logs/<session>-*.txt`, summary printed and saved; exit 0 only if all ran. Tests.

### [ ] AU5 · kit: Fri 20, AU1 and AU4 lines in the manual kit; part 2, the automated path

### [ ] AU6 · rehearsal with Sebas, no participant (part 2; not Mon 23)
- [ ] Synthetic AURA + headset, S1–S9, only Play, network and S3 keys by hand; session deleted after with Sebas's OK.
- [ ] Pass → automated recording from the next session, each session labelled by recording path; fail or no day → whole pilot manual. **Stop.**

## Fri 20 night · ICA live behind `EEG_LIVE_RULE=ica` (D-F6-275, D-F6-276) · approved
- [x] D-F6-279 (1): AURA's LSL streams listed; no quality nor impedance.
- [x] **I1** · pytest 531 → 540 (9 in `test_eeg_live_ica.py`); model and reference chunk-independent; epochs ≥ 97 % equal across chunkings, as with any rule (finding below) · `live.Buffer` rule `ica`: before S6 `nosound`; fit at S6 + `EDGE_S` on S4→S6; S6+ epochs held, then corrected (no blink rule) or `nosound` with the reason; reference recomputed with the final rule; stored model without refit; channel out before S6 → fit without it (Fp1 → `nosound`), after S6 → `nosound` to the end, no refit; tests. **Stop.**
- [x] **I2** · pytest 540 → 544; 0022 down/up; `replay --rule current|nosound` on T04 byte-identical · `eeg_live_rule` + `ica`; migration 0022 `eeg_sessions.ica`; `live.run` saves and prints it; `websocket` sounds for `ica`; `fill_from_xdf` and `replay --rule ica` through `Buffer`; tests. **Stop.**
- [x] **G** · approved (D-F6-281 (1)) · run 20 Nov: all pass but T03's decisions (6 EEG effects differ, no action; a S6 epoch at the reference's 15-epoch minimum; same with `nosound`, pre-existing); waits for Sebas · scratchpad script, T01 T03 T03b T04: simulated live = `replay --rule ica`; identified T01 T04 (corr ±0.02 of v3); fallback T03 T03b; A-7 ±1 (18, 18, 5, 6); fit < 2 s; pytest; harness 119/119. Not passed → Tue 24 with (2). `.env` unchanged tonight. **Stop.**
- [x] **S** · passed 20 Nov: model, reference, S3 offset equal on all four; epochs differing ≤ 1.05 %; fit ≤ 0.37 s; test sessions deleted (1 participant, 4 sessions, 1164 epochs) · XDFs over two LSL outlets at 10× into `live.run` (rule `ica` in the process), test sessions in the database, equal to G; deleted at the end. Needs AURA's software and Unity closed. **Stop.**
- [x] **V** · pytest 544 → 546; 0023 down/up; T04 5/246 (2.03 %) · `verify_eeg.sql`: A-7 live and XDF + epochs differing (`autorun` counts `live_epochs.csv` vs the XDF rows; migration 0023) (D-F6-281 (2)). **Stop.**
- [x] **RT** · pytest 546 → 553; `s6_non_poor` + `at_threshold` in the stored reference; verify_eeg block 4 · only if time: «reference at threshold» in `eeg_sessions` (S6 within ±1 of 15), read-only (D-F6-281 (5)). **Stop.**
- [ ] **MI** · monitor live indices (D-F6-277, D-F6-280): after S, switch off, design-system.md *Validated* + `Contenido_UI_Monitor_Indices.md`; own plan first.
- [ ] Tue 24 kit: `EEG_LIVE_RULE=ica` + restart before T05; T05's criterion of D-F6-281 (3) (in the draft of 20 Nov, «Kit del mar 24»).

## Fri 20 evening · monitor clock (D-F6-274 (1)) · OK from Sebas
- [x] **C1** · `4245152`, pytest 528 → 531; T04's S4 moves 10 s per 10 s · `_LIVE_TOP.elapsed_ms` = anchor (max of `session_elapsed_ms − server_received_at`) + `now()` while `IN_PROGRESS`; 4 tests; T04's S4 check read-only; pytest, commit, graphify, backend restart. **Stop.**
- [x] T04 processing: `ocul.py` v3 + `replay` (1)/(2)/(3) in `eeg_export_20nov_T04/`.
- [ ] Live indices all session (D-F6-274 (2)–(5)): wait for the EEG chat → design → Sebas.

## Fri 20 · AU4, AU0, M0, the M1 plan, then go/no-go · no presentation, no video (D-F6-227)
- [ ] AU4 (dry run and T01) → AU0.
- [ ] M0 moved to Wed 18 (D-F6-235): see below.

## Wed 18 evening · AU0 → AU2 → AU4 → AU3 before T02 (D-F6-244) · plan written, **waits for Sebas's OK** · cut-off 45 min before T02
- [x] AU0 · passed 17:55 · CLI with a `hostname` filter: synthetic AURA + Unity Play (no cap); exactly 2 streams; `hostname='MSI'` matches nothing. Fails → AU2 out.
- [x] AU2 · `2585c98` · `recorder.py` + `autorun`: one local AURA → CLI on the session's path; MANUAL line otherwise; Enter in `finally`. Tests + a Play test without cap.
- [x] AU4 · `b121e85` · `live_epochs.csv` at COMPLETED, the 4 SQL to logs, `summary.py`. Checked on T01, read-only.
- [x] AU3 · `e118ccd` · S3 lines in `live.py`: taps k/5, bad channel, Fp1 (D-F6-240 (2)). Checked on T01's XDF fed as live.
- [x] pytest 467, harness 119/119, one commit each, graphify by hook, code closed at `10f2fc0`, `preflight`, T02 kit. Draft: how each session was recorded.
- [x] **T02 `fffc578f` ran automated (AU6):** recording by `LabRecorderCLI`, stopped at COMPLETED, 4 SQL and summary, exit 0; G1 live = XDF on 268 epochs. EEG all POOR from an open HEAD_AWAY (visor moved over Fp1, 649 s); what-if without it: A-7 14/18. Draft and `eeg_export_18nov_T02/`.
- [x] AU3 fix `b2860e9`: the S3 taps on Cz no longer flag Cz (±1 s around each `SYNC_TAP`); pytest 468.

## Wed 18 evening · D-F6-239 and D-F6-240 · plan written, **waits for Sebas's OK** · M0 after if time, else Fri 20
- [x] U1 · `7a5c145` · `_assemblyComplete` guard in `PaintSlot` (set in `ShowAssemblyComplete`, cleared in `HideAssemblySlots` and `ShowAssembly`). Harness all PASS.
- [x] U2a · Content validated 17:10 · group proposal for 日 田 子 目 学 物 茶 馬 魚 鳥 to Content (plan table). **Stop until Content answers.**
- [x] U2b · `d96a61b`, harness 119/119 · `G`, `IDS`, `OVR` in `tools/assembly_segments.py`; preview clean; old 26 byte-identical; new harness check 35/35 authored.
- [x] Editor Stop with Sebas (OK): 学 and 月 in S5, green held under the ray. Two commits ("exception D-F6-239"), `graphify update .`.
- [x] E1 · on T01 and T02, plus T02 without HEAD_AWAY (scratchpad venv with scikit-learn) · read `ocul.py` whole → run on T01's XDF in place (scratchpad venv if it needs `mne`) → only aggregates to the draft.

## M0 (D-F6-235) · **moved to Fri 20** (D-F6-239; board 18 Nov 17:20) · plan written, waits for Sebas's OK (port: 5300 recommended)
- [ ] M0.1 · `npm run build` (dist is from 22 Oct) → `dashboard/nginx.conf` + `dashboard` service (`nginx:alpine`, `127.0.0.1:5300:80`, `/api/` → `backend:8000/`, SPA fallback). `/pretest` 200, deep link 200, `/api/health` ok.
- [ ] M0.2 · `docker compose down` (never `-v`) → `up -d`: all ports on 127.0.0.1; Playwright against nginx; `preflight` portal OK. **Stop:** Sebas opens the portal in Edge.
- [ ] M0.3 · compose comment, `stack-and-structure.md` line, kit line in the draft for AU5.
- [ ] `/plan` of M1, no code (V1.13 validated, D-F6-233); M1 itself in the pilot, a day without a participant. **Stop.**
- [ ] Go/no-go input: what is live, BR7 and T01 results, open findings; `tasks/` and draft up to date.

---

## Later (not before the pilot unless block R is done)
- [ ] Audit D-F6-186: Unity dead code (253 lines + `.meta`, unused events); own `ADAPTATION_SKIPPED` reason.
- [ ] B4c SDF morph (D-F6-115).
- [ ] Two Playwright tests failing on the 26 Oct data.
- [ ] Set A M images in the headset.
- [ ] Trial-level theta from the XDF (F4 §5).
- [ ] `check_lures` components rule (§16.3); classic pairs for the reserve (Content).

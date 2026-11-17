# Todo: week of 16 – 20 Nov 2026 (dry run → unfreeze → pilot ready)

Plan in `tasks/plan.md`. Aligned up to **D-F6-233** (Tue 17 17:05): T01 moves to Wed 18 11:00–12:00; BR3 (and BR4) this afternoon; AU1 Wed; AU4, AU0, M0 and the M1 plan Fri (D-F6-232). **Approved (D-F6-221).** **Approved by Sebas (16 Nov). No code today; `/build` starts Tue 17 after V4 and U0 (D-F6-198, D-F6-204).**
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

### [ ] C0b · code closed, Wed 18 10:15
- [ ] Commits done, `git status` clean; backend restarted, `/health`; `alembic current` at head; Unity closed and reopened.

### [ ] T1 · test with the cap, Wed 18 11:00–12:00 · T01, MULTIMODAL_ADAPTIVE, set A, visit 1 (D-F6-228, D-F6-232)
- [ ] Wed 10:30 R3; 10:50 network off; consent and pre-test in the portal; kit line by line; 5 taps in S3, none in S9.
- [ ] At S9, before LabRecorder's Stop: live `eeg_epochs` to `Claude outputs/eeg_export_17nov/live_epochs.csv` (read-only).
- [ ] Consent v1.3 on its own sheet; move head and cough before S3 (D-F6-216); red channel fixed before S4 (D-F6-213).
- [ ] **Done when:** S1 → S9, `autorun` exit 0, both streams. **Stop:** Sebas writes it offline.

### [ ] T2 · Wed 18 afternoon, after the test · read-only; the recording stays on this PC
- [ ] `autorun` log; the four SQL; `replay --xdf` on this PC matches the decisions.
- [ ] G1: `grid_origin_lsl` set; live CSV = `fill_from_xdf` rows (`epoch_index`, `lsl_start`, `chunk_clean`).
- [ ] S1: robust spread ≤ 50 ms, 0 S9 taps, drift empty "no S9 taps (D-F6-217)".
- [ ] S6: 15 S6 trials; block 4 reference chosen; block 7 A-7.
- [ ] `eeg_export_17nov/` as on 16 Nov (+ `live_epochs.csv`), no XDF.
- [ ] T01 kept as a test (code `T##`), out of the pilot analysis; deleted only if T01 asks (D-F6-230 (2)). **Stop:** Sebas.

## Tue 17 afternoon · BR3, BR4 if time (D-F6-232) · BR5 drafted

### [ ] BR3 · free recall in the portal, V1.12 (D-F6-226)
- [ ] Read the `research-dashboard-conventions` skill and V1.12 (`design-handoff/design-system.md`, `design-handoff/block-r/`).
- [ ] Backend `POST`/`GET /sessions/{id}/block-r/recall` (event `BLOCK_R_FREE_RECALL`; last save wins; never saved = null, saved with no marks = nothing recalled). `/research` stays read-only.
- [ ] V1.12 screen: the evaluated session's five kanji, Meaning/Reading toggles, order on first mark, "What they said", "Anything else", four states; *What counts* of D-F6-225 word for word; no clock (D-F6-212); never moves the VR.
- [ ] Tests: backend (save, replace, nothing ≠ never, 409 without block R), Vitest, Playwright smoke; 5-tell audit. **Stop:** Sebas against the artboard.

### [ ] BR4 · short visit end to end (path built in BR2)
- [ ] What the BR2 Stop found; short session closes `COMPLETED`; `learner_profile` ignores `SR-*` (test).
- [ ] Editor, test participant: portal → visit 2 → Play → block R with the recall marked in V1.12 → S9; BR7's SQL on it; participant deleted with Sebas's OK. **Stop.**

### [ ] BR5 · Thu kit (docs) · drafted Tue 17 15:35 in `Borrador_Plan_Fase6_9_17nov.md`; waits for Sebas to read it (and BR3/BR4)
- [ ] S1 → block R → close, no S2 (D-F6-229); PC list, network off (D-F6-193), visit 2 creation (P01, evaluated `65af2fe4`, `shortVisit`), S1 + D-F6-203 sentence, block R steps (V1.12 with D-F6-225; "Anything else you remember?" once; `R` when they are done; no clock, D-F6-212), **debriefing at the end** (Part B step 3, D-F6-192), close, SQL after.
- [ ] **Stop:** Sebas reads it.

## Wed 18 · 10:15 C0b · 10:30 R3 · 10:50 network off · 11:00 T1 · afternoon T2, BR4 if missing, AU1
- [ ] AI workshop: if its time clashes with 11:00–12:00, Sebas says so and the test moves.

## Thu 19 · visit 2 test at 12:00, then CH1

### [ ] BR6 · last check of the inputs (morning)
- [ ] Nothing changed in `docs_proyecto/` since Tue (else the export again); harness all PASS; inputs marked real. **Stop.**

### [ ] BR7 · visit 2 test, 12:00 (D-F6-207)
- [ ] P01, code only; short visit: S1 → block R on set A → R9' → debriefing → close, no S2 (D-F6-229).
- [ ] **Done when:** visit 2 points at `65af2fe4`; 1 recall end, 10 yes/no, 15 `SR-*`, recall saved in V1.12; nothing in `adaptation_decisions`; findings recorded.
- [ ] Cannot come → Fri 20 morning; last resort Mon 23, interval declared. **Stop.**

### [ ] CH1 · persistently bad channel (D-F6-216, D-F6-224) · after BR7
- [ ] D-F6-224: ±1 s around every `SYNC_TAP` left out of the count; 30 s bins from `grid_origin_lsl` (null origin: the XDF's first stamp, as the grid); tests for both (Cz with taps not excluded; bins at the stored origin).
- [ ] One function: > 20 % of samples > 100 µV in 2 consecutive 30 s bins → channel out to the end; max 1 per session (2 → EEG not counted); Fz → theta `UNAVAILABLE`, EI with 6; Fp1 never; reference recomputed if after S6.
- [ ] Same in `live.Buffer`, `fill_from_xdf` and replay; migration 0020 (`bad_channel`, `bad_channel_from_ms`); `bad_channel` in the decision's `eeg` block.
- [ ] Tests (one bin / two bins / two channels / Fz / Fp1 / live = offline); `rules-v2` byte-identical.
- [ ] Dry-run XDF in the container's `/tmp` (same PC), deleted after: P7 and A-7 with F3 excluded beside 0/18. `fill_from_xdf` on `65af2fe4` only with Sebas's OK.
- [ ] If it runs late, first thing on Fri 20, before AU1/AU4. **Stop.**

## Session automation (D-F6-219, D-F6-221) · never during a session · pilot starts with **manual recording**

**Part 1 · Fri 20 morning (leftovers → Tue 24 morning):** AU1 → AU4 → kit lines → AU0 only if time is left.
**Part 2 · a pilot day without a participant, with Sebas:** AU2, AU3, AU5, AU6.

### [ ] AU0 · spike `LabRecorderCLI` + synthetic AURA (≈ 1 h) · Fri 20
- [ ] Two queries by name and host; network on (`MSI`'s `AURA` visible); XDF has only the two local streams; query syntax written down. No host filter works → stop, manual kit stays. **Stop.**

### [ ] AU1 · `python -m app.eeg.preflight` (≈ 2 h) · Wed 18 afternoon, after T2; manual path (GUI running = OK)
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

## Fri 20 · AU4, AU0, M0, the M1 plan, then go/no-go · no presentation, no video (D-F6-227)
- [ ] AU4 (dry run and T01) → AU0.
- [ ] M0 (afternoon): `dashboard` service in compose, nginx on `127.0.0.1` serving `dashboard/dist`, proxy to the backend; from scratch `docker compose up -d`, nothing on `0.0.0.0`, Playwright smoke. **Stop.**
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

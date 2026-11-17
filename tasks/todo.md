# Todo: week of 16 – 20 Nov 2026 (dry run → unfreeze → pilot ready)

Plan in `tasks/plan.md`. Aligned up to **D-F6-222** (X8 on Tue 17, end of day). **Approved (D-F6-221).** **Approved by Sebas (16 Nov). No code today; `/build` starts Tue 17 after V4 and U0 (D-F6-198, D-F6-204).**
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

### [ ] X8 · content 31–35, end of day, after BR2 (D-F6-222, D-F6-202) · content commit (D-F6-62, D-F6-122)
- [ ] Gate per kanji: FBX in `NN_*/export/` and the 4 `R_NN_*_{P,F1,F2,M}.png` in `NN_*/pistas/` validated by Sebas (Registro or his OK in the draft). Incomplete → X8b Thu 19; none complete → no X8 today.
- [ ] `Reserve4` + menu "reserva 31-35" in `SetAObjectsIntegration.cs` (only complete kanji; root turn per FICHA); run the menu.
- [ ] Harness: `X18r4` (FICHA envelopes, 1 cm), X20 = 30 + n AUTHORED; PLACEHOLDER examples off `KANJI_KIN` if 金 entered. All PASS, count before → after.
- [ ] Commit lists what entered and what moved to Thu 19; `tasks/` and draft. **Stop.**

## Wed 18 · AI workshop · block R continues

### [ ] BR3 · free recall in the portal
- [ ] *What counts* text of D-F6-225 as V1.12 words it (plan, BR3); Meaning and Reading toggles only, doubtful answers in "What they said", no partial mark.
- [ ] V1.12 instead of the placeholder once D-F6-226 is on the board (the mirror stops at D-F6-225).
- [ ] Researcher marks recalled kanji; V1.12 if validated, else placeholder with the same states; no clock; the form does not advance the VR (D-F6-212). Playwright smoke. **Stop.**

### [ ] BR4 · short visit: S1–S2 → block R → close (no cap)
- [ ] Creation with the evaluated session; Unity skips S3–S10 and closes cleanly; same path as visit 4.
- [ ] End to end in the Editor with a test participant, deleted after with Sebas's OK. **Stop.**

### [ ] BR5 · Thu kit (docs)
- [ ] PC list, network off (D-F6-193), Inspector for visit 2 (code, evaluated session = dry run, short visit), S1–S2 + D-F6-203 sentence, block R operator steps ("Anything else you remember?" once; `R` when they say they are done; no clock, D-F6-212), **debriefing at the end** (Part B step 3, D-F6-192: no visit 4 for this participant), close, SQL after.
- [ ] **Stop:** Sebas reads it.

- [ ] End of day: inputs due from UI/UX, Content and web design (D-F6-208).

## Thu 19 · visit 2 test, then X8b

### [ ] BR6 · swap in what arrived (morning)
- [ ] Content and texts into `kanji_content.json`; form if it arrived and fits. Harness re-run; each input marked real or placeholder. **Stop.**

### [ ] BR7 · visit 2 test (D-F6-207)
- [ ] Dry-run participant, code only; S1–S2 → block R on set A → debriefing → close.
- [ ] **Done when:** recall, yes/no and 15 MC stored against the dry-run session; nothing from block R in `adaptation_decisions`; findings recorded.
- [ ] Cannot come → Fri 20 morning; last resort Mon 23, interval declared. **Stop.**

### [ ] X8b · what X8 left out on Tue (D-F6-222) · after BR7 · only if any
- [ ] Same gate and path as X8; harness all PASS (count before → after). **Stop.**

### [ ] CH1 · persistently bad channel (D-F6-216) · after BR7
- [ ] One function: > 20 % of samples > 100 µV in 2 consecutive 30 s bins → channel out to the end; max 1 per session (2 → EEG not counted); Fz → theta `UNAVAILABLE`, EI with 6; Fp1 never; reference recomputed if after S6.
- [ ] Same in `live.Buffer`, `fill_from_xdf` and replay; migration 0020 (`bad_channel`, `bad_channel_from_ms`); `bad_channel` in the decision's `eeg` block.
- [ ] Tests (one bin / two bins / two channels / Fz / Fp1 / live = offline); `rules-v2` byte-identical.
- [ ] Dry-run XDF in the container's `/tmp` (same PC), deleted after: P7 and A-7 with F3 excluded beside 0/18. `fill_from_xdf` on `65af2fe4` only with Sebas's OK.
- [ ] If it runs late, X8b moves to Fri. **Stop.**

## Session automation (D-F6-219, D-F6-221) · never during a session · pilot starts with **manual recording**

**Part 1 · Fri 20 morning (leftovers → Tue 24 morning):** AU1 → AU4 → kit lines → AU0 only if time is left.
**Part 2 · a pilot day without a participant, with Sebas:** AU2, AU3, AU5, AU6.

### [ ] AU0 · spike `LabRecorderCLI` + synthetic AURA (≈ 1 h) · only if time is left on Fri 20
- [ ] Two queries by name and host; network on (`MSI`'s `AURA` visible); XDF has only the two local streams; query syntax written down. No host filter works → stop, manual kit stays. **Stop.**

### [ ] AU1 · `python -m app.eeg.preflight` (≈ 2 h) · Fri 20, first; manual path (GUI running = OK)
- [ ] Services, port, portal, `git status`, processes (`tasklist`), one local `AURA`, synthetic off, network reported (WARN), `LabRecorderCLI`, disk. Same verdicts as manual R3. Tests.

### [ ] AU2 · `autorun` records with `LabRecorderCLI` (≈ 3 h) · part 2
- [ ] Exactly one local `AURA` and `UnityMarkers` (retry 10 s); two `AURA` → no recording, manual path; network up → WARN.
- [ ] Launch with the BIDS path; watch; Enter at `session COMPLETED`; Enter in `finally`; file closed. Tests.

### [ ] AU3 · S3 warnings (≈ 2–3 h) · part 2
- [ ] Per tap clear / not clear; < 3 clear → "repeat taps before S4"; channel > 20 % over 100 µV in the last 30 s → "fix before S4". Nothing printed from S4 but errors. Checked on the dry-run XDF fed as live.

### [ ] AU4 · end of session (≈ 2 h) · Fri 20, after AU1; tested on `65af2fe4` (SQL + summary read-only; processing re-run only with Sebas's OK)
- [ ] Processing, the four SQL to `backend/logs/<session>-*.txt`, summary printed and saved; exit 0 only if all ran. Tests.

### [ ] AU5 · kit: Fri 20, AU1 and AU4 lines in the manual kit; part 2, the automated path

### [ ] AU6 · rehearsal with Sebas, no participant (part 2; not Mon 23)
- [ ] Synthetic AURA + headset, S1–S9, only Play, network and S3 keys by hand; session deleted after with Sebas's OK.
- [ ] Pass → automated recording from the next session, each session labelled by recording path; fail or no day → whole pilot manual. **Stop.**

## Fri 20 · go/no-go input
- [ ] What is live, what is still placeholder, BR7 result, open findings; `tasks/` and draft up to date.

---

## Later (not before the pilot unless block R is done)
- [ ] Audit D-F6-186: Unity dead code (253 lines + `.meta`, unused events); own `ADAPTATION_SKIPPED` reason.
- [ ] B4c SDF morph (D-F6-115).
- [ ] Two Playwright tests failing on the 26 Oct data.
- [ ] Set A M images in the headset.
- [ ] Trial-level theta from the XDF (F4 §5).
- [ ] `check_lures` components rule (§16.3); classic pairs for the reserve (Content).

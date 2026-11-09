# Todo: week of 2 – 6 Nov (F4 S2 · integrate the EEG)

Plan: `tasks/plan.md`. Previous list: `tasks/archive/semana_26oct_todo.md`.
**Aligned up to: D-F6-159** (Fri 6 plan approved) (Fri 6 replanned 6 Nov; Mon–Thu: D-F6-131, approved 2 Nov, D-F6-132) (`Estado_Actual.md`, the board; it wins over this list).

Every Unity commit body says **F4 (D-F6-74)**, **correction** or **content (D-F6-…)**.
Every task ends with a **Stop**: Sebas's OK before the next dependent task.

---

## Mon 2 · markers and recording

### [x] L1 (F4): Unity LSL marker outlet (`97a6259`, `975f4da`; LSL4Unity embedded with one patch, harness X25, 105/105)
- [ ] LSL4Unity + liblsl x64 in the project; Editor and Link build load it.
- [ ] Outlet `UnityMarkers` / `Markers`, 1 string channel (JSON: `event`, `trial_id`, `event_id`, session clock), irregular rate.
- [ ] Mirror every `SessionCommunicationClient.SendSessionEvent` (one call site). Check which of F4 §2.1's list are not session events today (sound onsets, S4 segments) and push only those.
- [ ] `FRAME_HITCH` with `duration_ms` from `FrameRateLog` when a frame > 50 ms (D-F6-129).
- [ ] Test: EditMode/harness case, an in-process inlet resolves the stream and receives a mirrored event and a synthetic 60 ms `FRAME_HITCH`; a 40 ms frame sends nothing. Harness green.

### [x] L2: migration `0010` · `eeg_sessions` (`336c1ee`)
- [ ] Session FK, XDF path, stream info (jsonb), filter params, montage (default CH1 Fp1 … CH8 P4, changes + reason), sync offset/drift, alpha ratio + passed, reason if the EEG does not count.
- [ ] Test: upgrade/downgrade; default montage written.

### [x] L3: `app/eeg/lsl_reader.py` (`b0bb83b`, `d455e33`; Docker spike negative: the live reader runs on the PC)
- [ ] XDF read with corrected clock (`pyxdf`, dejitter); live inlet with `clocksync | dejitter` (P9).
- [ ] Stream info into `eeg_sessions`; deps `pylsl`, `pyxdf`, `numpy`, `scipy` in `requirements.txt`.
- [ ] Spike (30 min): can the container see LSL streams (`KnownPeers`)? If not, host process (question 1).
- [ ] Test: the 29 Oct XDF 1 → 8 ch, 250.0 Hz, 70 254 samples, no gaps.

### [x] L5: unique XDF name (P9) (`771e101` + fix: the backend sends `filename` and `stop` only; LabRecorder's remote `start` ticks every stream on the network, so the operator ticks the two and presses Start)
- [ ] Check LabRecorder's remote-control commands in its docs/source first.
- [ ] Backend sets `sub-<p>_ses-<session>_task-<condition>_run-<n>` and starts/stops recording; run counts up from existing files.
- [ ] Test: fake TCP server receives the expected commands.
- [-] Fallback: manual name field + box in the S3 checklist. Not needed: the remote control works from the container.

### [x] L4 Stop: Editor session → one XDF with `AURA` (synthetic if no cap, question 3) and `UnityMarkers`, plus its `eeg_sessions` row. **Passed, Sebas, 2 Nov 16:48:** `41524441` (`DEV_UNITY`, STATIC, S1–S2): AURA 17 877 samples at 249.9998 Hz, 33 markers, all inside the EEG span; both streams from `LaptopSebas1803`. First try `2b91ff7d` recorded every stream on the network (LabRecorder's remote `start`); fixed in `31e0efb`, XDF deleted by Sebas.

### [x] Close Mon: `tasks/`, `Borrador_Plan_Fase6_9_2nov.md` with "Dudas para PM" (lure trials in the estimator, question 2).

## Tue 3 · epochs and performance

### [x] T1: `preprocess.py`, `epochs.py`, migration `0011` · `eeg_epochs` (`e25bf8b`, done Wed 4; 29 Oct artifact blocks POOR; XDF 3 70 % clean chunks vs 81 % in the summary, the 200 ms blink pad: finding in `Borrador_Plan_Fase6_9_4nov.md`)
- [ ] 1–40 Hz band-pass, 60 Hz notch; params stored per session. P16 relative-power helper (1–40 Hz denominator).
- [ ] Epochs 5 s every 2.5 s; 1 s chunks with clean flags; drops: blink (Fp1 > 75 µV), amplitude > 100 µV, flat, `HEAD_AWAY` open, 1 s after a sound onset, `FRAME_HITCH` > 100 ms (D-F6-129). GOOD/ACCEPTABLE/POOR per reevaluation §5.3.
- [ ] `eeg_epochs`: session, start/end, game state, `trial_id`, ESL level, chunk flags, clean fraction, quality (index columns empty until S3 week).
- [ ] Tests: synthetic blink/flat/hitch chunks dropped; 29 Oct XDF 2 artifact blocks → POOR; XDF 3 S6/S7 counts near the S1 summary (14/14, 17/22) as a sanity check.

### [x] T2 (correction, diagnosis only): Profiler (4 Nov; S2 = dynamic CJK font writes/reimports its asset + glyph rasterizing, 1.7 s; S4 = `PaintEye` on the CPU every frame, 14–89 ms; proposals 1 and 2 in `Borrador_Plan_Fase6_9_4nov.md`)
- [ ] S2 entry hourglass: what stalls the main thread (load, instantiate, shader compile, GC).
- [ ] S4 eye-closing hitches: where they fall (open/closed/switch) and the cause.
- [ ] Proposal per hitch, not applied.

### [ ] Stop Tue: epochs with quality; diagnosis + fix proposal.

## Wed 4 · lures, S3 and S4

### [x] W1: lure fields from `kanji_metrics.py` (D-F6-130, D-F6-131) (`39c1f3c`; §2.4 checks in the default verdict, not a `--verify` flag: the script had none)
- [ ] Per kanji, per type (T1/T2/T3): `lure_strong`, `unrelated`, `provisional`. T1 strong = §15.2; T1 unrelated = outside the pool, minimum similarity, one per kanji. T2/T3 empty.
- [ ] `--verify` rules (§2.4): never two correct (not a reading/meaning of the target nor of any pool kanji), one distinct lure per kanji and type, outside the pool.

### [x] W2: lure trials in Unity + contract (`4ba0d4d`; harness 107/107, X27; no projection column yet: the keys are in `session_events.payload`)
- [ ] `TrialOption` gets its kind; `BuildOptions` builds [CORRECT, LURE_STRONG, IN_SET, UNRELATED] in half of each active type's trials per block (S6, S7, S8), seeded, same in the three conditions. Per-type switch; only T1 on.
- [ ] `option_kind` of the selected option and `lure_selected` in the contract (`EVENT_CONTRACT.md`, backend schema, LSL marker says the trial has a lure).
- [ ] Estimator untouched: a lure trial counts in the window like any other (D-F6-132).
- [ ] Harness: half of T1 per block, never two correct, same trials across conditions, T2/T3 unchanged.

### [x] W3 (F4): S3 step: channels blue (operator confirms) + sync test (5 taps at start, 5 in S9, each a marker). (`e57e395`; checklist in S3 with "EEG ready (researcher)", `SYNC_TAP` markers, `SYNC_TEST_COMPLETED`; harness 106/106)
- [ ] S3 checklist box: LabRecorder is **recording** only `AURA (LaptopSebas1803)` and `UnityMarkers (LaptopSebas1803)` (the operator presses Start by hand; the backend only names the file, 2 Nov).

### [x] W4 (F4): S4 eye markers + `EEG_BASELINE_RESULT` (alpha ratio P3, Pz, P4; passes ≥ 1.2). (`e57e395` markers, `c9d5670` `app/eeg/baseline.py`, live on the PC; 29 Oct XDF 1: 5.18 / 3.46 / 4.29)

### [x] W5 (correction): the approved perf fix; harness green. (`4b2f1ea`, D-F6-139: S0 prewarm of the font, the S2 lectern and the S4 eye frames; S2 first frame 1707 → 390 ms in the Editor; X28, 108/108)
### [x] AUDIO_ONSET (F4, D-F6-138): marker on each S5 reading, dropped by `epochs.py` (`6c9e02c`).
### [x] D-F6-145 (replaces D-F6-142): odd T1 counts round the half by the block seed (`ee79474`; X27, 108/108).
### [x] Content (D-F6-122): set A M images with the new edge colour (`ac26857`).

### [x] Stop Wed: lures S6–S8, S3/S4 markers in the Editor; no hourglass in S2, no hitches in S4. **Passed, Sebas, 4 Nov ~18:30:** `8a9e8deb` (`DEV_UNITY`, STATIC, S1–S9, synthetic AURA): no hourglass in S2, smooth S4 eye, lures fine (S6 2/3, S7 5/9, S8 2/5); sync 5/5 in S3 and S9; alpha 1.0 → not passed (expected, synthetic); 252 epochs. LabRecorder started before Play, so the XDF took the previous session's name (my step order; correct order D-F6-135); copied to the session's path, misnamed file deleted by Sebas. Finding: sounds leave S6–S8 mostly POOR (draft, finding 6).

## Thu 5 · cap (session `b5bcf5bd`, BEHAVIOR_ADAPTIVE, set A; analysis in `Borrador_Plan_Fase6_9_5nov.md`)

### [-] H1: offset/drift **no data** (the taps missed Cz; method fixed in D-F6-150). Alpha 5.6 · 2.55 · 3.49, passes (official, D-F6-155).
### [x] H2: block 3, `BLACK_SCREEN_START` → `END` 120.02 s (`14d46df`); no screen peak in 1–40 Hz.
### [x] H3: 499–500 of 500 samples in ±1 s of every `FRAME_HITCH`. Hitches = Profiler recording + component menus (A-22 closed, D-F6-153).
### [x] Afternoon: `SOUND_S = 0.5` (`4196699`), sync text (`9d47670`), `autorun` (`01e10ac`); backend 270 passed.
### [x] Stop Thu: results for the EEG chat in `Claude outputs/Borrador_Plan_Fase6_9_5nov.md`.

## Fri 6 · cap (STATIC, set B) · font and keys first (Sebas, 6 Nov)

### [x] K0a · font: why `NotoSansCJKjp-Regular SDF.asset` keeps showing as modified (diagnosis only; cause and options in `Borrador_Plan_Fase6_9_6nov.md`)
- [x] Cause: Dynamic + Clear Dynamic Data On Build. Play (`FontPrewarm.Run`) fills it: 2 → 246 characters, 8.4 MB once saved (reproduced). Closing the Editor and every build empty it again (TMP source: `EditorApplication.quitting`, `TMP_PreBuildProcessor`; read in the source, not run live). The commit holds a 2-character state that no workflow produces.
- [x] All 246 content characters have a glyph (no `[FontPrewarm]` warning).
- [x] Asset back to the commit (Thu 5's font) and reimported; Thu 5's working copy saved in the scratchpad.
- [ ] **Stop:** Sebas picks the fix (recommended: 1, untick the box + commit the 246 characters).

### [x] K0b · font fix (correction; option 1, Sebas 6 Nov)
- [x] X29 (RED 108/109: box on, 244/245 missing) → untick Clear Dynamic Data On Build + asset filled with the 245 characters (246, 4 pages, 8.4 MB) → GREEN 109/109.
- [x] S0 prewarm on the real asset: 0 added, file byte-identical (sha1) after SaveAssets.
- [x] Commit `ca53a70` (message `Downloads/commit_k0b_font.txt`, shown to Sebas first). `graphify update .`
- [x] **Gate (D-F6-159):** met (Sebas, 6 Nov). Sebas runs S0→S2 in the headset, no glyph warnings · restart Unity → `git status` clean · time left before the cap. Otherwise no commit before the session: `git checkout` the asset (Thu 5's font) and K0b goes after the session or Mon 9.
- [x] **Stop.**

### [x] K1 · researcher keys instead of component menus (F4, D-F6-158; brings D-F6-154 forward and widens it)
- [x] Clash check (draft, Shortcut Manager `[Default]`): no clash; G/E/T only switch Scene-view tools, C/B only inside closed windows. Live press in Play still pending (headset test). Was: G E T B C vs 1–4, H, L, M (`DebugTrialPresenter`, `DemoDirector`; are they active in `JapaneseLearningStudio`?) and vs Editor shortcuts with the Game view focused (Shortcut Manager + a real press in Play). On a clash: another letter, never an F, written down; wait for Sebas.
- [x] Static map key → action + allowed state (`ResearcherKeyActs`; G = while the chain runs, since every wait takes Force advance); `SessionFlowRunner.Update` reads `Keyboard.current`: **G** Force advance · **E** EEG ready (S3) · **T** sync tap without controller (Editor without headset) · **B** block 3 (after S9) · **C** force complete assembly (S5). Each press logged; outside its state, logged and ignored.
- [x] Remove the five `[ContextMenu]` attributes (methods stay). "Start session chain" and the debug/probe menus stay.
- [x] S0 log: the key list + "Game view in front". Operator steps in the draft: letters instead of menus.
- [x] Harness case X30 (13 combinations + 5 menus gone): 110/110. Was: each key → its action in its state; wrong state or no key → nothing. Harness green.
- [x] Editor + headset by Link, no cap (Sebas, 6 Nov): each letter in its state, no `FRAME_HITCH` > 100 ms.
- [x] One commit (body: F4, D-F6-158). `graphify update .`
- [x] **Stop.** Not ready before the cap → D-F6-153 (menus only outside S4–S8).

### [ ] F0 · before the cap (D-F6-153)
- [ ] Unity restarted just before; Profiler closed; Blender, ChatGPT, Firefox, VS Code closed on that PC.
- [ ] Inspector: `condition = STATIC`, `newSessionKanjiSet = B`, `createNewSessionOnPlay` on, `eegStep` on, `baselineTimeScale = 1`.
- [ ] Backend up (no `--reload`). From `backend\`: `$env:POSTGRES_HOST='127.0.0.1'; .venv\Scripts\python -m app.eeg.autorun` → *waiting for a new session*.
- [ ] AURA's software, all channels blue; LabRecorder open, not recording.
- [ ] **Stop:** Sebas confirms the list.

### [ ] F1 · session S1 → S9 (STATIC, set B)
- [ ] Play → autorun prints the id and `ses-<8>`. LabRecorder: Update, tick only `AURA` and `UnityMarkers` of `LaptopSebas1803` (not MSI's `AURA`), check the name, Start.
- [ ] S3: "EEG ready" with **E** (with K1) or the menu opened and closed fast (without K1). Sync (D-F6-150): the assistant alone, ring on Cz's housing, trigger at the same instant, ×5, spike in AURA before each next.
- [ ] S4 → S8: nobody touches the PC, switches window or opens menus; nobody talks to the participant (D-F6-152).
- [ ] S9: 5 taps again. Block 3 (2 min; **B** with K1), then Stop in LabRecorder.
- [ ] **Stop:** session `COMPLETED`, XDF closed, autorun done.

### [x] F2 · after the session (backend; the session doesn't wait for it)
- [x] F2a (`742ec49a`: 304 epochs 156/60/88, alpha passes): autorun says *both streams recorded*; epoch counts (GOOD/ACCEPTABLE/POOR) with rule B; `eeg_sessions` alpha ratio and passed (official, D-F6-155).
- [x] F2b (D-F6-156; b5bcf5bd A→B 166→190 non-POOR; commit `99e89f6`): `epochs.save` writes `sound_s` and `epochs_version` into `eeg_sessions.filter_params` (jsonb, no migration); test. Re-run `epochs.py` on `b5bcf5bd` with rule B. Both sessions show `sound_s = 0.5`. One commit.
- [x] F2c (D-F6-157; 742ec49a offset 155.3 ms OUT, drift 0.1; b5bcf5bd empty; 277 passed; commit `c5fbf90`): `app/eeg/sync.py` + migration `0012` (`sync_detail jsonb`, D-F6-159). Offset = median(Cz peak − `SYNC_TAP`) over the valid S3 taps; drift = median S9 − median S3; < 3 valid taps in S3 or S9 → empty columns + reason. Clear peak (D-F6-159): ±500 ms, > 5× MAD of the 2 s before (stored in `sync_detail`). Tests: synthetic known lags; 2 valid taps → empty + reason. `autorun` runs it after `epochs`. Run on today's and on `b5bcf5bd` (empty, "no clear peak"). One commit.
- [x] F2d (P7 S7: b5bcf5bd 56 %, 742ec49a 6 %; A-7 NOT VALID both; commit `080af89`): `database/verify_eeg.sql` (read-only, `-v sid=`): XDF + both streams + row; offset/drift in range or empty with its reason; epochs' rule; S4 alpha passes; S6 ≥ 6 non-POOR; % S7 windows with P7 ≥ 60 % (A-7, D-F6-127; vs the EEG chat's 61 % on `b5bcf5bd`); usable epochs per ESL level; `FRAME_HITCH` chunks per state; multimodal lines "n/a". One commit.
- [x] Run F2d on `b5bcf5bd` (after F2b) and today's; output in the draft. Commit messages in Downloads, shown first. `graphify update .`
- [x] **Stop:** Sebas saw both outputs. Pz diagnosis (not the cause) in the draft; second cap run moved to Mon 9 (Dudas 11).

### [x] F3 · week close in `Claude outputs/Borrador_Plan_Fase6_9_6nov.md`
- [x] Done, findings (recorded, not fixed), F4 S2 criterion (`Planteamiento_Tecnico_F4.md` §4) met or not, with the evidence.
- [x] "Dudas para PM" with the date, or "Sin dudas · 6 nov".
- [x] `tasks/` boxes up to date.
- [x] **Stop:** Sebas's OK (6 Nov).

### Moved
- [-] Spec v1.4 review → Mon 9 (board §1).
- [-] D-F6-151 (`window.py` ≥ 15 s) → week of 9 Nov.

---

## Later (not this week)
- [ ] B4c SDF morph (D-F6-115), before 13 Nov if at all.
- [ ] Two Playwright tests failing on today's data (26 Oct).
- [ ] T2/T3 lures on when Content's lists and MIRAI's answer (A-17) arrive.
- [ ] Look at the set A M images (`ac26857`) in the headset: not seen at Stop 3 because STATIC keeps LAL at MEDIUM; needs a session that reaches the LAL level that shows them.

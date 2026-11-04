# Todo: week of 2 – 6 Nov (F4 S2 · integrate the EEG)

Plan: `tasks/plan.md`. Previous list: `tasks/archive/semana_26oct_todo.md`.
**Aligned up to: D-F6-131** · approved by Sebas, 2 Nov (D-F6-132) (`Estado_Actual.md`, the board; it wins over this list).

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

## Thu 5 · cap

### [ ] H1: S3 and S4 in the headset with EEG: offset and drift (±100 ms, drift < 50 ms); alpha ratio.
### [ ] H2: block 3, 2 min black screen, with markers.
### [ ] H3: sample count around each `FRAME_HITCH`: no lost samples. Profiler connected during S4 in the headset (the ≈ 300 S4 slow frames of R2 not explained by T2).
### [ ] Stop Thu: results for the EEG chat in `Claude outputs/`.

## Fri 6 · cap

### [ ] F1: full S1 → S9 with EEG and lures in the headset.
### [ ] F2: `verify_eeg.sql`: XDF + row, offset/drift in range, S4 alpha passes, S6 ≥ 6 non-POOR epochs (else S4 open marked), % S7 windows where the EEG counts (≥ 2 non-POOR, ≥ 5 clean seconds counted once) ≥ 60 % (D-F6-127).
### [ ] F3: spec v1.4 review notes (draft in `Claude outputs/`).
### [ ] F4: week log draft in `Claude outputs/`.
### [ ] Stop Fri: F4 S2 criterion (`Planteamiento_Tecnico_F4.md` §4).

---

## Later (not this week)
- [ ] B4c SDF morph (D-F6-115), before 13 Nov if at all.
- [ ] Two Playwright tests failing on today's data (26 Oct).
- [ ] T2/T3 lures on when Content's lists and MIRAI's answer (A-17) arrive.
- [ ] Look at the set A M images (`ac26857`) in the headset: not seen at Stop 3 because STATIC keeps LAL at MEDIUM; needs a session that reaches the LAL level that shows them.

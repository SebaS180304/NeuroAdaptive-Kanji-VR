# Todo: week of 9 – 13 Nov 2026 (F4 S3 · multimodal)

Plan in `tasks/plan.md`. **Approved by Sebas; aligned up to D-F6-187** (audit fixes D-F6-186/187 added 10 Nov, waiting for Sebas's OK) (Tue updated 10 Nov: T0b sync anchor, D-F6-179; EEG staff moved, D-F6-180). Each task: tests, commit (message shown first), `graphify update .`, Stop.
Backend tests: `pytest` (exact invocation confirmed at M1). Harness: Unity Editor.

---

## Mon 9 · quality, sync, indices; cap at 18:00

### [x] M1 · sync at strike onset (S)
`backend/app/eeg/sync.py`, `autorun.py`, `tests/test_eeg_sync.py`, `test_eeg_autorun.py`.
- [x] Onset (D-F6-161, F4 §2.4): last point before the peak where **raw** |Cz| falls under max(5 × noise, 10 % of the peak). Noise = MAD × 1.4826 of Cz **from 400 to 150 ms before the peak** (F4 Registro 6 Nov §1), not the 2 s before the search window: taps close together contaminate that one. Peak stays in `sync_detail`, does not correct.
- [x] Each tap keeps its onset lag and its peak lag; `sync_detail` adds the spread of every clear tap (S3 and S9). The requirement (spread ≤ 50 ms, drift < 50 ms, |offset| ≤ 250 ms) is checked in `verify_eeg.sql` (M3), as today.
- [x] Offset = median of S3 only; S9 only measures drift; S9 under 3 clear taps → drift empty, session marked with its reason, offset kept (D-F6-173, D-F6-176).
- [x] `autorun`: lsl_reader → **sync → epochs**. Remove "Now block 3" (D-F6-167).
- [x] Tests: synthetic strike with known onset; 2 valid taps in S9 → offset kept, marked; 2 in S3 → empty; autorun order.
- [x] **Check:** on `742ec49a`, S3 offset 35.3 ms, spread 18.4, drift +16.9; `b5bcf5bd` empty with reason. Per tap, exactly one sample (4 ms) before the EEG chat's; their ≈ 47 is the median of all 10 taps, the offset is S3 only (D-F6-157/173/176).
- [x] **Stop.**

### [x] M2 · epochs: 9 chunks, covered time, offset (M)
`backend/app/eeg/epochs.py`, migration `0013`, `tests/test_eeg_epochs.py`.
- [x] 9 chunks of 1 s every 0.5 s from the epoch start (D-F6-163).
- [x] Quality = union of clean chunks: GOOD ≥ 4 s, ACCEPTABLE ≥ 3 s, POOR < 3 s (D-F6-166). `clean_fraction` = covered / 5.
- [x] `fill_from_xdf` subtracts the S3 offset from the EEG stamps, the same as live and replay (D-F6-176). Under 3 clear taps in S3: no correction, marked. Only S9 fails: corrected, marked, no drift.
- [x] Migration 0013: `cardinality(chunk_clean) IN (5, 9)`, up and down. Rows of sessions not recomputed stay valid.
- [x] `EPOCHS_VERSION` bumped; docstring.
- [x] Tests: 3 s of clean time in separate stretches is ACCEPTABLE; 2 clean chunks is POOR; five clean fixed chunks grade as D-F6-73; the offset moves a sound's exclusion by exactly that; migration up/down.
- [x] **Stop.**

### [x] M3 · verify_eeg.sql and recompute (S)
`database/verify_eeg.sql`.
- [x] Chunk start from the epoch's own length: `(k − 1) × 4000 / (cardinality − 1)` ms.
- [x] P7 window (D-F6-162, D-F6-151, D-F6-172): ends at `answered_elapsed_ms`, reaches back over max(3 trials, 15 s), epochs by centre **and finished at the answer**, clean seconds as a union.
- [x] Block 5 prints the official figure and, as a contrast only, the figure by centre without the finished rule. A-7 uses the official one.
- [x] Sync block: spread ≤ 50, drift < 50, |offset| ≤ 250; session marked when there is no valid sync.
- [x] Recompute `742ec49a` and `b5bcf5bd` (`sync` then `epochs`, D-F6-156).
- [x] **Check:** official P7 `b5bcf5bd` 67 % (12/18), `742ec49a` 78 % (14/18), both A-7 VALID. Contrast 72 % and 83 % vs the EEG chat's 78 % and 72 %: 1 and 2 windows of difference, reported in the draft, not adjusted.
- [x] **Stop:** Sebas sees both outputs. **Target 17:00; the cap does not wait for it.**

### [x] M7 · cap session (17:15 list, 18:00–19:45)
- [x] 17:15 D-F6-153: Unity restarted; Profiler closed; Blender, ChatGPT, Firefox, VS Code closed.
- [x] Inspector: `condition = BEHAVIOR_ADAPTIVE`, `newSessionKanjiSet = C`, `createNewSessionOnPlay` on, `eegStep` on, `baselineTimeScale = 1`. Inspector changes reverted after.
- [x] Backend up, no `--reload`, restarted with today's commits. `autorun` waiting. AURA all blue, **Pz checked** (D-F6-164); LabRecorder open, not recording.
- [x] **Stop:** Sebas confirms the list.
- [x] Play → LabRecorder: Update, tick only this PC's `AURA` and `UnityMarkers`, name has this session's id (D-F6-146), Start.
- [x] S3 and S9: 5 taps each, **≈ 3 s apart**, spike seen in AURA before the next (D-F6-150, D-F6-164). **E** for EEG ready.
- [x] S4 → S8: nobody touches the PC, nobody talks to the participant. **No block 3.** Stop in LabRecorder after S9.
- [x] Autorun finishes (if M1 is not committed yet, `sync` and `epochs` are rerun after it); `verify_eeg.sql` on the new session; second sync measurement noted (A-23).
- [x] 19:45 XDF to the EEG chat.
- [x] **Stop:** session `COMPLETED`, XDF closed.

### [x] M4 · features.py (S)
`backend/app/eeg/features.py` (new), `epochs.py` save, test.
- [x] Welch with Hann 1 s on clean chunks only; bins 4–7 / 8–12 / 13–22 / 1–40 Hz (Reevaluación §4.4.1).
- [x] EI per channel then averaged over the 7 channels present; theta relative on Fz; parietal alpha and theta/beta stored only (D-F6-129). POOR epochs stay empty.
- [x] Tests: synthetic known spectrum gives the expected ratios; a lost channel averages the rest.
- [x] **Stop.**

### [x] M5 · reference.py (S)
`backend/app/eeg/reference.py` (new), migration `0014`, test.
- [x] Mean and SD of ln(index) over non-POOR S6 epochs; under 6 → S4 eyes open, marked (D-F6-73). Stored in `eeg_sessions`.
- [x] SD of 0 → that index does not count (no division by zero).
- [x] Tests: S6 normal; 5 epochs → S4 and the mark; SD 0.
- [x] **Stop.**

### [x] M6 · window.py (S)
`backend/app/eeg/window.py` (new), test.
- [x] The window ends at the answer of the 3rd trial, as `verify_eeg.sql` (D-F6-177); the 15 s count back from it. Counts: ≥ 2 non-POOR epochs by centre and finished at the decision (D-F6-172), ≥ 5 s clean as a union, over max(3 trials, last 15 s) (D-F6-127/151/162). z = mean of the non-POOR epochs' z.
- [x] Tests: 3 s trials still reach back 15 s; a second shared by two epochs counts once; an epoch ending after the decision does not count.
- [x] **Check 1:** same counts as `verify_eeg.sql`, window by window: 18/18 on `b5bcf5bd` and on `742ec49a`. `07343b5d`: 18/18.
- [x] **Check 2 (F4 §5 "done when"):** `b5bcf5bd` parietal alpha z = +4.16 with eyes closed in S4 (n 17, by centre), expected ≈ +4.6; right direction and size, reported, not adjusted.
- [x] **Check 3 (D-F6-172):** P7 of S7 with finished epochs, against 78 % / 72 %, **in today's draft for the EEG chat**.
- [x] **Stop.**

### [x] M8 · close
- [x] `tasks/` ticked; `Claude outputs/Borrador_Plan_Fase6_9_9nov.md` updated with done, findings, P7, Dudas.
- [x] **Stop:** Sebas's OK.

---

## Tue 10 · rules; spec review (D-F6-180: from 14:30, in parallel with the reserve; Stops grouped at the end of each task, Sebas in Blender)

EEG staff session **Wed 11 at 12:00** (confirmed by Sebas, board §1). Nothing from it is applied until it has a number in §4.

### [x] T0 · autorun writes its output to a log file (S) · D-F6-179 (2)
`backend/app/eeg/autorun.py`, `tests/test_eeg_autorun.py`; the log folder gitignored.
- [x] Everything `autorun` prints, tracebacks and the `baseline` child's output go to one file per run; its path is printed at the start.
- [x] `faulthandler` writes Python's fatal errors there; a last line when the process ends, so a silent death shows as a log with no end line.
- [x] The cause of the 9 Nov death stays unconfirmed: this is for next time, not a diagnosis.
- [x] Test: the file receives a print and a child's output; the steps `autorun` runs do not change.
- [x] Operator lists (J2, J3, V2) add "autorun alive before S3" (D-F6-179 (2)) and "eyes open, looking at the dot" said at the end of S3 (D-F6-179 (3)). No code for the S4 halves notice (after the dry run).
- [x] **Stop** (grouped with T0b). Sebas OK, 10 Nov.

### [x] T0b · sync anchor at the first 50 % crossing (S) · D-F6-179 (1)
`backend/app/eeg/sync.py`, `tests/test_eeg_sync.py`.
- [x] Anchor = first sample in the ±500 ms window where |Cz − median| reaches 50 % of the peak. Noise window 400–150 ms **before the anchor**; threshold max(5 × noise, 10 % of the peak); onset = last point before the anchor under it. Nothing else changes; peak and anchor lags kept in `sync_detail` with `anchor_fraction` (there is no SYNC_VERSION); docstring updated.
- [x] Test: a strike with a plateau (peak at its end) gives the onset at the rise, not at the plateau's end; the existing tests stay green unchanged.
- [x] Recompute on the PC, `sync` then `epochs` (D-F6-156). Targets (F4 Registro 9 Nov night, PM 10 Nov), S3 / S9 / drift / spread: `742ec49a` **unchanged** 35.3 / 52.2 / +16.9 / 18.4 ms, tap by tap; `07343b5d` 65.3 / 85.7 / +20.3 / 15.6 ms, **S3-2 → 68.7 ms**; `b5bcf5bd` still empty with its reason. `verify_eeg.sql` on `07343b5d`: sync block now OK.
- [x] Mine vs the targets compared in the draft before the Stop; a figure off is reported, not tuned. **Done:** all match; drift +20.4 (rounding of 85.7 − 65.3) and four S9 taps move 8 ms, not three (`b31c92e`, `fc44a3a`).
- [x] **Stop** (T0 + T0b): Sebas sees the three sync outputs. OK, 10 Nov.

### [x] T1 · concordance.py (S)
`backend/app/eeg/concordance.py` (new), test.
- [x] Input: behavioural state, this window's `window.evaluate()`, the previous one's (the cause only changes the action: T2). Output: `CONFIRMED`, `VETO`, `LED`, `UNAVAILABLE`, `ONLY_ALERT` or `NEUTRAL`.
- [x] One synthetic test **per row of §3.5** (D-F6-128).
- [x] Lead tests: two windows ≤ −1.5 lead; one of the two without valid EEG does not lead; only `STABLE` leads. **The action tests (LAL one step down; `AT_LIMIT` at LOW) moved to T2**, where the action is chosen.
- [x] `STABLE` with z ≤ −1.5 in a single window → `ONLY_ALERT` (D-F6-174, marked in the code).
- [x] Alpha never changes the result (D-F6-129).
- [x] Default of T1, marked in the code: the index the state reads is missing (reference SD 0, M5) → `UNAVAILABLE`. Reviewed in J5 with D-F6-174.
- [x] **Stop.** Sebas OK, 10 Nov.

### [x] T2 · rules-v2-mm (M)
`backend/app/adaptation/rules.py`, `state.py`, migration `0015`, tests. Golden `--json` replay captured **before** editing.
- [x] Coincides: acts in 1 window. Veto: `NO_CHANGE`. Unavailable: as `BEHAVIOR_ADAPTIVE`, marked. Lead: per §3.3.
- [x] Lead action (moved from T1): `EEG_LED` → LAL one step down; at LOW → `NO_CHANGE` with `AT_LIMIT`, ESL unchanged (D-F6-128).
- [x] D-F6-174, each marked in the code and with a test: a vetoed window counts for the hysteresis; `STABLE` off MEDIUM with the EEG leading leads; coinciding when behaviour would act anyway gives `reason_code` `EEG_CONFIRMED`.
- [x] Unchanged and tested: initial window, cooldown 3, tail 4, level limits, one change at a time, D9; a difficulty raise only returns with `DISENGAGED` or `OVERLOADED` (D-F6-59).
- [x] Migration 0015: `eeg_counted`, `eeg_ei_z`, `eeg_theta_z`, `eeg_effect`; `project_event` copies them; `v_adaptations` not touched: it lists its columns one by one, so adding columns does not need it recreated. `proj_apply` patched in place from its own definition (fails loudly if the text moved); up/down/up checked.
- [x] Check every reader of `reason_code` (`outcome.py`, research API, dashboard) accepts the new codes. Research API and dashboard show it as text (VARCHAR 32); `outcome.py` gets `EEG_LED` → `UNCERTAIN` when still `STABLE` (marked default).
- [x] **Check:** `BEHAVIOR_ADAPTIVE` replay **byte-identical** to the golden; all earlier tests green. **Done:** 36/36 golden files identical (18 sessions × own and `behavior-v2`; 3 with no S7, empty both times); 361 passed, 4 skipped.
- [x] **D-F6-178, when T2 closes:** backend up, `docker compose exec backend python -m app.adaptation.replay 678b7806-6f0d-4c6c-9673-6f1addd53701` (its own version) and the same with `--version behavior-v2`. Both outputs verbatim in `Claude outputs/Borrador_Plan_Fase6_9_10nov.md` with the full id. If T2 is late, run them on the committed code anyway and say so (Sebas records the video at 19:00).
- [x] **Stop.** Sebas OK, 10 Nov.

### [x] T3 · spec v1.4 review (no edits to the spec, D-F6-88)
Read `docs_proyecto/NeuroAdaptive_VR_Game_Flow_v1_4_Unity_Design_Specification.docx` (source `Spec_v1_4_borrador.md`) against the code.
- [x] Developer review 1 (§3.4): angles from the saved `LayoutOfRecord` output, **with its date or commit**; if it is before 30 Oct, said so: re-measured Thu with Unity free. **Done:** table from 23 Oct (`ea2d32b`), last edited 27 Oct: re-measure Thu.
- [x] Developer review 2 (§11.3): head-away thresholds in the code (`HeadBehavior.cs`) vs `Medicion_D7_HeadAway.md` vs the spec.
- [x] Developer review 3 (§10.4, §11.5): today `concordance.py` and `rules-v2-mm` as committed; live path and EEG replay on Wed when X1/X2 close (PM corrects the spec Thu before the freeze).
- [x] Developer review 4 (§6.2): answered Wed with X6b.
- [x] Other mismatches with the code, by section, each with file and line. **Done:** 13 in the draft; one Duda (cap of 3 changes in `rules-v2-mm`).
- [x] All in the draft for PM; nothing written in `docs_proyecto/`.
- [x] **Stop.** Sebas OK, 10 Nov.

### [ ] T4 · from the EEG staff session · **moved to Wed 11 after 14:30**
- [ ] Only what has a number in §4. Rule changes recompute from XDF (D-F6-156). **Session confirmed Wed 11 at 12:00:** numbered items go after 14:30 and before J1 on Thu. Thursday's freeze does not move; if something does not fit, cut X7 first, then X6b.
- [ ] **Stop.**

### [x] T5 · close (draft with done, findings, replay output, T3 notes, Dudas; `tasks/`)
- [x] **Stop:** Sebas's OK, 10 Nov.

---

### [x] A1 · backend only on 127.0.0.1 (XS) · D-F6-186 (1) · Tue 10 evening
`docker-compose.yml` (backend `ports`).
- [x] `"127.0.0.1:8000:8000"` **and `"[::1]:8000:8000"`** (Windows resolves `localhost` to ::1 first: without it Unity's WebSocket took 2.24 s instead of 0.42 s), as `db` and `pgadmin`. Backend restarted.
- [x] **Check:** from this PC, `curl 127.0.0.1:8000/health` 200; dashboard through the Vite proxy (`127.0.0.1:8000`); `ws_smoke_test` (localhost) passes; Unity in the Editor (`localhost:8000`, Play until S1, a session created and events ACKed); `autorun` unaffected (it talks to the database, not to the API). From another machine the port no longer answers: noted for X5 (A-20), not tested here. **Done:** LAN address 192.168.10.122 refuses; NativeWebSocket from the Editor to `localhost` opens in 0.42 s; dashboard proxy 200; `ws_smoke_test` OK.
- [ ] **Stop.**

**Then, Tue evening if time allows, in this order (each its own commit and Stop):** X1b (with A2, below) → X6s → X4.

---

## Wed 11 · live, replay, fallback, lures (Benkyokai: no headset stops; each Stop is a note in the draft)

**EEG staff session Wed 11 at 12:00** (board §1, Wed row). **No Stops from Sebas 12:00–14:30:** X1 closes and has its Stop **before 12:00**; work from 12:00 to 13:30 goes on without Stops (each one a note in the draft). Staff answers with a number are applied **after 14:30** and before J1 (T4).

**13:30–14:30 (D-F6-178, demo ≈ 14:00):** no backend restart and `replay.py` never half done, committed or untouched. X2 is finished before 13:30 or starts after 14:30; X1's backend restart too. No migrations in that hour.

### [x] X0 · no session without a seed (XS) · D-F6-183 · with X1, before 13:30
`backend/app/schemas/session.py`, its route test. Unity untouched (`fallbackSeed` stays for the Editor without backend).
- [x] `random_seed` required and non-empty on session creation; 422 otherwise. Check every caller that creates sessions (Unity's `POST /sessions`, `ws_smoke_test`, test fixtures) still sends one.
- [x] Test: missing or empty seed → 422; with seed → created as today.
- [x] Stop grouped with X1's (before 12:00).

**Done Tue 10 (moved up):** `432de21`; live backend rejects a session without seed (422).

### [ ] A2 · live EEG read without the 60 s bound (XS) · D-F6-186 (2) · with X1b or right after, before 12:00
`backend/app/api/routes/websocket.py` (`_eeg_source`), `tests/test_eeg_live_read.py`.
- [ ] All epochs up to the answer (`start_ms <= answered_ms`), no lower bound; `EEG_LOOKBACK_MS` removed.
- [ ] Test: three trials spanning 75 s; the window counts the same epochs as `window.evaluate` over all of them (red before).
- [ ] Stop grouped with X1b's.

### [ ] A3 · the WebSocket closes a session like the PATCH (S) · D-F6-186 (3) · before 12:00
`backend/app/api/routes/sessions.py`, `websocket.py` (`_sync_current_state`), tests.
- [ ] One function for both paths: `current_state`, `status` (`_status_for`), `completed_at` once, the profile refresh, LabRecorder `stop` on S10; ABORTED is never overwritten (as today).
- [ ] With A7's backend half: a validation `ERROR` is logged with `logger.warning` and the original message.
- [ ] Test: S9's `STATE_ENTERED` over the WebSocket with no PATCH -> `COMPLETED`, `completed_at` set, `autorun.wait_completed` returns (sync and epochs then run, as `test_sync_runs_before_epochs_because_epochs_needs_the_offset` checks).
- [ ] **Stop** (before 12:00, with X1b's if they meet).

### [~] X1 · live path and heartbeat (M) · D-F6-171 · **X1a done Tue 10 (`9800c3c`), X1b Wed before 12:00**
**X1a (backend side), done:** at each S7 answer of `MULTIMODAL_ADAPTIVE` the WebSocket reads the epochs of the last 60 s and the reference; `feed(eeg_source=…)` → `window.evaluate()` ending at the answer → `decide()`. No epochs / no reference / read error → `UNAVAILABLE`. `STATIC` and `BEHAVIOR_ADAPTIVE` never read it (test). `rebuild` re-reads each stored block (test: same engine and decisions as live). 381 tests.
**X1b (`live.py` on the PC), notes for Wed:** reuse `epochs.make_epochs` over the **tail** of the buffer (≈ 30 s), sliced at a grid point (multiples of 2.5 s from the first sample) so `epoch_index` matches `fill_from_xdf`'s grid; the zero-phase filter needs a margin after the epoch's end before computing (edge), which is part of the arrival margin; offset from `sync.compute` once S3 ends (first `STATE_ENTERED` S4); `reference.compute` on entering S7; heartbeat (migration 0016) every 2 s; `autorun` starts it next to `baseline.py`.
`backend/app/eeg/live.py` (new), `autorun.py`, migration `0016`, `api/routes/websocket.py`, `adaptation/state.py`, tests.
- [ ] Buffers both streams on the PC; offset from the S3 taps (D-F6-173); every finished epoch to `eeg_epochs` with indices; reference on entering S7.
- [x] **`rebuild` and the lead:** `last_eeg` = the previous decision's payload `eeg` block, as is (one shape since `concordance.block()`, review 10 Nov). Test: live and rebuilt decide the same lead through `SessionAdaptationState.rebuild`.
- [ ] Heartbeat: `heartbeat_at` and the current EEG gap every 2 s.
- [x] Backend, on an S7 answer in `MULTIMODAL_ADAPTIVE`: reads the window's finished epochs (D-F6-172), calls `window.py`, feeds `decide()`; the EEG block goes into `ADAPTATION_DECISION`, and `rebuild` reads it.
- [ ] Arrival margin measured against the synthetic stream, recorded, and applied in `window.py` and `verify_eeg.sql`.
- [x] `STATIC` and `BEHAVIOR_ADAPTIVE` never read the EEG (test).
- [ ] **Check:** synthetic stream + `ws_smoke_test`: epochs arrive, heartbeat moves, a decision carries its EEG block, `decision_latency_ms` noted.
- [ ] **Stop.**

### [ ] A8 · no session without a set (S) · D-F6-187 · Wed after 14:30
`backend/app/schemas/session.py`, tests, `ws_smoke_test`.
- [ ] **First, in the draft:** every flow that creates a session and whether it sends a set: Unity `SessionBootstrap` (sends `newSessionKanjiSet`, default "A"); pre-test (creates participants, not sessions: to confirm); **short visit 4 and block R of D-F6-125** (not in code yet: which set would visit 4 be created with?); `ws_smoke_test` and the 13 test files that post `/sessions` (today without set; they would get one, as with the seed). **If any real flow has no set of its own: stop and tell PM; nothing is changed.**
- [ ] Only then: `assigned_kanji_set` required, `A`, `B` or `C` (422 otherwise); test; callers updated.
- [ ] **Stop.**

### [ ] X2 · replay.py with XDF (S)
`backend/app/adaptation/replay.py`, test.
- [ ] Adds XDF input: same filter-and-epoch path cut at the decision instants, S3 offset subtracted (D-F6-161, D-F6-173). Existing replay unchanged.
- [ ] Windows where `EEG_STATUS` says the process was down do not count, as they did not live.
- [ ] Reports `FRAME_HITCH` chunks per state (F4 §7; they are not in the database).
- [ ] **Check:** a session recorded through X1 replays to the same decisions; z differences reported.
- [ ] **Stop.**

### [ ] X3 · fallback, emulated (S) · D-F6-174
`live.py`, `state.py`, `scripts/synthetic_aura.py` (pause option), tests.
- [ ] `EEG_STATUS` (connected, lost, recovered, process down); `BEHAVIOR_FALLBACK` mark; > 60 s lost cancels the EEG for the session (§5.5); S4 alpha failing too.
- [ ] Heartbeat distinction: fresh with no valid epochs is not "process down"; stale is, and the backend writes it (D-F6-171).
- [ ] Emulated: stream stops pushing (cap off, Bluetooth); outlet gone (AURA closed); `live.py` killed.
- [ ] **Check:** in each case the session goes on with behaviour and is marked. **Real cases: J3.**
- [ ] **Stop.**

### [ ] X4 · lure columns (S) · D-F6-143
Migration `0017`, `project_event`, test.
- [ ] `option_kind`, `lure_selected`, `option_kinds` on `trials`, from the payload Unity already sends.
- [ ] Test: lure and no-lure trials project correctly; old sessions unaffected.
- [ ] **Stop.**

### [ ] X5 · A-20, LSL privacy
- [ ] Try (a) `.cfg` in AURA's executable folder, (b) PC off the lab network; synthetic stream, no cap.
- [ ] Check (b) keeps Link, AURA, LabRecorder, `autorun` and `live.py` working. **Seeing it from another PC needs someone at that PC.**
- [ ] Result in the draft, for a decision.
- [ ] **Stop.**

### [ ] X6s · substitution condition 1 without overlapping meanings (S) · D-F6-181 (2) · before X6a
`tools/kanji_metrics.py` (`hard_clash`, a check, export) → `kanji_content.json`; `backend/app/pretest/rules.py` (`_hard_clash`); tests of both. Commit as content (D-F6-62/122).
- [ ] `hard_clash` also fails when two meanings **share a word** (computed: *rice*/*rice field*) or one **includes** the other (an explicit `MEANING_INCLUDES` list, since no string shows it: *child*/*person*, *woman*/*person*, *shellfish*/*fish*; *thing* does not go in (precision of D-F6-181, 10 Nov). Both rules in one function, used by the table and the check of the nominal sets.
- [ ] The contract exports the clashing meaning pairs (`meaningClashes`, keyed like `similarity`); the pre-test's `_hard_clash` reads them. **Without this, two substitutions in a row can still bring 田 and 米 together**: the table only covers one substitution.
- [ ] The five nominal sets pass the new rule (no overlap among their own members).
- [ ] Regenerated table vs today's, in the draft. Dry run on 10 Nov (child/person only): 94 → 93 entries, only C 牛 loses 子 (8 left); woman/person and shellfish/fish do not change the table (one substitution), **no experimental kanji without a substitute**. If the real run leaves one empty: **stop, tell PM, nothing further.**
- [ ] Tests: `kanji_metrics` (child/person and rice/rice field clash; the table drops 子 for 牛); pre-test (with 田 already in the effective set, 米 is not offered). Backend suite green.
- [ ] **Stop.**

### [ ] X6a · T1 official lists (S) · D-F6-168, §16.2 and §16.3
`tools/kanji_metrics.py` → `kanji_content.json`, TMP font asset; commit as content.
- [ ] `LURE_T1` as §16.2 (10 of the sets change; reserve unchanged).
- [ ] "Sin relación" as an explicit table of the 35 of §16.2 instead of the greedy choice (4 of the reserve change); `provisional` true only for ⚑ metric (月, 竹, the reserve).
- [ ] `check_lures` clean. The components rule of §16.3 stays out this week.
- [ ] Font asset filled with the new characters and committed with the content; S0 prewarm leaves it byte-identical; X29 green.
- [ ] Harness green.
- [ ] **Stop.**

### [ ] X6b · T2/T3 official lists, active (S) · §16.4 · **second to cut**
`tools/kanji_metrics.py` → `kanji_content.json`, font asset, `TrialSequenceGenerator.ActiveLureTypes`, `SessionFlowRunner` card sizing, harness; commit as content + lures (D-F6-131).
- [ ] Font asset with the new characters **in this same commit** (as X6a). T2 and T3 strong and unrelated of the 35 (学 in katakana), **from §16.4 as it is in `docs_proyecto/`: final, with the six changes of 10 Nov** (人 robot, 手 neck, 石 brick, 門 window, 糸 needle, 学 play; D-F6-181 (3)). Categories stay in the document.
- [ ] D-F6-181 (1) (no part, whole or material as the T2 strong lure) is a content rule: no code; the current pairs already meet it.
- [ ] `check_lures`: T2/T3 present for all, distinct, and none is a taught meaning or reading of the pool (never two correct).
- [ ] Answer cards also sized from the lure texts.
- [ ] Harness: half of each type per block, never two correct, same trials across conditions; X29 green.
- [ ] **Stop.**

### [ ] X7 · reserve 16–20 (M) · **first to cut**
- [ ] FBX and the four images of `pistas/`, as sets A–C (D-F6-160); 18 and 19 with +90° X at the root. Harness only: **the headset look moves to Thu or Fri, after the cap.**
- [ ] **Stop.**

### [ ] X8 · close (draft, Dudas, `tasks/`)
- [ ] **Stop:** Sebas reads it Thu morning.

---

## Thu 12 · MULTIMODAL_ADAPTIVE end to end; rules frozen at night

### [x] J0 · cap of 3 changes per S7 (XS) · D-F6-182 · before the freeze (Thu morning, before J1)
`backend/app/adaptation/rules.py` (`RuleConfig.max_changes = 3`), test.
- [x] Explicit cap in `RuleConfig`, for both adaptive conditions; a blocked change is `NO_CHANGE` with its own `reason_code` (proposal `MAX_CHANGES`).
- [x] Test: `rules-v2-mm` with `EEG_CONFIRMED` every window stops at 3 (trials 3, 7, 11; 15 blocked).
- [x] **Check:** `rules-v2` replay byte-identical to the golden (it never reaches 3 + 1).
- [x] Tests that pin the T2 defaults 2 and 3: done 10 Nov (`d4f901d`).
- [x] **Stop.**

**Done Tue 10 (moved up):** `9ffc4c2`; reason `MAX_CHANGES`; rules-v2 replay byte-identical (36/36); D-F6-184 applied (`b1ccb46`): only eligible windows count for a lead. D-F6-185 (`3c8d9b7`): a low-confidence window cuts that count.

### [ ] A4–A7 · Unity: no event lost on a disconnect (S) · D-F6-186 (4)–(7) · Thu before J2 · one Unity commit, exception to the VR freeze (D-F6-122)
`unity-client/Assets/Scripts/Networking/SessionCommunicationClient.cs`. The commit body says it is the D-F6-186 exception.
- [ ] A4: send only with `_isConnected && _socket.State == WebSocketState.Open`; otherwise queue.
- [ ] A5: on quit with a non-empty queue, write it to `Logs/` as JSON and `Debug.LogError` with the count.
- [ ] A6: on open, flush the queue whenever it is not empty (first connection too), in order.
- [ ] A7: an `ERROR` from the backend -> `Debug.LogError` with its detail (backend half with A3).
- [ ] **Check in the Editor:** stop the backend in S7 and again in S8, start it again: no trial missing in `trials`, the queue arrives in order, `RECONNECTED` after it; quit with the backend down -> the JSON in `Logs/` and the count. J2 confirms it in the headset.
- [ ] **Stop.**

### [ ] J1 · synthetic end to end
- [ ] Editor, `MULTIMODAL_ADAPTIVE`, synthetic stream that varies between S6 and S7. Decisions with their EEG block; latency acceptable.
- [ ] **Stop** before the cap.

### [ ] J2 · cap, S1 → S9 in the headset
- [ ] Same list as M7 plus D-F6-179: `autorun` alive (log file growing) before S3; at the end of S3 the assistant says "eyes open, looking at the dot". Condition `MULTIMODAL_ADAPTIVE`; T1 lures on (T2/T3 if X6b), declared. New lure characters and card sizes seen in the headset.
- [ ] **Done when:** at least one decision with `EEG_CONFIRMED`, `EEG_VETO` or `EEG_LED`, applied and explained (F4 §5).
- [ ] None → forced state in the Editor, real signal confirms or vetoes; **declared as such**.
- [ ] **Stop.**

### [ ] J3 · three real fallbacks, one S7 each (D-F6-174), after J2 and not replacing it
For each case its own session in `MULTIMODAL_ADAPTIVE`: same list as J2 (M7 plus D-F6-179), `autorun` relaunched, its own XDF.
- [ ] Reach S7 with **G**, but **S4 complete** (no G in S4). If S6 is short, the reference falls to S4 eyes open, marked (D-F6-73).
- [ ] **Before cutting:** the EEG has counted in at least one S7 window (visible in `autorun`'s console).
- [ ] Case 1: cap off. Case 2: AURA software closed. Case 3: Bluetooth off.
- [ ] **Check, each case:** the session goes on with behaviour; `EEG_STATUS` lost and `BEHAVIOR_FALLBACK` in the database; heartbeat still fresh (the process did not die).
- [ ] A case that does not fit tonight moves to Fri morning, and PM is told.
- [ ] **Stop.**

### [ ] J4 · replay of J2
- [ ] Same decisions as live; every `EEG_LED` read one by one (F4 risk 8).
- [ ] **Stop.**

### [ ] J5 · freeze and close · **checklist: `docs_proyecto/Checklist_Congelamiento_Reglas_12nov.md`** (PM)
- [ ] **§2, conditions C1–C8**, each marked in the draft with its evidence: C1 = J1, C2 = J2 (or the forced state, declared), C3 = J4, **C4 = the four defaults of D-F6-174 and T1's (index with SD 0 → `UNAVAILABLE`) reviewed against J2**, C5 = `rules-v2` byte-identical, C6–C8 Sebas/PM (only noted).
- [ ] **C5:** `replay --json` of the 18 adaptive sessions (own version and `--version behavior-v2`) against the reference kept in `Claude outputs/referencia_replay_rules_v2_10nov/` (36 files, captured before T2): 36/36 identical.
- [ ] **§3, every parameter with its value** in the draft, read from the code at the commit to tag (not copied from the checklist): §3.1 epochs, quality, drop rules (F4 §6), P7 window, A-7, reference, offset; §3.2 confirm/veto, lead (D-F6-184/185), cap (`MAX_CHANGES`), defaults, **T1 default: the EEG counts but the index the state reads has no z (SD 0 in the reference) → `eeg_effect` = `UNAVAILABLE`, behavioural decision** (`concordance.py:49` theta for `OVERLOADED`, `:54` EI for the rest; test `test_the_index_the_state_reads_missing_is_unavailable`; duda 5, checklist row added by PM), `eeg_effect`, O4 of `EEG_LED`; §3.3 heartbeat, process down, **arrival margin (measured Wed)**, the > 60 s rule; §3.4 lures active on the dry run, seed, operation lists.
- [ ] **C9:** audit fixes 1–7 done (commits), A4–A7 tested in J2; D-F6-187 applied or why not.
- [ ] Tag proposed (name and commit), **created only with Sebas's OK**.
- [ ] **Stop:** rules frozen.

---

## Fri 13 · dry run with EEG

### [ ] V1 · verify_eeg.sql, multimodal lines (S)
- [ ] Every S7 decision in `MULTIMODAL_ADAPTIVE` has its EEG effect and none in the other conditions; counts per effect; `EEG_LED` outcome vs behaviour (F4 §7).
- [ ] Run on J2.
- [ ] **Stop.**

### [ ] V2 · dry run
- [ ] `MULTIMODAL_ADAPTIVE` (D-F6-175); lures active that day, declared (T1, and T2/T3 if X6b); set and participant as Sebas fixed them; the participant is not from the team and signs consent v1 (D-F6-76); lists as M7 plus the two D-F6-179 items of J2.
- [ ] **Done when:** full session with a participant, XDF with both streams.
- [ ] **Stop.**

### [ ] V3 · analysis
- [ ] `verify_eeg.sql` complete; replay matches; A-7 result; third sync measurement (A-23); `EEG_LED` one by one.
- [ ] **Stop.**

### [ ] V4 · week close
- [ ] Criterion of F4 S3 met or not, with evidence; findings recorded, not fixed.
- [ ] `tasks/` up to date; draft with Dudas or "Sin dudas · 13 nov".
- [ ] **Stop:** Sebas's OK.

---

## Later (not this week)
- [ ] Audit (D-F6-186, after the dry run): delete Unity's dead code (5 Phase-1 stubs and `XRTrackingProbe`, 253 lines, with their `.meta`; events `AdaptationClient.OnDecision`, `SessionCommunicationClient.OnDisconnected`/`OnReconnected`); own `ADAPTATION_SKIPPED` reason for an ESL change refused for a missing profile.
- [ ] V3: declare the up-to-one-frame delay of each `SYNC_TAP` (A-23 note) when analysing the 3rd offset measurement; no code.
- [ ] B4c SDF morph (D-F6-115).
- [ ] Two Playwright tests failing on the 26 Oct data.
- [ ] Set A M images in the headset (`ac26857`): needs a set A session reaching that LAL.
- [ ] Trial-level theta analysis from the XDF (F4 §5): a later script.
- [ ] Components rule of §16.3 in `check_lures`; classic pairs for the reserve (week of 16, Content).

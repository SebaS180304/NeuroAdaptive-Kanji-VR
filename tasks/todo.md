# Todo: week of 9 – 13 Nov 2026 (F4 S3 · multimodal)

Plan in `tasks/plan.md`. **Approved by Sebas; aligned up to D-F6-193 (Thu planned 12 Nov from D-F6-191 and D-F6-193, waiting for Sebas's OK)** (audit fixes D-F6-186/187 added 10 Nov, waiting for Sebas's OK) (Tue updated 10 Nov: T0b sync anchor, D-F6-179; EEG staff moved, D-F6-180). Each task: tests, commit (message shown first), `graphify update .`, Stop.
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

### [ ] T4 · from the EEG staff session · **moved to Thu 12 (D-F6-191): staff 11:00, decisions ≈ 12:30, T4 12:30–14:00; detail in the Thu section**
- [ ] Only what has a number in §4. Rule changes recompute from XDF (D-F6-156). **Session confirmed Wed 11 at 12:00:** numbered items go after 14:30 and before J1 on Thu. Thursday's freeze does not move; if something does not fit, cut X7 first, then X6b.
- [ ] **Stop.**

### [x] T5 · close (draft with done, findings, replay output, T3 notes, Dudas; `tasks/`)
- [x] **Stop:** Sebas's OK, 10 Nov.

---

### [x] A1 · backend only on 127.0.0.1 (XS) · D-F6-186 (1) · Tue 10 evening
`docker-compose.yml` (backend `ports`).
- [x] `"127.0.0.1:8000:8000"` **and `"[::1]:8000:8000"`** (Windows resolves `localhost` to ::1 first: without it Unity's WebSocket took 2.24 s instead of 0.42 s), as `db` and `pgadmin`. Backend restarted.
- [x] **Check:** from this PC, `curl 127.0.0.1:8000/health` 200; dashboard through the Vite proxy (`127.0.0.1:8000`); `ws_smoke_test` (localhost) passes; Unity in the Editor (`localhost:8000`, Play until S1, a session created and events ACKed); `autorun` unaffected (it talks to the database, not to the API). From another machine the port no longer answers: noted for X5 (A-20), not tested here. **Done:** LAN address 192.168.10.122 refuses; NativeWebSocket from the Editor to `localhost` opens in 0.42 s; dashboard proxy 200; `ws_smoke_test` OK.
- [x] **Stop.** Sebas OK, 10 Nov.

**Then, Tue evening if time allows, in this order (each its own commit and Stop):** X1b (with A2, below) → X6s → X4.

---

## Wed 11 · live, replay, fallback, lures (Benkyokai: no headset stops; each Stop is a note in the draft)

**Wed order, D-F6-189 (replaces the 12:00 notes below it):** A3 → Stop → **A9 (moved up)** → Stop → A8 flows in the draft (no code) → X2 if it fits. **Everything that restarts the backend, before 13:30.** 13:30–14:30: no restart, no migration, `replay.py` committed or untouched (D-F6-178). **13:30–16:00: no Stops from Sebas** (each Stop is a note in `Claude outputs/Borrador_Plan_Fase6_9_11nov.md`). EEG staff at **15:00**; numbered answers ≈ 16:30 → T4, before J1. **From 16:00, with Stops:** A8 (code, if the flows allow), X3, X5, X6a, X6b, X7 (cut X7, then X6b). Thu freeze does not move.

**Restarts, why they can wait:** the code is mounted and uvicorn has no `--reload`, so a commit changes nothing live until `docker compose restart backend`; a one-off `docker compose exec backend python …` already runs the new code. Nothing live needs A3/A9 before J1 (Thu). So: **one restart for A3 + A9 at ≈ 13:20 if both are committed; otherwise the restart moves to 16:00.** Before any restart, check Sebas recorded the Benkyokai backup video (D-F6-189 (1)). `replay.py` does not import `window.py`: A9 cannot touch the 14:00 demo.

**Started 12:26 (planning).** ≈ 60 min until 13:30 for A3 + A9; if A3 has not passed its Stop by ≈ 12:55, it is left uncommitted or stashed and A9 goes next, because A9's P7 is due in the 14:30 deck.

~~**EEG staff session Wed 11 at 12:00**~~ (moved to 15:00 by D-F6-189).

### [x] X0 · no session without a seed (XS) · D-F6-183 · with X1, before 13:30
`backend/app/schemas/session.py`, its route test. Unity untouched (`fallbackSeed` stays for the Editor without backend).
- [x] `random_seed` required and non-empty on session creation; 422 otherwise. Check every caller that creates sessions (Unity's `POST /sessions`, `ws_smoke_test`, test fixtures) still sends one.
- [x] Test: missing or empty seed → 422; with seed → created as today.
- [x] Stop grouped with X1's (before 12:00).

**Done Tue 10 (moved up):** `432de21`; live backend rejects a session without seed (422).

### [x] A2 · live EEG read without the 60 s bound (XS) · D-F6-186 (2) · with X1b or right after, before 12:00
`backend/app/api/routes/websocket.py` (`_eeg_source`), `tests/test_eeg_live_read.py`.
- [x] All epochs up to the answer (`start_ms <= answered_ms`), no lower bound; `EEG_LOOKBACK_MS` removed.
- [x] Test: three trials spanning 75 s; the window counts the same epochs as `window.evaluate` over all of them (red before: 23 vs 29). **Done Tue 10: `424646c`.**
- [x] Stop grouped with X1b's. Sebas OK, 10 Nov.

### [x] A3 · the WebSocket closes a session like the PATCH (S) · D-F6-186 (3) · **1st on Wed, before 13:30** (D-F6-189)
Today the close rule lives only in `update_session_state` (`sessions.py:136–164`: `_status_for`, `completed_at`, `learner_profile.refresh`, LabRecorder `stop`); `_sync_current_state` (`websocket.py:297`) only moves `current_state`. Extract it there, call it from both. Verification: `docker compose exec backend pytest -q` (all green, today 397).
`backend/app/api/routes/sessions.py`, `websocket.py` (`_sync_current_state`), tests.
- [x] One function for both paths: `current_state`, `status` (`_status_for`), `completed_at` once, the profile refresh, LabRecorder `stop` on S10; ABORTED is never overwritten (as today).
- [x] With A7's backend half: a validation `ERROR` is logged with `logger.warning` and the original message.
- [x] Test: S9's `STATE_ENTERED` over the WebSocket with no PATCH -> `COMPLETED`, `completed_at` set, `autorun.wait_completed` returns (sync and epochs then run, as `test_sync_runs_before_epochs_because_epochs_needs_the_offset` checks).
**Done Wed 11, 12:49:** `enter_state()` in `sessions.py`, called by the PATCH and by `_sync_current_state`; the WebSocket runs its follow-ups after the commit. `tests/test_session_close_ws.py` (3); 400 passed. Not live until the restart.
- [ ] **Stop** (Sebas, before 13:30). Commit; restart grouped with A9's.

### [~] X1 · live path and heartbeat (M) · D-F6-171 · **X1a `9800c3c`, X1b `f0b99da` `0dbde14` `2dffd48` (Tue 10); margin waits for PM (duda 6)**
**X1a (backend side), done:** at each S7 answer of `MULTIMODAL_ADAPTIVE` the WebSocket reads the epochs of the last 60 s and the reference; `feed(eeg_source=…)` → `window.evaluate()` ending at the answer → `decide()`. No epochs / no reference / read error → `UNAVAILABLE`. `STATIC` and `BEHAVIOR_ADAPTIVE` never read it (test). `rebuild` re-reads each stored block (test: same engine and decisions as live). 381 tests.
**X1b (`live.py` on the PC), notes for Wed:** reuse `epochs.make_epochs` over the **tail** of the buffer (≈ 30 s), sliced at a grid point (multiples of 2.5 s from the first sample) so `epoch_index` matches `fill_from_xdf`'s grid; the zero-phase filter needs a margin after the epoch's end before computing (edge), which is part of the arrival margin; offset from `sync.compute` once S3 ends (first `STATE_ENTERED` S4); `reference.compute` on entering S7; heartbeat (migration 0016) every 2 s; `autorun` starts it next to `baseline.py`.
`backend/app/eeg/live.py` (new), `autorun.py`, migration `0016`, `api/routes/websocket.py`, `adaptation/state.py`, tests.
- [x] Buffers both streams on the PC; offset from the S3 taps (D-F6-173); every finished epoch to `eeg_epochs` with indices; reference on entering S7.
- [x] **`rebuild` and the lead:** `last_eeg` = the previous decision's payload `eeg` block, as is (one shape since `concordance.block()`, review 10 Nov). Test: live and rebuilt decide the same lead through `SessionAdaptationState.rebuild`.
- [x] Heartbeat: `heartbeat_at` and the current EEG gap every 2 s (migration 0016).
- [x] Backend, on an S7 answer in `MULTIMODAL_ADAPTIVE`: reads the window's finished epochs (D-F6-172), calls `window.py`, feeds `decide()`; the EEG block goes into `ADAPTATION_DECISION`, and `rebuild` reads it.
- [~] Arrival margin **measured** (synthetic AURA + markers, S3 → S9): median 1.11–1.15 s, max 1.27–1.34 s after an epoch's end (1 s of it is the filter wait). **Fixed at 1.5 s by D-F6-188: applied in A9 (Wed after 14:30).**
- [x] `STATIC` and `BEHAVIOR_ADAPTIVE` never read the EEG (test).
- [~] **Check:** synthetic stream: epochs arrive (26, consecutive), heartbeat fresh, reference from S6 (all 11). A decision with its EEG block: covered by X1a's tests; **end to end through the WebSocket with `decision_latency_ms` goes to J1** (needs S7 answers in `MULTIMODAL_ADAPTIVE`).
- [x] **Stop** (X1b). Sebas OK, 10 Nov; end-to-end decision in J1.

### [x] A9 · arrival margin of 1.5 s in the three counts (S) · D-F6-188 · **moved up to Wed morning, before 13:30 (D-F6-189 (2))**
`backend/app/eeg/window.py` (live and replay), `database/verify_eeg.sql`, their tests.
Touch points: `window.py:46` (`e["end_ms"] <= decision_ms` → minus a named 1 500 ms constant); `verify_eeg.sql:72` and `:76` (`end_ms <= w.hi` → `w.hi - 1500`), header comment of block 5 updated. The `*_centre` contrast columns stay as they are.
- [x] An epoch counts in a window only if it **ended at least 1.5 s before the answer** (D-F6-172 + D-F6-188), in `window.py` and in `verify_eeg.sql`'s P7 block; each with its test (an epoch ending 1.4 s before the answer does not count, one ending 1.5 s before does).
- [x] **Check:** `window.py` and `verify_eeg.sql` still agree window by window on `b5bcf5bd`, `742ec49a`, `07343b5d` (as M6).
- [x] Official P7 recomputed for the three (today 67 %, 78 %, 83 %) **in `Borrador_Plan_Fase6_9_11nov.md`, a table old → new per session, with the commit**, for the EEG chat (→ F4) and the presentation chat (→ deck, closes 14:30); one under 60 % is reported as data, the rule is not changed. Computed with `psql` on the db and a one-off `docker compose exec`: no restart needed for the figure.
**Done Wed 11, 14:01: `33d3eae`.** P7 67→61 %, 78→72 %, 83→67 %, all VALID; window.py = SQL on 54/54 windows. 401 tests. Restart after 14:30 (A3 went live at 13:57, inside the no-restart hour: see the draft).
- [ ] Before 13:30 (D-F6-189). **Stop** (Sebas reads the table). Then the restart for A3 + A9 if ≤ 13:20, else at 16:00.

### [x] A8-flows · every session-creating flow, in the draft, no code · D-F6-187 condition · before 13:30, else 13:30–16:00 (no Stop, a note)
- [x] The list of A8's first bullet below, each flow with file:line and whether it sends `assigned_kanji_set`.
- [x] Verdict in one line: "no real flow without a set" → A8 code after 16:00; or "flow X has none" → **Dudas para PM**, A8 code stays out, Sebas told in one line.

**Done Wed 11, 14:55:** no real flow creates a session without a set (Unity sends "A" by default; pre-test and portal create none; visit 4 / block R not in code). A8 code from 16:00: `ws_smoke_test` and 23 API test posts get a set. Duda 1 answered by D-F6-190 (not on the board mirror yet at 15:11): visit 4 uses visit 3's set; block R keeps the session it evaluates in its own field, not `assigned_kanji_set`. Applied with block R (week of 16 Nov); nothing changes today.

### [x] A8 · no session without a set (S) · D-F6-187 · **Wed from 16:00, only if A8-flows says so** (it is a backend change: restart after it, outside 13:30–14:30)
`backend/app/schemas/session.py`, tests, `ws_smoke_test`.
- [x] **First, in the draft:** every flow that creates a session and whether it sends a set: Unity `SessionBootstrap` (sends `newSessionKanjiSet`, default "A"); pre-test (creates participants, not sessions: to confirm); **short visit 4 and block R of D-F6-125** (not in code yet: which set would visit 4 be created with?); `ws_smoke_test` and the 13 test files that post `/sessions` (today without set; they would get one, as with the seed). **If any real flow has no set of its own: stop and tell PM; nothing is changed.**
- [x] Only then: `assigned_kanji_set` required, `A`, `B` or `C` (422 otherwise); test; callers updated.
**Done Wed 11, 15:59: `1829024`.** Live with X3 in one restart (15:59). Missed flow found: Editor `SessionSetupTool.cs`, already sends a set.
- [x] **Stop:** Sebas OK, Wed 11.

### [x] X2 · replay.py with XDF (S) · **if it fits:** committed before 13:30 or started after 14:30, never half done in between (D-F6-178); with no Stop until 16:00, it closes with a note and Sebas's OK comes at 16:00
`backend/app/adaptation/replay.py`, test.
- [x] Adds XDF input: same filter-and-epoch path cut at the decision instants, S3 offset subtracted (D-F6-161, D-F6-173). Existing replay unchanged.
- [x] Windows where `EEG_STATUS` says the process was down do not count, as they did not live.
- [x] Reports `FRAME_HITCH` chunks per state (F4 §7; they are not in the database).
- [~] **Check:** a session recorded through X1 replays to the same decisions; z differences reported.
**Done Wed 11, 15:03: `0676fe8`.** Live cut vs offline on `07343b5d`/`742ec49a`: same counted windows and decisions 18/18, |dz| ≤ 0.13; plain replay 36/36 identical. The X1-recorded check moves to J4 (no multimodal session yet). X3 must write `EEG_STATUS` `payload.status` = `PROCESS_DOWN` etc.
- [x] **Stop:** Sebas OK, Wed 11 16:00.

### [x] X3 · fallback, emulated (S) · D-F6-174
`live.py`, `state.py`, `scripts/synthetic_aura.py` (pause option), tests.
- [x] `EEG_STATUS` (connected, lost, recovered, process down); `BEHAVIOR_FALLBACK` mark; > 60 s lost cancels the EEG for the session (§5.5); S4 alpha failing too.
- [x] Heartbeat distinction: fresh with no valid epochs is not "process down"; stale is, and the backend writes it (D-F6-171).
- [x] Emulated: stream stops pushing (cap off, Bluetooth); outlet gone (AURA closed); `live.py` killed.
- [x] **Check:** in each case the session goes on with behaviour and is marked. **Real cases: J3.**
**Done Wed 11, 15:21: `ccbfe26`.** `app/eeg/status.py`; `fallback` in the decision's `eeg` block; `not_counted_reason` for S4 / > 60 s. Emulated: AURA killed → LOST, `live.py` killed → PROCESS_DOWN, > 60 s → LOST_OVER_60S. 417 tests. Live with A8's restart.
- [x] **Stop:** Sebas OK, Wed 11 16:00.

### [x] X4 · lure columns (S) · D-F6-143
Migration `0017`, `project_event`, test.
- [x] `option_kind`, `lure_selected`, `option_kinds` on `trials`, from the payload Unity already sends.
- [x] Test: lure and no-lure trials project correctly; old sessions unaffected.
- [x] **Stop.** Sebas OK, 10 Nov.
**Done Tue 10 (moved up):** migration 0017; projected trials filled from their events (269, 3 lures chosen); up/down/up same function. 397 tests.

### [ ] X5 · A-20, LSL privacy
- [~] Try (a) `.cfg` in AURA's executable folder, (b) PC off the lab network; synthetic stream, no cap.
- [x] Check (b) keeps Link, AURA, LabRecorder, `autorun` and `live.py` working. **Seeing it from another PC needs someone at that PC.**
- [x] Result in the draft, for a decision.
**Wed 11: (b) passes (Sebas, 17:56, offline: script 5/5, Link, LabRecorder only this PC, AURA opens); Play test session `9ce593d8` deleted. Waits for D-F6-193 on the board.** Prepared 17:26. Offline script in the scratchpad (draft has the path and steps); (a) needs someone at another lab PC. Found: another `AURA` stream on the lab network (host Manuela); our readers filter by hostname. Not applied: no `lsl_api.cfg` written.
- [ ] **Stop.**

### [x] X6s · substitution condition 1 without overlapping meanings (S) · D-F6-181 (2) · before X6a
`tools/kanji_metrics.py` (`hard_clash`, a check, export) → `kanji_content.json`; `backend/app/pretest/rules.py` (`_hard_clash`); tests of both. Commit as content (D-F6-62/122).
- [x] `hard_clash` also fails when two meanings **share a word** (computed: *rice*/*rice field*) or one **includes** the other (an explicit `MEANING_INCLUDES` list, since no string shows it: *child*/*person*, *woman*/*person*, *shellfish*/*fish*; *thing* does not go in (precision of D-F6-181, 10 Nov). Both rules in one function, used by the table and the check of the nominal sets.
- [x] The contract exports the clashing meaning pairs (`meaningClashes`, keyed like `similarity`); the pre-test's `_hard_clash` reads them. **Without this, two substitutions in a row can still bring 田 and 米 together**: the table only covers one substitution.
- [x] The five nominal sets pass the new rule (no overlap among their own members).
- [x] Regenerated table vs today's, in the draft. Dry run on 10 Nov (child/person only): 94 → 93 entries, only C 牛 loses 子 (8 left); woman/person and shellfish/fish do not change the table (one substitution), **no experimental kanji without a substitute**. If the real run leaves one empty: **stop, tell PM, nothing further.**
- [x] Tests: `kanji_metrics` (child/person and rice/rice field clash; the table drops 子 for 牛); pre-test (with 田 already in the effective set, 米 is not offered). Backend suite green.
- [x] **Stop.** Sebas OK, 10 Nov.
**Done Tue 10 (moved up):** `53f52c3` + seed `0d6956d`; 94 → 93, only C 牛 loses 子 (8 left), no orphan; nominal sets pass; `meaningClashes` = 女人 人子 田米 貝魚; the pre-test no longer offers 米 after 田 (it did in sets A and C). 396 tests.

### [x] X6a · T1 official lists (S) · D-F6-168, §16.2 and §16.3
`tools/kanji_metrics.py` → `kanji_content.json`, TMP font asset; commit as content.
- [x] `LURE_T1` as §16.2 (10 of the sets change; reserve unchanged).
- [x] "Sin relación" as an explicit table of the 35 of §16.2 instead of the greedy choice (4 of the reserve change); `provisional` true only for ⚑ metric (月, 竹, the reserve).
- [x] `check_lures` clean. The components rule of §16.3 stays out this week.
- [x] Font asset filled with the new characters and committed with the content; S0 prewarm leaves it byte-identical; X29 green.
- [x] Harness green.
**Done Wed 11, 15:28: `719c9be`, seed `8570a5a`.** Font 246 → 259, second prewarm byte-identical; harness 110/110.
- [x] **Stop:** Sebas OK, Wed 11 16:00.

### [x] X6b · T2/T3 official lists, active (S) · §16.4 · **second to cut**
`tools/kanji_metrics.py` → `kanji_content.json`, font asset, `TrialSequenceGenerator.ActiveLureTypes`, `SessionFlowRunner` card sizing, harness; commit as content + lures (D-F6-131).
- [x] Font asset with the new characters **in this same commit** (as X6a). T2 and T3 strong and unrelated of the 35 (学 in katakana), **from §16.4 as it is in `docs_proyecto/`: final, with the six changes of 10 Nov** (人 robot, 手 neck, 石 brick, 門 window, 糸 needle, 学 play; D-F6-181 (3)). Categories stay in the document.
- [x] D-F6-181 (1) (no part, whole or material as the T2 strong lure) is a content rule: no code; the current pairs already meet it.
- [x] `check_lures`: T2/T3 present for all, distinct, and none is a taught meaning or reading of the pool (never two correct).
- [x] Answer cards also sized from the lure texts.
- [x] Harness: half of each type per block, never two correct, same trials across conditions; X29 green.
**Done Wed 11, 16:12: `e33abf6`, seed `bb80c93`.** check 0 failures (by mora); font 259 → 285; harness 110/110. Spec v1.4 point 4 to PM in the draft.
- [x] **Stop:** Sebas OK, Wed 11.

### [x] X7 · reserve 16–20 (M) · **first to cut**
- [x] FBX and the four images of `pistas/`, as sets A–C (D-F6-160); 18 and 19 with +90° X at the root. Harness only: **the headset look moves to Thu or Fri, after the cap.**
**Done Wed 11: 16–25 `e8d784a` (16:33), 26–30 `cb64881` (17:23; hints official at 17:20).** 29 is v010. Harness 112/112. Headset look after the cap (18/19 face, 21–24, 17 F2).
- [ ] **Stop.**

### [x] X8 · close (draft, Dudas, `tasks/`)
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

### [x] A4–A7 · Unity: no event lost on a disconnect (S) · D-F6-186 (4)–(7) · **re-timed 12 Nov: code on approval → ≈ 12:20; Stop ≈ 12:30–12:55, limit 13:10** · one Unity commit, exception to the VR freeze (D-F6-122)
`unity-client/Assets/Scripts/Networking/SessionCommunicationClient.cs` only; harness case N3 in `Assets/Editor/Phase2TestHarness.cs`. The commit body says it is the D-F6-186 exception (like D-F6-74).
- [x] A4: `SendOrQueue` sends only with `_isConnected && _socket.State == WebSocketState.Open`; otherwise queue.
- [x] A5: `OnApplicationQuit` with a non-empty queue writes it to `Logs/ws_queue_<session>_<utc>.json` and `Debug.LogError` with the count (and the dropped count).
- [x] A6: `OnOpen` drains the queue whenever it is not empty, first connection too, in order; `RECONNECTED` only on a real reconnect, as today.
- [x] A7: `OnMessage` with `type == "ERROR"` -> `Debug.LogError` with `Detail` (backend half done in A3, `45d1260`).
- [x] Harness: N3 written (queue -> JSON, order kept, dropped count, session id). **114/114 PASS** in the Editor (12 Nov).
- [x] **Check in the Editor (Sebas, Stop):** *Done 12 Nov on `567e730b`, which ran **`STATIC`** (flat): S7 and S8 cuts, 11 + 12 flushed, 0 dropped, 20 + 15 trials complete. Not exercised: the adaptive path and the quit dump (N3 only).* **`BEHAVIOR_ADAPTIVE`** (Sebas, 12 Nov), so the S7 cut also tests the queue with adaptation events; synthetic stream not needed. Note: `ADAPTATION_DECISION` is written by the backend, so while it is down no decision arrives; what Unity queues is the trial events plus `ADAPTATION_SKIPPED` (TIMEOUT) / `ADAPTATION_APPLIED`. Check those arrive in order after the flush and that decisions resume on the next trial. `docker compose stop backend` in S7 and again in S8, start it again: no trial missing in `trials`, events in order, `RECONNECTED` after the flush; quit with the backend down -> the JSON in `Logs/` and the count in the console. Session deleted afterwards if it is a test one.
- [x] Commit `d2f1fc1` (message shown first), `graphify update .`. J2 confirms it in the headset.
- [x] **Stop:** passed (Sebas, 12 Nov ≈ 12:30).

### [x] J1 · synthetic end to end (M) · after the A4–A7 Stop, **≈ 12:55–13:25, limit 13:30** (C1)
- [x] `07fb239` `backend/scripts/synthetic_aura.py`: add seeded noise (and a slow amplitude drift) so S6 has SD > 0 and z exists (found #8). One small commit; the 10 Hz sine stays.
- [x] *`be75faa0`, 12:56; S4 alpha failed with the synthetic stream, so no window counted (see draft).* Editor, `MULTIMODAL_ADAPTIVE`, synthetic stream, `autorun` as in the real session. S1 → S7 at least (G allowed after S4 complete).
- [x] *Rerun `5d752e08` (13:15, `d66a0e1`: synthetic alpha up in S4): alpha passed, 12/20 windows counted (2 VETO), C1 median 17.6, max 26.4, last 15.9 ms. Arrival max 54.7 s noted.* **Done when:** every S7 decision has its EEG block in the `ADAPTATION_DECISION` payload (window, `eeg_effect`, `EEG_STATUS`); `verify_eeg.sql` runs on it.
- [x] *C1 latency PASS: median 13.5, max 26.3, last 13.4 ms; 0 > 1500, 0 after next; EEG read measured apart, max 14.5 ms.* **Latency (Sebas, 12 Nov):** from `decision_latency_ms`, report in the draft the **median**, the **max** and the **last S7 trial's** latency. **Pass:** median ≤ 300 ms and max ≤ 1000 ms. **Stop and tell Sebas before J2** if any decision is > 1500 ms or arrives after the next `TRIAL_STARTED`.
- [ ] Test session kept until J5 (C1 evidence), then deleted with Sebas's OK.
- [x] **Stop:** passed (Sebas, 12 Nov ≈ 14:20): C1 PASS with `5d752e08`.
- [x] *Late epoch (54.7 / 70.4 s), read from the DB at 14:30: it is epoch 0 (S1/S2). `live.py` cuts nothing until the S3 offset exists (S4 entered + 1 s), so every S1–S3 epoch is cut in one batch then; epoch 0's lag ≈ S4 entry − its end (47.7 s / 60.6 s) plus the batch's own time. No S7 window can touch it. Recorded, not fixed; checked again in J2 and J4.*

### [x] P0 · offline kit for J2/J3 (no code) · **while Sebas cannot do an Editor Stop (from ≈ 12:20); ready and re-tried by 13:50** · D-F6-193
During J2 and J3 the PC is off the network: this chat cannot be reached. Everything Sebas needs goes in the draft, under "Jue 12 · sin red".
- [x] Operator list for J2: D-F6-153 (Blender closed) + M7 + D-F6-179 (`autorun` log growing before S3; "eyes open" line) + **D-F6-193: Ethernet out and Wi-Fi off before the cap (Part B, step 4b); back on when `autorun` prints *both streams recorded*.**
- [x] Operator list for J3: per case, its own session, `autorun` relaunched, S4 complete, G after, EEG counted in one S7 window before cutting (console line to look for), then the cut (cap off / AURA closed / Bluetooth off); what to note (time of the cut, case, session id).
- [x] Copy-paste commands that work offline: session ids of the day, `autorun`, `verify_eeg.sql` via `docker compose exec db psql`, a short SQL per J3 case (`EEG_STATUS` lost, `BEHAVIOR_FALLBACK`, heartbeat fresh). Tried once against the J1 session.
- [x] Where each Stop is written while offline (a line in the draft per session); this chat reads them after reconnecting.
- [x] *Done 14:27 (late): backend restarted (nothing from T4), `/health` ok, `docker compose port db 5432` = 127.0.0.1:5432, both P0 SQL files re-run on `5d752e08`, same output; `git status` clean after the docs(tasks) commit.* **13:40–13:50:** `git status` clean (except what T4 parked), every commit of the day in, backend restarted once with T4, `/health` ok, `graphify update .` done. **Network off ≈ 13:50**, before the cap.

### [ ] T4 · EEG staff decisions (**≈ 12:30–13:40, in parallel with the Editor runs**) · only what has a number in §4 (D-F6-191 (2))
- [x] *14:26: the board mirror (12:02) ends at D-F6-194; nothing from the EEG staff numbered. J2 runs with the current rules; J4 replays J2 with what comes later, declared (Sebas, 12 Nov).* Waits for PM to record the decisions (≈ 12:30). Nothing from the meeting is applied without a number.
- [ ] Each decision its own commit and test; rule changes recompute from the XDF (D-F6-156); `rules-v2` byte-identical (C5 rerun if `decide()` is touched).
- [ ] **Deadline 13:40:** one `docker compose restart backend` with everything committed, `/health` ok, P0 commands re-tried. What does not fit by 13:40 is parked uncommitted and goes after J4: J2 then ran with the rules before it, and J4 replays J2 with the new ones (declared).
- [ ] **Stop** (Sebas) before the network goes off.

### [x] J2 · cap, S1 → S9 in the headset · **14:00, offline** (D-F6-191 (3), D-F6-193)
- [ ] Same list as M7 plus D-F6-179 and D-F6-193 (the P0 list). Condition `MULTIMODAL_ADAPTIVE`; T1 and T2/T3 lures on (X6b done), declared. New lure characters (incl. 26–30 if in the set) and card sizes seen in the headset. A4–A7 seen: no `ERROR`/queue lines in the console.
- [x] *`a8e825e0`: `EEG_CONFIRMED` applied (S7-007), but its XDF has two `AURA` streams, so `fill_from_xdf` failed (exit 1). `bf5ceee3`: complete, 3 `EEG_VETO`. C1 holds in both. S3 offset None in both (1/5 taps). See draft 16:20.* **Done when:** at least one decision with `EEG_CONFIRMED`, `EEG_VETO` or `EEG_LED`, applied and explained (F4 §5).
- [ ] None -> forced state in the Editor, real signal confirms or vetoes; **declared as such**.
- [ ] **Stop:** Sebas writes it offline (P0); this chat reads it after reconnecting.

### [x] J3 · **out, D-F6-196 (not done, not moved to Fri; declared)** · three real fallbacks, one S7 each (D-F6-174), after J2 and not replacing it · **offline**
For each case its own session in `MULTIMODAL_ADAPTIVE`: same list as J2, `autorun` relaunched, its own XDF.
- [ ] Reach S7 with **G**, but **S4 complete** (no G in S4). If S6 is short, the reference falls to S4 eyes open, marked (D-F6-73).
- [ ] **Before cutting:** the EEG has counted in at least one S7 window (visible in `autorun`'s console).
- [ ] Case 1: cap off. Case 2: AURA software closed. Case 3: Bluetooth off.
- [ ] **Check, each case:** the session goes on with behaviour; `EEG_STATUS` lost and `BEHAVIOR_FALLBACK` in the database; heartbeat still fresh (the process did not die). Sebas runs the P0 SQL offline; this chat confirms after reconnecting.
- [ ] A case that does not fit moves to Fri morning, and PM is told (D-F6-191 (3)).
- [ ] **Stop:** written offline; read after reconnecting.

### [x] J4 · replay of J2 · **after reconnecting**
- [ ] First: read the J2/J3 notes and confirm the J3 checks from the database; `fill_from_xdf` for each session if `autorun` did not.
- [x] *`bf5ceee3`: 20/20 decisions equal; EEG block differs in 5/20 (arrival margin), no decision changed. `a8e825e0` not replayable (two `AURA`).* `replay` of J2: same decisions as live; every `EEG_LED` read one by one (F4 risk 8). If T4 landed after J2, a second replay with the new rules, declared.
- [x] **Stop:** J2 and J4 approved (Sebas, 12 Nov 16:33).

### [ ] J5 · freeze and close · **checklist: `docs_proyecto/Checklist_Congelamiento_Reglas_12nov.md`** (PM)
- [x] *In the draft, J5 section (16:50).* **§2, conditions C1–C8**, each marked in the draft with its evidence: C1 = J1, C2 = J2 (or the forced state, declared), C3 = J4, **C4 = the four defaults of D-F6-174 and T1's (index with SD 0 → `UNAVAILABLE`) reviewed against J2**, C5 = `rules-v2` byte-identical, C6–C8 Sebas/PM (only noted).
- [x] *36/36 identical at `053740e`.* **C5:** `replay --json` of the 18 adaptive sessions (own version and `--version behavior-v2`) against the reference kept in `Claude outputs/referencia_replay_rules_v2_10nov/` (36 files, captured before T2): 36/36 identical.
- [x] *Read from the code at `053740e`, in the draft.* **§3, every parameter with its value** in the draft, read from the code at the commit to tag (not copied from the checklist): §3.1 epochs, quality, drop rules (F4 §6), P7 window, A-7, reference, offset; §3.2 confirm/veto, lead (D-F6-184/185), cap (`MAX_CHANGES`), defaults, **T1 default: the EEG counts but the index the state reads has no z (SD 0 in the reference) → `eeg_effect` = `UNAVAILABLE`, behavioural decision** (`concordance.py:49` theta for `OVERLOADED`, `:54` EI for the rest; test `test_the_index_the_state_reads_missing_is_unavailable`; duda 5, checklist row added by PM), `eeg_effect`, O4 of `EEG_LED`; §3.3 heartbeat, process down, **arrival margin (measured Wed)**, the > 60 s rule; §3.4 lures active on the dry run, seed, operation lists.
- [x] **C9:** audit fixes 1–7 done (commits), A4–A7 tested in J2; D-F6-187 applied or why not. **Note in C9: the A4–A7 Editor Stop (`567e730b`) ran in `STATIC`, not `BEHAVIOR_ADAPTIVE` (Sebas, 12 Nov).**
- [x] *Proposed: `eeg-rules-freeze-2026-11-12` on the J5 docs commit; waiting for Sebas's OK.* Tag proposed (name and commit), **created only with Sebas's OK**.
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

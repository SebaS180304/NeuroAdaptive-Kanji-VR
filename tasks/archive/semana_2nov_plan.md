# Implementation Plan: week of 2 – 6 Nov 2026 (F4 S2 · integrate the EEG)

Written Mon 2 Nov 2026. **Fri 6 replanned on Fri 6 Nov, aligned up to D-F6-159, approved by Sebas (D-F6-159)**. Order: K0a → (K0b only if its gate holds) → K1 → F0 → F1 → F2 → F3, Stop after each; Mon–Thu sections aligned up to D-F6-131 (`Estado_Actual.md`). **Approved by Sebas, 2 Nov (D-F6-132)**: the live LSL reader tries Docker for 30 min, else runs on the PC; a lure trial counts in the estimator window like any other, only `lure_selected` and `option_kind` stay out of the decisions; synthetic `AURA` for Monday's stop; LSL4Unity + liblsl.
Last week's plan is archived in `tasks/archive/semana_26oct_{plan,todo}.md`; its open items
are carried over or dropped in the last section.

## Sources of truth
- **`Claude outputs/docs_proyecto/Estado_Actual.md` (the board) comes first.** A decision
  exists only with a number in its §4. This week: D-F6-123 to D-F6-131.
- `Planteamiento_Tecnico_F4.md`: §2 (components, tables), §4 (the S2 week and its "done
  when"), §7 (`verify_eeg.sql`), Registro 2 Nov (F4 S1 summary, P7/P9/A-7, FRAME_HITCH).
- `Propuesta_Trampas_T2_T3.md` §2.1 and §2.4; `Metricas_Dificultad_Kanji_Fase2.md` §15.2
  (provisional T1 list, D-F6-130).

## Week rules
- **Since the tag `vr-freeze-2026-10-30`, every Unity commit says in its body whether it is
  F4 (D-F6-74), a correction, or content (with its decision).** Lures are their own
  exception (D-F6-71, D-F6-118, D-F6-131).
- Every day ends with a **Stop**: Sebas's OK before the next day's `/build`.
- One change per commit, message file in Downloads, shown to Sebas first; nothing on main.
  `graphify update .` after code changes. Backend changes go live with
  `docker compose restart backend`, between sessions.
- Each day closes with `tasks/` up to date and `Claude outputs/Borrador_Plan_Fase6_9_<date>.md`
  with "Dudas para PM" or "Sin dudas · <date>".
- Cut order if time runs short (D-F6-123): reserve kanji and the mascot in the portal go
  first. F4 S2, lures, consent v1 and spec v1.4 are never cut.

## Dependency graph

```
L1 Unity marker outlet (+FRAME_HITCH) ─┬──────────────▶ L4 Editor stop (XDF with 2 streams)
L2 eeg_sessions (0010) ──▶ L3 lsl_reader ┤                     │
L5 LabRecorder RCS name ───────────────┘                      ▼
                                      T1 preprocess + epochs + eeg_epochs (0011)
T2 perf diagnosis (Profiler) ──▶ W5 apply approved fix          │
W1 lure fields (kanji_metrics) ──▶ W2 lures in trials + contract│
L1 ──▶ W3 S3 step (channels blue, sync taps)                    │
L1 + L3 ──▶ W4 S4 markers + EEG_BASELINE_RESULT ────────────────┤
                                                                ▼
                     H1 Thu headset: S3/S4, offset/drift, alpha, black screen, sample loss
                                                                ▼
                     F1 Fri full S1→S9 with EEG + lures ──▶ F2 verify_eeg.sql (A-7)
```

## Architecture decisions (proposed; open ones are in "Questions for Sebas")
- **One marker point in Unity.** `SessionCommunicationClient.SendSessionEvent` already sees
  every session event; the LSL outlet mirrors it there (event type, `trial_id`, `event_id`,
  session clock) instead of touching each controller. Only what is not a session event today
  gets its own push: sound onsets (if not already events), S3 sync taps, S4 eye segments,
  `FRAME_HITCH` (from `FrameRateLog`, which already times every frame).
- **Stream:** name `UnityMarkers`, type `Markers`, 1 string channel (JSON), irregular rate,
  source id fixed per machine. Library: LSL4Unity + liblsl x64 (named in F4 §2.1; the
  only new dependency in Unity).
- **Backend:** new package `backend/app/eeg/` (F4 §2.2). New deps: `pylsl`, `pyxdf`, `numpy`,
  `scipy`. Timestamps always from LSL's corrected clock (`dejitter`, `clocksync`; P9).
- **Montage** lives in `eeg_sessions` (AURA sends no channel labels): fixed default CH1 Fp1,
  CH2 F3, CH3 Fz, CH4 F4, CH5 Cz, CH6 P3, CH7 Pz, CH8 P4, with the day's changes and reason.
- **`eeg_epochs` keeps which 1 s chunks are clean** (5 flags per epoch), not only the
  fraction: P7 counts each clean second once even when two overlapping epochs share it
  (D-F6-127), and `verify_eeg.sql` can only do that with per-chunk data.
- **P16 (1–40 Hz denominator)** goes in now as the band constant and one tested
  relative-power helper; `features.py` (indices per epoch) is the S3 week (F4 §5).
- **Lures:** `kanji_metrics.py` writes per kanji and per trial type `lure_strong` and
  `unrelated` (with `provisional`) into `kanji_content.json`; T2/T3 stay empty. Unity builds
  the 4 options as [CORRECT, LURE_STRONG, IN_SET, UNRELATED] in half the trials of each
  *active* type, seeded and identical across conditions; only T1 is active.

## Mon 2 · markers and recording

- [ ] **L1 (F4):** LSL marker outlet in Unity, mirroring `SendSessionEvent`, plus
  `FRAME_HITCH` with its duration when a frame passes 50 ms (D-F6-129).
- [ ] **L2:** migration `0010` with `eeg_sessions` (fixed CH1–CH8 montage by default).
- [ ] **L3:** `app/eeg/lsl_reader.py`: reads an XDF (and a live inlet) with the corrected LSL
  clock and fills the stream info into `eeg_sessions`.
- [ ] **L5:** unique XDF name via LabRecorder's remote control
  (`sub-<p>_ses-<session>_task-<condition>_run-<n>`, run counts up). Fallback if it does not
  fit today: manual field and a box in the S3 checklist.
- [ ] **L4 Stop:** a session in the Editor leaves one XDF with `AURA` and `UnityMarkers`,
  and its `eeg_sessions` row.

## Tue 3 · epochs and performance

- [ ] **T1:** `preprocess.py` (1–40 Hz band-pass, 60 Hz notch, parameters stored per
  session) and `epochs.py` (5 s every 2.5 s, 1 s chunks; drops blink, amplitude, flat,
  `HEAD_AWAY` open, the second after a sound onset and **a chunk with a `FRAME_HITCH` >
  100 ms**; GOOD/ACCEPTABLE/POOR), migration `0011` with `eeg_epochs`. P16 helper.
- [ ] **T2 (correction, diagnosis only):** Profiler on (a) the headset hourglass when S2
  starts and (b) the slow frames of S4's eye-closing animation (R2: 333 frames > 20 ms,
  worst 321 ms). Proposal without applying it (preload/async load, shader warm-up, no
  instantiation on the spot).
- [ ] **Stop:** epochs of a recorded session with their quality, the 29 Oct artifact blocks
  POOR; diagnosis of both hitches and the proposed fix.

## Wed 4 · lures, S3 and S4

- [ ] **W1:** `kanji_metrics.py` writes the lure fields per kanji and type; T1 strong lure =
  §15.2 (provisional); T1 "unrelated" = a kanji outside the pool with minimum similarity,
  one per kanji, marked provisional. Rule check in `--verify` (above all: never two correct).
- [ ] **W2:** generic lure trials for T1/T2/T3 with a per-type switch, only T1 on;
  `option_kind` and `lure_selected` in the contract (`EVENT_CONTRACT.md`, backend schema,
  marker). Harness cases.
- [ ] **W3 (F4):** S3 new step: operator confirms all channels blue in AURA's software; sync
  test, 5 trigger taps on Cz at the start and 5 in S9, each a marker.
- [ ] **W4 (F4):** S4 markers for eyes open/closed start and end; `EEG_BASELINE_RESULT`
  (alpha ratio closed/open in P3, Pz, P4 and whether it passes ≥ 1.2).
- [ ] **W5 (correction):** the performance fix Sebas approves on Tue. Harness green.
- [ ] **Stop:** lures in S6–S8 in the Editor; S3 and S4 with their markers; no hourglass in
  S2 and no hitches in S4.

## Thu 5 · cap (Sebas and the MIRAI student)

- [ ] **H1:** S3 and S4 in the headset with EEG: offset and drift from the Cz peaks against
  the tap markers (±100 ms, drift < 50 ms); alpha ratio in the session.
- [ ] **H2:** block 3 pending from 29 Oct: 2 min with a black screen, with start/end markers.
- [ ] **H3:** EEG sample count around every `FRAME_HITCH` left: no lost samples.
- [ ] **Stop:** results written for the EEG chat (`Claude outputs/`).

## Fri 6 · cap (replanned 6 Nov; board §1 Vie 6, D-F6-149 to D-F6-155)

Already in the code since Thu 5 pm: `SOUND_S = 0.5` (`4196699`, D-F6-149), the sync text for
one person (`9d47670`, D-F6-150), `autorun` (`01e10ac`, D-F6-152). **Changed 6 Nov (Sebas):**
before the cap, (K0) find and fix why the CJK font asset keeps showing as modified, then (K1)
researcher keys instead of the components' menus (D-F6-158). New code today: K0, K1 and
`database/verify_eeg.sql` (F2).

```
K0a font: diagnose ──Stop──▶ K0b font: the fix Sebas picks ──Stop──┐
K1 researcher keys, letters (D-F6-158) ──Stop──────────────────┤
                                                                   ▼
F0 pre-cap list (D-F6-153) + autorun waiting ──Stop──▶ F1 session S1→S9, STATIC, set B
   ──Stop──▶ F2 autorun output + offset/drift + verify_eeg.sql (b5bcf5bd and today's)
   ──Stop──▶ F3 week close: F4 S2 criterion + Dudas para PM (Borrador_Plan_Fase6_9_6nov.md)
```

- [ ] **K0a · font, diagnosis only (correction, follows D-F6-139).** What I know: the asset
  `NotoSansCJKjp-Regular SDF` is **Dynamic** (`m_AtlasPopulationMode: 1`,
  `m_ClearDynamicDataOnBuild: 1`). `FontPrewarm.Run` (W5, `4b2f1ea`) adds every content
  character in S0 with `TryAddCharacters`. In the Editor, TMP writes those glyphs into the
  tracked `.asset` and its atlas, and something clears them again: right now the working copy
  has empty glyph and character tables, while the commit has two (`…` and `_`). So the file
  flips on every Play and every clear. To confirm, starting from a clean checkout, `git status`
  after each of: open Unity → Play/Stop → close and reopen Unity → a build. Write down which
  step writes and which clears. **Stop:** Sebas sees the cause and picks a fix.
  Candidates, in my order of preference:
  1. **Static atlas** made from `FontPrewarm.Characters(content json)` (ASCII + UI symbols +
     every content character), committed once. Nothing writes at runtime. The S2 rasterizing
     cost of T2 goes away for good, and the prewarm stays only as the "no glyph for" check.
     Cost: the atlas must be regenerated when content adds characters. A harness case fails
     if a content character is missing from it.
  2. Keep it Dynamic, but rasterize into a **runtime copy** made in S0 and set it as the
     default font. The tracked asset is never touched. It keeps the runtime cost that W5 moved
     to S0.
  3. Commit the cleared state and ignore the flips (`skip-worktree`): it hides the change,
     it does not fix it. Not recommended.
- [ ] **K0b · font fix** (correction): the option Sebas picks. Done when: clean checkout →
  Play S0→S2 → Stop → restart Unity → `git status` clean. No glyph warnings in S0. S2 starts
  without the hourglass (W5's 390 ms first frame or better). Harness green. One commit.
  **Stop.**
  **Gate before the cap (D-F6-159):** K0b goes in before the cap only if (1) the harness is
  green with the "every content character has a glyph" case, (2) Sebas runs S0 → S2 in the
  headset with no glyph warnings, and (3) there is still time before the cap. If any of the
  three fails, K0b is not committed before the session: the session uses Thu 5's font (the
  committed asset, with the working-copy diff discarded as on Thu 5), and K0b moves to after
  the session or Mon 9. K1 goes next either way.
- [ ] **K1 · researcher keys instead of component menus (F4, D-F6-74; D-F6-158, which brings
  D-F6-154 forward and widens it).** Opening a component's menu freezes the headset for
  1.6–3.9 s (A-22). Each of the five actions gets a letter key, read in
  `SessionFlowRunner.Update` through `Keyboard.current` (Input System, as `DebugTrialPresenter`
  and `DemoDirector` do). **No F-keys.** Each key acts only in its own state, calls the method
  that exists today, and is logged:

  | Key | Action (method today) | Acts only when |
  | --- | --- | --- |
  | **G** | Force advance (`ForceAdvance`) | a state is waiting (S1, S3) |
  | **E** | EEG ready (`ConfirmEegReady`) | S3 |
  | **T** | Sync tap without controller (`RequestSyncTap`) | Editor without headset, sync test of S3/S9 |
  | **B** | Black screen block 3 (`RunBlackBlock`) | after S9 (the session chain has ended) |
  | **C** | Force complete assembly (`KanjiAssemblyController.ForceComplete`) | an assembly is running (S5) |

  1. **Clash check first, written down before any code** (D-F6-158). In the code, the debug
     and demo keys are 1–4 and H (`DebugTrialPresenter`) and L, M, H and digits
     (`DemoDirector`); `SessionFlowRunner` reads no keys. G, E, T, B and C are not among
     them. I still check that neither component is active in `JapaneseLearningStudio`, and
     in the Editor (Shortcut Manager + a real press in Play with the Game view focused) that
     none of the five letters fires an Editor shortcut. W/E/R/T and friends are Scene-view
     tool keys and should not fire with the Game view focused, but that needs a real check.
     If a letter clashes, I propose another letter (never an F), write it in the draft, and
     wait for Sebas.
  2. One small static map, key → action + allowed state, so the harness can test it without
     the Input System. `Update` only reads the five keys and calls the map.
  3. Remove the five `[ContextMenu]` attributes. The methods stay public. "Start session
     chain" and the debug/probe menus stay, since no session uses them.
  4. The S0 log prints the key list with "Game view in front" (D-F6-154). The operator steps
     of the draft replace "menu" with the letter.

  **Done when:** a harness case passes (each key → its action in its state; in another
  state, or with no key, nothing happens); the harness is green; in Play in the Editor
  (headset by Link, no cap), pressing each key in its state gives no `FRAME_HITCH` > 100 ms;
  the five menu entries are gone. One commit (body: F4, D-F6-158). **Stop.** If it is not
  done before the cap, the session follows D-F6-153: menus only outside S4–S8.
- [ ] **F0 · before the cap.** Unity restarted just before; Profiler closed; Blender, ChatGPT,
  Firefox and VS Code closed on that PC (D-F6-153). Inspector: `condition = STATIC` (already
  in the scene), **`newSessionKanjiSet = B`** (the scene has no override; the default is A),
  `createNewSessionOnPlay` and `eegStep` on, `baselineTimeScale = 1`. Backend up without
  `--reload`. `autorun` in a terminal says *waiting for a new session*. AURA all blue;
  LabRecorder open, not recording. **Stop:** Sebas confirms the list.
- [ ] **F1 · session.** The operator steps for Fri 6 in `Borrador_Plan_Fase6_9_5nov.md`. Sync
  per D-F6-150: the assistant alone, controller ring on Cz's housing, trigger at the same
  instant, 5 in S3 and 5 in S9, spike checked in AURA before the next. With K1: E in S3 and
  B after S9, no menus. Without K1: menus only in S3 and after S9, opened and closed fast
  (D-F6-153). **From S4 to S8 nobody touches the
  PC, switches window or opens a menu, and nobody talks to the participant** (D-F6-152).
  Block 3 before Stop, in the same XDF. **Stop:** session `COMPLETED`, XDF closed, autorun done.
- [ ] **F2 · after.** Backend code, after the cap. The session doesn't wait for it.
  - **F2a · autorun output:** *both streams recorded*; epoch counts with rule B; the
    `eeg_sessions` alpha ratio from `baseline.py` (official, D-F6-155).
  - **F2b · epochs record their rule; `b5bcf5bd` recomputed (D-F6-156).** `epochs.save` also
    writes `sound_s` and `epochs_version` (a constant in `epochs.py`, bumped when a rule
    changes) into `eeg_sessions.filter_params`, which already exists as jsonb, so no
    migration is needed. Then `python -m app.eeg.epochs b5bcf5bd…` with rule B, which
    rewrites its `eeg_epochs`; the XDF is the source, so nothing is lost. Test: `save` stores
    both keys. Done when `b5bcf5bd`'s and today's rows say `sound_s = 0.5`. One commit.
  - **F2c · offset and drift into `eeg_sessions` (D-F6-157).** New `app/eeg/sync.py`, made
    from the 5 Nov scratch analysis. For each `SYNC_TAP`, find the Cz peak near the marker.
    A tap without a clear peak does not count. **Offset** = median of (Cz peak time −
    marker time) over the valid S3 taps. **Drift** = median over S9 − median over S3. With
    fewer than 3 valid taps in S3 or in S9, the columns stay empty and the reason is kept.
    Where to keep the reason and the per-tap detail: `eeg_sessions` has `sync_offset_ms` and
    `sync_drift_ms` but no column for it, so I propose migration `0012` with a
    `sync_detail jsonb` (taps, valid count, peak times, threshold, reason). The "clear peak"
    threshold is not set in D-F6-157: **proposed, for Sebas** a search window of ±500 ms
    around the marker and a peak > 5× the noise (MAD) of the 2 s before it (5 Nov: ≈ 480 µV
    peak-to-peak vs ≈ 40 at rest). The value used is stored in `sync_detail`. Tests: a
    synthetic XDF with known lags gives the expected offset and drift; 2 valid taps give
    empty columns with a reason. `autorun` runs it after `epochs`. Done when today's session
    has offset and drift (or empty with a reason) and `b5bcf5bd` has empty columns with
    "no clear peak". One commit for 0012 + `sync.py` + autorun.
  - **F2d · `database/verify_eeg.sql`**, read-only, in the style of
    `verify_adaptation.sql` (`-v sid=`), with what of F4 §7 exists today: XDF + both streams
    + row; offset/drift in range (±100 ms, drift < 50 ms) or empty with its reason; the rule
    the epochs were made with; S4 alpha passes; S6 ≥ 6 non-POOR; % of S7 windows where the
    EEG counts (≥ 2 non-POOR, ≥ 5 clean seconds counted once) ≥ 60 % (A-7, D-F6-127), as a
    cross-check against the EEG chat's 61 % for `b5bcf5bd`; usable epochs per ESL level;
    chunks dropped by `FRAME_HITCH` per state. Multimodal lines (`EEG_LED`, …) print "n/a,
    no MULTIMODAL session yet". Run on `b5bcf5bd` (after F2b) and today's. One commit.
  - **Stop:** Sebas sees both outputs.
- [ ] **F3 · week close** in `Claude outputs/Borrador_Plan_Fase6_9_6nov.md`: done, findings,
  F4 S2 criterion (§4: one complete session with EEG aligned to the events and quality per
  window in the database) met or not, with the evidence; "Dudas para PM" (or "Sin dudas ·
  6 nov"). `tasks/` up to date. **Stop:** Sebas's OK; the week's plan is archived Mon 9.
- **Not today:** spec v1.4 review (moved to Mon 9, board §1); D-F6-151 (`window.py` ≥ 15 s)
  week of 9 Nov; A-20 diagnosis.

## Checkpoints
| When | Sebas checks | Blocks |
| --- | --- | --- |
| Mon pm | XDF with two streams + `eeg_sessions` row | T1 on real recordings |
| Tue pm | epochs and quality; hitch diagnosis and fix proposal | W5 |
| Wed pm | lures S6–S8, S3, S4 in the Editor; no hourglass, no S4 hitches | Thu cap session |
| Thu pm | offset, drift, alpha, black screen, sample loss | Fri full session |
| Fri am, 1 | font cause (K0a) | the font fix |
| Fri am, 2 | `git status` clean after Play + restart (K0b) | the cap |
| Fri am, 3 | each letter in its state, no hitch > 100 ms (K1, D-F6-158) | the cap |
| Fri am, 4 | pre-cap list (D-F6-153), autorun waiting | the session |
| Fri, after S9 | session COMPLETED, XDF closed, autorun done | the analysis |
| Fri pm | autorun output, offset/drift, `verify_eeg.sql` on both sessions | week close |
| Fri close | F4 S2 criterion + Dudas para PM | S3 week (multimodal) |

## Risks and mitigations
| Risk | Impact | Mitigation |
| --- | --- | --- |
| The backend runs in Docker Desktop: LSL discovery (multicast) may not reach the container | High: no live reader, no live `EEG_BASELINE_RESULT` | Mon, 30 min spike with `KnownPeers`; if it fails, the live reader runs as a host process with the same `app/eeg` code and writes to Postgres on 127.0.0.1:5432 (question 1) |
| No cap on Monday: the Editor stop has no real `AURA` stream | Stop not checkable | A synthetic outlet named `AURA` (8 ch, 250 Hz) from a test script; the real one is Thu (question 3) |
| LabRecorder's remote control is off or its syntax differs from what I expect | No unique name | Check against LabRecorder's docs/source before coding; fallback = manual field (P9 allows it) |
| liblsl native plugin in Unity (x64, Editor + Link) | L1 slips | It is the only new Unity dependency; test in an EditMode case with an in-process inlet first |
| The perf fix touches S2/S4 after the freeze | Regression | Correction commits only, whole harness green, Sebas sees S2 and S4 in the headset on Wed |
| Lure trials and the estimator: "outside the decisions" (D-F6-71) is not explicit on whether a lure trial's error counts in the window | Different adaptations | Until PM answers, the estimator is untouched; lure fields are only recorded (question 2) |
| 29 Oct XDFs have no markers | T1 test is partial | Artifact blocks are checked by time ranges from the F4 S1 summary; marker-based drops tested on synthetic data and on Monday's XDF |

## Fri 6 · risks
| Risk | Impact | Mitigation |
| --- | --- | --- |
| The sync taps leave no spike again | No offset/drift: the first line of `verify_eeg.sql` is empty, F4 S2 only partial | The assistant checks each spike in AURA before the next (D-F6-150); if none shows in S3, repeat before "EEG ready" |
| `b5bcf5bd`'s epochs were made with rule A (1 s) | Its P7 % is not rule B | Question 6: re-run `epochs.py` on it, or report it as rule A |
| STATIC has no adaptation decisions to mark the S7 windows | No windows for the P7 % | `verify_eeg.sql` builds them from 3 consecutive answered S7 trials, as the estimator does; checked on `b5bcf5bd` first |
| A static atlas misses a character that content adds later | A blank glyph in the board | The S0 "no glyph for" warning stays, plus a harness case over the content json |
| K0 or K1 is not ready before the cap | The session waits | The session doesn't wait for them: without K0b, the font diff is discarded as on Thu 5 (it is generated data); without K1, the D-F6-153 menu rule applies |
| A letter is also an Editor shortcut with the Game view focused | The key triggers something else | Checked before coding (K1 step 1); on a clash, another letter is proposed, never an F (D-F6-158) |
| "Clear peak" threshold too strict or too loose | Valid taps dropped, or noise counted as a tap | Threshold stored in `sync_detail`; the EEG chat recomputes from the XDF as a cross-check (D-F6-157) |
## Questions for Sebas (Fri 6)
5. ~~Font asset~~ → Sebas, 6 Nov: find the cause and fix it first (K0).
6. ~~Re-run `b5bcf5bd`~~ → **D-F6-156** (F2b).
7. ~~Offset/drift in `eeg_sessions`~~ → **D-F6-157** (F2c).
8. ~~`sync_detail` and the clear-peak threshold~~ → **D-F6-159** (1): migration `0012` with
   `eeg_sessions.sync_detail` jsonb (taps, valid ones, peak times, threshold used, reason);
   clear peak = searched within ±500 ms of each `SYNC_TAP` and > 5× the MAD of the 2 s
   before; the threshold used goes into `sync_detail`.

## Questions for Sebas (before the `/build` of Mon 2; answered, D-F6-132)
1. **Live LSL reader:** OK to try the container first (30 min) and, if it cannot see the
   streams, run `app/eeg` live as a host process on the PC? Wed needs it for
   `EEG_BASELINE_RESULT`.
2. **Lure trials in the engine** → goes to PM as "Dudas para PM" today: does a T1 with lure
   count in the estimator's 3-trial window like any other trial (accuracy, RT), with only
   `lure_selected` kept out? I do not change the estimator until it has a number.
3. **Monday's stop without the cap:** OK with a synthetic `AURA` stream for the XDF check?
4. **LSL4Unity + liblsl** as the Unity dependency (F4 §2.1 names it): OK?

## Carried over / dropped from last week
- **B4c SDF morph:** not this week; may enter before 13 Nov as an improvement (D-F6-115).
- **F1 two failing Playwright tests (26 Oct):** still "another day".
- A1, B4, B5, B6, C7, C8, J9 and their sub-boxes: done last week (stale boxes); not carried.
- Not this week: retention block R (D-F6-125, week of 16–20 Nov); set A M colour (content);
  T2/T3 lure activation (lists from Content, week of 9 Nov).

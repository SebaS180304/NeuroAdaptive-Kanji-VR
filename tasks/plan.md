# Implementation Plan: week of 2 – 6 Nov 2026 (F4 S2 · integrate the EEG)

Written Mon 2 Nov 2026. **Aligned up to: D-F6-131** (`Estado_Actual.md`). **Approved by Sebas, 2 Nov (D-F6-132)**: the live LSL reader tries Docker for 30 min, else runs on the PC; a lure trial counts in the estimator window like any other, only `lure_selected` and `option_kind` stay out of the decisions; synthetic `AURA` for Monday's stop; LSL4Unity + liblsl.
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

## Fri 6 · cap

- [ ] **F1:** full S1 → S9 with EEG and lures in the headset.
- [ ] **F2:** `verify_eeg.sql` with the A-7 checks (D-F6-127) and what of F4 §7 exists today.
- [ ] **F3:** review of spec v1.4 (PM sends it Thu); my notes as a draft, against
  `Cambios_Spec_v1_4.md`.
- [ ] **F4:** week log draft in `Claude outputs/`.
- [ ] **Stop:** F4 S2 criterion met (`Planteamiento_Tecnico_F4.md` §4): one complete session
  with EEG aligned to the events and quality per window in the database.

## Checkpoints
| When | Sebas checks | Blocks |
| --- | --- | --- |
| Mon pm | XDF with two streams + `eeg_sessions` row | T1 on real recordings |
| Tue pm | epochs and quality; hitch diagnosis and fix proposal | W5 |
| Wed pm | lures S6–S8, S3, S4 in the Editor; no hourglass, no S4 hitches | Thu cap session |
| Thu pm | offset, drift, alpha, black screen, sample loss | Fri full session |
| Fri pm | F4 S2 criterion | S3 week (multimodal) |

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

## Questions for Sebas (before the `/build` of Mon 2)
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

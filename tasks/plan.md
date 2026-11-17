# Implementation Plan: week of 16 – 20 Nov 2026 (dry run → unfreeze → pilot ready)

Written Mon 16 Nov 2026; **updated 16 Nov night, aligned up to D-F6-221 · approved (D-F6-221); Tue 17 09:00: D-F6-222, X8 moves to Tue 17 end of day, after BR2** (automation in two parts, manual recording for the pilot start: D-F6-221; one S6 threshold: D-F6-220; bad channel: D-F6-216; sync: D-F6-217; S6 and reference: D-F6-218; session automation: D-F6-219, **proposal waiting for Sebas's OK**; two `AURA`: D-F6-206; two-visit test: D-F6-207; block R inputs: D-F6-208; end of the free recall: D-F6-212; one bad channel: D-F6-213; sync spread: D-F6-214). **Approved by Sebas (16 Nov). No code today; `/build` starts Tue 17 after V4 and U0.**
Last week's plan is archived in `tasks/archive/semana_9nov_{plan,todo}.md`; its open items are carried over in the last section.

## Sources of truth
- **`Claude outputs/docs_proyecto/Estado_Actual.md` first:** §1 rows "Semana 16–20 nov" and "Lun 16 (agenda)"; §4 D-F6-198 (freeze), D-F6-200 (grid phase), D-F6-204 (week), D-F6-206 (two `AURA`), D-F6-125, D-F6-190, D-F6-207 and D-F6-208 (block R), D-F6-202 and D-F6-222 (X8); §1 row "Mar 17 (agenda)".
- Today's operator kit: `Claude outputs/Borrador_Plan_Fase6_9_13nov.md` (today's times, docs only).
- `Checklist_Congelamiento_Reglas_12nov.md` (frozen values), `Consentimiento_Protocolo_Sesion_v1.md` Parts B and C (session steps, block R in the visits).

## Week rules
- **Rules stay frozen until V4 on Tue 17** (D-F6-198, D-F6-204). Until then: no code; findings recorded, not fixed.
- After the unfreeze, still **no rule value changes** (D-F6-200 (1) says so explicitly); a rule change needs its own number.
- One change per commit, message shown first; nothing on main. `graphify update .` after code. Backend changes go live with `docker compose restart backend`, between sessions.
- Each task ends with a **Stop** (Sebas's OK). Every day closes with `tasks/` up to date and the draft with "Dudas para PM" or "Sin dudas · <date>".
- Participants appear **only by code** (D-F6-205), in the draft, the database and commits. **The dry-run participant's data is kept:** the dry run is visit 1 of the block R test (D-F6-207).
- **Block R inputs (D-F6-208):** the board records them as delivered on Mon 16 (UI/UX `Contenido_UI_Bloque_R.md`, Content's 5 new kanji per set, web design's V1.12 recall form). BR0 checks each one in the mirror: what is there is used from the start; what is missing, or still pending Sebas's validation (V1.12 is marked *Pending* in `design-system.md`), is a declared placeholder until Wed 18, end of day.
- **Free recall (D-F6-212):** the researcher ends part 1 when the participant says they are done; **≈ 2 min is only a guide, no clock** in the VR or the portal. The researcher says *"Anything else you remember?"* once, when the participant goes quiet; never repeats, corrects or hints.
- **Rule values still frozen after U0 for the EEG quality:** a bad channel is handled by protocol (D-F6-213); any rule change for it waits for a number on Thu 19.

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
                     ──► X8 content 31–35, end of day (D-F6-222): only kanji with FBX + 4 validated hints
Wed 18                                                  │
                     BR3 portal recall ──► BR4 short visit (S1–S2 → R → close) ──► BR5 Thu kit
                     inputs from UI/UX, Content, web design by end of day (D-F6-208)
Thu 19               BR6 swap in what arrived ──► BR7 visit 2 test, dry-run participant (D-F6-207)
                     ──► CH1 bad-channel rule (D-F6-216), proved on the dry-run XDF on this PC
                     ──► X8b what X8 left out on Tue (D-F6-222; may slip to Fri)
Fri 20  go/no-go (PM / Sebas) ◄── everything above
Fri 20 morning       AU1 pre-session check + AU4 end-of-session (D-F6-221), tested on the dry-run XDF on this PC ──► AU0 only if time is left
Sat 21 – Mon 23      Sebas away: no rehearsal, no buffer
Tue 24 morning       what did not finish on Fri 20 ──► afternoon: first participant, **manual recording** (today's kit) + AU1 and AU4
later in the pilot   AU2 + AU3 + AU6 rehearsal with Sebas on a day without a participant; pass → automated recording from then on (sessions labelled by recording path)
```

G1 and G2 go first on Tue: both touch `fill_from_xdf` and are small. S1 and S6 are small and touch the same EEG files, so they follow G2 while that code is fresh; their Unity part shares BR2's Editor Stop. Block R has a hard date (visit 2 on Thu 19). CH1 goes after BR7 (D-F6-216) and before the automation, which reuses its measure in the S3 warning. X8 is content only: on Tue it closes the day after BR2, with whatever kanji have their 4 hints validated (D-F6-222); the rest goes to Thu 19 after BR7. The automation (D-F6-219, D-F6-221) is split: AU1 and AU4 do not change how a session is recorded, so they enter from Tue 24; AU2/AU3 change the recording and wait for a full rehearsal with Sebas on a pilot day without a participant.

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

**X8 · content 31–35, end of the day, after BR2 (D-F6-222, D-F6-202).** Content, exception to the VR freeze (D-F6-62, D-F6-122); no rule touched. Same path as X7 (`e8d784a`, `cb64881`). ≈ 1 h.
- **Gate, per kanji (read-only first):** FBX in `KanjiLessonAssets/NN_*/export/` (all five there and approved, D-F6-222) **and** the four official hints `R_NN_*_{P,F1,F2,M}.png` in `NN_*/pistas/`, **validated by Sebas** (Registro of `Tabla_Autoria_Kanji_Fase2.md` in the mirror, or Sebas's OK written in the draft). Other files in `pistas/` are drafts. A kanji with < 4 validated hints does not enter: it goes to X8b on Thu 19 after BR7. None complete → X8 does not run today.
- **Map:** 31 金 `KANJI_KIN`/`31_KANE` · 32 茶 `KANJI_CHA`/`32_CHA` · 33 馬 `KANJI_UMA`/`33_UMA` · 34 魚 `KANJI_SAKANA`/`34_SAKANA` · 35 鳥 `KANJI_TORI`/`35_TORI`.
- **Change:** `SetAObjectsIntegration.cs` gets `Reserve4` with only the complete kanji and a menu "reserva 31-35" (priority 309) that runs `Integrate("R", …)` and `IntegrateHints("R", …)`, all or none like a set (D-F6-26). Root turn per each FICHA (31 金 faces the player, no turn; check the other four). FBX, `.meta`, prefabs, hints and `KANJI_*.asset` links come from the menu, not by hand.
- **Harness:** `X18r4` checks the ones that entered against their FICHA envelopes (within 1 cm, centred pivot, no collider, no animation, `BLENDER_FBX`); X20 counts 30 + n AUTHORED. The PLACEHOLDER examples of X18b and X20 use `KANJI_KIN` today: if 金 enters, they move to a kanji still without object and images (a 31–35 one left out, or else `KANJI_ICHI`, which has neither; if `ICHI` is used elsewhere with another meaning, ask). **Done when:** all PASS, count before → after in the commit.
- **Commit:** `content(unity): reserve 31-35 objects and hints (X8, D-F6-222)`, listing which entered and which moved to Thu 19; then `tasks/` and the draft. Harness only; the headset look is later, as X7. **Stop.**

### Wed 18 · AI workshop (time to be confirmed) · block R continues

**BR3 · free recall in the portal.** The researcher marks recalled kanji for the evaluated session. V1.12 (`marking`, `saved`, `nothingRecalled`, `saveError`; "Save: nothing recalled" distinct from not saved) if Sebas has validated it, else a plain placeholder form with the same states (D-F6-208). **No clock and nothing that paces the 2 minutes** (D-F6-212). The form does not advance the VR: that is the `R` key. The write goes where the portal already writes (decided in BR0). Playwright smoke. **Stop.**

**BR4 · short visit: S1–S2 → block R → close (≈ 20 min, no cap).** The flow D-F6-207 asks for on Thu, and the same path visit 4 uses (D-F6-125). Session creation with the evaluated session; Unity skips S3–S10 and closes the session cleanly. Tested end to end in the Editor with a test participant (deleted after, as `SIM_1311`). **Stop.**

**BR5 · Thu kit (docs).** In the draft: PC list, network off (D-F6-193 applies to every session with a participant), Inspector values for visit 2 (participant code from V3, evaluated session = the dry run, short visit), S1–S2 with the D-F6-203 sentence, block R steps for the operator (part 1: instructions, the participant recalls aloud, the researcher marks in the portal; when they go quiet, *"Anything else you remember?"* once; when they say they are done, Game view in front and **`R`**; no clock, ≈ 2 min only as a guide; never repeat, correct or hint, D-F6-212), **debriefing at the end** (consent Part B step 3, D-F6-192, ≈ 3 min: this participant has no visit 4, and whoever finishes early gets it when leaving), close, SQL after. **Stop:** Sebas reads it.

**End of day:** inputs due from UI/UX (texts), Content (5 new kanji per set, `Metricas_…` §16) and web design (recall form) (D-F6-208).

### Thu 19 · visit 2 test, then X8b

**BR6 · swap in what arrived late (morning, only if something was still a placeholder).** Content and texts into `kanji_content.json` (no code); V1.12 if Sebas validated it after BR3 and it fits. Harness re-run; each item marked real or placeholder in the draft. **Stop.**

**BR7 · visit 2 test (D-F6-207).** Same participant as the dry run, code only; 3 days after visit 1. Short visit: S1–S2 → block R on set A → debriefing → close. **Done when:** recall, yes/no and 15 MC answers stored against the dry-run session; nothing from block R in `adaptation_decisions`; findings recorded. If the participant cannot come: **Fri 20 morning**, last resort **Mon 23** with the interval declared. **Stop.**

**X8b · what X8 left out on Tue (D-F6-222, after BR7).** Only if a kanji of 31–35 missed Tue's gate. Same gate and same path as X8 (add it to `Reserve4`, extend `X18r4`, move the PLACEHOLDER examples if needed); harness all PASS (count before → after). Content commit. **Stop.**

**CH1 · persistently bad channel (D-F6-216), after BR7.** Rule values numbered; one implementation for live, replay and `fill_from_xdf`.
- Rule: a channel is persistently bad when **> 20 % of its samples exceed 100 µV in 2 consecutive 30 s bins**; from then to the end of the session it leaves the amplitude criterion and the indices. **At most 1 channel per session** (a 2nd → the session's EEG does not count). **Fz** out → theta frontal `UNAVAILABLE`, Engagement Index with the other 6. **Fp1 keeps its own rule** (D-F6-75), never this one. Out after S6 → the reference is recomputed with the remaining channels.
- Where: one function in `epochs.py` that walks 30 s bins of session time and returns `(channel, from_t)`; `make_epochs` drops that channel from the amplitude check from `from_t`; `features.py` uses `EI_CHANNELS` minus it, and theta `None` if Fz; `reference.py` recomputes with the same channels. `live.Buffer` runs the same function on what it has (bins close as time passes), so live and offline agree. Migration **0020**: `eeg_sessions.bad_channel`, `bad_channel_from_ms`; the decision's `eeg` block carries `bad_channel`.
- Tests: synthetic stream with F3 over 100 µV in 25 % of two bins → excluded from the end of the 2nd bin, not before; one bin only → not excluded; two channels → session not counted; Fz → theta `UNAVAILABLE`; Fp1 never excluded; live = offline on the same signal; `rules-v2` byte-identical (C5).
- **Proof on the dry run, on this PC (D-F6-216):** XDF copied into the backend container's `/tmp` (same PC, as in V3) and deleted after; `replay --xdf` and a dry recompute (no write) give **P7 and A-7 with F3 excluded**, beside today's 0/18. `fill_from_xdf` re-run on `65af2fe4` only with Sebas's OK (it rewrites its epochs).
- Size ≈ 4–5 h. If it does not finish on Thu, X8b (if any) moves after AU1/AU4 (Fri 20, or Tue 24 morning, D-F6-221 (4)); CH1 is needed by the pilot. **Stop.**

**Session automation (D-F6-219): separate section below.** Waits for Sebas's OK; never during a session.

### Fri 20 · go/no-go (PM, Sebas)
This chat hands in: what is live (G1, G2, S1, S6, block R, CH1, X8), what is still placeholder, BR7 result, open findings, `tasks/` and the draft up to date; the automation plan and whether Sebas approved it.

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

**AU1 · pre-session check, `python -m app.eeg.preflight` (≈ 2 h) · Fri 20 morning, first.** On the manual path: LabRecorder's GUI running is expected (OK), not a WARN; `LabRecorderCLI` is not checked until AU2. One command, one line per check (OK / WARN / FAIL), exit 0 only with no FAIL:
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

**AU4 · end of session (≈ 2 h) · Fri 20 morning, after AU1.** On the manual path the operator still presses Stop; `autorun` keeps waiting for the file to close (as today). After the file closes: `lsl_reader` → `sync` → `epochs` (today); then the **four SQL** of kit §8 (`verify_eeg`, `verify_adaptation`, `verify_projection`, `p0_j3_fallback_check`) through `docker compose exec`, each saved to `backend/logs/<session>-<name>.txt`; then a **summary** printed and saved (`<session>-summary.txt`): Play → S9 duration, accuracy per state, A-7 live and from the XDF, sync (offset, robust spread), S4 alpha, S6 source and epochs, bad channel if any, decisions and changes, any FAIL/OUT/SHORT line from the SQL. On the manual path the summary ends by reminding to close LabRecorder's GUI; with `LabRecorderCLI` (later) it has already exited. Exit 0 only if every step ran. Tests: the summary from fixed rows. **Proof on the dry run, on this PC:** the four SQL and the summary on `65af2fe4` (read-only); the processing step re-run on it only with Sebas's OK, because it rewrites the dry run's epochs (after G1, S1, CH1 they differ from Monday's).

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
| Inputs delivered but not yet in the mirror, or V1.12 not validated | Med | BR0 lists what is real; placeholders only for the gaps; BR6 swaps late arrivals; the rest declared in BR7 |
| A channel loses contact mid-session in the pilot (as F3 on 16 Nov) | High | Protocol of D-F6-213: fix any red channel before S4; a loss from S4 to S8 is accepted and declared; the behavioural fallback covers the session (proved in `65af2fe4`); a rule change only with a number on Thu 19 (Q1) |
| Visit 2 participant cannot come Thu | Med | Fri 20 morning, then Mon 23 with the interval declared (D-F6-207) |
| G1 changes the epochs A-24 is decided on | Med | Old sessions keep the null origin = today's cut; V3 figures labelled with their grid |
| G2 drops a session's offline epochs | Low | Only with two local `AURA`; the live epochs stay and the log says why (D-F6-206) |
| Hints of 31–35 not validated by the end of Tue | Low | X8 takes only the complete kanji; the rest is X8b on Thu 19 after BR7 (D-F6-222) |
| CH1 on Thu pushes X8b | Low | X8b is content only and moves to Fri; the pilot needs CH1, not X8b |
| 15 S6 trials make each visit ≈ 40 s longer | Low | Inside the 1 h 15 blocks of D-F6-209 |

## Open items
- Questions 1–5 of 16 Nov closed (D-F6-206 to D-F6-208, D-F6-213, D-F6-214).
- PM question of 16 Nov night closed by D-F6-220 (one threshold, 15; S6 chooses the reference, it does not fail A-7).
- Week plan and automation approved (D-F6-221).

## Carried over from last week
- Audit (D-F6-186, after the dry run): Unity dead code (5 Phase-1 stubs and `XRTrackingProbe`, 253 lines, with their `.meta`; unused events); own `ADAPTATION_SKIPPED` reason for a refused ESL change. Not before the pilot unless block R is done.
- Later, unchanged: B4c SDF morph (D-F6-115); two Playwright tests failing on the 26 Oct data; set A M images in the headset; trial-level theta from the XDF (F4 §5); components rule of §16.3 in `check_lures` and classic pairs for the reserve (Content).

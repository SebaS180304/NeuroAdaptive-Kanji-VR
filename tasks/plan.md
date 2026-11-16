# Implementation Plan: week of 16 – 20 Nov 2026 (dry run → unfreeze → pilot ready)

Written Mon 16 Nov 2026; **updated 16 Nov after 13:15, aligned up to D-F6-208** (two `AURA`: D-F6-206; two-visit test: D-F6-207; block R inputs: D-F6-208). **Approved by Sebas (16 Nov). No code today; `/build` starts Tue 17 after V4 and U0.**
Last week's plan is archived in `tasks/archive/semana_9nov_{plan,todo}.md`; its open items are carried over in the last section.

## Sources of truth
- **`Claude outputs/docs_proyecto/Estado_Actual.md` first:** §1 rows "Semana 16–20 nov" and "Lun 16 (agenda)"; §4 D-F6-198 (freeze), D-F6-200 (grid phase), D-F6-204 (week), D-F6-206 (two `AURA`), D-F6-125, D-F6-190, D-F6-207 and D-F6-208 (block R), D-F6-202 (X8).
- Today's operator kit: `Claude outputs/Borrador_Plan_Fase6_9_13nov.md` (today's times, docs only).
- `Checklist_Congelamiento_Reglas_12nov.md` (frozen values), `Consentimiento_Protocolo_Sesion_v1.md` Parts B and C (session steps, block R in the visits).

## Week rules
- **Rules stay frozen until V4 on Tue 17** (D-F6-198, D-F6-204). Until then: no code; findings recorded, not fixed.
- After the unfreeze, still **no rule value changes** (D-F6-200 (1) says so explicitly); a rule change needs its own number.
- One change per commit, message shown first; nothing on main. `graphify update .` after code. Backend changes go live with `docker compose restart backend`, between sessions.
- Each task ends with a **Stop** (Sebas's OK). Every day closes with `tasks/` up to date and the draft with "Dudas para PM" or "Sin dudas · <date>".
- Participants appear **only by code** (D-F6-205), in the draft, the database and commits. **The dry-run participant's data is kept:** the dry run is visit 1 of the block R test (D-F6-207).
- **Block R inputs (D-F6-208):** built on declared placeholders; the real texts, 5 new kanji per set and recall form arrive by **Wed 18, end of day**; what has not arrived is used as placeholder on Thu 19 and declared.

## Dependency graph

```
Mon 16  V2 dry run = visit 1 (kit) ──► V3 analysis ──► XDF to EEG chat
                                            │
Tue 17                                      ▼
        V4 close ──► U0 unfreeze ──► G1 grid origin (D-F6-200 (1)) ──► G2 two AURA (D-F6-206)
                                                                          │
                                                                          ▼
                     BR0 design ──► BR1 data ──► BR2 block R in VR (Editor Stop)
Wed 18                                                  │
                     BR3 portal recall ──► BR4 short visit (S1–S2 → R → close) ──► BR5 Thu kit
                     inputs from UI/UX, Content, web design by end of day (D-F6-208)
Thu 19               BR6 swap in what arrived ──► BR7 visit 2 test, dry-run participant (D-F6-207)
                     X8 content 31–35 (independent of BR; after BR7)
Fri 20  go/no-go (PM / Sebas) ◄── everything above
```

G1 and G2 go first on Tue: both touch `fill_from_xdf`, are small, and A-24 (Thu) is decided with figures labelled by grid. Block R has a hard date (visit 2 on Thu 19), so nothing else enters Tue–Wed. X8 is content only and goes on Thu after the visit.

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

**BR0 · block R design, read-only (≈ 45 min).** Read D-F6-125, D-F6-131/181 (lure rules apply to block R), D-F6-187/190, D-F6-207/208, consent Parts B/C, spec v1.4 if it covers R. Output: one page in the draft: states, events, tables, where each placeholder lives and how the real input replaces it (content in `kanji_content.json`, texts, form). **Stop.**

**BR1 · data path.** Migration **0019**: the session row keeps **which session it evaluates** (D-F6-190 (2)); visit 4 gets visit 3's set (D-F6-190 (1)); block R answers stored as events with their trial kind, never read by `decide()` or the window code. Validation: the evaluated session belongs to the same participant and is earlier. Tests. **Stop.**

**BR2 · block R in VR, between S2 and S3.** Yes/no recognition with 10 kanji (5 seen, 5 new: **placeholder new kanji**, declared) and 15 multiple-choice trials T1–T3 with lures, no feedback, no hints, from the evaluated session's set; instruction texts placeholder. Harness test like X7; seen in the Editor with Sebas. Unity commit says "block R, exception D-F6-125". **Stop in the Editor** (Tue evening, or Wed around the workshop).

### Wed 18 · AI workshop (time to be confirmed) · block R continues

**BR3 · free recall in the portal.** The researcher marks recalled kanji for the evaluated session; plain placeholder form until web design's arrives (D-F6-208). The write goes where the portal already writes (decided in BR0). Playwright smoke. **Stop.**

**BR4 · short visit: S1–S2 → block R → close (≈ 20 min, no cap).** The flow D-F6-207 asks for on Thu, and the same path visit 4 uses (D-F6-125). Session creation with the evaluated session; Unity skips S3–S10 and closes the session cleanly. Tested end to end in the Editor with a test participant (deleted after, as `SIM_1311`). **Stop.**

**BR5 · Thu kit (docs).** In the draft: PC list, network off (D-F6-193 applies to every session with a participant), Inspector values for visit 2 (participant code from V3, evaluated session = the dry run, short visit), S1–S2 with the D-F6-203 sentence, block R steps for the operator (recall marked in the portal; no repeating or correcting what the participant says), **debriefing at the end** (consent Part B step 3, D-F6-192, ≈ 3 min: this participant has no visit 4, and whoever finishes early gets it when leaving), close, SQL after. **Stop:** Sebas reads it.

**End of day:** inputs due from UI/UX (texts), Content (5 new kanji per set, `Metricas_…` §16) and web design (recall form) (D-F6-208).

### Thu 19 · visit 2 test, then X8

**BR6 · swap in what arrived (morning).** Content and texts into `kanji_content.json` (no code); the form if it arrived and fits in the time. Harness re-run; each item marked real or placeholder in the draft. **Stop.**

**BR7 · visit 2 test (D-F6-207).** Same participant as the dry run, code only; 3 days after visit 1. Short visit: S1–S2 → block R on set A → debriefing → close. **Done when:** recall, yes/no and 15 MC answers stored against the dry-run session; nothing from block R in `adaptation_decisions`; findings recorded. If the participant cannot come: **Fri 20 morning**, last resort **Mon 23** with the interval declared. **Stop.**

**X8 · content 31–35** (D-F6-202, after BR7). Read the `Tabla_Autoria_Kanji_Fase2.md` Registro: each of 31 金 · 32 茶 · 33 馬 · 34 魚 · 35 鳥 with FBX yes/no and hints 4/4 yes/no. Only complete ones integrated as X7 did 16–30; harness all PASS (count before → after); the rest listed. Content commit (D-F6-62, D-F6-122). **Stop.**

A-23 and A-24 are Sebas's decisions with V3's figures; this chat only supplies them (no code unless numbered).

### Fri 20 · go/no-go (PM, Sebas)
This chat hands in: what is live (G1, G2, block R, X8), what is still placeholder, BR7 result, open findings, `tasks/` and the draft up to date.

## Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| The dry run brings a pilot blocker | High | Recorded in V3 with "blocks yes/no"; fixed only after U0 and with a number |
| Block R does not fit Tue–Wed (largest piece, Wed has the workshop) | High | Nothing else enters Tue–Wed; slices in order BR1 → BR2 → BR4 are the minimum for Thu; BR3 can fall back to recall noted on paper and typed after (declared) |
| Inputs arrive late or not at all (D-F6-208) | Med | Placeholders from Tue; BR6 swaps what arrived; the rest declared in BR7 |
| Visit 2 participant cannot come Thu | Med | Fri 20 morning, then Mon 23 with the interval declared (D-F6-207) |
| G1 changes the epochs A-24 is decided on | Med | Old sessions keep the null origin = today's cut; V3 figures labelled with their grid |
| G2 drops a session's offline epochs | Low | Only with two local `AURA`; the live epochs stay and the log says why (D-F6-206) |

## Open items
- None for PM today: the three questions of 16 Nov are closed by D-F6-206, D-F6-207 and D-F6-208.

## Carried over from last week
- Audit (D-F6-186, after the dry run): Unity dead code (5 Phase-1 stubs and `XRTrackingProbe`, 253 lines, with their `.meta`; unused events); own `ADAPTATION_SKIPPED` reason for a refused ESL change. Not before the pilot unless block R is done.
- Later, unchanged: B4c SDF morph (D-F6-115); two Playwright tests failing on the 26 Oct data; set A M images in the headset; trial-level theta from the XDF (F4 §5); components rule of §16.3 in `check_lures` and classic pairs for the reserve (Content).

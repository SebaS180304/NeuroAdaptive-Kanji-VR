# Todo: week of 16 – 20 Nov 2026 (dry run → unfreeze → pilot ready)

Plan in `tasks/plan.md`. Aligned up to **D-F6-208**. **Approved by Sebas (16 Nov). No code today; `/build` starts Tue 17 after V4 and U0 (D-F6-198, D-F6-204).**
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

### [ ] V4 · close of the dry run
- [ ] F4 S3 criterion met or not, with evidence; findings with owner; draft with Dudas or "Sin dudas · 17 nov".
- [ ] **Stop:** Sebas's OK.

### [ ] U0 · lift the freeze (D-F6-204) · docs only
- [ ] `git diff eeg-rules-freeze-2026-11-12 -- backend unity-client` shows no code change; "freeze lifted at <time>" in the draft.
- [ ] **Stop.**

### [ ] G1 · grid origin live = offline (D-F6-200 (1)) · no rule values change
- [ ] Migration 0018: `eeg_sessions.grid_origin_lsl` (null allowed), up and down.
- [ ] `live.py` writes `t0` once; `epochs.fill_from_xdf` and `replay.xdf_source` pass it as `t0` when not null.
- [ ] Tests: offline epochs = live epochs (index and start) when the XDF starts before `t0`; null origin = today's output; `rules-v2` replay byte-identical.
- [ ] Restart between sessions, `/health`; `fill_from_xdf` on the dry-run session unchanged (null origin).
- [ ] **Stop.**

### [ ] G2 · two `AURA` in the XDF (D-F6-206)
- [ ] `lsl_reader.load_xdf`: repeated name → keep the stream whose hostname is this PC; two from this PC → raise with its own message (never choose by sample count).
- [ ] Callers log that raise as "not filled, live epochs kept"; live epochs untouched.
- [ ] Tests: local + foreign → local; two local → no fill; one → today's behaviour.
- [ ] `a8e825e0` run through the new pick; result noted.
- [ ] **Stop.**

### [ ] BR0 · block R design, read-only
- [ ] D-F6-125, D-F6-131/181, D-F6-187/190, D-F6-207/208, consent Parts B/C read.
- [ ] One page in the draft: states, events, tables, where each placeholder lives and how the real input replaces it. **Stop.**

### [ ] BR1 · block R data (migration 0019)
- [ ] Evaluated session stored (D-F6-190 (2)); visit 4 with visit 3's set (D-F6-190 (1)); answers as events, outside `decide()` and the window code.
- [ ] Validation: same participant, earlier session. Tests. **Stop.**

### [ ] BR2 · block R in VR (between S2 and S3)
- [ ] Yes/no with 10 kanji (5 seen, 5 new as declared placeholders); 15 MC trials T1–T3 with lures; no feedback, no hints; evaluated session's set; placeholder texts.
- [ ] Harness test; seen in the Editor with Sebas; commit body "block R, exception D-F6-125". **Stop.**

## Wed 18 · AI workshop · block R continues

### [ ] BR3 · free recall in the portal
- [ ] Researcher marks recalled kanji; placeholder form until web design's arrives (D-F6-208). Playwright smoke. **Stop.**

### [ ] BR4 · short visit: S1–S2 → block R → close (no cap)
- [ ] Creation with the evaluated session; Unity skips S3–S10 and closes cleanly; same path as visit 4.
- [ ] End to end in the Editor with a test participant, deleted after with Sebas's OK. **Stop.**

### [ ] BR5 · Thu kit (docs)
- [ ] PC list, network off (D-F6-193), Inspector for visit 2 (code, evaluated session = dry run, short visit), S1–S2 + D-F6-203 sentence, block R operator steps, **debriefing at the end** (Part B step 3, D-F6-192: no visit 4 for this participant), close, SQL after.
- [ ] **Stop:** Sebas reads it.

- [ ] End of day: inputs due from UI/UX, Content and web design (D-F6-208).

## Thu 19 · visit 2 test, then X8

### [ ] BR6 · swap in what arrived (morning)
- [ ] Content and texts into `kanji_content.json`; form if it arrived and fits. Harness re-run; each input marked real or placeholder. **Stop.**

### [ ] BR7 · visit 2 test (D-F6-207)
- [ ] Dry-run participant, code only; S1–S2 → block R on set A → debriefing → close.
- [ ] **Done when:** recall, yes/no and 15 MC stored against the dry-run session; nothing from block R in `adaptation_decisions`; findings recorded.
- [ ] Cannot come → Fri 20 morning; last resort Mon 23, interval declared. **Stop.**

### [ ] X8 · content 31–35 (D-F6-202) · after BR7 · content commit (D-F6-62, D-F6-122)
- [ ] `Tabla_Autoria_Kanji_Fase2.md` Registro read: each of 31–35 with FBX yes/no, hints 4/4 yes/no.
- [ ] Only complete ones integrated as X7; harness all PASS (count before → after).
- [ ] Incomplete ones listed in the draft. **Stop.**
- [ ] A-23 / A-24: V3 figures supplied to Sebas; no code unless numbered.

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

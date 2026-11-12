# Implementation Plan: week of 9 – 13 Nov 2026 (F4 S3 · multimodal → dry run with EEG)

Written Mon 9 Nov 2026. **Approved by Sebas, aligned up to D-F6-178; updated on 10 Nov up to D-F6-187 (audit fixes waiting for Sebas's OK); Wed reordered 11 Nov up to D-F6-189; Thu planned 12 Nov up to D-F6-193 (waiting for Sebas's OK)** (the first version's questions are answered in D-F6-171 to D-F6-178; lure lists in `Metricas_Dificultad_Kanji_Fase2.md` §16).
Last week's plan is archived in `tasks/archive/semana_2nov_{plan,todo}.md`; its open items are carried over in the last section.

## Sources of truth
- **`Claude outputs/docs_proyecto/Estado_Actual.md` comes first** (§1 agenda; §4 decisions). A decision exists only with a number.
- `Planteamiento_Tecnico_F4.md` §2.2 (modules), §2.4 (sync), §5 (the week and its "done when"), §6 (parameters), §7 (`verify_eeg.sql`).
- `Reevaluacion_EEG_Justificacion.md` §3.2, §3.3, §3.5 (rules), §4.4.1–§4.4.3 (formulas), §5.4–§5.5 (reference, P7, A-7).
- `Metricas_Dificultad_Kanji_Fase2.md` §16 (official lures).

F4 §5 (EEG staff on Mon 9) and Reevaluación §4.4.1 (5 chunks) are behind the board; PM passes that to the EEG chat. This plan follows the board.

## Week rules
- Each task ends with a **Stop**: Sebas's OK before the next one. On Wed 11 there are no headset stops (D-F6-169): the Stop is reading the result in the draft.
- One change per commit, message shown first; nothing on main. Unity commits say in their body whether they are F4 (D-F6-74), lures (D-F6-71/118/131), content (D-F6-62/122) or a correction.
- `graphify update .` after code changes. Backend changes go live with `docker compose restart backend`, **between sessions**. No `--reload`.
- Every day closes with `tasks/` up to date and `Claude outputs/Borrador_Plan_Fase6_9_<date>.md` with "Dudas para PM" or "Sin dudas · <date>".
- With the cap on: D-F6-153 list, Blender closed. No menus or window changes from S4 to S8; no block 3 (D-F6-167).
- **Cut order (D-F6-170):** reserve kanji first, then T2/T3, then block R texts and form. **Never cut:** the Tue session with the EEG staff, Thursday's multimodal, the dry run, consent; nor EEG counting in the windows, confirm/veto/lead and the fallback (F4 §8).

## What the code review found

| # | Found | Where it is handled |
| --- | --- | --- |
| 1 | `sync.py` measures at the **peak** on the filtered signal; D-F6-161 asks for the **strike onset** on raw Cz, with spread ≤ 50 ms and \|offset\| ≤ 250 ms | M1 |
| 2 | `autorun` runs `epochs` **before** `sync`, so the offset would not exist yet | M1 |
| 3 | Migration 0011 has `CHECK (cardinality(chunk_clean) = 5)`; 9 chunks would fail the insert | M2, migration 0013 |
| 4 | `verify_eeg.sql` assumes 1 s between chunks, ends the window at `completed_elapsed_ms` (the decision is at the answer), has no 15 s and no "finished" rule | M3 |
| 5 | There is no live EEG path | X1 (D-F6-171) |
| 6 | `filter_eeg` is zero-phase over the whole buffer; live it only sees up to "now" | X1/X2: one path for live and replay, cut at the same instants |
| 7 | A replay from the XDF cannot know that `live.py` was down: the signal is there, the live epochs were not | X2 honours the stored `EEG_STATUS` |
| 8 | With the 10 Hz synthetic sine S6 has spread 0, so z is undefined | M5 guards it; J1 needs a stream that varies |
| 9 | **The new lures bring 38 characters the content does not have today** (e.g. 重 犬 右, ぎ ゆ, ム ノ リ). K0b committed the font with exactly today's 246, so S0 would dirty the asset | X6a/X6b commit the font with the content; X29 stays green |
| 10 | `SessionFlowRunner` sizes the answer cards from `OptionText` only, which never sees lure texts (T2 *friendship*, *butterfly*) | X6b |
| 11 | `lure_table` picks "sin relación" greedily; §16 fixes each one, and 犬 and 文 are now strong lures but still candidates | X6a: explicit table |

## Architecture decisions
- **Live path (D-F6-171):** `app/eeg/live.py`, started by `autorun` like `baseline.py`, buffers both streams on the PC and writes each finished epoch with its indices to `eeg_epochs`. At each S7 answer the backend reads them and calls `window.py` → `decide()`. No new endpoint. After the session `fill_from_xdf` still replaces `eeg_epochs` (D-F6-156); what was seen live stays in the `ADAPTATION_DECISION` payload.
- **Heartbeat (D-F6-171, condition):** `live.py` updates `eeg_sessions.heartbeat_at` and the current EEG gap every 2 s. Fresh heartbeat with no valid epochs is "no valid epochs"; stale heartbeat (> 10 s) is "process down", and the backend writes that `EEG_STATUS` itself, because a dead process cannot. The > 60 s rule reads the same fields. 2 s and 10 s are proposals, on the J5 freeze list.
- **Window (D-F6-162, D-F6-172, D-F6-177):** an epoch counts when its centre is inside the window **and it had finished at the decision instant**, the same in `window.py`, `replay.py` and `verify_eeg.sql`. The decision instant is the answer of the 3rd trial, and the 15 s count back from it. A small arrival margin, measured in X1, covers the PC-to-database write and is applied in all three.
- **Offset (D-F6-173, D-F6-176):** median of the S3 taps, live, in replay and in `fill_from_xdf`. S9 only measures drift; S9 under 3 taps marks the session and nothing is recomputed. What `sync.py` does today with the offset is already right; only the onset changes.
- **`window.py`, `concordance.py`, `reference.py`, `features.py` are pure** and shared by live and replay. Replay feeds the XDF through the same filter-and-epoch path. Criterion: same decisions; z differences reported, not hidden (online vs offline dejitter).
- **`SessionAdaptationState` stays rebuildable:** the EEG window goes into the `ADAPTATION_DECISION` payload and `rebuild` reads it.
- **`rules-v2-mm` is a branch inside `decide()`, taken only with an EEG window.** `BEHAVIOR_ADAPTIVE` never passes one, so its path stays byte-identical. The four defaults of D-F6-174 are marked in the code and reviewed in J5.
- `clean_fraction` becomes covered seconds / 5. The "at least 2 clean chunks" of D-F6-166 is implied by ≥ 3 s covered; a test pins it, no extra branch.

## Dependency graph

```
M1 sync at onset ─▶ M2 epochs (9 chunks, D-F6-166, offset) ─▶ M3 verify + recompute b5bcf5bd/742ec49a
                                     │                                     │
                                     ├─▶ M4 features ─▶ M5 reference ─▶ M6 window ◀┘ (same counts as the SQL)
                                     │                                     │
   M7 cap Mon 18:00 (runs with whatever is committed)                      ▼
                                                  T1 concordance ─▶ T2 rules-v2-mm
                                                                           │
                                       X1 live path + heartbeat ◀──────────┤
                                                     ├─▶ X2 replay  ───────┤
                                                     └─▶ X3 fallback ──────┤
   X4 lure columns ─▶ X6s subst. ─▶ X6a T1 ─▶ X6b T2/T3 · X5 A-20 · X7 reserve     │
                                                                           ▼
                        J1 synthetic E2E ─▶ J2 cap, multimodal ─▶ J3 three real fallbacks ─▶ J4 replay ─▶ J5 freeze
                                                                                                         │
                                                                     V1 verify lines ─▶ V2 dry run ─▶ V3 analysis ─▶ V4 close
```

## Tasks

Detail, criteria and checks in `tasks/todo.md`. Sizes: S 1–2 files, M 3–5.

### Mon 9 · quality, sync, indices; cap at 18:00
| Task | What | Size |
| --- | --- | --- |
| M1 | `sync.py` at strike onset (D-F6-161); `autorun` order; block 3 text out | S |
| M2 | `epochs.py`: 9 chunks, D-F6-166 quality, offset subtracted; migration 0013 | M |
| M3 | `verify_eeg.sql` as D-F6-162/172/161; recompute both sessions | S |
| **M7** | **17:15 list · 18:00 cap** `BEHAVIOR_ADAPTIVE`, set C, no block 3 · 19:45 XDF to EEG | — |
| M4 | `features.py`, index columns filled | S |
| M5 | `reference.py`; migration 0014 | S |
| M6 | `window.py`, same counts as the SQL; **P7 figure in today's draft** (D-F6-172) | S |
| M8 | Close | — |

**The cap does not wait for the code (Sebas, 9 Nov):** 17:15 list and 18:00 cap even if M1–M3 are not done. The XDF is the source and it is recomputed afterwards (D-F6-156). M4–M6 go after the cap if needed, but M6's figure is due tonight: it may go to the EEG staff at 12:00 tomorrow (D-F6-172).

### Tue 10 · from 14:30, in parallel with the reserve (D-F6-180)
Sebas is in Blender all afternoon (reserve 2nd batch, 14:45–19:00): Stops are grouped at the end of each task and read together. The EEG staff session moved to the end of the day or Wed 11 before 13:30; nothing from it is applied until it has a number in §4.

| Task | What | Size |
| --- | --- | --- |
| T0 | `autorun` writes its output to a log file (D-F6-179 (2)); "autorun alive before S3" and the eyes-open line added to the J2/J3/V2 lists | S |
| T0b | `sync.py` anchor at the first 50 % crossing of the peak (D-F6-179 (1)); recompute `742ec49a` (unchanged) and `07343b5d` (spread ≈ 15.6 ms) | S |
| T1 | `concordance.py`, one test per row of §3.5 plus the three lead tests | S |
| T2 | `rules-v2-mm` with the D-F6-174 cases; decision fields; migration 0015; `BEHAVIOR_ADAPTIVE` byte-identical | M |
| T3 | Spec v1.4 review against the code: the four "Developer review" points and other notes, in the draft for PM; the spec is not edited | — |
| T4 | Whatever the EEG staff session produces **and has a number in §4**; if the session is Wed, after 14:30 | ? |
| T5 | Close | — |

**When T2 closes (D-F6-178):** the two `replay` runs on `678b7806-6f0d-4c6c-9673-6f1addd53701` (own version and `--version behavior-v2`) go verbatim into `Borrador_Plan_Fase6_9_10nov.md`, whatever T2's state, because Sebas records the backup video at 19:00.

**T0b, why it is small:** only the point the onset search starts from moves (peak → first 50 % crossing); noise window, threshold and "last point under it" stay (D-F6-179 (1)). On `07343b5d` S3-2 has a plateau whose maximum is at its end (337 ms), so the noise window fell inside the plateau and the onset came out 4 ms before the peak. Targets (F4 Registro 9 Nov night), S3 / S9 / drift / spread: `742ec49a` 35.3 / 52.2 / +16.9 / 18.4 unchanged; `07343b5d` 65.3 / 85.7 / +20.3 / 15.6, S3-2 → 68.7 ms. Compared in the draft before the Stop; a figure off is reported, not tuned.

**T3 (PM, 10 Nov):** point 1 from the saved `LayoutOfRecord` output with its date or commit (before 30 Oct → re-measured Thu); point 2 today; point 3 today for `concordance` and `rules-v2-mm`, Wed for X1/X2, PM corrects the spec Thu before the freeze; point 4 Wed with X6b.

**EEG staff: Wed 11 at 12:00, confirmed** (board §1). No Stops from Sebas 12:00–14:30: X1 with its Stop before 12:00; numbered answers after 14:30 and before J1. The Thu freeze does not move; cut X7, then X6b.

### Wed 11 · live, replay, fallback, lures (Benkyokai: no headset stops)
**13:30–14:30 (D-F6-178):** the demo runs `replay.py` in the backend container, which reads the repo's file. No backend restart, no migrations, and `replay.py` never half done: X2 before or after that hour.

| Task | What | Size | If time runs out |
| --- | --- | --- | --- |
| X1 | `live.py`, heartbeat (migration 0016), backend read at the decision | M | never cut |
| X2 | `replay.py` with XDF | S | never cut |
| X3 | Fallback with the synthetic stream; `EEG_STATUS`, `BEHAVIOR_FALLBACK` | S | never cut |
| X4 | Lure columns (D-F6-143), migration 0017 | S | must be before the dry run |
| X5 | A-20 (LSL privacy) | — | due before the dry run |
| X6s | Substitution condition 1: no meaning shares a word with or includes another (D-F6-181 (2)); table regenerated; the pre-test gets the same rule | S | not cut; an orphan kanji stops it and goes to PM |
| X6a | T1 official lists (§16.2, §16.3), font | S | not cut |
| X6b | T2/T3 official lists (§16.4, final with the six changes of 10 Nov, D-F6-181 (3)), active | S | **second to go** |
| X7 | Reserve 16–20 (D-F6-160), harness only; headset look moved | M | **first to go** |
| X8 | Close | — | |

**X6s (D-F6-181 (2)), why the pre-test too:** the substitution table only answers "one substitution into the nominal set". The pre-test re-checks the set after each substitution with its own `_hard_clash` in `backend/app/pretest/rules.py`, which reads the contract. *Rice*/*rice field* can only meet there (田 and 米 are both reserve), so the rule travels in the contract as `meaningClashes` and both sides use the same pairs. "Includes" (*child*/*person*) is not visible in the strings, so it is an explicit list; only the pair D-F6-181 names goes in until PM answers the Duda of 10 Nov.

### Audit fixes (D-F6-186, D-F6-187), added 10 Nov evening · waiting for Sebas's OK

They protect session data, which cannot be repeated in the pilot. Detail in `tasks/todo.md`.

| When | Task | What | Size |
| --- | --- | --- | --- |
| Tue 10 evening | **A1** | Backend only on `127.0.0.1:8000`; Editor, dashboard, `ws_smoke_test`, `autorun` checked | XS |
| Tue 10 evening, if time | X1b -> X6s -> X4 | As approved, each its own commit and Stop | — |
| Wed before 12:00 | **A2** (with X1b) | Live EEG read without the 60 s bound; test with a 75 s window | XS |
| Wed before 12:00 | **A3** | WebSocket closes a session like the PATCH (one function); backend `ERROR` logged | S |
| Wed 13:30–14:30 | — | No backend restart, no migrations, `replay.py` never half done (D-F6-178) | — |
| Wed after 14:30 | T4 -> **A8** -> X2–X6 | T4 only numbered answers; A8 checks every session-creating flow **before** changing anything | S |
| Thu before J2 | **A4–A7** | One Unity commit (exception to the VR freeze, D-F6-122): no send on a closed socket, queue saved on quit, flush on first open, `ERROR` logged; Editor test with the backend cut in S7 and S8 | S |
| Thu, J5 | C9 | Audit fixes in the freeze checklist | — |
| Later | — | Unity dead code (253 lines + 3 events), own reason for a refused ESL change | — |

**Cut order unchanged:** X7, then X6b. The Thursday freeze does not move.

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Something else reaches the backend over the LAN (another PC, a Quest build) | Med | A1 checks every known client; a standalone Quest build would need the LAN IP, and none is planned before the pilot |
| A8: the short visit 4 of D-F6-125 has no set of its own (it only tests visit 3's) | Med | A8 checks before changing anything; if so, it stops and PM decides |
| A4–A7 touch Unity two days before the dry run | Med | One small commit, Editor test with real disconnects, J2 in the headset |
| Wednesday gets heavier (A2, A3, A8 on top of X1b–X6) | High | A2 and A3 are XS/S; cut X7 then X6b as agreed |

### Wed 11 · reordered by D-F6-189 (11 Nov, 12:26) · replaces the Wed timings above

| When | Task | Stop | Restart? |
| --- | --- | --- | --- |
| now → ≈ 12:55 | **A3** WebSocket close = PATCH close, one function | Sebas | yes, grouped |
| → ≈ 13:20 | **A9** 1.5 s margin in `window.py` + `verify_eeg.sql`; **P7 old → new for the three sessions in the draft** (EEG chat → F4; presentation chat → deck at 14:30) | Sebas | yes, grouped |
| ≈ 13:20 | **One** `docker compose restart backend` for A3 + A9, only if both are committed and the backup video is recorded; else it moves to 16:00 | — | — |
| → 16:00 | **A8-flows** in the draft (no code); **X2** if it fits (committed before 13:30 or started after 14:30) | notes in the draft | no (13:30–14:30 never) |
| 15:00 · ≈ 16:30 | EEG staff; numbered decisions → **T4** before J1 | — | — |
| from 16:00 | **A8** (if the flows allow) → X3 → X5 → X6a → X6b → X7; T4 slotted in when numbered | Sebas, each | after each backend task |

**Why the order holds at 12:26:** A9 is the one with an outside deadline (deck 14:30), so if A3 has not passed its Stop by ≈ 12:55 it is parked uncommitted and A9 goes first. Neither change is needed live before J1 (code is mounted, no `--reload`, P7 is computed with a one-off `exec`), so a missed 13:20 restart costs nothing but moves to 16:00. `replay.py` does not import `window.py`: the 14:00 demo is untouched by A9.

**Cut order unchanged:** X7, then X6b. A3, A9, A8-flows, X2, X3, X5, X6a are not cut.

### Thu 12 · multimodal end to end; rules frozen at night (D-F6-191, D-F6-193)

**Re-timed 12 Nov, 11:56** (A4–A7 and J1 no longer fit before 11:00; Sebas is in the staff session and the decisions until ≈ 12:30, so no Editor Stop before then). Code only after Sebas approves this plan.

| When | Task | Stop | Hard limit | Network |
| --- | --- | --- | --- | --- |
| on approval → ≈ 12:20 | **A4–A7** code + harness N3, compiled in the Editor (no Play) | — | — | on |
| ≈ 12:20 → Sebas free | **P0** offline kit in the draft (no code); tried on a session once J1 exists | read with T4's Stop | before 13:40 | on |
| ≈ 12:30 → 12:55 | **A4–A7 Stop** in the Editor, `BEHAVIOR_ADAPTIVE`, backend stopped in S7 and again in S8 (G after S4 complete); then the commit (message shown first) | Sebas | **13:10**, else see question 1 | on |
| ≈ 12:55 → 13:25 | **J1** synthetic, `MULTIMODAL_ADAPTIVE`, C1 latency (median, max, last S7 trial) | Sebas; **J2 does not start** if any > 1500 ms or after the next `TRIAL_STARTED` | **13:30** | on |
| ≈ 12:30 → 13:40 | **T4** in parallel (backend code, no Editor): only what has a number in §4; tests, one commit each | Sebas, with J1's | **13:40 restart**; what does not fit stays uncommitted, J4 replays it, declared | on |
| 13:40 → 13:50 | `docker compose restart backend` (one), `/health`, P0 commands re-tried, `git status` clean except what T4 parked | — | 13:50 | on |
| **≈ 13:50** | **Network off** (Ethernet out, Wi-Fi off) before the cap (D-F6-193) | — | before the cap | **off** |
| 14:00 | **J2** cap, `MULTIMODAL_ADAPTIVE`, Blender closed → **J3** three real fallbacks (a case that does not fit → Fri morning) | written offline by Sebas | — | **off** until *both streams recorded* of the last session |
| after reconnecting | J2/J3 notes read and checked in the database → **J4** replay of J2 (and with T4's parked rules, declared) → J2/J3/J4 Stops together | Sebas | — | on |
| afternoon / night | §3.4 angles; **J5** freeze; tag only with Sebas's OK | Sebas | — | on |

**Order inside 12:30–13:40:** the Editor runs (A4–A7 Stop, J1) and T4 share the backend. A4–A7's Stop stops and starts it; J1 needs it up; T4 code is mounted but only goes live with the 13:40 restart (no `--reload`), so J1 runs with the rules before T4, which is fine for C1 (latency and the EEG block, not the rule values).

**Why P0 exists:** with the PC offline (D-F6-193) this chat cannot be reached during J2 and J3. Whatever Sebas needs then (lists, commands, the SQL for each fallback case, where to note each Stop) must be in the draft and tried once on J1's session before 14:00. Local services (database, backend, LSL, Link) work offline (X5 (b)).

**T4 vs J2:** J2 does not wait for T4. A numbered decision not committed and live by 13:40 is parked; J2 runs with the rules before it, and J4 replays J2 with the new rules too, declared. Rule changes recompute from the XDF (D-F6-156), so nothing is lost.

If J2 gives no EEG decision: the forced test of F4 §5, declared as such.

### Thu 12 · after the tag · E1 read-only export for the EEG chat (planned 12 Nov, ≈ 17:10; waits for Sebas's OK)

**Goal:** `Claude outputs/eeg_export_12nov/`: one CSV per table for the two J2 sessions (`a8e825e0`, `bf5ceee3`), plus a one-page README of the columns. No change to the database or to the code (the tag `eeg-rules-freeze-2026-11-12` stays the frozen state).

**How:** one SQL file, `Claude outputs/eeg_export_12nov/export.sql`, run inside `BEGIN READ ONLY` with `\copy (SELECT …) TO STDOUT WITH CSV HEADER` through `docker compose exec -T db psql`, one call per CSV. A read-only transaction refuses any write, so "no change to the database" is enforced, not only intended. Nothing goes to git (`Claude outputs/` is ignored).

| File | Source | Rows (expected) | Columns |
| --- | --- | --- | --- |
| `eeg_sessions.csv` | `eeg_sessions` | 2 | session, `sync_offset_ms`, `sync_drift_ms`, `sync_detail` (JSON: taps with `valid`, `why`, `peak_uv`, `mad_uv`, `lag_ms`), `alpha_ratio`, `alpha_passed`, `not_counted_reason`, `reference` (JSON: source, n, mean/SD per index), `filter_params`, `montage`, `stream_info`, `xdf_path` |
| `eeg_epochs.csv` | `eeg_epochs` | 282 + 237 | every column, plus `origin` (see open question 1) |
| `adaptation_decisions.csv` | `adaptation_decisions` + `session_events.payload->'eeg'` | 40 | trial, elapsed, state, cause, confidence, action, reason, levels, latency, then the whole `eeg` block flattened: `counted`, `non_poor`, `clean_s`, `ei_z`, `theta_z`, `alpha_z`, `effect`, `fallback` |
| `eeg_status.csv` | `session_events` where `event_type = 'EEG_STATUS'` | 2 (one `CONNECTED` each) | session, event id, `status`, `session_elapsed_ms`, `eeg_gap_ms`, `heartbeat_age_s`, `source` |
| `README.md` | written by hand | one page | what each file and column is, units, how each was made, the caveats below |

**Caveat found while planning (open question 1):** "the live epochs" exist only for `a8e825e0`. Its `fill_from_xdf` failed (two `AURA`), so its 282 rows are the ones `live.py` wrote during the session. For `bf5ceee3`, `autorun` ran `fill_from_xdf`, which deletes the live rows and re-cuts the whole XDF: its 237 rows are the offline cut (`live.py` had written 234). The live rows of `bf5ceee3` are gone from the database.

**Checks:** row counts as in the table; each CSV opens with its header; `adaptation_decisions.csv` has the same `counted`/`effect` as block C of `p0_j3_fallback_check.sql`; `git status` clean; nothing in the database changed (the `count(*)` of the four tables is the same before and after).

**Scope:** XS–S, no code, ≈ 30 min. No Stop in the Editor.

### Fri 13 · dry run (`MULTIMODAL_ADAPTIVE`)
V1 multimodal lines in `verify_eeg.sql` → V2 dry run with consent v1 → V3 `verify_eeg.sql`, replay, one-by-one review of `EEG_LED` → V4 week close.

## Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| T4 brings a rule change that cannot be live by 13:40 | Med | Parked; J2 runs on the old rules and J4 replays J2 with both, declared |
| Something breaks during J2/J3 and this chat is offline | Med | P0 kit tried on J1 before 14:00; Sebas notes it and it is fixed after reconnecting; a J3 case that does not fit goes to Fri morning |
| P7 with finished epochs only falls below 60 % (D-F6-172) | High: A-7 and the frozen rules | M3/M6 give the figure tonight; EEG chat and the Tue session see it before the freeze |
| Wednesday is overloaded (X1–X7) and X1 is the largest piece of the week | High | Never-cut items first, reserve and T2/T3 last; if X1 slips, Thu morning absorbs it and J1 shrinks |
| Thursday is long: J2 plus three sessions with S4 complete | High | J3 only after J2; each cut needs one counted window, and if a case does not fit, it moves to Fri morning and PM is told |
| With G, S6 is short and the reference falls to S4 eyes open | Med | Expected and marked (D-F6-73, D-F6-174); M5 tests that branch |
| The EEG staff (now end of Tue or Wed before 13:30, D-F6-180) change the quality rule, thresholds or the sync anchor | Med | D-F6-166 says it is revised on Tue; epochs recompute from XDF in minutes (D-F6-156) |
| No EEG decision on Thu (ceiling effect, 2–3 adaptations) | Med | Forced test of F4 §5, declared |
| Backend read at decision adds latency to `DECISION` | Med | Epoch rows only; `decision_latency_ms` already stored; checked in J1 |
| Disconnecting the PC from the lab network (A-20 b) also cuts local LSL | Med | Tested in X5 with the synthetic stream before anyone relies on it |
| New font characters or longer lure texts show badly | Med | Harness on Wed; seen in the headset in J2 |
| `EEG_LED` fires on fatigue | Med | Reviewed one by one (F4 risk 8) |

## Open items
- **E1, question 1 (Sebas):** `bf5ceee3` no longer has its live epochs. Export what the database has, with `origin = xdf` on those rows (recommended), or also re-cut them as `live.py` would (`live.Buffer` over the XDF, as `replay --xdf` does; computed, not what was stored live, so still not the live rows)?
1. **Sebas:** set and participant of the dry run, by Thu 12 at night (D-F6-175).
2. **Sebas:** T2 categories of §16.4, before Wed. A change is content.
3. **Sebas:** A-20 needs someone at another lab PC to see whether the streams are visible.

## Carried over from last week
- T2/T3 lures → X6b.
- Later, unchanged: B4c SDF morph (D-F6-115); two Playwright tests failing on the 26 Oct data; set A M images in the headset (needs a set A session that reaches that LAL; today's is set C).
- The other unchecked boxes in the archived `todo.md` (L1–L5, W, T2, the Fri 6 operator list) are stale ticks of work the board records as done.

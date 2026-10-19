# Implementation Plan: Research Web Portal v1 (dashboard + kanji pre-test)

Written 17 Oct 2026. Replaces the kanji pre-test plan (archived in
`tasks/archive/kanji_pretest_{plan,todo}.md`; its Tasks 1–3 are done and its open
tasks 3b, 4, 5 and 6 are folded in below).

## Sources of truth
- Skill `.claude/skills/research-dashboard-conventions/` (master copy): scope V1.1–V1.11,
  data contract, stack, design system (validation log: every screen *Validated*),
  design rules. The skill outranks the brief.
- Mockups: `https://claude.ai/artifact/Xh2oJPSpVH8hubWxNZcooL` (22 artboards).
  Design System: `https://claude.ai/artifact/NBVJKr7iEdfApEAFx1uZ4L`; its 45 color
  tokens match `design-system.md` in both themes (checked 17 Oct).
- Spec §13.1–13.2 and `Plan_Fase5a.md` D8: the inclusion criterion "no previous study
  of Japanese" was **accepted by MIRAI on 9 Oct**.

## Overview
One local web app (`dashboard/`, Vite + React + TS) served on `127.0.0.1`, over the
existing FastAPI backend. It has two parts with different deadlines:
- **Pre-test (V1.10 + V1.11):** registration and the kanji pre-test. Needed **before
  the pilot** (23 Nov), because no session can be created without it.
- **Session review (V1.1–V1.9):** read-only screens over the projected data. F7 window
  (16–20 Nov); the backend read router can go earlier.

## Architecture decisions
- **Read-only, one exception.** `/research` router, `GET` only, Pydantic schemas in
  `backend/app/schemas/research.py`, SQL views and functions called with `text()`.
  The only writes are registration (`POST /participants`) and the pre-test routes.
- **Missing data goes to the backend, never React** (skill rule 2). Three gaps found on
  17 Oct are closed with SQL in a migration:
  - V1.7 needs `verify_*` as **functions that return discrepancy rows**. Today they are
    `psql` scripts with `\echo`, and two of them check a single hard-coded session.
  - V1.7 shows when each projection error happened. `projection_errors` has no elapsed
    time and `session_events` has it only inside `payload`, so a view
    `v_projection_errors` extracts it in SQL.
  - "Not projected" needs a rule: the session has events but no `session_states` rows.
    A session with no events is shown as "No data".
- **Abandoned sessions become `ABORTED` by a database rule (decided 17 Oct).**
  - The rule is a SQL function, `abort_stale_sessions(p_idle interval DEFAULT
    '30 minutes')`. It sets `IN_PROGRESS` → `ABORTED` when the last `session_events` row
    (or `updated_at`, if there are no events) is older than `p_idle`, and returns how many
    rows it changed.
  - The `postgres:16` image has no `pg_cron`, so the backend runs the function once at
    startup and then every 5 minutes. `shortcut:` an in-process loop, not a database
    scheduler; move it to `pg_cron` if the backend stops being always on.
  - Why 30 minutes: in the 13 normal completed sessions, the longest gap between two
    events is 1.8 min, and a whole session takes 5–14 min.
  - `PATCH /sessions/{id}/state` already never takes a session out of `ABORTED`.
- **Data clean-up (decided 17 Oct), after a `pg_dump` backup:**
  - **Delete** the 23 sessions created before `JapaneseLearningStudio.unity` existed (commit
    `267d48a`, 15 Sep 12:32 +09:00). All are `CREATED`, with 323 events in total, and no
    project document cites them. Also delete participants left with no sessions, no
    pre-test answers and no consent, except `DEV_UNITY`.
  - **Do not delete** the three sessions with the 1,918 open `DUPLICATE` errors
    (`dc28e1ea`, `fc835228`, `d3f19117`). They are F3 evidence (`Evidencia_Criterios_F3.md`,
    `Plan_Fase3.md`). The errors are known: several Editor runs were stored under one id,
    and `Plan_Fase3.md` records the root-cause fix. Mark those errors resolved, with a
    note in `detail`, so V1.7 shows real problems only. Sebas confirms this split before
    anything runs (Task 0.1). **Approved by Sebas on 17 Oct.**
- **Fonts: local, via Fontsource (decided 17 Oct).** The packages are
  `@fontsource-variable/newsreader` (variable, for the optical-size axis),
  `@fontsource/public-sans` (400/500/600), `@fontsource/jetbrains-mono` (400) and
  `@fontsource/noto-serif-jp` (500). Noto Serif JP ships in `unicode-range` chunks, so the
  browser downloads only the chunks that the shown kanji need. Added to the stack table.
- **Export CSV is a menu (decided 17 Oct).** The CTA opens a popover with "Trials (CSV)"
  and "Adaptations (CSV)". In a STATIC session, Adaptations is disabled with the reason
  "No adaptations in a static session". It uses the elevated popover style that
  `design-system.md` already defines.
- **The Pause button on the kanji screen (decided 17 Oct)** goes back to the pre-test list
  without saving the current kanji. A short status notice says "Paused at [n] answered".
  Start or Resume continues at the right kanji, so the backend needs no change.
- **Registration options** follow spec §13.1 and the accepted criterion. **Approved by
  Sebas on 17 Oct** (table below). Each list is stored as a fixed `Literal` set in the API
  schema.
- **Theme:** light by default, with `[data-theme="dark"]` and `prefers-color-scheme`.
  V1.1, V1.7 and V1.8 have no dark artboard, so their dark screenshots are built from the
  tokens and are not compared to a mockup.
- **Copy change:** the inclusion notice on registration says the criterion is
  *accepted* (MIRAI, 9 Oct), not *proposed*. Same notice, same layout.

### Registration options (approved by Sebas, 17 Oct)
| Question (participant-facing) | Options shown | Stored value |
| --- | --- | --- |
| How old are you? | 18–24 · 25–34 · 35–44 · 45 or older · Prefer not to answer | `age_range`: `18-24`, `25-34`, `35-44`, `45+`, NULL |
| Have you studied Japanese before (classes, courses or self-study)? | Yes · No · Prefer not to answer | `previous_japanese_experience`: true / false / NULL |
| Have you studied kanji before? | Yes · No · Prefer not to answer | `previous_kanji_experience` |
| Have you used a VR headset before? | Yes · No · Prefer not to answer | `previous_vr_experience` |
| How often is it hard for you to keep your attention on study tasks? *(optional)* | Never · Rarely · Sometimes · Often · Very often · Prefer not to answer | `self_rated_attention_difficulty`: `NEVER`, `RARELY`, `SOMETIMES`, `OFTEN`, `VERY_OFTEN`, NULL |

How the answers are handled:
- **Previous Japanese study, Yes:** the inclusion notice appears. **Prefer not to
  answer:** the notice also appears, worded "not reported".
- **The attention question has 5 options**, where the mockup shows 4 placeholders. The
  pill group simply gets one more pill.
- **The question about how the participant feels before a session** (spec §13.1,
  "alertness/fatigue") is asked per session, not at registration. It is out of scope here.

## Dependency graph
```
0.1 backup + clean-up ─┐
0.2 abort rule (0005) ─┼─► 2.1 session list (ABORTED, not projected)
0.3 read SQL (0006) ───┴─► 2.x session screens, 3.2 quality
1.1 options (Sebas) ─► 1.2 registration rules ─► 1.5 register screen
1.3 scaffold ─► 1.4 /research/participants + V1.11 ─► 1.5 pick/register ─► 1.6 kanji + done
                                                                            │
                     1.7 session gate + kanji_items (backend) ◄────────────┘ (merge after 1.6)
                     1.8 Unity uses kanji_items
                     1.9 assembly B and C ─► 1.10 assembly of the first-choice reserve
1.3 ─► 2.1 ─► 2.2 summary ─► 2.3 timeline ─► 2.4 trials + inspector ─► 2.5 adaptations ─► 2.6 plan ─► 2.7 export
1.4 ─► 3.1 participant view;  0.3 ─► 3.2 quality
```

## Phases
- **Phase 0. Data foundation (backend and DB only):** Tasks 0.1–0.3 → Checkpoint 0.
- **Phase 1. Pre-test, end to end, before the pilot:** Tasks 1.1–1.10 → Checkpoints A and B.
  The headset checks of Tasks 1.8 and 1.9 and Checkpoint B run together on Tue 20 Oct;
  the step-by-step script is "Headset session, Tue 20 Oct" in `todo.md`.
- **Phase 2. Session review:** Tasks 2.1–2.7 → Checkpoint C.
- **Phase 3. Participant and quality, closing v1:** Tasks 3.1–3.3 → Checkpoint D.

## Risks and mitigations
| Risk | Impact | Mitigation |
| --- | --- | --- |
| A participant takes a break of more than 30 min, and the rule aborts a live session | High | 30 min is about 17 times the longest normal gap. `p_idle` is a parameter. The ABORTED status is shown, never hidden, so a false abort is visible. Pause in VR is not a feature today |
| The clean-up deletes evidence | High | Only rows no document cites. `pg_dump` first (`*.dump` is gitignored). The SQL is shown to Sebas before it runs |
| Sets B and C, and the reserve, have no assembly segments: S5 assembles placeholder parts | High | S5 does not break: placeholders, `segments_authored = false` and a warning (Task 1.8). Task 1.9 cuts B and C before the dry run; Task 1.10 the 10 first-choice reserve kanji |
| Timeline performance (hundreds of marks, ECharts) | Med | One ECharts instance with custom series; a Chrome DevTools profile only if it lags |
| F7 is the schedule's only buffer | Med | Phase 1 goes first. Phase 2 can shrink to V1.1–V1.4, as the replan allows |
| Design rules vs shadcn defaults (uniform radius, system font) | Med | Tokens override shadcn's CSS variables. The 5-tell audit runs at every checkpoint |
| Unity Editor dev Play is blocked by the session gate | Med | `DEV_UNITY` gets consent and a pre-test via the API in Task 1.7 |

## Decisions (17 Oct, Sebas)
- Registration options: approved as in the table above.
- Clean-up: delete the 23 pre-scene sessions and their orphan participants; for the 3 F3
  evidence sessions, only resolve their `DUPLICATE` errors.
- Branches: Phase 0 and Task 1.2 are committed on `feature/kanji-pretest`. Then
  `phase/7-research-dashboard` is created from its tip, and every task from 1.3 on goes
  there.
- The abort rule (30 min, run by the backend every 5 min), Pause, Fontsource and the
  Export menu are approved as described above.

## Open questions
1. ~~Assembly segments for the 20 reserve kanji: who draws them, and when?~~ Decided 19 Oct: Tasks 1.9 (B and C) and 1.10 (the 10 first-choice reserve kanji). The groups of those 10 still have to be defined from stroke order (Task 1.10)
2. MIRAI: how consent is recorded; review of the substitution ranking (carried over,
   Checkpoint A of the old plan).

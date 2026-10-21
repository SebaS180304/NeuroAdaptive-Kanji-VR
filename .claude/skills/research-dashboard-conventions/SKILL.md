---
name: research-dashboard-conventions
description: Conventions for the NeuroAdaptive VR Research Web Dashboard (React frontend + read-only FastAPI /research router, local to the lab machine). Use it before designing, implementing, reviewing or planning any dashboard screen, component, read endpoint or feature.
---

# Research Web Dashboard · Conventions

A web app that lets a researcher review, **after** a session, what happened in
the NeuroAdaptive VR prototype (kanji learning in Unity/Quest): trials,
environment, behavior, and the decisions of the F5a adaptive loop. It runs
**only on the lab machine**. v1 is **read-only** over what migrations
`0002`–`0007` project. It was built in **F6 (Oct 19–23)**, ahead of its original
F7 slot (Nov 16–20); the Learner Profile (F-PROFILE) is part of it.

**Aligned up to: D-F6-11** of `Claude outputs/docs_proyecto/Estado_Actual.md`, the
alignment board. A decision exists only with a number in its §4; if this skill
disagrees with the board, the board wins and Sebas is told.

Full context brief (Spanish, copy of the claude.ai Project):
`Claude outputs/docs_proyecto/Brief_Research_Dashboard_Dev_V1.md`.

## Status of this skill

| Part | Status | File |
| --- | --- | --- |
| v1 scope, available data and roadmap | Defined | `references/scope-and-roadmap.md` |
| Data contract | Defined (endpoints are a proposal) | `references/data-contract.md` |
| Visualization rules | Defined (visual values pending) | `references/visualization-rules.md` |
| Design system (tokens, components) | **Tokens approved Oct 16 (light + dark)**; per-screen status in its validation log | `references/design-system.md` |
| Design rules (anti-generic) + final audit | Defined (Oct 16) | `references/design-rules.md` |
| Stack, structure and repo workflow | Defined (proposal where marked) | `references/stack-and-structure.md` |
| Template for future features | Ready | `templates/feature-spec.md` |

**If a section is PENDING, do not invent values.** Use semantically named CSS
variables (`--color-condition-static`, etc.) and leave a `TODO(design)`. The
values come from the *Design System* artifact that Sebas validates.

## Rules that do not bend

1. **Read-only.** The `/research` router has `GET` endpoints only. The frontend
   never connects to PostgreSQL directly. One exception: the kanji pre-test
   screen (V1.10) posts to the existing `/participants/{id}/pretest` routes.
2. **The frontend never reads `session_events.payload`.** It reads projected
   tables, views (`v_adaptations`, `v_environment_intervals`,
   `v_trial_behavior`) and `trial_timeline()`. Missing data is added in the
   backend (projection, view or migration), never in React.
3. **NULL means not recorded, never zero** (D9). Show `—` with a tooltip. Watch
   out for the `COALESCE(..., 0)` in `trial_timeline()` for sessions recorded
   before an event type existed (see `data-contract.md`).
4. **Time is `session_elapsed_ms`** (D7), shown as `mm:ss.SSS` from session start.
5. **Non-clinical language.** Never "diagnosis", "ADHD", "deficit", "disorder".
   `learner_state` is an *estimated state* with its confidence.
6. **Pseudonymous participants.** Only `external_code` / IDs, also in exports,
   logs, fixtures and screenshots.
7. **Local, no outbound traffic.** Frontend on `127.0.0.1`, no analytics, no
   runtime CDNs, fonts bundled.
8. **Reserve what does not exist; never fake it.** EEG, HCI self-report: a
   visible reserved slot ("Available in a later version"). No sample data. The
   Learner Profile exists (migration `0007`) and goes at the top of the
   Participant View (D-F6-4).
9. **Do not restart the backend during a headset session.** There is no
   `--reload`; changes are applied with `docker compose restart backend` between
   sessions.
10. **Commits in English** (subject and body), Conventional Commits, one change
    per commit, and show Sebas each message first. Repository docs in English.
11. **After changing code, run `graphify update .`** (rule in `CLAUDE.md`).
12. **Design rules apply to code too** (`references/design-rules.md`): no generic
    fonts, no purple/indigo/violet gradients, no identical card rows, radius by
    role, soft directional shadows.
13. **Finish every iteration with the 5-tell AI-slop audit**
    (`design-rules.md` §5): name each tell found, rewrite it, then report the
    table to Sebas.

## Workflow

```
PM chat ──phase plan──▶ UI/UX chat ──mockup in Claude Design──▶ Sebas validates
   ▲                                                                  │
   │                       design spec (templates/feature-spec.md)  ◀┘
   │                                       │
   └──── roadmap updated ◀── dev chat implements with this skill
```

- **Design:** the source of truth is the *Design System* artifact plus the design
  docs in the Project. The dev chat does not decide new colors, typography or
  layout: if something is missing, it flags it and asks.
- **Implementation:** `frontend-design` for visual quality, the `shadcn` MCP for
  components, the Playwright MCP to verify in the browser against the mockup.
  Plan in `tasks/plan.md` + `tasks/todo.md` (archiving the previous plan).
- **New features:** `templates/feature-spec.md`. When one closes, move its row in
  the roadmap.

## When to read each reference

- Creating or changing a screen → `scope-and-roadmap.md` + `design-system.md`
  (check its validation log first) + `design-rules.md`.
- Requesting or exposing data → `data-contract.md`.
- Drawing a chart, timeline or table → `visualization-rules.md`.
- Creating files, installing libraries, running tests or committing →
  `stack-and-structure.md`.
- Planning something outside v1 → `templates/feature-spec.md`.

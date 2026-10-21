## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.

## How the chats stay aligned (read first)

Several Claude chats work on this project (PM, development, web design, UI/UX,
EEG, content). They stay aligned through one board:
`Claude outputs/docs_proyecto/Estado_Actual.md`.

- Read `Estado_Actual.md` before starting any task. If a plan, brief or doc
  disagrees with it, the board wins: tell Sebas, do not "fix" the other doc.
- A decision exists only once it has a number in §4 of the board. Do not act on
  a decision that is not there yet, even if it came up in a message.
- `Claude outputs/docs_proyecto/` is a read-only mirror that only the PM chat
  updates. Never write there. Hand progress over as a draft in `Claude outputs/`.
- Edit only the docs and files the board lists as yours (§3). For anything else,
  write a proposal and tell Sebas.

## Project docs (planning and design)

Plans, technical design, test scripts and the daily progress log live in a
claude.ai Project. A read-only copy is exported to `Claude outputs/docs_proyecto/`
(gitignored); start with its `README.md`. For the current phase (F6, M3 on 23 Oct)
read `Plan_Fase6.md` (F5a close in §0, Learner Profile v1 decisions in §4, criteria
in §5, daily log in §9); the previous phase is `Plan_Fase5a.md` and
`Planteamiento_Tecnico_F5a.md`.
The copy can be out of date: if it disagrees with the code, the code wins; ask Sebas
before relying on a planning detail that looks stale.

## Research Web Dashboard

Before designing, implementing or planning anything for the research dashboard
(read-only `/research` router in the backend, `dashboard/` frontend), load the
project skill `.claude/skills/research-dashboard-conventions/`. Its context brief
is `Claude outputs/docs_proyecto/Brief_Research_Dashboard_Dev_V1.md`. Visual
values come only from the validated Design System artifact; until then the
skill's `design-system.md` is marked PENDING and no colors or fonts are invented.

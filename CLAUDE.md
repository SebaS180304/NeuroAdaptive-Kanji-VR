## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.

## Project docs (planning and design)

Plans, technical design, test scripts and the daily progress log live in a
claude.ai Project. A read-only copy is exported to `Claude outputs/docs_proyecto/`
(gitignored); start with its `README.md`. For the current phase (F5a) read
`Plan_Fase5a.md` (criteria in §5, daily log in §9) and `Planteamiento_Tecnico_F5a.md`.
The copy can be out of date: if it disagrees with the code, the code wins; ask Sebas
before relying on a planning detail that looks stale.

## Research Web Dashboard

Before designing, implementing or planning anything for the research dashboard
(read-only `/research` router in the backend, `dashboard/` frontend), load the
project skill `.claude/skills/research-dashboard-conventions/`. Its context brief
is `Claude outputs/docs_proyecto/Brief_Research_Dashboard_Dev_V1.md`. Visual
values come only from the validated Design System artifact; until then the
skill's `design-system.md` is marked PENDING and no colors or fonts are invented.

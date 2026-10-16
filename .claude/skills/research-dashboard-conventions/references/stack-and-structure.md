# Stack and structure

## What the repo already has (Oct 16)

- `backend/`: FastAPI 0.115 async + SQLAlchemy 2.0 (asyncpg) + Alembic, running
  in Docker (`docker-compose.yml`, service `backend`, port 8000). Routers in
  `backend/app/api/routes/`, registered in `backend/app/main.py`.
- CORS already accepts `http://localhost:5173` (`backend/app/config.py`).
- The kanji pre-test API (`/participants/{id}/pretest`, migration `0004`) exists.
  Its capture screen is **part of the dashboard** (V1.10, decided by Sebas on Oct 16);
  there is no separate static page.
- Repo root: `package.json` with `shadcn` as a devDependency, `node_modules/` and
  `.mcp.json` with the shadcn MCP server. **There is no frontend yet** and no
  `components.json`.

## Stack (proposal)

| Layer | Choice |
| --- | --- |
| Build | Vite + React + TypeScript (strict) |
| Styles | Tailwind CSS + CSS token variables |
| Components | shadcn/ui (through the MCP) |
| Data | TanStack Query |
| Tables | TanStack Table |
| Charts / timeline | Apache ECharts |
| Routing | React Router: `/sessions`, `/sessions/:id`, `/participants`, `/participants/:id`, `/quality`, `/pretest` |
| API types | `openapi-typescript` from `http://localhost:8000/openapi.json` |
| Backend | New `research` router in the existing FastAPI app, `GET` only |
| Tests | pytest inside the container (backend); Vitest + Testing Library; Playwright e2e |

Do not add libraries outside this table without noting it in the matching
`feature-spec`.

## Structure (proposal)

```
dashboard/                      # new, sibling of backend/ and unity-client/
  components.json               # shadcn (the root MCP uses it from here)
  package.json
  src/
    api/                        # generated types + TanStack Query hooks
    components/{ui,timeline,reserved}/
    features/{sessions,session,participant,quality}/
    lib/                        # mm:ss.SSS, NULL → "—", CSV
    styles/tokens.css
  tests/e2e/                    # Playwright
backend/app/api/routes/research.py
backend/app/schemas/research.py
backend/tests/test_research_api.py
```

The dashboard runs outside Docker with `npm run dev` on `127.0.0.1:5173`. If it
later moves into `docker-compose.yml`, publish it on `127.0.0.1`, like pgAdmin.

## Commands

- Backend: `docker compose up -d`; tests **inside the container**:
  `docker compose exec backend pytest tests/test_research_api.py`.
- **The backend has no `--reload`.** After changing Python code, apply it with
  `docker compose restart backend`, **never during a headset session** (it closes
  the WebSocket; that is how session `98752f4e` dropped on Oct 7).
- Frontend: `npm run dev`, `npm run gen:api`, `npm run test`, `npx playwright test`.
- After changing code: `graphify update .` (rule in `CLAUDE.md`).

## Repo workflow

- The dev chat's plan lives in `tasks/plan.md` + `tasks/todo.md`. Today they hold
  the pre-test plan; when the dashboard starts, the previous plan is archived in
  `tasks/archive/`, as was done with S4.
- One branch per phase: `phase/<n>-<description>`. Proposal:
  `phase/7-research-dashboard`. The read router can go first on its own branch if
  the PM chat schedules it before F7.
- Commits in English (subject and body), Conventional Commits with scope
  `dashboard` or `research-api`; one change per commit, and show Sebas each
  message first.
- Repository docs (README, comments) in English. Design docs live in the
  claude.ai Project, in Spanish, with a copy in `Claude outputs/docs_proyecto/`.

## Claude Code tools

- `frontend-design` plugin.
- `shadcn` MCP (already in `.mcp.json`).
- Playwright MCP: verification and screenshots against the mockup.
- Chrome DevTools MCP: only to debug timeline performance.

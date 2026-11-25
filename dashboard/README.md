# dashboard/

The research portal and the live session monitor: React 19, Vite, TanStack Query, React Router and
Tailwind 4, in TypeScript. It reads the backend's read-only `/research` API; the only writes are the
pre-test and the free-recall form.

## Screens (`src/features/`)

| Folder | What |
| --- | --- |
| `participants/` | Participant list, participant view and the learner profile |
| `pretest/` | Registration and the kanji pre-test of visit 1 |
| `sessions/` | Session list and session view: timeline, trials, adaptations, the free recall, exports |
| `quality/` | Data quality |
| `monitor/` | The live session monitor (V1.13), second screen, 1440 × 900, read-only |
| `tokens/` | Design tokens |

Visual values come only from the validated design system (the research-dashboard-conventions skill and
`design-handoff/design-system.md`); no colour or font is invented here.

## Run

```powershell
npm ci
npm run dev       # Vite on :5173, /api proxied to the backend on 127.0.0.1:8000
npm run build     # type check + build into dist/, which nginx serves on 127.0.0.1:5300
```

In the lab the portal is the built `dist/` served by the `dashboard` container (nginx, `/api/` proxied
to the backend): run `npm run build` after a change, no container restart needed.

## Live monitor switches

The monitor's panels follow switches in `backend/.env`, off by default, applied with
`docker compose up -d backend` between sessions:

- `EEG_MONITOR_LIVE`: the per-channel signal quality (M1b);
- `MONITOR_LIVE_INDICES`: the per-epoch indices for the whole session (MI). Off, the panel shows the
  per-decision form.

## Test

```powershell
npm test          # Vitest
npx tsc -b        # types
npm run lint      # oxlint
npm run e2e       # Playwright (tests/e2e/)
npm run gen:api   # regenerate src/api/schema.d.ts from the running backend's OpenAPI
```

More in the documentation site: `docs/testing.md`.

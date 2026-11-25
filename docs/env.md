# Settings (`backend/.env`)

`backend/app/config.py` reads every setting from the environment and from `backend/.env`. The same file
serves the backend in Docker (through `env_file`) and the PC's scripts (`autorun`, `live.py`, `preflight`),
which read it from `backend\`. A variable set in the environment wins over the file.

!!! warning "Apply a change with `docker compose up -d backend`"
    Docker reads `env_file` only when it creates the container. `docker compose restart backend` keeps
    the old values. Change `.env` only between sessions, then `docker compose up -d backend`, and check the
    value in the container: `docker compose exec -T backend env`. The PC's scripts read the file again
    each time they start.

| Variable | Default | What |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | `development` turns on SQLAlchemy's SQL log and debug logging. Set `production` only in `autorun`'s window to keep its console readable. |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | see `config.py` | Database credentials; the same as the `db` service in `docker-compose.yml`. |
| `POSTGRES_HOST` | `localhost` | `db` inside Docker (set by `docker-compose.yml`); `127.0.0.1` for the PC's scripts. |
| `POSTGRES_PORT` | `5432` | |
| `EEG_LIVE_RULE` | `current` | The live EEG rule: `current` (1), `nosound` (2), `ica` (3, with an automatic fallback to (2)). See "EEG pipeline". |
| `EEG_MONITOR_LIVE` | `false` | M1b: `live.py` computes the monitor's per-channel figures. Display only. |
| `MONITOR_LIVE_INDICES` | `false` | MI: the monitor's per-epoch indices for the whole session. Display only. |
| `LABRECORDER_HOST`, `LABRECORDER_ROOT` | empty | LabRecorder's remote control and its root folder; set for Docker in `docker-compose.yml`. |

Display-only switches never change an epoch, a window or a decision. They are switched on only between
sessions and only after their own check.

`backend/.env.example` is the template; it may lag behind this table.

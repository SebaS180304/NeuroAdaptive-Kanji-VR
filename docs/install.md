# Install from scratch

On one Windows PC, which runs Docker, Unity, the AURA software and LabRecorder. Everything listens on
`127.0.0.1` only.

## 1. Docker stack: PostgreSQL, backend, portal, pgAdmin

Requirements: Docker Desktop, Git.

```powershell
git clone <repo> NeuroAdaptativeVR; cd NeuroAdaptativeVR
Copy-Item backend\.env.example backend\.env           # then set the values, see "Settings (.env)"
docker compose up -d --build
docker compose exec -T backend alembic upgrade head   # schema up to the current revision
```

| Service | Container | Port | What |
| --- | --- | --- | --- |
| `db` | `neuroadaptive_postgres` | 5432 | PostgreSQL 16, data in the `pgdata` volume |
| `backend` | `neuroadaptive_backend` | 8000 | FastAPI (`uvicorn`, no auto-reload), the repo's `backend/` mounted at `/app` |
| `dashboard` | `neuroadaptive_dashboard` | 5300 | nginx serving `dashboard/dist` |
| `pgadmin` | `neuroadaptive_pgadmin` | 8081 | pgAdmin with the connection preloaded (`pgadmin/servers.json`) |
| `kanji-tools` | — | — | profile `tools`, one-shot: `docker compose run --rm kanji-tools …` |

Check: `curl http://127.0.0.1:8000/health/db` answers `{"status":"ok","db_result":1}`.

!!! warning "Code and settings apply differently"
    A change to backend **code** goes live with `docker compose restart backend` (no session running).
    A change to `backend\.env` needs `docker compose up -d backend`: `restart` keeps the container's old
    environment.

## 2. Portal

The portal is static files that nginx serves from `dashboard/dist`. Build them once, and after every change:

```powershell
cd dashboard
npm ci
npm run build          # tsc + vite build into dist/; nginx serves it at http://127.0.0.1:5300
```

The kanji seed (`database/seed_kanji_items.sql`) is applied after `alembic upgrade head`; see
`backend/README.md`.

## 3. The PC side of the EEG path (Python on Windows)

`autorun`, `live.py`, `preflight`, `replay` and the summary scripts run on the PC, because they read LSL.
They use their own virtual environment in `backend\.venv` and read the same `backend\.env`.

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -c "from app.config import get_settings as g; print(g().eeg_live_rule)"
```

On the PC, `POSTGRES_HOST` must point at `127.0.0.1` (in Docker it is `db`). The session commands set it
for their window: `$env:POSTGRES_HOST='127.0.0.1'`.

!!! note
    `replay` reads the database with `psycopg2`, which the PC's `.venv` does not have. Run it inside the
    container, with the XDF copied to `/tmp` and deleted afterwards (see "EEG pipeline").

## 4. Unity and the Quest 2 over Link

- Unity **6000.5.10f1**, opened from Unity Hub on `unity-client/`. Packages and the scene setup:
  `unity-client/README.md`.
- The headset runs the Editor's Play mode over Meta Quest **Link**. TODO: Sebas, the Link settings used in
  the lab (cable or Air Link, resolution, refresh rate, Meta Quest app version).
- The scene's `SessionBootstrap` takes the participant code, condition, kanji set and visit in the
  Inspector (never saved in the scene).
- Unity publishes the LSL stream `UnityMarkers` while the Editor is open. **Reopen Unity before each
  session**, so no old `UnityMarkers` is left.

## 5. AURA over LSL

- AURA is a prototype cap from MIRAI: 8 channels (`Ch1`–`Ch8`), 250 Hz, ADS1299, DC-coupled, on battery.
  Montage CH1 Fp1, CH2 F3, CH3 Fz, CH4 F4, CH5 Cz, CH6 P3, CH7 Pz, CH8 P4.
- Its software publishes the LSL stream `AURA` (type `EEG`) and an empty `AURA_Markers`, with
  **LSL Stream Out** switched on. It publishes no quality or impedance over LSL.
- On the lab PC the stream reports `source_id` `AURA_COM3`. TODO: Sebas, the COM port and the pairing
  steps on a new PC.
- `live.py` and the recorder take only streams of **this PC** (by host name), and exactly one of each name.

## 6. LabRecorder

- `LabRecorderCLI.exe` records each session to
  `<root>/sub-<code>/ses-<8>/eeg/…_eeg.xdf`, started by `autorun` at Play and stopped at S9.
  `preflight` checks that it is found and that the root is writable.
- The LabRecorder GUI stays open as the manual fallback: if `autorun` prints `MANUAL: …`, the operator
  records by hand into the same path.
- TODO: Sebas, where `LabRecorderCLI.exe` is installed on a new PC and how it is put on the path.

## 7. Check the whole PC

```powershell
cd backend; .\.venv\Scripts\python.exe -m app.eeg.preflight
```

It must end with no `FAIL`. See "Running a session".

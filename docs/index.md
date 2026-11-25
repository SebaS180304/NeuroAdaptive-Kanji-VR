# NeuroAdaptive VR

An adaptive kanji-learning prototype in virtual reality. It records behaviour and EEG, and, in one
condition, adapts the task from both. This site is for a developer who has to bring the project up from
scratch and keep it running. The research plan, the decisions (`D-F6-…`) and the protocol live outside the
repo, in the project's planning documents.

## The three conditions

| Condition | What adapts the task | EEG |
| --- | --- | --- |
| `STATIC` | nothing | recorded, not used |
| `BEHAVIOR_ADAPTIVE` | behaviour (pace, accuracy, idle, head) | recorded, not used |
| `MULTIMODAL_ADAPTIVE` | behaviour, with the EEG confirming, vetoing or leading | used live from S7 |

A participant does four visits: V1–V3 with the cap, one condition each, and a short V4 with no cap.
A session walks through stages S1–S9: S1 welcome, S2 tutorial, S3 system validation (sync taps),
S4 EEG baseline, S5 learning, S6 guided practice (calibration), S7 adaptive retrieval (the only stage
where the engine decides), S8 assessment, S9 summary.

## Architecture

```
 Meta Quest 2 ── Link ──> Unity Editor (unity-client/) ──── WebSocket / REST ───> backend (FastAPI, Docker, :8000)
                              │                                                       │
                              └── LSL "UnityMarkers" ──┐                              ├── PostgreSQL 16 (Docker, :5432)
 AURA cap (8 ch, 250 Hz) ── AURA software ── LSL "AURA" ┤                              │
                                                        ├──> LabRecorderCLI ──> XDF file (one per session)
                                                        └──> live.py (on the PC, started by autorun)
                                                                   │  epochs, reference, ICA, heartbeat
                                                                   └──────────────> PostgreSQL
 Portal and live monitor (dashboard/, React, served by nginx in Docker, :5300) <── reads the backend's /research API
```

- **Unity** runs the session: stages, trials, the environment and the assistance levels. It sends every
  event to the backend and, at the same moment, a marker over LSL.
- **The backend** stores the events, runs the adaptation engine at each S7 answer, and serves the
  read-only `/research` API that the portal and the monitor use.
- **The EEG path runs on the PC, not in Docker**, because LSL streams are local. `autorun` waits for a
  new session, starts the recording (`LabRecorderCLI`) and `live.py`. `live.py` cuts 5 s epochs as the
  signal arrives and writes them to the database. The backend reads them at each S7 answer.
- **After the session**, `autorun` re-cuts the whole XDF (`fill_from_xdf`) for the analysis and writes a
  summary. The live cut stays the official one for what the engine decided.
- **The portal** (`dashboard/`) is the researcher's tool: participants, the pre-test, the session view,
  data quality, and the live monitor on a second screen. It is read-only except for the pre-test and the
  recall form.

## Where things are

| Folder | What |
| --- | --- |
| `backend/` | FastAPI, SQLAlchemy, Alembic migrations, the adaptation engine (`app/adaptation/`), the EEG path (`app/eeg/`), pytest |
| `dashboard/` | React portal and live monitor (Vite, TanStack Query, Vitest, Playwright) |
| `unity-client/` | Unity 6000.5.10f1 project for Quest 2 over Link, with its Editor test harness |
| `database/` | `schema.sql` (generated), `ERD.md`, `EVENT_CONTRACT.md`, verification SQL |
| `tools/` | Offline kanji content tools (metrics, seed SQL) in their own container |
| `docs/` | This site (MkDocs Material) |

## Build this site

```powershell
python -m venv $env:USERPROFILE\.venvs\mkdocs          # once, with internet
& $env:USERPROFILE\.venvs\mkdocs\Scripts\python -m pip install -r requirements-docs.txt
& $env:USERPROFILE\.venvs\mkdocs\Scripts\mkdocs build --strict   # writes site/, opens from file:// offline
```

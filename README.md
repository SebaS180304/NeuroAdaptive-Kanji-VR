# NeuroAdaptive VR

Adaptive kanji-learning prototype in Virtual Reality, instrumented with
behavioral telemetry and EEG. Single repository for the project: Unity
client, backend and database under one version control tree.

Status: **M1 · Technical Feasibility closed** (3 September 2026).
In progress: **Phase 2 · Core Kanji VR Experience**, feeding milestone
**M2 · Instrumented Learning Prototype** (25 September).

## What is here

| Folder | Contents |
|---|---|
| `backend/` | FastAPI async + SQLAlchemy 2.0 + WebSocket. See `backend/README.md`. |
| `database/` | `schema.sql` (human-readable reference), `ERD.md` and `verify_m1.sql` (milestone verification queries). |
| `unity-client/` | Complete Unity 6000.5.10f1 project, targeting Meta Quest 2. See `unity-client/README.md`. |
| `docker-compose.yml` | PostgreSQL 16 + backend + pgAdmin, to bring everything up with one command. |
| `pgadmin/servers.json` | Preloaded connection for the pgAdmin portal (`http://localhost:8081`). |

## Getting started

```bash
cp backend/.env.example backend/.env
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/ws_smoke_test.py   # walking skeleton
docker compose exec backend pytest                            # 4 tests
```

The smoke test and the test suite run **inside the container**: the
dependencies (`httpx`, `websockets`, `pytest`) are installed there, not in
the host's Python. Running them from your own shell fails with
`ModuleNotFoundError`.

Then `unity-client/README.md` explains how to open the Unity project and
run the same round trip from the Editor.

## M1 status

Committed deliverables: *Unity/Quest configured; FastAPI skeleton;
WebSocket tested; WAVEX capability validation; initial timestamps.*

- [x] FastAPI backend, executed and tested against a real PostgreSQL
- [x] PostgreSQL configured — initial schema and Alembic migrations
- [x] Unity ↔ backend round trip over WebSocket, with events persisted
      and their payloads intact
- [x] Initial telemetry event definition (WS protocol + `session_events`;
      the full behavioral vocabulary lands in Phase 3)
- [x] WAVEX capability validation — closed on its documentary axis
- [ ] The "Quest" half of *Unity/Quest configured*: Meta XR Core SDK,
      interaction profile, and verification inside the headset
- [ ] Empirical EEG validation — blocked on having the device in hand

Details in `claude/Evaluacion_Cierre_M1_Fase1.md` and
`claude/Fase1_Estructura_Tecnica_Estado.md` (Claude Project).

## Why the PostgreSQL schema is "initial" rather than complete

The project proposal assigns the **full schema v1** (with
`KanjiLearningItem`, trials, EEG, adaptation and learner profile) to
**M2**, not to Phase 1. What exists today is the minimum base the walking
skeleton needs — participants, sessions, config snapshot, technical
validation and a generic event log — shaped so that later phases hang
their tables on top without breaking anything. Details in
`database/ERD.md`.

`session_events` has `event_type VARCHAR(64)` plus `payload JSONB`, both
indexed, so it absorbs new events without a migration. Phase 2 leans on
that: it emits its telemetry through the generic log and **does not touch
the database**; Phase 3 promotes those events into relational tables once
the vocabulary has been stabilized by real use.

## Source of truth

Design decisions (Game Flow S0–S10, ESL/LAL, trial types, the eight-phase
schedule) live in the associated Claude Project ("Neuroadaptative VR Kanji
Project"): `Anteproyecto_NeuroAdaptive_VR_MIRAI.docx` and
`NeuroAdaptive_VR_Game_Flow_v1_1_Unity_Design_Specification.docx`. This
repository implements those decisions; it does not redefine them.

A caveat learned during M1: the Project is the source of truth for
**design and decisions**, not for the **execution state** of the
repository. Update the status documents whenever a block of work closes,
or verify against the repo before a milestone review.

## In progress — Phase 2 (Static VR Learning Prototype)

The `JapaneseLearningStudio` scene with its five functional zones, the 25
`KanjiLearningItem` assets, the response system shared by S5/S6/S7/S8, the
S5 mechanics, and the flow chained end to end without adaptation. Detailed
plan in `claude/Planteamiento_Fase2_M2.md`.

## Branch convention

`milestone/<milestone>-<short-description>`. The M1 branch is
`milestone/m1-unity-backend-communication`; Phase 2 runs on
`milestone/m2-static-learning-prototype`.

## A note on language

Repository documentation is written in English so the work travels beyond
the team. Design documents in the Claude Project remain in Spanish; the
specification and the project proposal are in English already.

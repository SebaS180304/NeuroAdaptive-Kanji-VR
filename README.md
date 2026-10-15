# NeuroAdaptive VR

Adaptive kanji-learning prototype in Virtual Reality, instrumented with
behavioral telemetry and EEG. Single repository for the project: Unity
client, backend and database under one version control tree.

Status: **M1 · Technical Feasibility closed** (3 September 2026). Phase 2
(static learning prototype) and Phase 3 (behavior instrumentation) are
merged into the current line of work.
In progress: **Phase 5a · Behavior Adaptation** (closed loop in S7).

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
docker compose exec backend pytest                            # whole suite
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

## In progress — Phase 5a (Behavior Adaptation)

In an adaptive session, the backend decides after every S7 answer whether to
change the environment (ESL) or the assistance (LAL), and sends a `DECISION`
over the WebSocket. Unity applies it between trials, and three trials later
the backend classifies the outcome of each change. Code in
`backend/app/adaptation/` and `unity-client/Assets/Scripts/Networking/AdaptationClient.cs`;
detailed plan in `claude/Planteamiento_Tecnico_F5a.md`.

## Branch convention

Milestones M1 and M2 ran on `milestone/<milestone>-<short-description>`
(`milestone/m1-unity-backend-communication`,
`milestone/m2-static-learning-prototype`). From Phase 3 on, each phase runs
on `phase/<n>-<short-description>` (`phase/3-behavior-instrumentation`,
`phase/5a-behavior-adpatation`).

## A note on language

Repository documentation is written in English so the work travels beyond
the team. Design documents in the Claude Project remain in Spanish; the
specification and the project proposal are in English already.

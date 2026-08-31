# NeuroAdaptive VR — Fase 1: Foundation & Feasibility

Estructura técnica inicial del prototipo NeuroAdaptive VR (aprendizaje
de kanji en VR con adaptación conductual/EEG). Este repo cubre la
**Fase 1** del cronograma (W1–W2, 17–28 ago 2026): base de Unity y
backend, y el esquema inicial de PostgreSQL — orientado a demostrar el
milestone **M1 · Technical Feasibility**.

## Qué hay acá

| Carpeta | Contenido |
|---|---|
| `backend/` | FastAPI async + SQLAlchemy + WebSocket. Ver `backend/README.md` para levantarlo. |
| `database/` | `schema.sql` (referencia) + `ERD.md` — esquema PostgreSQL inicial, verificado contra Postgres real. |
| `unity-client/` | Estructura de scripts C# (GameFlowController, controladores de la spec, cliente WebSocket) para armar sobre un proyecto Unity 6 nuevo. Ver `unity-client/README.md`. |
| `docker-compose.yml` | PostgreSQL + backend, para levantar todo con un comando. |

## Cómo arrancar

```bash
cp backend/.env.example backend/.env
docker compose up -d --build
docker compose exec backend alembic upgrade head
python backend/scripts/ws_smoke_test.py   # walking skeleton end-to-end
```

Después, `unity-client/README.md` explica cómo crear el proyecto Unity
real y conectarlo al mismo WebSocket.

## Qué pide M1 y qué de eso cubre este repo

Según `NeuroAdaptative VR Project Proposal.pdf` (acciones inmediatas
17–28 ago) y el anteproyecto (M1, 28 ago 2026):

- [x] Backend FastAPI skeleton
- [x] PostgreSQL configurado (esquema inicial + migraciones)
- [x] Definición de eventos de telemetría conductual (protocolo WS +
      `session_events` — vocabulario completo llega en Fase 3)
- [x] Prueba de comunicación Unity↔Backend por WebSocket — protocolo y
      cliente Unity listos; correr `ws_smoke_test.py` (simulando
      Unity) confirma el roundtrip REST + WebSocket + PostgreSQL
- [ ] Setup real de Unity + Oculus Quest — este repo deja la
      *estructura* (scripts, packages, README de setup); crear el
      proyecto Unity en tu máquina y correrlo en el headset físico
      queda pendiente de tu lado (spec de Meta cambia con el tiempo,
      ver `unity-client/README.md`)
- [ ] WAVEX capability validation — depende del hardware/API real, no
      resoluble desde este entorno

## Por qué el esquema de PostgreSQL es "inicial" y no el completo

El anteproyecto marca el **schema v1 completo** (con `KanjiLearningItem`,
trials, EEG, adaptación, learner profile) como entregable de **M2** (25
sep 2026), no de Fase 1. Lo que este repo entrega ahora es la base
mínima necesaria para probar el walking skeleton — participantes,
sesiones, config snapshot, validación técnica y un event log genérico
— pensada para que las tablas de Fase 2 en adelante se cuelguen encima
sin romper nada. Detalle completo en `database/ERD.md`.

## Fuente de verdad del proyecto

Las decisiones de diseño (Game Flow S0–S10, ESL/LAL, trial types,
cronograma de 8 fases) viven en el Project de Claude asociado
("Neuroadaptative VR Kanji Project"): `Anteproyecto_NeuroAdaptive_VR_MIRAI.docx`,
`NeuroAdaptive_VR_Game_Flow_v1_Unity_Design_Specification.docx`, y la
síntesis en `claude/Sintesis_Analisis_Comprension_Proyecto.md`. Este
repo implementa esas decisiones; no las redefine.

## Próximos pasos (Fase 2 — W3–W4)

Escena Unity `Japanese Learning Studio`, contenido de los 15 kanji
experimentales + pools, core learning loop sin adaptación
("Static VR Learning Prototype").

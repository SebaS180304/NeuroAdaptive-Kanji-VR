# Fase 1 (Foundation & Feasibility) — estado técnico

Última actualización: 3 de septiembre de 2026, al cierre de M1.
Repositorio: `C:\Users\drdom\Documents\NeuroAdaptativeVR`, monorepo único,
publicado en `https://github.com/SebaS180304/NeuroAdaptive-Kanji-VR` (privado).

> Este documento reemplaza la versión del 24 de agosto, que describía un estado
> ya superado: en aquel momento el backend no se había ejecutado nunca,
> `unity-client/` era una carpeta de scripts sin proyecto Unity, y el
> repositorio ni siquiera existía en la raíz. Esa desactualización llegó a
> producir una evaluación equivocada del proyecto, así que conviene mantener
> este archivo al día al cerrar cada bloque de trabajo.

## Estructura del repositorio

```
NeuroAdaptativeVR/
├── .git/                    ← repositorio único en la raíz
├── .gitignore               ← backend, datos de investigación, OS
├── docker-compose.yml       ← db (Postgres 16) + backend + pgAdmin
├── backend/                 ← FastAPI + SQLAlchemy 2.0 + WebSocket
├── database/                ← schema.sql, ERD.md, verify_m1.sql
├── pgadmin/servers.json     ← conexión pre-cargada del portal
└── unity-client/            ← proyecto Unity 6000.5.10f1 completo
    ├── .gitignore           ← plantilla oficial de Unity (patrones anclados)
    ├── .gitattributes       ← reglas de Git LFS
    ├── Assets/
    ├── Packages/
    └── ProjectSettings/
```

Los dos `.gitignore` están separados a propósito: el de Unity usa patrones
anclados (`/[Ll]ibrary/`, `/[Tt]emp/`) que se resuelven relativos a su propia
carpeta. Moverlos a la raíz los rompería y `Library/` empezaría a versionarse.

## Backend

FastAPI async + SQLAlchemy 2.0 + PostgreSQL 16 + WebSocket. Rutas: `/health`,
`/health/db`, `/participants`, `/sessions` (con `PATCH /sessions/{id}/state`) y
`/ws/session/{session_id}`, que implementa el protocolo
PING / SESSION_EVENT / VALIDATION_EVENT.

**Verificado de punta a punta el 25 de agosto** con Python 3.12 y Postgres real.
Los cuatro tests pasan: `test_health`, `test_health_db`,
`test_full_session_walking_skeleton` y `test_websocket_ping_and_events`.

## Base de datos

Esquema inicial de 5 tablas: `participants`, `experiment_sessions`,
`session_config_snapshots`, `system_validation_events`, `session_events`.
Deliberadamente acotado a lo que Fase 1 necesita — el "schema v1" completo es
entregable de M2. Detalle en `database/ERD.md`.

`database/verify_m1.sql` contiene las consultas de verificación del hito,
reutilizables. Portal de inspección en `http://localhost:8081` (pgAdmin, con el
servidor pre-cargado vía `pgadmin/servers.json`).

## Cliente Unity

Proyecto Unity **6000.5.10f1**, plantilla Universal 3D, sobre Meta Quest 2.

Paquetes relevantes: `com.endel.nativewebsocket` (git URL, resuelto),
`com.unity.nuget.newtonsoft-json` 3.2.2, `com.unity.xr.openxr` 1.17.1,
`com.unity.xr.management` 4.7.0, `com.unity.ai.assistant` 2.18.0-pre.2.

Estructura de `Assets/`: `Scripts/{Core,Controllers,Data,Networking}`, más
`Prefabs/`, `Scenes/`, `ScriptableObjects/`, `Settings/` y `XR/`. Nota: la
estructura es **plana**, no bajo `_Project/` como planteaba el esqueleto
original; esa carpeta se eliminó por ser un duplicado exacto.

Componentes funcionales en Fase 1:

- `SessionCommunicationClient` — cliente WebSocket real sobre NativeWebSocket,
  con heartbeat, manejo de errores y bombeo de la cola de mensajes.
- `GameFlowController` — máquina de estados S0–S9 con emisión de
  `STATE_ENTERED`.
- `SessionBootstrap` — crea participante y sesión por REST y abre el WebSocket,
  para no copiar UUIDs a mano.
- Los 14 controladores de la sección 14 del spec, como stubs documentados.

## Estado de OpenXR

OpenXR habilitado con su loader para **Standalone** (`buildTarget: 1`).
Pendiente: habilitar Android, instalar el Meta XR Core SDK con sus tres feature
groups, y habilitar al menos un **interaction profile** — los 18 están hoy en
`m_enabled: 0`, y sin ninguno OpenXR puede no inicializar sin dar error claro.

## Cierre de M1 · 3 de septiembre de 2026

Round trip Unity↔backend demostrado en el Editor, sin VR: participante y sesión
creados por REST desde Unity, WebSocket abierto, `VALIDATION_EVENT` y
`STATE_ENTERED` con sus ACKs, heartbeat PING/PONG sostenido, avance de estados
hasta S9 con el guard rechazando correctamente el avance más allá, y cierre
limpio del socket al detener Play. Los eventos quedaron persistidos en
PostgreSQL **con su payload íntegro**, lo que confirma la corrección del
protocolo (el DTO mandaba `payload_json` como string; el backend lee `payload`
esperando un objeto, y guardaba vacío sin error).

Ambos criterios de salida de M1 cumplidos. Trabajo publicado en la rama `M1`.

## Qué queda abierto

- **Mitad "Quest" del entregable "Unity/Quest configurados"**: Meta XR Core SDK,
  interaction profile y repetición del round trip vía Quest Link.
- **Cuatro preguntas a Mirai**: A2 (posiciones de electrodo alcanzables), A5
  (filtros por defecto, respuesta truncada), A7 (definición del stream LSL) y
  A13 (si referencia y tierra consumen dos de los ocho canales). A2 y A7
  bloquean diseño de Fase 4.
- **Validaciones empíricas de EEG**: grupos B, C y D del checklist, dependientes
  de tener el dispositivo. La primera debe ser C1, el bloqueo alfa.
- **Reconciliar el spec a v1.1**: ver `Reconciliacion_Spec_v1_1.md`. Bloquea el
  arranque de Fase 2.

## Siguiente fase

Fase 2 (W3–W4): escena Japanese Learning Studio, dataset de los 15 kanji
experimentales y core learning loop sin adaptación. Plan detallado en
`Plan_Arranque_Fase2.md`.

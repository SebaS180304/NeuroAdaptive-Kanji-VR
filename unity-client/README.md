# NeuroAdaptive VR — Unity Client (Fase 1)

Esqueleto tecnico del cliente Unity/Quest. Esta carpeta **no** es un
proyecto Unity completo exportado desde el Editor (no hay `Library/`,
`ProjectSettings/*.asset` ni GUIDs generados) — es la estructura de
scripts y la configuracion de paquetes que arma sobre un proyecto Unity
nuevo, siguiendo la especificacion de `Game Flow v1 / Unity Design
Specification` del proyecto.

## 1. Crear el proyecto Unity real

1. Instalar **Unity 6.1 o superior** (minimo recomendado por Meta:
   `6000.0.66f2`) via Unity Hub. Fuente: [Meta Horizon — Unity project
   setup](https://developers.meta.com/horizon/documentation/unity/unity-project-setup/).
2. Unity Hub → New Project → template **3D (Core)** o **VR Core**.
   Nombrarlo, por ejemplo, `NeuroAdaptiveVR`.
3. Cerrar Unity. Copiar el contenido de esta carpeta (`Assets/_Project/`
   y `Packages/manifest.json`) sobre el proyecto recien creado,
   fusionando `Packages/manifest.json` si Unity ya genero uno (agregar
   las dependencias listadas aca, no pisar las que Unity puso por
   default).
4. Reabrir el proyecto en Unity Hub. Unity va a importar los assets y
   resolver los paquetes del manifest.

## 2. Paquetes / SDKs requeridos

> ⚠️ **NO fusiones versiones fijadas a mano en `Packages/manifest.json`.**
> La version original de este README pedia copiar un manifest con
> versiones pineadas (`com.unity.xr.management: 4.5.1`,
> `com.unity.xr.openxr: 1.15.1`, `com.unity.nuget.newtonsoft-json: 3.2.1`,
> `com.unity.textmeshpro: 3.2.0-pre.10`). Eso **rompe la resolucion de
> paquetes** en Unity 6000.5+: esas versiones son de 2024 y el Editor
> nuevo exige minimos mas altos, con lo que el grafo de dependencias
> queda insatisfacible y el proyecto no abre.
>
> El `manifest.json` de esta carpeta ahora solo declara modulos
> integrados de Unity (siempre resolubles). **Todo lo demas se instala
> desde el Editor**, dejando que Package Manager elija la version
> compatible con tu Editor.

Instalar asi:

- **XR Plugin Management + OpenXR Plugin** — *no* los agregues a mano.
  Ve a **Edit → Project Settings → XR Plug-in Management** y marca
  **OpenXR**; Unity instala `com.unity.xr.management` y
  `com.unity.xr.openxr` con las versiones correctas automaticamente.
  (El Oculus XR Plugin viejo esta deprecado; el path actual es OpenXR.)
- **Newtonsoft JSON** — Package Manager → **+ → Add package by name** →
  `com.unity.nuget.newtonsoft-json`, **sin escribir version**. Se usa
  para serializacion robusta de los mensajes WebSocket (mas flexible que
  `JsonUtility` para el `payload` libre de
  `SessionEvent`/`SystemValidationEvent`).
- **Input System** — Package Manager → `com.unity.inputsystem`, sin
  version. La plantilla Universal 3D suele traerlo ya.
- **TextMeshPro** — **no lo instales**. En Unity 6 viene dentro de
  `com.unity.ugui` y el paquete suelto esta descontinuado.

**Instalar manualmente desde Package Manager (no estan en el registry
publico de Unity, se instalan via su propio instalador o Asset Store):**

- **Meta XR Core SDK** — componentes esenciales para Quest.
- **Meta XR Platform SDK** — identidad, entitlements, cloud storage
  (se usa mas adelante, no bloquea Fase 1).
- **NativeWebSocket** (`https://github.com/endel/NativeWebSocket`,
  instalar via Package Manager → Add package from git URL) — cliente
  WebSocket compatible con builds IL2CPP de Quest.
  `SessionCommunicationClient.cs` esta escrito para este paquete
  (implementacion comentada, lista para descomentar tras instalarlo).

Despues de instalar Meta XR: Project Settings → XR Plug-in Management →
habilitar OpenXR para Android, y activar los OpenXR Feature Groups
**Meta XR Feature**, **Meta XR Foveation** y **Meta XR Subsampled
Layout** (requeridos por Meta para acceso completo al headset).

## 3. Estructura de carpetas

```
Assets/_Project/
├── Scenes/                 # JapaneseLearningStudio.unity va aca (Fase 2)
├── Scripts/
│   ├── Core/                GameFlowController, SessionClock
│   ├── Controllers/         Los 14 controladores de la spec seccion 14
│   ├── Data/                KanjiLearningItem, enums (GameFlowState, ESL/LAL, trial types)
│   └── Networking/          SessionCommunicationClient, contratos de mensajes WS
├── ScriptableObjects/       # Assets KanjiLearningItem (Fase 2)
└── Prefabs/                 # Prefabs de zonas funcionales (Fase 2)
```

Cada script tiene un docstring citando la seccion de la spec que
implementa y la fase del cronograma donde se completa su logica real.
En Fase 1 son deliberadamente **esqueletos**: la maquina de estados y
el cliente WebSocket son funcionales (una vez instalado NativeWebSocket
y armada la escena minima), pero el contenido pedagogico llega en
Fase 2.

## 4. Probar el walking skeleton (objetivo de M1)

1. Levantar el backend (ver `../backend/README.md`).
2. En Unity, crear un GameObject vacio con `GameFlowController` +
   `SessionCommunicationClient` (el `[RequireComponent]` los liga).
3. Configurar `backendBaseUrl` = `ws://<IP-de-tu-PC>:8000` (usar la IP
   de red local si vas a probar desde el Quest físico; `localhost`
   solo sirve corriendo en el Editor).
4. Instalar NativeWebSocket y descomentar la implementacion en
   `SessionCommunicationClient.Connect()`.
5. Crear una sesion vía REST (`POST /sessions`, ver README del
   backend o `scripts/ws_smoke_test.py`) y pasar ese `session_id` a
   `GameFlowController`/`Configure()`.
6. Play: deberías ver en consola el `PING`/`PONG` cada
   `pingIntervalSeconds`, y `STATE_ENTERED` al llamar
   `AdvanceToNextState()`.

## 5. Que NO esta en Fase 1

Contenido kanji real, escena `JapaneseLearningStudio` armada,
mecanicas de aprendizaje (discovery, assembly, trials), ESL/LAL
aplicando cambios visuales reales, EEG/WAVEX. Todo eso es Fase 2 en
adelante — ver `Sintesis_Analisis_Comprension_Proyecto.md` en el
Project de Claude para el cronograma completo.

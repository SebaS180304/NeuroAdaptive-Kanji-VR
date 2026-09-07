# NeuroAdaptive VR — Unity Client

The Unity/Quest client for the prototype. **This is a real, complete Unity
project**, not a skeleton to copy over another one: it has
`ProjectSettings/`, a resolved `Packages/manifest.json` and generated
GUIDs. Open it directly from Unity Hub by pointing at this folder.

> Previous version of this README: it described an `Assets/_Project/`
> folder that no longer exists, claimed this was not a real Unity project,
> and asked the reader to "uncomment the WebSocket implementation". None of
> that has been true since 28 August 2026. Corrected in Phase 2's step 0.

## 1. Opening the project

Unity **6000.5.10f1** (the exact version lives in
`ProjectSettings/ProjectVersion.txt`). Unity Hub → Add → select this
folder. The first open regenerates `Library/`, which git ignores.

## 2. Packages already installed

Nothing needs installing by hand to work in the Editor. `manifest.json`
already resolves:

| Package | Version | Why |
|---|---|---|
| `com.endel.nativewebsocket` | git `#upm` | WebSocket client that works in IL2CPP builds for Quest. `System.Net.WebSockets` is not reliable there. |
| `com.unity.nuget.newtonsoft-json` | 3.2.2 | Serialization of the WS messages. `JsonUtility` cannot handle the free-form `payload`. |
| `com.unity.xr.openxr` | 1.17.1 | XR. OpenXR is the current path; the old Oculus XR Plugin is deprecated. |
| `com.unity.xr.management` | 4.7.0 | XR loader. |
| `com.unity.render-pipelines.universal` | 17.5.0 | URP (Universal 3D template). |
| `com.unity.inputsystem` | 1.20.0 | Input. |

> **Do not pin versions by hand in `manifest.json`.** Installing from
> Package Manager without typing a version lets the Editor pick a
> compatible one. Pinning 2024-era versions into a 6000.5+ Editor makes the
> dependency graph unsatisfiable and the project will not open. TextMeshPro
> in particular **is not installed separately**: in Unity 6 it ships inside
> `com.unity.ugui`.

## 3. Layout

```
Assets/
├── Scenes/
│   ├── M1_RoundTrip.unity              # M1 round trip scene
│   └── JapaneseLearningStudio.unity    # main scene (Phase 2)
├── Scripts/
│   ├── Core/          GameFlowController, SessionBootstrap, SessionClock
│   ├── Controllers/   The 14 controllers from spec section 14
│   ├── Data/          KanjiLearningItem, GameFlowState, ExperimentalCondition,
│   │                  RetrievalTrialType
│   └── Networking/    SessionCommunicationClient, WebSocketMessages
├── ScriptableObjects/  KanjiLearningItem assets (Phase 2)
├── Prefabs/            Prefabs for the functional zones (Phase 2)
├── Settings/           URP renderers and volume profiles
└── XR/                 OpenXR loader and settings
```

The layout is **flat**, not nested under `_Project/`. That folder was an
exact duplicate of `Assets/Scripts/` and was removed before the repository
was consolidated.

Every script cites, in its docstring, the spec section it implements and
the phase in which its real logic lands.

## 4. What works today

The three walking-skeleton components are real, tested code:

- **`SessionCommunicationClient`** — WebSocket over NativeWebSocket, with a
  configurable PING/PONG heartbeat, error handling, and message-queue
  pumping in `Update()` (without that pump, `OnMessage` never runs).
- **`GameFlowController`** — the S0–S9 state machine, emitting
  `STATE_ENTERED` and guarding against advancing past S9. It exposes
  `IsAdaptationAllowed()`, which returns true only in S7 and only under
  adaptive conditions.
- **`SessionBootstrap`** — creates a participant and a session over REST and
  hands the `session_id` to the client before opening the socket, so you
  never copy UUIDs by hand between curl and the Inspector.

**That last one is Phase 1 only.** From Phase 2 onward the researcher
creates the session and Unity merely consumes it; `createNewSessionOnPlay`
stops being the normal path. Note that while it is on, every Play creates a
new participant and session, and a failed run leaves orphaned participants
in the database.

The other fourteen controllers from spec section 14 are present: ten are
stubs with TODOs, while `EnvironmentalStimulationController`,
`LearningAssistanceController` and `PronunciationAudioController` carry only
their guard clauses (adaptation timing, and the ban on pre-response audio in
Kanji → Reading trials). `BehaviorTelemetryController` is functional: its
`Emit()` is the single exit point for events.

## 5. Running the round trip

1. Start the backend: see `../backend/README.md`, section 1 (Docker).
2. Open `Assets/Scenes/M1_RoundTrip.unity`.
3. On the session GameObject, check `SessionBootstrap.backendHttpUrl`
   (`http://localhost:8000`) and `SessionCommunicationClient.backendBaseUrl`
   (`ws://localhost:8000`). Mind the scheme: one is `http://`, the other
   `ws://`. To test from a physical Quest, use the PC's LAN IP in both;
   `localhost` only works when running in the Editor.
4. Press Play. The console should show, in order: participant created,
   session created, `WS abierto`, the `VALIDATION_EVENT` ACK, the S0→S1
   `STATE_ENTERED` with its ACK, and then `PING`/`PONG` every
   `pingIntervalSeconds`.
5. To advance states manually: right-click the `SessionBootstrap` header
   during Play → **Advance To Next State**.
6. Check the database: `docker compose exec -T db psql -U neuroadaptive
   -d neuroadaptive_vr < ../database/verify_m1.sql`. Query 3 must return
   `payload_ok = true`.

## 6. The wire contract

Two rules that Unity code must respect, because both were bugs before
Phase 2 and neither fails loudly on its own:

- **The event payload is an object, not a serialized string.** The backend
  reads `payload` expecting an object; sending a JSON string stores an
  empty payload without raising. This is why `SendSessionEvent` takes a
  `Dictionary<string, object>` and the project uses Newtonsoft rather than
  `JsonUtility`.
- **Game flow states travel as the backend's enum value, not as the C#
  member name.** Always use `GameFlowState.ToWireValue()`, never
  `.ToString()`: the former yields `S1_WELCOME_ORIENTATION`, the latter
  `S1_WelcomeOrientation`, and only the first one validates against the
  Pydantic model and the `game_flow_state` PostgreSQL type. Each enum
  member carries its wire value in an `[EnumMember]` attribute, which is
  the single source of truth; a member added without one throws on first
  use rather than sending wrong strings silently.

## 7. XR status

OpenXR is enabled with its loader for **Standalone** (`buildTarget: 1`),
which is enough for Quest Link — the target for Phase 2.

Outstanding, and needed only once an APK build comes into scope:

- Android Build Support + OpenJDK + Android SDK & NDK in the Editor.
- Meta XR Core SDK with its three feature groups (**Meta XR Feature**,
  **Meta XR Foveation**, **Meta XR Subsampled Layout**).
- At least one enabled **interaction profile**. All 18 currently sit at
  `m_enabled: 0`, and with none of them OpenXR may fail to initialize
  without a clear error. The relevant one is **Oculus Touch Controller
  Profile**.
- OpenXR enabled for the Android build target as well.

## 8. What Phase 2 brings

The `JapaneseLearningStudio` scene with its five functional zones, the 25
`KanjiLearningItem` assets (15 experimental + 5 reserve + 5 tutorial), the
response system shared by S5/S6/S7/S8, the S5 mechanics (discovery,
standardized audio, guided assembly, guided association) and the flow
chained end to end without adaptation.

Detailed plan: `claude/Planteamiento_Fase2_M2.md` in the Claude Project.

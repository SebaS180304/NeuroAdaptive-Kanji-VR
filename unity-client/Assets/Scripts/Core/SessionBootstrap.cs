using System;
using System.Collections;
using System.Collections.Generic;
using System.Text;
using NeuroAdaptiveVR.Data;
using NeuroAdaptiveVR.Networking;
using Newtonsoft.Json;
using UnityEngine;
using UnityEngine.Networking;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// Arranque de sesion.
    ///
    /// Crea participante y sesion por REST y le pasa el session_id al
    /// SessionCommunicationClient antes de abrir el WebSocket, para no copiar
    /// UUIDs a mano entre curl y el Inspector.
    ///
    /// FASE 2: ademas instala el instante cero del Session Clock a partir del
    /// `session_clock_started_at` que devuelve el backend. Sin eso, cada
    /// evento sale con `session_elapsed_ms = -1` (ver SessionClock y
    /// database/EVENT_CONTRACT.md seccion 3).
    ///
    /// `createNewSessionOnPlay` era correcto para M1 y deja de serlo ahora: a
    /// partir de Fase 2 la sesion la crea el investigador y Unity solo la
    /// consume. Mientras el Research Dashboard no exista (Fase 7), la sesion
    /// se crea por REST a mano y su id se pega en `existingSessionId`.
    /// </summary>
    [RequireComponent(typeof(SessionCommunicationClient))]
    public class SessionBootstrap : MonoBehaviour
    {
        [Header("Backend")]
        [Tooltip("Base HTTP del backend. Ojo: aca va http://, no ws://.")]
        [SerializeField] private string backendHttpUrl = "http://localhost:8000";

        [Header("Sesion")]
        [Tooltip("Si esta activo, crea participante + sesion nuevos en cada Play. " +
                 "Camino de M1; en Fase 2 la sesion la crea el investigador.")]
        [SerializeField] private bool createNewSessionOnPlay = true;

        [Tooltip("Se usa solo si createNewSessionOnPlay esta desactivado.")]
        [SerializeField] private string existingSessionId;

        [Tooltip("STATIC | BEHAVIOR_ADAPTIVE | MULTIMODAL_ADAPTIVE")]
        [SerializeField] private string condition = "STATIC";

        [Header("Prueba")]
        [Tooltip("Manda un VALIDATION_EVENT en cuanto conecta, util para verificar el round trip completo.")]
        [SerializeField] private bool sendValidationEventOnConnect = true;

        [Tooltip("Avanza S0 -> S1 en cuanto conecta, produciendo el primer STATE_ENTERED.")]
        [SerializeField] private bool advanceToFirstStateOnConnect = true;

        private SessionCommunicationClient _client;
        private GameFlowController _flow;

        private void Awake()
        {
            _client = GetComponent<SessionCommunicationClient>();
            _flow = GetComponent<GameFlowController>();
        }

        private IEnumerator Start()
        {
            // El reloj es estatico y sobrevive entre Plays en el Editor.
            // Sin este reset, la segunda sesion heredaria el cero de la primera
            // y todos sus session_elapsed_ms saldrian desplazados.
            SessionClock.ResetForNewSession();

            // Lo mismo que el reloj y por lo mismo: el contexto es estatico y
            // sobrevive entre Plays en el Editor. Sin este reset, la segunda
            // sesion heredaria el set y la seed de la primera.
            SessionContext.Reset();

            string sessionId = existingSessionId;

            if (createNewSessionOnPlay)
            {
                string participantId = null;
                string externalCode = $"UNITY_{DateTime.UtcNow:yyyyMMddHHmmss}";

                yield return PostJson(
                    $"{backendHttpUrl}/participants",
                    JsonConvert.SerializeObject(new Dictionary<string, object>
                    {
                        { "external_code", externalCode },
                    }),
                    body => participantId = ReadField(body, "id"));

                if (string.IsNullOrEmpty(participantId))
                {
                    Debug.LogError("[SessionBootstrap] No se pudo crear el participante. Abortando.");
                    yield break;
                }
                Debug.Log($"[SessionBootstrap] Participante creado: {participantId}");

                yield return PostJson(
                    $"{backendHttpUrl}/sessions",
                    JsonConvert.SerializeObject(new Dictionary<string, object>
                    {
                        { "participant_id", participantId },
                        { "condition", condition },
                    }),
                    body =>
                    {
                        sessionId = ReadField(body, "id");
                        InstallSessionData(body);
                    });

                if (string.IsNullOrEmpty(sessionId))
                {
                    Debug.LogError("[SessionBootstrap] No se pudo crear la sesion. Abortando.");
                    yield break;
                }
                Debug.Log($"[SessionBootstrap] Sesion creada: {sessionId}");
            }
            else if (!string.IsNullOrWhiteSpace(sessionId))
            {
                // Sesion creada por el investigador: hay que ir a buscar su
                // instante cero, porque no lo tenemos de una respuesta previa.
                yield return GetJson($"{backendHttpUrl}/sessions/{sessionId}", InstallSessionData);
            }

            if (string.IsNullOrWhiteSpace(sessionId))
            {
                Debug.LogError("[SessionBootstrap] No hay session_id. Activa createNewSessionOnPlay o pega uno en existingSessionId.");
                yield break;
            }

            // Una sesion de verdad tiene que traer set y seed. Sin ellos no es
            // reconstruible (spec 6.1), y eso es un error de configuracion del
            // investigador, no un caso a resolver en runtime: la sesion se para
            // antes de producir datos que nadie va a poder reproducir.
            //
            // El camino de depuracion --createNewSessionOnPlay, heredado de M1--
            // crea sesiones sin esos campos a proposito, asi que ahi se avisa y
            // se sigue.
            if (!SessionContext.IsComplete)
            {
                string falta = (SessionContext.AssignedKanjiSet == null ? "assigned_kanji_set " : "") +
                               (SessionContext.RandomSeedRaw == null ? "random_seed" : "");

                if (createNewSessionOnPlay)
                {
                    Debug.LogWarning($"[SessionBootstrap] Sesion de depuracion sin {falta.Trim()}. " +
                                     "Se usan los valores del Inspector y la corrida NO es reconstruible. " +
                                     "Para una sesion real, creala por REST con esos campos.");
                }
                else
                {
                    Debug.LogError($"[SessionBootstrap] La sesion {sessionId} no trae {falta.Trim()}. " +
                                   "Sin eso la sesion no es reconstruible (spec 6.1) y no se arranca. " +
                                   "Recreala por REST con assigned_kanji_set y random_seed.");
                    yield break;
                }
            }

            _client.OnConnected += HandleConnected;

            _client.Configure(sessionId);
            _client.Connect();
        }

        /// <summary>
        /// Instala TODO lo que la sesion declara, no solo el reloj.
        ///
        /// Hasta el 16 de septiembre esta respuesta se leia para sacar un campo y
        /// se tiraban los otros cuatro -- el set asignado, la seed, la condicion y
        /// el numero de visita--, que mientras tanto vivian a mano en el
        /// Inspector. La fila podia decir set A con seed 20260909 mientras la
        /// corrida usaba el set B con otra seed, y nada los comparaba.
        /// </summary>
        private static void InstallSessionData(string jsonBody)
        {
            string iso = ReadField(jsonBody, "session_clock_started_at");
            if (!SessionClock.TrySetSessionZeroFromIso(iso))
            {
                Debug.LogWarning("[SessionBootstrap] La sesion no trae session_clock_started_at usable. " +
                                 "Los eventos saldran con session_elapsed_ms = -1.");
            }

            SessionContext.Install(
                sessionId:         ReadField(jsonBody, "id"),
                assignedKanjiSet:  ReadField(jsonBody, "assigned_kanji_set"),
                randomSeedRaw:     ReadField(jsonBody, "random_seed"),
                conditionWire:     ReadField(jsonBody, "condition"),
                visitNumberRaw:    ReadField(jsonBody, "visit_number"));
        }

        private void OnEnable()
        {
            // El HTTP vive en este componente, no en GameFlowController: ese
            // controlador es dueño del estado y no tiene por que saber que hay un
            // backend. Aqui ya estan la URL base y los helpers.
            if (_flow == null) _flow = GetComponent<GameFlowController>();
            if (_flow != null) _flow.OnStateEntered += HandleStateEntered;
        }

        private void OnDisable()
        {
            if (_flow != null) _flow.OnStateEntered -= HandleStateEntered;
        }

        /// <summary>
        /// Sube el estado a experiment_sessions.current_state.
        ///
        /// Hasta el 16 de septiembre NADIE llamaba a este endpoint: la columna se
        /// quedaba en el valor con que nacia la fila durante toda la sesion, y
        /// `status` con ella. Una sesion completa y una abandonada se veian
        /// exactamente igual en la base.
        ///
        /// Es fire-and-forget a proposito: si el PATCH falla, la sesion sigue --
        /// la fuente de verdad del estado es el STATE_ENTERED del log de eventos,
        /// que ya viajo por el WebSocket. Esta columna es una comodidad para
        /// consultar, no el registro primario.
        /// </summary>
        private void HandleStateEntered(GameFlowState state)
        {
            if (!SessionContext.IsInstalled || string.IsNullOrWhiteSpace(SessionContext.SessionId))
                return;

            StartCoroutine(PatchJson(
                $"{backendHttpUrl}/sessions/{SessionContext.SessionId}/state",
                JsonConvert.SerializeObject(new Dictionary<string, object>
                {
                    { "new_state", state.ToWireValue() },
                })));
        }

        private void HandleConnected()
        {
            _client.OnConnected -= HandleConnected;

            if (sendValidationEventOnConnect)
            {
                _client.SendValidationEvent(
                    component: "UNITY_BACKEND_WS",
                    status: "OK",
                    payload: new Dictionary<string, object>
                    {
                        { "note", "round trip desde Unity" },
                        { "unity_version", Application.unityVersion },
                        { "platform", Application.platform.ToString() },
                    });
            }

            if (!advanceToFirstStateOnConnect) return;

            if (_flow == null)
            {
                Debug.LogWarning("[SessionBootstrap] No hay GameFlowController en este GameObject, " +
                                 "asi que no se enviara el primer STATE_ENTERED.");
                return;
            }

            // Primer STATE_ENTERED: S0 -> S1.
            _flow.AdvanceToNextState();
        }

        /// <summary>
        /// Avanza un estado a mano desde el menu contextual del componente
        /// (click derecho en el header del script durante Play).
        /// </summary>
        [ContextMenu("Advance To Next State")]
        private void AdvanceState()
        {
            if (_flow == null)
            {
                Debug.LogWarning("[SessionBootstrap] No hay GameFlowController en este GameObject.");
                return;
            }
            _flow.AdvanceToNextState();
        }

        private IEnumerator PostJson(string url, string json, Action<string> onSuccess)
        {
            using var request = new UnityWebRequest(url, UnityWebRequest.kHttpVerbPOST);
            request.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(json));
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");

            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                Debug.LogError($"[SessionBootstrap] POST {url} fallo: {request.error} · {request.downloadHandler?.text}");
                yield break;
            }

            onSuccess?.Invoke(request.downloadHandler.text);
        }

        private IEnumerator PatchJson(string url, string json)
        {
            using var request = new UnityWebRequest(url, "PATCH");
            request.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(json));
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");

            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                // Warning y no error: el estado ya quedo registrado en
                // session_events. Esto solo sincroniza una columna de comodidad.
                Debug.LogWarning($"[SessionBootstrap] PATCH {url} fallo: {request.error}. " +
                                 "current_state queda desactualizado; los STATE_ENTERED no.");
            }
        }

        private IEnumerator GetJson(string url, Action<string> onSuccess)
        {
            using var request = UnityWebRequest.Get(url);

            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                Debug.LogError($"[SessionBootstrap] GET {url} fallo: {request.error} · {request.downloadHandler?.text}");
                yield break;
            }

            onSuccess?.Invoke(request.downloadHandler.text);
        }

        /// <summary>
        /// Lee un campo de primer nivel de una respuesta JSON, como string
        /// crudo.
        ///
        /// DateParseHandling.None no es opcional: por defecto Newtonsoft
        /// convierte cualquier string que parezca fecha en un DateTime, y
        /// entonces .ToString() devuelve el formato de la cultura local
        /// ("07/09/2026 10:06:40") en vez del ISO-8601 con offset que mando
        /// el backend. SessionClock.TrySetSessionZeroFromIso recibiria una
        /// fecha sin zona horaria y el instante cero quedaria desplazado por
        /// el offset local -- nueve horas, corriendo esto en Japon.
        /// </summary>
        private static readonly JsonSerializerSettings RawJsonSettings = new()
        {
            DateParseHandling = DateParseHandling.None,
        };

        private static string ReadField(string jsonBody, string key)
        {
            try
            {
                var parsed = JsonConvert.DeserializeObject<Dictionary<string, object>>(
                    jsonBody, RawJsonSettings);
                return parsed != null && parsed.TryGetValue(key, out var value) ? value?.ToString() : null;
            }
            catch (Exception ex)
            {
                Debug.LogError($"[SessionBootstrap] No se pudo leer '{key}' de la respuesta: {ex.Message}");
                return null;
            }
        }
    }
}

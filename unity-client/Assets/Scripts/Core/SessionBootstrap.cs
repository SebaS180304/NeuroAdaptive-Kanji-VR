using System;
using System.Collections;
using System.Collections.Generic;
using System.Text;
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
                        InstallSessionClock(body);
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
                yield return GetJson($"{backendHttpUrl}/sessions/{sessionId}", InstallSessionClock);
            }

            if (string.IsNullOrWhiteSpace(sessionId))
            {
                Debug.LogError("[SessionBootstrap] No hay session_id. Activa createNewSessionOnPlay o pega uno en existingSessionId.");
                yield break;
            }

            _client.OnConnected += HandleConnected;

            _client.Configure(sessionId);
            _client.Connect();
        }

        private static void InstallSessionClock(string jsonBody)
        {
            string iso = ReadField(jsonBody, "session_clock_started_at");
            if (!SessionClock.TrySetSessionZeroFromIso(iso))
            {
                Debug.LogWarning("[SessionBootstrap] La sesion no trae session_clock_started_at usable. " +
                                 "Los eventos saldran con session_elapsed_ms = -1.");
            }
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

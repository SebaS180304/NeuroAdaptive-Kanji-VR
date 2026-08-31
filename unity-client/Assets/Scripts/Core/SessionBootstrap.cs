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
    /// Arranque de sesion para el walking skeleton de M1.
    ///
    /// Hace por REST lo mismo que backend/scripts/ws_smoke_test.py: crea
    /// un participante, crea una sesion, y le pasa el session_id al
    /// SessionCommunicationClient antes de abrir el WebSocket. Asi no hay
    /// que copiar UUIDs a mano entre curl y el Inspector.
    ///
    /// FASE 1 unicamente. En Fase 2+ la sesion la crea el investigador
    /// desde el Research Dashboard y Unity solo la consume.
    /// </summary>
    [RequireComponent(typeof(SessionCommunicationClient))]
    public class SessionBootstrap : MonoBehaviour
    {
        [Header("Backend")]
        [Tooltip("Base HTTP del backend. Ojo: aca va http://, no ws://.")]
        [SerializeField] private string backendHttpUrl = "http://localhost:8000";

        [Header("Sesion")]
        [Tooltip("Si esta activo, crea participante + sesion nuevos en cada Play.")]
        [SerializeField] private bool createNewSessionOnPlay = true;

        [Tooltip("Se usa solo si createNewSessionOnPlay esta desactivado.")]
        [SerializeField] private string existingSessionId;

        [Tooltip("STATIC | BEHAVIOR_ADAPTIVE | MULTIMODAL_ADAPTIVE")]
        [SerializeField] private string condition = "STATIC";

        [Header("Prueba")]
        [Tooltip("Manda un VALIDATION_EVENT en cuanto conecta, util para verificar el round trip completo.")]
        [SerializeField] private bool sendValidationEventOnConnect = true;

        private SessionCommunicationClient _client;
        private GameFlowController _flow;

        private void Awake()
        {
            _client = GetComponent<SessionCommunicationClient>();
            _flow = GetComponent<GameFlowController>();
        }

        private IEnumerator Start()
        {
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
                    body => participantId = ReadId(body));

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
                    body => sessionId = ReadId(body));

                if (string.IsNullOrEmpty(sessionId))
                {
                    Debug.LogError("[SessionBootstrap] No se pudo crear la sesion. Abortando.");
                    yield break;
                }
                Debug.Log($"[SessionBootstrap] Sesion creada: {sessionId}");
            }

            if (string.IsNullOrWhiteSpace(sessionId))
            {
                Debug.LogError("[SessionBootstrap] No hay session_id. Activa createNewSessionOnPlay o pega uno en existingSessionId.");
                yield break;
            }

            if (sendValidationEventOnConnect)
            {
                _client.OnConnected += HandleConnected;
            }

            _client.Configure(sessionId);
            _client.Connect();
        }

        private void HandleConnected()
        {
            _client.OnConnected -= HandleConnected;

            _client.SendValidationEvent(
                component: "UNITY_BACKEND_WS",
                status: "OK",
                payload: new Dictionary<string, object>
                {
                    { "note", "round trip M1 desde Unity" },
                    { "unity_version", Application.unityVersion },
                    { "platform", Application.platform.ToString() },
                });

            // Primer STATE_ENTERED: S0 -> S1.
            if (_flow != null)
            {
                _flow.AdvanceToNextState();
            }
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

        private static string ReadId(string jsonBody)
        {
            try
            {
                var parsed = JsonConvert.DeserializeObject<Dictionary<string, object>>(jsonBody);
                return parsed != null && parsed.TryGetValue("id", out var id) ? id?.ToString() : null;
            }
            catch (Exception ex)
            {
                Debug.LogError($"[SessionBootstrap] No se pudo leer el id de la respuesta: {ex.Message}");
                return null;
            }
        }
    }
}

using System;
using System.Collections.Generic;
using System.Text;
using NativeWebSocket;
using Newtonsoft.Json;
using UnityEngine;

namespace NeuroAdaptiveVR.Networking
{
    /// <summary>
    /// SessionCommunicationClient (spec seccion 14): integracion
    /// WebSocket/REST con el backend FastAPI. Recibe comandos de
    /// adaptacion y emite telemetria.
    ///
    /// ESTADO EN FASE 1: implementacion funcional del "walking skeleton"
    /// que pide M1 (Technical Feasibility) -- conectar, mandar PING,
    /// recibir PONG, mandar un SESSION_EVENT y recibir el ACK. El
    /// vocabulario completo de eventos conductuales (spec 11.1) y los
    /// comandos de adaptacion ESL/LAL llegan en fases posteriores (3 y 5).
    ///
    /// DEPENDENCIA: paquete UPM NativeWebSocket
    /// (https://github.com/endel/NativeWebSocket.git#upm).
    /// System.Net.WebSockets no funciona de forma confiable en builds
    /// IL2CPP para Quest, por eso no se usa aca.
    /// </summary>
    public class SessionCommunicationClient : MonoBehaviour
    {
        [Header("Backend connection")]
        [Tooltip("ws://localhost:8000 corriendo en el Editor. Para un build en el Quest, la IP LAN de la PC.")]
        [SerializeField] private string backendBaseUrl = "ws://localhost:8000";

        [Tooltip("Se puede pegar a mano, o dejar que SessionBootstrap lo cree via REST.")]
        [SerializeField] private string sessionId;

        [Header("Heartbeat")]
        [SerializeField] private float pingIntervalSeconds = 5f;

        public event Action OnConnected;
        public event Action OnDisconnected;
        public event Action<IncomingMessage> OnMessageReceived;

        private WebSocket _socket;
        private float _pingTimer;
        private bool _isConnected;

        public bool IsConnected => _isConnected;
        public string SessionId => sessionId;

        public void Configure(string newSessionId)
        {
            sessionId = newSessionId;
        }

        /// <summary>
        /// Abre el WebSocket. Es async void a proposito: NativeWebSocket
        /// no devuelve el control de Connect() hasta que el socket cierra,
        /// asi que no se puede await desde Start() sin bloquear el flujo.
        /// </summary>
        public async void Connect()
        {
            if (string.IsNullOrWhiteSpace(sessionId))
            {
                Debug.LogError("[SessionCommunicationClient] sessionId vacio. " +
                               "Usa Configure(), pegalo en el Inspector, o agrega SessionBootstrap.");
                return;
            }

            string url = $"{backendBaseUrl}/ws/session/{sessionId}";
            Debug.Log($"[SessionCommunicationClient] Conectando a {url}");

            _socket = new WebSocket(url);

            _socket.OnOpen += () =>
            {
                _isConnected = true;
                Debug.Log("[SessionCommunicationClient] WS abierto.");
                OnConnected?.Invoke();
            };

            _socket.OnError += (errMsg) =>
            {
                Debug.LogError($"[SessionCommunicationClient] WS error: {errMsg}");
            };

            _socket.OnClose += (closeCode) =>
            {
                _isConnected = false;
                Debug.Log($"[SessionCommunicationClient] WS cerrado ({closeCode}).");
                OnDisconnected?.Invoke();
            };

            _socket.OnMessage += (bytes) =>
            {
                string json = Encoding.UTF8.GetString(bytes);
                Debug.Log($"[SessionCommunicationClient] <- {json}");
                try
                {
                    var msg = JsonConvert.DeserializeObject<IncomingMessage>(json);
                    OnMessageReceived?.Invoke(msg);
                }
                catch (Exception ex)
                {
                    Debug.LogError($"[SessionCommunicationClient] No se pudo parsear el mensaje: {ex.Message}");
                }
            };

            await _socket.Connect();
        }

        public void SendPing()
        {
            SendMessageInternal(new OutgoingMessage
            {
                Type = "PING",
                ClientTimestamp = DateTime.UtcNow.ToString("o"),
            });
        }

        public void SendSessionEvent(string eventType, Dictionary<string, object> payload = null)
        {
            SendMessageInternal(new OutgoingMessage
            {
                Type = "SESSION_EVENT",
                EventType = eventType,
                ClientTimestamp = DateTime.UtcNow.ToString("o"),
                Payload = payload ?? new Dictionary<string, object>(),
            });
        }

        public void SendValidationEvent(string component, string status, Dictionary<string, object> payload = null)
        {
            SendMessageInternal(new OutgoingMessage
            {
                Type = "VALIDATION_EVENT",
                Component = component,
                Status = status,
                ClientTimestamp = DateTime.UtcNow.ToString("o"),
                Payload = payload ?? new Dictionary<string, object>(),
            });
        }

        private void SendMessageInternal(OutgoingMessage msg)
        {
            if (!_isConnected || _socket == null)
            {
                Debug.LogWarning("[SessionCommunicationClient] Sin conexion; mensaje descartado.");
                return;
            }

            string json = JsonConvert.SerializeObject(msg);
            Debug.Log($"[SessionCommunicationClient] -> {json}");

            // SendText devuelve Task; el descarte explicito evita el warning CS4014.
            _ = _socket.SendText(json);
        }

        private void Update()
        {
            // NativeWebSocket entrega los callbacks en el hilo principal solo
            // si se bombea la cola cada frame. Sin esto, OnMessage nunca corre.
#if !UNITY_WEBGL || UNITY_EDITOR
            _socket?.DispatchMessageQueue();
#endif

            if (!_isConnected) return;

            _pingTimer += Time.deltaTime;
            if (_pingTimer >= pingIntervalSeconds)
            {
                _pingTimer = 0f;
                SendPing();
            }
        }

        private async void OnApplicationQuit()
        {
            if (_socket != null)
            {
                await _socket.Close();
                _socket = null;
            }
        }
    }
}

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
    /// recibir PONG, mandar un SESSION_EVENT y recibir el ACK.
    ///
    /// F5a (14 Oct) · reconnection. On 7 Oct session 98752f4e lost its
    /// socket when the backend reloaded (uvicorn --reload saw a .py change)
    /// and every event after that was dropped ("Sin conexion; mensaje
    /// descartado"); S3 then stopped the session. Now:
    /// - an unexpected close schedules a reconnect with a growing delay
    ///   (ReconnectPolicy: 0.5, 1, 2, 4, then every 5 s), until it works;
    /// - while disconnected, SESSION_EVENT and VALIDATION_EVENT messages are
    ///   kept in order in a bounded queue (OutgoingQueue) instead of dropped,
    ///   with their original client_timestamp, and flushed on reconnect;
    /// - the reconnect is recorded as a VALIDATION_EVENT UNITY_BACKEND_WS
    ///   with status RECONNECTED (gap, attempts, flushed, dropped).
    /// PINGs are never queued. A message already on the wire when the
    /// socket died can still be lost: there is no per-event ACK tracking.
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

        [Header("Reconnection (F5a, 14 Oct)")]
        [Tooltip("Reconnect by itself after an unexpected close.")]
        [SerializeField] private bool autoReconnect = true;
        [Tooltip("Events kept while disconnected; past this the newest are dropped and counted.")]
        [SerializeField] private int maxQueuedMessages = OutgoingQueue.DefaultCapacity;

        public event Action OnConnected;
        public event Action OnDisconnected;
        public event Action<IncomingMessage> OnMessageReceived;
        /// <summary>After a reconnect, once the queue has been flushed.</summary>
        public event Action OnReconnected;

        private WebSocket _socket;
        private float _pingTimer;
        private bool _isConnected;
        private bool _closing;              // quitting: never reconnect
        private bool _everConnected;
        private int _attempts;              // failed attempts since the last open
        private float _reconnectAt = -1f;   // realtime of the next attempt, -1 = none
        private float _disconnectedAt = -1f;
        private OutgoingQueue _queue;

        public bool IsConnected => _isConnected;
        public string SessionId => sessionId;
        public int QueuedMessages => _queue?.Count ?? 0;

        private void Awake()
        {
            _queue = new OutgoingQueue(maxQueuedMessages);
        }

        public void Configure(string newSessionId)
        {
            sessionId = newSessionId;
        }

        /// <summary>
        /// Abre el WebSocket. Es async void a proposito: NativeWebSocket
        /// no devuelve el control de Connect() hasta que el socket cierra,
        /// asi que no se puede await desde Start() sin bloquear el flujo.
        ///
        /// Each call makes a new socket; the handlers ignore events from an
        /// older one, so a late close of a dead socket cannot touch the new one.
        /// </summary>
        public async void Connect()
        {
            if (string.IsNullOrWhiteSpace(sessionId))
            {
                Debug.LogError("[SessionCommunicationClient] sessionId vacio. " +
                               "Usa Configure(), pegalo en el Inspector, o agrega SessionBootstrap.");
                return;
            }
            if (_queue == null) _queue = new OutgoingQueue(maxQueuedMessages);

            string url = $"{backendBaseUrl}/ws/session/{sessionId}";
            Debug.Log($"[SessionCommunicationClient] Conectando a {url}" +
                      (_attempts > 0 ? $" (reconnect attempt {_attempts + 1})" : ""));

            var socket = new WebSocket(url);
            _socket = socket;
            _reconnectAt = -1f;

            socket.OnOpen += () =>
            {
                if (socket != _socket) return;
                bool reconnect = _everConnected;
                int attempts = _attempts + 1;
                _isConnected = true;
                _everConnected = true;
                _attempts = 0;
                Debug.Log("[SessionCommunicationClient] WS abierto.");
                OnConnected?.Invoke();
                if (reconnect) FlushAfterReconnect(attempts);
            };

            socket.OnError += (errMsg) =>
            {
                if (socket != _socket) return;
                Debug.LogError($"[SessionCommunicationClient] WS error: {errMsg}");
            };

            socket.OnClose += (closeCode) =>
            {
                if (socket != _socket) return;
                bool wasConnected = _isConnected;
                _isConnected = false;
                Debug.Log($"[SessionCommunicationClient] WS cerrado ({closeCode}).");
                if (wasConnected)
                {
                    _disconnectedAt = Time.realtimeSinceStartup;
                    OnDisconnected?.Invoke();
                }
                ScheduleReconnect();
            };

            socket.OnMessage += (bytes) =>
            {
                if (socket != _socket) return;
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

            try
            {
                await socket.Connect();
            }
            catch (Exception ex)
            {
                // NativeWebSocket reports through OnError/OnClose; this is only
                // for an exception that escapes it, so the loop still retries.
                if (socket == _socket)
                {
                    Debug.LogError($"[SessionCommunicationClient] Connect failed: {ex.Message}");
                    _isConnected = false;
                    ScheduleReconnect();
                }
            }
        }

        private void ScheduleReconnect()
        {
            if (_closing || !autoReconnect || !_everConnected || _reconnectAt >= 0f) return;
            float delay = ReconnectPolicy.DelaySeconds(_attempts);
            _attempts++;
            _reconnectAt = Time.realtimeSinceStartup + delay;
            Debug.LogWarning($"[SessionCommunicationClient] Reconnecting in {delay:0.0} s " +
                             $"(attempt {_attempts}; {QueuedMessages} events queued).");
        }

        private void FlushAfterReconnect(int attempts)
        {
            long gapMs = _disconnectedAt >= 0f
                ? (long)((Time.realtimeSinceStartup - _disconnectedAt) * 1000f) : -1;
            int dropped = _queue.Dropped;
            var pending = _queue.DrainAll();
            foreach (var msg in pending) SendNow(msg);
            Debug.LogWarning($"[SessionCommunicationClient] Reconnected after {gapMs} ms and {attempts} " +
                             $"attempt(s): {pending.Count} queued events sent, {dropped} dropped.");

            SendValidationEvent("UNITY_BACKEND_WS", "RECONNECTED", new Dictionary<string, object>
            {
                { "gap_ms", gapMs },
                { "attempts", attempts },
                { "flushed", pending.Count },
                { "dropped", dropped },
            });
            _disconnectedAt = -1f;
            OnReconnected?.Invoke();
        }

        public void SendPing()
        {
            if (!_isConnected) return;   // a ping is only meaningful now: never queued
            SendNow(new OutgoingMessage
            {
                Type = "PING",
                ClientTimestamp = DateTime.UtcNow.ToString("o"),
            });
        }

        public void SendSessionEvent(string eventType, Dictionary<string, object> payload = null)
        {
            SendOrQueue(new OutgoingMessage
            {
                Type = "SESSION_EVENT",
                EventType = eventType,
                ClientTimestamp = DateTime.UtcNow.ToString("o"),
                Payload = payload ?? new Dictionary<string, object>(),
            });
        }

        public void SendValidationEvent(string component, string status, Dictionary<string, object> payload = null)
        {
            SendOrQueue(new OutgoingMessage
            {
                Type = "VALIDATION_EVENT",
                Component = component,
                Status = status,
                ClientTimestamp = DateTime.UtcNow.ToString("o"),
                Payload = payload ?? new Dictionary<string, object>(),
            });
        }

        private void SendOrQueue(OutgoingMessage msg)
        {
            if (_isConnected && _socket != null)
            {
                SendNow(msg);
                return;
            }
            if (_queue == null) _queue = new OutgoingQueue(maxQueuedMessages);
            if (!_queue.Enqueue(msg) && _queue.Dropped == 1)
                Debug.LogError($"[SessionCommunicationClient] Queue full ({_queue.Capacity}): events are being " +
                               "dropped until the connection is back.");
            else if (_queue.Count == 1)
                Debug.LogWarning("[SessionCommunicationClient] Sin conexion; events are queued until it is back.");
        }

        private void SendNow(OutgoingMessage msg)
        {
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

            if (_reconnectAt >= 0f && Time.realtimeSinceStartup >= _reconnectAt && !_closing)
            {
                _reconnectAt = -1f;
                Connect();
            }

            if (!_isConnected) return;

            // Unscaled: a paused or slowed timeScale must not stop the heartbeat.
            _pingTimer += Time.unscaledDeltaTime;
            if (_pingTimer >= pingIntervalSeconds)
            {
                _pingTimer = 0f;
                SendPing();
            }
        }

        private async void OnApplicationQuit()
        {
            _closing = true;
            if (_socket != null)
            {
                var socket = _socket;
                _socket = null;
                await socket.Close();
            }
        }
    }

    /// <summary>
    /// Delay before each reconnect attempt: 0.5, 1, 2, 4 s, then every 5 s.
    /// Short at first because the usual cause is a backend restart (~2 s).
    /// </summary>
    public static class ReconnectPolicy
    {
        private static readonly float[] Steps = { 0.5f, 1f, 2f, 4f };
        public const float MaxDelaySeconds = 5f;

        public static float DelaySeconds(int failedAttempts)
            => failedAttempts < 0 ? Steps[0]
             : failedAttempts < Steps.Length ? Steps[failedAttempts] : MaxDelaySeconds;
    }

    /// <summary>
    /// Bounded FIFO for the messages produced while disconnected. Keeps the
    /// order (the backend projects events in arrival order) and, when full,
    /// drops the newest and counts them, so the oldest context survives.
    /// Plain class so the harness can test it without a socket.
    /// </summary>
    public sealed class OutgoingQueue
    {
        public const int DefaultCapacity = 5000;   // ~10 min of a busy S7

        private readonly Queue<OutgoingMessage> _items = new();

        public OutgoingQueue(int capacity = DefaultCapacity) { Capacity = Math.Max(1, capacity); }

        public int Capacity { get; }
        public int Count => _items.Count;
        public int Dropped { get; private set; }

        public bool Enqueue(OutgoingMessage msg)
        {
            if (msg == null) return false;
            if (_items.Count >= Capacity) { Dropped++; return false; }
            _items.Enqueue(msg);
            return true;
        }

        /// <summary>Everything queued, oldest first; the queue and the drop count start again.</summary>
        public List<OutgoingMessage> DrainAll()
        {
            var all = new List<OutgoingMessage>(_items);
            _items.Clear();
            Dropped = 0;
            return all;
        }
    }
}

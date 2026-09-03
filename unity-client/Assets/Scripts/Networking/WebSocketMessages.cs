using System.Collections.Generic;
using Newtonsoft.Json;

namespace NeuroAdaptiveVR.Networking
{
    /// <summary>
    /// Contratos de mensajes del WebSocket de sesion. Deben coincidir
    /// exactamente con el protocolo documentado en
    /// backend/app/api/routes/websocket.py -- si un campo cambia de un
    /// lado, cambia del otro en el mismo commit.
    ///
    /// FASE 1 (corregido 28 ago 2026): la version anterior mandaba el
    /// payload como string bajo la llave "payload_json". El backend lee
    /// message.get("payload", {}) y espera un OBJETO bajo la llave
    /// "payload", asi que los eventos se guardaban con payload vacio sin
    /// dar error. Ahora se usa Newtonsoft.Json (ya presente en el
    /// proyecto) y un Dictionary, que serializa como objeto JSON real.
    /// </summary>
    public class OutgoingMessage
    {
        [JsonProperty("type")]
        public string Type;

        [JsonProperty("client_timestamp", NullValueHandling = NullValueHandling.Ignore)]
        public string ClientTimestamp;

        /// <summary>Solo para SESSION_EVENT.</summary>
        [JsonProperty("event_type", NullValueHandling = NullValueHandling.Ignore)]
        public string EventType;

        /// <summary>Solo para VALIDATION_EVENT.</summary>
        [JsonProperty("component", NullValueHandling = NullValueHandling.Ignore)]
        public string Component;

        /// <summary>Solo para VALIDATION_EVENT.</summary>
        [JsonProperty("status", NullValueHandling = NullValueHandling.Ignore)]
        public string Status;

        /// <summary>
        /// Objeto libre. NullValueHandling.Ignore evita mandar llaves
        /// vacias en un PING.
        /// </summary>
        [JsonProperty("payload", NullValueHandling = NullValueHandling.Ignore)]
        public Dictionary<string, object> Payload;
    }

    public class IncomingMessage
    {
        [JsonProperty("type")]
        public string Type;

        [JsonProperty("server_time")]
        public string ServerTime;

        /// <summary>
        /// Nullable a proposito: el backend (`session_clock.offset_ms`)
        /// devuelve None cuando el mensaje no traia `client_timestamp`, y
        /// eso viaja como `null` en el JSON. Con un double no-nullable,
        /// Newtonsoft lanza excepcion al deserializar y el PONG se pierde
        /// en silencio.
        /// </summary>
        [JsonProperty("offset_ms")]
        public double? OffsetMs;

        /// <summary>Solo ACK: "SESSION_EVENT" | "VALIDATION_EVENT".</summary>
        [JsonProperty("of")]
        public string Of;

        /// <summary>
        /// El backend devuelve un int para el ACK de SESSION_EVENT y un
        /// string para el de VALIDATION_EVENT, asi que se deserializa
        /// como object para tolerar ambos. (Inconsistencia conocida del
        /// backend, anotada para limpiar en Fase 2.)
        /// </summary>
        [JsonProperty("id")]
        public object Id;

        /// <summary>Solo ERROR.</summary>
        [JsonProperty("detail")]
        public string Detail;
    }
}

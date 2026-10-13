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
        /// Id del evento persistido que confirma el ACK. Siempre string.
        ///
        /// FASE 2, paso 0 (7 sep 2026): antes el backend mandaba un int
        /// para el ACK de SESSION_EVENT (PK BIGINT) y un string para el de
        /// VALIDATION_EVENT (PK UUID), asi que este campo era `object`
        /// para tolerar ambos. El backend ya normaliza los dos a string
        /// (ver app/api/routes/websocket.py), de modo que el campo puede
        /// tiparse. Si vuelve a llegar un numero crudo, Newtonsoft lo
        /// convierte a su representacion textual sin lanzar.
        /// </summary>
        [JsonProperty("id")]
        public string Id;

        /// <summary>Solo ERROR.</summary>
        [JsonProperty("detail")]
        public string Detail;

        // --- DECISION (F5a, Planteamiento_Tecnico_F5a.md §8.1) ---
        // One per answered trial of an adaptive S7, NO_CHANGE included. Sent by
        // the backend during the feedback of that trial; applied (or skipped)
        // by SessionFlowRunner between trials. Nullable where the backend can
        // send null, for the same reason as OffsetMs.

        [JsonProperty("decision_id")] public string DecisionId;
        [JsonProperty("trial_id")] public string TrialId;
        /// <summary>NO_CHANGE | CHANGE_ENVIRONMENT | CHANGE_ASSISTANCE.</summary>
        [JsonProperty("action")] public string Action;
        /// <summary>ESL | LAL, null with NO_CHANGE.</summary>
        [JsonProperty("dimension")] public string Dimension;
        [JsonProperty("from_level")] public string FromLevel;
        [JsonProperty("to_level")] public string ToLevel;
        /// <summary>D9: the raise opens a window of proactive cues.</summary>
        [JsonProperty("proactive_cues")] public bool? ProactiveCues;
        [JsonProperty("learner_state")] public string LearnerState;
        [JsonProperty("cause")] public string Cause;
        [JsonProperty("confidence")] public double? Confidence;
        [JsonProperty("reason_code")] public string ReasonCode;
        [JsonProperty("explanation")] public string Explanation;
        [JsonProperty("cooldown_until_trial")] public int? CooldownUntilTrial;
    }
}

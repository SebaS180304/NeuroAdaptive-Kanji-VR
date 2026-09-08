using System.Collections.Generic;
using NeuroAdaptiveVR.Core;
using NeuroAdaptiveVR.Data;
using NeuroAdaptiveVR.Networking;
using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Punto unico de emision de eventos conductuales hacia
    /// SessionCommunicationClient (spec seccion 14). Vocabulario en la spec
    /// 11.1; forma del payload en database/EVENT_CONTRACT.md.
    ///
    /// FASE 2: este controlador es dueño del bloque de contexto. Un emisor
    /// pasa solo los campos propios de su evento y **no puede omitir el
    /// contexto, porque nunca lo arma**. Esa es toda la razon de que el
    /// contexto viva aca y no en cada llamador: el criterio de aceptacion 8
    /// de Fase 2 exige que cada evento lleve sus identificadores, y una
    /// convencion documentada no es una garantia -- el paso 0 de esta fase
    /// encontro dos contratos que el codigo afirmaba cumplir y no cumplia.
    ///
    /// NOTA (28 ago 2026): el payload paso de ser un string con JSON
    /// serializado a un Dictionary. El backend espera un OBJETO bajo la
    /// llave "payload" (ver backend/app/api/routes/websocket.py); mandar
    /// un string dejaba el payload vacio en la base sin dar error.
    /// </summary>
    [RequireComponent(typeof(SessionCommunicationClient))]
    public class BehaviorTelemetryController : MonoBehaviour
    {
        [SerializeField] private SessionCommunicationClient communicationClient;

        [Header("Contexto de sesion (se actualiza desde los controladores)")]
        [SerializeField] private GameFlowState currentState = GameFlowState.S0_SessionInitialization;
        [SerializeField] private StimulationOrAssistanceLevel currentEsl = StimulationOrAssistanceLevel.Off;
        [SerializeField] private StimulationOrAssistanceLevel currentLal = StimulationOrAssistanceLevel.Off;

        private TrialContext? _activeTrial;

        public GameFlowState CurrentState => currentState;
        public TrialContext? ActiveTrial => _activeTrial;

        private void Awake()
        {
            if (communicationClient == null)
                communicationClient = GetComponent<SessionCommunicationClient>();
        }

        // ------------------------------------------------------------------
        // Contexto
        // ------------------------------------------------------------------

        public void SetState(GameFlowState state) => currentState = state;

        public void SetLevels(StimulationOrAssistanceLevel esl, StimulationOrAssistanceLevel lal)
        {
            currentEsl = esl;
            currentLal = lal;
        }

        /// <summary>Abre un trial. Todo evento emitido hasta EndTrial lleva el bloque de trial.</summary>
        public void BeginTrial(TrialContext trial)
        {
            if (_activeTrial.HasValue)
            {
                Debug.LogWarning($"[BehaviorTelemetry] BeginTrial({trial.TrialId}) con " +
                                 $"{_activeTrial.Value.TrialId} todavia abierto. Se cierra el anterior; " +
                                 "revisa que TRIAL_COMPLETED se emita siempre antes del siguiente trial.");
            }
            _activeTrial = trial;
        }

        public void EndTrial() => _activeTrial = null;

        // ------------------------------------------------------------------
        // Emision
        // ------------------------------------------------------------------

        /// <summary>
        /// Emite un evento. `fields` son solo los campos propios del evento;
        /// el bloque de contexto (y el de trial, si hay uno abierto) los
        /// agrega este metodo.
        /// </summary>
        public void Emit(string eventType, Dictionary<string, object> fields = null)
        {
            if (TelemetryEvents.RequiresTrialContext(eventType) && !_activeTrial.HasValue)
            {
                // Error y no warning: un evento de trial sin trial_id es
                // exactamente la fila que Fase 3 no va a poder migrar, y se
                // guardaria sin protestar porque el payload es JSONB.
                Debug.LogError($"[BehaviorTelemetry] '{eventType}' requiere un trial abierto y no hay " +
                               "ninguno. El evento NO se emite. Llama a BeginTrial primero.");
                return;
            }

            communicationClient.SendSessionEvent(eventType, BuildPayload(fields));
        }

        /// <summary>Atajo para el caso de un solo par clave/valor.</summary>
        public void Emit(string eventType, string key, object value)
            => Emit(eventType, new Dictionary<string, object> { { key, value } });

        private Dictionary<string, object> BuildPayload(Dictionary<string, object> fields)
        {
            var payload = new Dictionary<string, object>
            {
                { TelemetryContract.KeySchemaVersion, TelemetryContract.PayloadSchemaVersion },
                { TelemetryContract.KeyState, currentState.ToWireValue() },
                { TelemetryContract.KeySessionElapsedMs, SessionClock.ElapsedMs() },
                { TelemetryContract.KeyEsl, currentEsl.ToWireValue() },
                { TelemetryContract.KeyLal, currentLal.ToWireValue() },
            };

            if (_activeTrial.HasValue)
            {
                var t = _activeTrial.Value;
                payload[TelemetryContract.KeyTrialId] = t.TrialId;
                payload[TelemetryContract.KeyTrialType] = t.TrialType.ToWireValue();
                payload[TelemetryContract.KeyTrialSequence] = t.TrialSequence;
                payload[TelemetryContract.KeyKanjiId] = t.KanjiId;
            }

            if (fields == null) return payload;

            foreach (var kv in fields)
            {
                // El contexto gana. Si un emisor intenta pisar `state` o
                // `trial_id` es un bug del emisor, no una personalizacion:
                // el punto del bloque de contexto es que sea el mismo para
                // todos los eventos del mismo momento.
                if (payload.ContainsKey(kv.Key))
                {
                    Debug.LogWarning($"[BehaviorTelemetry] El emisor intenta sobrescribir el campo de " +
                                     $"contexto '{kv.Key}'. Se conserva el valor del contexto.");
                    continue;
                }
                payload[kv.Key] = kv.Value;
            }

            return payload;
        }
    }
}

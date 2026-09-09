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
    /// Este controlador es dueño del bloque de contexto. Un emisor pasa solo
    /// los campos propios de su evento y **no puede omitir el contexto,
    /// porque nunca lo arma**.
    ///
    /// CORRECCION (9 sep 2026): antes guardaba sus propias copias de estado,
    /// ESL y LAL, que alguien tenia que mantener al dia con SetState/SetLevels.
    /// Nadie las mantenia, asi que los eventos salieron con
    /// state=S1_WELCOME_ORIENTATION y lal=OFF mientras el trial_id decia S7 y
    /// los cues concedidos eran los de MEDIUM y HIGH. El payload se
    /// contradecia a si mismo y la base guardo 19 trials con el LAL
    /// equivocado.
    ///
    /// Ahora **no guarda ninguna copia**: lee los tres valores de quien los
    /// posee en el momento de emitir. Un valor que solo existe en un sitio no
    /// puede desincronizarse, que es una garantia distinta --y mas fuerte--
    /// que acordarse de sincronizar dos.
    /// </summary>
    [RequireComponent(typeof(SessionCommunicationClient))]
    public class BehaviorTelemetryController : MonoBehaviour
    {
        [Header("Salida")]
        [SerializeField] private SessionCommunicationClient communicationClient;

        [Header("Fuentes del bloque de contexto")]
        [Tooltip("Dueño del estado S0-S10.")]
        [SerializeField] private GameFlowController gameFlow;

        [Tooltip("Dueño del nivel ESL.")]
        [SerializeField] private EnvironmentalStimulationController stimulation;

        [Tooltip("Dueño del nivel LAL.")]
        [SerializeField] private LearningAssistanceController assistance;

        private TrialContext? _activeTrial;
        private bool _warnedMissingSource;

        /// <summary>Estado actual, leido de su dueño. No hay copia local.</summary>
        public GameFlowState CurrentState
            => gameFlow != null ? gameFlow.CurrentState : GameFlowState.S0_SessionInitialization;

        public TrialContext? ActiveTrial => _activeTrial;

        private void Awake()
        {
            if (communicationClient == null) communicationClient = GetComponent<SessionCommunicationClient>();
            if (gameFlow == null) gameFlow = GetComponent<GameFlowController>();
            if (stimulation == null) stimulation = GetComponent<EnvironmentalStimulationController>();
            if (assistance == null) assistance = GetComponent<LearningAssistanceController>();
        }

        // ------------------------------------------------------------------
        // Trial
        // ------------------------------------------------------------------

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

        public void Emit(string eventType, Dictionary<string, object> fields = null)
        {
            if (TelemetryEvents.RequiresTrialContext(eventType) && !_activeTrial.HasValue)
            {
                Debug.LogError($"[BehaviorTelemetry] '{eventType}' requiere un trial abierto y no hay " +
                               "ninguno. El evento NO se emite. Llama a BeginTrial primero.");
                return;
            }

            communicationClient.SendSessionEvent(eventType, BuildPayload(fields));
        }

        public void Emit(string eventType, string key, object value)
            => Emit(eventType, new Dictionary<string, object> { { key, value } });

        private Dictionary<string, object> BuildPayload(Dictionary<string, object> fields)
        {
            WarnOnceIfSourceMissing();

            var payload = new Dictionary<string, object>
            {
                { TelemetryContract.KeySchemaVersion, TelemetryContract.PayloadSchemaVersion },
                { TelemetryContract.KeyState, CurrentState.ToWireValue() },
                { TelemetryContract.KeySessionElapsedMs, SessionClock.ElapsedMs() },
                { TelemetryContract.KeyEsl, CurrentEsl().ToWireValue() },
                { TelemetryContract.KeyLal, CurrentLal().ToWireValue() },
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

        private StimulationOrAssistanceLevel CurrentEsl()
            => stimulation != null ? stimulation.CurrentLevel : StimulationOrAssistanceLevel.Off;

        private StimulationOrAssistanceLevel CurrentLal()
            => assistance != null ? assistance.CurrentLevel : StimulationOrAssistanceLevel.Off;

        /// <summary>
        /// Una fuente ausente no aborta la emision --perder telemetria es peor
        /// que grabarla incompleta-- pero tiene que ser ruidosa. Un OFF por
        /// defecto es indistinguible de un OFF real en la base, y ese es
        /// justamente el modo de fallo que produjo 19 trials con el LAL
        /// equivocado.
        /// </summary>
        private void WarnOnceIfSourceMissing()
        {
            if (_warnedMissingSource) return;
            if (gameFlow != null && stimulation != null && assistance != null) return;

            _warnedMissingSource = true;
            Debug.LogError("[BehaviorTelemetry] Faltan fuentes del bloque de contexto en este GameObject: " +
                           $"{(gameFlow == null ? "GameFlowController " : "")}" +
                           $"{(stimulation == null ? "EnvironmentalStimulationController " : "")}" +
                           $"{(assistance == null ? "LearningAssistanceController" : "")}" +
                           ". Los campos correspondientes van a salir con su valor por defecto, que en " +
                           "la base es indistinguible de un valor real.");
        }
    }
}

using System;
using System.Collections;
using System.Collections.Generic;
using NeuroAdaptiveVR.Data;
using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Sistema de respuesta: el ciclo de un trial, una sola vez, para los
    /// cuatro estados que lo usan (S5 asociacion guiada, S6 calibracion,
    /// S7 retrieval, S8 assessment).
    ///
    /// presentar prompt y opciones -> seleccion -> validacion -> feedback ->
    /// cerrar y emitir.
    ///
    /// Los tres tipos de trial (spec 6) son variaciones de **presentacion**
    /// sobre este mismo ciclo, no mecanismos distintos. Por eso no hay ni un
    /// solo `if (trialType == ...)` en el flujo de control de esta clase: lo
    /// unico que depende del tipo es que texto se muestra --lo resuelve quien
    /// arma el TrialRequest-- y que cue concede LAL, que lo resuelve
    /// LearningAssistanceController.
    ///
    /// Reutilizar el mecanismo entre S6 y S7 no es una comodidad de
    /// implementacion: es lo que hace que los tiempos de respuesta de la
    /// calibracion sean comparables con los del bloque experimental
    /// (spec 5.4). Un `if` por estado aqui rompe esa comparabilidad en
    /// silencio.
    /// </summary>
    [RequireComponent(typeof(BehaviorTelemetryController))]
    public class ResponseSystemController : MonoBehaviour
    {
        [Header("Dependencias")]
        [SerializeField] private BehaviorTelemetryController telemetry;
        [SerializeField] private LearningAssistanceController assistance;
        [SerializeField] private PronunciationAudioController pronunciation;

        [Tooltip("Cualquier MonoBehaviour que implemente ITrialPresenter.")]
        [SerializeField] private MonoBehaviour presenterBehaviour;

        [Header("Parametros de trial")]
        [Tooltip("Numero fijo de opciones. LAL NO puede cambiarlo (spec 9.3).")]
        [SerializeField] private int optionCount = 4;

        [Tooltip("Segundos que permanece el feedback antes de cerrar el trial.")]
        [SerializeField] private float feedbackSeconds = 1.5f;

        private ITrialPresenter _presenter;

        // Estado del trial en curso
        private TrialRequest _request;
        private TrialContext _context;
        private double _responseClockStart;
        private bool _awaitingResponse;
        private int _hintCount;
        private LalCue _cuesPresented;

        /// <summary>Se dispara al cerrar el trial, con el resultado completo.</summary>
        public event Action<TrialResult> OnTrialCompleted;

        public bool TrialInProgress => _request != null;

        private void Awake()
        {
            if (telemetry == null) telemetry = GetComponent<BehaviorTelemetryController>();
            if (assistance == null) assistance = GetComponent<LearningAssistanceController>();
            if (pronunciation == null) pronunciation = GetComponent<PronunciationAudioController>();

            if (assistance == null)
            {
                Debug.LogError("[ResponseSystem] Falta LearningAssistanceController en este GameObject. " +
                               "Es quien decide que cue concede LAL para cada tipo de trial (spec 9.1); " +
                               "sin el no se puede abrir ningun trial.");
                return;
            }

            _presenter = presenterBehaviour as ITrialPresenter;
            if (_presenter == null)
            {
                Debug.LogError("[ResponseSystem] presenterBehaviour no implementa ITrialPresenter. " +
                               "Sin presentador no se puede correr ningun trial.");
                return;
            }

            _presenter.OnOptionChosen += HandleOptionChosen;
            _presenter.OnHintRequested += HandleHintRequested;
        }

        private void OnDestroy()
        {
            if (_presenter == null) return;
            _presenter.OnOptionChosen -= HandleOptionChosen;
            _presenter.OnHintRequested -= HandleHintRequested;
        }

        // ------------------------------------------------------------------
        // Inicio
        // ------------------------------------------------------------------

        public void BeginTrial(TrialRequest request)
        {
            if (request == null) { Debug.LogError("[ResponseSystem] TrialRequest nulo."); return; }
            if (_presenter == null) return;

            if (TrialInProgress)
            {
                Debug.LogError($"[ResponseSystem] Ya hay un trial abierto ({_context.TrialId}). " +
                               "Se ignora el nuevo. Cada trial debe cerrarse antes del siguiente.");
                return;
            }

            if (!ValidateRequest(request)) return;

            // El estado sale del controlador de telemetria, que es tambien
            // quien estampa el `state` del bloque de contexto. Una sola
            // lectura, un solo valor: el prefijo del trial_id y el state del
            // payload no pueden discrepar.
            GameFlowState state = telemetry.CurrentState;
            WarnIfStateDoesNotRunTrials(state);

            _request = request;
            _context = request.ToTrialContext(state);
            _hintCount = 0;
            _cuesPresented = LalCue.None;

            telemetry.BeginTrial(_context);

            LalCue available = assistance.AvailableCuesNow(request.TrialType);

            var optionIds = new List<string>(request.Options.Count);
            string correctOptionId = null;
            foreach (var o in request.Options)
            {
                optionIds.Add(o.OptionId);
                if (o.IsCorrect) correctOptionId = o.OptionId;
            }

            telemetry.Emit(TelemetryEvents.TrialStarted, new Dictionary<string, object>
            {
                { "kanji_char", request.Target.character },
                { "options", optionIds },          // en el orden presentado
                { "correct_option", correctOptionId },
                { "hint_available", available != LalCue.None },
            });

            _presenter.SetHintAvailable(available != LalCue.None);
            _presenter.Present(request.TrialType, BuildPromptText(request), request.Options);

            // El cronometro arranca DESPUES de presentar. El tiempo de
            // presentacion y animacion no es tiempo de respuesta -- ver
            // database/EVENT_CONTRACT.md seccion 8.
            _responseClockStart = Time.realtimeSinceStartupAsDouble;
            _awaitingResponse = true;
        }

        /// <summary>
        /// Texto del prompt segun el tipo (spec 6). Es lo unico que ramifica
        /// por tipo de trial, y es presentacion pura.
        /// </summary>
        private static string BuildPromptText(TrialRequest r) => r.TrialType switch
        {
            RetrievalTrialType.MeaningToKanji => r.Target.targetMeaning,   // T1: significado
            RetrievalTrialType.KanjiToMeaning => r.Target.character,       // T2: kanji
            RetrievalTrialType.KanjiToReading => r.Target.character,       // T3: kanji
            _ => r.Target.character,
        };

        /// <summary>
        /// Los trials solo ocurren en cuatro estados (spec 12, matriz de
        /// recoleccion de datos): S5 asociacion guiada, S6 calibracion,
        /// S7 retrieval y S8 assessment.
        ///
        /// Warning y no error: correr un trial fuera de esos estados es casi
        /// seguro un fallo de cableado, pero abortarlo impediria probar el
        /// ciclo aisladamente. Lo que no puede pasar es que ocurra en silencio.
        /// </summary>
        private static void WarnIfStateDoesNotRunTrials(GameFlowState state)
        {
            switch (state)
            {
                case GameFlowState.S5_StandardizedLearning:
                case GameFlowState.S6_GuidedPracticeCalibration:
                case GameFlowState.S7_ExperimentalRetrieval:
                case GameFlowState.S8_ImmediateAssessment:
                    return;
                default:
                    Debug.LogWarning($"[ResponseSystem] Trial abierto en {state}, que no es un estado " +
                                     "de trials (spec 12: solo S5, S6, S7 y S8). El trial_id y la " +
                                     "telemetria van a llevar ese estado. Si no era la intencion, " +
                                     "haz que el GameFlowController entre al estado correcto primero.");
                    return;
            }
        }

        private bool ValidateRequest(TrialRequest request)
        {
            // El numero de opciones es fijo y LAL no puede tocarlo (spec 9.3).
            // La comprobacion esta aqui y no en un comentario porque Fase 5 va
            // a conectar un motor que cambia LAL en caliente, y este es el
            // punto donde un error de ese tipo se hace visible.
            if (request.Options.Count != optionCount)
            {
                Debug.LogError($"[ResponseSystem] El trial trae {request.Options.Count} opciones y " +
                               $"la configuracion fija {optionCount}. El numero de opciones es " +
                               "constante del experimento (spec 9.3). Trial abortado.");
                return false;
            }

            int correct = 0;
            var seen = new HashSet<string>();
            foreach (var o in request.Options)
            {
                if (o.IsCorrect) correct++;
                if (!seen.Add(o.OptionId))
                {
                    Debug.LogError($"[ResponseSystem] Opcion duplicada '{o.OptionId}'. Trial abortado.");
                    return false;
                }
            }

            if (correct != 1)
            {
                Debug.LogError($"[ResponseSystem] El trial tiene {correct} opciones correctas y debe " +
                               "tener exactamente una. Trial abortado.");
                return false;
            }

            return true;
        }

        // ------------------------------------------------------------------
        // Hint
        // ------------------------------------------------------------------

        private void HandleHintRequested()
        {
            if (!_awaitingResponse) return;

            LalCue available = assistance.AvailableCuesNow(_request.TrialType);
            if (available == LalCue.None)
            {
                // No es un error: en LOW y OFF no hay ayuda que dar. Se emite
                // igualmente, porque pedir ayuda y no recibirla es una
                // observacion conductual, no un no-evento.
                EmitHintRequested(LalCue.None);
                return;
            }

            _cuesPresented |= available;

            if ((available & LalCue.TargetReadingAudio) != 0)
            {
                // Ruta unica del audio pre-respuesta. El guard de T3 vive ahi.
                pronunciation?.TryPlayPreResponseCue(_request.TrialType, available, _request.Target);
            }

            _presenter.ShowCue(available);
            EmitHintRequested(available);
        }

        private void EmitHintRequested(LalCue granted)
        {
            _hintCount++;
            telemetry.Emit(TelemetryEvents.HintRequested, new Dictionary<string, object>
            {
                { "hint_type", CueNames(granted) },
                { "hint_available", granted != LalCue.None },
                { "time_since_trial_start_ms", ElapsedMs() },
            });
        }

        // ------------------------------------------------------------------
        // Respuesta
        // ------------------------------------------------------------------

        private void HandleOptionChosen(string optionId)
        {
            if (!_awaitingResponse) return;

            // Un paso: elegir es confirmar. El cronometro para aqui y en
            // ningun otro sitio (spec 11.1, "participant commits to an answer").
            long responseTimeMs = ElapsedMs();
            _awaitingResponse = false;

            bool isCorrect = false;
            string correctText = null;
            bool found = false;

            foreach (var o in _request.Options)
            {
                if (o.OptionId == optionId) { isCorrect = o.IsCorrect; found = true; }
                if (o.IsCorrect) correctText = o.DisplayText;
            }

            if (!found)
            {
                Debug.LogError($"[ResponseSystem] La opcion '{optionId}' no pertenece a este trial. " +
                               "Se ignora y el trial sigue abierto.");
                _awaitingResponse = true;
                return;
            }

            telemetry.Emit(TelemetryEvents.AnswerSelected, new Dictionary<string, object>
            {
                { "kanji_char", _request.Target.character },
                { "selected_option", optionId },
                { "is_correct", isCorrect },
                { "response_time_ms", responseTimeMs },
                { "timed_out", false },   // sin timeout en Fase 2; el campo existe para no cambiar la forma
            });

            StartCoroutine(CompleteTrial(isCorrect, correctText, responseTimeMs, optionId));
        }

        private IEnumerator CompleteTrial(bool isCorrect, string correctText, long responseTimeMs,
                                          string selectedOptionId)
        {
            if (_request.ImmediateFeedback)
            {
                _presenter.ShowFeedback(isCorrect, correctText);

                // El feedback post-respuesta puede repetir la lectura en los
                // tres tipos de trial, T3 incluido: ya respondio, no revela
                // nada (spec 9.2).
                pronunciation?.PlayFeedback(_request.Target);

                yield return new WaitForSecondsRealtime(feedbackSeconds);
            }

            var result = new TrialResult(
                _context.TrialId, _request.TrialType, _context.KanjiId, selectedOptionId,
                isCorrect, responseTimeMs, false, _hintCount, _cuesPresented);

            telemetry.Emit(TelemetryEvents.TrialCompleted, new Dictionary<string, object>
            {
                { "is_correct", isCorrect },
                { "response_time_ms", responseTimeMs },
                { "hint_count", _hintCount },
                { "cues_presented", CueNames(_cuesPresented) },
            });

            _presenter.Clear();
            telemetry.EndTrial();
            _request = null;

            OnTrialCompleted?.Invoke(result);
        }

        // ------------------------------------------------------------------

        private long ElapsedMs()
            => (long)((Time.realtimeSinceStartupAsDouble - _responseClockStart) * 1000.0);

        /// <summary>
        /// Los cues viajan como lista de nombres y no como entero de flags:
        /// un bitmask en un payload JSONB obliga a decodificarlo en cada
        /// consulta y no se puede filtrar con `payload -> 'cues_presented' ? 'X'`.
        /// </summary>
        private static List<string> CueNames(LalCue cues)
        {
            var names = new List<string>();
            if ((cues & LalCue.TargetReadingAudio) != 0) names.Add("TARGET_READING_AUDIO");
            if ((cues & LalCue.VisualAssociation) != 0) names.Add("VISUAL_ASSOCIATION");
            if ((cues & LalCue.ReverseSemanticAssociation) != 0) names.Add("REVERSE_SEMANTIC_ASSOCIATION");
            if ((cues & LalCue.VisualTransformation) != 0) names.Add("VISUAL_TRANSFORMATION");
            return names;
        }
    }
}

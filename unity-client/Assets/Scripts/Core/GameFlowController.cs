using System;
using NeuroAdaptiveVR.Controllers;
using NeuroAdaptiveVR.Data;
using NeuroAdaptiveVR.Networking;
using UnityEngine;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// GameFlowController (spec seccion 14): dueño de la maquina de
    /// estados S0-S9 (S10 ocurre fuera del headset) y de las
    /// transiciones entre fases estandarizadas/calibracion/adaptativa/
    /// assessment.
    ///
    /// FASE 2: emite STATE_ENTERED a traves de BehaviorTelemetryController,
    /// no directamente por el cliente WebSocket, para que el evento lleve el
    /// bloque de contexto del contrato de payload
    /// (database/EVENT_CONTRACT.md). El campo `state` del payload lo pone
    /// ahora el contexto, no este controlador.
    ///
    /// Desde el 16 de septiembre hace ademas dos cosas al entrar a un estado:
    /// comprueba el par ESL/LAL contra la matriz del Apendice A, y avisa a quien
    /// escuche --SessionBootstrap-- para que la fila de la base siga el estado
    /// real de la sesion. Las dos son guardas: no eligen nada.
    /// </summary>
    [RequireComponent(typeof(SessionCommunicationClient))]
    [RequireComponent(typeof(BehaviorTelemetryController))]
    public class GameFlowController : MonoBehaviour
    {
        [SerializeField] private BehaviorTelemetryController telemetry;

        [Header("Session context (asignado en S0)")]
        [Tooltip("Fallback de depuracion. Si la sesion trae condicion, gana la sesion: " +
                 "es un dato de experiment_sessions, no una preferencia del Editor.")]
        [SerializeField] private ExperimentalCondition condition;

        [SerializeField] private GameFlowState currentState = GameFlowState.S0_SessionInitialization;

        [Header("Guarda del Apendice A")]
        [Tooltip("Comprobar que el par ESL/LAL sea admisible en el estado al que se entra. " +
                 "Desactivarlo solo tiene sentido para probar a proposito una combinacion prohibida.")]
        [SerializeField] private bool enforceStateLevelMatrix = true;

        private EnvironmentalStimulationController _stimulation;
        private LearningAssistanceController _assistance;

        public event Action<GameFlowState> OnStateEntered;

        public GameFlowState CurrentState => currentState;

        /// <summary>
        /// La condicion de la sesion. Sale de experiment_sessions cuando hay
        /// sesion instalada; el campo del Inspector es solo el fallback.
        /// </summary>
        public ExperimentalCondition Condition
            => SessionContext.IsInstalled ? SessionContext.Condition : condition;

        /// <summary>
        /// Orden canonico de estados (spec 14.1).
        ///
        /// S2 es condicional: spec 7.3 lo limita a la primera visita. La decision
        /// se toma en AdvanceToNextState leyendo SessionContext.VisitNumber, que
        /// viene de la base; no hay un flag aparte que alguien tenga que recordar
        /// poner.
        /// </summary>
        private static readonly GameFlowState[] StateOrder =
        {
            GameFlowState.S0_SessionInitialization,
            GameFlowState.S1_WelcomeOrientation,
            GameFlowState.S2_VRTutorial,
            GameFlowState.S3_SystemValidation,
            GameFlowState.S4_EEGBaseline,
            GameFlowState.S5_StandardizedLearning,
            GameFlowState.S6_GuidedPracticeCalibration,
            GameFlowState.S7_ExperimentalRetrieval,
            GameFlowState.S8_ImmediateAssessment,
            GameFlowState.S9_SessionSummary,
        };

        private void Awake()
        {
            if (telemetry == null) telemetry = GetComponent<BehaviorTelemetryController>();
            _stimulation = GetComponent<EnvironmentalStimulationController>();
            _assistance = GetComponent<LearningAssistanceController>();

            if (telemetry == null)
            {
                Debug.LogError("[GameFlowController] Falta BehaviorTelemetryController en este " +
                               "GameObject. Sin el no se emite telemetria con el bloque de contexto.");
            }
        }

        /// <param name="applyNominalLevels">
        /// Aplicar el par ESL/LAL que la tabla del Apendice A da como nominal
        /// para este estado, ANTES de emitir STATE_ENTERED.
        ///
        /// Por omision true, y ese es el punto: si entrar a un estado no fijara
        /// sus niveles, alguien tendria que acordarse de hacerlo en cada
        /// transicion, y el 17 de septiembre quedo demostrado que no basta con
        /// acordarse. El banco de pruebas lo pasa en false porque parte de su
        /// trabajo es ejercitar combinaciones prohibidas a proposito.
        /// </param>
        public void EnterState(GameFlowState newState, bool applyNominalLevels = true)
        {
            // Este controlador es el unico dueño del estado. La telemetria lo
            // LEE de aqui al emitir, en vez de guardar una copia que alguien
            // tenga que mantener al dia -- por eso basta con asignarlo antes
            // de emitir y no hay ningun SetState que se pueda olvidar.
            currentState = newState;

            // Los niveles se aplican ANTES de emitir. Si se aplicaran despues,
            // el STATE_ENTERED saldria con el par del estado anterior y la fila
            // diria que S7 empezo con el LAL de S1.
            if (applyNominalLevels) ApplyNominalLevels(newState);

            Debug.Log($"[GameFlowController] STATE_ENTERED: {newState} (wire: {newState.ToWireValue()})");

            // Sin campos propios: `state` viaja en el bloque de contexto.
            telemetry.Emit(TelemetryEvents.StateEntered);

            CheckStateLevelMatrix(newState);

            OnStateEntered?.Invoke(newState);
        }

        /// <summary>
        /// Pone el par ESL/LAL que el estado pide (spec 7, tabla del Game Flow).
        ///
        /// ORIGEN DE ESTE METODO. El 17 de septiembre la guarda del Apendice A
        /// --escrita el dia anterior-- empezo a gritar en cada corrida:
        /// "S7 no admite LAL=OFF". Tenia razon. El banco de pruebas entraba al
        /// estado y SOLO DESPUES fijaba los niveles, asi que entre una cosa y la
        /// otra el estado era S7 con los niveles de S1, y el STATE_ENTERED salia
        /// con ese par.
        ///
        /// El arreglo no fue reordenar dos lineas en quien llamaba: fue que
        /// entrar a un estado aplique sus niveles. Reordenar habria funcionado
        /// hasta el siguiente sitio que entrara a un estado sin acordarse.
        /// </summary>
        private void ApplyNominalLevels(GameFlowState state)
        {
            var esl = StateLevelMatrix.ExpectedEsl(state);
            var lal = StateLevelMatrix.ExpectedLal(state);
            if (esl == null || lal == null) return;   // S0 y S10 no tienen niveles

            // betweenTrials: true porque entrar a un estado ES, por definicion,
            // fuera de un trial. Si hubiera uno abierto, el guard de 10.2 lo
            // rechazaria, y eso seria correcto: significaria que alguien cambia
            // de estado a media respuesta.
            if (_stimulation != null) _stimulation.SetLevel(esl.Value, betweenTrials: true);
            if (_assistance != null) _assistance.SetLevel(lal.Value, betweenTrials: true);
        }

        /// <summary>
        /// Guarda del Apendice A.
        ///
        /// Error, pero NO se bloquea la transicion. Quedarse atascado a mitad de
        /// una sesion por un nivel mal puesto es peor que continuar con el nivel
        /// mal puesto y que quede constancia: el estado y los dos niveles viajan
        /// en el bloque de contexto de cada evento, asi que la violacion queda en
        /// la base y `verify_esl_content.sql` la encuentra aunque nadie estuviera
        /// mirando la consola.
        /// </summary>
        private void CheckStateLevelMatrix(GameFlowState state)
        {
            if (!enforceStateLevelMatrix || !StateLevelMatrix.HasRuleFor(state)) return;

            if (_stimulation == null || _assistance == null)
            {
                Debug.LogWarning("[GameFlowController] No hay ESL o LAL en este GameObject: " +
                                 "la matriz del Apendice A no se puede comprobar.");
                return;
            }

            string violacion = StateLevelMatrix.Violation(
                state, _stimulation.CurrentLevel, _assistance.CurrentLevel);

            if (violacion != null)
                Debug.LogError($"[GameFlowController] Apendice A: {violacion}. " +
                               "El estado cambia igual y la violacion queda registrada en la " +
                               "telemetria, pero el dato de este bloque hay que mirarlo con cuidado.");
        }

        public void AdvanceToNextState()
        {
            int currentIndex = Array.IndexOf(StateOrder, currentState);
            if (currentIndex < 0 || currentIndex >= StateOrder.Length - 1)
            {
                Debug.LogWarning("[GameFlowController] No next state (already at S9 or invalid state).");
                return;
            }

            var next = StateOrder[currentIndex + 1];

            // S2 solo en la primera visita (spec 7.3). El tutorial ensena los
            // controles; repetirlo en la segunda visita gasta tiempo de sesion y
            // mete practica extra con la mecanica justo antes de medirla.
            if (next == GameFlowState.S2_VRTutorial && SessionContext.IsInstalled &&
                !SessionContext.IsFirstVisit)
            {
                Debug.Log($"[GameFlowController] S2 se salta: visita {SessionContext.VisitNumber} " +
                          "(spec 7.3, tutorial solo en la primera).");
                next = StateOrder[currentIndex + 2];
            }

            EnterState(next);
        }

        /// <summary>
        /// Solo S7 permite adaptacion dinamica de ESL/LAL (spec seccion 7.8,
        /// Appendix A). Los controladores de adaptacion (Fase 5) deben
        /// consultar este metodo antes de aplicar cualquier cambio.
        /// </summary>
        public bool IsAdaptationAllowed()
        {
            if (currentState != GameFlowState.S7_ExperimentalRetrieval)
                return false;

            return Condition switch
            {
                ExperimentalCondition.Static => false,
                ExperimentalCondition.BehaviorAdaptive => true,
                ExperimentalCondition.MultimodalAdaptive => true,
                _ => false,
            };
        }
    }
}

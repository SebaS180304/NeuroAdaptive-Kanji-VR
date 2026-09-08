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
    /// </summary>
    [RequireComponent(typeof(SessionCommunicationClient))]
    [RequireComponent(typeof(BehaviorTelemetryController))]
    public class GameFlowController : MonoBehaviour
    {
        [SerializeField] private BehaviorTelemetryController telemetry;

        [Header("Session context (asignado en S0)")]
        [SerializeField] private ExperimentalCondition condition;
        [SerializeField] private GameFlowState currentState = GameFlowState.S0_SessionInitialization;

        public event Action<GameFlowState> OnStateEntered;

        public GameFlowState CurrentState => currentState;
        public ExperimentalCondition Condition => condition;

        /// <summary>
        /// Orden canonico de estados (spec 14.1). No incluye transiciones
        /// condicionales (p.ej. S2 solo en la primera visita); esa logica
        /// se agrega al encadenar el flujo (plan de Fase 2, 4.5).
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

            if (telemetry == null)
            {
                Debug.LogError("[GameFlowController] Falta BehaviorTelemetryController en este " +
                               "GameObject. Sin el no se emite telemetria con el bloque de contexto.");
                return;
            }

            telemetry.SetState(currentState);
        }

        public void EnterState(GameFlowState newState)
        {
            currentState = newState;

            // El orden importa: el contexto se actualiza ANTES de emitir, de
            // modo que el `state` del payload sea el estado al que se entra.
            telemetry.SetState(newState);

            Debug.Log($"[GameFlowController] STATE_ENTERED: {newState} (wire: {newState.ToWireValue()})");

            // Sin campos propios: `state` viaja en el bloque de contexto.
            telemetry.Emit(TelemetryEvents.StateEntered);

            OnStateEntered?.Invoke(newState);
        }

        public void AdvanceToNextState()
        {
            int currentIndex = Array.IndexOf(StateOrder, currentState);
            if (currentIndex < 0 || currentIndex >= StateOrder.Length - 1)
            {
                Debug.LogWarning("[GameFlowController] No next state (already at S9 or invalid state).");
                return;
            }
            EnterState(StateOrder[currentIndex + 1]);
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

            return condition switch
            {
                ExperimentalCondition.Static => false,
                ExperimentalCondition.BehaviorAdaptive => true,
                ExperimentalCondition.MultimodalAdaptive => true,
                _ => false,
            };
        }
    }
}

using System;
using System.Collections.Generic;
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
    /// FASE 1: implementa solo la maquina de estados y la notificacion
    /// de STATE_ENTERED al backend via SessionCommunicationClient. Cada
    /// controlador especifico (LearningBoardController, TrialController,
    /// etc.) se conecta en las fases donde su contenido se construye
    /// (ver README de este proyecto y Sintesis_Analisis_Comprension_Proyecto).
    /// </summary>
    [RequireComponent(typeof(SessionCommunicationClient))]
    public class GameFlowController : MonoBehaviour
    {
        [SerializeField] private SessionCommunicationClient communicationClient;

        [Header("Session context (asignado en S0)")]
        [SerializeField] private ExperimentalCondition condition;
        [SerializeField] private GameFlowState currentState = GameFlowState.S0_SessionInitialization;

        public event Action<GameFlowState> OnStateEntered;

        public GameFlowState CurrentState => currentState;
        public ExperimentalCondition Condition => condition;

        /// <summary>
        /// Orden canonico de estados (spec 14.1). No incluye transiciones
        /// condicionales (p.ej. S2 solo en la primera visita); esa logica
        /// se agrega en Fase 2 cuando el contenido real exista.
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
            if (communicationClient == null)
                communicationClient = GetComponent<SessionCommunicationClient>();
        }

        public void EnterState(GameFlowState newState)
        {
            currentState = newState;

            // ToWireValue(), no ToString(): el backend valida contra el valor
            // del enum (SCREAMING_SNAKE_CASE), no contra el nombre del miembro
            // de C#. Ver GameFlowState.cs. En el log se muestran los dos para
            // que la consola siga siendo legible y a la vez se vea que sale
            // por el cable.
            string wireState = newState.ToWireValue();
            Debug.Log($"[GameFlowController] STATE_ENTERED: {newState} (wire: {wireState})");

            communicationClient.SendSessionEvent(
                eventType: "STATE_ENTERED",
                payload: new Dictionary<string, object>
                {
                    { "state", wireState },
                });

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

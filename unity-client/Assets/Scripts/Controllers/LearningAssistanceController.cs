using NeuroAdaptiveVR.Data;
using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// LAL Controller (spec seccion 9 / 14): aplica cues pedagogicos
    /// segun tipo de trial y comando del backend. No cambia dificultad,
    /// cantidad de respuestas, tiempo, tipografia, scoring ni el
    /// espaciado de retrieval (spec 9.3).
    ///
    /// FASE: nivel fijo (scripted/MEDIUM) en Fases 1-4; adaptacion
    /// dinamica real llega en Fase 5 (M3), solo dentro de S7 y solo si
    /// GameFlowController.IsAdaptationAllowed() es true.
    /// </summary>
    public class LearningAssistanceController : MonoBehaviour
    {
        [SerializeField]
        private StimulationOrAssistanceLevel currentLevel = StimulationOrAssistanceLevel.Off;

        public StimulationOrAssistanceLevel CurrentLevel => currentLevel;

        /// <summary>
        /// Unico punto de entrada para cambiar LAL. Fase 5 debe validar
        /// aca las reglas de timing (solo entre trials, spec 10.2) antes
        /// de aplicar el cambio -- se deja el guard-clause explicito
        /// desde ya para que quede imposible de saltarse.
        /// </summary>
        public void SetLevel(StimulationOrAssistanceLevel newLevel, bool betweenTrials)
        {
            if (!betweenTrials)
            {
                Debug.LogError("[LearningAssistanceController] Blocked: LAL can only change " +
                                "between trials, never while the learner is answering (spec 10.2).");
                return;
            }
            currentLevel = newLevel;
        }
    }
}

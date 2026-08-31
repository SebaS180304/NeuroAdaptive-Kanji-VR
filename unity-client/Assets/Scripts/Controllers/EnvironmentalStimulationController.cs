using NeuroAdaptiveVR.Data;
using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// ESL Controller (spec seccion 8 / 14): "One scene, one controller"
    /// -- LOW/MEDIUM/HIGH son configuraciones de parametros de la misma
    /// escena, nunca escenas separadas. Controla exclusivamente densidad
    /// de props, objetos en movimiento y eventos perifericos; nunca
    /// lighting, UI, contenido, dificultad, cantidad de respuestas,
    /// tiempo, audio o scoring (spec 8.3).
    ///
    /// FASE: nivel fijo (scripted) en Fases 1-4; adaptacion dinamica real
    /// llega en Fase 5 (M3), solo dentro de S7.
    /// </summary>
    public class EnvironmentalStimulationController : MonoBehaviour
    {
        [SerializeField]
        private StimulationOrAssistanceLevel currentLevel = StimulationOrAssistanceLevel.Off;

        public StimulationOrAssistanceLevel CurrentLevel => currentLevel;

        /// <summary>Ver LearningAssistanceController.SetLevel: mismo guard-clause de timing.</summary>
        public void SetLevel(StimulationOrAssistanceLevel newLevel, bool betweenTrials)
        {
            if (!betweenTrials)
            {
                Debug.LogError("[EnvironmentalStimulationController] Blocked: ESL can only change " +
                                "between trials, never while the learner is answering (spec 10.2).");
                return;
            }
            currentLevel = newLevel;

            // TODO (Fase 2-5): aplicar densidad de props / movimiento /
            // eventos perifericos segun tabla 8.1, delegando en
            // PeripheralEventScheduler para los eventos temporizados.
        }
    }
}

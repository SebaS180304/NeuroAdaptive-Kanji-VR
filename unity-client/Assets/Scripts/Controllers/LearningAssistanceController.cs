using NeuroAdaptiveVR.Data;
using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// LAL Controller (spec seccion 9). Dos responsabilidades:
    ///
    /// 1. Guardar el nivel activo y hacer cumplir la regla de timing: LAL
    ///    solo cambia entre trials, nunca mientras el participante responde
    ///    (spec 10.2).
    /// 2. Ser la **unica fuente** de que cue esta disponible para un trial
    ///    dado. Esa es la tabla de 9.1, y es trial-aware a proposito.
    ///
    /// FASE: el nivel se fija por configuracion; quien lo decide es Fase 5,
    /// y solo dentro de S7. Este controlador no elige nunca su propio nivel.
    /// </summary>
    public class LearningAssistanceController : MonoBehaviour
    {
        [SerializeField]
        private StimulationOrAssistanceLevel currentLevel = StimulationOrAssistanceLevel.Off;

        public StimulationOrAssistanceLevel CurrentLevel => currentLevel;

        /// <summary>
        /// Unico punto de entrada para cambiar LAL. El guard-clause de timing
        /// es explicito para que sea imposible saltarselo por accidente
        /// cuando Fase 5 conecte el Adaptation Engine.
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

        /// <summary>
        /// Cues disponibles para este tipo de trial en este nivel, segun la
        /// tabla de la spec 9.1.
        ///
        /// La tabla depende del **tipo de trial** y no solo del nivel, y la
        /// razon es la regla de 9.1: "support is trial-aware so that a cue
        /// never directly reveals the target response". En T1 la respuesta es
        /// una forma y en T2 un significado, asi que oir la lectura ayuda sin
        /// regalar nada; en T3 la respuesta ES la lectura, asi que el audio
        /// queda prohibido y la asistencia sube por el canal visual.
        ///
        /// Devolver los cues disponibles no es presentarlos: con el modelo de
        /// hint bajo peticion, esto es lo que el participante obtiene SI pide
        /// ayuda. El campo "hint available" de la spec 11 es exactamente esto.
        /// </summary>
        public static LalCue AvailableCues(RetrievalTrialType trialType, StimulationOrAssistanceLevel level)
        {
            switch (level)
            {
                case StimulationOrAssistanceLevel.Off:
                case StimulationOrAssistanceLevel.Low:
                    // 9.1: "No pre-response pedagogical cue" en los tres tipos.
                    return LalCue.None;

                case StimulationOrAssistanceLevel.Medium:
                    return trialType == RetrievalTrialType.KanjiToReading
                        ? LalCue.VisualAssociation                       // T3: sin audio
                        : LalCue.TargetReadingAudio;                    // T1 y T2

                case StimulationOrAssistanceLevel.High:
                    switch (trialType)
                    {
                        case RetrievalTrialType.MeaningToKanji:          // T1
                            return LalCue.VisualTransformation | LalCue.TargetReadingAudio;
                        case RetrievalTrialType.KanjiToMeaning:          // T2
                            return LalCue.ReverseSemanticAssociation | LalCue.TargetReadingAudio;
                        case RetrievalTrialType.KanjiToReading:          // T3
                            return LalCue.VisualAssociation | LalCue.VisualTransformation;
                        default:
                            return LalCue.None;
                    }

                case StimulationOrAssistanceLevel.Baseline:
                    // BASELINE es un nivel de ESL para S4 (spec 7.5), no de LAL.
                    Debug.LogWarning("[LearningAssistanceController] BASELINE no es un nivel de LAL " +
                                     "(es de ESL, spec 7.5). Se trata como OFF.");
                    return LalCue.None;

                default:
                    return LalCue.None;
            }
        }

        public LalCue AvailableCuesNow(RetrievalTrialType trialType)
            => AvailableCues(trialType, currentLevel);
    }
}

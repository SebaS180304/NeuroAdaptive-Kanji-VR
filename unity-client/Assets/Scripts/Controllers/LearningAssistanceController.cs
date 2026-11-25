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

        [Tooltip("D9 (approved by MIRAI on 13 Oct): trials that get the cue without asking after " +
                 "the engine raises LAL. Adaptive conditions only; STATIC never.")]
        [SerializeField] private int proactiveTrials = ProactiveCueWindow.DefaultLength;

        private readonly ProactiveCueWindow _proactive = new ProactiveCueWindow();

        public StimulationOrAssistanceLevel CurrentLevel => currentLevel;

        /// <summary>Trials of the current proactive window still to come (D9).</summary>
        public int ProactiveTrialsLeft => _proactive.Remaining;

        /// <summary>
        /// Unico punto de entrada para cambiar LAL. El guard-clause de timing
        /// es explicito para que sea imposible saltarselo por accidente
        /// cuando Fase 5 conecte el Adaptation Engine.
        ///
        /// D9: with <paramref name="proactiveCues"/> (the engine's DECISION
        /// carries it), a raise opens a window of 3 trials in which the cue is
        /// presented without asking. The count starts at the first trial after
        /// this call. A new raise opens a new window; lowering LAL closes it.
        /// A blocked change opens nothing.
        /// </summary>
        public void SetLevel(StimulationOrAssistanceLevel newLevel, bool betweenTrials, bool proactiveCues = false)
        {
            if (!betweenTrials)
            {
                Debug.LogError("[LearningAssistanceController] Blocked: LAL can only change " +
                                "between trials, never while the learner is answering (spec 10.2).");
                return;
            }
            int from = Rank(currentLevel), to = Rank(newLevel);
            currentLevel = newLevel;

            if (to < from) _proactive.Close();
            else if (to > from && proactiveCues) _proactive.Open(proactiveTrials);
        }

        /// <summary>
        /// Called once at the start of every trial (D9). Returns the position
        /// of this trial in the proactive window (1..3), or 0 when the cue stays
        /// on request. Outside an adaptive S7 (STATIC, S6, S8...) it always
        /// returns 0 and closes any window, so the cue can never appear by
        /// itself there.
        /// </summary>
        public int BeginTrialProactive(bool adaptationAllowed)
        {
            if (!adaptationAllowed) { _proactive.Close(); return 0; }
            return _proactive.NextTrial();
        }

        /// <summary>Order of the LAL levels; BASELINE (an ESL level) and unknown values rank as OFF.</summary>
        private static int Rank(StimulationOrAssistanceLevel level) => level switch
        {
            StimulationOrAssistanceLevel.Low => 1,
            StimulationOrAssistanceLevel.Medium => 2,
            StimulationOrAssistanceLevel.High => 3,
            _ => 0,
        };

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

    /// <summary>
    /// D9 window: after the engine raises LAL, the next N trials (3, MIRAI,
    /// 13 Oct) present the cue without asking. Plain class so the harness can
    /// test it without a scene.
    ///
    /// Fits spec 10.2 without new rules: the 3-trial cooldown stops LAL from
    /// changing inside the window, and the 4-trial tail freeze keeps the last
    /// possible window inside S7.
    /// </summary>
    public sealed class ProactiveCueWindow
    {
        public const int DefaultLength = 3;

        private int _length;
        private int _index;

        public int Remaining => _length - _index;
        public bool Active => Remaining > 0;

        /// <summary>Opens a new window; the next trial is number 1.</summary>
        public void Open(int length = DefaultLength)
        {
            _length = Mathf.Max(0, length);
            _index = 0;
        }

        public void Close()
        {
            _length = 0;
            _index = 0;
        }

        /// <summary>The trial's position in the window (1..length), or 0 if the window is closed.</summary>
        public int NextTrial()
        {
            if (!Active) return 0;
            _index++;
            return _index;
        }
    }
}

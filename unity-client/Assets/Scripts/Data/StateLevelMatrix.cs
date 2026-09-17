using System.Collections.Generic;
using System.Linq;

namespace NeuroAdaptiveVR.Data
{
    /// <summary>
    /// Que niveles de ESL y LAL admite cada estado (spec seccion 7, tabla del
    /// Game Flow v1, y Apendice A).
    ///
    /// POR QUE EXISTE
    /// --------------
    /// Hasta el 16 de septiembre la matriz estaba escrita en el spec y en ningun
    /// sitio mas. Los niveles se fijaban por configuracion y **nadie comprobaba
    /// que el par estado-nivel fuera el correcto**: S8 aceptaba LAL=HIGH sin
    /// protestar. S8 es la medida primaria de aprendizaje inmediato y se define
    /// por ser "no-assistance"; correrlo con asistencia no produce un dato malo,
    /// produce un dato que mide otra cosa y lo parece todo.
    ///
    /// Esto no elige niveles: solo dice cuales son admisibles. Quien los aplica
    /// es el encadenado del flujo, y quien los posee siguen siendo
    /// EnvironmentalStimulationController y LearningAssistanceController.
    ///
    /// DOS INTERPRETACIONES DECLARADAS
    /// -------------------------------
    /// 1. **S2 y S5 tienen LAL "scripted"**, que no es un valor del enum. Se
    ///    interpreta como OFF: en esos estados la ayuda la da la mecanica, no la
    ///    concede LAL bajo peticion, y la matriz 9.1 no interviene. Si el revisor
    ///    de MIRAI lee "scripted" como un nivel propio, esta tabla cambia.
    /// 2. **S7 dice "MEDIUM -> dynamic"**. En Fase 2, condicion STATIC, el nivel
    ///    se queda en MEDIUM. La tabla admite LOW/MEDIUM/HIGH porque Fase 5 podra
    ///    moverlo dentro de S7 -- y solo dentro de S7.
    /// </summary>
    public static class StateLevelMatrix
    {
        private readonly struct Allowed
        {
            public readonly StimulationOrAssistanceLevel[] Esl;
            public readonly StimulationOrAssistanceLevel[] Lal;

            /// <summary>
            /// El par NOMINAL del estado: el que aplica quien entra a el.
            ///
            /// Existe aparte de las listas porque "admisible" y "el que toca" no
            /// son lo mismo. S7 admite LOW, MEDIUM y HIGH --Fase 5 puede moverlo
            /// dentro del estado-- pero entra en MEDIUM. Deducir el nominal del
            /// primer elemento de la lista funcionaria hasta que alguien
            /// reordenara la lista por claridad y cambiara el comportamiento sin
            /// tocar ninguna linea de logica.
            /// </summary>
            public readonly StimulationOrAssistanceLevel NominalEsl;
            public readonly StimulationOrAssistanceLevel NominalLal;

            public readonly string Note;

            public Allowed(StimulationOrAssistanceLevel[] esl, StimulationOrAssistanceLevel[] lal,
                           StimulationOrAssistanceLevel nominalEsl,
                           StimulationOrAssistanceLevel nominalLal,
                           string note = null)
            {
                Esl = esl; Lal = lal;
                NominalEsl = nominalEsl; NominalLal = nominalLal;
                Note = note;
            }
        }

        private static readonly StimulationOrAssistanceLevel[] Off =
            { StimulationOrAssistanceLevel.Off };

        private static readonly Dictionary<GameFlowState, Allowed> Table = new()
        {
            // S0 y S10 no ocurren dentro de la experiencia: no hay niveles que validar.
            [GameFlowState.S1_WelcomeOrientation] = new Allowed(
                new[] { StimulationOrAssistanceLevel.Low }, Off,
                StimulationOrAssistanceLevel.Low, StimulationOrAssistanceLevel.Off),

            [GameFlowState.S2_VRTutorial] = new Allowed(
                new[] { StimulationOrAssistanceLevel.Low }, Off,
                StimulationOrAssistanceLevel.Low, StimulationOrAssistanceLevel.Off,
                "LAL 'scripted' se interpreta como OFF"),

            [GameFlowState.S3_SystemValidation] = new Allowed(
                new[] { StimulationOrAssistanceLevel.Minimal }, Off,
                StimulationOrAssistanceLevel.Minimal, StimulationOrAssistanceLevel.Off),

            [GameFlowState.S4_EEGBaseline] = new Allowed(
                new[] { StimulationOrAssistanceLevel.Baseline }, Off,
                StimulationOrAssistanceLevel.Baseline, StimulationOrAssistanceLevel.Off),

            [GameFlowState.S5_StandardizedLearning] = new Allowed(
                new[] { StimulationOrAssistanceLevel.Low }, Off,
                StimulationOrAssistanceLevel.Low, StimulationOrAssistanceLevel.Off,
                "LAL 'scripted' se interpreta como OFF"),

            [GameFlowState.S6_GuidedPracticeCalibration] = new Allowed(
                new[] { StimulationOrAssistanceLevel.Medium },
                new[] { StimulationOrAssistanceLevel.Medium },
                StimulationOrAssistanceLevel.Medium, StimulationOrAssistanceLevel.Medium),

            [GameFlowState.S7_ExperimentalRetrieval] = new Allowed(
                new[] { StimulationOrAssistanceLevel.Low, StimulationOrAssistanceLevel.Medium,
                        StimulationOrAssistanceLevel.High },
                new[] { StimulationOrAssistanceLevel.Low, StimulationOrAssistanceLevel.Medium,
                        StimulationOrAssistanceLevel.High },
                StimulationOrAssistanceLevel.Medium, StimulationOrAssistanceLevel.Medium,
                "MEDIUM en Fase 2; Fase 5 puede moverlo, y solo aqui"),

            [GameFlowState.S8_ImmediateAssessment] = new Allowed(
                new[] { StimulationOrAssistanceLevel.Focus, StimulationOrAssistanceLevel.Low }, Off,
                StimulationOrAssistanceLevel.Focus, StimulationOrAssistanceLevel.Off,
                "sin asistencia: es la medida primaria de aprendizaje inmediato"),

            [GameFlowState.S9_SessionSummary] = new Allowed(
                new[] { StimulationOrAssistanceLevel.Low }, Off,
                StimulationOrAssistanceLevel.Low, StimulationOrAssistanceLevel.Off),
        };

        /// <summary>El ESL nominal del estado: el que aplica quien entra a el.</summary>
        public static StimulationOrAssistanceLevel? ExpectedEsl(GameFlowState state)
            => Table.TryGetValue(state, out var a) ? a.NominalEsl : (StimulationOrAssistanceLevel?)null;

        public static StimulationOrAssistanceLevel? ExpectedLal(GameFlowState state)
            => Table.TryGetValue(state, out var a) ? a.NominalLal : (StimulationOrAssistanceLevel?)null;

        public static bool HasRuleFor(GameFlowState state) => Table.ContainsKey(state);

        /// <summary>
        /// Comprueba el par. Devuelve null si es admisible, o el motivo si no.
        ///
        /// Devuelve texto en vez de loguear: quien llama decide la severidad y el
        /// prefijo. Asi esta misma tabla la puede usar el arnes de pruebas sin
        /// ensuciar la consola.
        /// </summary>
        public static string Violation(GameFlowState state,
                                       StimulationOrAssistanceLevel esl,
                                       StimulationOrAssistanceLevel lal)
        {
            if (!Table.TryGetValue(state, out var a)) return null;

            var fallos = new List<string>();
            if (!a.Esl.Contains(esl))
                fallos.Add($"ESL={esl.ToWireValue()} (admisibles: {Wire(a.Esl)})");
            if (!a.Lal.Contains(lal))
                fallos.Add($"LAL={lal.ToWireValue()} (admisibles: {Wire(a.Lal)})");

            if (fallos.Count == 0) return null;

            return $"{state.ToWireValue()} no admite {string.Join(" ni ", fallos)}" +
                   (a.Note != null ? $". Nota: {a.Note}" : "");
        }

        private static string Wire(StimulationOrAssistanceLevel[] levels)
            => string.Join("/", levels.Select(l => l.ToWireValue()));
    }
}

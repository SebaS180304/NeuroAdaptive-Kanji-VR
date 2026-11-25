using System.Runtime.Serialization;

namespace NeuroAdaptiveVR.Data
{
    /// <summary>
    /// Las tres condiciones experimentales comparten el mismo Game
    /// Flow; solo difieren en que fuentes de datos puede usar el
    /// Adaptation Engine y si tiene permiso para actuar (spec seccion 10).
    ///
    /// Los valores de cable coinciden con el enum `experimental_condition`
    /// de PostgreSQL y con `ExperimentalCondition` del backend.
    /// </summary>
    public enum ExperimentalCondition
    {
        [EnumMember(Value = "STATIC")]
        Static,

        [EnumMember(Value = "BEHAVIOR_ADAPTIVE")]
        BehaviorAdaptive,

        [EnumMember(Value = "MULTIMODAL_ADAPTIVE")]
        MultimodalAdaptive,
    }

    /// <summary>Niveles compartidos por ESL y LAL (spec secciones 8-9).</summary>
    public enum StimulationOrAssistanceLevel
    {
        [EnumMember(Value = "OFF")]
        Off,

        [EnumMember(Value = "LOW")]
        Low,

        [EnumMember(Value = "MEDIUM")]
        Medium,

        [EnumMember(Value = "HIGH")]
        High,

        /// <summary>Solo ESL: usado en S4 (spec seccion 7.5).</summary>
        [EnumMember(Value = "BASELINE")]
        Baseline,

        /// <summary>
        /// Solo ESL: S8, Immediate Assessment (Apendice A y spec 7.9).
        ///
        /// 7.9 describe Focus Mode como "environment darkened/neutralized",
        /// pero 3.3 dice que la iluminacion permanece estable entre niveles de
        /// ESL y 8.3 la pone explicitamente fuera de ESL. Se contradicen, y S8
        /// es la medida primaria de aprendizaje inmediato.
        ///
        /// INTERPRETACION del 10 de septiembre de 2026, no hecho de la spec:
        /// "neutralized" = conteo de props 0 y sin eventos perifericos, SIN
        /// tocar la iluminacion. Preserva las dos invariantes y deja FOCUS como
        /// caso extremo del mismo mecanismo en vez de una excepcion. Pendiente
        /// de confirmar con el revisor de MIRAI.
        /// </summary>
        [EnumMember(Value = "FOCUS")]
        Focus,

        /// <summary>Solo ESL: S3, System Validation (Apendice A).</summary>
        [EnumMember(Value = "MINIMAL")]
        Minimal,
    }

    public static class ExperimentalConditionExtensions
    {
        public static string ToWireValue(this ExperimentalCondition condition)
            => EnumWire<ExperimentalCondition>.Value(condition);

        public static bool TryFromWireValue(string wireValue, out ExperimentalCondition condition)
            => EnumWire<ExperimentalCondition>.TryParse(wireValue, out condition);
    }

    public static class StimulationOrAssistanceLevelExtensions
    {
        public static string ToWireValue(this StimulationOrAssistanceLevel level)
            => EnumWire<StimulationOrAssistanceLevel>.Value(level);

        public static bool TryFromWireValue(string wireValue, out StimulationOrAssistanceLevel level)
            => EnumWire<StimulationOrAssistanceLevel>.TryParse(wireValue, out level);
    }
}

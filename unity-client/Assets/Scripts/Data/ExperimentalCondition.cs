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

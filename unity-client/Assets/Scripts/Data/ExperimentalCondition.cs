namespace NeuroAdaptiveVR.Data
{
    /// <summary>
    /// Las tres condiciones experimentales comparten el mismo Game
    /// Flow; solo difieren en que fuentes de datos puede usar el
    /// Adaptation Engine y si tiene permiso para actuar (spec seccion 10).
    /// </summary>
    public enum ExperimentalCondition
    {
        Static,
        BehaviorAdaptive,
        MultimodalAdaptive,
    }

    /// <summary>Niveles compartidos por ESL y LAL (spec secciones 8-9).</summary>
    public enum StimulationOrAssistanceLevel
    {
        Off,
        Low,
        Medium,
        High,
        Baseline, // ESL-only: usado en S4 (spec seccion 7.5)
    }
}

using System.Runtime.Serialization;

namespace NeuroAdaptiveVR.Data
{
    /// <summary>
    /// Los tres tipos de trial de retrieval fijos (spec seccion 6).
    ///
    /// El valor de cable lleva el identificador T1/T2/T3 del spec ademas de
    /// la direccion, para que una fila de `session_events` se lea sin tener
    /// que consultar la tabla del spec. Ver database/EVENT_CONTRACT.md.
    /// </summary>
    public enum RetrievalTrialType
    {
        [EnumMember(Value = "T1_MEANING_TO_KANJI")]
        MeaningToKanji,

        [EnumMember(Value = "T2_KANJI_TO_MEANING")]
        KanjiToMeaning,

        [EnumMember(Value = "T3_KANJI_TO_READING")]
        KanjiToReading,
    }

    public static class RetrievalTrialTypeExtensions
    {
        public static string ToWireValue(this RetrievalTrialType type)
            => EnumWire<RetrievalTrialType>.Value(type);

        public static bool TryFromWireValue(string wireValue, out RetrievalTrialType type)
            => EnumWire<RetrievalTrialType>.TryParse(wireValue, out type);
    }
}

using System;
using System.Collections.Generic;
using Newtonsoft.Json;

namespace NeuroAdaptiveVR.Data
{
    /// <summary>
    /// Tipos de deserializacion de Assets/Resources/kanji_content.json.
    ///
    /// El JSON lo genera tools/kanji_metrics.py --export y NO se escribe a mano
    /// (spec v1.2 seccion 14: "Nothing in the kanji dataset is authored by hand in
    /// the Editor"). Estas clases son un espejo de su forma, nada mas: no
    /// calculan, no corrigen y no rellenan huecos.
    ///
    /// Por que son clases y no un Dictionary&lt;string, object&gt;: un typo en el
    /// nombre de un campo tiene que romper al deserializar, no devolver null en el
    /// trial 47. Es la misma razon por la que el contrato de eventos de la base
    /// tiene nombres fijos aunque la columna sea JSONB.
    /// </summary>
    [Serializable]
    public class KanjiContentContract
    {
        [JsonProperty("schemaVersion")] public int SchemaVersion;
        [JsonProperty("generatedBy")] public string GeneratedBy;

        /// <summary>
        /// Ruta relativa de la tipografia con la que se midio la complejidad
        /// perimetrica. Viaja en el contrato porque esas metricas dependen del
        /// glifo concreto: medidas sobre otra cara, describen otro experimento.
        /// </summary>
        [JsonProperty("font")] public string Font;

        [JsonProperty("sets")] public Dictionary<string, List<string>> Sets = new();
        [JsonProperty("reserve")] public List<string> Reserve = new();
        [JsonProperty("tutorial")] public List<string> Tutorial = new();

        /// <summary>
        /// set -> kanji experimental -> kanji de reserva que pueden reemplazarlo
        /// (spec 13.2). Derivada por script, nunca mantenida a mano.
        /// </summary>
        [JsonProperty("substitutionTable")]
        public Dictionary<string, Dictionary<string, List<string>>> SubstitutionTable = new();

        [JsonProperty("kanji")] public List<KanjiContentRecord> Kanji = new();
    }

    /// <summary>
    /// Una fila del contrato. Es la fuente de verdad de todo lo que se ve aqui:
    /// ningun KanjiLearningItem repite estos valores.
    /// </summary>
    [Serializable]
    public class KanjiContentRecord
    {
        /// <summary>
        /// Id estable. Viaja como kanji_id en la telemetria y en Fase 3 es llave
        /// foranea en Postgres. Sale de KANJI_IDS en tools/kanji_metrics.py y no
        /// se deriva de la lectura: 日 y 火 se leen las dos ひ.
        /// </summary>
        [JsonProperty("id")] public string Id;

        [JsonProperty("kanji")] public string Character;
        [JsonProperty("meaning")] public string Meaning;

        /// <summary>
        /// La UNICA lectura que se ensena y se evalua (spec 4.3, target reading
        /// rule). Kun'yomi salvo las dos excepciones declaradas, 門 y 肉.
        /// </summary>
        [JsonProperty("targetReading")] public string TargetReading;

        [JsonProperty("strokes")] public int Strokes;
        [JsonProperty("morae")] public int Morae;
        [JsonProperty("assemblyGroups")] public int AssemblyGroups;
        [JsonProperty("commonReadings")] public int CommonReadings;
        [JsonProperty("perimetricComplexity")] public float PerimetricComplexity;

        /// <summary>Transparencia del glifo, revisor 1. null si no se puntuo.</summary>
        [JsonProperty("imageabilityGlyph")] public int? ImageabilityGlyph;

        /// <summary>Concrecion del objeto, revisor 2. null si no se puntuo.</summary>
        [JsonProperty("imageabilityObject")] public int? ImageabilityObject;

        [JsonProperty("discoveryType")] public string DiscoveryTypeRaw;
        [JsonProperty("textbookLesson")] public string TextbookLesson;

        /// <summary>Experimental / Reserve / Tutorial.</summary>
        [JsonProperty("role")] public string Role;

        /// <summary>"A" / "B" / "C" / "Tutorial", o null para la reserva.</summary>
        [JsonProperty("experimentalSet")] public string ExperimentalSetRaw;

        public DiscoveryType DiscoveryType =>
            Enum.TryParse(DiscoveryTypeRaw, out DiscoveryType d) ? d : DiscoveryType.None;

        /// <summary>
        /// El pool se deduce de role y experimentalSet juntos, porque el JSON deja
        /// experimentalSet en null para la reserva. Deducirlo de uno solo daria
        /// Reserve para los tutoriales.
        /// </summary>
        public ExperimentalSet Pool => Role switch
        {
            "Experimental" => Enum.TryParse(ExperimentalSetRaw, out ExperimentalSet s)
                              ? s : ExperimentalSet.Reserve,
            "Tutorial" => ExperimentalSet.Tutorial,
            _ => ExperimentalSet.Reserve,
        };

        /// <summary>
        /// Para logs y para el encabezado del Inspector. No es un dato del
        /// contrato: se compone al vuelo.
        /// </summary>
        public string Label => $"{Character} · {Meaning} · {TargetReading}";
    }
}

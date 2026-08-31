using System.Collections.Generic;
using UnityEngine;

namespace NeuroAdaptiveVR.Data
{
    /// <summary>
    /// KanjiLearningItem (spec seccion 4.3): modelo de datos data-driven
    /// para cada kanji experimental. Se define como ScriptableObject para
    /// poder crear/editar los 15 kanji + pools de reserva/tutorial desde
    /// el Editor sin tocar codigo (principio de "revision de dataset kanji
    /// data-driven" del anteproyecto, seccion 6.2).
    ///
    /// NOTA DE FASE: esta clase se deja definida desde Fase 1 porque el
    /// contenido depende de ella, pero el pipeline de carga/asignacion
    /// real (KanjiContentController) se implementa en Fase 2 (M2).
    /// </summary>
    [CreateAssetMenu(fileName = "NewKanjiLearningItem", menuName = "NeuroAdaptiveVR/Kanji Learning Item")]
    public class KanjiLearningItem : ScriptableObject
    {
        [Header("Pedagogical data")]
        public string character;
        public string meaning;
        public string kunyomi;
        public string onyomi;
        public int strokeCount;
        public List<string> exampleWords = new();
        public List<string> contextExamples = new();

        [Header("Experimental metadata")]
        public string targetMeaning;
        [Tooltip("Unica lectura evaluada explicitamente (spec: Target reading rule).")]
        public string primaryTargetReading;
        public string visualAssociationType;
        public List<string> assistanceCues = new();
        [Tooltip("A, B, C (experimental) / Reserve / Tutorial (spec seccion 4.1-4.2).")]
        public string experimentalSet;

        [Header("Assembly metadata")]
        [Tooltip("2-4 segmentos grandes (spec seccion 5.3). Sin reconocimiento de trazo.")]
        public List<string> assemblySegmentIds = new();

        [Header("Runtime / pre-test metadata")]
        public KnowledgeClassification knowledgeClassification = KnowledgeClassification.Unknown;
    }

    /// <summary>Clasificacion de pre-test (spec seccion 13.2).</summary>
    public enum KnowledgeClassification
    {
        Unknown,
        PartiallyKnown,
        Known,
    }
}

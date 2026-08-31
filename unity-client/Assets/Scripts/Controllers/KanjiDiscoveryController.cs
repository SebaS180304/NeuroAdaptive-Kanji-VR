using NeuroAdaptiveVR.Data;
using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Responsabilidad (spec seccion 5.1 / 14): corre la secuencia de
    /// descubrimiento estandarizada objeto/concepto -> forma -> kanji
    /// para cada item, eligiendo entre descubrimiento pictografico o
    /// contextual segun corresponda (design rule: solo transformar
    /// visualmente cuando la relacion pictografica es defendible).
    ///
    /// FASE: implementacion real en Fase 2, en conjunto con
    /// VisualTransformationController y PronunciationAudioController.
    /// </summary>
    public class KanjiDiscoveryController : MonoBehaviour
    {
        // TODO (Fase 2): reproducir secuencia por KanjiLearningItem,
        // exponer eventos de exposicion (exposure timestamps, spec 7.6).
    }
}

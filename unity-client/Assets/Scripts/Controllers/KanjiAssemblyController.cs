using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Responsabilidad (spec seccion 5.3 / 14): Guided Kanji Assembly --
    /// 2-4 segmentos grandes por kanji, sin reconocimiento de trazo.
    /// Telemetria: tiempo de armado, seleccion/colocacion de segmentos,
    /// intentos incorrectos. Clasificado como telemetria secundaria, no
    /// outcome experimental primario en v1.
    ///
    /// FASE: implementacion real en Fase 2.
    /// </summary>
    public class KanjiAssemblyController : MonoBehaviour
    {
        // TODO (Fase 2): drag/grab de segmentos hacia slots resaltados en
        // orden configurado (assemblySegmentIds de KanjiLearningItem).
    }
}

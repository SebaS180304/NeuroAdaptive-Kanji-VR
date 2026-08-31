using System.Collections.Generic;
using NeuroAdaptiveVR.Data;
using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Responsabilidad (spec seccion 14): carga los KanjiLearningItem
    /// asignados a la sesion (set A/B/C + pools de reserva/tutorial,
    /// spec 4.1-4.2) y su metadata de runtime.
    ///
    /// FASE: implementacion real en Fase 2 (M2), cuando se autoren los
    /// 15 kanji experimentales + 5 de reserva + 5 de tutorial como
    /// assets KanjiLearningItem.
    /// </summary>
    public class KanjiContentController : MonoBehaviour
    {
        [SerializeField] private List<KanjiLearningItem> allItems = new();

        // TODO (Fase 2): asignacion por sesion (seed pseudoaleatoria),
        // logica de reemplazo desde Reserve Pool segun pre-test (13.2).
        public IReadOnlyList<KanjiLearningItem> AllItems => allItems;
    }
}

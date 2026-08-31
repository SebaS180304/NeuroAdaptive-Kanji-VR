using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Responsabilidad (spec seccion 8.1 / 14): programa eventos
    /// visuales no relacionados a la tarea segun la configuracion ESL
    /// activa (tabla 8.1: MEDIUM ~1 cada 25-35s, HIGH ~1 cada 10-15s).
    ///
    /// FASE: implementacion real en Fase 2, timing exacto sujeto a
    /// validacion piloto (spec seccion 16).
    /// </summary>
    public class PeripheralEventScheduler : MonoBehaviour
    {
        // TODO (Fase 2): timers configurables por nivel ESL; los valores
        // de esta clase son "to validate" segun spec 16, no hardcodear
        // como definitivos.
    }
}

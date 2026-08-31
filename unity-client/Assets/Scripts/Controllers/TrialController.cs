using NeuroAdaptiveVR.Data;
using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Responsabilidad (spec seccion 6 / 14): genera y resuelve los
    /// trials T1/T2/T3 de retrieval y de assessment (S8). Maneja
    /// espaciado pseudoaleatorizado y evita repeticion inmediata del
    /// mismo item (spec 6.1).
    ///
    /// FASE: implementacion real en Fase 2-3 (M2), la parte de
    /// adaptacion dinamica (solo dentro de S7) llega en Fase 5 (M3).
    /// </summary>
    public class TrialController : MonoBehaviour
    {
        // TODO (Fase 2): generar secuencia de trials con seed guardada
        // para reconstruccion exacta de sesion (spec 6.1, 11).
        public RetrievalTrialType CurrentTrialType { get; private set; }
    }
}

using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Responsabilidad (spec seccion 7.3 / 14): corre las interacciones
    /// del tutorial de primera visita (S2) usando el Tutorial Pool
    /// (一, 二, 三, con 四/五 de refuerzo). Ensena Look & Select,
    /// Grab & Place y Request Hint sin contaminar los sets experimentales.
    ///
    /// FASE: implementacion real en Fase 2, junto con el resto de
    /// mecanicas de aprendizaje estandarizadas.
    /// </summary>
    public class TutorialController : MonoBehaviour
    {
        // TODO (Fase 2): TUTORIAL_STARTED/SELECT/GRAB/PLACE/HINT_REQUESTED/
        // ERROR/COMPLETED -- emitir via BehaviorTelemetryController.
    }
}

using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Responsabilidad (spec seccion 14): detecta HEAD_AWAY / HEAD_RETURNED
    /// segun una region de foco de tarea configurable.
    ///
    /// FASE: implementacion real en Fase 3 (M2). El angulo/tiempo que
    /// define HEAD_AWAY esta explicitamente "to validate" via pruebas de
    /// usabilidad VR (spec seccion 16) -- no hardcodear un umbral final aca.
    /// </summary>
    public class HeadOrientationTracker : MonoBehaviour
    {
        [SerializeField] private Transform headTransform;
        [SerializeField] private Transform taskFocusReference;

        [Tooltip("Provisional -- pendiente de validacion con pruebas de usabilidad VR (spec 16).")]
        [SerializeField] private float headAwayAngleThresholdDegrees = 45f;

        // TODO (Fase 3): logica real de deteccion + debounce temporal +
        // emision de HEAD_AWAY/HEAD_RETURNED via BehaviorTelemetryController.
    }
}

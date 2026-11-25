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
    ///
    /// Los tres campos se exponen como propiedades de solo lectura. Ademas
    /// de ser lo que la logica de Fase 3 va a consumir, evita el warning
    /// CS0414 del compilador: no sabe que [SerializeField] significa que
    /// Unity si usa el campo, asi que un campo privado con inicializador y
    /// sin lecturas se reporta como "assigned but never used".
    /// </summary>
    public class HeadOrientationTracker : MonoBehaviour
    {
        [SerializeField] private Transform headTransform;
        [SerializeField] private Transform taskFocusReference;

        [Tooltip("Provisional -- pendiente de validacion con pruebas de usabilidad VR (spec 16).")]
        [SerializeField] private float headAwayAngleThresholdDegrees = 45f;

        public Transform HeadTransform => headTransform;
        public Transform TaskFocusReference => taskFocusReference;
        public float HeadAwayAngleThresholdDegrees => headAwayAngleThresholdDegrees;

        // TODO (Fase 3): logica real de deteccion + debounce temporal +
        // emision de HEAD_AWAY/HEAD_RETURNED via BehaviorTelemetryController.
    }
}

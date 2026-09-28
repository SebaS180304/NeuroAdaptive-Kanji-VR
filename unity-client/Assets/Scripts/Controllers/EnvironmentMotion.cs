using NeuroAdaptiveVR.Core;
using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Movimiento de los objetos moviles de la Environmental Layer.
    ///
    /// Existe porque un objeto llamado "mover" que no se mueve es peor que no
    /// tenerlo: la tabla 8.1 cuenta "objetos en movimiento" como uno de los tres
    /// parametros de ESL, y si esos objetos estan quietos, el nivel MEDIUM y el
    /// HIGH se diferencian solo en densidad de props. La manipulacion quedaria a
    /// medias sin que nada avisara.
    ///
    /// Los dos modos son los dos ejemplos literales de 8.1: "curtain/blind
    /// motion" y "slow movement outside window".
    ///
    /// RECONSTRUCTIBLE (30 September 2026, F3.2)
    /// ----------------------------------------
    /// The starting phase derives from the session seed and the object's name
    /// (EnvironmentSeed "motion:{name}"), and the clock of the motion starts
    /// when the object is activated -- that is, at its ENVIRONMENT_APPLIED. So
    /// the pose of any mover at any instant is a function of (session seed,
    /// time since ENVIRONMENT_APPLIED), both of which are in the data. Until M2
    /// the phase came from the sibling index and the clock from Time.time since
    /// the application started, and neither was recorded.
    /// </summary>
    public class EnvironmentMotion : MonoBehaviour
    {
        public enum Mode
        {
            /// <summary>Oscilacion pequena y continua. Cortina o persiana.</summary>
            Sway,

            /// <summary>Recorrido lento de un extremo a otro, con pausa. Silueta tras la ventana.</summary>
            Traverse,
        }

        [SerializeField] private Mode mode = Mode.Sway;

        [Header("Sway")]
        [Tooltip("Grados de balanceo a cada lado.")]
        [SerializeField] private float swayDegrees = 4f;
        [SerializeField] private float swayPeriodSeconds = 3.5f;

        [Header("Traverse")]
        [Tooltip("Eje local del recorrido, normalmente el largo de la ventana.")]
        [SerializeField] private Vector3 traverseAxis = Vector3.forward;
        [SerializeField] private float traverseDistance = 1.4f;
        [SerializeField] private float traverseSeconds = 6f;
        [Tooltip("Segundos quieto fuera de vista entre pasadas.")]
        [SerializeField] private float traversePauseSeconds = 5f;

        private Vector3 _origin;
        private Quaternion _restRotation;
        private float _phase;
        private float _startedAt;

        /// <summary>Phase in [0, 1) of the cycle at activation. Exposed for the harness.</summary>
        public float Phase => _phase;

        private void Awake()
        {
            _origin = transform.localPosition;
            _restRotation = transform.localRotation;
        }

        /// <summary>
        /// Phase from the session seed and the object's name: two movers do not
        /// move in unison, and the same session gives the same phase every time.
        /// A Random.value here would make a reconstructed session look different.
        /// </summary>
        public static float PhaseFor(int baseSeed, string objectName) =>
            EnvironmentSeed.Unit(EnvironmentSeed.For(baseSeed, "motion:" + objectName));

        private void OnEnable()
        {
            // Al reaparecer por un cambio de ESL, el objeto arranca en su sitio
            // en vez de saltar a media animacion.
            transform.localPosition = _origin;
            transform.localRotation = _restRotation;

            var esl = FindAnyObjectByType<EnvironmentalStimulationController>();
            _phase = PhaseFor(esl != null ? esl.BaseSeed : EnvironmentSeed.Base(0), name);
            _startedAt = Time.time;
        }

        private void Update()
        {
            switch (mode)
            {
                case Mode.Sway: UpdateSway(); break;
                case Mode.Traverse: UpdateTraverse(); break;
            }
        }

        private void UpdateSway()
        {
            if (swayPeriodSeconds <= 0f) return;
            float t = ((Time.time - _startedAt) / swayPeriodSeconds + _phase) * Mathf.PI * 2f;
            float angle = Mathf.Sin(t) * swayDegrees;
            transform.localRotation = _restRotation * Quaternion.Euler(0f, 0f, angle);
        }

        private void UpdateTraverse()
        {
            float cycle = traverseSeconds + traversePauseSeconds;
            if (cycle <= 0f) return;

            float t = Mathf.Repeat(Time.time - _startedAt + _phase * cycle, cycle);
            if (t > traverseSeconds)
            {
                // Pausa: fuera de vista, en el extremo de salida.
                transform.localPosition = _origin + traverseAxis.normalized * traverseDistance;
                return;
            }

            float u = t / traverseSeconds;
            transform.localPosition = _origin + traverseAxis.normalized * (traverseDistance * u);
        }
    }
}

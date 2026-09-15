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
    /// DEUDA CONOCIDA: la fase inicial se deriva del indice del objeto, asi que
    /// el movimiento es identico entre sesiones que apliquen el mismo perfil en
    /// el mismo momento -- pero NO esta atada a la seed de la sesion. Dos
    /// sesiones con la misma seed ven los mismos objetos moverse igual; lo que
    /// no se reconstruye es en que instante de su ciclo estaba cada uno cuando
    /// empezo un trial concreto. Para spec 6.1 eso importa, y se cierra cuando
    /// EnvironmentalStimulationController reciba la seed real de
    /// experiment_sessions.random_seed.
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

        private void Awake()
        {
            _origin = transform.localPosition;
            _restRotation = transform.localRotation;

            // Fase derivada del indice en la jerarquia: dos objetos hermanos no
            // se mueven al unisono, y el resultado es el mismo en cada arranque.
            // Un Random.value aqui haria que la misma sesion reconstruida se
            // viera distinta.
            _phase = transform.GetSiblingIndex() * 0.37f;
        }

        private void OnEnable()
        {
            // Al reaparecer por un cambio de ESL, el objeto arranca en su sitio
            // en vez de saltar a media animacion.
            transform.localPosition = _origin;
            transform.localRotation = _restRotation;
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
            float t = (Time.time / swayPeriodSeconds + _phase) * Mathf.PI * 2f;
            float angle = Mathf.Sin(t) * swayDegrees;
            transform.localRotation = _restRotation * Quaternion.Euler(0f, 0f, angle);
        }

        private void UpdateTraverse()
        {
            float cycle = traverseSeconds + traversePauseSeconds;
            if (cycle <= 0f) return;

            float t = Mathf.Repeat(Time.time + _phase * cycle, cycle);
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

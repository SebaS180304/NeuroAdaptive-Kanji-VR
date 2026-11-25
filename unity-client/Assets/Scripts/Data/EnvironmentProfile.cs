using UnityEngine;

namespace NeuroAdaptiveVR.Data
{
    /// <summary>
    /// Los parametros de la tabla 8.1 de la spec para un nivel de ESL.
    ///
    /// Por que es un asset y no codigo: 8.2 es explicito -- "one scene, one
    /// controller"; LOW, MEDIUM y HIGH son configuraciones de parametros de la
    /// MISMA escena, no escenas distintas. Y la seccion 16 marca los tres
    /// parametros como "to validate", asi que van a cambiar despues del piloto.
    /// Un valor que va a cambiar tras mirar datos no se escribe en un .cs.
    ///
    /// Por que guarda RANGOS y no numeros: porque 8.1 escribio rangos. Un perfil
    /// con "5 props" hace desaparecer del proyecto el hecho de que la spec dijo
    /// "4-6", y nadie que lea el asset dentro de seis meses sabra que ahi habia
    /// un rango. El valor concreto se sortea con la seed de la sesion, que es la
    /// misma regla de reproducibilidad que el criterio de aceptacion 7 impone a
    /// la secuencia de trials: misma seed, mismo entorno.
    ///
    /// Lo que este asset NO lleva, a proposito: la lista de props. Los props
    /// viven en la escena, bajo EnvironmentalLayer, y cada uno declara su tier.
    /// Si el perfil de HIGH listara sus props y el de MEDIUM los suyos, la
    /// columna de ejemplos de 8.1 --que es literalmente aditiva, "MEDIUM +
    /// bookshelf..."-- estaria escrita dos veces y podria discrepar.
    /// </summary>
    [CreateAssetMenu(menuName = "NeuroAdaptive VR/Environment Profile",
                     fileName = "EnvironmentProfile")]
    public class EnvironmentProfile : ScriptableObject
    {
        [Header("Nivel que este perfil configura")]
        [Tooltip("Un perfil por nivel. EnvironmentalStimulationController rechaza " +
                 "un cambio a un nivel que no tenga perfil, en vez de cambiar el " +
                 "nivel sin cambiar la escena.")]
        public StimulationOrAssistanceLevel level = StimulationOrAssistanceLevel.Low;

        [Header("Densidad de props de fondo (spec 8.1)")]
        [Min(0)] public int propCountMin = 2;
        [Min(0)] public int propCountMax = 3;

        [Tooltip("Tier maximo que este nivel puede activar. Es lo que hace que la " +
                 "progresion sea aditiva como la describe 8.1: MEDIUM = LOW + mas " +
                 "cosas, HIGH = MEDIUM + mas cosas. Sin este tope, un HIGH podria " +
                 "salir con siete props de tier 1 y ninguno de los de HIGH.")]
        [Range(0, 3)] public int maxTier = 1;

        [Header("Objetos en movimiento (spec 8.1)")]
        [Min(0)] public int moverCountMin;
        [Min(0)] public int moverCountMax;

        [Header("Eventos perifericos (spec 8.1)")]
        [Tooltip("Segundos entre eventos. Ambos en 0 = sin eventos perifericos, " +
                 "que es lo que 8.1 pide para LOW.")]
        [Min(0f)] public float peripheralIntervalMinSeconds;
        [Min(0f)] public float peripheralIntervalMaxSeconds;

        [Header("Procedencia")]
        [TextArea(2, 4)]
        [Tooltip("De donde salen estos numeros. Util cuando el piloto los cambie.")]
        public string sourceNote = "Spec 8.1, marcado 'to validate' en 16.";

        public bool HasPeripheralEvents =>
            peripheralIntervalMaxSeconds > 0f && peripheralIntervalMinSeconds > 0f;

        /// <summary>
        /// Un perfil incoherente no se detecta mirandolo: se detecta cuando la
        /// escena hace algo raro dos semanas despues. Mejor gritar al editarlo.
        /// </summary>
        private void OnValidate()
        {
            if (propCountMax < propCountMin)
            {
                Debug.LogError($"[EnvironmentProfile:{name}] propCountMax ({propCountMax}) " +
                               $"es menor que propCountMin ({propCountMin}).", this);
            }
            if (moverCountMax < moverCountMin)
            {
                Debug.LogError($"[EnvironmentProfile:{name}] moverCountMax ({moverCountMax}) " +
                               $"es menor que moverCountMin ({moverCountMin}).", this);
            }
            if (peripheralIntervalMaxSeconds < peripheralIntervalMinSeconds)
            {
                Debug.LogError($"[EnvironmentProfile:{name}] el intervalo maximo " +
                               $"({peripheralIntervalMaxSeconds}s) es menor que el minimo " +
                               $"({peripheralIntervalMinSeconds}s).", this);
            }
            // Un solo extremo en cero deja el intervalo indefinido: o los dos o
            // ninguno. Sin esto, "0 a 30" se leeria como eventos instantaneos.
            bool onlyOneZero = (peripheralIntervalMinSeconds == 0f) ^ (peripheralIntervalMaxSeconds == 0f);
            if (onlyOneZero)
            {
                Debug.LogError($"[EnvironmentProfile:{name}] el intervalo tiene un solo extremo " +
                               "en cero. Para desactivar los eventos perifericos, ambos en 0.", this);
            }
        }
    }
}

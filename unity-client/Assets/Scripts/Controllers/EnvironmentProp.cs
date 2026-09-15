using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Marca un objeto de la Environmental Layer con el nivel a partir del cual
    /// aparece.
    ///
    /// La columna de ejemplos de la spec 8.1 es aditiva: MEDIUM es "LOW +
    /// decoracion japonesa, movimiento lento fuera de la ventana", y HIGH es
    /// "MEDIUM + estanteria, mas desorden decorativo". Con un tier por objeto,
    /// esa aditividad es una propiedad de la escena y no una lista que alguien
    /// tenga que mantener coherente en tres sitios.
    ///
    /// Que un objeto sea prop o mover NO se declara aqui: se decide por donde
    /// cuelga (EnvironmentalLayer/Props o EnvironmentalLayer/Movers). Un campo
    /// `kind` seria un segundo sitio donde dice lo mismo que la jerarquia, y
    /// podrian discrepar.
    /// </summary>
    public class EnvironmentProp : MonoBehaviour
    {
        [Tooltip("1 = visible desde LOW · 2 = desde MEDIUM · 3 = solo en HIGH.\n" +
                 "El controlador activa los tiers <= al del nivel activo, hasta " +
                 "alcanzar el conteo que sortea el perfil.")]
        [Range(1, 3)]
        [SerializeField] private int tier = 1;

        public int Tier => tier;
    }
}

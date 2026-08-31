using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Responsabilidad (spec seccion 5.2 / 9.2 / 14): maneja audio de
    /// lectura objetivo estandarizado y gateado por LAL. Regla dura que
    /// esta clase debe hacer cumplir siempre, en cualquier fase:
    /// Kanji -> Reading NUNCA reproduce el audio antes de la respuesta.
    ///
    /// FASE: implementacion real en Fase 2, dependiente de las
    /// grabaciones de audio estandarizadas (trabajo operativo en
    /// paralelo).
    /// </summary>
    public class PronunciationAudioController : MonoBehaviour
    {
        [SerializeField] private AudioSource audioSource;

        /// <summary>
        /// Punto unico de reproduccion pre-respuesta: cualquier llamado
        /// debe pasar por aca para que la regla Kanji->Reading sea
        /// imposible de saltarse por accidente.
        /// </summary>
        public bool TryPlayPreResponseCue(Data.RetrievalTrialType trialType)
        {
            if (trialType == Data.RetrievalTrialType.KanjiToReading)
            {
                Debug.LogWarning("[PronunciationAudioController] Blocked: target reading audio " +
                                  "is prohibited before response in Kanji->Reading trials.");
                return false;
            }

            // TODO (Fase 2): reproducir clip real segun LAL activo.
            return true;
        }
    }
}

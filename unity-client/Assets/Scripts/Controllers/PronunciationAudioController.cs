using NeuroAdaptiveVR.Data;
using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Audio de la lectura objetivo (spec 5.2 y 9.2).
    ///
    /// Regla dura que esta clase hace cumplir en todas las fases:
    /// **en un trial Kanji -> Reading, la lectura objetivo NUNCA suena antes
    /// de la respuesta.** La respuesta ES la lectura; reproducirla la
    /// regalaria.
    ///
    /// La regla vive en un solo metodo a proposito. Si aparece una segunda
    /// ruta capaz de reproducir audio pre-respuesta, deja de ser una garantia
    /// y pasa a ser una convencion -- y este proyecto ya perdio tiempo dos
    /// veces con contratos que solo vivian en un comentario.
    ///
    /// Los tres momentos de 9.2 son distintos y solo uno esta restringido:
    /// - Exposicion inicial (S5): estandarizado, suena para todos.
    /// - Feedback post-respuesta: puede repetirse para todos, incluido T3.
    /// - Asistencia pre-respuesta: gobernada por LAL, prohibida en T3.
    /// </summary>
    public class PronunciationAudioController : MonoBehaviour
    {
        [SerializeField] private AudioSource audioSource;

        private void Awake()
        {
            if (audioSource == null) audioSource = GetComponent<AudioSource>();
        }

        /// <summary>
        /// Exposicion inicial de S5. Estandarizada: suena para todos los
        /// participantes, sin importar LAL ni condicion. Es lo que hace
        /// comparable la instruccion entre condiciones (spec 9.2).
        /// </summary>
        public void PlayInitialExposure(KanjiItem item)
        {
            Play(item, "exposicion inicial");
        }

        /// <summary>
        /// Cue de asistencia pre-respuesta. **Unico camino permitido** para
        /// reproducir audio mientras el trial esta abierto.
        ///
        /// Devuelve false y no reproduce nada si el trial es T3 o si LAL no
        /// concede el cue de audio para este tipo de trial.
        /// </summary>
        public bool TryPlayPreResponseCue(RetrievalTrialType trialType, LalCue availableCues,
                                          KanjiItem item)
        {
            if (trialType == RetrievalTrialType.KanjiToReading)
            {
                Debug.LogWarning("[PronunciationAudioController] Blocked: target reading audio " +
                                  "is prohibited before response in Kanji->Reading trials " +
                                  "(spec 5.2, 9.2).");
                return false;
            }

            if ((availableCues & LalCue.TargetReadingAudio) == 0)
            {
                // No es un error: en LOW y OFF simplemente no hay audio disponible.
                return false;
            }

            Play(item, "cue pre-respuesta");
            return true;
        }

        /// <summary>
        /// Feedback post-respuesta. Permitido en los tres tipos de trial,
        /// T3 incluido: una vez respondido, la lectura ya no revela nada.
        /// </summary>
        public void PlayFeedback(KanjiItem item)
        {
            Play(item, "feedback post-respuesta");
        }

        private void Play(KanjiItem item, string moment)
        {
            if (item == null) return;

            var clip = item.TargetReadingAudio;

            // El log se emite SIEMPRE, haya clip o no. Es lo que permite verificar
            // la regla de T3 --que la lectura objetivo no suena antes de responder--
            // sin depender de que las grabaciones existan, y sigue sirviendo cuando
            // existan: deja en consola el momento exacto de cada disparo.
            Debug.Log($"[PronunciationAudio] ({moment}) {item.Character} -> {item.TargetReading}" +
                      (clip == null ? "  [sin clip autorado]" : ""));

            if (audioSource == null || clip == null) return;
            audioSource.PlayOneShot(clip);
        }
    }
}

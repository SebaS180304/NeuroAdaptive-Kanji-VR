using System;
using UnityEngine;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// Referencia temporal comun de la sesion (anteproyecto 5.3),
    /// espejo del lado Unity de app/services/session_clock.py.
    ///
    /// El instante cero real lo fija el backend en S0
    /// (`experiment_sessions.session_clock_started_at`); SessionBootstrap lo
    /// lee de la respuesta REST y lo instala aca con SetSessionZero. Todo lo
    /// que se mide en milisegundos desde entonces sale de ElapsedMs.
    ///
    /// Por que importa el cero y no basta el timestamp de pared: en Fase 4 la
    /// telemetria de Unity hay que alinearla con ventanas de EEG. Dos maquinas
    /// derivan entre si; un offset contra un cero conocido no. Y el campo no se
    /// puede reconstruir despues para datos ya recogidos.
    /// </summary>
    public class SessionClock : MonoBehaviour
    {
        private static DateTime? _sessionZeroUtc;
        private static bool _warnedMissingZero;

        /// <summary>Timestamp ISO-8601 UTC actual, para el sobre del mensaje.</summary>
        public static string NowIsoUtc() => DateTime.UtcNow.ToString("o");

        public static bool HasSessionZero => _sessionZeroUtc.HasValue;

        /// <summary>
        /// Instala el instante cero que reporto el backend. Idempotente por
        /// sesion: un segundo intento con otro valor se ignora con warning,
        /// porque mover el cero a media sesion invalida todos los
        /// `session_elapsed_ms` ya emitidos.
        /// </summary>
        public static void SetSessionZero(DateTime utc)
        {
            if (_sessionZeroUtc.HasValue)
            {
                if (Math.Abs((_sessionZeroUtc.Value - utc).TotalMilliseconds) > 1)
                {
                    Debug.LogWarning("[SessionClock] Ya habia un instante cero instalado " +
                                     $"({_sessionZeroUtc.Value:o}); se ignora el nuevo ({utc:o}). " +
                                     "Mover el cero invalidaria los session_elapsed_ms ya emitidos.");
                }
                return;
            }

            _sessionZeroUtc = utc.ToUniversalTime();
            Debug.Log($"[SessionClock] Instante cero de sesion: {_sessionZeroUtc.Value:o}");
        }

        /// <summary>
        /// Intenta instalar el cero desde el string ISO-8601 que devuelve el
        /// backend en `session_clock_started_at`. Devuelve false si viene
        /// vacio o no parsea.
        /// </summary>
        public static bool TrySetSessionZeroFromIso(string iso)
        {
            if (string.IsNullOrWhiteSpace(iso)) return false;
            if (!DateTime.TryParse(iso, null,
                    System.Globalization.DateTimeStyles.AdjustToUniversal |
                    System.Globalization.DateTimeStyles.AssumeUniversal, out var parsed))
            {
                Debug.LogWarning($"[SessionClock] No se pudo parsear session_clock_started_at: '{iso}'");
                return false;
            }
            SetSessionZero(parsed);
            return true;
        }

        /// <summary>
        /// Milisegundos desde el instante cero. Devuelve -1 si el cero no se
        /// instalo, y avisa una sola vez. El -1 es un centinela detectable:
        /// database/verify_events.sql lo reporta en vez de dejar pasar un
        /// valor plausible pero sin origen.
        /// </summary>
        public static long ElapsedMs()
        {
            if (!_sessionZeroUtc.HasValue)
            {
                if (!_warnedMissingZero)
                {
                    _warnedMissingZero = true;
                    Debug.LogError("[SessionClock] No hay instante cero de sesion instalado. " +
                                   "session_elapsed_ms sale como -1 en todos los eventos. " +
                                   "SessionBootstrap deberia llamar TrySetSessionZeroFromIso " +
                                   "con el session_clock_started_at que devuelve POST /sessions.");
                }
                return -1;
            }

            return (long)(DateTime.UtcNow - _sessionZeroUtc.Value).TotalMilliseconds;
        }

        /// <summary>Solo para tests y para reiniciar entre Plays en el Editor.</summary>
        public static void ResetForNewSession()
        {
            _sessionZeroUtc = null;
            _warnedMissingZero = false;
        }
    }
}

using System;
using UnityEngine;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// Referencia temporal comun de la sesion (anteproyecto 5.3),
    /// espejo del lado Unity de app/services/session_clock.py.
    ///
    /// El instante cero real de la sesion lo fija el backend en S0
    /// (`session_clock_started_at`); este componente solo expone un
    /// reloj UTC local consistente para timestampear eventos salientes
    /// hasta que la sincronizacion fina con WAVEX se implemente
    /// (Fase 4).
    /// </summary>
    public class SessionClock : MonoBehaviour
    {
        public static string NowIsoUtc() => DateTime.UtcNow.ToString("o");
    }
}

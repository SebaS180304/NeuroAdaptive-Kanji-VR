using System.Collections;
using System.Collections.Generic;
using System.Text;
using UnityEngine;
using UnityEngine.XR;
using UnityEngine.XR.Management;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// Levanta el runtime de XR al entrar a Play, y deja constancia de si hay
    /// visor o no.
    ///
    /// EL PROBLEMA, ENCONTRADO EL 17 DE SEPTIEMBRE EN LA SEGUNDA PASADA POR
    /// QUEST LINK
    /// -----------------------------------------------------------------------
    /// Con el visor puesto: la camara no seguia la cabeza, los mandos no
    /// estaban donde estaban las manos, el campo de vision se veia diminuto y
    /// --el sintoma que delato todo-- al girar la cabeza a la izquierda la
    /// escena parecia irse a la derecha.
    ///
    /// Los cuatro sintomas son uno solo. El diagnostico por consola dio:
    ///
    ///     XRDisplaySubsystem: 0
    ///     XRInputSubsystem: 0
    ///     InputDevices: 0
    ///     XRSettings: enabled=False isDeviceActive=False loadedDeviceName=''
    ///
    /// XR nunca arranco. No habia VR: lo que el participante veia era la
    /// **ventana de Game de Unity, plana, colgada en el escritorio virtual de
    /// Quest Link**. Sobre esa hipotesis los cuatro sintomas se explican sin
    /// sobrar ninguno: un panel plano no responde a la cabeza; su campo de
    /// vision es el de una camara de 60 grados recortada a un rectangulo que
    /// ocupa una parte del visor; los mandos son los simulados, quietos en el
    /// origen; y al girar la cabeza el panel se queda clavado en el mundo, asi
    /// que **aparenta** moverse en sentido contrario. La "vision invertida" no
    /// era un eje al reves: era mirar un cuadro colgado en la pared.
    ///
    /// POR QUE NO ARRANCO, Y POR QUE ESO VUELVE A PASAR
    /// -----------------------------------------------
    /// "Initialize XR on Startup" inicializa XR **una sola vez, al cargar el
    /// dominio** -- al abrir Unity y en cada recompilacion de scripts. No al
    /// dar Play. Si en ese instante Quest Link no estaba levantado, o el
    /// runtime activo de OpenXR no era el de Meta, la inicializacion se queda
    /// sin sesion y **Unity no vuelve a intentarlo nunca**. En el log solo
    /// queda "Loading OpenXR loader library at path: ..." y despues nada: ni
    /// error, ni aviso.
    ///
    /// De ahi que el orden natural de trabajo --abrir Unity, programar un
    /// rato, ponerse el visor, dar Play-- produzca exactamente este fallo.
    ///
    /// QUE HACE ESTE COMPONENTE
    /// ------------------------
    /// 1. Al entrar a Play, si XR no esta arriba, lo levanta
    ///    (InitializeLoaderSync + StartSubsystems). Eso convierte "conecta el
    ///    visor y reinicia Unity" en "conecta el visor y dale Play".
    /// 2. Si aun asi no hay visor, lo dice con todas sus letras en la consola.
    ///
    /// El punto 2 importa mas que el 1. Una sesion sin visor **no falla**:
    /// avanza de estado, aplica ESL, manda STATE_ENTERED y escribe filas en
    /// experiment_sessions y session_events que son indistinguibles de las de
    /// una sesion buena. El dato no sale malo, sale midiendo otra cosa -- que
    /// es el modo de fallo que este proyecto lleva persiguiendo desde el
    /// principio: dos representaciones de un mismo hecho que pueden discrepar
    /// en silencio. Aqui las dos representaciones eran "la base dice sesion de
    /// VR" y "el participante estaba viendo una ventana".
    /// </summary>
    [DefaultExecutionOrder(-100)]   // antes que SessionBootstrap
    public class XRRuntimeGuard : MonoBehaviour
    {
        [Tooltip("Intentar levantar XR al entrar a Play si no esta arriba. " +
                 "Apagarlo solo tiene sentido para reproducir el fallo a proposito.")]
        [SerializeField] private bool bringUpXrIfDown = true;

        [Tooltip("Cuanto esperar a que el subsistema de display empiece a correr. " +
                 "Los subsistemas arrancan asincronos: preguntar en el primer " +
                 "Update contestaria 'no hay visor' en una sesion que si lo tiene.")]
        [SerializeField] private float startupTimeoutSeconds = 10f;

        /// <summary>
        /// Si hay un visor de verdad pintando. Falso hasta que termina la
        /// comprobacion, asi que no se debe leer antes de OnHeadsetResolved.
        /// </summary>
        public static bool HeadsetActive { get; private set; }

        /// <summary>Volcado legible del estado de XR, para consola y pruebas.</summary>
        public static string Diagnosis { get; private set; } = "sin comprobar";

        /// <summary>Se dispara una vez, cuando ya se sabe si hay visor.</summary>
        public static event System.Action<bool> OnHeadsetResolved;

        private static readonly List<XRDisplaySubsystem> Displays = new();
        private static readonly List<XRInputSubsystem> Inputs = new();

        private void Awake()
        {
            HeadsetActive = false;
            Diagnosis = "sin comprobar";

            if (!bringUpXrIfDown || DisplayRunning()) return;

            var settings = XRGeneralSettings.Instance;
            if (settings == null || settings.Manager == null)
            {
                Debug.LogWarning("[XRRuntimeGuard] No hay XRGeneralSettings para este target. " +
                                 "Project Settings > XR Plug-in Management, pestana Standalone, " +
                                 "con OpenXR marcado.");
                return;
            }

            var manager = settings.Manager;

            // InitializeLoaderSync bloquea, y esta bien que bloquee: es un
            // arranque, no un frame de juego, y hacerlo asincrono obligaria a
            // que todo lo demas esperara igualmente.
            if (!manager.isInitializationComplete)
            {
                Debug.Log("[XRRuntimeGuard] XR no estaba inicializado (es lo normal si el visor " +
                          "se conecto despues de abrir Unity). Reintentando ahora.");
                manager.InitializeLoaderSync();
            }

            if (manager.activeLoader == null)
            {
                Debug.LogWarning("[XRRuntimeGuard] Ningun loader de XR pudo inicializar. " +
                                 "Casi siempre es que Quest Link no esta activo, o que el runtime " +
                                 "activo de OpenXR no es el de Meta.");
                return;
            }

            Debug.Log($"[XRRuntimeGuard] Loader activo: {manager.activeLoader.name}. Arrancando subsistemas.");
            manager.StartSubsystems();
        }

        private IEnumerator Start()
        {
            float limite = Time.realtimeSinceStartup + startupTimeoutSeconds;
            while (Time.realtimeSinceStartup < limite && !DisplayRunning())
                yield return null;

            HeadsetActive = DisplayRunning();
            Diagnosis = BuildDiagnosis();

            if (HeadsetActive)
            {
                Debug.Log("[XRRuntimeGuard] Visor activo.\n" + Diagnosis);
            }
            else
            {
                // Warning y no error: correr sin visor en el Editor es legitimo
                // y se hace todos los dias. Lo que no es legitimo es correr sin
                // visor **creyendo** que lo hay, y para eso basta con que el
                // mensaje diga exactamente que se va a ver.
                Debug.LogWarning(
                    "[XRRuntimeGuard] NO HAY VISOR: esta corrida es plana.\n" +
                    "Si tienes el Quest puesto, lo que estas viendo es la ventana de Game de " +
                    "Unity colgada en el escritorio virtual de Link: la cabeza no movera la " +
                    "camara, los mandos no seguiran a tus manos, el campo de vision sera el de " +
                    "una ventana y la escena parecera moverse al lado contrario al girar la " +
                    "cabeza.\n" +
                    "Revisa, en este orden: (1) que Meta Quest Link este abierto y el visor en " +
                    "modo Link ANTES de dar Play; (2) que el runtime activo de OpenXR sea el de " +
                    "Meta (en la app de Link: Settings > General > OpenXR Runtime > Set as " +
                    "active); (3) que Project Settings > XR Plug-in Management > Standalone " +
                    "tenga OpenXR marcado.\n" +
                    "Una sesion corrida asi produce filas que parecen validas y no lo son: " +
                    "no la uses como dato.\n" + Diagnosis);
            }

            OnHeadsetResolved?.Invoke(HeadsetActive);
        }

        private static bool DisplayRunning()
        {
            SubsystemManager.GetSubsystems(Displays);
            foreach (var d in Displays)
                if (d != null && d.running) return true;
            return false;
        }

        private static string BuildDiagnosis()
        {
            var sb = new StringBuilder();

            SubsystemManager.GetSubsystems(Displays);
            SubsystemManager.GetSubsystems(Inputs);

            sb.Append("  display=").Append(Displays.Count)
              .Append(" input=").Append(Inputs.Count)
              .Append(" isDeviceActive=").Append(XRSettings.isDeviceActive)
              .Append(" loadedDevice='").Append(XRSettings.loadedDeviceName).Append('\'')
              .Append(" eyeTex=").Append(XRSettings.eyeTextureWidth)
              .Append('x').Append(XRSettings.eyeTextureHeight);

            foreach (var s in Inputs)
                sb.Append("\n  origen de tracking = ").Append(s.GetTrackingOriginMode());

            var devices = new List<InputDevice>();
            InputDevices.GetDevices(devices);
            sb.Append("\n  dispositivos: ").Append(devices.Count);
            foreach (var d in devices)
                sb.Append("\n    '").Append(d.name).Append("' [").Append(d.characteristics).Append(']');

            return sb.ToString();
        }
    }
}

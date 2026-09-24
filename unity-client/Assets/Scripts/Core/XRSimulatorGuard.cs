using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.XR;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// Apaga el simulador de XRI cuando hay un visor de verdad.
    ///
    /// EL PROBLEMA, ENCONTRADO EL 17 DE SEPTIEMBRE EN LA PRIMERA PASADA POR
    /// QUEST LINK
    /// -----------------------------------------------------------------------
    /// `SimulatedDeviceLifecycleManager` crea dispositivos XR simulados --un
    /// HMD y dos mandos-- en cuanto arranca la escena. El `TrackedPoseDriver`
    /// de la camara se ata a un `&lt;XRHMD&gt;` por accion de input, y con dos HMD
    /// registrados en el Input System gana el simulado. El HMD simulado reposa
    /// en el origen y no responde a la cabeza real.
    ///
    /// No es un fallo del simulador: es correcto que simule. El fallo es que
    /// simule **al mismo tiempo** que el visor de verdad.
    ///
    /// NOTA SOBRE LA PASADA DEL 17 POR LA TARDE. Este componente se escribio
    /// creyendo que el simulador era la causa de que la camara no siguiera a la
    /// cabeza. No lo era: el diagnostico posterior mostro que XR nunca habia
    /// arrancado (ver XRRuntimeGuard). El simulador si habria secuestrado la
    /// pose en cuanto XR funcionara, asi que esta guarda sigue haciendo falta,
    /// pero conviene recordar que resolvia un problema que aun no se habia
    /// manifestado.
    ///
    /// COMO SE DISTINGUE UN VISOR REAL
    /// -------------------------------
    /// Por el subsistema de display. No sirve preguntar si hay un HMD --el
    /// simulador crea uno-- ni mirar el loader de XR Management, que en el
    /// Editor puede inicializar sin visor conectado. Un `XRDisplaySubsystem`
    /// corriendo significa que algo esta pintando dos ojos en un panel fisico,
    /// y el simulador no crea ninguno.
    ///
    /// La comprobacion va en dos tiempos, y el primero importa:
    ///
    /// - En Awake, si XR **ya** esta arriba (XRRuntimeGuard corre en -100 y lo
    ///   levanta antes), el simulador se apaga sin que llegue a registrar nada.
    ///   Asi el TrackedPoseDriver nunca se ata al HMD simulado y no hay que
    ///   confiar en que se reate solo al desaparecer.
    /// - Si no, se sondea durante unos segundos, porque los subsistemas
    ///   arrancan de forma asincrona y preguntar en un solo frame contestaria
    ///   "no hay visor" en una sesion que si lo tiene.
    /// </summary>
    public class XRSimulatorGuard : MonoBehaviour
    {
        [Tooltip("El objeto del simulador. Si se deja vacio, se usa este mismo.")]
        [SerializeField] private GameObject simulatorRoot;

        [Tooltip("Cuanto esperar a que arranque el subsistema de display antes de " +
                 "dar por hecho que no hay visor. Los subsistemas arrancan asincronos.")]
        [SerializeField] private float waitSeconds = 12f;

        private static readonly List<XRDisplaySubsystem> Displays = new();

        private bool _resuelto;

        private void Awake()
        {
            if (simulatorRoot == null) simulatorRoot = gameObject;

            // Camino rapido: XRRuntimeGuard ya levanto XR. Apagar aqui evita
            // que el simulador llegue a registrar dispositivos.
            if (RealHeadsetRunning()) Apagar("en Awake, antes de que el simulador registre nada");
        }

        private IEnumerator Start()
        {
            if (_resuelto) yield break;

            float limite = Time.realtimeSinceStartup + waitSeconds;
            while (Time.realtimeSinceStartup < limite)
            {
                if (RealHeadsetRunning())
                {
                    Apagar("tras el sondeo");
                    yield break;
                }
                yield return null;
            }

            Debug.Log("[XRSimulatorGuard] Sin visor: el simulador sigue activo para poder " +
                      "probar con teclado y raton en el Editor.");
        }

        private void Apagar(string cuando)
        {
            _resuelto = true;
            Debug.Log($"[XRSimulatorGuard] Visor real detectado ({cuando}): se apaga el simulador " +
                      $"'{simulatorRoot.name}'. Con los dos activos, la camara sigue al HMD " +
                      "simulado y deja de responder a la cabeza.");
            simulatorRoot.SetActive(false);
        }

        private static bool RealHeadsetRunning()
        {
            SubsystemManager.GetSubsystems(Displays);
            foreach (var d in Displays)
                if (d != null && d.running) return true;
            return false;
        }
    }
}

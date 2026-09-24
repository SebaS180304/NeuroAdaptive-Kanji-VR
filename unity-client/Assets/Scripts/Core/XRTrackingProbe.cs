using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.XR;
using UnityEngine.XR;
using XRNodeDevice = UnityEngine.XR.InputDevice;
using XRUsages = UnityEngine.XR.CommonUsages;
using InputTPD = UnityEngine.InputSystem.XR.TrackedPoseDriver;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// SONDA TEMPORAL DE DIAGNOSTICO. Se quita en cuanto la cabeza funcione.
    ///
    /// Sintoma del 24 de septiembre: con el visor puesto, XR arriba y las manos
    /// siguiendo a los mandos, la sala va "pegada a la cara": se ve en estereo
    /// pero girar la cabeza no cambia la vista.
    ///
    /// La cadena que mueve la camara tiene tres eslabones, y esta sonda mide
    /// cada uno por separado durante unos segundos mientras se gira la cabeza:
    ///
    ///   1. RUNTIME  -- la rotacion que OpenXR reporta para el visor (API XR
    ///                  clasica, sin pasar por el Input System).
    ///   2. ACCION   -- lo que lee la accion XRI Head/Rotation del
    ///                  TrackedPoseDriver, y DE QUE DISPOSITIVO lo lee.
    ///   3. CAMARA   -- la rotacion local que la camara termina teniendo.
    ///
    /// Donde el giro deja de propagarse esta el bloqueo, y el veredicto final
    /// lo dice sin interpretar.
    /// </summary>
    public class XRTrackingProbe : MonoBehaviour
    {
        [SerializeField] private float startDelaySeconds = 2f;
        [SerializeField] private float durationSeconds = 15f;
        [SerializeField] private float sampleIntervalSeconds = 0.5f;

        private const string Tag = "[XRTrackingProbe]";

        private IEnumerator Start()
        {
            yield return new WaitForSeconds(startDelaySeconds);

            var cam = Camera.main;
            var tpd = cam != null ? cam.GetComponent<InputTPD>() : null;
            var action = tpd != null ? tpd.rotationInput.action : null;

            Debug.Log($"{Tag} Empieza. GIRA LA CABEZA a izquierda, derecha, arriba y abajo durante {durationSeconds:0} s.\n" +
                      DescribeHmdDevices() + "\n" + DescribeAction(action));

            float end = Time.realtimeSinceStartup + durationSeconds;
            bool first = true;
            float raw0 = 0, act0 = 0, cam0 = 0;
            float rawMin = 0, rawMax = 0, actMin = 0, actMax = 0, camMin = 0, camMax = 0;
            var samples = new StringBuilder();

            while (Time.realtimeSinceStartup < end)
            {
                float rawYaw = float.NaN, actYaw = float.NaN, camYaw = float.NaN;

                var head = InputDevices.GetDeviceAtXRNode(XRNode.Head);
                if (head.isValid && head.TryGetFeatureValue(XRUsages.deviceRotation, out Quaternion rq))
                    rawYaw = rq.eulerAngles.y;

                if (action != null && action.enabled)
                    actYaw = action.ReadValue<Quaternion>().eulerAngles.y;

                if (cam != null) camYaw = cam.transform.localEulerAngles.y;

                if (first)
                {
                    raw0 = rawYaw; act0 = actYaw; cam0 = camYaw;
                    first = false;
                }

                Track(rawYaw, raw0, ref rawMin, ref rawMax);
                Track(actYaw, act0, ref actMin, ref actMax);
                Track(camYaw, cam0, ref camMin, ref camMax);

                string src = action?.activeControl?.device?.name ?? "(ninguno)";
                samples.AppendLine($"  runtime={Fmt(rawYaw)}  accion={Fmt(actYaw)} [de: {src}]  camara={Fmt(camYaw)}");

                yield return new WaitForSeconds(sampleIntervalSeconds);
            }

            float rawRange = rawMax - rawMin, actRange = actMax - actMin, camRange = camMax - camMin;

            string veredicto;
            if (rawRange < 5f)
                veredicto = "El RUNTIME no reporta giro. El problema esta antes de Unity: Quest Link, " +
                            "el sensor de proximidad del visor, o el runtime de OpenXR activo.";
            else if (actRange < 5f)
                veredicto = "El runtime SI gira, pero la accion XRI Head/Rotation NO. La camara esta leyendo " +
                            $"de otro dispositivo ('{action?.activeControl?.device?.name ?? "ninguno"}') o la " +
                            "accion no esta atada al visor real.";
            else if (camRange < 5f)
                veredicto = "El runtime y la accion SI giran, pero la CAMARA NO. Algo sobrescribe la " +
                            "transformada de la camara despues del TrackedPoseDriver.";
            else
                veredicto = "Los tres eslabones giran: el tracking de cabeza funciona.";

            Debug.Log($"{Tag} Resultado tras {durationSeconds:0} s.\n" +
                      $"  Rango de giro horizontal -> runtime {rawRange:0.0} grados, accion {actRange:0.0} grados, camara {camRange:0.0} grados\n" +
                      $"  VEREDICTO: {veredicto}\n" +
                      "  Muestras:\n" + samples);
        }

        private static void Track(float yaw, float yaw0, ref float min, ref float max)
        {
            if (float.IsNaN(yaw) || float.IsNaN(yaw0)) return;
            float d = Mathf.DeltaAngle(yaw0, yaw);
            if (d < min) min = d;
            if (d > max) max = d;
        }

        private static string Fmt(float v) => float.IsNaN(v) ? "  n/a " : $"{v,6:0.0}";

        private static string DescribeHmdDevices()
        {
            var sb = new StringBuilder("  Visores (XRHMD) registrados en el Input System:");
            int n = 0;
            foreach (var d in InputSystem.devices)
            {
                if (!(d is XRHMD)) continue;
                n++;
                sb.Append($"\n    '{d.name}' layout={d.layout} enabled={d.enabled} " +
                          $"(simulado={d.name.ToLowerInvariant().Contains("simulat")})");
            }
            if (n == 0) sb.Append("\n    NINGUNO");
            else if (n > 1) sb.Append($"\n    AVISO: hay {n} visores; la camara puede estar leyendo el equivocado.");
            return sb.ToString();
        }

        private static string DescribeAction(InputAction action)
        {
            if (action == null) return "  Accion de rotacion del TrackedPoseDriver: NO ENCONTRADA";
            var sb = new StringBuilder($"  Accion '{action.actionMap?.name}/{action.name}' enabled={action.enabled}; controles atados:");
            foreach (var c in action.controls) sb.Append($"\n    {c.path}");
            if (action.controls.Count == 0) sb.Append("\n    NINGUNO");
            return sb.ToString();
        }
    }
}

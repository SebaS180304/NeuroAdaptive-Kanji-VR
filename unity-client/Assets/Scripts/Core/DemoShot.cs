using Unity.Cinemachine;
using UnityEngine;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// One shot of the 30 Oct teaser (Plan_Grabacion_Demo_29oct.md §3), on its own CinemachineCamera with a spline
    /// dolly. The DemoDirector launches it with the digit key of its number; the camera holds still for the 2 s
    /// margins and travels the dolly once, eased, between moveStart and moveEnd.
    /// </summary>
    [RequireComponent(typeof(CinemachineCamera), typeof(CinemachineSplineDolly))]
    public class DemoShot : MonoBehaviour
    {
        public enum Action { None, ObjectApproach }

        public const float Margin = 2f;

        [Tooltip("Shot number of the recording plan: T6 is 6, launched with key 6.")]
        public int number = 6;
        [Tooltip("Second part of the file name: T6_<cameraName>_<attempt>.mp4.")]
        public string cameraName = "orbit";
        public Action action = Action.None;
        [Tooltip("Seconds from the start of the clip; the margins are included in total.")]
        public float actionAt = Margin;
        public float moveStart = 3f;
        public float moveEnd = 9f;
        public float total = 12f;
        [Tooltip("Out to the end of the dolly and back to the start inside the move window, eased both ways.")]
        public bool returnHome;
        [Tooltip("Where the depth of field focuses; empty follows the 3D object, or the board while there is none.")]
        public Transform focus;
        [Tooltip("The camera's LookAt target follows the focus point (the board, then the object as it comes and floats), eased.")]
        public bool lookAtFocus;

        public string FileStem => $"T{number}_{cameraName}";

        /// <summary>Dolly position (0-1) t seconds into the clip: still before moveStart and after moveEnd, smoothstep between.</summary>
        public static float Travel(float t, float start, float end)
        {
            float x = Mathf.Clamp01((t - start) / Mathf.Max(end - start, 1e-4f));
            return x * x * (3f - 2f * x);
        }

        /// <summary>Dolly position for this shot's settings: one travel, or out and back with the turn at mid-window.</summary>
        public static float Position(float t, float start, float end, bool returnHome)
        {
            if (!returnHome) return Travel(t, start, end);
            float mid = 0.5f * (start + end);
            return t < mid ? Travel(t, start, mid) : 1f - Travel(t, mid, end);
        }
    }
}

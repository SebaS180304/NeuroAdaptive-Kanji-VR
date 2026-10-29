using NeuroAdaptiveVR.Data;
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
        public enum Action { None, ObjectApproach, C3, Animal, Hint }

        public const float Margin = 2f;

        [Tooltip("Shot number of the recording plan: T6 is 6, launched with key 6.")]
        public int number = 6;
        [Tooltip("Launched with Shift + the digit: a second camera for the same shot number (T2's orbit).")]
        public bool shift;
        [Tooltip("Adds the room's ESL level to the file name (T2 is the same frame at LOW, MEDIUM and HIGH).")]
        public bool levelInName;
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
        [Tooltip("Focus pull: from the board to the first active room object whose name starts with this (T4: OutsideFigure), between pullStart and pullEnd.")]
        public string pullTo;
        public float pullStart = 3f;
        public float pullEnd = 4.5f;
        [Tooltip("Above 0: the pull waits for the target to walk out past this |x| (T4: the silhouette appearing in the window), lasts pullEnd - pullStart and the clip ends holdAfterPull later.")]
        public float pullAtAbsX;
        public float holdAfterPull = 5f;
        [Tooltip("Action Animal: the PeripheralAnimation to play (T5); look and focus follow it, and the clip lasts its animation plus the margins.")]
        public string animal;
        [Tooltip("Action Hint: a real trial of this type at this LAL level, with the hint the game gives there (T8).")]
        public RetrievalTrialType hintType = RetrievalTrialType.KanjiToReading;
        public StimulationOrAssistanceLevel hintLevel = StimulationOrAssistanceLevel.High;
        [Tooltip("The camera's LookAt target follows the focus point (the board, then the object as it comes and floats), eased.")]
        public bool lookAtFocus;

        public string FileStem => Stem(number, cameraName, null);

        /// <summary>T2_wide, or T2_wide_HIGH when the level goes in the name.</summary>
        public static string Stem(int number, string camera, string level) =>
            string.IsNullOrEmpty(level) ? $"T{number}_{camera}" : $"T{number}_{camera}_{level}";

        /// <summary>Dolly position (0-1) t seconds into the clip: still before moveStart and after moveEnd, smoothstep between.</summary>
        public static float Travel(float t, float start, float end)
        {
            float x = Mathf.Clamp01((t - start) / Mathf.Max(end - start, 1e-4f));
            return x * x * (3f - 2f * x);
        }

        /// <summary>Several cameras on one key: each press records the next one, in order, round and round (T5, T8).</summary>
        public static int NextIndex(int last, int count) => count <= 0 ? -1 : (last + 1) % count;

        /// <summary>The target has just walked out past |x| (moving away from the centre of the room).</summary>
        public static bool Crossed(float previousAbsX, float absX, float threshold) => previousAbsX < threshold && absX >= threshold;

        /// <summary>Dolly position for this shot's settings: one travel, or out and back with the turn at mid-window.</summary>
        public static float Position(float t, float start, float end, bool returnHome)
        {
            if (!returnHome) return Travel(t, start, end);
            float mid = 0.5f * (start + end);
            return t < mid ? Travel(t, start, mid) : 1f - Travel(t, mid, end);
        }
    }
}

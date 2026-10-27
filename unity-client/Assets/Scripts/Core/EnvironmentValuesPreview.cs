using System.Linq;
using NeuroAdaptiveVR.Controllers;
using NeuroAdaptiveVR.Data;
using UnityEngine;
using UnityEngine.InputSystem;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// Headset stop of E1 (D-F6-85, D-F6-101): the candidate values for the silhouettes, the curtains and the wind,
    /// switched live from the keyboard so Sebas can compare them, with the ESL held at MEDIUM (or HIGH). Nothing is
    /// saved: the offsets go on child transforms and the wind on runtime material copies, so leaving Play undoes
    /// it all. The approved values are then written into the scene in their own commit.
    ///   L  level MEDIUM / HIGH        S  silhouette distance: today 7.5 m · 5.5 m · 4.8 m
    ///   D  silhouette ground lowered so the sill cuts at the hip (on / off)
    ///   C  curtains drawn outward: today · 25 % · 40 % of the sheet width    W  wind A: 6 · 9 · 12 cm
    /// Add it before Play and remove it after: never send editor commands during Play (finding P2).
    /// shortcut: a tool for one headset stop; delete it once the E1 values are committed.
    /// </summary>
    public class EnvironmentValuesPreview : MonoBehaviour
    {
        // Geometry read in Unity on 27 Oct: eye (0, 1.60, 0); window wall at z 3.96; the open half of each window
        // runs from |x| 1.65 (wall on the board side) to 2.48 (the paper half); its sill is at y 0.69.
        private const float EyeY = 1.60f, WallZ = 3.96f, OpenInner = 1.65f, OpenOuter = 2.48f, SillY = 0.69f;
        private const float TodayZ = 7.5f, TodayStart = 3.7f, HalfWidth = 0.17f, Margin = 0.15f, HipHeight = 0.65f;
        private const float SheetWidth = 0.95f;

        private static readonly float[] SilhouetteZ = { TodayZ, 5.5f, 4.8f };
        private static readonly float[] CurtainDraw = { 0f, 0.25f, 0.40f };
        private static readonly float[] WindAmplitude = { 0.06f, 0.09f, 0.12f };

        [SerializeField] private StimulationOrAssistanceLevel level = StimulationOrAssistanceLevel.Medium;
        [SerializeField, Range(0, 2)] private int silhouette;
        [SerializeField] private bool lowerGround;
        [SerializeField, Range(0, 2)] private int curtain;
        [SerializeField, Range(0, 2)] private int wind;

        private EnvironmentalStimulationController _esl;
        private Transform[] _figures, _sheets;
        private Renderer[] _windRenderers;
        private string _shown;

        /// <summary>Height above the figure's feet where the sill hides it, standing at depth z on flat ground.</summary>
        public static float SillCutAt(float z) => EyeY - (EyeY - SillY) * z / WallZ;

        /// <summary>Start of the walk (|x|) at depth z: hidden behind the wall on the board side, with a margin.</summary>
        public static float StartAt(float z) => OpenInner * z / WallZ - HalfWidth - Margin;

        private void Start()
        {
            _esl = FindAnyObjectByType<EnvironmentalStimulationController>();
            var movers = GameObject.Find("EnvironmentalLayer").transform.Find("Movers").Cast<Transform>().ToList();
            _figures = movers.Where(t => t.name.StartsWith("OutsideFigure")).Select(t => t.GetChild(0)).ToArray();
            _sheets = movers.Where(t => t.name.StartsWith("Curtain")).Select(t => t.GetChild(0)).ToArray();
            _windRenderers = movers.Where(t => t.name.StartsWith("Curtain"))
                .SelectMany(t => t.GetComponentsInChildren<Renderer>(true)).ToArray();
        }

        private void Update()
        {
            var k = Keyboard.current;
            if (k != null)
            {
                if (k.lKey.wasPressedThisFrame) level = level == StimulationOrAssistanceLevel.Medium ? StimulationOrAssistanceLevel.High : StimulationOrAssistanceLevel.Medium;
                if (k.sKey.wasPressedThisFrame) silhouette = (silhouette + 1) % SilhouetteZ.Length;
                if (k.dKey.wasPressedThisFrame) lowerGround = !lowerGround;
                if (k.cKey.wasPressedThisFrame) curtain = (curtain + 1) % CurtainDraw.Length;
                if (k.wKey.wasPressedThisFrame) wind = (wind + 1) % WindAmplitude.Length;
            }
            if (_esl != null && _esl.CurrentLevel != level) _esl.SetLevel(level, betweenTrials: true);

            float z = SilhouetteZ[silhouette];
            float drop = lowerGround ? Mathf.Min(0f, SillCutAt(z) - HipHeight) : 0f;
            foreach (var f in _figures)
            {
                float side = Mathf.Sign(f.parent.position.x);   // the mover walks outward from its root
                f.localPosition = new Vector3(side * (StartAt(z) - TodayStart), drop, z - TodayZ);
            }
            foreach (var s in _sheets)
                s.localPosition = new Vector3(Mathf.Sign(s.parent.position.x) * CurtainDraw[curtain] * SheetWidth, 0f, 0f);
            foreach (var r in _windRenderers)
                if (r.sharedMaterial != null && r.sharedMaterial.HasProperty("_WindAmplitude"))
                    r.material.SetFloat("_WindAmplitude", WindAmplitude[wind]);   // runtime copy, never the asset

            string shown = $"{level} · silhouette z {z} m{(lowerGround ? $", ground {drop:+0.00;-0.00} m" : "")} " +
                           $"(sill cuts at {SillCutAt(z) - drop:0.00} m of 1.36) · curtains {CurtainDraw[curtain] * 100:0} % · wind {WindAmplitude[wind] * 100:0} cm";
            if (shown != _shown) { _shown = shown; Debug.Log($"[EnvironmentValuesPreview] {shown}"); }
        }
    }
}

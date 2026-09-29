using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Highlights a button on the controllers the participant is holding, with an
    /// optional label joined to it by a thin line (demo of 30 September, controls
    /// induction). It works on the in-VR XRI UniversalController models, so what
    /// lights up is the controller in the participant's own hand, not a picture.
    ///
    /// Only <see cref="ControlsIntro"/> uses it. Nothing shows outside the
    /// induction, so the trials carry no extra visual stimulus.
    ///
    /// The highlight swaps the mesh's material for a runtime copy with emission
    /// and restores the original when hidden. ControllerAnimator only moves
    /// transforms, so the trigger keeps its press animation while lit.
    /// </summary>
    public class ControllerCallouts : MonoBehaviour
    {
        private const string Log = "[ControllerCallouts]";

        public enum Part { Trigger, Menu }

        [Tooltip("'Left Controller Visual' under the XR Origin.")]
        [SerializeField] private Transform leftVisual;
        [Tooltip("'Right Controller Visual' under the XR Origin.")]
        [SerializeField] private Transform rightVisual;
        [Tooltip("The board canvas: its font is copied for the labels.")]
        [SerializeField] private Canvas boardCanvas;

        [Header("Look")]
        [Tooltip("The Learning Board's accent (selected segment / buttons).")]
        [SerializeField] private Color accent = new(0.35f, 0.65f, 1f, 1f);
        [SerializeField] private float pulseHz = 1.5f;
        [Tooltip("Label offset from the button, in metres, along the camera's right (outwards) and up.")]
        [SerializeField] private Vector2 labelOffset = new(0.075f, 0.055f);
        [SerializeField] private float labelFontSize = 30f;

        private sealed class Lit
        {
            public Renderer Renderer;
            public Material Original;
            public Material Glow;
        }

        private sealed class Label
        {
            public Transform Anchor;
            public float Side;            // -1 left hand, +1 right hand
            public GameObject Root;
            public RectTransform Panel;
            public LineRenderer Line;
        }

        private readonly List<Lit> _lit = new();
        private readonly List<Label> _labels = new();
        private Material _lineMat;
        private Camera _cam;

        public bool AnyShown => _lit.Count > 0 || _labels.Count > 0;

        private void Awake()
        {
            if (leftVisual == null) leftVisual = FindVisual("Left Controller Visual");
            if (rightVisual == null) rightVisual = FindVisual("Right Controller Visual");
        }

        private void OnDisable() => HideAll();

        // ------------------------------------------------------------------
        // API
        // ------------------------------------------------------------------

        /// <summary>Lights <paramref name="part"/> on the chosen hands; a label is added when given.</summary>
        public void Show(Part part, bool left, bool right, string label = null)
        {
            if (left) ShowOn(leftVisual, part, -1f, label);
            if (right) ShowOn(rightVisual, part, +1f, label);
        }

        public void HideAll()
        {
            foreach (var l in _lit)
            {
                if (l.Renderer != null) l.Renderer.sharedMaterial = l.Original;
                if (l.Glow != null) Destroy(l.Glow);
            }
            _lit.Clear();
            foreach (var lb in _labels)
                if (lb.Root != null) Destroy(lb.Root);
            _labels.Clear();
        }

        // ------------------------------------------------------------------

        private void ShowOn(Transform visual, Part part, float side, string label)
        {
            if (visual == null)
            {
                Debug.LogWarning($"{Log} no controller visual for side {side}");
                return;
            }
            var mesh = FindDeep(visual, part == Part.Trigger ? "Trigger" : "Button_Home");
            var r = mesh != null ? mesh.GetComponent<Renderer>() : null;
            if (r == null)
            {
                Debug.LogWarning($"{Log} {part} mesh not found under {visual.name}");
                return;
            }

            if (_lit.Find(x => x.Renderer == r) == null)
            {
                var glow = new Material(r.sharedMaterial) { name = r.sharedMaterial.name + " (callout)" };
                glow.EnableKeyword("_EMISSION");
                glow.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
                _lit.Add(new Lit { Renderer = r, Original = r.sharedMaterial, Glow = glow });
                r.sharedMaterial = glow;
            }

            if (!string.IsNullOrEmpty(label) && _labels.Find(x => x.Anchor == r.transform) == null)
                _labels.Add(MakeLabel(r.transform, side, label));
        }

        private void LateUpdate()
        {
            if (!AnyShown) return;

            // Pulse between a dim and a bright accent: always clearly lit, never off.
            float s = 0.5f + 0.5f * Mathf.Sin(Time.unscaledTime * pulseHz * 2f * Mathf.PI);
            Color baseCol = Color.Lerp(accent * 0.75f, Color.Lerp(accent, Color.white, 0.35f), s);
            baseCol.a = 1f;
            Color emis = accent * Mathf.Lerp(0.6f, 1.6f, s);
            foreach (var l in _lit)
            {
                if (l.Glow == null) continue;
                if (l.Glow.HasProperty("_BaseColor")) l.Glow.SetColor("_BaseColor", baseCol);
                if (l.Glow.HasProperty("_Color")) l.Glow.SetColor("_Color", baseCol);
                if (l.Glow.HasProperty("_EmissionColor")) l.Glow.SetColor("_EmissionColor", emis);
            }

            if (_cam == null) _cam = Camera.main;
            if (_cam == null) return;
            var ct = _cam.transform;
            foreach (var lb in _labels)
            {
                if (lb.Anchor == null || lb.Root == null) continue;
                // A controller that loses tracking is deactivated by XRI: hide its label with it.
                bool on = lb.Anchor.gameObject.activeInHierarchy;
                if (lb.Root.activeSelf != on) lb.Root.SetActive(on);
                if (!on) continue;
                // Beside the hand, outwards and up in view space, so it never covers the controller.
                Vector3 p = lb.Anchor.GetComponent<Renderer>().bounds.center;
                Vector3 pos = p + ct.right * (labelOffset.x * lb.Side) + ct.up * labelOffset.y;
                lb.Root.transform.position = pos;
                lb.Root.transform.rotation = ct.rotation;   // parallel to the view: no roll, always readable

                // Line from the panel's inner edge to the button.
                float halfW = lb.Panel.rect.width * 0.5f * lb.Root.transform.lossyScale.x;
                float halfH = lb.Panel.rect.height * 0.5f * lb.Root.transform.lossyScale.y;
                Vector3 edge = pos - ct.right * (halfW * lb.Side) - ct.up * halfH;
                lb.Line.SetPosition(0, edge);
                lb.Line.SetPosition(1, p);
                lb.Line.startColor = lb.Line.endColor = accent;
            }
        }

        private Label MakeLabel(Transform anchor, float side, string text)
        {
            var root = new GameObject("Callout " + anchor.name, typeof(RectTransform), typeof(Canvas));
            root.transform.SetParent(transform, false);
            var canvas = root.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.WorldSpace;
            canvas.sortingOrder = 10;
            var rt = (RectTransform)root.transform;
            rt.sizeDelta = new Vector2(10f, 10f);
            rt.localScale = Vector3.one * 0.0005f;    // 30 pt ≈ 1.5 cm

            var panelGo = new GameObject("Panel", typeof(RectTransform), typeof(Image));
            panelGo.transform.SetParent(rt, false);
            var img = panelGo.GetComponent<Image>();
            img.color = new Color(0.05f, 0.08f, 0.13f, 0.92f);
            img.raycastTarget = false;
            var panel = (RectTransform)panelGo.transform;

            var textGo = new GameObject("Text", typeof(RectTransform), typeof(TextMeshProUGUI));
            textGo.transform.SetParent(panel, false);
            var tmp = textGo.GetComponent<TextMeshProUGUI>();
            var boardText = boardCanvas != null ? boardCanvas.GetComponentInChildren<TMP_Text>(true) : null;
            if (boardText != null) tmp.font = boardText.font;
            tmp.text = text;
            tmp.fontSize = labelFontSize;
            tmp.color = Color.white;
            tmp.alignment = TextAlignmentOptions.Center;
            tmp.textWrappingMode = TextWrappingModes.NoWrap;
            tmp.raycastTarget = false;
            tmp.ForceMeshUpdate();
            Vector2 size = tmp.GetPreferredValues(text) + new Vector2(36f, 18f);
            panel.sizeDelta = size;
            var trt = (RectTransform)textGo.transform;
            trt.anchorMin = Vector2.zero; trt.anchorMax = Vector2.one;
            trt.offsetMin = trt.offsetMax = Vector2.zero;

            // Accent bar on the side facing the controller.
            var barGo = new GameObject("Bar", typeof(RectTransform), typeof(Image));
            barGo.transform.SetParent(panel, false);
            var bar = barGo.GetComponent<Image>();
            bar.color = accent;
            bar.raycastTarget = false;
            var brt = (RectTransform)barGo.transform;
            float x = side > 0 ? 0f : 1f;          // right hand: bar on the left edge; left hand: right edge
            brt.anchorMin = new Vector2(x, 0f); brt.anchorMax = new Vector2(x, 1f);
            brt.pivot = new Vector2(x, 0.5f);
            brt.sizeDelta = new Vector2(8f, 0f);
            brt.anchoredPosition = Vector2.zero;

            if (_lineMat == null)
            {
                var sh = Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Sprites/Default");
                _lineMat = new Material(sh) { name = "CalloutLine" };
                if (_lineMat.HasProperty("_BaseColor")) _lineMat.SetColor("_BaseColor", accent);
            }
            var lineGo = new GameObject("Line");
            lineGo.transform.SetParent(transform, false);
            lineGo.transform.SetParent(root.transform, true);
            var line = lineGo.AddComponent<LineRenderer>();
            line.useWorldSpace = true;
            line.positionCount = 2;
            line.widthMultiplier = 0.0018f;
            line.sharedMaterial = _lineMat;
            line.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            line.receiveShadows = false;

            return new Label { Anchor = anchor, Side = side, Root = root, Panel = panel, Line = line };
        }

        // ------------------------------------------------------------------

        private static Transform FindVisual(string name)
        {
            foreach (var t in FindObjectsByType<Transform>(FindObjectsInactive.Include))
                if (t.name == name) return t;
            return null;
        }

        private static Transform FindDeep(Transform t, string name)
        {
            if (t.name == name) return t;
            foreach (Transform c in t)
            {
                var f = FindDeep(c, name);
                if (f != null) return f;
            }
            return null;
        }
    }
}

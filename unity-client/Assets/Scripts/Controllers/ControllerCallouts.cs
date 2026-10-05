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
    ///
    /// The Menu button (5 October, phase test F3). OBS_02 found its marking
    /// confusing; the text was fine. On the XRI model the button is a 6 mm dot
    /// next to the face buttons, lit in the same blue as the trigger, with a
    /// label off to the side whose line crossed the face buttons. Now it has its
    /// own colour (amber, never used for the trigger), a pulsing ring around the
    /// button several times its size, and the label sits straight above the
    /// button in view, with a vertical line down to it.
    ///
    /// Meta Quest 2 models (5 October, after the headset check of F3). The
    /// generic XRI model does not have the Quest 2 layout, so the participant
    /// saw a lit button that was not where their thumb found it. The visuals are
    /// now the Touch for Quest 2 models (Assets/Models/MetaQuest2Controllers).
    /// Each is one skinned mesh with a bone per button; its mesh was split in the
    /// Editor into three submeshes by bone weight (OculusTouchForQuest2_*_Buttons):
    /// 0 the body, 1 the trigger (b_trigger_front), 2 the menu button
    /// (b_button_oculus). A part found as a bone glows through its submesh's
    /// material slot; a part found as its own mesh (the generic model, kept as a
    /// fallback) glows through its renderer. Same look either way.
    /// </summary>
    public class ControllerCallouts : MonoBehaviour
    {
        private const string Log = "[ControllerCallouts]";

        public enum Part { Trigger, Menu }

        [Tooltip("The left controller model: 'Left MetaQuest2 Model' (or the generic 'Left Controller Visual').")]
        [SerializeField] private Transform leftVisual;
        [Tooltip("The right controller model: 'Right MetaQuest2 Model' (or the generic 'Right Controller Visual').")]
        [SerializeField] private Transform rightVisual;
        [Tooltip("The board canvas: its font is copied for the labels.")]
        [SerializeField] private Canvas boardCanvas;

        [Header("Look")]
        [Tooltip("The Learning Board's accent (selected segment / buttons).")]
        [SerializeField] private Color accent = new(0.35f, 0.65f, 1f, 1f);
        [Tooltip("Menu button only: its own colour, so it never reads as the trigger.")]
        [SerializeField] private Color menuAccent = new(1f, 0.72f, 0.20f, 1f);
        [SerializeField] private float pulseHz = 1.5f;
        [Tooltip("Label offset from the button, in metres, along the camera's right (outwards) and up.")]
        [SerializeField] private Vector2 labelOffset = new(0.075f, 0.055f);
        [SerializeField] private float labelFontSize = 30f;

        [Header("Menu button (5 October, phase test F3)")]
        [Tooltip("Label of the Menu button: straight above it in view, in metres.")]
        [SerializeField] private float menuLabelHeight = 0.065f;
        [Tooltip("Radius of the ring around the Menu button, in metres (the button is ~6 mm).")]
        [SerializeField] private float menuRingRadius = 0.009f;
        [SerializeField] private float menuRingWidth = 0.0025f;

        // Mesh name on the generic XRI model, bone name on the Meta Quest 2 models.
        private static readonly string[] TriggerNames = { "b_trigger_front", "Trigger" };
        private static readonly string[] MenuNames = { "b_button_oculus", "Button_Home" };

        // Material slots of the split Meta Quest 2 mesh (see the class summary).
        private const int TriggerSlot = 1, MenuSlot = 2;

        private sealed class Lit
        {
            public Renderer Renderer;
            public int Slot;
            public Material Original;
            public Material Glow;
            public Color Accent;
        }

        private sealed class Label
        {
            public Transform Anchor;
            public float Side;            // -1 left hand, +1 right hand
            public bool Above;            // Menu: straight above the button, vertical line
            public GameObject Root;
            public RectTransform Panel;
            public LineRenderer Line;
        }

        private sealed class Ring
        {
            public LineRenderer Line;
            public Material Mat;
            public Color Accent;
        }

        private readonly List<Lit> _lit = new();
        private readonly List<Label> _labels = new();
        private readonly List<Ring> _rings = new();
        private readonly List<GameObject> _anchors = new();
        private Material _lineMat;
        private Camera _cam;

        public bool AnyShown => _lit.Count > 0 || _labels.Count > 0 || _rings.Count > 0;

        private void Awake()
        {
            if (leftVisual == null) leftVisual = FindVisual("Left MetaQuest2 Model");
            if (leftVisual == null) leftVisual = FindVisual("Left Controller Visual");
            if (rightVisual == null) rightVisual = FindVisual("Right MetaQuest2 Model");
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
                if (l.Renderer != null) SetSlot(l.Renderer, l.Slot, l.Original);
                if (l.Glow != null) Destroy(l.Glow);
            }
            _lit.Clear();
            foreach (var a in _anchors)
                if (a != null) Destroy(a);
            _anchors.Clear();
            foreach (var lb in _labels)
                if (lb.Root != null) Destroy(lb.Root);
            _labels.Clear();
            foreach (var rg in _rings)
            {
                if (rg.Line != null) Destroy(rg.Line.gameObject);
                if (rg.Mat != null) Destroy(rg.Mat);
            }
            _rings.Clear();
        }

        // ------------------------------------------------------------------

        private void ShowOn(Transform visual, Part part, float side, string label)
        {
            if (visual == null)
            {
                Debug.LogWarning($"{Log} no controller visual for side {side}");
                return;
            }
            Transform anchor = null;
            foreach (var n in part == Part.Trigger ? TriggerNames : MenuNames)
                if ((anchor = FindDeep(visual, n)) != null) break;
            if (anchor == null)
            {
                Debug.LogWarning($"{Log} {part} not found under {visual.name}");
                return;
            }

            Color col = part == Part.Menu ? menuAccent : accent;
            Renderer r = anchor.GetComponent<Renderer>();
            int slot = 0;
            if (r == null)
            {
                // Meta model: the part is a bone; it glows through its submesh's slot, and
                // labels and rings go to the centre of that submesh, not to the bone pivot.
                var smr = visual.GetComponentInChildren<SkinnedMeshRenderer>(true);
                slot = part == Part.Trigger ? TriggerSlot : MenuSlot;
                if (smr == null || smr.sharedMesh == null || smr.sharedMesh.subMeshCount <= slot)
                {
                    Debug.LogWarning($"{Log} {visual.name}: no split mesh with a slot for {part}");
                    return;
                }
                r = smr;
                var existing = anchor.Find("Callout anchor " + anchor.name);
                if (existing != null) anchor = existing;
                else
                {
                    var centre = smr.transform.TransformPoint(smr.sharedMesh.GetSubMesh(slot).bounds.center);
                    var a = new GameObject("Callout anchor " + anchor.name);
                    a.transform.SetParent(anchor, false);
                    a.transform.position = centre;
                    _anchors.Add(a);
                    anchor = a.transform;
                }
            }

            if (_lit.Find(x => x.Renderer == r && x.Slot == slot) == null)
            {
                var original = r.sharedMaterials[slot];
                var glow = new Material(original) { name = original.name + " (callout)" };
                glow.EnableKeyword("_EMISSION");
                glow.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
                _lit.Add(new Lit { Renderer = r, Slot = slot, Original = original, Glow = glow, Accent = col });
                SetSlot(r, slot, glow);
                if (part == Part.Menu) _rings.Add(MakeRing(visual, anchor, menuRingRadius, col));
            }

            if (!string.IsNullOrEmpty(label) && _labels.Find(x => x.Anchor == anchor) == null)
                _labels.Add(MakeLabel(anchor, side, label, col, part == Part.Menu));
        }

        private static void SetSlot(Renderer r, int slot, Material m)
        {
            var mats = r.sharedMaterials;
            if (slot < mats.Length) { mats[slot] = m; r.sharedMaterials = mats; }
        }

        /// <summary>The point a label and its line go to: the button mesh's centre, or the anchor.</summary>
        private static Vector3 AnchorPoint(Transform anchor)
        {
            var r = anchor.GetComponent<Renderer>();
            return r != null ? r.bounds.center : anchor.position;
        }

        private void LateUpdate()
        {
            if (!AnyShown) return;

            // Pulse between a dim and a bright accent: always clearly lit, never off.
            float s = 0.5f + 0.5f * Mathf.Sin(Time.unscaledTime * pulseHz * 2f * Mathf.PI);
            foreach (var l in _lit)
            {
                if (l.Glow == null) continue;
                Color baseCol = Color.Lerp(l.Accent * 0.75f, Color.Lerp(l.Accent, Color.white, 0.35f), s);
                baseCol.a = 1f;
                Color emis = l.Accent * Mathf.Lerp(0.6f, 1.6f, s);
                if (l.Glow.HasProperty("_BaseColor")) l.Glow.SetColor("_BaseColor", baseCol);
                if (l.Glow.HasProperty("_Color")) l.Glow.SetColor("_Color", baseCol);
                if (l.Glow.HasProperty("_EmissionColor")) l.Glow.SetColor("_EmissionColor", emis);
            }
            if (_cam == null) _cam = Camera.main;
            // The ring breathes: a little larger and brighter at the peak.
            foreach (var rg in _rings)
            {
                if (rg.Line == null) continue;
                var rt = rg.Line.transform;
                rt.localScale = Vector3.one * Mathf.Lerp(1f, 1.25f, s);
                Color rc = Color.Lerp(rg.Accent, Color.Lerp(rg.Accent, Color.white, 0.4f), s);
                if (rg.Mat != null)
                {
                    if (rg.Mat.HasProperty("_BaseColor")) rg.Mat.SetColor("_BaseColor", rc);
                    if (rg.Mat.HasProperty("_Color")) rg.Mat.SetColor("_Color", rc);
                }
            }

            if (_cam == null) return;
            var ct = _cam.transform;
            foreach (var lb in _labels)
            {
                if (lb.Anchor == null || lb.Root == null) continue;
                // A controller that loses tracking is deactivated by XRI: hide its label with it.
                bool on = lb.Anchor.gameObject.activeInHierarchy;
                if (lb.Root.activeSelf != on) lb.Root.SetActive(on);
                if (!on) continue;
                Vector3 p = AnchorPoint(lb.Anchor);
                float halfW = lb.Panel.rect.width * 0.5f * lb.Root.transform.lossyScale.x;
                float halfH = lb.Panel.rect.height * 0.5f * lb.Root.transform.lossyScale.y;
                Vector3 pos, edge;
                if (lb.Above)
                {
                    // Menu: straight above the button in view; the line drops vertically onto
                    // it, so it cannot be read as pointing at a neighbouring button.
                    pos = p + ct.up * (menuLabelHeight + halfH);
                    edge = pos - ct.up * halfH;
                }
                else
                {
                    // Beside the hand, outwards and up in view space, so it never covers the controller.
                    pos = p + ct.right * (labelOffset.x * lb.Side) + ct.up * labelOffset.y;
                    edge = pos - ct.right * (halfW * lb.Side) - ct.up * halfH;   // panel's inner edge
                }
                lb.Root.transform.position = pos;
                lb.Root.transform.rotation = ct.rotation;   // parallel to the view: no roll, always readable
                lb.Line.SetPosition(0, edge);
                lb.Line.SetPosition(1, p);
            }
        }

        private Label MakeLabel(Transform anchor, float side, string text, Color col, bool above)
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
            bar.color = col;
            bar.raycastTarget = false;
            var brt = (RectTransform)barGo.transform;
            if (above)
            {
                // Menu: bar along the bottom edge, where the line leaves for the button.
                brt.anchorMin = new Vector2(0f, 0f); brt.anchorMax = new Vector2(1f, 0f);
                brt.pivot = new Vector2(0.5f, 0f);
                brt.sizeDelta = new Vector2(0f, 8f);
            }
            else
            {
                float x = side > 0 ? 0f : 1f;          // right hand: bar on the left edge; left hand: right edge
                brt.anchorMin = new Vector2(x, 0f); brt.anchorMax = new Vector2(x, 1f);
                brt.pivot = new Vector2(x, 0.5f);
                brt.sizeDelta = new Vector2(8f, 0f);
            }
            brt.anchoredPosition = Vector2.zero;

            if (_lineMat == null) _lineMat = NewUnlit("CalloutLine", accent);
            var lineMat = above ? NewUnlit("CalloutLine (menu)", col) : _lineMat;
            var lineGo = new GameObject("Line");
            lineGo.transform.SetParent(transform, false);
            lineGo.transform.SetParent(root.transform, true);
            var line = lineGo.AddComponent<LineRenderer>();
            line.useWorldSpace = true;
            line.positionCount = 2;
            line.widthMultiplier = 0.0018f;
            line.sharedMaterial = lineMat;
            line.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            line.receiveShadows = false;

            return new Label { Anchor = anchor, Side = side, Above = above, Root = root, Panel = panel, Line = line };
        }

        /// <summary>
        /// A ring around the Menu button so a small button reads from arm's length.
        /// Child of the button: it follows the hand and the press animation. It lies
        /// in the plane of the controller's face (the model's up axis is the face
        /// normal), 4 mm above it so the curved shell does not hide part of it.
        /// </summary>
        private Ring MakeRing(Transform visual, Transform button, float radius, Color col)
        {
            var go = new GameObject("Callout ring " + button.name);
            go.transform.SetParent(button, false);
            go.transform.position = AnchorPoint(button) + visual.up * 0.004f;
            go.transform.rotation = Quaternion.LookRotation(visual.up, visual.forward);
            var mat = NewUnlit("CalloutRing", col);
            var line = go.AddComponent<LineRenderer>();
            line.useWorldSpace = false;
            line.loop = true;
            const int n = 40;
            line.positionCount = n;
            // Local units divided by the parent's scale, so radius and width are in metres.
            float scale = Mathf.Max(1e-5f, go.transform.lossyScale.x);
            for (int i = 0; i < n; i++)
            {
                float a = i * 2f * Mathf.PI / n;
                line.SetPosition(i, new Vector3(Mathf.Cos(a), Mathf.Sin(a), 0f) * (radius / scale));
            }
            line.widthMultiplier = menuRingWidth / scale;
            // View-facing ribbon: the URP Unlit material is single-sided, and a ribbon lying
            // flat on the face was culled from the participant's side (checked in the Editor).
            line.alignment = LineAlignment.View;
            line.sharedMaterial = mat;
            line.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            line.receiveShadows = false;
            return new Ring { Line = line, Mat = mat, Accent = col };
        }

        private static Material NewUnlit(string name, Color col)
        {
            var sh = Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Sprites/Default");
            var m = new Material(sh) { name = name };
            if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", col);
            if (m.HasProperty("_Color")) m.SetColor("_Color", col);
            return m;
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

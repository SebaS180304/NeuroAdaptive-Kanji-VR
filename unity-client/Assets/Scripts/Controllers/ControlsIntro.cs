using System;
using System.Collections;
using NeuroAdaptiveVR.Core;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.XR.Interaction.Toolkit.UI;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Controls induction at the start of S2 (30 September, for participants
    /// with no VR experience). Teaches only what the session uses: the ray, the
    /// trigger to select, and the left Menu button to re-center the view.
    ///
    /// It has its own podium: a small stand about 1.1 m in front of the
    /// participant, with a screen tilted towards them. It wears the same materials
    /// as the Learning Board's stand. It is a different object from the Learning Board, which stays
    /// visible behind it, and it is removed when the induction ends. The screen
    /// sits ~18 degrees below eye level: reading it is a glance down, not a
    /// head turn.
    ///
    /// Everything is built at runtime from code, so the scene only holds this
    /// component. The podium is a teaching prop, outside the Environmental
    /// Layer and outside the ESL manipulation.
    ///
    /// Each step waits for the participant to DO the thing: "Next" is itself a
    /// point-and-trigger, the targets move, and the re-center step waits for the
    /// real Menu press (Skip after a few seconds, so a controller without that
    /// button cannot block the session).
    /// </summary>
    public class ControlsIntro : MonoBehaviour
    {
        private const string Log = "[ControlsIntro]";

        [SerializeField] private ViewRecenter viewRecenter;
        [Tooltip("The board canvas: its camera, layer and font are copied.")]
        [SerializeField] private Canvas boardCanvas;
        [Tooltip("The board stand's material, so the podium matches it.")]
        [SerializeField] private Material standMaterial;

        [Header("Podium (world, metres)")]
        [Tooltip("Centre of the screen.")]
        [SerializeField] private Vector3 screenCenter = new(0f, 0.98f, 1.02f);
        [SerializeField] private Vector2 screenSize = new(0.66f, 0.44f);
        [Tooltip("Degrees the screen leans back from vertical, facing the eye at 1.36 m.")]
        [SerializeField] private float screenTilt = 25f;

        [Header("Look")]
        [SerializeField] private Color bodyColor = new(0.06f, 0.07f, 0.09f, 1f);
        [SerializeField] private Color screenColor = new(0.07f, 0.10f, 0.15f, 1f);
        [SerializeField] private Color textColor = new(0.93f, 0.96f, 1f, 1f);
        [SerializeField] private Color buttonColor = new(0.15f, 0.50f, 0.95f, 1f);
        [SerializeField] private Color targetColor = new(0.20f, 0.80f, 0.40f, 1f);

        [SerializeField] private float skipAfterSeconds = 8f;

        public struct Result
        {
            public long DurationMs;
            public int TargetsHit;
            public bool Recentered;
            public bool RecenterSkipped;
        }

        private GameObject _root;
        private TMP_Text _title, _body;
        private RawImage _diagram;
        private GameObject _diagramBack;
        private Button _next, _target, _skip;
        private string _clicked;
        private bool _recentered;

        private void Awake()
        {
            if (viewRecenter == null) viewRecenter = FindAnyObjectByType<ViewRecenter>();
        }

        // ------------------------------------------------------------------

        public IEnumerator Run(Action<Result> done)
        {
            float t0 = Time.realtimeSinceStartup;
            var r = new Result();
            Build();
            _root.SetActive(true);
            if (viewRecenter != null) viewRecenter.OnRecentered += HandleRecentered;

            // 1 · The controllers
            Page("Welcome to VR",
                 "You hold one controller in each hand.\nPoint its ray at something and pull the <b>TRIGGER</b>\n" +
                 "(index finger) to select it.",
                 diagram: true);
            yield return WaitFor(_next, "Next");

            // 2 · Point and select: three targets in different places
            Page("Point and select", "Point at the green square and pull the trigger.", diagram: false);
            var spots = new[] { new Vector2(-210f, -40f), new Vector2(210f, 10f), new Vector2(0f, -120f) };
            for (int i = 0; i < spots.Length; i++)
            {
                ((RectTransform)_target.transform).anchoredPosition = spots[i];
                yield return WaitFor(_target, null);
                r.TargetsHit++;
                _body.text = i < spots.Length - 1 ? "Good! Now the next one." : "Great, that is all you need to answer.";
            }
            yield return new WaitForSecondsRealtime(0.8f);

            // 3 · Re-center with the left Menu button
            Page("Re-center the view",
                 "If the view ever feels tilted or off to one side,\npress the <b>MENU</b> button (≡) on your <b>LEFT</b> controller.\n" +
                 "Try it now.",
                 diagram: true);
            _next.gameObject.SetActive(false);
            _recentered = false;
            float waitFrom = Time.realtimeSinceStartup;
            _clicked = null;
            while (!_recentered && _clicked != "Skip")
            {
                if (!_skip.gameObject.activeSelf && Time.realtimeSinceStartup - waitFrom > skipAfterSeconds)
                    _skip.gameObject.SetActive(true);
                yield return null;
            }
            _skip.gameObject.SetActive(false);
            r.Recentered = _recentered;
            r.RecenterSkipped = !_recentered;
            _body.text = _recentered ? "Done! The view is centered again.\nYou are ready." : "No problem. You can do it at any time.";
            _diagram.gameObject.SetActive(false);
            _diagramBack.SetActive(false);
            yield return WaitFor(_next, "Continue");

            if (viewRecenter != null) viewRecenter.OnRecentered -= HandleRecentered;
            _root.SetActive(false);
            r.DurationMs = (long)((Time.realtimeSinceStartup - t0) * 1000f);
            Debug.Log($"{Log} done in {r.DurationMs} ms · targets {r.TargetsHit} · " +
                      (r.Recentered ? "re-centered" : "re-center skipped"));
            done?.Invoke(r);
        }

        private void HandleRecentered(string reason) => _recentered = true;

        private IEnumerator WaitFor(Button b, string label)
        {
            if (label != null) b.GetComponentInChildren<TMP_Text>().text = label;
            b.gameObject.SetActive(true);
            b.interactable = true;
            string id = b.name;
            _clicked = null;
            yield return new WaitUntil(() => _clicked == id);
            b.gameObject.SetActive(false);
        }

        private void Page(string title, string body, bool diagram)
        {
            _title.text = title;
            _body.text = body;
            bool showDiagram = diagram && _diagram.texture != null;
            _diagram.gameObject.SetActive(showDiagram);
            _diagramBack.SetActive(showDiagram);
            _next.gameObject.SetActive(false);
            _target.gameObject.SetActive(false);
            _skip.gameObject.SetActive(false);
        }

        // ------------------------------------------------------------------
        // Runtime construction
        // ------------------------------------------------------------------

        private void Build()
        {
            if (_root != null) return;
            if (boardCanvas == null)
            {
                var bc = GameObject.Find("BoardCanvas");
                if (bc != null) boardCanvas = bc.GetComponent<Canvas>();
            }
            int layer = boardCanvas != null ? boardCanvas.gameObject.layer : 0;

            _root = new GameObject("ControlsIntroPodium");
            _root.transform.SetParent(transform, false);
            _root.transform.position = Vector3.zero;


            // --- the podium body: base, column, and the tilted top that carries the screen
            var tilt = Quaternion.Euler(screenTilt, 0f, 0f);
            float half = screenSize.y * 0.5f;
            Vector3 topLow = screenCenter + tilt * new Vector3(0f, -half, 0f);   // lower (front) edge of the top
            float columnTop = topLow.y - 0.02f;
            float columnZ = screenCenter.z + 0.02f;

            Box("Base", new Vector3(0f, 0.02f, columnZ), new Vector3(0.52f, 0.04f, 0.40f), Quaternion.identity, bodyColor);
            Box("Column", new Vector3(0f, columnTop * 0.5f, columnZ), new Vector3(0.30f, columnTop, 0.22f), Quaternion.identity, bodyColor);
            var top = Box("Top", screenCenter + tilt * new Vector3(0f, 0f, 0.025f),
                          new Vector3(screenSize.x + 0.06f, screenSize.y + 0.06f, 0.04f), tilt, bodyColor);

            // --- the screen: a world-space canvas on the top, facing the participant
            var cgo = new GameObject("IntroCanvas", typeof(RectTransform), typeof(Canvas), typeof(CanvasScaler));
            cgo.layer = layer;
            cgo.transform.SetParent(_root.transform, false);
            var canvas = cgo.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.WorldSpace;
            if (boardCanvas != null) canvas.worldCamera = boardCanvas.worldCamera;
            cgo.GetComponent<CanvasScaler>().dynamicPixelsPerUnit = 10f;
            cgo.AddComponent<TrackedDeviceGraphicRaycaster>();
            var crt = (RectTransform)cgo.transform;
            crt.sizeDelta = new Vector2(screenSize.x * 1000f, screenSize.y * 1000f);
            crt.localScale = Vector3.one * 0.001f;
            crt.position = screenCenter + tilt * new Vector3(0f, 0f, -0.004f);
            crt.rotation = tilt;

            var bg = UiObj<Image>("Screen", crt);
            Stretch((RectTransform)bg.transform);
            // Same surface as the Learning Board.
            var boardBg = boardCanvas != null ? boardCanvas.transform.Find("Background") : null;
            var boardImg = boardBg != null ? boardBg.GetComponent<Image>() : null;
            bg.color = boardImg != null ? boardImg.color : screenColor;
            bg.raycastTarget = true;   // the screen stops the ray

            TMP_FontAsset font = null;
            var boardText = boardCanvas != null ? boardCanvas.GetComponentInChildren<TMP_Text>(true) : null;
            if (boardText != null) font = boardText.font;

            _title = Text("Title", crt, font, 40f, new Vector2(0f, 180f), new Vector2(620f, 56f));
            _title.fontStyle = FontStyles.Bold;
            _body = Text("Body", crt, font, 24f, new Vector2(0f, 150f), new Vector2(620f, 110f));
            _body.alignment = TextAlignmentOptions.Top;
            ((RectTransform)_body.transform).pivot = new Vector2(0.5f, 1f);

            var dback = UiObj<Image>("DiagramBack", crt);
            dback.color = new Color(0.03f, 0.05f, 0.08f, 1f);
            dback.raycastTarget = false;
            ((RectTransform)dback.transform).anchoredPosition = new Vector2(0f, -72f);
            ((RectTransform)dback.transform).sizeDelta = new Vector2(520f, 178f);
            _diagramBack = dback.gameObject;

            _diagram = UiObj<RawImage>("Diagram", crt);
            _diagram.texture = Resources.Load<Texture2D>("tutorial/controllers");
            _diagram.color = Color.white;
            _diagram.raycastTarget = false;
            var drt = (RectTransform)_diagram.transform;
            drt.anchoredPosition = new Vector2(0f, -72f);
            drt.sizeDelta = new Vector2(496f, 178f);

            _next = MakeButton("Next", crt, font, new Vector2(0f, -178f), new Vector2(190f, 56f), buttonColor, "Next");
            _target = MakeButton("Target", crt, font, Vector2.zero, new Vector2(84f, 84f), targetColor, "");
            _skip = MakeButton("Skip", crt, font, new Vector2(250f, -178f), new Vector2(110f, 46f),
                               new Color(0.40f, 0.42f, 0.46f, 1f), "Skip");

            _root.SetActive(false);
        }

        private GameObject Box(string name, Vector3 pos, Vector3 size, Quaternion rot, Color color)
        {
            var g = GameObject.CreatePrimitive(PrimitiveType.Cube);
            g.name = name;
            Destroy(g.GetComponent<Collider>());   // decoration never takes the ray
            g.transform.SetParent(_root.transform, false);
            g.transform.SetPositionAndRotation(pos, rot);
            g.transform.localScale = size;
            var mr = g.GetComponent<MeshRenderer>();
            if (standMaterial != null) mr.sharedMaterial = standMaterial;
            // No tint: the podium wears the same material as the board's stand
            // and the window frames, so it reads as furniture of the same room.
            return g;
        }

        private T UiObj<T>(string name, RectTransform parent) where T : Component
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(T));
            go.layer = parent.gameObject.layer;
            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);
            rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f);
            return go.GetComponent<T>();
        }

        private static void Stretch(RectTransform rt)
        {
            rt.anchorMin = Vector2.zero; rt.anchorMax = Vector2.one;
            rt.offsetMin = rt.offsetMax = Vector2.zero;
        }

        private TMP_Text Text(string name, RectTransform parent, TMP_FontAsset font, float size, Vector2 pos, Vector2 box)
        {
            var t = UiObj<TextMeshProUGUI>(name, parent);
            if (font != null) t.font = font;
            t.fontSize = size;
            t.color = textColor;
            t.alignment = TextAlignmentOptions.Center;
            t.textWrappingMode = TextWrappingModes.Normal;
            t.raycastTarget = false;
            var rt = (RectTransform)t.transform;
            rt.anchoredPosition = pos;
            rt.sizeDelta = box;
            return t;
        }

        private Button MakeButton(string name, RectTransform parent, TMP_FontAsset font, Vector2 pos, Vector2 size,
                                  Color color, string label)
        {
            var img = UiObj<Image>(name, parent);
            img.color = Color.white;
            var rt = (RectTransform)img.transform;
            rt.anchoredPosition = pos;
            rt.sizeDelta = size;
            var b = img.gameObject.AddComponent<Button>();
            b.targetGraphic = img;
            var cb = b.colors;
            cb.normalColor = color;
            cb.highlightedColor = Color.Lerp(color, Color.white, 0.35f);
            cb.pressedColor = Color.Lerp(color, Color.black, 0.2f);
            cb.selectedColor = color;
            b.colors = cb;
            string id = name;
            b.onClick.AddListener(() => _clicked = id);

            var t = Text("Label", rt, font, 28f, Vector2.zero, size);
            t.color = Color.white;
            t.text = label;
            t.textWrappingMode = TextWrappingModes.NoWrap;
            b.gameObject.SetActive(false);
            return b;
        }

    }
}

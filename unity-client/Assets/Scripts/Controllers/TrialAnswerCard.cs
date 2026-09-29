using System;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Una tarjeta de la Response Area (spec 3.1).
    ///
    /// Sabe dibujarse y avisar de que la eligieron. No sabe si su opcion es la
    /// correcta, no mide tiempo y no emite telemetria: eso vive en
    /// ResponseSystemController. La misma division que ITrialPresenter declara,
    /// aplicada un nivel mas abajo.
    ///
    /// Son cuatro, fijas. Spec 9.3 pone el numero de opciones fuera de LAL y
    /// ResponseSystemController aborta el trial si no recibe exactamente cuatro.
    /// Que la escena tenga cuatro tarjetas autoradas --y no una lista que crece--
    /// es esa misma regla expresada en la jerarquia.
    ///
    /// Card states (UI design v1.3, D1, 30 September): the card draws its own
    /// rest / ray-over / pressed look with a background colour and a 6-unit
    /// border (child "Frame"), and the Button's ColorTint is switched off
    /// (a 4 % highlight was invisible in the headset). Colour only: no scale,
    /// no depth, no glow, no sound, no vibration (design rules 7-9). The
    /// guided assembly keeps its own look (SetAssemblyLook): there the
    /// presenter paints the segments.
    /// </summary>
    [RequireComponent(typeof(Button))]
    public class TrialAnswerCard : MonoBehaviour,
        IPointerEnterHandler, IPointerExitHandler, IPointerDownHandler, IPointerUpHandler
    {
        [SerializeField] private Button button;
        [SerializeField] private TMP_Text label;

        [Header("Card states (UI design v1.3, D1)")]
        [SerializeField] private Color restColor = new(0.1647f, 0.1922f, 0.2588f, 1f);      // #2A3142
        [SerializeField] private Color restBorder = new(0.2275f, 0.2627f, 0.3412f, 1f);     // #3A4357
        [SerializeField] private Color hoverColor = new(0.2039f, 0.2510f, 0.3529f, 1f);     // #34405A
        [SerializeField] private Color hoverBorder = new(0.3490f, 0.6510f, 1f, 1f);         // #59A6FF
        [SerializeField] private float borderWidth = 6f;
        [SerializeField] private float hoverSeconds = 0.09f;
        [SerializeField] private float pressSeconds = 0.06f;

        [Header("Feedback (UI design v1.3, D2)")]
        [SerializeField] private Color correctColor = new(0.1216f, 0.2902f, 0.2039f, 1f);   // #1F4A34
        [SerializeField] private Color correctBorder = new(0.2627f, 0.8196f, 0.4784f, 1f);  // #43D17A
        [SerializeField] private Color wrongColor = new(0.2902f, 0.1647f, 0.1333f, 1f);     // #4A2A22
        [SerializeField] private Color wrongBorder = new(0.9412f, 0.5294f, 0.3529f, 1f);    // #F0875A
        [Tooltip("Border of the correct card when it was not chosen: solid green at this alpha.")]
        [SerializeField, Range(0f, 1f)] private float missedBorderAlpha = 0.7f;
        [SerializeField, Range(0f, 1f)] private float fadedAlpha = 0.4f;
        [SerializeField] private float feedbackFadeSeconds = 0.15f;
        [Tooltip("Pop of the chosen correct card: scale and depth towards the viewer (canvas units = mm).")]
        [SerializeField] private float popScale = 1.05f;
        [SerializeField] private float popDepth = 15f;

        /// <summary>How a card looks during immediate feedback (D2).</summary>
        public enum FeedbackMark { None, ChosenCorrect, ChosenWrong, CorrectMissed, Faded }

        private FeedbackMark _mark;
        private CanvasGroup _group;
        private float _popStart = -1f;
        private const float PopUp = 0.12f, PopHold = 0.25f, PopDown = 0.20f;   // 570 ms in all
        private Vector3 _restScale = Vector3.one;
        private float _restZ;

        private bool _assemblyLook;
        private bool _pointerOver, _pointerDown, _chosen;
        private Image _background;
        private RectTransform _frame;
        private Image[] _edges;
        private Color _bgFrom, _bgTo, _edgeFrom, _edgeTo;
        private float _fadeStart, _fadeSeconds;

        private string _optionId;

        /// <summary>El participante eligio esta tarjeta. Elegir es confirmar.</summary>
        public event Action<string> OnChosen;

        public string OptionId => _optionId;

        private void Reset()
        {
            button = GetComponent<Button>();
            label = GetComponentInChildren<TMP_Text>();
        }

        private void Awake()
        {
            if (button == null) button = GetComponent<Button>();
            if (label == null) label = GetComponentInChildren<TMP_Text>();

            if (label == null)
                Debug.LogError($"[TrialAnswerCard] '{name}' no tiene TMP_Text. " +
                               "La tarjeta no puede mostrar su opcion.");
            else
                // One line, always (25 September). The card grows to fit the
                // text instead -- see StudioTrialPresenter.FitCardsTo.
                label.textWrappingMode = TextWrappingModes.NoWrap;

            button.onClick.AddListener(Choose);

            // The authored colour is read before anything paints the card, so
            // SetTint(null) always restores it.
            _background = button.targetGraphic as Image;
            _restScale = transform.localScale;
            _restZ = transform.localPosition.z;
            if (button.targetGraphic != null) _homeColor = button.targetGraphic.color;
            button.transition = Selectable.Transition.None;
        }

        private void OnDestroy()
        {
            if (button != null) button.onClick.RemoveListener(Choose);
        }

        public void Bind(string optionId, string displayText, float fontSize)
        {
            _optionId = optionId;
            if (label != null)
            {
                label.text = displayText;
                label.fontSize = fontSize;
            }
            gameObject.SetActive(true);
            button.interactable = true;
            _chosen = false;
            _pointerDown = false;
            _assemblyLook = false;
            ClearFeedback();
            SetTint(null);   // a card never carries an assembly highlight into a trial
            SetOutline(false);
            SetImage(null);  // nor a segment image
            Repaint(0f);
        }

        /// <summary>
        /// Marks the card for immediate feedback: colours fade in over 150 ms,
        /// the faded cards drop to 40 % opacity, and the chosen correct card
        /// pops (1.00 -> 1.05 and 15 mm towards the viewer in 120 ms, 250 ms
        /// hold, back in 200 ms). Everything returns to rest on the next Bind.
        /// </summary>
        public void ShowFeedback(FeedbackMark mark)
        {
            _mark = mark;
            if (mark == FeedbackMark.Faded)
            {
                if (_group == null) _group = GetComponent<CanvasGroup>();
                if (_group == null) _group = gameObject.AddComponent<CanvasGroup>();
                _group.alpha = fadedAlpha;
            }
            if (mark == FeedbackMark.ChosenCorrect) _popStart = Time.unscaledTime;
            Repaint(feedbackFadeSeconds);
        }

        private void ClearFeedback()
        {
            _mark = FeedbackMark.None;
            _popStart = -1f;
            if (_group != null) _group.alpha = 1f;
            transform.localScale = _restScale;
            var p = transform.localPosition;
            transform.localPosition = new Vector3(p.x, p.y, _restZ);
        }

        /// <summary>
        /// The guided assembly paints its segments itself (tints and the white
        /// outline): the card then hides its frame and leaves the colour alone.
        /// Bind turns it back off.
        /// </summary>
        public void SetAssemblyLook(bool on)
        {
            _assemblyLook = on;
            Repaint(0f);
        }

        // ------------------------------------------------------------------
        // Ray over / pressed (D1)
        // ------------------------------------------------------------------

        public void OnPointerEnter(PointerEventData e) { _pointerOver = true; Repaint(hoverSeconds); }
        public void OnPointerExit(PointerEventData e) { _pointerOver = false; _pointerDown = false; Repaint(hoverSeconds); }
        public void OnPointerDown(PointerEventData e) { _pointerDown = true; Repaint(pressSeconds); }
        public void OnPointerUp(PointerEventData e) { _pointerDown = false; Repaint(pressSeconds); }

        private void OnDisable()
        {
            // A card hidden under the ray never gets its exit event.
            _pointerOver = false;
            _pointerDown = false;
        }

        private bool Interactable => button != null && button.interactable;

        /// <summary>Recomputes the target look and fades to it over `seconds` (0 = at once).</summary>
        private void Repaint(float seconds)
        {
            if (_assemblyLook)
            {
                if (_frame != null) _frame.gameObject.SetActive(false);
                _fadeSeconds = 0f;
                return;
            }

            bool lit = _chosen || (Interactable && (_pointerOver || _pointerDown));
            Color bg = lit ? hoverColor : restColor;
            Color edge = lit ? hoverBorder : restBorder;
            switch (_mark)
            {
                case FeedbackMark.ChosenCorrect: bg = correctColor; edge = correctBorder; break;
                case FeedbackMark.ChosenWrong: bg = wrongColor; edge = wrongBorder; break;
                case FeedbackMark.CorrectMissed:
                    bg = restColor;
                    edge = correctBorder;
                    edge.a = missedBorderAlpha;
                    break;
                case FeedbackMark.Faded: bg = restColor; edge = restBorder; break;
            }

            EnsureFrame();
            _frame.gameObject.SetActive(true);
            _bgFrom = _background != null ? _background.color : bg;
            _edgeFrom = _edges[0].color;
            _bgTo = bg;
            _edgeTo = edge;
            _fadeStart = Time.unscaledTime;
            _fadeSeconds = seconds;
            if (seconds <= 0f) ApplyFade(1f);
        }

        private void Update()
        {
            if (_popStart >= 0f) AnimatePop();
            if (_fadeSeconds <= 0f) return;
            float t = Mathf.Clamp01((Time.unscaledTime - _fadeStart) / _fadeSeconds);
            ApplyFade(1f - (1f - t) * (1f - t));   // ease-out
            if (t >= 1f) _fadeSeconds = 0f;
        }

        private void AnimatePop()
        {
            float t = Time.unscaledTime - _popStart;
            float k;
            if (t < PopUp) { float u = t / PopUp; k = 1f - (1f - u) * (1f - u); }            // ease-out
            else if (t < PopUp + PopHold) k = 1f;
            else if (t < PopUp + PopHold + PopDown)
            {
                float u = (t - PopUp - PopHold) / PopDown;
                k = 1f - (u < 0.5f ? 2f * u * u : 1f - Mathf.Pow(-2f * u + 2f, 2f) / 2f);  // ease-in-out
            }
            else { k = 0f; _popStart = -1f; }

            transform.localScale = _restScale * Mathf.Lerp(1f, popScale, k);
            var p = transform.localPosition;
            transform.localPosition = new Vector3(p.x, p.y, _restZ - popDepth * k);
        }

        private void ApplyFade(float k)
        {
            if (_background != null) _background.color = Color.Lerp(_bgFrom, _bgTo, k);
            if (_edges != null)
                foreach (var e in _edges) e.color = Color.Lerp(_edgeFrom, _edgeTo, k);
        }

        /// <summary>
        /// Four thin Images along the card's edges, inside it, drawn over the
        /// background and under the label. Separate from the assembly's white
        /// Outline, so both can exist.
        /// </summary>
        private void EnsureFrame()
        {
            if (_frame != null) return;
            var go = new GameObject("Frame", typeof(RectTransform));
            go.layer = gameObject.layer;
            _frame = (RectTransform)go.transform;
            _frame.SetParent(transform, false);
            _frame.anchorMin = Vector2.zero;
            _frame.anchorMax = Vector2.one;
            _frame.offsetMin = _frame.offsetMax = Vector2.zero;
            _frame.SetAsFirstSibling();

            _edges = new Image[4];
            // left, right, bottom, top
            var mins = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(0, 0), new Vector2(0, 1) };
            var maxs = new[] { new Vector2(0, 1), new Vector2(1, 1), new Vector2(1, 0), new Vector2(1, 1) };
            var pivots = new[] { new Vector2(0, 0.5f), new Vector2(1, 0.5f), new Vector2(0.5f, 0), new Vector2(0.5f, 1) };
            for (int i = 0; i < 4; i++)
            {
                var e = new GameObject("Edge", typeof(RectTransform), typeof(Image));
                e.layer = gameObject.layer;
                var rt = (RectTransform)e.transform;
                rt.SetParent(_frame, false);
                rt.anchorMin = mins[i];
                rt.anchorMax = maxs[i];
                rt.pivot = pivots[i];
                rt.anchoredPosition = Vector2.zero;
                rt.sizeDelta = i < 2 ? new Vector2(borderWidth, 0f) : new Vector2(0f, borderWidth);
                var img = e.GetComponent<Image>();
                img.raycastTarget = false;
                img.color = restBorder;
                _edges[i] = img;
            }
        }

        private RawImage _image;

        /// <summary>
        /// A picture on the card instead of text: a kanji segment during the
        /// guided assembly (30 September). Null removes it. Square, centred,
        /// as tall as the card allows; not a raycast target, so the card's own
        /// button still takes the ray.
        /// </summary>
        public void SetImage(Texture texture)
        {
            if (texture == null)
            {
                if (_image != null) _image.gameObject.SetActive(false);
                return;
            }
            if (_image == null)
            {
                var go = new GameObject("SegmentImage", typeof(RectTransform), typeof(RawImage));
                go.layer = gameObject.layer;
                var rt = (RectTransform)go.transform;
                rt.SetParent(transform, false);
                rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f);
                _image = go.GetComponent<RawImage>();
                _image.raycastTarget = false;
            }
            float side = ((RectTransform)transform).rect.height * 0.92f;
            ((RectTransform)_image.transform).sizeDelta = new Vector2(side, side);
            _image.texture = texture;
            _image.color = Color.white;
            _image.gameObject.SetActive(true);
            _image.transform.SetAsLastSibling();
        }

        private Outline _outline;

        /// <summary>White border marking the segment in hand during the assembly. Trials never show it.</summary>
        public void SetOutline(bool on)
        {
            if (_outline == null)
            {
                if (!on) return;
                var g = button != null ? button.targetGraphic : null;
                if (g == null) return;
                _outline = g.gameObject.AddComponent<Outline>();
                _outline.effectColor = Color.white;
                _outline.effectDistance = new Vector2(8f, -8f);
            }
            _outline.enabled = on;
        }

        private Color? _homeColor;

        /// <summary>
        /// Colours the card (assembly: selected segment, hint). Null restores
        /// the authored colour. Trials never tint: Bind resets it.
        /// </summary>
        public void SetTint(Color? color)
        {
            var g = button != null ? button.targetGraphic : null;
            if (g == null) return;
            if (_homeColor == null) _homeColor = g.color;
            g.color = color ?? _homeColor.Value;
            _fadeSeconds = 0f;   // a running hover fade must not overwrite the tint
        }

        /// <summary>Width the label needs to show this text on one line at this size.</summary>
        public float PreferredTextWidth(string text, float fontSize)
        {
            if (label == null || string.IsNullOrEmpty(text)) return 0f;
            float was = label.fontSize;
            label.fontSize = fontSize;
            float w = label.GetPreferredValues(text, float.PositiveInfinity, float.PositiveInfinity).x;
            label.fontSize = was;
            return w;
        }

        public float Width => ((RectTransform)transform).rect.width;

        /// <summary>
        /// Sets the card width. The label keeps the inset it was authored with
        /// (10 px a side in the scene), so text and card grow together.
        /// </summary>
        public void SetWidth(float width)
        {
            var card = (RectTransform)transform;
            float inset = 0f;
            if (label != null) inset = card.rect.width - ((RectTransform)label.transform).rect.width;
            card.SetSizeWithCurrentAnchors(RectTransform.Axis.Horizontal, width);
            if (label != null)
                ((RectTransform)label.transform).SetSizeWithCurrentAnchors(RectTransform.Axis.Horizontal, width - inset);
        }

        public void SetInteractable(bool value)
        {
            if (button != null) button.interactable = value;
            Repaint(hoverSeconds);
        }

        public void Hide()
        {
            _optionId = null;
            _chosen = false;
            ClearFeedback();
            if (label != null) label.text = string.Empty;
            gameObject.SetActive(false);
        }

        private void Choose()
        {
            if (string.IsNullOrEmpty(_optionId)) return;

            // Se desactiva en el acto: una segunda pulsacion sobre la misma
            // tarjeta no debe llegar al sistema de respuesta. La autoridad sobre
            // si el trial sigue abierto es de ResponseSystemController; esto solo
            // evita el doble evento en el camino.
            button.interactable = false;
            // Stays in the pressed look until the next Bind: with no immediate
            // feedback this is the only sign of which card was chosen.
            _chosen = true;
            Repaint(pressSeconds);
            OnChosen?.Invoke(_optionId);
        }
    }
}

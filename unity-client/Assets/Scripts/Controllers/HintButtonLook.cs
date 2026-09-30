using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Look of the board's Hint button (UI design v1.3).
    ///
    /// D1: under the ray it gets a 6-unit accent border and a slightly lighter
    /// background; colour only, no scale, glow, sound or vibration. The Button's
    /// ColorTint is switched off.
    ///
    /// P3: at rest it is an amber chip with round ends (#E3B341) that reads
    /// "? Hint" in #1C2230, instead of a grey "?" with no button shape.
    /// </summary>
    [RequireComponent(typeof(Button))]
    public class HintButtonLook : MonoBehaviour,
        IPointerEnterHandler, IPointerExitHandler, IPointerDownHandler, IPointerUpHandler
    {
        [Header("Chip (P3)")]
        [SerializeField] private bool chip = true;
        [SerializeField] private Color restColor = new(0.8902f, 0.7020f, 0.2549f, 1f);    // #E3B341
        [SerializeField] private string labelText = "? Hint";
        [SerializeField] private Color labelColor = new(0.1098f, 0.1333f, 0.1882f, 1f);   // #1C2230

        [Header("Ray over (D1)")]
        [SerializeField] private Color hoverBorder = new(0.3490f, 0.6510f, 1f, 1f);       // #59A6FF
        [Tooltip("How much the background lightens under the ray.")]
        [SerializeField, Range(0f, 0.5f)] private float hoverLighten = 0.12f;
        [SerializeField] private float borderWidth = 6f;
        [SerializeField] private float hoverSeconds = 0.09f;

        private Button _button;
        private Image _background;
        private Color _rest;
        private Image[] _strokes;
        private bool _over, _down;
        private Color _bgFrom, _bgTo, _edgeFrom, _edgeTo;
        private float _t0, _dur;

        private void Awake()
        {
            _button = GetComponent<Button>();
            _button.transition = Selectable.Transition.None;
            _background = _button.targetGraphic as Image;

            if (chip && _background != null)
            {
                _background.color = restColor;
                float r = ((RectTransform)transform).rect.height * 0.5f;
                _background.sprite = PillSprite.Get(r);
                _background.type = Image.Type.Sliced;
                _background.pixelsPerUnitMultiplier = 1f;
                var label = GetComponentInChildren<TMP_Text>(true);
                if (label != null)
                {
                    label.text = labelText;
                    label.color = labelColor;
                    label.fontStyle = FontStyles.Bold;
                }
            }
            _rest = _background != null ? _background.color : Color.gray;
            BuildFrame();
            Paint(0f);
        }

        private void OnDisable()
        {
            _over = _down = false;
            Paint(0f);
        }

        public void OnPointerEnter(PointerEventData e) { _over = true; Paint(hoverSeconds); }
        public void OnPointerExit(PointerEventData e) { _over = _down = false; Paint(hoverSeconds); }
        public void OnPointerDown(PointerEventData e) { _down = true; Paint(hoverSeconds); }
        public void OnPointerUp(PointerEventData e) { _down = false; Paint(hoverSeconds); }

        private void Paint(float seconds)
        {
            if (_strokes == null) return;
            bool lit = _button != null && _button.interactable && (_over || _down);
            Color restEdge = hoverBorder; restEdge.a = 0f;   // no border at rest
            _bgFrom = _background != null ? _background.color : _rest;
            _edgeFrom = _strokes[0].color;
            _bgTo = lit ? Color.Lerp(_rest, Color.white, hoverLighten) : _rest;
            _edgeTo = lit ? hoverBorder : restEdge;
            _t0 = Time.unscaledTime;
            _dur = seconds;
            if (seconds <= 0f) Apply(1f);
        }

        private void Update()
        {
            if (_dur <= 0f) return;
            float t = Mathf.Clamp01((Time.unscaledTime - _t0) / _dur);
            Apply(1f - (1f - t) * (1f - t));
            if (t >= 1f) _dur = 0f;
        }

        private void Apply(float k)
        {
            if (_background != null) _background.color = Color.Lerp(_bgFrom, _bgTo, k);
            foreach (var e in _strokes) e.color = Color.Lerp(_edgeFrom, _edgeTo, k);
        }

        /// <summary>
        /// The hover border: one pill-shaped outline for the chip, or four thin
        /// edges for a rectangular button. Drawn over the background, under the label.
        /// </summary>
        private void BuildFrame()
        {
            var go = new GameObject("Frame", typeof(RectTransform));
            go.layer = gameObject.layer;
            var frame = (RectTransform)go.transform;
            frame.SetParent(transform, false);
            frame.anchorMin = Vector2.zero;
            frame.anchorMax = Vector2.one;
            frame.offsetMin = frame.offsetMax = Vector2.zero;
            frame.SetAsFirstSibling();

            if (chip)
            {
                var img = go.AddComponent<Image>();
                img.sprite = PillSprite.Get(((RectTransform)transform).rect.height * 0.5f, borderWidth);
                img.type = Image.Type.Sliced;
                img.raycastTarget = false;
                img.color = new Color(0, 0, 0, 0);
                _strokes = new[] { img };
                return;
            }

            _strokes = new Image[4];
            var mins = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(0, 0), new Vector2(0, 1) };
            var maxs = new[] { new Vector2(0, 1), new Vector2(1, 1), new Vector2(1, 0), new Vector2(1, 1) };
            var pivots = new[] { new Vector2(0, 0.5f), new Vector2(1, 0.5f), new Vector2(0.5f, 0), new Vector2(0.5f, 1) };
            for (int i = 0; i < 4; i++)
            {
                var e = new GameObject("Edge", typeof(RectTransform), typeof(Image));
                e.layer = gameObject.layer;
                var rt = (RectTransform)e.transform;
                rt.SetParent(frame, false);
                rt.anchorMin = mins[i];
                rt.anchorMax = maxs[i];
                rt.pivot = pivots[i];
                rt.anchoredPosition = Vector2.zero;
                rt.sizeDelta = i < 2 ? new Vector2(borderWidth, 0f) : new Vector2(0f, borderWidth);
                var img = e.GetComponent<Image>();
                img.raycastTarget = false;
                img.color = new Color(0, 0, 0, 0);
                _strokes[i] = img;
            }
        }
    }
}

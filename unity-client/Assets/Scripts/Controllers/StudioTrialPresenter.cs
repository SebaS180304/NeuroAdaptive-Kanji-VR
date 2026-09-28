using System;
using System.Collections.Generic;
using NeuroAdaptiveVR.Data;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Implementacion de ITrialPresenter con la geometria real de la escena
    /// JapaneseLearningStudio: Central Learning Board y Response Area (spec 3.1).
    ///
    /// Es la SEGUNDA implementacion de la misma interfaz. DebugTrialPresenter se
    /// conserva a proposito: es el arnes que permite correr el ciclo sin escena
    /// y es con el que se levantaron los datos que verifica verify_trials.sql.
    /// Dos presentadores contra una interfaz, y ResponseSystemController sin
    /// enterarse de cual esta conectado -- que es justamente lo que hace
    /// comparables los tiempos de S6 y S7 (spec 5.4).
    ///
    /// Este componente dibuja y avisa. No valida, no cronometra y no emite
    /// telemetria.
    /// </summary>
    public class StudioTrialPresenter : MonoBehaviour, ITrialPresenter
    {
        [Header("Central Learning Board")]
        [SerializeField] private TMP_Text promptLabel;
        [SerializeField] private TMP_Text feedbackLabel;
        [SerializeField] private TMP_Text cueLabel;

        [Tooltip("Stage title strip at the top of the board ('Step 3 of 9 · Learn'). " +
                 "NOT cleared by Clear(): it belongs to the stage, not to the trial.")]
        [SerializeField] private TMP_Text stageTitleLabel;

        [Header("Response Area")]
        [Tooltip("Exactamente cuatro. Spec 9.3 fija el numero de opciones y LAL no puede cambiarlo.")]
        [SerializeField] private TrialAnswerCard[] cards = new TrialAnswerCard[4];

        [Header("Ayuda")]
        [SerializeField] private Button hintButton;

        [Header("Tipografia")]
        [Tooltip("Tamano para ideogramas: un kanji suelto se lee por su forma, no por su texto.")]
        [SerializeField] private float promptIdeographicSize = 420f;
        [SerializeField] private float promptKanaSize = 200f;
        [SerializeField] private float promptLatinSize = 150f;
        [SerializeField] private float optionIdeographicSize = 210f;
        [SerializeField] private float optionKanaSize = 120f;
        [SerializeField] private float optionLatinSize = 95f;

        [Tooltip("Board text size for session messages (welcome, baseline, summary). " +
                 "Sentences, not single glyphs, so far smaller than a prompt.")]
        [SerializeField] private float messageSize = 70f;

        [Tooltip("Size of the placeholder text of S5 derivation stages 1-3.")]
        [SerializeField] private float derivationSize = 160f;

        [Header("Card layout (25 September)")]
        [Tooltip("Space between the widest text and the label edge, per side. The card grows to " +
                 "fit its text on ONE line instead of shrinking the font.")]
        [SerializeField] private float cardTextPadding = 15f;
        [Tooltip("Horizontal gap between two cards of the row (40 in the authored scene).")]
        [SerializeField] private float cardGap = 40f;

        [Header("Guided assembly slots (spec 5.3)")]
        [SerializeField] private float slotSize = 240f;
        [SerializeField] private float slotGap = 40f;
        [Tooltip("Vertical position of the slot row on the board: where the glyph sits.")]
        [SerializeField] private float slotRowY = 90f;
        [SerializeField] private float slotLabelSize = 60f;
        [SerializeField] private Color slotEmptyColor = new Color(1f, 1f, 1f, 0.12f);
        [SerializeField] private Color slotNextColor = new Color(0.35f, 0.65f, 1f, 0.55f);
        [SerializeField] private Color slotFilledColor = new Color(0.30f, 0.72f, 0.40f, 0.55f);
        [SerializeField] private Color slotWrongColor = new Color(0.85f, 0.35f, 0.25f, 0.70f);
        [SerializeField] private Color segmentSelectedColor = new Color(0.35f, 0.65f, 1f, 1f);
        [SerializeField] private Color segmentHintColor = new Color(1f, 0.82f, 0.30f, 1f);

        public event Action<string> OnOptionChosen;
        public event Action OnHintRequested;

        /// <summary>A board slot was selected (guided assembly). Only the highlighted slot is selectable.</summary>
        public event Action<int> OnSlotChosen;

        // Where each card lives in the scene. ShowSingleChoice moves one card
        // to the centre; everything that presents a trial puts them back, so a
        // centred Start card can never leak into a trial layout.
        private Vector2[] _cardHome;

        // One width for every card of the row (FitCardsTo). Equal widths are
        // deliberate: a wider card is an easier target (Fitts' law), and the
        // correct answer must never be the easier one to hit.
        private float _cardWidth;

        // Label sizes as authored in the scene. ShowExposure enlarges the
        // reading line; Clear() puts every size back so no trial inherits it.
        private float _feedbackHomeSize, _cueHomeSize;
        private Color _feedbackHomeColor;

        // ------------------------------------------------------------------
        // Ciclo de vida
        // ------------------------------------------------------------------

        private void Awake()
        {
            if (feedbackLabel != null) { _feedbackHomeSize = feedbackLabel.fontSize; _feedbackHomeColor = feedbackLabel.color; }
            if (cueLabel != null) _cueHomeSize = cueLabel.fontSize;

            if (cards != null)
            {
                _cardHome = new Vector2[cards.Length];
                for (int i = 0; i < cards.Length; i++)
                    if (cards[i] != null)
                    {
                        _cardHome[i] = ((RectTransform)cards[i].transform).anchoredPosition;
                        _cardWidth = Mathf.Max(_cardWidth, cards[i].Width);
                    }
            }

            if (cards == null || cards.Length != 4)
            {
                Debug.LogError($"[StudioTrialPresenter] Hay {cards?.Length ?? 0} tarjetas cableadas y " +
                               "deben ser exactamente 4 (spec 9.3). ResponseSystemController aborta " +
                               "el trial si recibe otro numero de opciones, asi que esto se veria como " +
                               "un trial que nunca abre.");
            }
            else
            {
                foreach (var c in cards)
                {
                    if (c == null)
                    {
                        Debug.LogError("[StudioTrialPresenter] Hay una tarjeta sin asignar en el array.");
                        continue;
                    }
                    c.OnChosen += HandleCardChosen;
                }
            }

            if (hintButton != null) hintButton.onClick.AddListener(HandleHintClicked);

            Clear();
        }

        private void OnDestroy()
        {
            if (cards != null)
                foreach (var c in cards)
                    if (c != null) c.OnChosen -= HandleCardChosen;

            if (hintButton != null) hintButton.onClick.RemoveListener(HandleHintClicked);
        }

        private void HandleCardChosen(string optionId) => OnOptionChosen?.Invoke(optionId);
        private void HandleSlotClicked(int index) => OnSlotChosen?.Invoke(index);
        private void HandleHintClicked() => OnHintRequested?.Invoke();

        // ------------------------------------------------------------------
        // ITrialPresenter
        // ------------------------------------------------------------------

        public void Present(RetrievalTrialType trialType, string promptText,
                            IReadOnlyList<TrialOption> options)
        {
            if (feedbackLabel != null) feedbackLabel.text = string.Empty;
            if (cueLabel != null) cueLabel.text = string.Empty;
            RestoreLabelStyle();   // an S5 exposure may have enlarged the cue line
            HideAssemblySlots();

            if (promptLabel != null)
            {
                promptLabel.text = promptText;
                promptLabel.fontSize = PromptSizeFor(promptText);
            }

            RestoreCardPositions();

            // Safety net: FitCardsTo already sized the row for every text the
            // contract can produce. Growing here would only happen with content
            // that bypassed it, and would change the layout mid-block -- so it
            // is loud.
            float need = 0f;
            for (int i = 0; i < options.Count && cards != null && i < cards.Length; i++)
                if (cards[i] != null)
                    need = Mathf.Max(need, CardWidthFor(cards[i], options[i].DisplayText));
            if (need > _cardWidth + 0.5f)
            {
                Debug.LogWarning($"[StudioTrialPresenter] An option needs a {need:0}-wide card and the row " +
                                 $"is {_cardWidth:0}. Growing it now: the card layout changed in the middle " +
                                 "of a block. FitCardsTo was not given this text.");
                LayoutRow(need);
            }

            int n = Mathf.Min(options.Count, cards?.Length ?? 0);
            for (int i = 0; i < n; i++)
                cards[i].Bind(options[i].OptionId, options[i].DisplayText,
                              OptionSizeFor(options[i].DisplayText));

            // Si llegaran menos de cuatro opciones el sistema de respuesta ya
            // habria abortado; ocultar el resto evita dejar una tarjeta del trial
            // anterior visible si eso cambiara alguna vez.
            for (int i = n; i < (cards?.Length ?? 0); i++)
                cards[i].Hide();
        }

        public void ShowFeedback(bool isCorrect, string correctText)
        {
            if (cards != null)
                foreach (var c in cards)
                    if (c != null) c.SetInteractable(false);

            if (feedbackLabel == null) return;

            feedbackLabel.text = isCorrect ? "OK" : correctText;
            feedbackLabel.color = isCorrect ? new Color(0.30f, 0.72f, 0.40f)
                                            : new Color(0.85f, 0.45f, 0.25f);
        }

        public void SetHintAvailable(bool available)
        {
            if (hintButton == null) return;
            hintButton.gameObject.SetActive(available);
            hintButton.interactable = available;
        }

        public void ShowCue(LalCue cue)
        {
            if (cueLabel == null) return;

            // Fase 2 nombra el cue en texto. Los cues visuales reales --asociacion,
            // transformacion-- son assets de contenido y llegan con S5. Nombrarlos
            // ahora no es decorativo: hace visible en el visor, y comprobable en la
            // grabacion, que LAL concedio exactamente lo que la matriz 9.1 dice, sin
            // tener que leer la base.
            cueLabel.text = cue == LalCue.None ? string.Empty : cue.ToString();
        }

        public void Clear()
        {
            if (promptLabel != null) promptLabel.text = string.Empty;
            if (feedbackLabel != null) feedbackLabel.text = string.Empty;
            if (cueLabel != null) cueLabel.text = string.Empty;
            RestoreLabelStyle();
            HideAssemblySlots();
            if (hintButton != null) hintButton.gameObject.SetActive(false);

            if (cards != null)
                foreach (var c in cards)
                    if (c != null) c.Hide();
        }

        // ------------------------------------------------------------------
        // Session messages (outside any trial)
        // ------------------------------------------------------------------
        //
        // Not part of ITrialPresenter: they are not trial presentation, and the
        // response system must not know they exist. They live HERE and not in
        // a second board component because this presenter is the one owner of
        // the board (decision D1, 24 September). Two components writing
        // promptLabel would make the winner depend on call order.

        /// <summary>Clears the board and shows a sentence on it.</summary>
        public void ShowMessage(string text)
        {
            Clear();
            if (promptLabel == null) return;
            promptLabel.text = text;
            promptLabel.fontSize = messageSize;
        }

        /// <summary>
        /// Keeps the current message and offers ONE card (e.g. "Start"). The
        /// choice arrives through OnOptionChosen like any other; the response
        /// system ignores it because no trial is open.
        /// </summary>
        public void ShowSingleChoice(string optionId, string label)
        {
            if (cards == null || cards.Length == 0 || cards[0] == null) return;
            cards[0].Bind(optionId, label, OptionSizeFor(label));
            for (int i = 1; i < cards.Length; i++)
                if (cards[i] != null) cards[i].Hide();

            // Centred on the Response Area, same height as its home. Card 1
            // sits at the far left of a four-card row; a lone button there
            // reads as "one of several", and on 24 September it read as
            // misplaced. Present() restores it before the first trial.
            if (_cardHome != null)
                ((RectTransform)cards[0].transform).anchoredPosition = new Vector2(0f, _cardHome[0].y);

            // A lone button has no row to match: it only has to fit its label.
            // Present() puts the row width back.
            cards[0].SetWidth(Mathf.Max(_cardWidth, CardWidthFor(cards[0], label)));
        }

        /// <summary>
        /// Sizes every card of the row ONCE, from the widest text any card can
        /// show, so each option fits on one line at its normal font size. Called
        /// by SessionFlowRunner at session start with every option text of the
        /// whole contract: the layout is then the same for every trial, every
        /// block and every kanji set. Never shrinks below the authored width.
        /// </summary>
        public void FitCardsTo(IEnumerable<string> texts)
        {
            if (cards == null || cards.Length == 0 || cards[0] == null) return;
            float need = _cardWidth;
            string widest = null;
            foreach (var t in texts)
            {
                float w = CardWidthFor(cards[0], t);
                if (w > need) { need = w; widest = t; }
            }
            LayoutRow(need);

            float row = cards.Length * _cardWidth + (cards.Length - 1) * cardGap;
            Debug.Log($"[StudioTrialPresenter] Answer cards {_cardWidth:0} wide, row {row:0}" +
                      (widest != null ? $" (widest text: '{widest}')" : " (authored width, every text fits)"));
        }

        private float CardWidthFor(TrialAnswerCard card, string text)
        {
            float textW = card.PreferredTextWidth(text, OptionSizeFor(text));
            if (textW <= 0f) return 0f;
            var cardRt = (RectTransform)card.transform;
            // What the card adds around its label (the authored inset), plus padding.
            float inset = 0f;
            var lbl = card.GetComponentInChildren<TMP_Text>(true);
            if (lbl != null) inset = cardRt.rect.width - ((RectTransform)lbl.transform).rect.width;
            return Mathf.Ceil(textW + 2f * cardTextPadding + inset);
        }

        /// <summary>
        /// Gives every card the same width and re-spaces the row around the
        /// centre of the Response Area, keeping the authored gap and height.
        /// Widens the canvas rect if the row outgrows it, so nothing sits
        /// outside its own canvas.
        /// </summary>
        private void LayoutRow(float width)
        {
            _cardWidth = width;
            int n = cards.Length;
            for (int i = 0; i < n; i++)
            {
                if (cards[i] == null) continue;
                cards[i].SetWidth(width);
                float x = (i - (n - 1) * 0.5f) * (width + cardGap);
                if (_cardHome != null) _cardHome[i] = new Vector2(x, _cardHome[i].y);
            }
            RestoreCardPositions();

            if (cards[0] != null && cards[0].transform.parent is RectTransform area)
            {
                float row = n * width + (n - 1) * cardGap;
                if (area.rect.width < row)
                    area.SetSizeWithCurrentAnchors(RectTransform.Axis.Horizontal, row);
            }
        }

        /// <summary>
        /// S5 exposure, stage 4 onwards (spec 7.6): the glyph, then its meaning,
        /// then its target reading, each added to what is already there so the
        /// three end up on the board together. Null leaves a line empty.
        ///
        /// Uses the same three labels a trial uses, with its own sizes: the
        /// glyph at prompt size, the meaning where feedback goes, the reading
        /// where the cue goes but large -- it is the thing being taught, not a
        /// hint. Clear() restores the trial sizes.
        /// </summary>
        public void ShowExposure(string glyph, string meaning = null, string reading = null)
        {
            if (cards != null)
                foreach (var c in cards) if (c != null) c.Hide();
            if (hintButton != null) hintButton.gameObject.SetActive(false);

            if (promptLabel != null)
            {
                promptLabel.text = glyph ?? string.Empty;
                promptLabel.fontSize = promptIdeographicSize;
            }
            if (feedbackLabel != null)
            {
                feedbackLabel.text = meaning ?? string.Empty;
                feedbackLabel.color = Color.white;
            }
            if (cueLabel != null)
            {
                cueLabel.text = reading ?? string.Empty;
                cueLabel.fontSize = Mathf.Max(_cueHomeSize, 90f);
            }
        }

        /// <summary>
        /// S5 derivation stages 1-3 (spec 5.1), drawn on the board since
        /// 25 September -- in the same spot where the glyph appears at stage
        /// 4, so the object visibly becomes the character without the
        /// participant turning the head. `main` is the stage content, `note`
        /// the small line under it (progress, "not authored").
        /// </summary>
        public void ShowDerivationStage(string main, string note)
        {
            if (cards != null)
                foreach (var c in cards) if (c != null) c.Hide();
            if (hintButton != null) hintButton.gameObject.SetActive(false);
            RestoreLabelStyle();

            if (promptLabel != null)
            {
                promptLabel.text = main ?? string.Empty;
                promptLabel.fontSize = derivationSize;
            }
            if (feedbackLabel != null) feedbackLabel.text = string.Empty;
            if (cueLabel != null) cueLabel.text = note ?? string.Empty;
        }

        // ------------------------------------------------------------------
        // Guided assembly (spec 5.3) -- the board half of it
        // ------------------------------------------------------------------
        //
        // Slots on the board, where the glyph was, so the kanji is rebuilt in
        // the place it was just shown. Segments on the answer cards, in the
        // Response Area: the participant already looks there to answer, so the
        // assembly adds no new head movement (decided 25 September; the spec
        // 3.1 Interaction Table sits ~36 degrees down at 0.85 m and would make
        // the neck flex once per kanji -- EEG artefact).
        //
        // KanjiAssemblyController decides; this draws. Segment choices arrive
        // through OnOptionChosen like any card; ResponseSystemController ignores
        // them because no trial is open.

        private readonly List<Button> _slots = new();
        private readonly List<TMP_Text> _slotLabels = new();
        private readonly List<bool> _slotFilled = new();
        private int _slotNext = -1;
        private Coroutine _slotFlash;

        /// <summary>
        /// Clears the board, draws `slotCount` empty slots and binds the segment
        /// cards in row order (id, label) centred in the Response Area.
        /// </summary>
        public void ShowAssembly(int slotCount, IReadOnlyList<(string id, string label)> row, string instruction)
        {
            Clear();
            if (promptLabel != null) promptLabel.text = string.Empty;
            if (cueLabel != null) cueLabel.text = instruction ?? string.Empty;

            BuildSlots(slotCount);

            RestoreCardPositions();
            int n = Mathf.Min(row.Count, cards?.Length ?? 0);
            for (int i = 0; i < n; i++)
            {
                cards[i].Bind(row[i].id, row[i].label, OptionSizeFor(row[i].label));
                float x = (i - (n - 1) * 0.5f) * (_cardWidth + cardGap);
                ((RectTransform)cards[i].transform).anchoredPosition = new Vector2(x, _cardHome[i].y);
            }
            for (int i = n; i < (cards?.Length ?? 0); i++) cards[i].Hide();
        }

        /// <summary>Replaces the small line under the board content (assembly instruction).</summary>
        public void SetCue(string text)
        {
            if (cueLabel != null) cueLabel.text = text ?? string.Empty;
        }

        /// <summary>Highlights slot `index` as the next one and makes only it selectable.</summary>
        public void HighlightSlot(int index)
        {
            _slotNext = index;
            for (int i = 0; i < _slots.Count; i++) PaintSlot(i);
        }

        /// <summary>Marks the selected segment (null = none) and re-enables every segment still in the row.</summary>
        public void SetSegmentSelected(string segmentId, string hintSegmentId)
        {
            if (cards == null) return;
            foreach (var c in cards)
            {
                if (c == null || !c.gameObject.activeSelf || c.OptionId == null) continue;
                c.SetInteractable(true);
                if (c.OptionId == segmentId) c.SetTint(segmentSelectedColor);
                else if (c.OptionId == hintSegmentId) c.SetTint(segmentHintColor);
                else c.SetTint(null);
            }
        }

        /// <summary>The segment went into slot `index`: the slot shows its label and the card leaves the row.</summary>
        public void FillSlot(int index, string segmentId, string label)
        {
            if (index < 0 || index >= _slots.Count) return;
            _slotFilled[index] = true;
            _slotLabels[index].text = label;
            PaintSlot(index);
            if (cards != null)
                foreach (var c in cards)
                    if (c != null && c.OptionId == segmentId) c.Hide();
        }

        /// <summary>Wrong segment for slot `index`: a short flash, then it is the next slot again.</summary>
        public void FlashSlotWrong(int index)
        {
            if (index < 0 || index >= _slots.Count) return;
            if (_slotFlash != null) StopCoroutine(_slotFlash);
            _slotFlash = StartCoroutine(FlashRoutine(index));
        }

        private System.Collections.IEnumerator FlashRoutine(int index)
        {
            if (_slots[index].targetGraphic != null) _slots[index].targetGraphic.color = slotWrongColor;
            yield return new WaitForSecondsRealtime(0.4f);
            if (index < _slots.Count) PaintSlot(index);
            _slotFlash = null;
        }

        private void PaintSlot(int i)
        {
            bool next = i == _slotNext && !_slotFilled[i];
            _slots[i].interactable = next;
            if (_slots[i].targetGraphic != null)
                _slots[i].targetGraphic.color = _slotFilled[i] ? slotFilledColor : next ? slotNextColor : slotEmptyColor;
        }

        private void BuildSlots(int count)
        {
            HideAssemblySlots();
            var parent = promptLabel != null ? promptLabel.transform.parent as RectTransform : null;
            if (parent == null) { Debug.LogError("[StudioTrialPresenter] No board canvas to draw assembly slots on."); return; }

            for (int i = 0; i < count; i++)
            {
                if (i >= _slots.Count) _slots.Add(CreateSlot(parent, i));
                var b = _slots[i];
                b.gameObject.SetActive(true);
                var rt = (RectTransform)b.transform;
                rt.anchoredPosition = new Vector2((i - (count - 1) * 0.5f) * (slotSize + slotGap), slotRowY);
                _slotLabels[i].text = string.Empty;
                _slotFilled[i] = false;
            }
            _slotNext = -1;
            for (int i = 0; i < count; i++) PaintSlot(i);
        }

        private Button CreateSlot(RectTransform parent, int index)
        {
            var go = new GameObject($"AssemblySlot{index + 1}", typeof(RectTransform), typeof(Image), typeof(Button));
            go.layer = parent.gameObject.layer;
            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);
            rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f);
            rt.sizeDelta = new Vector2(slotSize, slotSize);

            var img = go.GetComponent<Image>();
            img.color = slotEmptyColor;
            var b = go.GetComponent<Button>();
            b.targetGraphic = img;
            b.transition = Selectable.Transition.None;   // the slot colour is state, not hover feedback
            int captured = index;
            b.onClick.AddListener(() => HandleSlotClicked(captured));

            var lgo = new GameObject("Label", typeof(RectTransform), typeof(TextMeshProUGUI));
            lgo.layer = go.layer;
            var lrt = (RectTransform)lgo.transform;
            lrt.SetParent(rt, false);
            lrt.anchorMin = Vector2.zero; lrt.anchorMax = Vector2.one;
            lrt.offsetMin = lrt.offsetMax = Vector2.zero;
            var t = lgo.GetComponent<TextMeshProUGUI>();
            if (promptLabel != null) t.font = promptLabel.font;
            t.fontSize = slotLabelSize;
            t.alignment = TextAlignmentOptions.Center;
            t.textWrappingMode = TextWrappingModes.NoWrap;
            t.raycastTarget = false;

            _slotLabels.Add(t);
            _slotFilled.Add(false);
            return b;
        }

        private void HideAssemblySlots()
        {
            if (_slotFlash != null) { StopCoroutine(_slotFlash); _slotFlash = null; }
            foreach (var b in _slots) if (b != null) b.gameObject.SetActive(false);
            _slotNext = -1;
        }

        /// <summary>Stage strip at the top of the board. Empty string hides it.</summary>
        public void SetStageTitle(string text)
        {
            if (stageTitleLabel != null) stageTitleLabel.text = text ?? string.Empty;
        }

        private void RestoreLabelStyle()
        {
            if (feedbackLabel != null)
            {
                if (_feedbackHomeSize > 0f) feedbackLabel.fontSize = _feedbackHomeSize;
                feedbackLabel.color = _feedbackHomeColor;
            }
            if (cueLabel != null && _cueHomeSize > 0f) cueLabel.fontSize = _cueHomeSize;
        }

        private void RestoreCardPositions()
        {
            if (_cardHome == null) return;
            for (int i = 0; i < cards.Length; i++)
                if (cards[i] != null)
                {
                    ((RectTransform)cards[i].transform).anchoredPosition = _cardHome[i];
                    if (_cardWidth > 0f && !Mathf.Approximately(cards[i].Width, _cardWidth))
                        cards[i].SetWidth(_cardWidth);   // undo a wider lone Start/Continue
                }
        }

        // ------------------------------------------------------------------
        // Tipografia derivada del contenido, no del tipo de trial
        // ------------------------------------------------------------------

        // Un kanji suelto necesita mucho mas tamano angular que una palabra en
        // ingles, asi que el tamano tiene que variar. La tentacion es ramificar
        // por RetrievalTrialType --T1 muestra significado, T2 y T3 muestran el
        // kanji-- pero ese mapeo ya vive en ResponseSystemController.BuildPromptText.
        // Repetirlo aqui pondria el mismo hecho en dos sitios, y el dia que uno
        // cambiara el otro dibujaria un kanji con tamano de texto.
        //
        // Clasificar por el contenido de la cadena que efectivamente llego no
        // puede discrepar con lo que se paso: se deriva de ello. Y como efecto
        // secundario, las opciones se dimensionan solas sin que el presentador
        // sepa nada del tipo de trial.

        private enum Script { Ideographic, Kana, Latin }

        private static Script Classify(string s)
        {
            if (string.IsNullOrWhiteSpace(s)) return Script.Latin;

            bool anyIdeograph = false, anyKana = false, anyOther = false;
            foreach (var ch in s)
            {
                if (char.IsWhiteSpace(ch)) continue;
                if ((ch >= '一' && ch <= '鿿') || (ch >= '㐀' && ch <= '䶿'))
                    anyIdeograph = true;
                else if ((ch >= '぀' && ch <= 'ゟ') || (ch >= '゠' && ch <= 'ヿ'))
                    anyKana = true;
                else
                    anyOther = true;
            }

            if (anyOther) return Script.Latin;
            if (anyIdeograph) return Script.Ideographic;   // kanji, con o sin okurigana
            if (anyKana) return Script.Kana;               // una lectura: T3
            return Script.Latin;
        }

        private float PromptSizeFor(string s) => Classify(s) switch
        {
            Script.Ideographic => promptIdeographicSize,
            Script.Kana => promptKanaSize,
            _ => promptLatinSize,
        };

        private float OptionSizeFor(string s) => Classify(s) switch
        {
            Script.Ideographic => optionIdeographicSize,
            Script.Kana => optionKanaSize,
            _ => optionLatinSize,
        };
    }
}

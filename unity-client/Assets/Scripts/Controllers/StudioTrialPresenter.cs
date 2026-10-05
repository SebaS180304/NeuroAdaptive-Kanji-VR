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

        [Header("Card layout (25 September; P2 on 30 September)")]
        [Tooltip("Space between the widest text and the label edge, per side.")]
        [SerializeField] private float cardTextPadding = 15f;
        [Tooltip("P2: option text shrinks from its script's size (optionLatinSize etc.) down to " +
                 "this before it takes a second line. The card width is sized so every text of " +
                 "the contract fits at this size.")]
        [SerializeField] private float optionMinSize = 70f;
        [Tooltip("Horizontal gap between two cards of the row (40 in the authored scene).")]
        [SerializeField] private float cardGap = 40f;

        [Header("Guided assembly slots (spec 5.3)")]
        [SerializeField] private float slotSize = 240f;
        [SerializeField] private float slotGap = 40f;
        [Tooltip("Vertical position of the slot row on the board: where the glyph sits.")]
        [SerializeField] private float slotRowY = 90f;
        [SerializeField] private float slotLabelSize = 60f;
        [SerializeField] private Color slotEmptyColor = new Color(1f, 1f, 1f, 0.12f);
        [Tooltip("Next slot, ray elsewhere: muted, so the ray's arrival is visible.")]
        [SerializeField] private Color slotNextColor = new Color(0.35f, 0.65f, 1f, 0.28f);
        [Tooltip("Next slot with the ray on it.")]
        [SerializeField] private Color slotHoverColor = new Color(0.45f, 0.75f, 1f, 0.85f);
        [SerializeField] private Color slotFilledColor = new Color(0.30f, 0.72f, 0.40f, 0.55f);
        [SerializeField] private Color slotWrongColor = new Color(0.85f, 0.35f, 0.25f, 0.70f);
        [Tooltip("Segment in the row, ray elsewhere.")]
        [SerializeField] private Color segmentIdleColor = new Color(0.18f, 0.32f, 0.55f, 1f);
        [Tooltip("Segment under the ray, and the segment in hand (which also gets a white border).")]
        [SerializeField] private Color segmentSelectedColor = new Color(0.35f, 0.65f, 1f, 1f);
        [SerializeField] private Color segmentHintColor = new Color(0.80f, 0.64f, 0.20f, 1f);
        [SerializeField] private Color segmentHintHoverColor = new Color(1f, 0.84f, 0.32f, 1f);

        [Header("Question line (30 September, demo)")]
        [Tooltip("One line above the prompt that says what the trial asks. Same text in every " +
                 "condition, so it does not touch the ESL/LAL manipulation.")]
        [SerializeField] private float questionSize = 62f;
        [Tooltip("Vertical position on the board canvas, between the stage strip and the glyph.")]
        [SerializeField] private float questionY = 308f;
        [SerializeField] private Color questionColor = new Color(0.80f, 0.86f, 0.95f, 1f);
        [Tooltip("P1 asks for Medium, and the project only has Noto Sans CJK JP Regular. Until the " +
                 "Medium font asset is imported (after the demos), the question uses a copy of the " +
                 "font material with the face dilated by this much. 0 = plain Regular.")]
        [SerializeField, Range(0f, 0.3f)] private float questionMediumDilate = 0.08f;

        [Header("Stage chip (UI design v1.3, P1)")]
        [SerializeField] private float stageTitleSize = 56f;
        [SerializeField] private Color stageTitleColor = new Color(0.6627f, 0.7059f, 0.7765f, 1f);   // #A9B4C6
        [SerializeField] private Color stageChipBorder = new Color(0.2275f, 0.2667f, 0.3765f, 1f);   // #3A4460
        [SerializeField] private float stageChipBorderWidth = 2f;
        [SerializeField] private float stageChipHeight = 80f;
        [Tooltip("Space between the text and each round end of the chip.")]
        [SerializeField] private float stageChipPadding = 28f;

        [Header("Progress dots (UI design v1.3, P6)")]
        [Tooltip("One dot per trial of the current block, right of the stage chip. They change " +
                 "only when a trial starts, and look the same at every ESL level.")]
        [SerializeField] private float progressDotSize = 14f;
        [SerializeField] private float progressDotSpacing = 10f;
        [Tooltip("Gap between the stage chip and the first dot.")]
        [SerializeField] private float progressGap = 24f;
        [SerializeField] private Color progressDoneColor = new Color(0.4863f, 0.5412f, 0.6471f, 1f);    // #7C8AA5
        [SerializeField] private Color progressCurrentColor = new Color(0.3490f, 0.6510f, 1f, 1f);      // #59A6FF
        [SerializeField] private Color progressPendingColor = new Color(0.2275f, 0.2667f, 0.3765f, 1f); // #3A4460

        [Header("Assembly with authored segment images (30 September)")]
        [Tooltip("Resources folder with {KANJI_ID}_FULL.png and {KANJI_ID}_SEG{n}.png. When every " +
                 "segment of a kanji is there, the assembly draws the real strokes; otherwise it " +
                 "falls back to the labelled slots.")]
        [SerializeField] private string segmentResourceFolder = "assembly";
        [SerializeField] private float frameSize = 560f;
        [SerializeField] private Color frameBackColor = new Color(1f, 1f, 1f, 0.06f);
        [SerializeField] private Color ghostColor = new Color(1f, 1f, 1f, 0.10f);
        [Tooltip("A segment already in place. Muted on purpose (5 October, phase test F1): the " +
                 "brightest thing on the board must be the place to fill next, not what is done.")]
        [SerializeField] private Color segmentPlacedColor = new Color(0.50f, 0.56f, 0.66f, 1f);
        [Tooltip("The place of the next segment, ray elsewhere: the dim end of its pulse.")]
        [SerializeField] private Color segmentTargetColor = new Color(0.35f, 0.65f, 1f, 0.55f);
        [Tooltip("The bright end of the pulse of the next place (5 October, phase test F1).")]
        [SerializeField] private Color segmentTargetPulseColor = new Color(0.72f, 0.90f, 1f, 1f);
        [Tooltip("The place of the next segment, ray on it: steady, no pulse, so the ray's arrival reads.")]
        [SerializeField] private Color segmentTargetHoverColor = new Color(1f, 1f, 1f, 1f);
        [Tooltip("Pulses per second of the next place. Slow on purpose: a soft cue, not a flicker, " +
                 "and far below the EEG bands of interest.")]
        [SerializeField, Range(0.2f, 2f)] private float targetPulseHz = 0.8f;
        [Tooltip("A correct piece flashes this colour, then turns placed. The whole kanji too, when complete.")]
        [SerializeField] private Color segmentCorrectColor = new Color(0.30f, 0.90f, 0.45f, 1f);
        [Tooltip("Wrong piece: the target flashes this, strong enough to read over the ghost.")]
        [SerializeField] private Color segmentWrongColor = new Color(1f, 0.30f, 0.25f, 1f);
        [SerializeField] private float correctFlashSeconds = 0.45f;

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
        private FontStyles _feedbackHomeStyle;

        [Header("Trial feedback on the board (UI design v1.3, D2)")]
        [SerializeField] private Color feedbackCorrectColor = new(0.2627f, 0.8196f, 0.4784f, 1f);   // #43D17A
        [SerializeField] private Color feedbackWrongColor = new(0.9412f, 0.5294f, 0.3529f, 1f);     // #F0875A
        [SerializeField] private float feedbackSize = 96f;

        // ------------------------------------------------------------------
        // Ciclo de vida
        // ------------------------------------------------------------------

        private void Awake()
        {
            if (feedbackLabel != null)
            {
                _feedbackHomeSize = feedbackLabel.fontSize;
                _feedbackHomeColor = feedbackLabel.color;
                _feedbackHomeStyle = feedbackLabel.fontStyle;
            }
            if (cueLabel != null)
            {
                _cueHomeSize = cueLabel.fontSize;
                _cueHomeColor = cueLabel.color;
                _cueHomeColorKnown = true;
            }

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
                    // Explicit null check, not ??: in the Editor a missing
                    // component comes back as a fake-null object.
                    var relay = c.gameObject.GetComponent<UiHoverRelay>();
                    if (relay == null) relay = c.gameObject.AddComponent<UiHoverRelay>();
                    relay.OnHover += _ => RepaintSegments();
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
            SetQuestion(QuestionFor(trialType));

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
                    need = Mathf.Max(need, MinCardWidthFor(cards[i], options[i].DisplayText));
            if (need > _cardWidth + 0.5f)
            {
                Debug.LogWarning($"[StudioTrialPresenter] An option needs a {need:0}-wide card and the row " +
                                 $"is {_cardWidth:0}. Growing it now: the card layout changed in the middle " +
                                 "of a block. FitCardsTo was not given this text.");
                LayoutRow(need);
            }

            // P2: one text size for the four cards of the trial (decided 30
            // September): the largest size at which every option fits on one
            // line, never above its script's size nor below optionMinSize. A
            // bigger or smaller card text would make one answer stand out, the
            // same reason the four cards share one width.
            int n = Mathf.Min(options.Count, cards?.Length ?? 0);
            float trialSize = float.PositiveInfinity;
            for (int i = 0; i < n; i++)
                trialSize = Mathf.Min(trialSize, OneLineSizeFor(cards[i], options[i].DisplayText));
            for (int i = 0; i < n; i++)
            {
                string text = options[i].DisplayText;
                float size = Mathf.Min(OptionSizeFor(text), trialSize);
                bool wrap = cards[i].PreferredTextWidth(text, size) > cards[i].LabelWidth - 2f * cardTextPadding + 0.5f;
                cards[i].Bind(options[i].OptionId, text, size, wrap);
            }

            // Si llegaran menos de cuatro opciones el sistema de respuesta ya
            // habria abortado; ocultar el resto evita dejar una tarjeta del trial
            // anterior visible si eso cambiara alguna vez.
            for (int i = n; i < (cards?.Length ?? 0); i++)
                cards[i].Hide();
        }

        /// <summary>
        /// Immediate feedback (UI design v1.3, D2). The cards show which one was
        /// chosen and which one was correct: chosen and correct in green with a
        /// short pop, chosen and wrong in coral, the correct one (if missed) with
        /// a green border, the rest faded. The board says "Correct" or
        /// "Answer: ...". The kanji keeps its colour. Colour only, no glow
        /// (design rule 9); the pop is the only card movement in the game and
        /// starts in the same frame as the feedback.
        /// </summary>
        public void ShowFeedback(bool isCorrect, string correctText, string selectedOptionId, string correctOptionId)
        {
            if (cards != null)
                foreach (var c in cards)
                {
                    if (c == null || !c.gameObject.activeSelf) continue;
                    c.SetInteractable(false);
                    bool chosen = c.OptionId == selectedOptionId;
                    bool correct = c.OptionId == correctOptionId;
                    c.ShowFeedback(chosen && correct ? TrialAnswerCard.FeedbackMark.ChosenCorrect
                                 : chosen ? TrialAnswerCard.FeedbackMark.ChosenWrong
                                 : correct ? TrialAnswerCard.FeedbackMark.CorrectMissed
                                 : TrialAnswerCard.FeedbackMark.Faded);
                }

            if (feedbackLabel == null) return;

            feedbackLabel.text = isCorrect ? "Correct" : $"Answer: {correctText}";
            feedbackLabel.color = isCorrect ? feedbackCorrectColor : feedbackWrongColor;
            feedbackLabel.fontSize = feedbackSize;
            feedbackLabel.fontStyle = FontStyles.Bold;
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
            //
            // P3 (UI design v1.3): the cue is a chip with the cue in words, in
            // amber on the card colour, instead of the enum name in plain text.
            // Only the cue: the "Hint · " prefix went on 30 September (Sebas);
            // the chip already reads as the hint, it sits by the Hint button.
            if (cue == LalCue.None)
            {
                cueLabel.text = string.Empty;
                HideCueChip();
                return;
            }
            string text = CueWords(cue);
            if (text.Length > 0) text = char.ToUpperInvariant(text[0]) + text.Substring(1);
            cueLabel.text = text;
            cueLabel.fontSize = cueChipFontSize;
            cueLabel.color = cueChipTextColor;
            ShowCueChip(text);
        }

        [Header("Cue chip (UI design v1.3, P3)")]
        [SerializeField] private Color cueChipColor = new(0.1647f, 0.1922f, 0.2588f, 1f);     // #2A3142
        [SerializeField] private Color cueChipTextColor = new(0.8902f, 0.7020f, 0.2549f, 1f); // #E3B341
        [SerializeField] private float cueChipFontSize = 56f;
        [SerializeField] private Vector2 cueChipPadding = new(32f, 14f);

        private Image _cueChip;
        private string _cueChipText;
        private Vector2 _cueHomePos;
        private bool _cueShifted;
        private Color _cueHomeColor;
        private bool _cueHomeColorKnown;

        /// <summary>
        /// Short, lower-case names of the granted cues, joined with " · ". Short on
        /// purpose: LAL HIGH grants two cues at once, and the full enum names
        /// ("target reading audio · visual transformation") ran under the Hint
        /// button. The names still map one-to-one to the LalCue flags.
        /// </summary>
        private static string CueWords(LalCue cue)
        {
            var parts = new List<string>();
            foreach (LalCue flag in Enum.GetValues(typeof(LalCue)))
            {
                if (flag == LalCue.None || (cue & flag) != flag) continue;
                parts.Add(flag switch
                {
                    LalCue.TargetReadingAudio => "reading audio",
                    LalCue.VisualAssociation => "picture",
                    LalCue.ReverseSemanticAssociation => "meaning link",
                    LalCue.VisualTransformation => "shape",
                    _ => flag.ToString().ToLowerInvariant(),
                });
            }
            return string.Join(" · ", parts);
        }

        private void ShowCueChip(string text)
        {
            if (!_cueHomeColorKnown) { _cueHomeColor = Color.white; _cueHomeColorKnown = true; }
            if (_cueChip == null)
            {
                var go = new GameObject("CueChip", typeof(RectTransform), typeof(Image));
                go.layer = cueLabel.gameObject.layer;
                var rt = (RectTransform)go.transform;
                rt.SetParent(cueLabel.transform.parent, false);
                _cueChip = go.GetComponent<Image>();
                _cueChip.raycastTarget = false;
                _cueChip.type = Image.Type.Sliced;
            }
            // Behind the label: moving the chip to the label's index pushes the
            // label one up. Only when the chip is in front, or the second call
            // would put it back on top of the text.
            if (_cueChip.transform.GetSiblingIndex() > cueLabel.transform.GetSiblingIndex())
                _cueChip.transform.SetSiblingIndex(cueLabel.transform.GetSiblingIndex());

            // Keep the chip clear of the Hint button (bottom right): if it would
            // reach it, the cue line slides left for as long as the chip shows.
            var labelRt = (RectTransform)cueLabel.transform;
            if (!_cueShifted) _cueHomePos = labelRt.anchoredPosition;
            labelRt.anchoredPosition = _cueHomePos;
            cueLabel.ForceMeshUpdate();
            if (hintButton != null && hintButton.gameObject.activeSelf && hintButton.transform.parent == labelRt.parent)
            {
                var hrt = (RectTransform)hintButton.transform;
                float hintLeft = hrt.anchoredPosition.x - hrt.rect.width * hrt.pivot.x;
                float right = labelRt.anchoredPosition.x + cueLabel.textBounds.max.x + cueChipPadding.x;
                float clear = hintLeft - 24f;
                if (right > clear)
                {
                    labelRt.anchoredPosition = _cueHomePos + new Vector2(clear - right, 0f);
                    _cueShifted = true;
                    cueLabel.ForceMeshUpdate();
                }
            }
            var b = cueLabel.textBounds;
            var chipRt = (RectTransform)_cueChip.transform;
            var parent = (RectTransform)chipRt.parent;
            Vector3 centre = parent.InverseTransformPoint(cueLabel.transform.TransformPoint(b.center));
            chipRt.anchorMin = chipRt.anchorMax = new Vector2(0.5f, 0.5f);
            chipRt.pivot = new Vector2(0.5f, 0.5f);
            Vector2 size = new(b.size.x + 2f * cueChipPadding.x, b.size.y + 2f * cueChipPadding.y);
            chipRt.sizeDelta = size;
            chipRt.anchoredPosition = (Vector2)centre - parent.rect.center;
            _cueChip.sprite = PillSprite.Get(size.y * 0.5f);
            _cueChip.color = cueChipColor;
            _cueChip.gameObject.SetActive(true);
            _cueChipText = text;
        }

        private void HideCueChip()
        {
            if (_cueChip != null) _cueChip.gameObject.SetActive(false);
            _cueChipText = null;
            if (_cueShifted && cueLabel != null)
            {
                ((RectTransform)cueLabel.transform).anchoredPosition = _cueHomePos;
                _cueShifted = false;
            }
            if (cueLabel != null && _cueHomeColorKnown) cueLabel.color = _cueHomeColor;
        }

        // Any other use of the cue line (exposure reading, assembly instruction,
        // notes) overwrites its text: the chip follows the text it was built for.
        private void LateUpdate()
        {
            PulseAssemblyTarget();
            if (_cueChipText != null && (cueLabel == null || cueLabel.text != _cueChipText))
            {
                // Undo only what the chip changed: whoever wrote the new text may
                // have set its own size (the S5 reading is 90).
                bool chipSize = cueLabel != null && Mathf.Approximately(cueLabel.fontSize, cueChipFontSize);
                HideCueChip();
                if (chipSize && _cueHomeSize > 0f) cueLabel.fontSize = _cueHomeSize;
            }
        }

        public void Clear()
        {
            SetQuestion(null);
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
        /// show. P2: "fits" means at optionMinSize, on one line or on two lines
        /// broken between words; Present then picks the largest size that fits. Called
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
                float w = MinCardWidthFor(cards[0], t);
                if (w > need) { need = w; widest = t; }
            }
            LayoutRow(need);

            float row = cards.Length * _cardWidth + (cards.Length - 1) * cardGap;
            Debug.Log($"[StudioTrialPresenter] Answer cards {_cardWidth:0} wide, row {row:0}" +
                      (widest != null ? $" (widest text: '{widest}')" : " (authored width, every text fits)"));
        }

        /// <summary>
        /// P2: card width a text needs at the minimum size. A text of several
        /// words may take two lines, so it only needs its longest line when
        /// split in two between words; a single word needs its full width. The
        /// row is sized from this, so no word is ever split.
        /// </summary>
        private float MinCardWidthFor(TrialAnswerCard card, string text)
        {
            if (string.IsNullOrEmpty(text)) return 0f;
            float size = Mathf.Min(OptionSizeFor(text), optionMinSize);
            float oneLine = CardWidthAt(card, text, size);
            int best = -1;
            float bestLine = float.PositiveInfinity;
            for (int i = text.IndexOf(' '); i > 0; i = text.IndexOf(' ', i + 1))
            {
                float line = Mathf.Max(CardWidthAt(card, text.Substring(0, i).TrimEnd(), size),
                                       CardWidthAt(card, text.Substring(i + 1).TrimStart(), size));
                if (line < bestLine) { bestLine = line; best = i; }
            }
            return best < 0 ? oneLine : Mathf.Min(oneLine, bestLine);
        }

        /// <summary>
        /// P2: the largest size, between optionMinSize and the script's size,
        /// at which <paramref name="text"/> fits this card on one line.
        /// Returns optionMinSize when it does not fit even there (it wraps).
        /// </summary>
        private float OneLineSizeFor(TrialAnswerCard card, string text)
        {
            float max = OptionSizeFor(text);
            float min = Mathf.Min(max, optionMinSize);
            float room = card.LabelWidth - 2f * cardTextPadding;
            float w = card.PreferredTextWidth(text, max);
            if (w <= 0f || w <= room) return max;
            // Text width is linear in font size.
            return Mathf.Clamp(Mathf.Floor(max * room / w), min, max);
        }

        private float CardWidthAt(TrialAnswerCard card, string text, float size)
        {
            float textW = card.PreferredTextWidth(text, size);
            if (textW <= 0f) return 0f;
            var cardRt = (RectTransform)card.transform;
            float inset = 0f;
            var lbl = card.GetComponentInChildren<TMP_Text>(true);
            if (lbl != null) inset = cardRt.rect.width - ((RectTransform)lbl.transform).rect.width;
            return Mathf.Ceil(textW + 2f * cardTextPadding + inset);
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
            SetQuestion(null);
            HideAssemblySlots();
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
            SetQuestion(null);
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
        private bool _assemblyActive;
        private string _segmentInHand, _segmentHint;

        /// <summary>
        /// Clears the board, draws `slotCount` empty slots and binds the segment
        /// cards in row order (id, label) centred in the Response Area.
        /// </summary>
        public void ShowAssembly(int slotCount, IReadOnlyList<(string id, string label)> row, string instruction,
                                 string kanjiId = null)
        {
            Clear();
            if (promptLabel != null) promptLabel.text = string.Empty;
            if (cueLabel != null) cueLabel.text = instruction ?? string.Empty;

            // Real strokes when every segment image exists; labelled slots otherwise.
            var segTex = LoadSegments(kanjiId, slotCount, out var fullTex);
            _imageMode = segTex != null;
            if (_imageMode) BuildFrame(fullTex, segTex);
            else BuildSlots(slotCount);

            RestoreCardPositions();
            int n = Mathf.Min(row.Count, cards?.Length ?? 0);
            for (int i = 0; i < n; i++)
            {
                cards[i].Bind(row[i].id, _imageMode ? string.Empty : row[i].label, OptionSizeFor(row[i].label));
                cards[i].SetAssemblyLook(true);   // the assembly paints its own segments
                if (_imageMode) cards[i].SetImage(_cardTex[SegmentIndex(row[i].id)]);
                float x = (i - (n - 1) * 0.5f) * (_cardWidth + cardGap);
                ((RectTransform)cards[i].transform).anchoredPosition = new Vector2(x, _cardHome[i].y);
            }
            for (int i = n; i < (cards?.Length ?? 0); i++) cards[i].Hide();

            _assemblyActive = true;
            _segmentInHand = _segmentHint = null;
            RepaintSegments();
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
            for (int i = 0; i < SlotCount; i++) PaintSlot(i);
        }

        /// <summary>Marks the selected segment (null = none) and re-enables every segment still in the row.</summary>
        public void SetSegmentSelected(string segmentId, string hintSegmentId)
        {
            if (cards == null) return;
            _segmentInHand = segmentId;
            _segmentHint = hintSegmentId;
            foreach (var c in cards)
                if (c != null && c.gameObject.activeSelf && c.OptionId != null) c.SetInteractable(true);
            RepaintSegments();
        }

        /// <summary>
        /// Segment colours from state + ray (28 September): muted blue at rest,
        /// bright blue under the ray, bright blue with a white border while in
        /// hand, amber for the hint. Only during an assembly; trials keep the
        /// authored card look.
        /// </summary>
        private void RepaintSegments()
        {
            if (!_assemblyActive || cards == null) return;
            foreach (var c in cards)
            {
                if (c == null || !c.gameObject.activeSelf || c.OptionId == null) continue;
                var relay = c.GetComponent<UiHoverRelay>();
                bool hovered = relay != null && relay.Hovered;
                bool inHand = c.OptionId == _segmentInHand;
                Color color = c.OptionId == _segmentHint && !inHand
                    ? (hovered ? segmentHintHoverColor : segmentHintColor)
                    : (inHand || hovered ? segmentSelectedColor : segmentIdleColor);
                c.SetTint(color);
                c.SetOutline(inHand);
            }
        }

        /// <summary>The segment went into slot `index`: the slot shows its label and the card leaves the row.</summary>
        public void FillSlot(int index, string segmentId, string label)
        {
            if (index < 0 || index >= SlotCount) return;
            if (_imageMode) _segFilled[index] = true;
            else
            {
                _slotFilled[index] = true;
                _slotLabels[index].text = label;
            }
            PaintSlot(index);
            if (_imageMode) StartCoroutine(CorrectFlash(index));
            if (cards != null)
                foreach (var c in cards)
                    if (c != null && c.OptionId == segmentId) c.Hide();
        }

        /// <summary>Wrong segment for slot `index`: a short flash, then it is the next slot again.</summary>
        public void FlashSlotWrong(int index)
        {
            if (index < 0 || index >= SlotCount) return;
            if (_slotFlash != null) StopCoroutine(_slotFlash);
            _slotFlash = StartCoroutine(FlashRoutine(index));
        }

        private System.Collections.IEnumerator FlashRoutine(int index)
        {
            var list = _imageMode ? _segSlots : _slots;
            if (index < list.Count && list[index].targetGraphic != null)
                list[index].targetGraphic.color = _imageMode ? segmentWrongColor : slotWrongColor;
            yield return new WaitForSecondsRealtime(_imageMode ? 0.55f : 0.4f);
            if (index < SlotCount) PaintSlot(index);
            _slotFlash = null;
        }

        private void PaintSlot(int i)
        {
            if (_imageMode) { PaintSegmentSlot(i); return; }
            bool next = i == _slotNext && !_slotFilled[i];
            _slots[i].interactable = next;
            var relay = _slots[i].GetComponent<UiHoverRelay>();
            bool hovered = relay != null && relay.Hovered;
            if (_slots[i].targetGraphic != null)
                _slots[i].targetGraphic.color = _slotFilled[i] ? slotFilledColor
                                              : next ? (hovered ? slotHoverColor : Color.Lerp(slotNextColor, segmentTargetPulseColor, TargetPulse()))
                                              : slotEmptyColor;
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
            go.AddComponent<UiHoverRelay>().OnHover += _ =>
            {
                if (captured < _slots.Count && _slotFlash == null) PaintSlot(captured);
            };

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
            if (_frame != null) _frame.gameObject.SetActive(false);
            _imageMode = false;
            _slotNext = -1;
            _assemblyActive = false;
            _segmentInHand = _segmentHint = null;
        }

        // ------------------------------------------------------------------
        // Assembly with authored segment images (30 September)
        // ------------------------------------------------------------------
        //
        // One frame where the glyph sits. The whole kanji shows as a faint
        // ghost; the place of the next segment is tinted and is the only thing
        // the ray can hit; each placed segment turns solid in its exact place.
        // Every segment image is the full frame with only its strokes inked,
        // cut from the same Noto face the board uses (tools/assembly_segments.py),
        // so stacking them rebuilds the glyph pixel for pixel. The controller,
        // the slot indices and the telemetry are the same as with labelled slots.

        private bool _imageMode;
        private RectTransform _frame;
        private RawImage _ghost;
        private readonly List<Button> _segSlots = new();
        private readonly List<bool> _segFilled = new();
        private readonly Dictionary<string, int> _segIndexById = new();

        private Texture2D[] _cardTex;

        private int SlotCount => _imageMode ? _segSlots.Count : _slots.Count;

        private int SegmentIndex(string segmentId) =>
            segmentId != null && _segIndexById.TryGetValue(segmentId, out var i) ? i : 0;

        /// <summary>All N segment textures of a kanji, or null if any is missing.</summary>
        private Texture2D[] LoadSegments(string kanjiId, int count, out Texture2D full)
        {
            full = null;
            _segIndexById.Clear();
            if (string.IsNullOrEmpty(kanjiId) || count <= 0) return null;
            var tex = new Texture2D[count];
            _cardTex = new Texture2D[count];
            for (int i = 0; i < count; i++)
            {
                tex[i] = Resources.Load<Texture2D>($"{segmentResourceFolder}/{kanjiId}_SEG{i + 1}");
                if (tex[i] == null) return null;
                // The card shows the piece cropped and large; the board keeps the full frame.
                _cardTex[i] = Resources.Load<Texture2D>($"{segmentResourceFolder}/{kanjiId}_SEG{i + 1}_CARD") ?? tex[i];
                // AssemblyPlan names placeholder segments {KANJI_ID}_SEG{n}, in slot order.
                _segIndexById[$"{kanjiId}_SEG{i + 1}"] = i;
            }
            full = Resources.Load<Texture2D>($"{segmentResourceFolder}/{kanjiId}_FULL");
            return tex;
        }

        private void BuildFrame(Texture2D full, Texture2D[] segments)
        {
            var parent = promptLabel != null ? promptLabel.transform.parent as RectTransform : null;
            if (parent == null) { Debug.LogError("[StudioTrialPresenter] No board canvas for the assembly frame."); return; }

            if (_frame == null)
            {
                var go = new GameObject("AssemblyFrame", typeof(RectTransform), typeof(Image));
                go.layer = parent.gameObject.layer;
                _frame = (RectTransform)go.transform;
                _frame.SetParent(parent, false);
                _frame.anchorMin = _frame.anchorMax = new Vector2(0.5f, 0.5f);
                var back = go.GetComponent<Image>();
                back.color = frameBackColor;
                back.raycastTarget = false;
                _ghost = NewRawImage("Ghost", _frame);
            }
            _frame.gameObject.SetActive(true);
            _frame.sizeDelta = new Vector2(frameSize, frameSize);
            _frame.anchoredPosition = new Vector2(0f, slotRowY);
            _ghost.texture = full;
            _ghost.color = ghostColor;
            _ghost.gameObject.SetActive(full != null);

            for (int i = 0; i < segments.Length; i++)
            {
                if (i >= _segSlots.Count)
                {
                    var img = NewRawImage($"Segment{i + 1}", _frame);
                    var b = img.gameObject.AddComponent<Button>();
                    b.targetGraphic = img;
                    b.transition = Selectable.Transition.None;
                    int captured = i;
                    b.onClick.AddListener(() => HandleSlotClicked(captured));
                    img.gameObject.AddComponent<UiHoverRelay>().OnHover += _ =>
                    {
                        if (captured < _segSlots.Count && _slotFlash == null) PaintSlot(captured);
                    };
                    _segSlots.Add(b);
                    _segFilled.Add(false);
                }
                var raw = (RawImage)_segSlots[i].targetGraphic;
                raw.texture = segments[i];
                _segSlots[i].gameObject.SetActive(true);
                _segFilled[i] = false;
            }
            for (int i = segments.Length; i < _segSlots.Count; i++) _segSlots[i].gameObject.SetActive(false);

            _slotNext = -1;
            // Only the frame's own children are shown; the Image of the frame is the backdrop.
            for (int i = 0; i < segments.Length; i++) PaintSlot(i);
        }

        private RawImage NewRawImage(string name, RectTransform parent)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(RawImage));
            go.layer = parent.gameObject.layer;
            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);
            rt.anchorMin = Vector2.zero; rt.anchorMax = Vector2.one;
            rt.offsetMin = rt.offsetMax = Vector2.zero;
            var img = go.GetComponent<RawImage>();
            img.raycastTarget = false;
            return img;
        }

        private void PaintSegmentSlot(int i)
        {
            if (i < 0 || i >= _segSlots.Count) return;
            var b = _segSlots[i];
            var raw = (RawImage)b.targetGraphic;
            bool filled = _segFilled[i];
            bool next = i == _slotNext && !filled;
            var relay = b.GetComponent<UiHoverRelay>();
            bool hovered = relay != null && relay.Hovered;
            b.interactable = next;
            // Only the target can take the ray: the others cover the same rectangle.
            raw.raycastTarget = next;
            raw.color = filled ? segmentPlacedColor
                      : next ? (hovered ? segmentTargetHoverColor : Color.Lerp(segmentTargetColor, segmentTargetPulseColor, TargetPulse()))
                      : Color.clear;
            if (next && b.transform.GetSiblingIndex() != b.transform.parent.childCount - 1)
                b.transform.SetAsLastSibling();
        }

        /// <summary>0..1, smooth: where the next place is in its pulse.</summary>
        private float TargetPulse() =>
            0.5f + 0.5f * Mathf.Sin(Time.unscaledTime * targetPulseHz * 2f * Mathf.PI);

        /// <summary>
        /// Keeps the next place pulsing (5 October, phase test F1: OBS_02 asked for the
        /// place to fill to pulse). Only while an assembly runs, never over a wrong-piece
        /// flash, and never on a slot already filled (the completion green stays).
        /// </summary>
        private void PulseAssemblyTarget()
        {
            if (!_assemblyActive || _slotFlash != null || _slotNext < 0 || _slotNext >= SlotCount) return;
            bool filled = _imageMode ? _segFilled[_slotNext] : _slotFilled[_slotNext];
            if (!filled) PaintSlot(_slotNext);
        }

        private System.Collections.IEnumerator CorrectFlash(int index)
        {
            if (index >= _segSlots.Count) yield break;
            var raw = (RawImage)_segSlots[index].targetGraphic;
            raw.color = segmentCorrectColor;
            yield return new WaitForSecondsRealtime(correctFlashSeconds);
            if (_imageMode && index < _segSlots.Count && _segFilled[index]) PaintSlot(index);
        }

        /// <summary>
        /// The kanji is complete: every piece (or every slot) turns green. The
        /// caller decides how long it stays before moving on.
        /// </summary>
        public void ShowAssemblyComplete()
        {
            if (_imageMode)
            {
                StopAllCoroutines();   // a pending per-piece flash must not repaint over the green
                _slotFlash = null;
                for (int i = 0; i < _segSlots.Count; i++)
                    if (_segSlots[i].gameObject.activeSelf)
                        ((RawImage)_segSlots[i].targetGraphic).color = segmentCorrectColor;
                if (_ghost != null) _ghost.color = Color.clear;
            }
            else
            {
                for (int i = 0; i < _slots.Count; i++)
                    if (_slots[i].gameObject.activeSelf && _slots[i].targetGraphic != null)
                        _slots[i].targetGraphic.color = segmentCorrectColor;
            }
            SetCue("Well done!");
        }

        // ------------------------------------------------------------------
        // Question line (30 September)
        // ------------------------------------------------------------------

        private TMP_Text _question;

        /// <summary>What the trial asks, by type. English, like the rest of the board.</summary>
        public static string QuestionFor(RetrievalTrialType type) => type switch
        {
            RetrievalTrialType.MeaningToKanji => "Which kanji has this meaning?",
            RetrievalTrialType.KanjiToMeaning => "What does this kanji mean?",
            RetrievalTrialType.KanjiToReading => "How do you read this kanji?",
            _ => string.Empty,
        };

        /// <summary>The line above the prompt. Null or empty hides it.</summary>
        public void SetQuestion(string text)
        {
            if (string.IsNullOrEmpty(text))
            {
                if (_question != null) _question.text = string.Empty;
                return;
            }
            if (_question == null)
            {
                var parent = promptLabel != null ? promptLabel.transform.parent as RectTransform : null;
                if (parent == null) return;
                var go = new GameObject("QuestionLabel", typeof(RectTransform), typeof(TextMeshProUGUI));
                go.layer = parent.gameObject.layer;
                var rt = (RectTransform)go.transform;
                rt.SetParent(parent, false);
                rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f);
                rt.sizeDelta = new Vector2(1500f, 80f);
                var t = go.GetComponent<TextMeshProUGUI>();
                if (promptLabel != null) t.font = promptLabel.font;
                var medium = MediumMaterial(t.font);
                if (medium != null) t.fontSharedMaterial = medium;
                t.alignment = TextAlignmentOptions.Center;
                t.textWrappingMode = TextWrappingModes.NoWrap;
                t.raycastTarget = false;
                _question = t;
            }
            ((RectTransform)_question.transform).anchoredPosition = new Vector2(0f, questionY);
            _question.fontSize = questionSize;
            _question.color = questionColor;
            _question.text = text;
        }

        private Material _mediumMaterial;

        /// <summary>
        /// Stand-in for a Medium weight: the font's own material with a slightly
        /// dilated face. Remove when the Noto Sans JP Medium asset exists.
        /// </summary>
        private Material MediumMaterial(TMP_FontAsset font)
        {
            if (font == null || font.material == null || questionMediumDilate <= 0f) return null;
            if (_mediumMaterial == null)
            {
                _mediumMaterial = new Material(font.material) { name = font.material.name + " (Medium)" };
                _mediumMaterial.SetFloat(ShaderUtilities.ID_FaceDilate, questionMediumDilate);
                ShaderUtilities.UpdateShaderRatios(_mediumMaterial);
            }
            return _mediumMaterial;
        }

        private RectTransform _stageChip;

        /// <summary>
        /// Stage chip at the top of the board ("Step 3 of 9 · Learn"). Empty
        /// string hides it. P1: the text sits inside a pill outline, sized to
        /// the text, centred where the old strip was.
        /// </summary>
        public void SetStageTitle(string text)
        {
            if (stageTitleLabel == null) return;
            stageTitleLabel.text = text ?? string.Empty;
            StyleStageChip();
            LayoutHeader();
        }

        private void StyleStageChip()
        {
            stageTitleLabel.fontSize = stageTitleSize;
            stageTitleLabel.color = stageTitleColor;
            stageTitleLabel.alignment = TextAlignmentOptions.Center;
            stageTitleLabel.textWrappingMode = TextWrappingModes.NoWrap;
            if (_stageChip != null) return;

            var parent = stageTitleLabel.transform.parent as RectTransform;
            if (parent == null) return;
            var go = new GameObject("StageChip", typeof(RectTransform), typeof(Image));
            go.layer = stageTitleLabel.gameObject.layer;
            _stageChip = (RectTransform)go.transform;
            _stageChip.SetParent(parent, false);
            var lrt = (RectTransform)stageTitleLabel.transform;
            _stageChip.anchorMin = lrt.anchorMin;
            _stageChip.anchorMax = lrt.anchorMax;
            _stageChip.pivot = new Vector2(0.5f, 0.5f);
            _stageChip.SetSiblingIndex(stageTitleLabel.transform.GetSiblingIndex());   // behind the text
            var img = go.GetComponent<Image>();
            img.sprite = PillSprite.Get(stageChipHeight * 0.5f, stageChipBorderWidth);
            img.type = Image.Type.Sliced;
            img.color = stageChipBorder;
            img.raycastTarget = false;
        }

        private float _headerY = float.NaN;

        /// <summary>
        /// Places the header row: the stage chip, then the progress dots, the
        /// pair centred on the board as one group (so a stage without dots
        /// keeps its chip exactly where it was).
        /// </summary>
        private void LayoutHeader()
        {
            if (stageTitleLabel == null) return;
            var lrt = (RectTransform)stageTitleLabel.transform;
            if (float.IsNaN(_headerY)) _headerY = lrt.anchoredPosition.y;

            bool chipOn = !string.IsNullOrEmpty(stageTitleLabel.text);
            if (_stageChip != null) _stageChip.gameObject.SetActive(chipOn);
            int dots = _progressCount;

            float chipW = 0f;
            if (chipOn)
            {
                float textW = stageTitleLabel.GetPreferredValues(stageTitleLabel.text,
                                  float.PositiveInfinity, float.PositiveInfinity).x;
                chipW = textW + 2f * stageChipPadding;
            }
            float dotsW = dots > 0 ? dots * progressDotSize + (dots - 1) * progressDotSpacing : 0f;
            float total = chipW + dotsW + (chipOn && dots > 0 ? progressGap : 0f);
            float left = -total * 0.5f;

            if (chipOn)
            {
                lrt.sizeDelta = new Vector2(chipW, stageChipHeight);
                lrt.anchoredPosition = new Vector2(left + chipW * 0.5f, _headerY);
                if (_stageChip != null)
                {
                    _stageChip.sizeDelta = lrt.sizeDelta;
                    _stageChip.anchoredPosition = lrt.anchoredPosition;
                }
            }

            if (_progressRow != null)
            {
                _progressRow.gameObject.SetActive(dots > 0);
                float x = left + (chipOn ? chipW + progressGap : 0f);
                _progressRow.anchoredPosition = new Vector2(x + dotsW * 0.5f, _headerY);
                _progressRow.sizeDelta = new Vector2(dotsW, progressDotSize);
            }
        }

        // ------------------------------------------------------------------
        // Progress dots (P6)
        // ------------------------------------------------------------------

        private RectTransform _progressRow;
        private readonly List<Image> _progressDots = new();
        private int _progressCount;

        /// <summary>
        /// Progress through the current block: <paramref name="index"/> is the
        /// 0-based trial that is starting, <paramref name="count"/> the block
        /// length. Dots before it are done, it is current, the rest pending.
        /// count 0 hides the dots. SessionFlowRunner calls this only when a
        /// trial starts and when a block ends, so answering never moves them.
        /// Clear() leaves them alone: like the stage chip, they belong to the
        /// block, not to one trial.
        /// </summary>
        public void SetProgress(int index, int count)
        {
            count = Mathf.Max(0, count);
            if (count > 0) EnsureProgressRow(count);
            _progressCount = _progressRow != null ? count : 0;

            for (int i = 0; i < _progressDots.Count; i++)
            {
                var dot = _progressDots[i];
                bool on = i < _progressCount;
                dot.gameObject.SetActive(on);
                if (!on) continue;
                dot.color = i < index ? progressDoneColor
                          : i == index ? progressCurrentColor
                          : progressPendingColor;
                ((RectTransform)dot.transform).anchoredPosition =
                    new Vector2(i * (progressDotSize + progressDotSpacing), 0f);
            }
            LayoutHeader();
        }

        private void EnsureProgressRow(int count)
        {
            if (_progressRow == null)
            {
                var parent = stageTitleLabel != null ? stageTitleLabel.transform.parent as RectTransform : null;
                if (parent == null) return;
                var go = new GameObject("ProgressDots", typeof(RectTransform));
                go.layer = parent.gameObject.layer;
                _progressRow = (RectTransform)go.transform;
                _progressRow.SetParent(parent, false);
                var lrt = (RectTransform)stageTitleLabel.transform;
                _progressRow.anchorMin = lrt.anchorMin;
                _progressRow.anchorMax = lrt.anchorMax;
                _progressRow.pivot = new Vector2(0.5f, 0.5f);
                if (float.IsNaN(_headerY)) _headerY = lrt.anchoredPosition.y;
            }
            var sprite = PillSprite.Get(progressDotSize * 0.5f);   // a pill as tall as it is wide is a circle
            while (_progressDots.Count < count)
            {
                var d = new GameObject("Dot" + _progressDots.Count, typeof(RectTransform), typeof(Image));
                d.layer = _progressRow.gameObject.layer;
                var rt = (RectTransform)d.transform;
                rt.SetParent(_progressRow, false);
                rt.anchorMin = rt.anchorMax = new Vector2(0f, 0.5f);
                rt.pivot = new Vector2(0f, 0.5f);
                rt.sizeDelta = new Vector2(progressDotSize, progressDotSize);
                var img = d.GetComponent<Image>();
                img.sprite = sprite;
                img.type = Image.Type.Simple;
                img.raycastTarget = false;
                _progressDots.Add(img);
            }
        }

        private void RestoreLabelStyle()
        {
            if (feedbackLabel != null)
            {
                if (_feedbackHomeSize > 0f) feedbackLabel.fontSize = _feedbackHomeSize;
                feedbackLabel.color = _feedbackHomeColor;
                feedbackLabel.fontStyle = _feedbackHomeStyle;
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

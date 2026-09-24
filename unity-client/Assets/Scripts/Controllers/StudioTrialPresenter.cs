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

        public event Action<string> OnOptionChosen;
        public event Action OnHintRequested;

        // Where each card lives in the scene. ShowSingleChoice moves one card
        // to the centre; everything that presents a trial puts them back, so a
        // centred Start card can never leak into a trial layout.
        private Vector2[] _cardHome;

        // ------------------------------------------------------------------
        // Ciclo de vida
        // ------------------------------------------------------------------

        private void Awake()
        {
            if (cards != null)
            {
                _cardHome = new Vector2[cards.Length];
                for (int i = 0; i < cards.Length; i++)
                    if (cards[i] != null)
                        _cardHome[i] = ((RectTransform)cards[i].transform).anchoredPosition;
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
        private void HandleHintClicked() => OnHintRequested?.Invoke();

        // ------------------------------------------------------------------
        // ITrialPresenter
        // ------------------------------------------------------------------

        public void Present(RetrievalTrialType trialType, string promptText,
                            IReadOnlyList<TrialOption> options)
        {
            if (feedbackLabel != null) feedbackLabel.text = string.Empty;
            if (cueLabel != null) cueLabel.text = string.Empty;

            if (promptLabel != null)
            {
                promptLabel.text = promptText;
                promptLabel.fontSize = PromptSizeFor(promptText);
            }

            RestoreCardPositions();

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
        }

        /// <summary>Stage strip at the top of the board. Empty string hides it.</summary>
        public void SetStageTitle(string text)
        {
            if (stageTitleLabel != null) stageTitleLabel.text = text ?? string.Empty;
        }

        private void RestoreCardPositions()
        {
            if (_cardHome == null) return;
            for (int i = 0; i < cards.Length; i++)
                if (cards[i] != null)
                    ((RectTransform)cards[i].transform).anchoredPosition = _cardHome[i];
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

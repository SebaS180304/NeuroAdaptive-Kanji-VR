using System;
using System.Collections.Generic;
using System.Text;
using NeuroAdaptiveVR.Data;
using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Presentador de consola. Dibuja el trial en el log y acepta la
    /// respuesta por teclado --1-4 eligen opcion, H pide ayuda-- o desde el
    /// menu contextual del componente durante Play.
    ///
    /// No es un placeholder de la escena: es un banco de pruebas. La escena
    /// `JapaneseLearningStudio` llega despues, pero el ciclo del trial y su
    /// telemetria se ejercitan aqui sin depender de ella. Se conserva incluso
    /// con la escena hecha: un fallo que aparece aqui esta en el ciclo, y uno
    /// que solo aparece en VR esta en la escena.
    ///
    /// CORRECCION (9 sep 2026): la primera version usaba UnityEngine.Input,
    /// la API del Input Manager antiguo. Este proyecto tiene
    /// com.unity.inputsystem y Active Input Handling en "Input System Package
    /// (New)", donde esa API lanza InvalidOperationException en cada frame.
    /// Ahora el camino se elige en compilacion: con el Input System activo, la
    /// rama vieja ni siquiera se compila, asi que no puede volver a fallar en
    /// runtime por este motivo.
    /// </summary>
    public class DebugTrialPresenter : MonoBehaviour, ITrialPresenter
    {
        [Tooltip("Si se desactiva, solo se puede responder desde el menu contextual.")]
        [SerializeField] private bool acceptKeyboardInput = true;

        private readonly List<TrialOption> _options = new();
        private bool _accepting;
        private bool _hintAvailable;

        public event Action<string> OnOptionChosen;
        public event Action OnHintRequested;

        // ------------------------------------------------------------------
        // ITrialPresenter
        // ------------------------------------------------------------------

        public void Present(RetrievalTrialType trialType, string promptText,
                            IReadOnlyList<TrialOption> options)
        {
            _options.Clear();
            _options.AddRange(options);
            _accepting = true;

            var sb = new StringBuilder();
            sb.AppendLine($"┌─ {TrialLabel(trialType)}");
            sb.AppendLine($"│  {promptText}");
            sb.Append("│  ");
            for (int i = 0; i < _options.Count; i++)
                sb.Append($"[{i + 1}] {_options[i].DisplayText}   ");
            sb.AppendLine();
            sb.Append(_hintAvailable
                ? "└─ teclas 1-4 para responder · H para ayuda · o menu contextual"
                : "└─ teclas 1-4 para responder · o menu contextual");
            Debug.Log(sb.ToString());
        }

        public void ShowFeedback(bool isCorrect, string correctText)
        {
            _accepting = false;
            Debug.Log(isCorrect ? "   ✔ correcto" : $"   ✘ incorrecto — era: {correctText}");
        }

        public void SetHintAvailable(bool available) => _hintAvailable = available;

        public void ShowCue(LalCue cue) => Debug.Log($"   ◆ cue presentado: {cue}");

        public void Clear()
        {
            _accepting = false;
            _options.Clear();
        }

        // ------------------------------------------------------------------
        // Entrada
        // ------------------------------------------------------------------

        /// <summary>
        /// Elige la opcion por indice visible (0 = tarjeta [1]). Publico para
        /// que se pueda responder sin teclado, desde el menu contextual o
        /// desde un test.
        /// </summary>
        public void ChooseOption(int index)
        {
            if (!_accepting) { Debug.LogWarning("[DebugTrialPresenter] No hay trial esperando respuesta."); return; }
            if (index < 0 || index >= _options.Count)
            {
                Debug.LogWarning($"[DebugTrialPresenter] Indice {index} fuera de rango " +
                                 $"(hay {_options.Count} opciones).");
                return;
            }

            _accepting = false;   // evita dos respuestas en el mismo frame
            OnOptionChosen?.Invoke(_options[index].OptionId);
        }

        public void RequestHint()
        {
            if (!_accepting) return;
            OnHintRequested?.Invoke();
        }

        private void Update()
        {
            if (!_accepting || !acceptKeyboardInput) return;

            if (_hintAvailable && HintKeyPressed()) { RequestHint(); return; }

            for (int i = 0; i < _options.Count && i < 4; i++)
            {
                if (OptionKeyPressed(i)) { ChooseOption(i); return; }
            }
        }

        // La rama que no corresponde al Active Input Handling del proyecto no
        // se compila. Con "Both" gana el Input System, que es el camino que
        // este proyecto usa de verdad.
#if ENABLE_INPUT_SYSTEM
        private static readonly Key[] DigitKeys = { Key.Digit1, Key.Digit2, Key.Digit3, Key.Digit4 };

        private static bool HintKeyPressed()
            => Keyboard.current != null && Keyboard.current.hKey.wasPressedThisFrame;

        private static bool OptionKeyPressed(int index)
            => Keyboard.current != null && index < DigitKeys.Length
               && Keyboard.current[DigitKeys[index]].wasPressedThisFrame;
#elif ENABLE_LEGACY_INPUT_MANAGER
        private static bool HintKeyPressed() => Input.GetKeyDown(KeyCode.H);

        private static bool OptionKeyPressed(int index) => Input.GetKeyDown(KeyCode.Alpha1 + index);
#else
        private static bool HintKeyPressed() => false;
        private static bool OptionKeyPressed(int index) => false;
#endif

        // ------------------------------------------------------------------
        // Menu contextual: responder sin teclado y sin foco en la Game view
        // ------------------------------------------------------------------

        [ContextMenu("Answer 1")] private void Answer1() => ChooseOption(0);
        [ContextMenu("Answer 2")] private void Answer2() => ChooseOption(1);
        [ContextMenu("Answer 3")] private void Answer3() => ChooseOption(2);
        [ContextMenu("Answer 4")] private void Answer4() => ChooseOption(3);
        [ContextMenu("Request Hint")] private void HintFromMenu() => RequestHint();

        private static string TrialLabel(RetrievalTrialType t) => t switch
        {
            RetrievalTrialType.MeaningToKanji => "T1 · significado → kanji",
            RetrievalTrialType.KanjiToMeaning => "T2 · kanji → significado",
            RetrievalTrialType.KanjiToReading => "T3 · kanji → lectura",
            _ => t.ToString(),
        };
    }
}

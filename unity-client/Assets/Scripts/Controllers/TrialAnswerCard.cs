using System;
using TMPro;
using UnityEngine;
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
    /// </summary>
    [RequireComponent(typeof(Button))]
    public class TrialAnswerCard : MonoBehaviour
    {
        [SerializeField] private Button button;
        [SerializeField] private TMP_Text label;

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

            button.onClick.AddListener(Choose);
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
        }

        public void SetInteractable(bool value)
        {
            if (button != null) button.interactable = value;
        }

        public void Hide()
        {
            _optionId = null;
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
            OnChosen?.Invoke(_optionId);
        }
    }
}

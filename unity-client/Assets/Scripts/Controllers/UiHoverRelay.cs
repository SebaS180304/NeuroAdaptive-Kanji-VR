using System;
using UnityEngine;
using UnityEngine.EventSystems;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Reports when a pointer -- the XR ray included, through the XR UI input
    /// module -- enters or leaves this UI element. Added at runtime by
    /// StudioTrialPresenter to the answer cards and the assembly slots, so
    /// the assembly can show hover feedback (28 September, headset pass: the
    /// authored ColorTint hover was a 4 % change, invisible in the headset).
    /// </summary>
    public class UiHoverRelay : MonoBehaviour, IPointerEnterHandler, IPointerExitHandler
    {
        public bool Hovered { get; private set; }
        public event Action<bool> OnHover;

        public void OnPointerEnter(PointerEventData eventData) => Set(true);
        public void OnPointerExit(PointerEventData eventData) => Set(false);

        // A card hidden under the ray never gets its exit event.
        private void OnDisable() => Set(false);

        private void Set(bool value)
        {
            if (Hovered == value) return;
            Hovered = value;
            OnHover?.Invoke(value);
        }
    }
}

using System.Linq;
using NeuroAdaptiveVR.Controllers;
using NeuroAdaptiveVR.Data;
using UnityEngine;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// Headset preview of the room, not part of any session (Sebas, 26 Oct: to judge the rice field, the
    /// silhouettes and the animals). While enabled it holds the ESL at HIGH whatever the flow asks for, switches
    /// the peripheral scheduler off (no random draw, no PERIPHERAL_EVENT telemetry) and shows every animal in
    /// turn, in a fixed order, looping. Set it before Play: never send editor commands during Play (finding P2).
    /// Lives in the demo scene (D-F6-84), off: the room is loaded after the first frame, so the demo director
    /// must switch it on for T5 (J6), never the Inspector. shortcut: for the 30 Oct video only, delete it after.
    /// </summary>
    public class PeripheralPreview : MonoBehaviour
    {
        [SerializeField] private float gapSeconds = 1.5f;

        private EnvironmentalStimulationController _esl;
        private PeripheralAnimation[] _animals;
        private GameObject[] _figures;
        private int _index = -1;
        private float _nextAt;

        private void Start()
        {
            _esl = FindAnyObjectByType<EnvironmentalStimulationController>();
            var scheduler = FindAnyObjectByType<PeripheralEventScheduler>();
            if (scheduler != null) scheduler.enabled = false;
            _animals = GameObject.Find("EnvironmentalLayer").transform.Find("PeripheralEvents")
                .GetComponentsInChildren<PeripheralAnimation>(true).OrderBy(a => a.name, System.StringComparer.Ordinal).ToArray();
            foreach (var a in _animals) a.gameObject.SetActive(false);
            _figures = GameObject.Find("EnvironmentalLayer").transform.Find("Movers").Cast<Transform>()
                .Where(t => t.name.StartsWith("OutsideFigure")).Select(t => t.gameObject).ToArray();
            Debug.Log($"[PeripheralPreview] ESL held at HIGH; {_animals.Length} animals in turn: {string.Join(", ", _animals.Select(a => a.name))}");
        }

        private void Update()
        {
            if (_esl != null && _esl.CurrentLevel != StimulationOrAssistanceLevel.High)
                _esl.SetLevel(StimulationOrAssistanceLevel.High, betweenTrials: true);
            // HIGH draws 2-3 movers from the lowest tier up, so the curtains (T2) come first and a silhouette (T3)
            // shows only when the draw gives 3, and then only one. The preview shows both, walking.
            foreach (var figure in _figures) if (!figure.activeSelf) figure.SetActive(true);
            if (_animals.Length == 0 || Time.time < _nextAt) return;

            if (_index >= 0) _animals[_index].gameObject.SetActive(false);
            _index = (_index + 1) % _animals.Length;
            _animals[_index].gameObject.SetActive(true);   // OnEnable restarts its pose at t = 0
            _nextAt = Time.time + _animals[_index].DurationSeconds + gapSeconds;
        }
    }
}

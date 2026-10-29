using System;
using System.Collections;
using System.Linq;
using NeuroAdaptiveVR.Controllers;
using NeuroAdaptiveVR.Data;
using NeuroAdaptiveVR.Networking;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.SceneManagement;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// Demonstration scene for the 30 Oct video (D-F6-84), not in Build Settings. It loads the experiment scene
    /// additively, so the room is always the current one, and switches the session chain off before any Start runs:
    /// no backend, no session, no telemetry, nothing in the database. The states are fixed in the Inspector before
    /// Play (never send editor commands during Play, finding P2).
    /// </summary>
    public class DemoDirector : MonoBehaviour
    {
        public const string ScenePath = "Assets/Scenes/Demo_Video.unity";
        public const string ExperimentScene = "JapaneseLearningStudio";

        /// <summary>Everything that would open a session, talk to the backend or draw a random event.</summary>
        public static readonly Type[] Silenced =
        {
            typeof(SessionBootstrap), typeof(SessionFlowRunner), typeof(GameFlowController),
            typeof(SessionCommunicationClient), typeof(AdaptationClient), typeof(PeripheralEventScheduler),
            typeof(DebugTrialPresenter),   // its H and digit keys would answer a trial nobody started
        };

        [Tooltip("Label only: with no session nothing reads it; it names the condition the shots stand for.")]
        [SerializeField] private string condition = "BEHAVIOR_ADAPTIVE";
        [SerializeField] private StimulationOrAssistanceLevel esl = StimulationOrAssistanceLevel.Medium;
        [SerializeField] private StimulationOrAssistanceLevel lal = StimulationOrAssistanceLevel.Medium;
        [SerializeField] private string kanji = "火";
        [SerializeField] private int roomSeed = 1;
        [SerializeField] private float cardSeconds = 3f;
        [SerializeField] private string card = "Demonstration scene. States set for the recording.";

        private EnvironmentalStimulationController _room;

        private IEnumerator Start()
        {
            SceneManager.sceneLoaded += Silence;
            yield return SceneManager.LoadSceneAsync(ExperimentScene, LoadSceneMode.Additive);
            SceneManager.sceneLoaded -= Silence;
            // Lighting and skybox come from the active scene.
            SceneManager.SetActiveScene(SceneManager.GetSceneByName(ExperimentScene));

            var content = FindAnyObjectByType<KanjiContentController>();
            if (content != null && !content.IsLoaded) content.Load();
            var item = content != null ? content.ByCharacter(kanji) : null;
            if (item == null) Debug.LogError($"[Demo] Kanji {kanji} is not in the contract.");

            // The room still builds its telemetry events (they stay queued, the client is off); a zero keeps the
            // clock from logging an error on every level change. Enter Play Mode keeps statics, so reset first.
            SessionClock.ResetForNewSession();
            SessionClock.SetSessionZero(DateTime.UtcNow);
            _room = FindAnyObjectByType<EnvironmentalStimulationController>();
            _room.SetSeed(roomSeed);
            _room.SetLevel(esl, betweenTrials: true);
            FindAnyObjectByType<LearningAssistanceController>().SetLevel(lal, betweenTrials: true);
            Debug.Log($"[Demo] {condition} · ESL {esl} · LAL {lal} · kanji {kanji} · seed {roomSeed}");

            var board = FindAnyObjectByType<StudioTrialPresenter>();
            board.ShowMessage(card);
            yield return new WaitForSecondsRealtime(cardSeconds);
            if (item != null) board.ShowExposure(item.Character, item.Meaning, item.TargetReading);
        }

        // L / M / H switch the room; the fixed seed gives the same room at a level on every attempt (plan §2).
        private void Update()
        {
            var k = Keyboard.current;
            if (_room == null || k == null) return;
            if (k.lKey.wasPressedThisFrame) _room.SetLevel(StimulationOrAssistanceLevel.Low, betweenTrials: true);
            if (k.mKey.wasPressedThisFrame) _room.SetLevel(StimulationOrAssistanceLevel.Medium, betweenTrials: true);
            if (k.hKey.wasPressedThisFrame) _room.SetLevel(StimulationOrAssistanceLevel.High, betweenTrials: true);
        }

        // sceneLoaded runs after Awake and OnEnable and before Start, so a component switched off here never starts.
        private static void Silence(Scene scene, LoadSceneMode mode)
        {
            foreach (var root in scene.GetRootGameObjects())
                foreach (var b in root.GetComponentsInChildren<Behaviour>(true).Where(b => Silenced.Contains(b.GetType())))
                    b.enabled = false;
        }
    }
}

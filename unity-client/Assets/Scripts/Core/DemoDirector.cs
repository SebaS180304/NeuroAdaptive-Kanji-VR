using System;
using System.Collections;
using System.Linq;
using NeuroAdaptiveVR.Controllers;
using NeuroAdaptiveVR.Data;
using NeuroAdaptiveVR.Networking;
using Unity.Cinemachine;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
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

        [Tooltip("The cinematic look (D-F6-114): seen only by the recording camera, through its own layer.")]
        [SerializeField] private Volume cineLook;

        /// <summary>The editor's DemoRecording starts the Recorder on this (file stem) and stops it on ShotEnded.</summary>
        public static event Action<string> ShotStarted;
        public static event Action ShotEnded;

        private const float LookFollowRate = 6f;   // 1/s: about 0.4 s to settle on a new focus point

        private EnvironmentalStimulationController _room;
        private StudioTrialPresenter _board;
        private KanjiDiscoveryController _discovery;
        private PronunciationAudioController _voice;
        private KanjiItem _item;
        private DemoShot[] _shots;
        private Coroutine _running;

        private IEnumerator Start()
        {
            SceneManager.sceneLoaded += Silence;
            yield return SceneManager.LoadSceneAsync(ExperimentScene, LoadSceneMode.Additive);
            SceneManager.sceneLoaded -= Silence;
            // Lighting and skybox come from the active scene.
            SceneManager.SetActiveScene(SceneManager.GetSceneByName(ExperimentScene));
            // Untracked (flat run) the controller models sit at the eye, right where the recording cameras start.
            foreach (var hand in new[] { "Left Controller", "Right Controller" }) GameObject.Find(hand)?.SetActive(false);

            var content = FindAnyObjectByType<KanjiContentController>();
            if (content != null && !content.IsLoaded) content.Load();
            var item = _item = content != null ? content.ByCharacter(kanji) : null;
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

            _discovery = FindAnyObjectByType<KanjiDiscoveryController>();
            _voice = FindAnyObjectByType<PronunciationAudioController>();
            _shots = FindObjectsByType<DemoShot>(FindObjectsInactive.Include, FindObjectsSortMode.None);
            var board = _board = FindAnyObjectByType<StudioTrialPresenter>();
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
            // Digit N launches shot TN from its first frame; one shot (one camera) at a time.
            for (int n = 1; n <= 9; n++)
            {
                if (!k[Key.Digit1 + (n - 1)].wasPressedThisFrame) continue;
                var shot = _shots.FirstOrDefault(s => s.number == n);
                if (shot == null) { Debug.LogWarning($"[Demo] No shot T{n} in the scene."); continue; }
                if (_running != null) { Debug.LogWarning("[Demo] A shot is running; wait for it to end."); continue; }
                _running = StartCoroutine(RunShot(shot));
            }
        }

        private IEnumerator RunShot(DemoShot shot)
        {
            foreach (var s in _shots) s.GetComponent<CinemachineCamera>().Priority = s == shot ? 10 : 0;
            var dolly = shot.GetComponent<CinemachineSplineDolly>();
            dolly.CameraPosition = 0f;
            var look = shot.GetComponent<CinemachineCamera>().LookAt;
            if (shot.lookAtFocus && look != null) look.position = FocusPoint(shot);
            yield return null;   // let the brain cut to the shot before the first recorded frame
            ShotStarted?.Invoke(shot.FileStem);
            Debug.Log($"[Demo] {shot.FileStem} · {shot.total:F0} s");

            bool acted = false;
            float t0 = Time.realtimeSinceStartup;
            for (float t = 0f; t < shot.total; t = Time.realtimeSinceStartup - t0)
            {
                dolly.CameraPosition = DemoShot.Position(t, shot.moveStart, shot.moveEnd, shot.returnHome);
                // Eased, so the cut from the board to the object (they are 0.1 m apart when it appears) is a glide.
                if (shot.lookAtFocus && look != null)
                    look.position = Vector3.Lerp(look.position, FocusPoint(shot), 1f - Mathf.Exp(-LookFollowRate * Time.deltaTime));
                if (cineLook != null && cineLook.profile.TryGet(out DepthOfField dof))
                    dof.focusDistance.value = Vector3.Distance(shot.transform.position, FocusPoint(shot));
                if (!acted && t >= shot.actionAt) { acted = true; Act(shot.action); }
                yield return null;
            }

            ShotEnded?.Invoke();
            _discovery?.Hide();
            if (_item != null) _board.ShowExposure(_item.Character, _item.Meaning, _item.TargetReading);
            _running = null;
        }

        // A set focus wins; otherwise the board until the object appears on it, then the object (Sebas, 29 Oct).
        private Vector3 FocusPoint(DemoShot shot)
        {
            if (shot.focus != null) return shot.focus.position;
            var obj = _discovery != null ? _discovery.Spawned : null;
            if (obj == null) return _discovery != null ? _discovery.transform.position : _board.transform.position;   // the discovery controller sits on LearningBoard
            var rs = obj.GetComponentsInChildren<Renderer>();
            return rs.Length > 0 ? rs.Aggregate(rs[0].bounds, (b, r) => { b.Encapsulate(r.bounds); return b; }).center : obj.position;
        }

        private void Act(DemoShot.Action action)
        {
            if (action != DemoShot.Action.ObjectApproach || _item == null || _discovery == null) return;
            // As S5 stage 1 (D-F6-49): the object comes close, levitates while the reading plays, and goes back.
            if (!_discovery.ShowStage(_item, 1)) return;
            // Unlike S5, the board keeps the kanji, its meaning and reading in view (Sebas, 29 Oct).
            _board.ShowExposure(_item.Character, _item.Meaning, _item.TargetReading);
            StartCoroutine(_discovery.Approach(() => _voice?.PlayInitialExposure(_item)));
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

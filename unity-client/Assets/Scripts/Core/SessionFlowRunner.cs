using System.Collections;
using System.Collections.Generic;
using System.Linq;
using NeuroAdaptiveVR.Controllers;
using NeuroAdaptiveVR.Data;
using NeuroAdaptiveVR.Networking;
using UnityEngine;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// Runs a whole session, S1 to S9, in one scene (plan front B2, spec 7).
    ///
    /// WHAT IT OWNS, AND WHAT IT DOES NOT
    /// ----------------------------------
    /// It owns the ORDER of the session's contents: what happens inside each
    /// state and when to move on. It does not own the state itself
    /// (GameFlowController does, and applies the Appendix A levels on entry),
    /// the trial cycle (ResponseSystemController), the board
    /// (StudioTrialPresenter), or the sequences (TrialSequenceGenerator).
    /// Every one of those already existed and was verified; this component
    /// only calls them in order. If a bug fix ever lands here that belongs to
    /// one of them, something drifted.
    ///
    /// WHEN IT STARTS
    /// --------------
    /// When S1 is entered, which SessionBootstrap does once the WebSocket is
    /// open -- that is, AFTER the session has been installed from the
    /// backend. Plans are built at that moment and not in Awake. TrialDebugRunner
    /// built its items in Awake and on 24 September loaded set B while the
    /// session said A; the chain cannot have that failure because it never
    /// looks at the set before the session exists.
    ///
    /// DECISIONS TAKEN WITH SEBAS ON 24 SEPTEMBER
    /// ------------------------------------------
    /// - S1: the participant starts with a "Start" card, ray + trigger. That
    ///   choice is START_SELECTED.
    /// - S2: "look &amp; select" only -- three practice trials with the tutorial
    ///   pool through the real response cycle. Grab &amp; place comes with assembly.
    /// - S3: if the headset or the WebSocket is missing, the session STOPS and
    ///   says why. A researcher can force the advance from the context menu,
    ///   and the forcing is recorded.
    /// - S4: real 60 s + 45 s by default, with a debug time scale that travels
    ///   in BASELINE_COMPLETED.
    /// - S6 = 9 trials (3 per type), S7 = 20, S8 = 15 without feedback.
    /// </summary>
    [RequireComponent(typeof(GameFlowController))]
    public class SessionFlowRunner : MonoBehaviour
    {
        private const string Log = "[SessionFlow]";
        private const string StartOptionId = "START";

        [Header("Dependencies (found automatically if empty)")]
        [SerializeField] private GameFlowController flow;
        [SerializeField] private ResponseSystemController responses;
        [SerializeField] private KanjiContentController content;
        [SerializeField] private BehaviorTelemetryController telemetry;
        [SerializeField] private SessionCommunicationClient client;
        [Tooltip("The board. Session messages and the Start card go through it: it is the board's only owner.")]
        [SerializeField] private StudioTrialPresenter board;
        [Tooltip("Any MonoBehaviour implementing ILearningBlock. Empty = S5 is crossed with a labelled placeholder.")]
        [SerializeField] private MonoBehaviour learningBlockBehaviour;
        [Tooltip("Recenters the view when the session starts. Empty = no automatic recenter.")]
        [SerializeField] private ViewRecenter viewRecenter;

        [Header("Start")]
        [Tooltip("Start the chain when S1 is entered. Off = only from the context menu.")]
        [SerializeField] private bool runOnSessionStart = true;

        [Header("Trial blocks (spec 6.1)")]
        [SerializeField] private int tutorialTrials = 3;
        [SerializeField] private int s6Trials = 9;
        [SerializeField] private int s7Trials = 20;
        [SerializeField] private int s8Trials = 15;
        [Tooltip("Minimum lag between two appearances of the same kanji (decided 16 Sep).")]
        [SerializeField] private int minLag = 2;

        [Header("Timing -- TO VALIDATE with the pilot")]
        [SerializeField] private float transitionSeconds = 1.5f;
        [Tooltip("How long S3 keeps checking before declaring a failure.")]
        [SerializeField] private float systemCheckWindowSeconds = 5f;
        [SerializeField] private float baselineEyesOpenSeconds = 60f;
        [SerializeField] private float baselineEyesClosedSeconds = 45f;
        [Tooltip("DEBUG ONLY. Multiplies the S4 durations. Travels in BASELINE_COMPLETED, " +
                 "so a shortened baseline can never pass for a real one.")]
        [Range(0.01f, 1f)]
        [SerializeField] private float baselineTimeScale = 1f;
        [SerializeField] private float s5PlaceholderSeconds = 3f;

        [Header("Debug fallbacks (the session wins when it has them)")]
        [SerializeField] private string fallbackSet = "A";
        [SerializeField] private int fallbackSeed = 20260909;

        private readonly List<KanjiItem> _set = new();
        private string _setName;
        private int _sessionSeed;

        private bool _running;
        private bool _forceAdvance;
        private string _lastChoice;
        private TrialResult _lastResult;
        private bool _trialClosed;
        private AudioSource _chime;

        private readonly Dictionary<GameFlowState, (int correct, int total)> _scores = new();

        public bool IsRunning => _running;

        // ------------------------------------------------------------------
        // Lifecycle
        // ------------------------------------------------------------------

        private void Awake()
        {
            if (flow == null) flow = GetComponent<GameFlowController>();
            if (responses == null) responses = GetComponent<ResponseSystemController>();
            if (content == null) content = FindAnyObjectByType<KanjiContentController>();
            if (telemetry == null) telemetry = GetComponent<BehaviorTelemetryController>();
            if (client == null) client = GetComponent<SessionCommunicationClient>();
            if (board == null) board = FindAnyObjectByType<StudioTrialPresenter>();
            if (viewRecenter == null) viewRecenter = FindAnyObjectByType<ViewRecenter>();
        }

        /// <summary>
        /// What the PARTICIPANT reads at the top of the board. Deliberately not
        /// the spec names (decided 24 September):
        /// - "Experimental Retrieval" would reveal the manipulation, so S6 and
        ///   S7 are both "Practice": to the participant they are the same task.
        /// - "Assessment" or "Test" invites evaluation anxiety exactly in S8,
        ///   the primary learning measure, so it is "Final round".
        /// </summary>
        private static readonly Dictionary<GameFlowState, string> StageTitles = new()
        {
            [GameFlowState.S1_WelcomeOrientation]        = "Welcome",
            [GameFlowState.S2_VRTutorial]                = "Controls practice",
            [GameFlowState.S3_SystemValidation]          = "System check",
            [GameFlowState.S4_EEGBaseline]               = "Rest",
            [GameFlowState.S5_StandardizedLearning]      = "Learn",
            [GameFlowState.S6_GuidedPracticeCalibration] = "Practice",
            [GameFlowState.S7_ExperimentalRetrieval]     = "Practice",
            [GameFlowState.S8_ImmediateAssessment]       = "Final round",
            [GameFlowState.S9_SessionSummary]            = "Complete",
        };

        private void AnnounceStage(GameFlowState state)
        {
            if (board == null) return;

            // N comes from GameFlowController, which owns the S2 skip rule: the
            // counter cannot say "of 9" in a session that runs eight states.
            var states = flow.SessionStates();
            int step = 0;
            for (int i = 0; i < states.Count; i++)
                if (states[i] == state) { step = i + 1; break; }

            string name = StageTitles.TryGetValue(state, out var t) ? t : string.Empty;
            board.SetStageTitle(step > 0 ? $"Step {step} of {states.Count} · {name}" : name);
        }

        private void OnEnable()
        {
            if (flow != null) flow.OnStateEntered += HandleStateEntered;
            if (responses != null) responses.OnTrialCompleted += HandleTrialCompleted;
            if (board != null) board.OnOptionChosen += HandleBoardChoice;
        }

        private void OnDisable()
        {
            if (flow != null) flow.OnStateEntered -= HandleStateEntered;
            if (responses != null) responses.OnTrialCompleted -= HandleTrialCompleted;
            if (board != null) board.OnOptionChosen -= HandleBoardChoice;
        }

        private void HandleStateEntered(GameFlowState state)
        {
            if (_running || !runOnSessionStart) return;
            if (state == GameFlowState.S1_WelcomeOrientation) StartCoroutine(RunSession());
        }

        private void HandleTrialCompleted(TrialResult result)
        {
            _lastResult = result;
            _trialClosed = true;
        }

        private void HandleBoardChoice(string optionId) => _lastChoice = optionId;

        // ------------------------------------------------------------------
        // Researcher controls
        // ------------------------------------------------------------------

        [ContextMenu("Start session chain")]
        private void StartFromMenu()
        {
            if (_running) { Debug.LogWarning($"{Log} Already running."); return; }
            if (flow.CurrentState == GameFlowState.S0_SessionInitialization)
                flow.AdvanceToNextState();   // enters S1, whose handler starts the chain
            else
                StartCoroutine(RunSession());
        }

        /// <summary>
        /// Researcher override for a state that is waiting (S1 without a choice,
        /// S3 with a failed check). Recorded wherever it is consumed.
        /// </summary>
        [ContextMenu("Force advance (researcher)")]
        public void ForceAdvance()
        {
            Debug.LogWarning($"{Log} Researcher forced the advance of {flow.CurrentState}.");
            _forceAdvance = true;
        }

        // ------------------------------------------------------------------
        // The chain
        // ------------------------------------------------------------------

        private IEnumerator RunSession()
        {
            _running = true;
            _scores.Clear();

            if (!ResolveSetAndSeed())
            {
                Show("This session cannot start.\nSee the console.");
                _running = false;
                yield break;
            }

            Debug.Log($"{Log} Session chain started · set {_setName} · session seed {_sessionSeed} · " +
                      $"visit {(SessionContext.IsInstalled ? SessionContext.VisitNumber.ToString() : "?")}");

            while (true)
            {
                var state = flow.CurrentState;
                AnnounceStage(state);
                bool ok = true;
                yield return RunState(state, r => ok = r);

                if (!ok)
                {
                    Debug.LogError($"{Log} {state} could not complete. The chain stops here; " +
                                   "the session row stays IN_PROGRESS, which is the truth.");
                    _running = false;
                    yield break;
                }

                if (state == GameFlowState.S9_SessionSummary) break;

                board?.Clear();
                yield return new WaitForSecondsRealtime(transitionSeconds);
                flow.AdvanceToNextState();
            }

            Debug.Log($"{Log} Session complete. " + string.Join(" · ",
                _scores.Select(kv => $"{kv.Key.ShortCode()} {kv.Value.correct}/{kv.Value.total}")));
            _running = false;
        }

        private IEnumerator RunState(GameFlowState state, System.Action<bool> done)
        {
            switch (state)
            {
                case GameFlowState.S1_WelcomeOrientation:        yield return RunWelcome(); break;
                case GameFlowState.S2_VRTutorial:                yield return RunTutorial(done); yield break;
                case GameFlowState.S3_SystemValidation:          yield return RunSystemCheck(); break;
                case GameFlowState.S4_EEGBaseline:               yield return RunBaseline(); break;
                case GameFlowState.S5_StandardizedLearning:      yield return RunLearning(); break;
                case GameFlowState.S6_GuidedPracticeCalibration: yield return RunBlock(state, _set, s6Trials, true, done); yield break;
                case GameFlowState.S7_ExperimentalRetrieval:     yield return RunBlock(state, _set, s7Trials, true, done); yield break;
                // S8 defers feedback: it is the primary learning measure, and
                // showing the answer would contaminate the trials after it.
                case GameFlowState.S8_ImmediateAssessment:       yield return RunBlock(state, _set, s8Trials, false, done); yield break;
                case GameFlowState.S9_SessionSummary:            RunSummary(); break;
                default:
                    Debug.LogError($"{Log} No content for {state}.");
                    done(false);
                    yield break;
            }
            done(true);
        }

        // ------------------------------------------------------------------
        // S1 -- Welcome & Orientation (spec 7.2)
        // ------------------------------------------------------------------

        private IEnumerator RunWelcome()
        {
            _lastChoice = null;
            _forceAdvance = false;

            // Every participant starts from the designed pose, however the
            // headset was put on (spec 7.2, "appears at the central station").
            if (viewRecenter != null) viewRecenter.Recenter("SESSION_START");

            Show("Today you will learn five new kanji.\n\nLook at the panel to begin.\n\n" +
                 "<size=60%>If the view feels off at any time,\npress the menu button on the left controller.</size>");
            board?.ShowSingleChoice(StartOptionId, "Start");
            float shownAt = Time.realtimeSinceStartup;

            yield return new WaitUntil(() => _lastChoice == StartOptionId || _forceAdvance);

            long reactionMs = (long)((Time.realtimeSinceStartup - shownAt) * 1000f);
            bool forced = _lastChoice != StartOptionId;
            _forceAdvance = false;

            telemetry.Emit(TelemetryEvents.StartSelected, new Dictionary<string, object>
            {
                { "reaction_ms", reactionMs },
                { "forced_by_researcher", forced },
            });
            Debug.Log($"{Log} S1 · Start {(forced ? "FORCED by researcher" : "selected")} after {reactionMs} ms");
        }

        // ------------------------------------------------------------------
        // S2 -- VR Tutorial, "look & select" only (spec 7.3)
        // ------------------------------------------------------------------

        private IEnumerator RunTutorial(System.Action<bool> done)
        {
            var pool = content.Tutorial;
            telemetry.Emit(TelemetryEvents.TutorialStarted, new Dictionary<string, object>
            {
                { "activities", new List<string> { "LOOK_AND_SELECT" } },
                { "pool", pool.Select(i => i.KanjiId).ToList() },
            });

            Show("Practice\n\nPoint at an answer and pull the trigger.");
            yield return new WaitForSecondsRealtime(3f);

            bool ok = true;
            yield return RunBlock(GameFlowState.S2_VRTutorial, pool, tutorialTrials, true, r => ok = r);

            _scores.TryGetValue(GameFlowState.S2_VRTutorial, out var s);
            telemetry.Emit(TelemetryEvents.TutorialCompleted, new Dictionary<string, object>
            {
                { "trials", s.total },
                { "correct", s.correct },
            });
            done(ok);
        }

        // ------------------------------------------------------------------
        // S3 -- System Validation (spec 7.4)
        // ------------------------------------------------------------------

        private IEnumerator RunSystemCheck()
        {
            _forceAdvance = false;
            Show("Checking the system...");

            bool headset = false, websocket = false;
            float until = Time.realtimeSinceStartup + systemCheckWindowSeconds;
            while (Time.realtimeSinceStartup < until)
            {
                headset = XRRuntimeGuard.HeadsetActive;
                websocket = client != null && client.IsConnected;
                if (headset && websocket) break;
                yield return null;
            }

            bool passed = headset && websocket;
            bool forced = false;

            if (!passed)
            {
                string why = (headset ? "" : "no headset (XR is not running) · ") +
                             (websocket ? "" : "backend WebSocket disconnected");
                Debug.LogError($"{Log} S3 FAILED: {why.TrimEnd(' ', '·')}. The session waits. " +
                               "Fix it, or use 'Force advance (researcher)' on SessionFlowRunner -- " +
                               "the override is recorded.");
                Show("Please wait.\nThe researcher is checking the equipment.");
                yield return new WaitUntil(() => _forceAdvance);
                _forceAdvance = false;
                forced = true;
            }

            telemetry.Emit(TelemetryEvents.SystemCheckCompleted, new Dictionary<string, object>
            {
                { "headset_active", headset },
                { "websocket_connected", websocket },
                { "passed", passed },
                { "forced_by_researcher", forced },
                // WAVEX is Phase 4. Saying so explicitly beats omitting it: an
                // absent field reads as "not checked for an unknown reason".
                { "eeg_checked", false },
            });
            Debug.Log($"{Log} S3 · headset {headset} · websocket {websocket} · " +
                      (passed ? "PASSED" : "FORCED by researcher"));
        }

        // ------------------------------------------------------------------
        // S4 -- EEG Baseline, 60 s eyes open + 45 s eyes closed (spec 7.5)
        // ------------------------------------------------------------------

        private IEnumerator RunBaseline()
        {
            float open = baselineEyesOpenSeconds * baselineTimeScale;
            float closed = baselineEyesClosedSeconds * baselineTimeScale;

            if (baselineTimeScale < 1f)
                Debug.LogWarning($"{Log} S4 baseline SHORTENED x{baselineTimeScale} (debug). " +
                                 "Recorded in BASELINE_COMPLETED; this session's baseline is not valid.");

            telemetry.Emit(TelemetryEvents.BaselineStarted, new Dictionary<string, object>
            {
                { "eyes_open_s", baselineEyesOpenSeconds },
                { "eyes_closed_s", baselineEyesClosedSeconds },
                { "time_scale", baselineTimeScale },
            });

            float t0 = Time.realtimeSinceStartup;
            Show("Relax and look forward.");
            yield return new WaitForSecondsRealtime(open);
            float t1 = Time.realtimeSinceStartup;

            // The participant cannot read the board with the eyes closed, so
            // the END of the closed segment has to be a sound. The chime marks
            // both edges so the two segments are symmetric for the participant.
            Show("Close your eyes.\nOpen them when you hear the chime.");
            PlayChime();
            yield return new WaitForSecondsRealtime(closed);
            PlayChime();
            float t2 = Time.realtimeSinceStartup;

            telemetry.Emit(TelemetryEvents.BaselineCompleted, new Dictionary<string, object>
            {
                { "eyes_open_ms", (long)((t1 - t0) * 1000f) },
                { "eyes_closed_ms", (long)((t2 - t1) * 1000f) },
                { "time_scale", baselineTimeScale },
                { "valid_duration", baselineTimeScale >= 1f },
            });
            Debug.Log($"{Log} S4 · baseline done ({(t2 - t0):0.0} s, scale {baselineTimeScale})");
        }

        // ------------------------------------------------------------------
        // S5 -- Standardized Learning Block (spec 7.6)
        // ------------------------------------------------------------------

        private IEnumerator RunLearning()
        {
            if (learningBlockBehaviour is ILearningBlock block)
            {
                yield return block.Run(_set, _sessionSeed);
                yield break;
            }

            Debug.LogWarning($"{Log} S5 has no learning block assigned (front B3). Crossed with a " +
                             "placeholder: NO learning content was shown, so this session's S6-S8 " +
                             "measure recognition of kanji that were never taught.");
            Show("Learning block\n(not built yet)");
            yield return new WaitForSecondsRealtime(s5PlaceholderSeconds);
        }

        // ------------------------------------------------------------------
        // S6 / S7 / S8 (and the S2 tutorial) -- trial blocks
        // ------------------------------------------------------------------

        private IEnumerator RunBlock(GameFlowState state, IReadOnlyList<KanjiItem> items,
                                     int count, bool immediateFeedback, System.Action<bool> done)
        {
            if (items == null || items.Count < 4)
            {
                Debug.LogError($"{Log} {state.ShortCode()} needs at least 4 kanji for four distinct " +
                               $"options (spec 9.3); got {items?.Count ?? 0}.");
                done(false);
                yield break;
            }

            int blockSeed = TrialSequenceGenerator.BlockSeed(_sessionSeed, state);
            var plan = TrialSequenceGenerator.Build(state, items, count, minLag, blockSeed);
            if (plan.Count == 0) { done(false); yield break; }

            TrialSequenceTelemetry.Emit(telemetry, plan, _setName, _sessionSeed);

            int correct = 0;
            foreach (var planned in plan.Trials)
            {
                _trialClosed = false;
                _lastResult = null;

                responses.BeginTrial(planned.ToRequest(immediateFeedback));

                // BeginTrial rejects malformed trials with an error and opens
                // nothing. Without this check the chain would wait forever for
                // a trial that never existed.
                if (!responses.TrialInProgress && !_trialClosed)
                {
                    Debug.LogError($"{Log} {state.ShortCode()}-{planned.Sequence:D3} did not open.");
                    done(false);
                    yield break;
                }

                yield return new WaitUntil(() => _trialClosed);
                if (_lastResult != null && _lastResult.IsCorrect) correct++;
            }

            _scores[state] = (correct, plan.Count);
            Debug.Log($"{Log} {state.ShortCode()} · {correct}/{plan.Count} correct");
            done(true);
        }

        // ------------------------------------------------------------------
        // S9 -- Session Summary (spec 7.x): a NEUTRAL message
        // ------------------------------------------------------------------

        private void RunSummary()
        {
            // No score on the board. Spec asks for a neutral completion
            // message; showing performance would colour the S10 self-report
            // the participant fills in right after taking the headset off.
            Show("The session is complete.\n\nThank you. You can take off the headset.");
        }

        // ------------------------------------------------------------------
        // Helpers
        // ------------------------------------------------------------------

        private bool ResolveSetAndSeed()
        {
            _set.Clear();

            if (content == null)
            {
                Debug.LogError($"{Log} No KanjiContentController in the scene.");
                return false;
            }
            if (!content.IsLoaded && !content.Load()) return false;

            bool fromSession = SessionContext.IsInstalled && SessionContext.AssignedKanjiSet != null;
            _setName = fromSession ? SessionContext.AssignedKanjiSet : fallbackSet;
            _sessionSeed = SessionContext.IsInstalled && SessionContext.RandomSeedRaw != null
                ? SessionContext.Seed
                : fallbackSeed;

            if (!fromSession)
                Debug.LogWarning($"{Log} The session has no assigned_kanji_set; using the debug " +
                                 $"fallback '{fallbackSet}'. This run is NOT reconstructible.");

            _set.AddRange(content.Set(_setName));
            if (_set.Count == 0)
            {
                Debug.LogError($"{Log} Set '{_setName}' came back empty from the contract.");
                return false;
            }
            return true;
        }

        private void Show(string text)
        {
            if (board != null) board.ShowMessage(text);
            else Debug.Log($"{Log} [board] {text.Replace('\n', ' ')}");
        }

        private void PlayChime()
        {
            if (_chime == null)
            {
                _chime = gameObject.AddComponent<AudioSource>();
                _chime.playOnAwake = false;
                _chime.spatialBlend = 0f;
                _chime.clip = BuildChime();
            }
            _chime.Play();
        }

        /// <summary>A 0.4 s, 880 Hz tone with a soft envelope. Procedural so
        /// S4 does not depend on an authored asset that does not exist yet.</summary>
        private static AudioClip BuildChime()
        {
            const int rate = 44100;
            const float seconds = 0.4f;
            int n = (int)(rate * seconds);
            var data = new float[n];
            for (int i = 0; i < n; i++)
            {
                float t = (float)i / rate;
                float env = Mathf.Min(1f, t / 0.02f) * Mathf.Exp(-t * 6f);
                data[i] = 0.35f * env * Mathf.Sin(2f * Mathf.PI * 880f * t);
            }
            var clip = AudioClip.Create("S4Chime", n, 1, rate, false);
            clip.SetData(data, 0);
            return clip;
        }
    }
}

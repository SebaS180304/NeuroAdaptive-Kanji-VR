using System.Collections;
using System.Collections.Generic;
using NeuroAdaptiveVR.Controllers;
using NeuroAdaptiveVR.Data;
using UnityEngine;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// S5 -- Standardized Learning Block (spec 7.6), version 1.
    ///
    /// For each of the five kanji, in set order:
    ///
    ///   object -> transformation -> reveal -> meaning -> reading -> audio
    ///   -> [assembly] -> guided association
    ///
    /// SCOPE OF VERSION 1 (agreed 24 September, Replan_Cierre_M2_24sep.md §5)
    /// ---------------------------------------------------------------------
    /// - Stages 1-3 of the derivation: labelled placeholders ON THE BOARD
    ///   (moved from the Object Area on 25 September, see
    ///   KanjiDiscoveryController), unless authored content exists.
    /// - Stage 4, meaning and reading: real, from the contract, on the board.
    /// - Audio: whatever clip the item carries. Today that is a TTS
    ///   placeholder; KANJI_EXPOSED records which, so a synthetic clip is
    ///   never mistaken for a recording.
    /// - Assembly: NOT in this version. Skipped, and recorded as skipped in
    ///   KANJI_EXPOSED, so the build delivered on the 25th has no half-built step.
    /// - Guided association: real. One trial per kanji through the same
    ///   response cycle as S6-S8, type drawn from the seed (decision D3).
    ///
    /// Pacing is FIXED, not participant-driven: every participant gets the same
    /// exposure (spec 7.6, "all participants receive equivalent initial
    /// instruction"). The durations are decision D5 and are TO VALIDATE with
    /// the pilot -- they are Inspector fields for that reason, not constants.
    ///
    /// This component orders the steps and waits. It draws nothing itself:
    /// what each derivation stage shows is KanjiDiscoveryController's call,
    /// the board is StudioTrialPresenter's, audio to PronunciationAudioController, trials to
    /// ResponseSystemController.
    /// </summary>
    public class S5LearningBlockController : MonoBehaviour, ILearningBlock
    {
        private const string Log = "[S5]";

        [Header("Dependencies (found automatically if empty)")]
        [SerializeField] private StudioTrialPresenter board;
        [SerializeField] private KanjiDiscoveryController discovery;
        [SerializeField] private PronunciationAudioController pronunciation;
        [SerializeField] private ResponseSystemController responses;
        [SerializeField] private BehaviorTelemetryController telemetry;

        [Header("Timing -- D5, TO VALIDATE with the pilot")]
        [SerializeField] private float derivationStageSeconds = 2f;
        [SerializeField] private float glyphSeconds = 1.5f;
        [SerializeField] private float meaningSeconds = 2f;
        [Tooltip("Reading stays on the board this long AFTER its audio ends.")]
        [SerializeField] private float readingSeconds = 2f;
        [Tooltip("Blank board between one kanji's association and the next kanji's object. " +
                 "3 s since 25 September: at 1 s the next kanji arrived before the last one settled.")]
        [SerializeField] private float betweenKanjiSeconds = 3f;

        private bool _trialClosed;
        private TrialResult _lastResult;

        private void Awake()
        {
            if (board == null) board = FindAnyObjectByType<StudioTrialPresenter>();
            if (discovery == null) discovery = FindAnyObjectByType<KanjiDiscoveryController>();
            if (pronunciation == null) pronunciation = GetComponent<PronunciationAudioController>();
            if (responses == null) responses = GetComponent<ResponseSystemController>();
            if (telemetry == null) telemetry = GetComponent<BehaviorTelemetryController>();
        }

        private void OnEnable()
        {
            if (responses != null) responses.OnTrialCompleted += HandleTrialCompleted;
        }

        private void OnDisable()
        {
            if (responses != null) responses.OnTrialCompleted -= HandleTrialCompleted;
        }

        private void HandleTrialCompleted(TrialResult r)
        {
            _lastResult = r;
            _trialClosed = true;
        }

        public IEnumerator Run(IReadOnlyList<KanjiItem> set, string setName, int sessionSeed)
        {
            var state = GameFlowState.S5_StandardizedLearning;
            int blockSeed = TrialSequenceGenerator.BlockSeed(sessionSeed, state);
            var plan = TrialSequenceGenerator.BuildOnePerKanji(state, set, blockSeed);
            if (plan.Count != set.Count)
            {
                Debug.LogError($"{Log} The association plan has {plan.Count} trials for {set.Count} kanji. " +
                               "S5 is crossed without association.");
            }
            else
            {
                // Planned before the first exposure, like every other block:
                // the plan is what was intended, the trials are what happened.
                TrialSequenceTelemetry.Emit(telemetry, plan, setName, sessionSeed);
            }

            int correct = 0;
            for (int i = 0; i < set.Count; i++)
            {
                var item = set[i];
                Debug.Log($"{Log} {i + 1}/{set.Count} · {item} · exposure");

                // ---- Stages 1-3, on the board (since 25 September) -----------
                // Same spot as the glyph of stage 4: the object becomes the
                // character in place, and the head never has to turn.
                string progress = $"kanji {i + 1} of {set.Count}";

                var stageMs = new List<long>(KanjiDiscoveryController.StageCount);
                int authored = 0;
                float t0 = Time.realtimeSinceStartup;

                for (int stage = 1; stage < KanjiDiscoveryController.StageCount; stage++)
                {
                    float ts = Time.realtimeSinceStartup;
                    if (discovery != null && discovery.ShowStage(item, stage, progress)) authored++;
                    yield return new WaitForSecondsRealtime(derivationStageSeconds);
                    stageMs.Add(Ms(ts));
                }
                discovery?.Hide();

                // ---- Stage 4: the character, then meaning, then reading ----
                float t4 = Time.realtimeSinceStartup;
                board?.ShowExposure(item.Character);
                yield return new WaitForSecondsRealtime(glyphSeconds);
                stageMs.Add(Ms(t4));
                authored++;   // stage 4 is the real glyph: always "authored"

                board?.ShowExposure(item.Character, item.Meaning);
                yield return new WaitForSecondsRealtime(meaningSeconds);

                board?.ShowExposure(item.Character, item.Meaning, item.TargetReading);
                AudioClip clip = pronunciation != null ? pronunciation.PlayInitialExposure(item) : null;
                if (clip != null) yield return new WaitForSecondsRealtime(clip.length);
                yield return new WaitForSecondsRealtime(readingSeconds);

                telemetry?.Emit(TelemetryEvents.KanjiExposed, new Dictionary<string, object>
                {
                    { TelemetryContract.KeyKanjiId, item.KanjiId },
                    { "kanji_char", item.Character },
                    { "exposure_index", i + 1 },
                    { "discovery_type", item.Content.DiscoveryTypeRaw },
                    { "exposure_ms", Ms(t0) },
                    { "stage_ms", stageMs },
                    { "stages_authored", authored },
                    { "audio_played", clip != null && pronunciation != null },
                    { "audio_source", PronunciationAudioController.SourceOf(clip) },
                    // Spec 7.6 puts guided assembly here. Version 1 skips it on
                    // purpose (agreed 24 Sep); saying so in the row keeps a
                    // missing step from reading as a lost event.
                    { "assembly", "NOT_IMPLEMENTED" },
                });

                // ---- Guided association (D3) -------------------------------
                if (i < plan.Count)
                {
                    _trialClosed = false;
                    _lastResult = null;
                    responses.BeginTrial(plan.Trials[i].ToRequest(immediateFeedback: true));

                    if (!responses.TrialInProgress && !_trialClosed)
                    {
                        Debug.LogError($"{Log} S5-{i + 1:D3} did not open; continuing without it.");
                    }
                    else
                    {
                        yield return new WaitUntil(() => _trialClosed);
                        if (_lastResult != null && _lastResult.IsCorrect) correct++;
                    }
                }

                board?.Clear();
                yield return new WaitForSecondsRealtime(betweenKanjiSeconds);
            }

            Debug.Log($"{Log} Block done · association {correct}/{plan.Count} correct");
        }

        private static long Ms(float since) => (long)((Time.realtimeSinceStartup - since) * 1000f);
    }
}

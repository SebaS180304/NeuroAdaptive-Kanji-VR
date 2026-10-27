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
    ///   -> assembly -> guided association
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
    /// - Assembly: with the ray, through KanjiAssemblyController (added after
    ///   the 25 September cut-off build, which skipped it). Without that
    ///   component the step is skipped and KANJI_EXPOSED records it.
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
        [Tooltip("Guided assembly (spec 5.3). Empty = the step is skipped and KANJI_EXPOSED says so.")]
        [SerializeField] private KanjiAssemblyController assembly;
        [SerializeField] private PronunciationAudioController pronunciation;
        [SerializeField] private ResponseSystemController responses;
        [SerializeField] private BehaviorTelemetryController telemetry;

        [Header("Timing -- D5, TO VALIDATE with the pilot")]
        [Tooltip("Stage 1 without the approach: how long the object (or its placeholder) stays before C3.")]
        [SerializeField] private float derivationStageSeconds = 2f;
        [SerializeField] private float meaningSeconds = 2f;
        [Tooltip("Reading stays on the board this long AFTER its audio ends.")]
        [SerializeField] private float readingSeconds = 2f;
        [Tooltip("Blank board between one kanji's association and the next kanji's object. " +
                 "3 s since 25 September: at 1 s the next kanji arrived before the last one settled.")]
        [SerializeField] private float betweenKanjiSeconds = 3f;

        [Tooltip("D-F6-49: stage 1 brings the object to 0.72 m, levitating, and plays its reading 3 times (8 s). " +
                 "ON for the 23 Oct test (D-F6-58); with it off, stage 1 stays as before.")]
        [SerializeField] private bool objectApproach = false;

        private bool _trialClosed;
        private TrialResult _lastResult;

        private void Awake()
        {
            if (board == null) board = FindAnyObjectByType<StudioTrialPresenter>();
            if (discovery == null) discovery = FindAnyObjectByType<KanjiDiscoveryController>();
            if (assembly == null) assembly = FindAnyObjectByType<KanjiAssemblyController>();
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

                int objectAudioPlays = 0;
                float ts = Time.realtimeSinceStartup;
                bool shown = discovery != null && discovery.ShowStage(item, 1, progress);
                if (objectApproach && shown)
                    yield return discovery.Approach(() => { pronunciation?.PlayInitialExposure(item); objectAudioPlays++; });
                else
                    yield return new WaitForSecondsRealtime(derivationStageSeconds);
                stageMs.Add(Ms(ts));

                // ---- Stages 2-4, C3 (D-F6-64, D-F6-90; Diseno_UI_Kanji_Studio_v1.md §10) ----
                // Object → form 1 → form 2 → kanji in one 7.8 s sequence with the summary strip at the end,
                // the same in every condition and level. stage_ms keeps four entries: stage 2 runs from
                // the start of C3 to the form 1 → form 2 transition, stage 3 to the form 2 → kanji
                // transition, stage 4 to the end of C3 (it replaces the 1.5 s glyph of before).
                var stageSources = new List<string>
                {
                    shown ? HintCells.Authored : HintCells.Placeholder,
                    item.TransformationForm1Sprite != null ? HintCells.Authored : HintCells.Placeholder,
                    item.TransformationForm2Sprite != null ? HintCells.Authored : HintCells.Placeholder,
                    HintCells.Authored,   // stage 4 is the real glyph
                };
                foreach (var source in stageSources) if (source == HintCells.Authored) authored++;
                bool strip = board != null && board.BeginC3(item, progress);
                float c0 = Time.realtimeSinceStartup;
                var marks = new List<float> { c0 };
                long stripOnsetMs = -1;
                for (float t = 0f; t < C3Timeline.TotalSeconds; t = Time.realtimeSinceStartup - c0)
                {
                    board?.SetC3(t);
                    discovery?.SetObjectScale(C3Timeline.ObjectScale(t));
                    if (marks.Count == 1 && t >= C3Timeline.FormToFormStart) marks.Add(c0 + t);
                    if (marks.Count == 2 && t >= C3Timeline.FormToKanjiStart) marks.Add(c0 + t);
                    if (strip && stripOnsetMs < 0 && t >= C3Timeline.StripIn) stripOnsetMs = Ms(t0);
                    yield return null;
                }
                board?.EndC3();
                discovery?.Hide();
                float c1 = Time.realtimeSinceStartup;
                while (marks.Count < 3) marks.Add(c1);
                stageMs.Add((long)((marks[1] - marks[0]) * 1000f));
                stageMs.Add((long)((marks[2] - marks[1]) * 1000f));
                stageMs.Add((long)((c1 - marks[2]) * 1000f));

                // ---- Then meaning, then reading ----

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
                    // D-F6-64, D-F6-91, D-F6-104: where each stage came from, the summary strip and the transition.
                    { "stage_asset_source", stageSources },
                    { "summary_strip_onset_ms", stripOnsetMs >= 0 ? stripOnsetMs : (object)null },
                    { "summary_strip_ms", stripOnsetMs >= 0 ? (long)((c1 - t0) * 1000f) - stripOnsetMs : 0L },
                    { "c3_transition", C3Timeline.Crossfade },
                    { "object_source", KanjiDiscoveryController.ObjectSourceOf(discovery != null ? item.AnchorObjectPrefab : null) },
                    { "object_audio_plays", objectAudioPlays },   // D-F6-49: 3 with the approach on, 0 off
                    { "audio_played", clip != null && pronunciation != null },
                    { "audio_source", PronunciationAudioController.SourceOf(clip) },
                    // RAY: ASSEMBLY_SEGMENT_PLACED / ASSEMBLY_COMPLETED follow.
                    // NOT_IMPLEMENTED: no assembly controller in the scene, so the
                    // missing step never reads as a lost event.
                    { "assembly", assembly != null ? "RAY" : "NOT_IMPLEMENTED" },
                });

                // ---- Guided assembly (spec 5.3, since 28 September) ---------
                if (assembly != null)
                    yield return assembly.Run(item, blockSeed, i + 1);

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

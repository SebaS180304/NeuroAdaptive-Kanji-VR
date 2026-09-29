using System.Collections;
using System.Collections.Generic;
using System.Linq;
using NeuroAdaptiveVR.Core;
using NeuroAdaptiveVR.Data;
using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Guided kanji assembly (spec 5.3 / 14): 2-4 large stroke groups per
    /// kanji, no handwriting recognition. The board shows the segmented target
    /// area and highlights the next slot; the participant selects a segment
    /// with the ray and places it in the highlighted slot, in the configured
    /// order. Secondary telemetry, not a primary experimental outcome.
    ///
    /// HOW IT PLAYS (decided 24-25 September)
    /// --------------------------------------
    /// - Ray, two steps: trigger on a segment takes it (it turns blue), trigger
    ///   on the highlighted slot places it. Selection and placement are
    ///   separate actions, and both are timed.
    /// - Slots on the board where the glyph was; segments on the answer
    ///   cards, in the Response Area (see StudioTrialPresenter for why).
    /// - A wrong segment flashes the slot red and goes back to the row. It
    ///   counts as an incorrect attempt; the slot stays highlighted. After
    ///   three wrong attempts in a row on the same slot, the correct segment
    ///   is tinted as a hint, and every later placement records it.
    /// - Segments without authored content are labelled placeholders
    ///   ("part 1"), N = assemblyGroups (decision D2, AssemblyPlan).
    ///
    /// Telemetry: ASSEMBLY_SEGMENT_PLACED per attempt (D4), then
    /// ASSEMBLY_COMPLETED as the aggregate.
    ///
    /// This component decides and records; the board draws
    /// (StudioTrialPresenter, the board's only owner, D1).
    /// </summary>
    public class KanjiAssemblyController : MonoBehaviour
    {
        private const string Log = "[Assembly]";

        [SerializeField] private StudioTrialPresenter board;
        [SerializeField] private BehaviorTelemetryController telemetry;

        [Tooltip("Wrong attempts in a row on one slot before the correct segment is tinted as a hint.")]
        [SerializeField] private int hintAfterWrong = 3;
        [Tooltip("The finished kanji stays on the board this long before the association trial.")]
        [SerializeField] private float completedSeconds = 1.5f;
        [Tooltip("The complete kanji stays green this long (not after a forced completion).")]
        [SerializeField] private float successSeconds = 1.6f;

        [Header("Sounds (procedural)")]
        [SerializeField] private bool playSounds = true;
        [SerializeField, Range(0f, 1f)] private float volume = 0.5f;

        private AudioSource _audio;
        private AudioClip _placeClip, _wrongClip, _doneClip;

        private readonly Queue<string> _segmentClicks = new();
        private readonly Queue<int> _slotClicks = new();
        private bool _forced;

        public bool Running { get; private set; }

        private void Awake()
        {
            if (board == null) board = FindAnyObjectByType<StudioTrialPresenter>();
            if (telemetry == null) telemetry = GetComponent<BehaviorTelemetryController>();
            BuildClips();
        }

        private void OnEnable()
        {
            if (board == null) return;
            board.OnOptionChosen += HandleSegment;
            board.OnSlotChosen += HandleSlot;
        }

        private void OnDisable()
        {
            if (board == null) return;
            board.OnOptionChosen -= HandleSegment;
            board.OnSlotChosen -= HandleSlot;
        }

        private void HandleSegment(string id) { if (Running) _segmentClicks.Enqueue(id); }
        private void HandleSlot(int index) { if (Running) _slotClicks.Enqueue(index); }

        /// <summary>
        /// Researcher escape hatch: completes the running assembly with every
        /// remaining segment in place. Recorded as forced_by_researcher.
        /// </summary>
        [ContextMenu("Force complete assembly (researcher)")]
        public void ForceComplete()
        {
            if (Running) _forced = true;
        }

        public IEnumerator Run(KanjiItem item, int blockSeed, int exposureIndex)
        {
            var plan = AssemblyPlan.For(item, blockSeed);
            if (plan.Problem != null)
            {
                Debug.LogError($"{Log} {item}: {plan.Problem}. Assembly skipped for this kanji.");
                yield break;
            }
            if (board == null)
            {
                Debug.LogError($"{Log} No StudioTrialPresenter; assembly skipped.");
                yield break;
            }

            _segmentClicks.Clear();
            _slotClicks.Clear();
            _forced = false;
            Running = true;

            var row = plan.RowOrder.Select(i => (plan.SegmentIds[i], plan.Labels[i])).ToList();
            board.ShowAssembly(plan.Count, row, Instruction(0, plan.Count), item.KanjiId);
            Debug.Log($"{Log} {item} · {plan.Count} slots ({(plan.Authored ? "authored" : "placeholders from assemblyGroups")}) · " +
                      $"row {string.Join(" ", plan.RowSegmentIds)}");

            float t0 = Time.realtimeSinceStartup;
            int incorrect = 0, attempts = 0, hints = 0;
            int slot = 0;
            string selected = null;
            float selectedAt = 0f;
            int wrongHere = 0;
            string hintFor = null;

            board.HighlightSlot(0);
            board.SetSegmentSelected(null, null);

            while (slot < plan.Count && !_forced)
            {
                while (_segmentClicks.Count > 0)
                {
                    string id = _segmentClicks.Dequeue();
                    if (!plan.SegmentIds.Contains(id)) continue;   // not a segment (stray card event)
                    selected = id;
                    selectedAt = Time.realtimeSinceStartup;
                    board.SetSegmentSelected(selected, hintFor);
                }

                while (_slotClicks.Count > 0 && slot < plan.Count)
                {
                    int s = _slotClicks.Dequeue();
                    if (s != slot || selected == null) continue;   // only the highlighted slot, with a segment in hand

                    attempts++;
                    string expected = plan.SegmentIds[slot];
                    bool ok = selected == expected;
                    float now = Time.realtimeSinceStartup;

                    telemetry?.Emit(TelemetryEvents.AssemblySegmentPlaced, new Dictionary<string, object>
                    {
                        { TelemetryContract.KeyKanjiId, item.KanjiId },
                        { "exposure_index", exposureIndex },
                        { "attempt", attempts },
                        { "slot_index", slot + 1 },
                        { "segment_id", selected },
                        { "expected_segment_id", expected },
                        { "is_correct", ok },
                        { "selected_ms", Ms(t0, selectedAt) },
                        { "placed_ms", Ms(t0, now) },
                        { "hint_shown", hintFor == expected },
                        { "segments_authored", plan.Authored },
                    });

                    if (ok)
                    {
                        Play(_placeClip);
                        board.FillSlot(slot, selected, plan.Labels[slot]);
                        slot++;
                        wrongHere = 0;
                        hintFor = null;
                        selected = null;
                        if (slot < plan.Count)
                        {
                            board.HighlightSlot(slot);
                            board.SetCue(Instruction(slot, plan.Count));
                        }
                    }
                    else
                    {
                        incorrect++;
                        wrongHere++;
                        selected = null;
                        Play(_wrongClip);
                        board.FlashSlotWrong(slot);
                        if (wrongHere >= hintAfterWrong && hintFor == null)
                        {
                            hintFor = expected;
                            hints++;
                            Debug.Log($"{Log} {item} · slot {slot + 1}: {wrongHere} wrong in a row, hint on {expected}");
                        }
                    }
                    board.SetSegmentSelected(selected, hintFor);
                }

                yield return null;
            }

            bool forced = _forced;
            Running = false;
            long duration = Ms(t0, Time.realtimeSinceStartup);

            telemetry?.Emit(TelemetryEvents.AssemblyCompleted, new Dictionary<string, object>
            {
                { TelemetryContract.KeyKanjiId, item.KanjiId },
                { "exposure_index", exposureIndex },
                { "duration_ms", duration },
                { "incorrect_attempts", incorrect },
                { "segment_count", plan.Count },
                { "segments_placed", slot },
                { "hints_shown", hints },
                { "row_order", plan.RowSegmentIds.ToList() },
                { "segments_authored", plan.Authored },
                { "forced_by_researcher", forced },
            });
            Debug.Log($"{Log} {item} · done in {duration} ms · {incorrect} wrong · {hints} hints" +
                      (forced ? " · FORCED by researcher" : ""));

            // The kanji, whole, where it was built.
            if (!forced)
            {
                // Success is visible AND audible: in VR the eyes may be on the cards.
                board.ShowAssemblyComplete();
                Play(_doneClip);
                yield return new WaitForSecondsRealtime(successSeconds);
            }
            board.ShowExposure(item.Character);
            yield return new WaitForSecondsRealtime(completedSeconds);
        }

        // ------------------------------------------------------------------
        // Sounds, generated so no asset is needed (same approach as the S4 chime)
        // ------------------------------------------------------------------

        private void Play(AudioClip clip)
        {
            if (!playSounds || clip == null) return;
            if (_audio == null)
            {
                _audio = gameObject.AddComponent<AudioSource>();
                _audio.playOnAwake = false;
                _audio.spatialBlend = 0f;
            }
            _audio.PlayOneShot(clip, volume);
        }

        private void BuildClips()
        {
            if (_placeClip != null) return;
            _placeClip = Tones("AssemblyPlace", new[] { 988f }, 0.09f, 0.35f);                 // short high tick
            _wrongClip = Tones("AssemblyWrong", new[] { 196f }, 0.16f, 0.30f, down: true);
            _doneClip = Tones("AssemblyDone", new[] { 523f, 659f, 784f, 1047f }, 0.11f, 0.35f); // C E G C
        }

        private static AudioClip Tones(string name, float[] freqs, float noteSeconds, float amp, bool down = false)
        {
            const int rate = 44100;
            int per = (int)(rate * noteSeconds);
            int tail = (int)(rate * 0.15f);
            var data = new float[per * freqs.Length + tail];
            for (int k = 0; k < freqs.Length; k++)
                for (int i = 0; i < per + tail && k * per + i < data.Length; i++)
                {
                    float t = (float)i / rate;
                    float f = down ? freqs[k] * (1f - 0.25f * t / noteSeconds) : freqs[k];
                    float env = Mathf.Min(1f, t / 0.005f) * Mathf.Exp(-t * (down ? 14f : 18f));
                    data[k * per + i] += amp * env * Mathf.Sin(2f * Mathf.PI * f * t);
                }
            var clip = AudioClip.Create(name, data.Length, 1, rate, false);
            clip.SetData(data, 0);
            return clip;
        }

        private static string Instruction(int slot, int count) =>
            $"Pick a part, then its place on the board · {slot + 1} of {count}";

        private static long Ms(float from, float to) => (long)((to - from) * 1000f);
    }
}

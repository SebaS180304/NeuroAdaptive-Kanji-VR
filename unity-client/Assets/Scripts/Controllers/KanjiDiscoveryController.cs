using System;
using System.Collections;
using NeuroAdaptiveVR.Data;
using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Stages 1-3 of the four-stage pictographic derivation (spec 5.1): decides
    /// WHAT each stage shows. Stage 4, the modern character, is the glyph.
    ///
    /// ON THE BOARD, NOT IN THE OBJECT AREA (decided 25 September)
    /// ------------------------------------------------------------
    /// Version 1 drew stages 1-3 on a panel in the Object / Association Area,
    /// ~35 degrees to the participant's left, as spec 3.1 places it. The first
    /// headset pass showed the cost: every kanji made the participant turn the
    /// head left and back, which is neck muscle and movement artefact in the
    /// EEG in the middle of the learning block, five times per session. It also
    /// split one continuous transformation across two surfaces.
    ///
    /// Now every stage is drawn on the Learning Board, in the spot where the
    /// glyph appears at stage 4, so the object becomes the character in place.
    /// A declared deviation from spec 3.1, recorded in
    /// Replan_Cierre_M2_24sep.md.
    ///
    /// The board keeps ONE owner: this component asks StudioTrialPresenter to
    /// draw, it never writes to the board's labels itself.
    ///
    /// AUTHORED ASSETS VERSUS PLACEHOLDERS
    /// -----------------------------------
    /// Stage 1 instantiates the kanji's anchorObjectPrefab at objectAnchor (in
    /// front of the board) when one exists. Everything missing -- today, all of
    /// it -- becomes a LABELLED placeholder that says what it stands for.
    /// Placeholders never show the glyph: that would spoil stage 4.
    /// </summary>
    public class KanjiDiscoveryController : MonoBehaviour
    {
        public const int StageCount = 4;

        [SerializeField] private StudioTrialPresenter board;
        [Tooltip("Where an authored stage-1 object is instantiated: just in front of the board.")]
        [SerializeField] private Transform objectAnchor;

        private GameObject _spawned;

        private void Awake()
        {
            if (board == null) board = FindAnyObjectByType<StudioTrialPresenter>();
        }

        /// <summary>What KANJI_EXPOSED.object_source records for stage 1: the Blender object or the labelled placeholder.</summary>
        public static string ObjectSourceOf(GameObject anchorObjectPrefab) => anchorObjectPrefab != null ? "BLENDER_FBX" : "PLACEHOLDER";

        /// <summary>Shows stage 1, 2 or 3 for this kanji.</summary>
        /// <param name="progress">Short text for the note line, e.g. "kanji 2 of 5".</param>
        /// <returns>True if the stage came from authored content, false if it is a placeholder.</returns>
        public bool ShowStage(KanjiItem item, int stage, string progress = null)
        {
            ClearSpawned();
            string prefix = string.IsNullOrEmpty(progress) ? string.Empty : progress + " · ";

            if (stage == 1 && item.AnchorObjectPrefab != null)
            {
                _spawned = Instantiate(item.AnchorObjectPrefab, objectAnchor != null ? objectAnchor : transform);
                board?.ShowDerivationStage(string.Empty, $"{prefix}stage 1/{StageCount}");
                return true;
            }

            string main = stage == 1 ? item.Meaning : "drawing";
            string what = stage == 1 ? "object" : "drawing";
            board?.ShowDerivationStage(main, $"{prefix}{what} · stage {stage}/{StageCount} · not authored");
            return false;
        }

        public void Hide() => ClearSpawned();

        /// <summary>The stage-1 object while it is on show (the demo scene focuses on it), else null.</summary>
        public Transform Spawned => _spawned != null ? _spawned.transform : null;

        /// <summary>C3 starts by shrinking the object in place (C3Timeline.ObjectScale): 1 is its own scale, 0 hides it.</summary>
        public void SetObjectScale(float s)
        {
            if (_spawned == null) return;
            if (_spawnedScale == null) _spawnedScale = _spawned.transform.localScale;
            _spawned.transform.localScale = _spawnedScale.Value * s;
            _spawned.SetActive(s > 0f);
        }

        private Vector3? _spawnedScale;

        // ---- Stage 1 with the object coming closer (D-F6-49; behind S5's switch, off until A-9) ----

        /// <summary>Length of stage 1 when the object comes closer, levitates and goes back.</summary>
        public const float ApproachSeconds = 8f;
        /// <summary>Where it levitates: in line between the eye and the board anchor, 0.72 m from the eye, ≈ 12° below the gaze.</summary>
        public static readonly Vector3 NearPoint = new(0f, 1.45f, 0.70f);
        /// <summary>When the reading plays, seconds into stage 1.</summary>
        public static readonly float[] ObjectReadingSeconds = { 1.5f, 3.5f, 5.5f };
        private const float BobMetres = 0.015f, BobPeriod = 2f, TurnDegrees = 20f, TurnPeriod = 6f;

        /// <summary>
        /// Position and turn (degrees about the world vertical, on top of the prefab's own rotation) at t seconds
        /// into stage 1: 0-1 s from the anchor to NearPoint, 1-7 s levitating and turning, 7-8 s back. A pure
        /// function of t, the same for every participant; the harness samples it (X14).
        /// </summary>
        public static (Vector3 pos, float turnDeg) ApproachPose(Vector3 anchor, float t)
        {
            static float Smooth(float x) { x = Mathf.Clamp01(x); return x * x * (3f - 2f * x); }
            if (t < 1f) return (Vector3.Lerp(anchor, NearPoint, Smooth(t)), 0f);
            if (t < 7f)
            {
                float u = t - 1f;
                return (NearPoint + Vector3.up * (BobMetres * Mathf.Sin(2f * Mathf.PI * u / BobPeriod)),
                        TurnDegrees * Mathf.Sin(2f * Mathf.PI * u / TurnPeriod));
            }
            return (Vector3.Lerp(NearPoint, anchor, Smooth(t - 7f)), 0f);
        }

        /// <summary>Runs stage 1's approach on the spawned object; onReading is called at each reading time.</summary>
        public IEnumerator Approach(Action onReading)
        {
            if (_spawned == null) yield break;
            var obj = _spawned.transform;
            Vector3 anchor = obj.position;
            Quaternion baseRotation = obj.rotation;
            float t0 = Time.realtimeSinceStartup;
            int next = 0;
            for (float t = 0f; t < ApproachSeconds; t = Time.realtimeSinceStartup - t0)
            {
                var (pos, turn) = ApproachPose(anchor, t);
                obj.SetPositionAndRotation(pos, Quaternion.Euler(0f, turn, 0f) * baseRotation);
                while (next < ObjectReadingSeconds.Length && t >= ObjectReadingSeconds[next]) { onReading?.Invoke(); next++; }
                yield return null;
                if (_spawned == null) yield break;
            }
            obj.SetPositionAndRotation(anchor, baseRotation);
        }

        private void ClearSpawned()
        {
            if (_spawned != null) Destroy(_spawned);
            _spawned = null;
            _spawnedScale = null;
        }
    }
}

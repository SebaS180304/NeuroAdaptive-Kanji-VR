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

        private void ClearSpawned()
        {
            if (_spawned != null) Destroy(_spawned);
            _spawned = null;
        }
    }
}

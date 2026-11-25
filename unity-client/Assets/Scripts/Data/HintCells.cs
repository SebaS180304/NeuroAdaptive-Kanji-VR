namespace NeuroAdaptiveVR.Data
{
    /// <summary>
    /// What each cell of the spec §9.1 matrix shows on the board (Diseno_UI_Kanji_Studio_v1.md §9.1, D-F6-63):
    /// LAL decides WHICH cues a trial grants (LearningAssistanceController); this decides how they are drawn.
    ///   T1 HIGH  partial strip in zone B (object → form 1 → ? → ?)   T2 HIGH  meaning link in zone A
    ///   T3 MED   picture in zone A                                  T3 HIGH  full strip in zone B, zone A empty
    /// Reading audio (T1/T2) gets the speaker indicator (D-F6-89); T3 never has audio before the answer.
    /// </summary>
    public static class HintCells
    {
        public enum ZoneA { None, Picture, MeaningLink }
        public enum ZoneB { None, PartialStrip, FullStrip }

        public const string Authored = "AUTHORED";
        public const string Placeholder = "PLACEHOLDER";

        public static ZoneA ZoneAFor(RetrievalTrialType type, LalCue cue)
        {
            if ((cue & LalCue.ReverseSemanticAssociation) != 0) return ZoneA.MeaningLink;
            // In T3 HIGH the object is already the strip's first box, so zone A stays empty (§9.1).
            if ((cue & LalCue.VisualAssociation) != 0 && (cue & LalCue.VisualTransformation) == 0) return ZoneA.Picture;
            return ZoneA.None;
        }

        public static ZoneB ZoneBFor(RetrievalTrialType type, LalCue cue)
        {
            if ((cue & LalCue.VisualTransformation) == 0) return ZoneB.None;
            // T1's cards are kanji: the strip stops at form 1 so it never shows the glyph (§9.1).
            return type == RetrievalTrialType.KanjiToReading ? ZoneB.FullStrip : ZoneB.PartialStrip;
        }

        public static bool AudioIndicator(RetrievalTrialType type, LalCue cue)
            => (cue & LalCue.TargetReadingAudio) != 0 && type != RetrievalTrialType.KanjiToReading;

        /// <summary>
        /// asset_source of the visual hint (D-F6-91): AUTHORED when every image the cell draws exists, PLACEHOLDER
        /// when one is missing, null when the cell has no visual hint (audio only, or no cue).
        /// </summary>
        public static string AssetSource(RetrievalTrialType type, LalCue cue, KanjiItem item)
        {
            var a = ZoneAFor(type, cue);
            var b = ZoneBFor(type, cue);
            if (a == ZoneA.None && b == ZoneB.None) return null;
            bool ok = item != null
                && (a != ZoneA.Picture || item.VisualAssociationSprite != null)
                && (a != ZoneA.MeaningLink || item.MeaningLinkSprite != null)
                && (b == ZoneB.None || (item.VisualAssociationSprite != null && item.TransformationForm1Sprite != null))
                && (b != ZoneB.FullStrip || item.TransformationForm2Sprite != null);
            return ok ? Authored : Placeholder;
        }
    }
}

namespace NeuroAdaptiveVR.Data
{
    /// <summary>
    /// C3, the pictographic story of a kanji in S5 (D-F6-64, D-F6-90; Diseno_UI_Kanji_Studio_v1.md §10, 27 Oct table),
    /// from the moment the object is back on the board. One table for the crossfade and the SDF morph (D-F6-103):
    ///   0.0–0.5  object shrinks 1 → 0 (ease in-out) while form 1 fades in
    ///   0.5–2.3  form 1 still · 2.3–3.1 form 1 → form 2 (800 ms) · 3.1–4.9 form 2 still
    ///   4.9–5.7  form 2 → kanji (800 ms) · 5.7–7.8 kanji still; summary strip in at 6.0 (300 ms), out from 7.5 (300 ms)
    /// Every value is a pure function of t, the same in every condition and level.
    /// </summary>
    public static class C3Timeline
    {
        public const float TotalSeconds = 7.8f;
        public const float ShrinkSeconds = 0.5f;
        public const float FormToFormStart = 2.3f, FormToKanjiStart = 4.9f, TransitionSeconds = 0.8f;
        public const float StripIn = 6.0f, StripOut = 7.5f, StripFadeSeconds = 0.3f;

        public const string Crossfade = "CROSSFADE";   // c3_transition (D-F6-104)

        /// <summary>w = 6u⁵ − 15u⁴ + 10u³ (§10.1): zero speed and acceleration at both ends, monotonic.</summary>
        public static float Smootherstep(float u)
        {
            u = u < 0f ? 0f : u > 1f ? 1f : u;
            return u * u * u * (u * (6f * u - 15f) + 10f);
        }

        /// <summary>Weight of B in a transition that starts at t0 (0 before, 1 after).</summary>
        public static float Transition(float t, float t0) => Smootherstep((t - t0) / TransitionSeconds);

        /// <summary>Scale of the 3D object: 1 → 0 over the first 0.5 s, ease in-out.</summary>
        public static float ObjectScale(float t) => 1f - Smootherstep(t / ShrinkSeconds);

        /// <summary>Opacity of each layer at t: form 1, form 2, the kanji glyph, and the summary strip.</summary>
        public static (float form1, float form2, float kanji, float strip) Opacities(float t)
        {
            float fadeIn = Smootherstep(t / ShrinkSeconds);
            float toForm2 = Transition(t, FormToFormStart);
            float toKanji = Transition(t, FormToKanjiStart);
            float strip = t < StripIn ? 0f
                        : t < StripIn + StripFadeSeconds ? (t - StripIn) / StripFadeSeconds
                        : t < StripOut ? 1f
                        : t < StripOut + StripFadeSeconds ? 1f - (t - StripOut) / StripFadeSeconds
                        : 0f;
            return (fadeIn * (1f - toForm2), toForm2 * (1f - toKanji), toKanji, strip);
        }
    }
}

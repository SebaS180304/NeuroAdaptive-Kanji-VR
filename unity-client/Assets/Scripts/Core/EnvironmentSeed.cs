using NeuroAdaptiveVR.Data;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// Where every random draw of the Environmental Layer gets its seed
    /// (Phase 3, F3.2, 30 September 2026).
    ///
    /// Until M2 the ESL used one seed saved in the scene (-1058336171, left there
    /// by a session of 24 September): every participant saw the same props and
    /// the same curtain side, and ENVIRONMENT_APPLIED reported a seed that was
    /// not the session's. Now each draw derives from the session seed plus a
    /// purpose label, the same way trial blocks derive their BlockSeed:
    ///
    ///   selection:{LEVEL}   which props and movers a level activates
    ///   motion:{object}     the starting phase of each moving object
    ///   peripheral:{LEVEL}  which peripheral object fires and when
    ///
    /// The selection is per LEVEL, not per state: LOW is the same set of props
    /// in S1, S2, S5 and S9 of one session. The room the participant learns in
    /// does not change between states that share a level (it answers the open
    /// question to MIRAI about LOW varying 2 vs 3 props within a session).
    ///
    /// Without a session (edit mode, debug Play) the fallback seed of the
    /// component is used, and the caller says so in the telemetry.
    /// </summary>
    public static class EnvironmentSeed
    {
        public static bool FromSession => SessionContext.IsInstalled && SessionContext.RandomSeedRaw != null;

        /// <summary>The base the purposes derive from: the session seed, or the fallback.</summary>
        public static int Base(int fallback) => FromSession ? SessionContext.Seed : fallback;

        public static int For(int baseSeed, string purpose) => StableHash.Of($"{baseSeed}:esl:{purpose}");

        /// <summary>A value in [0, 1) derived from a seed; used for motion phases.</summary>
        public static float Unit(int seed) => (float)((uint)seed / 4294967296.0);
    }
}

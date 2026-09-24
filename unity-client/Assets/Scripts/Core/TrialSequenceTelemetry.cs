using System.Collections.Generic;
using NeuroAdaptiveVR.Controllers;
using NeuroAdaptiveVR.Data;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// Emits TRIAL_SEQUENCE_GENERATED for a block plan (spec 6.1, EVENT_CONTRACT §5.8).
    ///
    /// Until 24 September this payload was built inside TrialDebugRunner. The
    /// chained session now builds plans too, and two copies of the payload
    /// would drift the first time someone added a field to one of them -- the
    /// usual shape of this project's bugs. One builder, two callers.
    /// </summary>
    public static class TrialSequenceTelemetry
    {
        /// <param name="sessionSeed">
        /// The session seed (experiment_sessions.random_seed through StableHash).
        /// The plan itself carries the BLOCK seed derived from it; both travel,
        /// because reconstruction needs the block seed and the audit trail
        /// needs to see where it came from.
        /// </param>
        public static void Emit(BehaviorTelemetryController telemetry, TrialPlan plan,
                                string kanjiSet, int sessionSeed)
        {
            if (telemetry == null || plan == null) return;

            telemetry.Emit(TelemetryEvents.TrialSequenceGenerated, new Dictionary<string, object>
            {
                { "block_state", plan.State.ToWireValue() },
                { "kanji_set", kanjiSet },
                { "seed", sessionSeed },
                { "block_seed", plan.Seed },
                { "seed_raw", SessionContext.IsInstalled ? SessionContext.RandomSeedRaw : null },
                { "trial_count", plan.Count },
                { "min_lag_requested", plan.MinLag },
                { "min_lag_achieved", plan.ShortestLag() == int.MaxValue ? -1 : plan.ShortestLag() },
                { "distinct_pairs", plan.DistinctPairs },
                { "ordering_attempts", plan.OrderingAttempts },
                { "sequence", plan.ToTelemetryRows() },
            });
        }
    }
}

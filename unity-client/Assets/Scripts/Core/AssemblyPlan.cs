using System.Collections.Generic;
using System.Linq;
using NeuroAdaptiveVR.Data;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// What one guided assembly (spec 5.3) consists of, decided before it
    /// starts: which segments, in which order they fill the slots, and in which
    /// order they sit in the row. Pure data from the item and a seed, so the
    /// Phase 2 harness can check it without a scene and a session can be
    /// reconstructed from its seed.
    ///
    /// SEGMENT COUNT (decision D2)
    /// ---------------------------
    /// Authored segments are used when the item has them. Otherwise the plan
    /// makes N labelled placeholders, N = assemblyGroups from the contract.
    /// That number is not decorative: assembly groups are part of the
    /// balance band of spec 4.1, so a kanji with the wrong piece count would
    /// unbalance its set.
    ///
    /// ROW ORDER
    /// ---------
    /// Slots are filled in segment order (spec 5.3, "in the configured
    /// order"). The row the participant picks from is shuffled from the seed,
    /// otherwise the task would reduce to "take the leftmost piece".
    /// </summary>
    public sealed class AssemblyPlan
    {
        public const int MinSegments = 2;
        public const int MaxSegments = 4;   // also the number of cards in the Response Area

        public readonly string KanjiId;

        /// <summary>Segment ids in SLOT order: slot i takes SegmentIds[i].</summary>
        public readonly IReadOnlyList<string> SegmentIds;

        /// <summary>Text shown on each segment and on its slot once filled, in slot order.</summary>
        public readonly IReadOnlyList<string> Labels;

        /// <summary>Row position -> slot index. RowOrder[0] is the leftmost segment.</summary>
        public readonly IReadOnlyList<int> RowOrder;

        public readonly bool Authored;

        public int Count => SegmentIds.Count;

        /// <summary>Null when the plan is usable; otherwise why not.</summary>
        public readonly string Problem;

        private AssemblyPlan(string kanjiId, List<string> ids, List<string> labels,
                             List<int> rowOrder, bool authored, string problem)
        {
            KanjiId = kanjiId;
            SegmentIds = ids;
            Labels = labels;
            RowOrder = rowOrder;
            Authored = authored;
            Problem = problem;
        }

        public IEnumerable<string> RowSegmentIds => RowOrder.Select(i => SegmentIds[i]);

        public static AssemblyPlan For(KanjiItem item, int blockSeed)
        {
            var authored = item.AssemblySegments?.Where(s => s != null).ToList() ?? new List<AssemblySegment>();
            bool useAuthored = authored.Count > 0;
            int groups = item.AssemblyGroups;

            var ids = new List<string>();
            var labels = new List<string>();
            if (useAuthored)
            {
                for (int i = 0; i < authored.Count; i++)
                {
                    var s = authored[i];
                    ids.Add(string.IsNullOrEmpty(s.segmentId) ? $"{item.KanjiId}_SEG{i + 1}" : s.segmentId);
                    labels.Add(string.IsNullOrEmpty(s.description) ? $"part {i + 1}" : s.description);
                }
            }
            else
            {
                for (int i = 0; i < groups; i++)
                {
                    ids.Add($"{item.KanjiId}_SEG{i + 1}");
                    labels.Add($"part {i + 1}");
                }
            }

            string problem = null;
            if (ids.Count < MinSegments || ids.Count > MaxSegments)
                problem = $"{ids.Count} segments; spec 5.3 allows {MinSegments}-{MaxSegments}";
            else if (useAuthored && groups > 0 && authored.Count != groups)
                problem = $"{authored.Count} authored segments but the contract says assemblyGroups={groups} (balance band, spec 4.1)";
            else if (ids.Distinct().Count() != ids.Count)
                problem = "duplicate segment ids";

            var row = Enumerable.Range(0, ids.Count).ToList();
            var rng = new System.Random(StableHash.Of($"{blockSeed}:assembly:{item.KanjiId}"));
            for (int i = row.Count - 1; i > 0; i--)
            {
                int j = rng.Next(i + 1);
                (row[i], row[j]) = (row[j], row[i]);
            }

            return new AssemblyPlan(item.KanjiId, ids, labels, row, useAuthored, problem);
        }
    }
}

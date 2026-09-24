using System.Collections;
using System.Collections.Generic;
using NeuroAdaptiveVR.Data;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// What SessionFlowRunner needs from the S5 learning block (spec 7.6), and
    /// nothing more.
    ///
    /// It exists so the chain can be built and verified BEFORE the S5
    /// mechanics are: with no block assigned, the runner crosses S5 with a
    /// labelled placeholder, and the day the block exists it plugs in here
    /// without the runner changing. The same trick ITrialPresenter played for
    /// the response system in early September.
    /// </summary>
    public interface ILearningBlock
    {
        /// <param name="set">The five kanji of the session set, in contract order.</param>
        /// <param name="sessionSeed">The session seed. The block derives its own from it.</param>
        IEnumerator Run(IReadOnlyList<KanjiItem> set, int sessionSeed);
    }
}

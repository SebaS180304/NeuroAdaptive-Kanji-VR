using System.Collections.Generic;
using System.Linq;

namespace NeuroAdaptiveVR.Data
{
    /// <summary>Un trial planeado, con sus opciones ya resueltas y ordenadas.</summary>
    public sealed class PlannedTrial
    {
        /// <summary>Posicion 1-based dentro del plan de SU estado.</summary>
        public readonly int Sequence;

        public readonly KanjiItem Target;
        public readonly RetrievalTrialType TrialType;

        /// <summary>
        /// Las cuatro opciones EN EL ORDEN EN QUE SE VAN A PRESENTAR. El orden
        /// forma parte del plan, no es cosa del presentador: spec 6.1 pide
        /// reconstruccion exacta, y una reconstruccion que baraja distinto no
        /// reconstruye la misma tarea.
        /// </summary>
        public readonly IReadOnlyList<TrialOption> Options;

        public PlannedTrial(int sequence, KanjiItem target, RetrievalTrialType trialType,
                            IReadOnlyList<TrialOption> options)
        {
            Sequence = sequence;
            Target = target;
            TrialType = trialType;
            Options = options;
        }

        public TrialRequest ToRequest(bool immediateFeedback)
            => new TrialRequest(Sequence, Target, TrialType, Options, immediateFeedback);
    }

    /// <summary>
    /// La secuencia completa de un bloque de trials, generada de una vez.
    ///
    /// POR QUE SE GENERA ENTERA Y NO TRIAL A TRIAL
    /// -------------------------------------------
    /// Spec 6.1: "Random seeds and final trial sequence are stored to permit
    /// exact session reconstruction". Un generador que produjera el siguiente
    /// trial bajo demanda no tendria nunca una "secuencia final" que guardar --
    /// solo la tendria al terminar, cuando ya no sirve para nada.
    ///
    /// Ademas, el espaciado minimo entre apariciones del mismo kanji es una
    /// propiedad de la secuencia, no de un trial. Solo se puede garantizar
    /// mirandola completa.
    /// </summary>
    public sealed class TrialPlan
    {
        public readonly GameFlowState State;
        public readonly int Seed;
        public readonly int MinLag;
        public readonly IReadOnlyList<PlannedTrial> Trials;

        /// <summary>
        /// Cuantos intentos de ordenacion hicieron falta. 1 es lo normal. Mas de
        /// 1 significa que el primer barajado dejo un callejon sin salida al
        /// final de la secuencia y hubo que reintentar con otra seed derivada.
        /// Se guarda porque forma parte de como se produjo esta secuencia.
        /// </summary>
        public readonly int OrderingAttempts;

        public TrialPlan(GameFlowState state, int seed, int minLag,
                         IReadOnlyList<PlannedTrial> trials, int orderingAttempts)
        {
            State = state;
            Seed = seed;
            MinLag = minLag;
            Trials = trials;
            OrderingAttempts = orderingAttempts;
        }

        public int Count => Trials.Count;

        /// <summary>
        /// Cuantos pares (kanji, tipo) distintos cubre. Con cinco kanji y tres
        /// tipos el maximo es 15, y llegar a 15 es lo que garantiza que ninguna
        /// celda de la comparacion entre kanji se quede vacia.
        /// </summary>
        public int DistinctPairs =>
            Trials.Select(t => $"{t.Target.KanjiId}|{t.TrialType}").Distinct().Count();

        /// <summary>
        /// La separacion mas corta que hay en la secuencia entre dos apariciones
        /// del mismo kanji. int.MaxValue si ningun kanji se repite.
        /// </summary>
        public int ShortestLag()
        {
            var ultima = new Dictionary<string, int>();
            int peor = int.MaxValue;

            for (int i = 0; i < Trials.Count; i++)
            {
                string id = Trials[i].Target.KanjiId;
                if (ultima.TryGetValue(id, out int antes))
                    peor = System.Math.Min(peor, i - antes);
                ultima[id] = i;
            }
            return peor;
        }

        /// <summary>
        /// La secuencia en la forma en que viaja a la base. Es lo que hace
        /// cumplible la segunda mitad de 6.1: la seed sola obligaria a tener el
        /// codigo de hoy para reconstruir nada.
        /// </summary>
        public List<Dictionary<string, object>> ToTelemetryRows()
            => Trials.Select(t => new Dictionary<string, object>
            {
                { "trial_sequence", t.Sequence },
                { "kanji_id", t.Target.KanjiId },
                { "trial_type", t.TrialType.ToWireValue() },
                { "options", t.Options.Select(o => o.OptionId).ToList() },
                { "correct_option", t.Options.First(o => o.IsCorrect).OptionId },
            }).ToList();

        public string Summary()
            => $"{State.ShortCode()} · {Count} trials · {DistinctPairs} pares (kanji,tipo) · " +
               $"separacion min. {(ShortestLag() == int.MaxValue ? "n/a" : ShortestLag().ToString())} " +
               $"(pedida {MinLag}) · seed {Seed}" +
               (OrderingAttempts > 1 ? $" · {OrderingAttempts} intentos de ordenacion" : "");
    }
}

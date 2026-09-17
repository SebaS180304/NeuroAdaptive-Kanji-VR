using NeuroAdaptiveVR.Core;
using UnityEngine;

namespace NeuroAdaptiveVR.Data
{
    /// <summary>
    /// Lo que la sesion declara, leido de experiment_sessions y no del Inspector.
    ///
    /// EL PROBLEMA QUE RESUELVE
    /// ------------------------
    /// Hasta el 16 de septiembre habia cuatro hechos viviendo en dos sitios a la
    /// vez: el set asignado, la seed, la condicion y el numero de visita estaban
    /// en la fila de la base Y en campos del Inspector, y nada los comparaba. La
    /// fila podia decir set A con seed 20260909 mientras la corrida usaba el set
    /// B con otra seed, y el dato resultante habria sido inanalizable sin que
    /// nada avisara.
    ///
    /// Es la misma forma de los fallos del 9 de septiembre --el `esl=OFF` por
    /// fallback-- y del contrato zombi del 15. Un hecho, un sitio.
    ///
    /// POR QUE ES ESTATICO
    /// -------------------
    /// Igual que SessionClock, y por la misma razon: lo consultan componentes que
    /// no tienen por que conocerse entre ellos, y su vida es exactamente la de la
    /// sesion. Y con el mismo cuidado: `Reset()` se llama al arrancar cada Play,
    /// porque el estado estatico sobrevive entre Plays en el Editor y una sesion
    /// heredando el contexto de la anterior es justo el tipo de fallo que se
    /// descubre en el analisis.
    /// </summary>
    public static class SessionContext
    {
        public static string SessionId { get; private set; }

        /// <summary>"A" / "B" / "C", tal como lo asigno el investigador.</summary>
        public static string AssignedKanjiSet { get; private set; }

        /// <summary>La seed tal cual vino: el backend la guarda como texto.</summary>
        public static string RandomSeedRaw { get; private set; }

        /// <summary>
        /// La seed usable. Sale de RandomSeedRaw por StableHash, no por
        /// int.Parse: asi el investigador puede poner "20260909", un UUID o
        /// "piloto-p03-visita2" y todos funcionan igual de bien.
        /// </summary>
        public static int Seed { get; private set; }

        public static ExperimentalCondition Condition { get; private set; }
        public static int VisitNumber { get; private set; }

        /// <summary>Spec 7.3: el tutorial de S2 solo corre en la primera visita.</summary>
        public static bool IsFirstVisit => VisitNumber <= 1;

        /// <summary>
        /// True cuando la sesion trae todo lo que hace falta para reconstruirla.
        /// Sin set o sin seed la sesion NO es reconstruible, y eso es un error de
        /// configuracion, no un caso a resolver en runtime.
        /// </summary>
        public static bool IsComplete { get; private set; }

        public static bool IsInstalled { get; private set; }

        public static void Reset()
        {
            SessionId = null;
            AssignedKanjiSet = null;
            RandomSeedRaw = null;
            Seed = 0;
            Condition = ExperimentalCondition.Static;
            VisitNumber = 0;
            IsComplete = false;
            IsInstalled = false;
        }

        public static void Install(string sessionId, string assignedKanjiSet, string randomSeedRaw,
                                   string conditionWire, string visitNumberRaw)
        {
            SessionId = sessionId;
            AssignedKanjiSet = string.IsNullOrWhiteSpace(assignedKanjiSet) ? null : assignedKanjiSet.Trim();
            RandomSeedRaw = string.IsNullOrWhiteSpace(randomSeedRaw) ? null : randomSeedRaw.Trim();
            Seed = RandomSeedRaw == null ? 0 : StableHash.Of(RandomSeedRaw);

            Condition = ExperimentalConditionExtensions.TryFromWireValue(conditionWire, out var c)
                ? c
                : ExperimentalCondition.Static;

            VisitNumber = int.TryParse(visitNumberRaw, out int v) ? v : 1;

            IsComplete = AssignedKanjiSet != null && RandomSeedRaw != null;
            IsInstalled = true;

            Debug.Log($"[SessionContext] {sessionId} · set {AssignedKanjiSet ?? "(sin asignar)"} · " +
                      $"seed \"{RandomSeedRaw ?? "(sin seed)"}\" -> {Seed} · " +
                      $"{Condition.ToWireValue()} · visita {VisitNumber}" +
                      (IsFirstVisit ? " (primera: S2 corre)" : " (S2 se salta)"));
        }

        /// <summary>
        /// Compara lo que dice la sesion con lo que alguien dejo escrito en el
        /// Inspector. Devuelve false si se contradicen.
        ///
        /// Error y no warning: correr el set B sobre una sesion que declara el A
        /// produce datos que parecen validos y no lo son. Vale mucho mas parar.
        /// </summary>
        public static bool AgreesWithInspector(string inspectorSet, string component)
        {
            if (!IsInstalled || AssignedKanjiSet == null) return true;
            if (string.IsNullOrWhiteSpace(inspectorSet)) return true;
            if (string.Equals(inspectorSet.Trim(), AssignedKanjiSet, System.StringComparison.OrdinalIgnoreCase))
                return true;

            Debug.LogError($"[SessionContext] {component} tiene el set '{inspectorSet}' en el Inspector " +
                           $"pero la sesion {SessionId} declara '{AssignedKanjiSet}'. " +
                           "La corrida se detiene: los datos parecerian validos y no lo serian.");
            return false;
        }
    }
}

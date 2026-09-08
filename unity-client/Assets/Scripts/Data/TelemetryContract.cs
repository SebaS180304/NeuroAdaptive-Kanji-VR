using System.Collections.Generic;

namespace NeuroAdaptiveVR.Data
{
    /// <summary>
    /// Contrato del payload de eventos, version 1.
    /// Documento normativo: database/EVENT_CONTRACT.md.
    ///
    /// Fase 2 no lleva migracion de base de datos: toda la telemetria
    /// conductual entra por el log generico `session_events`
    /// (event_type VARCHAR + payload JSONB) y Fase 3 promueve esas filas a
    /// las tablas relacionales del data contract de la spec seccion 11. Esa
    /// promocion solo es posible si cada evento de Fase 2 ya trae los
    /// identificadores que van a ser llaves foraneas.
    ///
    /// Una columna JSONB nunca avisa de que el payload esta mal. Por eso el
    /// contrato se hace cumplir desde BehaviorTelemetryController, que estampa
    /// el bloque de contexto sin que el emisor pueda omitirlo, y se comprueba
    /// con database/verify_events.sql.
    /// </summary>
    public static class TelemetryContract
    {
        /// <summary>
        /// Version del contrato. Subir al cambiar la forma del payload.
        /// Es lo que permite que Fase 3 migre filas escritas bajo versiones
        /// distintas sin tener que adivinar la forma de cada una.
        /// </summary>
        public const int PayloadSchemaVersion = 1;

        // --- Bloque de contexto: presente en TODOS los eventos ---
        public const string KeySchemaVersion = "schema_version";
        public const string KeyState = "state";
        public const string KeySessionElapsedMs = "session_elapsed_ms";
        public const string KeyEsl = "esl";
        public const string KeyLal = "lal";

        // --- Bloque de trial: solo en eventos dentro de un trial ---
        public const string KeyTrialId = "trial_id";
        public const string KeyTrialType = "trial_type";
        public const string KeyTrialSequence = "trial_sequence";
        public const string KeyKanjiId = "kanji_id";
    }

    /// <summary>
    /// Nombres de los eventos. Constantes y no strings sueltos porque un
    /// typo en un `event_type` produce una fila que se guarda sin error y
    /// desaparece de cualquier consulta que filtre por el nombre correcto.
    /// El vocabulario es el de la spec seccion 11.1.
    /// </summary>
    public static class TelemetryEvents
    {
        // Fase 1
        public const string StateEntered = "STATE_ENTERED";

        // Fase 2 -- sistema de respuesta
        public const string TrialStarted = "TRIAL_STARTED";
        public const string AnswerSelected = "ANSWER_SELECTED";
        public const string HintRequested = "HINT_REQUESTED";
        public const string TrialCompleted = "TRIAL_COMPLETED";

        // Fase 2 -- mecanicas de S5
        public const string KanjiExposed = "KANJI_EXPOSED";
        public const string AssemblyCompleted = "ASSEMBLY_COMPLETED";

        // Fase 3 -- reservados. Declarados aca para que Fase 2 no use estos
        // nombres para otra cosa y para que el vocabulario viva en un solo
        // archivo. NO emitir todavia.
        public const string HeadAway = "HEAD_AWAY";
        public const string HeadReturned = "HEAD_RETURNED";
        public const string DistractorInteraction = "DISTRACTOR_INTERACTION";

        /// <summary>
        /// Eventos que solo tienen sentido dentro de un trial abierto.
        /// BehaviorTelemetryController los rechaza con error si no hay trial,
        /// en vez de mandar un payload sin `trial_id` que nadie va a notar
        /// hasta que Fase 3 intente migrarlo.
        /// </summary>
        private static readonly HashSet<string> TrialScoped = new()
        {
            TrialStarted, AnswerSelected, HintRequested, TrialCompleted,
        };

        public static bool RequiresTrialContext(string eventType) => TrialScoped.Contains(eventType);
    }

    /// <summary>
    /// Identidad del trial activo. Se pasa completo a
    /// BehaviorTelemetryController.BeginTrial y de ahi se estampa en cada
    /// evento del trial.
    /// </summary>
    public readonly struct TrialContext
    {
        public readonly string TrialId;
        public readonly RetrievalTrialType TrialType;
        public readonly int TrialSequence;
        public readonly string KanjiId;

        /// <param name="state">Estado que corre el trial: S5, S6, S7 u S8.</param>
        /// <param name="sequence">Posicion 1-based dentro de la secuencia de ese estado.</param>
        /// <param name="kanjiId">Nombre del asset KanjiLearningItem, p.ej. "KANJI_YAMA".</param>
        public TrialContext(GameFlowState state, int sequence, RetrievalTrialType trialType, string kanjiId)
        {
            // Identificador determinista, no UUID: la spec 6.1 pide que la
            // seed y la secuencia permitan reconstruir la sesion exactamente,
            // y un id derivado de la secuencia es el mismo al reconstruirla.
            // El prefijo de estado hace falta porque hay trials en S5, S6, S7
            // y S8, cada uno con su propia numeracion.
            TrialId = $"{state.ShortCode()}-{sequence:D3}";
            TrialType = trialType;
            TrialSequence = sequence;
            KanjiId = kanjiId;
        }
    }
}

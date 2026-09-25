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
        //
        // TRIAL_SEQUENCE_GENERATED lleva la secuencia COMPLETA de un bloque, tal
        // como se planeo, antes de correr el primer trial. Spec 6.1 pide guardar
        // "random seeds and final trial sequence" para poder reconstruir la
        // sesion, y la seed sola no basta: reconstruir con ella obliga a que el
        // codigo generador de hoy siga existiendo y comportandose igual dentro de
        // seis meses.
        //
        // Se parece a duplicar lo que luego dira cada TRIAL_STARTED, y no lo es:
        // esto dice QUE SE PLANEO y aquellos dicen QUE OCURRIO. Si una sesion se
        // aborta en el trial 12, los dos registros difieren -- y esa diferencia
        // es justo el dato que dice donde se corto.
        public const string TrialSequenceGenerated = "TRIAL_SEQUENCE_GENERATED";

        public const string TrialStarted = "TRIAL_STARTED";
        public const string AnswerSelected = "ANSWER_SELECTED";
        public const string HintRequested = "HINT_REQUESTED";
        public const string TrialCompleted = "TRIAL_COMPLETED";

        // Phase 2 -- session chain (S1-S4). Names from spec 7.2-7.5.
        //
        // START_SELECTED: the participant chose Start in S1; carries the time
        // from the welcome panel to the choice.
        // TUTORIAL_STARTED / TUTORIAL_COMPLETED wrap S2. In M2 the tutorial is
        // "look & select" only, so its selections travel as ordinary TRIAL_*
        // events with the S2- prefix instead of TUTORIAL_SELECT; the prefix is
        // what excludes them from the primary analysis. Grab & place and
        // TUTORIAL_GRAB/PLACE arrive with the assembly mechanic.
        // SYSTEM_CHECK_COMPLETED closes S3, with what was checked and whether a
        // researcher forced the advance. A forced S3 is data, not a footnote.
        // BASELINE_STARTED / BASELINE_COMPLETED wrap S4. COMPLETED carries the
        // time scale, so a shortened debug baseline can never pass for a real one.
        public const string StartSelected = "START_SELECTED";
        public const string TutorialStarted = "TUTORIAL_STARTED";
        public const string TutorialCompleted = "TUTORIAL_COMPLETED";
        public const string SystemCheckCompleted = "SYSTEM_CHECK_COMPLETED";
        public const string BaselineStarted = "BASELINE_STARTED";
        public const string BaselineCompleted = "BASELINE_COMPLETED";

        // VIEW_RECENTERED: the view was moved back to the designed eye pose.
        // Recorded because it rewrites where "forward" is: Phase 3's head-away
        // metrics measure angle from the board, and a recenter mid-block is a
        // discontinuity in that signal that must be explainable afterwards.
        public const string ViewRecentered = "VIEW_RECENTERED";

        // STAGE_INTRO_ACKNOWLEDGED: the participant pressed Continue on the
        // announcement shown before S2, S4, S5, S6, S7 and S8 (25 September).
        // The wait is self-paced, so it varies between participants; it falls
        // BETWEEN blocks, never inside one, and recording it keeps session
        // duration fully accounted for.
        public const string StageIntroAcknowledged = "STAGE_INTRO_ACKNOWLEDGED";

        // Fase 2 -- mecanicas de S5
        public const string KanjiExposed = "KANJI_EXPOSED";
        public const string AssemblyCompleted = "ASSEMBLY_COMPLETED";

        // Fase 2 -- capa ambiental (ESL)
        //
        // ENVIRONMENT_APPLIED se emite cuando un perfil se aplica de verdad, no
        // cuando alguien pide un cambio de nivel: un nivel sin perfil se rechaza
        // y no produce evento. Asi, la ausencia del evento significa que la
        // escena no cambio, en vez de significar que quiza cambio.
        //
        // PERIPHERAL_EVENT deja rastro de cada distraccion concreta. Fase 5
        // necesita poder correlacionarla con lo que hizo el participante
        // inmediatamente despues; un estimulo que actuo sobre la sesion y no se
        // registro es una variable que no se puede reconstruir.
        public const string EnvironmentApplied = "ENVIRONMENT_APPLIED";
        public const string PeripheralEvent = "PERIPHERAL_EVENT";

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
        /// <param name="kanjiId">
        /// El id estable del kanji, p.ej. "KANJI_YAMA". Sale de KANJI_IDS en
        /// tools/kanji_metrics.py, NO del nombre del asset: hasta el 15 de
        /// septiembre se derivaba del nombre de archivo, asi que renombrar un
        /// asset en el Editor cambiaba una llave foranea de Postgres en silencio.
        /// </param>
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

using System;
using System.Collections.Generic;

namespace NeuroAdaptiveVR.Data
{
    /// <summary>
    /// Cues pedagogicos que LAL puede poner a disposicion (spec 9.1).
    /// Flags porque HIGH combina dos en los tres tipos de trial.
    /// </summary>
    [Flags]
    public enum LalCue
    {
        None = 0,
        TargetReadingAudio = 1 << 0,
        VisualAssociation = 1 << 1,
        ReverseSemanticAssociation = 1 << 2,
        VisualTransformation = 1 << 3,
    }

    /// <summary>
    /// Una opcion de respuesta tal como se presenta. El texto ya viene
    /// resuelto: el sistema de respuesta no sabe si es un kanji, un
    /// significado o una lectura, solo lo muestra.
    /// </summary>
    public readonly struct TrialOption
    {
        /// <summary>Id estable de la opcion. Es lo que viaja en la telemetria.</summary>
        public readonly string OptionId;

        /// <summary>Texto a mostrar en la tarjeta.</summary>
        public readonly string DisplayText;

        public readonly bool IsCorrect;

        public TrialOption(string optionId, string displayText, bool isCorrect)
        {
            OptionId = optionId;
            DisplayText = displayText;
            IsCorrect = isCorrect;
        }
    }

    /// <summary>
    /// Contrato de entrada del sistema de respuesta.
    ///
    /// La razon de que exista: el mismo ciclo corre en S5 (asociacion
    /// guiada), S6 (calibracion), S7 (retrieval) y S8 (assessment). Si el
    /// componente supiera quien lo llama, habria un `if (state == S7)`
    /// dentro y dejaria de ser el mismo mecanismo -- que es justo lo que
    /// hace comparables los tiempos de respuesta de S6 y S7 (spec 5.4).
    ///
    /// Las opciones llegan **ya construidas y ya ordenadas**. Quien las
    /// arma es el generador de secuencia, con la seed de la sesion, y las
    /// guarda para permitir reconstruccion exacta (spec 6.1).
    /// </summary>
    public sealed class TrialRequest
    {
        // NO hay campo State a proposito.
        //
        // Un trial ocurre EN el estado en que este la sesion; no lo declara.
        // La primera version si lo llevaba, y el resultado era un payload que
        // se contradecia a si mismo: el bloque de contexto decia
        // S1_WELCOME_ORIENTATION --el estado real del GameFlowController-- y
        // el trial_id decia "S7-001", porque los ponia quien construia el
        // request. Dos fuentes de verdad para el mismo hecho.
        //
        // Ahora el estado se lee del BehaviorTelemetryController al abrir el
        // trial, que es la misma fuente que estampa el bloque de contexto, asi
        // que no pueden discrepar.

        public int Sequence { get; }
        public KanjiLearningItem Target { get; }
        public RetrievalTrialType TrialType { get; }
        public IReadOnlyList<TrialOption> Options { get; }

        // Tampoco hay campo Lal, por la misma razon que no hay State: el
        // nivel lo posee LearningAssistanceController y el sistema de
        // respuesta lo lee de ahi. Llevarlo en el request creaba un LAL que
        // gobernaba los cues mientras el bloque de contexto estampaba otro.

        /// <summary>
        /// S8 (Immediate Assessment) puede diferir el feedback: es la medida
        /// de aprendizaje primaria y mostrar la respuesta correcta durante el
        /// bloque contaminaria los trials siguientes del mismo bloque.
        /// </summary>
        public bool ImmediateFeedback { get; }

        public TrialRequest(
            int sequence,
            KanjiLearningItem target,
            RetrievalTrialType trialType,
            IReadOnlyList<TrialOption> options,
            bool immediateFeedback = true)
        {
            Sequence = sequence;
            Target = target ?? throw new ArgumentNullException(nameof(target));
            TrialType = trialType;
            Options = options ?? throw new ArgumentNullException(nameof(options));
            ImmediateFeedback = immediateFeedback;
        }

        /// <param name="state">
        /// Estado actual de la sesion, leido del BehaviorTelemetryController.
        /// Es lo que da el prefijo del trial_id ("S7-007") y lo que garantiza
        /// que ese prefijo coincida con el `state` del bloque de contexto.
        /// </param>
        public TrialContext ToTrialContext(GameFlowState state)
            => new TrialContext(state, Sequence, TrialType, Target.name);
    }

    /// <summary>
    /// Resultado cerrado de un trial.
    ///
    /// Propiedades de solo lectura por constructor y no `init`: los
    /// accesores `init` dependen de System.Runtime.CompilerServices.
    /// IsExternalInit, cuya disponibilidad varia entre perfiles de .NET en
    /// Unity. No compensa arriesgar un fallo de compilacion por azucar
    /// sintactico.
    /// </summary>
    public sealed class TrialResult
    {
        public string TrialId { get; }
        public RetrievalTrialType TrialType { get; }
        public string KanjiId { get; }
        public string SelectedOptionId { get; }
        public bool IsCorrect { get; }
        public long ResponseTimeMs { get; }
        public bool TimedOut { get; }
        public int HintCount { get; }
        public LalCue CuesPresented { get; }

        public TrialResult(string trialId, RetrievalTrialType trialType, string kanjiId,
                           string selectedOptionId, bool isCorrect, long responseTimeMs,
                           bool timedOut, int hintCount, LalCue cuesPresented)
        {
            TrialId = trialId;
            TrialType = trialType;
            KanjiId = kanjiId;
            SelectedOptionId = selectedOptionId;
            IsCorrect = isCorrect;
            ResponseTimeMs = responseTimeMs;
            TimedOut = timedOut;
            HintCount = hintCount;
            CuesPresented = cuesPresented;
        }
    }
}

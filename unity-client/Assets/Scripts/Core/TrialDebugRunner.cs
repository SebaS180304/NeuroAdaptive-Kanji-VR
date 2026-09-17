using System.Collections.Generic;
using System.Linq;
using NeuroAdaptiveVR.Controllers;
using NeuroAdaptiveVR.Data;
using UnityEngine;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// Banco de pruebas del sistema de respuesta. Arma unos cuantos trials
    /// del set A oficial y se los pasa al ResponseSystemController uno a uno.
    ///
    /// ALCANCE: es andamiaje, no el generador de secuencia. El generador de
    /// verdad --orden pseudoaleatorizado, espaciado controlado, sin
    /// repeticion inmediata, secuencia guardada para reconstruccion exacta
    /// (spec 6.1)-- es trabajo del encadenado del flujo. Esto solo produce
    /// trials bien formados para ejercitar el ciclo y su telemetria.
    ///
    /// El contenido sale de KanjiContentController, igual que en la sesion real.
    /// Este archivo llevaba hasta el 15 de septiembre su propia copia del set A;
    /// ver el comentario de BuildItems para por que dejo de llevarla.
    /// </summary>
    public class TrialDebugRunner : MonoBehaviour
    {
        [SerializeField] private ResponseSystemController responseSystem;
        [SerializeField] private GameFlowController gameFlow;

        [Tooltip("De donde salen los kanji. Es el mismo componente que usara la " +
                 "sesion real: el banco de pruebas ya no tiene contenido propio.")]
        [SerializeField] private KanjiContentController content;

        [Header("Sesion simulada")]
        [Tooltip("Estado al que se hace entrar a la sesion antes de correr. " +
                 "No se 'declara' en el trial: el GameFlowController entra de verdad, " +
                 "emite su STATE_ENTERED, y de ahi salen el bloque de contexto y el " +
                 "prefijo del trial_id.")]
        [SerializeField] private GameFlowState state = GameFlowState.S7_ExperimentalRetrieval;

        [Tooltip("Nivel de LAL fijo. En Fase 2 no lo decide nadie en runtime.")]
        [SerializeField] private StimulationOrAssistanceLevel lal = StimulationOrAssistanceLevel.Medium;

        [Tooltip("Nivel de ESL fijo. Existe por la misma razon que el de LAL, y ademas " +
                 "por una concreta: hasta el 10 de septiembre no habia " +
                 "EnvironmentalStimulationController en la escena, asi que " +
                 "BehaviorTelemetryController caia a su fallback y estampaba esl=OFF. " +
                 "El valor por omision del enum tambien es OFF, asi que el dato correcto " +
                 "y el dato por fallback se ven identicos en la base. La unica forma de " +
                 "demostrar que el cableado quedo bien es fijar un valor que NO sea OFF " +
                 "y verlo llegar.")]
        [SerializeField] private StimulationOrAssistanceLevel esl = StimulationOrAssistanceLevel.Off;

        [Tooltip("Fallback de depuracion. Si la sesion trae random_seed, gana la sesion: " +
                 "la seed es un dato de experiment_sessions, no una preferencia del Editor.")]
        [SerializeField] private int randomSeed = 20260909;

        [Tooltip("Cuantos trials. 15 o mas incluye el cruce completo (5 kanji x 3 tipos) " +
                 "mas los extras; menos reparte por tipo. S7 usa 20, S6 usa 9, S8 usa 15.")]
        [SerializeField] private int trialCount = 20;

        [Tooltip("Separacion minima entre dos apariciones del mismo kanji (spec 6.1). " +
                 "Con cinco kanji, subirla a 4 fuerza la rotacion fija 1-2-3-4-5, que es " +
                 "justo lo que 6.1 prohibe al pedir una secuencia pseudoaleatoria.")]
        [SerializeField] private int minLag = 2;

        [Tooltip("S8 difiere el feedback: es la medida de aprendizaje primaria " +
                 "y mostrar la respuesta contaminaria los trials siguientes.")]
        [SerializeField] private bool immediateFeedback = true;

        [SerializeField] private bool startOnPlay = false;

        [Tooltip("Fallback de depuracion. Si la sesion trae assigned_kanji_set, gana la sesion, " +
                 "y si los dos estan puestos y NO coinciden, la corrida se detiene.")]
        [SerializeField] private string setName = "A";

        private readonly List<KanjiItem> _items = new();
        private TrialPlan _plan;
        private int _planIndex;       // siguiente trial del plan
        private int _sequence;        // numeracion global, no se reinicia entre corridas
        private int _runRemaining;    // trials que faltan en la corrida actual

        /// <summary>
        /// El set efectivo: el de la sesion si hay sesion, el del Inspector si no.
        /// </summary>
        private string EffectiveSet =>
            SessionContext.IsInstalled && SessionContext.AssignedKanjiSet != null
                ? SessionContext.AssignedKanjiSet
                : setName;

        /// <summary>
        /// La seed efectiva. Misma regla que el set: manda la sesion.
        /// </summary>
        private int EffectiveSeed =>
            SessionContext.IsInstalled && SessionContext.RandomSeedRaw != null
                ? SessionContext.Seed
                : randomSeed;

        private void Awake()
        {
            if (responseSystem == null) responseSystem = GetComponent<ResponseSystemController>();
            if (gameFlow == null) gameFlow = GetComponent<GameFlowController>();
            if (content == null) content = FindAnyObjectByType<KanjiContentController>();
            BuildItems();
            // Las sondas toman sus opciones del plan sin pasar por StartRun, asi
            // que el plan tiene que existir desde Awake.
            BuildPlan();
        }

        private void OnEnable()
        {
            if (responseSystem != null) responseSystem.OnTrialCompleted += HandleTrialCompleted;
        }

        private void OnDisable()
        {
            if (responseSystem != null) responseSystem.OnTrialCompleted -= HandleTrialCompleted;
        }

        private void Start()
        {
            if (startOnPlay) StartRun();
        }

        [ContextMenu("Start Trial Run")]
        public void StartRun()
        {
            // Entrar de verdad al estado antes de correr. Esto emite su
            // STATE_ENTERED, actualiza el contexto de telemetria y actualiza
            // experiment_sessions.current_state en el backend. Sin esto, los
            // eventos saldrian con el estado en que se quedo el bootstrap
            // (S1) y un trial_id que dice otra cosa.
            if (gameFlow == null)
            {
                Debug.LogError("[TrialDebugRunner] Falta GameFlowController en este GameObject. " +
                               "Sin el no se puede entrar al estado y los trials saldrian con el " +
                               "estado equivocado en la telemetria.");
                return;
            }

            // Los niveles PRIMERO, el estado despues.
            //
            // Al reves --como estaba hasta el 17 de septiembre-- el
            // STATE_ENTERED salia con el par de niveles del estado anterior, y
            // la guarda del Apendice A lo cazaba en cada corrida: "S7 no admite
            // LAL=OFF". Tenia razon.
            //
            // Este banco entra con applyNominalLevels: false porque parte de su
            // trabajo es ejercitar combinaciones que la matriz prohibe --el caso
            // 6 del protocolo pone S8 con LAL=HIGH a proposito--. Si el estado
            // le pisara los niveles, esa prueba no podria existir.
            var assistance = GetComponent<LearningAssistanceController>();
            if (assistance == null)
            {
                Debug.LogError("[TrialDebugRunner] Falta LearningAssistanceController. Sin el, el LAL " +
                               "de la telemetria y el de los cues saldrian de sitios distintos.");
                return;
            }
            assistance.SetLevel(lal, betweenTrials: true);

            // ESL por el mismo camino que LAL: se fija en su dueño y la telemetria
            // lo lee de ahi. No se pasa en el request ni se copia a ningun sitio --
            // esa fue exactamente la forma de los dos bugs del 9 de septiembre.
            var stimulation = GetComponent<EnvironmentalStimulationController>();
            if (stimulation == null)
            {
                Debug.LogError("[TrialDebugRunner] Falta EnvironmentalStimulationController. " +
                               "La telemetria caeria a su fallback y estamparia esl=OFF, que es " +
                               "indistinguible de un OFF real en la base de datos.");
                return;
            }
            // La seed del entorno sale de la misma sesion que la de los trials.
            // Si el ESL sorteara sus props con otra seed, dos reconstrucciones de
            // la misma sesion verian salas distintas -- y el entorno es la
            // manipulacion, no decorado.
            stimulation.SetSeed(EffectiveSeed);
            stimulation.SetLevel(esl, betweenTrials: true);

            // Ahora si: el estado, con los niveles ya puestos.
            if (gameFlow.CurrentState != state)
                gameFlow.EnterState(state, applyNominalLevels: false);

            // El plan se reconstruye --misma seed, misma secuencia (spec 6.1)--
            // pero la numeracion global NO se reinicia: varias corridas dentro
            // del mismo Play comparten sesion, y reiniciar la secuencia
            // produciria dos trials distintos con el mismo trial_id.
            if (!BuildPlan()) return;
            _planIndex = 0;
            _runRemaining = _plan.Count;

            EmitSequence();
            Debug.Log($"[TrialDebugRunner] Arrancando {_plan.Count} trials · estado {state} · " +
                      $"LAL {lal} · ESL {esl} · " +
                      $"feedback {(immediateFeedback ? "inmediato" : "diferido")} · " +
                      $"seed {randomSeed} · numeracion desde {_sequence + 1}");
            NextTrial();
        }

        private void HandleTrialCompleted(TrialResult result)
        {
            Debug.Log($"[TrialDebugRunner] {result.TrialId} · {result.TrialType} · " +
                      $"{(result.IsCorrect ? "correcto" : "incorrecto")} · " +
                      $"{result.ResponseTimeMs} ms · {result.HintCount} hint(s)");
            NextTrial();
        }

        private void NextTrial()
        {
            if (_plan == null || _runRemaining <= 0 || _planIndex >= _plan.Count)
            {
                Debug.Log("[TrialDebugRunner] Corrida terminada.");
                return;
            }

            // El trial sale del plan, no se inventa aqui. El tipo, el kanji
            // objetivo y el orden de las cuatro opciones ya estaban decididos
            // antes del primer trial, que es lo que hace reconstruible la
            // secuencia (spec 6.1).
            var planeado = _plan.Trials[_planIndex++];
            _runRemaining--;
            _sequence++;

            // La secuencia del request es la global del banco, no la del plan:
            // el trial_id tiene que ser unico dentro de la sesion aunque se
            // corran varios planes seguidos en el mismo Play.
            responseSystem.BeginTrial(new TrialRequest(
                _sequence, planeado.Target, planeado.TrialType,
                planeado.Options, immediateFeedback));
        }

        /// <summary>
        /// Construye el plan del bloque con la seed y el set efectivos.
        /// Devuelve false si algo impide construirlo.
        /// </summary>
        private bool BuildPlan()
        {
            if (_items.Count == 0) return false;

            _plan = TrialSequenceGenerator.Build(state, _items, trialCount, minLag, EffectiveSeed);
            _planIndex = 0;
            return _plan.Count > 0;
        }

        /// <summary>
        /// Manda la secuencia planeada a la base antes de correr el primer trial.
        ///
        /// Va sin contexto de trial a proposito: no pertenece a ningun trial, es
        /// el plan de todos. Por eso TRIAL_SEQUENCE_GENERATED no esta en la lista
        /// de eventos que exigen un trial abierto.
        /// </summary>
        private void EmitSequence()
        {
            var telemetry = GetComponent<BehaviorTelemetryController>();
            if (telemetry == null || _plan == null) return;

            telemetry.Emit(TelemetryEvents.TrialSequenceGenerated, new Dictionary<string, object>
            {
                { "block_state", state.ToWireValue() },
                { "kanji_set", EffectiveSet },
                { "seed", EffectiveSeed },
                { "seed_raw", SessionContext.IsInstalled ? SessionContext.RandomSeedRaw : null },
                { "trial_count", _plan.Count },
                { "min_lag_requested", _plan.MinLag },
                { "min_lag_achieved", _plan.ShortestLag() == int.MaxValue ? -1 : _plan.ShortestLag() },
                { "distinct_pairs", _plan.DistinctPairs },
                { "ordering_attempts", _plan.OrderingAttempts },
                { "sequence", _plan.ToTelemetryRows() },
            });
        }

        // ------------------------------------------------------------------
        // Sondas de los guards
        // ------------------------------------------------------------------
        //
        // Cada una manda deliberadamente un trial mal formado. Existen porque
        // un guard que nunca se ha disparado es una afirmacion, no una
        // garantia: son la diferencia entre "el codigo comprueba el numero de
        // opciones" y "vi el codigo rechazar un trial de tres opciones".
        //
        // Las cinco deben producir un Debug.LogError del ResponseSystem y
        // **ningun evento en la base**. Si alguna deja pasar el trial, el
        // guard esta roto y la telemetria correspondiente seria basura que
        // nadie detectaria hasta el analisis.

        [ContextMenu("Probe: numero de opciones incorrecto")]
        private void ProbeWrongOptionCount()
        {
            Debug.Log("[Probe] Esperado: error de numero de opciones, trial abortado.");
            var opts = OptionsFor(0, RetrievalTrialType.KanjiToMeaning);
            opts.RemoveAt(0);                       // 3 opciones en vez de 4
            SendProbe(opts, RetrievalTrialType.KanjiToMeaning);
        }

        [ContextMenu("Probe: dos opciones correctas")]
        private void ProbeTwoCorrect()
        {
            Debug.Log("[Probe] Esperado: error de 2 opciones correctas, trial abortado.");
            var opts = OptionsFor(0, RetrievalTrialType.KanjiToMeaning);
            for (int i = 0; i < opts.Count; i++)
                opts[i] = new TrialOption(opts[i].OptionId, opts[i].DisplayText, i < 2);
            SendProbe(opts, RetrievalTrialType.KanjiToMeaning);
        }

        [ContextMenu("Probe: id de opcion duplicado")]
        private void ProbeDuplicateOption()
        {
            Debug.Log("[Probe] Esperado: error de opcion duplicada, trial abortado.");
            var opts = OptionsFor(0, RetrievalTrialType.KanjiToMeaning);
            opts[1] = new TrialOption(opts[0].OptionId, opts[1].DisplayText, false);
            SendProbe(opts, RetrievalTrialType.KanjiToMeaning);
        }

        [ContextMenu("Probe: abrir trial con otro ya abierto")]
        private void ProbeDoubleBegin()
        {
            Debug.Log("[Probe] Esperado: el primer trial se presenta, el segundo se rechaza. " +
                      "Responde el primero para dejar el sistema limpio.");
            _sequence++;
            responseSystem.BeginTrial(new TrialRequest(_sequence, _items[0],
                RetrievalTrialType.KanjiToMeaning,
                OptionsFor(0, RetrievalTrialType.KanjiToMeaning), immediateFeedback));
            responseSystem.BeginTrial(new TrialRequest(_sequence + 1, _items[1],
                RetrievalTrialType.KanjiToMeaning,
                OptionsFor(1, RetrievalTrialType.KanjiToMeaning), immediateFeedback));
        }

        [ContextMenu("Probe: cambiar LAL a media respuesta")]
        private void ProbeLalMidTrial()
        {
            var assistance = GetComponent<LearningAssistanceController>();
            if (assistance == null) { Debug.LogWarning("[Probe] Falta LearningAssistanceController."); return; }

            Debug.Log("[Probe] Esperado: cambio bloqueado (spec 10.2, LAL solo cambia entre trials).");
            assistance.SetLevel(StimulationOrAssistanceLevel.High, betweenTrials: false);
        }

        private void SendProbe(List<TrialOption> options, RetrievalTrialType trialType)
        {
            _sequence++;
            responseSystem.BeginTrial(new TrialRequest(_sequence, _items[0], trialType,
                                                       options, immediateFeedback));
        }

        /// <summary>
        /// Opciones para las sondas, pedidas al mismo generador que usa el plan.
        ///
        /// Las sondas mandan trials deliberadamente mal formados, y para eso
        /// necesitan un trial BIEN formado del que partir. Pedirselo al generador
        /// --en vez de tener aqui una segunda implementacion-- es lo que asegura
        /// que lo que rompen sea exactamente lo que el sistema recibe de verdad.
        /// </summary>
        private List<TrialOption> OptionsFor(int targetIndex, RetrievalTrialType trialType)
            => TrialSequenceGenerator.BuildOptions(
                   _items, _items[targetIndex], trialType, EffectiveSeed + targetIndex);

        private void BuildItems()
        {
            _items.Clear();

            if (content == null)
            {
                Debug.LogError("[TrialDebugRunner] Falta el KanjiContentController. Sin el no hay " +
                               "contenido que probar: este banco ya no lleva copia propia del set A.");
                return;
            }

            if (!content.IsLoaded && !content.Load()) return;

            // Si la sesion declara un set y el Inspector declara otro, se para.
            // Correr el B sobre una sesion que dice A produce datos que parecen
            // validos y no lo son -- y hasta hoy eso no daba ninguna señal.
            if (!SessionContext.AgreesWithInspector(setName, "TrialDebugRunner")) return;

            _items.AddRange(content.Set(EffectiveSet));

            if (_items.Count == 0)
                Debug.LogError($"[TrialDebugRunner] El set '{EffectiveSet}' vino vacio del contrato.");
            else
                Debug.Log($"[TrialDebugRunner] Set {EffectiveSet}" +
                          (SessionContext.IsInstalled && SessionContext.AssignedKanjiSet != null
                               ? " (de la sesion)" : " (del Inspector)") + ": " +
                          string.Join(" ", _items.Select(i => i.ToString())));
        }
    }
}

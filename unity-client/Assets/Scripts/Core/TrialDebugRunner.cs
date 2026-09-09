using System.Collections.Generic;
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
    /// Los KanjiLearningItem se crean en memoria a proposito: los assets
    /// reales llegan el lunes con KanjiContentController y kanji_content.json,
    /// y no tener que esperarlos es lo que permite verificar el ciclo hoy.
    /// </summary>
    public class TrialDebugRunner : MonoBehaviour
    {
        [SerializeField] private ResponseSystemController responseSystem;
        [SerializeField] private GameFlowController gameFlow;

        [Header("Sesion simulada")]
        [Tooltip("Estado al que se hace entrar a la sesion antes de correr. " +
                 "No se 'declara' en el trial: el GameFlowController entra de verdad, " +
                 "emite su STATE_ENTERED, y de ahi salen el bloque de contexto y el " +
                 "prefijo del trial_id.")]
        [SerializeField] private GameFlowState state = GameFlowState.S7_ExperimentalRetrieval;

        [Tooltip("Nivel de LAL fijo. En Fase 2 no lo decide nadie en runtime.")]
        [SerializeField] private StimulationOrAssistanceLevel lal = StimulationOrAssistanceLevel.Medium;

        [Tooltip("Misma seed = misma secuencia. Es el principio de spec 6.1.")]
        [SerializeField] private int randomSeed = 20260909;

        [SerializeField] private int trialCount = 3;

        [Tooltip("S8 difiere el feedback: es la medida de aprendizaje primaria " +
                 "y mostrar la respuesta contaminaria los trials siguientes.")]
        [SerializeField] private bool immediateFeedback = true;

        [SerializeField] private bool startOnPlay = false;

        // Set A oficial (Metricas_Dificultad_Kanji_Fase2, decision D4).
        // Significados en ingles: es lo que ve el participante.
        private static readonly (string id, string ch, string meaning, string reading)[] SetA =
        {
            ("KANJI_TSUKI",  "月", "moon",   "つき"),
            ("KANJI_KURUMA", "車", "car",    "くるま"),
            ("KANJI_HI",     "火", "fire",   "ひ"),
            ("KANJI_TAKE",   "竹", "bamboo", "たけ"),
            ("KANJI_ISHI",   "石", "stone",  "いし"),
        };

        private readonly List<KanjiLearningItem> _items = new();
        private System.Random _rng;
        private int _sequence;        // numeracion global, no se reinicia entre corridas
        private int _runRemaining;    // trials que faltan en la corrida actual

        private void Awake()
        {
            if (responseSystem == null) responseSystem = GetComponent<ResponseSystemController>();
            if (gameFlow == null) gameFlow = GetComponent<GameFlowController>();
            BuildItems();
            // Las sondas llaman a BuildOptions sin pasar por StartRun, asi que
            // el generador tiene que existir desde Awake.
            _rng = new System.Random(randomSeed);
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

            if (gameFlow.CurrentState != state) gameFlow.EnterState(state);

            // Igual que el estado: el nivel se fija en su dueño, no se
            // "declara" en cada trial. betweenTrials va en true porque aqui
            // no hay ninguno abierto -- si lo hubiera, el guard de spec 10.2
            // lo rechazaria, que es lo correcto.
            var assistance = GetComponent<LearningAssistanceController>();
            if (assistance == null)
            {
                Debug.LogError("[TrialDebugRunner] Falta LearningAssistanceController. Sin el, el LAL " +
                               "de la telemetria y el de los cues saldrian de sitios distintos.");
                return;
            }
            assistance.SetLevel(lal, betweenTrials: true);

            // El generador vuelve a la seed --misma seed, misma secuencia
            // (spec 6.1)-- pero la numeracion NO se reinicia: varias corridas
            // dentro del mismo Play comparten sesion, y reiniciar la secuencia
            // produciria dos trials distintos con el mismo trial_id.
            _rng = new System.Random(randomSeed);
            _runRemaining = trialCount;
            Debug.Log($"[TrialDebugRunner] Arrancando {trialCount} trials · estado {state} · " +
                      $"LAL {lal} · feedback {(immediateFeedback ? "inmediato" : "diferido")} · " +
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
            if (_runRemaining <= 0)
            {
                Debug.Log("[TrialDebugRunner] Corrida terminada.");
                return;
            }

            _sequence++;
            _runRemaining--;

            // Tipo rotando desde el inicio de ESTA corrida, para que tres
            // trials cubran T1, T2 y T3 sea cual sea la numeracion global.
            var trialType = (RetrievalTrialType)((trialCount - _runRemaining - 1) % 3);
            int targetIndex = _rng.Next(_items.Count);

            responseSystem.BeginTrial(new TrialRequest(
                _sequence, _items[targetIndex], trialType,
                BuildOptions(targetIndex, trialType), immediateFeedback));
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
            var opts = BuildOptions(0, RetrievalTrialType.KanjiToMeaning);
            opts.RemoveAt(0);                       // 3 opciones en vez de 4
            SendProbe(opts, RetrievalTrialType.KanjiToMeaning);
        }

        [ContextMenu("Probe: dos opciones correctas")]
        private void ProbeTwoCorrect()
        {
            Debug.Log("[Probe] Esperado: error de 2 opciones correctas, trial abortado.");
            var opts = BuildOptions(0, RetrievalTrialType.KanjiToMeaning);
            for (int i = 0; i < opts.Count; i++)
                opts[i] = new TrialOption(opts[i].OptionId, opts[i].DisplayText, i < 2);
            SendProbe(opts, RetrievalTrialType.KanjiToMeaning);
        }

        [ContextMenu("Probe: id de opcion duplicado")]
        private void ProbeDuplicateOption()
        {
            Debug.Log("[Probe] Esperado: error de opcion duplicada, trial abortado.");
            var opts = BuildOptions(0, RetrievalTrialType.KanjiToMeaning);
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
                BuildOptions(0, RetrievalTrialType.KanjiToMeaning), immediateFeedback));
            responseSystem.BeginTrial(new TrialRequest(_sequence + 1, _items[1],
                RetrievalTrialType.KanjiToMeaning,
                BuildOptions(1, RetrievalTrialType.KanjiToMeaning), immediateFeedback));
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
            if (_rng == null) _rng = new System.Random(randomSeed);
            _sequence++;
            responseSystem.BeginTrial(new TrialRequest(_sequence, _items[0], trialType,
                                                       options, immediateFeedback));
        }

        /// <summary>
        /// Distractores intra-set: el objetivo mas tres de los otros cuatro
        /// del mismo set, en orden barajado con la seed.
        ///
        /// La regla es de la tabla de autoria §6, y lo que la hace segura es
        /// que dentro de cada set las cinco lecturas, los cinco significados
        /// y las cinco formas son distintos -- verificado por
        /// kanji_metrics.py. Sin esa garantia, un trial podria presentar dos
        /// opciones correctas sin que nada lo detecte.
        /// </summary>
        private List<TrialOption> BuildOptions(int targetIndex, RetrievalTrialType trialType)
        {
            var pool = new List<int>();
            for (int i = 0; i < _items.Count; i++) if (i != targetIndex) pool.Add(i);

            // Fisher-Yates con la seed de la sesion: misma seed, mismas opciones
            // en el mismo orden (spec 6.1).
            for (int i = pool.Count - 1; i > 0; i--)
            {
                int j = _rng.Next(i + 1);
                (pool[i], pool[j]) = (pool[j], pool[i]);
            }

            var chosen = new List<int> { targetIndex };
            for (int i = 0; i < 3 && i < pool.Count; i++) chosen.Add(pool[i]);

            for (int i = chosen.Count - 1; i > 0; i--)
            {
                int j = _rng.Next(i + 1);
                (chosen[i], chosen[j]) = (chosen[j], chosen[i]);
            }

            var options = new List<TrialOption>(chosen.Count);
            foreach (int idx in chosen)
                options.Add(new TrialOption(SetA[idx].id, OptionText(idx, trialType), idx == targetIndex));

            return options;
        }

        /// <summary>
        /// Que se muestra en la tarjeta depende del tipo de trial: en T1 la
        /// respuesta es un kanji, en T2 un significado, en T3 una lectura.
        /// </summary>
        private static string OptionText(int index, RetrievalTrialType trialType) => trialType switch
        {
            RetrievalTrialType.MeaningToKanji => SetA[index].ch,
            RetrievalTrialType.KanjiToMeaning => SetA[index].meaning,
            RetrievalTrialType.KanjiToReading => SetA[index].reading,
            _ => SetA[index].ch,
        };

        private void BuildItems()
        {
            _items.Clear();
            foreach (var (id, ch, meaning, reading) in SetA)
            {
                var item = ScriptableObject.CreateInstance<KanjiLearningItem>();
                item.name = id;                        // es el kanji_id de la telemetria
                item.character = ch;
                item.meaning = meaning;
                item.targetMeaning = meaning;
                item.primaryTargetReading = reading;
                item.experimentalSet = "A";
                _items.Add(item);
            }
        }
    }
}

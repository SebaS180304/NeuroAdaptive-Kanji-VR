using System;
using System.Collections.Generic;
using System.Linq;
using NeuroAdaptiveVR.Data;
using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// ESL Controller (spec seccion 8 / 14): "One scene, one controller"
    /// -- LOW/MEDIUM/HIGH son configuraciones de parametros de la misma
    /// escena, nunca escenas separadas.
    ///
    /// Controla exclusivamente densidad de props, objetos en movimiento y
    /// eventos perifericos. Nunca lighting, UI, contenido, dificultad, cantidad
    /// de respuestas, tiempo, audio ni scoring (spec 8.3).
    ///
    /// COMO SE GARANTIZA ESA LISTA
    /// ---------------------------
    /// No leyendo 8.3 antes de cada cambio. Este componente sostiene UNA
    /// referencia --`environmentalLayerRoot`-- y no puede alcanzar nada fuera de
    /// ese subarbol. El Learning Board, la Response Area, la iluminacion y el
    /// suelo cuelgan de otro sitio, asi que "ESL toco el board" deja de ser algo
    /// que haya que revisar y pasa a ser estructuralmente imposible.
    ///
    /// Es el mismo movimiento que la ruta unica de audio pre-respuesta en
    /// PronunciationAudioController y que haber quitado las copias de state/esl/lal
    /// de BehaviorTelemetryController. Un hecho, un sitio.
    ///
    /// FASE: el nivel se fija por configuracion. La adaptacion dinamica real
    /// llega en Fase 5 (M3) y solo dentro de S7.
    /// </summary>
    public class EnvironmentalStimulationController : MonoBehaviour
    {
        [Header("Frontera de contencion")]
        [Tooltip("Raiz de la Environmental Layer. TODO lo que ESL puede tocar cuelga " +
                 "de aqui, y nada de lo que ESL no puede tocar cuelga de aqui. El suelo, " +
                 "por ejemplo, esta deliberadamente fuera.")]
        [SerializeField] private Transform environmentalLayerRoot;

        [Header("Perfiles (spec 8.1)")]
        [Tooltip("Uno por nivel. Un nivel sin perfil no se aplica: ver SetLevel.")]
        [SerializeField] private EnvironmentProfile[] profiles = Array.Empty<EnvironmentProfile>();

        [Header("Telemetria")]
        [SerializeField] private BehaviorTelemetryController telemetry;

        [Header("Reproducibilidad")]
        [Tooltip("Seed con la que se sortean los conteos dentro del rango del perfil. " +
                 "DEUDA: deberia venir de experiment_sessions.random_seed, que existe " +
                 "en la base desde M1 y todavia nadie consume. Mientras tanto se fija " +
                 "aqui y se registra en el evento, para que al menos quede en el dato " +
                 "con que seed se genero el entorno.")]
        [SerializeField] private int seed = 20260909;

        [SerializeField]
        private StimulationOrAssistanceLevel currentLevel = StimulationOrAssistanceLevel.Off;

        private EnvironmentProfile _activeProfile;
        private System.Random _rngBacking;
        private bool _warnedNoRoot;

        /// <summary>
        /// Perezoso a proposito. Inicializarlo solo en Awake deja el componente
        /// roto con un NullReference si alguien llama SetLevel antes --desde
        /// herramientas de editor, o si el orden de ejecucion cambia--. Un
        /// generador que se crea cuando hace falta no tiene ese modo de fallo.
        /// </summary>
        private System.Random Rng => _rngBacking ??= new System.Random(seed);

        public StimulationOrAssistanceLevel CurrentLevel => currentLevel;
        public EnvironmentProfile ActiveProfile => _activeProfile;

        /// <summary>Se dispara cuando un perfil se aplica de verdad.</summary>
        public event Action<EnvironmentProfile> OnProfileApplied;

        private void Awake()
        {
            if (telemetry == null) telemetry = GetComponent<BehaviorTelemetryController>();
            _rngBacking = new System.Random(seed);
            VerifyContainment();
        }

        /// <summary>
        /// La seed la debe fijar quien conoce la sesion, antes del primer SetLevel.
        /// </summary>
        public void SetSeed(int newSeed)
        {
            seed = newSeed;
            _rngBacking = new System.Random(seed);
        }

        /// <summary>
        /// Cambia el nivel de estimulacion ambiental.
        ///
        /// El guard de timing es de spec 10.2: una adaptacion ocurre entre trials,
        /// nunca mientras el participante esta respondiendo. Cambiar el entorno a
        /// media respuesta contaminaria el tiempo de respuesta de ese trial, que es
        /// la medida primaria.
        /// </summary>
        public void SetLevel(StimulationOrAssistanceLevel newLevel, bool betweenTrials)
        {
            if (!betweenTrials)
            {
                Debug.LogError("[EnvironmentalStimulationController] Bloqueado: el ESL solo " +
                               "puede cambiar entre trials, nunca mientras el participante " +
                               "responde (spec 10.2).");
                return;
            }

            var profile = profiles.FirstOrDefault(p => p != null && p.level == newLevel);
            if (profile == null)
            {
                // Deliberadamente NO se cambia currentLevel.
                //
                // La alternativa --aceptar el nivel y no aplicar nada-- produciria
                // telemetria que dice MEDIUM sobre una escena que sigue en LOW. Es
                // exactamente la forma de los dos bugs del 9 de septiembre: un valor
                // que gobierna el dato y otro que gobierna lo que se ve.
                Debug.LogError($"[EnvironmentalStimulationController] No hay perfil para " +
                               $"{newLevel}. El nivel NO cambia: aceptarlo sin aplicarlo " +
                               $"dejaria la telemetria diciendo {newLevel} sobre una escena " +
                               $"que sigue en {currentLevel}.");
                return;
            }

            currentLevel = newLevel;
            _activeProfile = profile;
            Apply(profile);
        }

        // ------------------------------------------------------------------
        // Aplicacion
        // ------------------------------------------------------------------

        private void Apply(EnvironmentProfile profile)
        {
            if (environmentalLayerRoot == null)
            {
                if (!_warnedNoRoot)
                {
                    _warnedNoRoot = true;
                    Debug.LogError("[EnvironmentalStimulationController] Falta " +
                                   "environmentalLayerRoot. El nivel cambia en la telemetria " +
                                   "pero la escena no cambia -- que es justo la discrepancia " +
                                   "que este componente existe para impedir.");
                }
                return;
            }

            int propCount = ActivateGroup("Props", profile.propCountMin, profile.propCountMax, profile.maxTier);
            int moverCount = ActivateGroup("Movers", profile.moverCountMin, profile.moverCountMax, profile.maxTier);

            Debug.Log($"[EnvironmentalStimulationController] {profile.level}: " +
                      $"{propCount} props · {moverCount} movers · " +
                      $"eventos perifericos {(profile.HasPeripheralEvents ? $"cada {profile.peripheralIntervalMinSeconds:0.#}-{profile.peripheralIntervalMaxSeconds:0.#}s" : "ninguno")} " +
                      $"· seed {seed}");

            EmitApplied(profile, propCount, moverCount);
            OnProfileApplied?.Invoke(profile);
        }

        /// <summary>
        /// Activa `count` objetos del grupo, sorteando dentro del rango y
        /// respetando el tope de tier. Los que sobran se desactivan: el estado
        /// anterior no puede quedar colgando.
        /// </summary>
        private int ActivateGroup(string groupName, int min, int max, int maxTier)
        {
            var group = environmentalLayerRoot.Find(groupName);
            if (group == null)
            {
                Debug.LogWarning($"[EnvironmentalStimulationController] No existe " +
                                 $"{environmentalLayerRoot.name}/{groupName}.");
                return 0;
            }

            var all = group.GetComponentsInChildren<EnvironmentProp>(true).ToList();

            // Primero se apagan todos. Aplicar un nivel es poner la escena en un
            // estado, no acumular sobre el anterior.
            foreach (var p in all) p.gameObject.SetActive(false);

            var eligible = all.Where(p => p.Tier <= maxTier).ToList();
            int target = Mathf.Clamp(NextInclusive(min, max), 0, eligible.Count);

            if (max > eligible.Count)
            {
                Debug.LogWarning($"[EnvironmentalStimulationController] El perfil pide hasta " +
                                 $"{max} en {groupName} y solo hay {eligible.Count} objetos con " +
                                 $"tier <= {maxTier}. Se activan {target}. Faltan objetos en la " +
                                 $"escena, no es un fallo de configuracion del perfil.");
            }

            // Orden: por tier ascendente --para que el nivel alto conserve lo del
            // bajo y anada encima-- y barajado dentro de cada tier con la seed,
            // para que no sea siempre el mismo subconjunto pero si sea el mismo
            // para la misma seed.
            var ordered = eligible
                .GroupBy(p => p.Tier)
                .OrderBy(g => g.Key)
                .SelectMany(g => Shuffle(g.ToList()))
                .ToList();

            for (int i = 0; i < target; i++) ordered[i].gameObject.SetActive(true);
            return target;
        }

        private int NextInclusive(int min, int max) => max <= min ? min : Rng.Next(min, max + 1);

        private List<T> Shuffle<T>(List<T> items)
        {
            for (int i = items.Count - 1; i > 0; i--)
            {
                int j = Rng.Next(i + 1);
                (items[i], items[j]) = (items[j], items[i]);
            }
            return items;
        }

        // ------------------------------------------------------------------
        // Telemetria
        // ------------------------------------------------------------------

        private void EmitApplied(EnvironmentProfile profile, int propCount, int moverCount)
        {
            if (telemetry == null) return;

            // Fijate en lo que NO va aqui: el nivel. Ya viaja en el bloque de
            // contexto como `esl`, estampado por BehaviorTelemetryController desde
            // este mismo componente. Repetirlo en el payload crearia dos copias del
            // mismo hecho en la misma fila, que es la forma de falla que este
            // proyecto lleva cinco veces encontrando.
            telemetry.Emit(TelemetryEvents.EnvironmentApplied, new Dictionary<string, object>
            {
                { "profile_name", profile.name },
                { "prop_count", propCount },
                { "mover_count", moverCount },
                { "peripheral_interval_min_ms", Mathf.RoundToInt(profile.peripheralIntervalMinSeconds * 1000f) },
                { "peripheral_interval_max_ms", Mathf.RoundToInt(profile.peripheralIntervalMaxSeconds * 1000f) },
                { "max_tier", profile.maxTier },
                { "seed", seed },
            });
        }

        // ------------------------------------------------------------------
        // Contencion
        // ------------------------------------------------------------------

        /// <summary>
        /// La frontera del comentario de cabecera es una promesa hasta que algo
        /// la comprueba. Un EnvironmentProp colgado fuera de la Environmental
        /// Layer no daria error: simplemente no se activaria nunca, y alguien
        /// perderia una tarde buscando por que.
        /// </summary>
        private void VerifyContainment()
        {
            if (environmentalLayerRoot == null) return;

            // Sin FindObjectsSortMode: Unity 6.3 deprecó la sobrecarga que lo
            // lleva. Aquí el orden nunca importó -- solo se busca lo que está
            // fuera de sitio para gritarlo.
            var stray = FindObjectsByType<EnvironmentProp>(FindObjectsInactive.Include)
                .Where(p => !p.transform.IsChildOf(environmentalLayerRoot))
                .ToList();

            foreach (var p in stray)
            {
                Debug.LogError($"[EnvironmentalStimulationController] '{p.name}' tiene " +
                               $"EnvironmentProp pero no cuelga de " +
                               $"{environmentalLayerRoot.name}. ESL no puede alcanzarlo, asi " +
                               $"que nunca se va a activar ni desactivar.", p);
            }
        }
    }
}

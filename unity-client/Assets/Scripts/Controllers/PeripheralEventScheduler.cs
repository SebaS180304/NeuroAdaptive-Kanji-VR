using System.Collections.Generic;
using System.Linq;
using NeuroAdaptiveVR.Data;
using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Programa los eventos visuales no relacionados con la tarea, segun el
    /// intervalo del perfil ESL activo (spec 8.1: LOW ninguno, MEDIUM ~1 cada
    /// 25-35 s, HIGH ~1 cada 10-15 s).
    ///
    /// NO decide el intervalo: lo lee del perfil que aplico
    /// EnvironmentalStimulationController. Si lo tuviera en campos propios,
    /// habria dos sitios diciendo cada cuanto ocurre un evento periferico, y la
    /// telemetria registraria uno mientras la escena obedece al otro.
    ///
    /// Los valores de 8.1 estan marcados "to validate" en 16: el intervalo real
    /// lo fija el piloto midiendo distraccion y confort.
    /// </summary>
    public class PeripheralEventScheduler : MonoBehaviour
    {
        [SerializeField] private EnvironmentalStimulationController stimulation;
        [SerializeField] private BehaviorTelemetryController telemetry;

        [Tooltip("Cuanto dura visible cada evento periferico.")]
        [SerializeField] private float eventDurationSeconds = 1.5f;

        private EnvironmentProfile _profile;
        private readonly List<GameObject> _pool = new();
        private float _nextEventAt = -1f;
        private GameObject _active;
        private float _activeUntil;
        private int _eventIndex;
        private bool _warnedEmptyPool;

        private void Awake()
        {
            if (stimulation == null) stimulation = GetComponent<EnvironmentalStimulationController>();
            if (telemetry == null) telemetry = GetComponent<BehaviorTelemetryController>();
        }

        private void OnEnable()
        {
            if (stimulation != null) stimulation.OnProfileApplied += HandleProfileApplied;
        }

        private void OnDisable()
        {
            if (stimulation != null) stimulation.OnProfileApplied -= HandleProfileApplied;
        }

        private void HandleProfileApplied(EnvironmentProfile profile)
        {
            _profile = profile;
            HideActive();
            RebuildPool();

            if (profile == null || !profile.HasPeripheralEvents)
            {
                _nextEventAt = -1f;    // LOW y FOCUS: sin eventos perifericos
                return;
            }
            ScheduleNext();
        }

        private void RebuildPool()
        {
            _pool.Clear();
            var container = FindContainer();
            if (container == null) return;

            foreach (Transform child in container)
            {
                _pool.Add(child.gameObject);
                child.gameObject.SetActive(false);
            }
        }

        private Transform FindContainer()
        {
            // El contenedor se localiza a traves del mismo root que usa ESL, no
            // por una referencia propia: si el scheduler pudiera apuntar a otro
            // sitio, podria animar cosas fuera de la Environmental Layer, y la
            // frontera de contencion dejaria de serlo.
            var root = GameObject.Find("EnvironmentalLayer");
            return root == null ? null : root.transform.Find("PeripheralEvents");
        }

        private void ScheduleNext()
        {
            float min = _profile.peripheralIntervalMinSeconds;
            float max = _profile.peripheralIntervalMaxSeconds;
            _nextEventAt = Time.time + Random.Range(min, max);
        }

        private void Update()
        {
            if (_active != null && Time.time >= _activeUntil) HideActive();
            if (_nextEventAt < 0f || _profile == null) return;
            if (Time.time < _nextEventAt) return;

            Fire();
            ScheduleNext();
        }

        private void Fire()
        {
            if (_pool.Count == 0)
            {
                if (!_warnedEmptyPool)
                {
                    _warnedEmptyPool = true;
                    Debug.LogWarning("[PeripheralEventScheduler] El perfil pide eventos " +
                                     "perifericos pero EnvironmentalLayer/PeripheralEvents esta " +
                                     "vacio. El intervalo corre y no ocurre nada: en Fase 2 los " +
                                     "objetos son placeholder y llegan con el contenido.");
                }
                return;
            }

            _active = _pool[Random.Range(0, _pool.Count)];
            _active.SetActive(true);
            _activeUntil = Time.time + eventDurationSeconds;
            _eventIndex++;

            // Se registra porque Fase 5 necesita poder correlacionar una
            // distraccion concreta con lo que hizo el participante justo despues.
            // Un evento periferico que ocurre y no deja rastro es una variable
            // que actuo sobre la sesion y no se puede reconstruir.
            telemetry?.Emit(TelemetryEvents.PeripheralEvent, new Dictionary<string, object>
            {
                { "event_index", _eventIndex },
                { "object_name", _active.name },
                { "duration_ms", Mathf.RoundToInt(eventDurationSeconds * 1000f) },
            });
        }

        private void HideActive()
        {
            if (_active == null) return;
            _active.SetActive(false);
            _active = null;
        }
    }
}

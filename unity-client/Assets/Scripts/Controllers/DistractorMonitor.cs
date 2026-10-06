using System.Collections.Generic;
using NeuroAdaptiveVR.Core;
using NeuroAdaptiveVR.Data;
using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// F5a, D5: emits DISTRACTOR_INTERACTION (EVENT_CONTRACT.md 5.11) when the
    /// environment takes the participant's attention, so the estimator can tell
    /// "the room took it" (lower the ESL) from "the head went elsewhere"
    /// (floor, ceiling, controllers).
    ///
    /// - DWELL: the head stays on an active prop, mover or peripheral, outside
    ///   the task region of D7, for DwellMinMs. Emitted when the dwell ends.
    /// - ORIENTING: within OrientingWindowMs of a PERIPHERAL_EVENT, the head
    ///   turns OrientingMinDeg toward the object. Emitted when the window ends;
    ///   no turn, no row.
    ///
    /// It reuses HeadAwayMonitor's angles (yaw/pitch relative to the head→board
    /// direction) and its thresholds as the task region, so the two events can
    /// never disagree about where the task is. The detectors are plain C#
    /// (DistractorBehavior.cs, harness case X7); this component only feeds them
    /// the angles and the boxes of the objects active right now, and emits.
    ///
    /// Limits measured on 6 Oct (Medicion_D7_HeadAway.md): looks made with the
    /// eyes only produce nothing, and the object named in a DWELL is the nearest
    /// box, often a neighbour of the one actually looked at.
    /// </summary>
    public class DistractorMonitor : MonoBehaviour
    {
        private const string Log = "[DistractorMonitor]";

        [SerializeField] private BehaviorTelemetryController telemetry;
        [SerializeField] private GameFlowController gameFlow;
        [SerializeField] private HeadAwayMonitor headAway;
        [SerializeField] private PeripheralEventScheduler peripherals;

        [Header("Thresholds — TO VALIDATE (F5a D5)")]
        [SerializeField] private DistractorThresholds thresholds = DistractorThresholds.Default;
        [Tooltip("Movers move: the boxes are recomputed this often.")]
        [SerializeField] private float boxRefreshSeconds = 0.2f;

        private Transform _layer;
        private DwellDetector _dwell;
        private OrientingDetector _orienting;
        private readonly List<AngularBox> _boxes = new();
        private double _nextRefresh;
        private Transform _orientingTarget;

        public IReadOnlyList<AngularBox> Boxes => _boxes;

        private void Awake()
        {
            if (telemetry == null) telemetry = FindAnyObjectByType<BehaviorTelemetryController>();
            if (gameFlow == null) gameFlow = FindAnyObjectByType<GameFlowController>();
            if (headAway == null) headAway = FindAnyObjectByType<HeadAwayMonitor>();
            if (peripherals == null) peripherals = FindAnyObjectByType<PeripheralEventScheduler>();
            var layer = GameObject.Find("EnvironmentalLayer");
            if (layer != null) _layer = layer.transform;
            _dwell = new DwellDetector(thresholds);
            _orienting = new OrientingDetector(thresholds);
            if (headAway == null || _layer == null)
                Debug.LogError($"{Log} Missing HeadAwayMonitor or EnvironmentalLayer: DISTRACTOR_INTERACTION will not be measured.");
        }

        private void OnEnable()
        {
            if (peripherals != null) peripherals.OnPeripheralFired += HandlePeripheral;
        }

        private void OnDisable()
        {
            if (peripherals != null) peripherals.OnPeripheralFired -= HandlePeripheral;
            if (_dwell != null) EmitDwell(_dwell.ForceClose(), Time.realtimeSinceStartupAsDouble);
        }

        // LateUpdate: HeadAwayMonitor has already computed this frame's angles.
        private void LateUpdate()
        {
            if (headAway == null || _layer == null) return;
            if (gameFlow == null || gameFlow.CurrentState == GameFlowState.S0_SessionInitialization) return;
            _dwell.Thresholds = thresholds;        // Inspector edits apply live
            _orienting.Thresholds = thresholds;
            double now = Time.realtimeSinceStartupAsDouble;

            if (now >= _nextRefresh)
            {
                RefreshBoxes();
                _nextRefresh = now + boxRefreshSeconds;
            }

            bool tracked = headAway.Tracked;
            float yaw = headAway.YawDeg, pitch = headAway.PitchDeg;
            if (!tracked) EmitDwell(_dwell.ForceClose(), now);
            else EmitDwell(_dwell.Step(now, yaw, pitch, !headAway.InsideTaskRegion(yaw, pitch), _boxes), now);

            if (_orienting.Pending)
                EmitOrienting(_orienting.Step(now, DistanceToTarget(yaw, pitch), tracked), now);
        }

        private void HandlePeripheral(GameObject obj, int eventIndex)
        {
            if (headAway == null || obj == null) return;
            double now = Time.realtimeSinceStartupAsDouble;
            _orientingTarget = obj.transform;
            EmitOrienting(_orienting.Begin(now, obj.name, eventIndex, DistanceToTarget(headAway.YawDeg, headAway.PitchDeg)), now);
        }

        private float DistanceToTarget(float yaw, float pitch)
        {
            if (_orientingTarget == null || !TryBox(_orientingTarget, "PERIPHERAL", out var box)) return 0f;
            return box.DistanceToCentre(yaw, pitch);
        }

        // ------------------------------------------------------------------
        // Boxes of the objects active right now
        // ------------------------------------------------------------------

        private void RefreshBoxes()
        {
            _boxes.Clear();
            foreach (var prop in _layer.GetComponentsInChildren<EnvironmentProp>(false))
            {
                string group = prop.transform.parent != null && prop.transform.parent.name == "Movers" ? "MOVER" : "PROP";
                if (TryBox(prop.transform, group, out var box)) _boxes.Add(box);
            }
            var container = _layer.Find("PeripheralEvents");
            if (container != null)
                foreach (Transform child in container)
                    if (child.gameObject.activeInHierarchy && TryBox(child, "PERIPHERAL", out var box))
                        _boxes.Add(box);
        }

        private bool TryBox(Transform t, string group, out AngularBox box)
        {
            box = new AngularBox { Name = t.name, Group = group, YawMin = float.MaxValue, YawMax = float.MinValue,
                                   PitchMin = float.MaxValue, PitchMax = float.MinValue };
            bool any = false;
            foreach (var r in t.GetComponentsInChildren<Renderer>(false))
            {
                if (r is ParticleSystemRenderer || !r.enabled) continue;
                var b = r.bounds;
                for (int i = 0; i < 8; i++)
                {
                    var c = new Vector3((i & 1) == 0 ? b.min.x : b.max.x, (i & 2) == 0 ? b.min.y : b.max.y,
                                        (i & 4) == 0 ? b.min.z : b.max.z);
                    if (!headAway.TryAngles(c, out float y, out float p)) return false;
                    box.YawMin = Mathf.Min(box.YawMin, y); box.YawMax = Mathf.Max(box.YawMax, y);
                    box.PitchMin = Mathf.Min(box.PitchMin, p); box.PitchMax = Mathf.Max(box.PitchMax, p);
                    any = true;
                }
            }
            return any;
        }

        // ------------------------------------------------------------------
        // Emission
        // ------------------------------------------------------------------

        private void EmitDwell(DwellDetector.Result? result, double now)
        {
            if (result == null || telemetry == null) return;
            var r = result.Value;
            var fields = Common("DWELL", r.ObjectName, r.ObjectGroup, now, r.OnsetT);
            fields["duration_ms"] = r.DurationMs;
            fields["peripheral_event_index"] = null;
            fields["head_turn_deg"] = Round1(r.CentreDistanceDeg);
            fields["box_distance_deg"] = Round1(r.BoxDistanceDeg);
            telemetry.Emit(TelemetryEvents.DistractorInteraction, fields);
            Debug.Log($"{Log} DWELL {r.ObjectName} ({r.ObjectGroup}) {r.DurationMs} ms");
        }

        private void EmitOrienting(OrientingDetector.Result? result, double now)
        {
            if (result == null || telemetry == null) return;
            var r = result.Value;
            var fields = Common("ORIENTING", r.ObjectName, "PERIPHERAL", now, r.OnsetT);
            fields["duration_ms"] = r.PeakMs;
            fields["peripheral_event_index"] = r.EventIndex;
            fields["head_turn_deg"] = Round1(r.TurnDeg);
            fields["box_distance_deg"] = null;
            telemetry.Emit(TelemetryEvents.DistractorInteraction, fields);
            Debug.Log($"{Log} ORIENTING to {r.ObjectName} (#{r.EventIndex}) turn {r.TurnDeg:0.0} deg");
        }

        private Dictionary<string, object> Common(string kind, string name, string group, double now, double onset)
        {
            var th = thresholds;
            return new Dictionary<string, object>
            {
                { "kind", kind },
                { "object_name", name },
                { "object_group", group },
                { "onset_offset_ms", -(int)System.Math.Round((now - onset) * 1000.0) },
                { "dwell_min_ms", th.DwellMinMs },
                { "dwell_break_ms", th.DwellBreakMs },
                { "box_margin_deg", th.BoxMarginDeg },
                { "orienting_min_deg", th.OrientingMinDeg },
                { "orienting_window_ms", th.OrientingWindowMs },
            };
        }

        private static float Round1(float v) => Mathf.Round(v * 10f) / 10f;
    }
}

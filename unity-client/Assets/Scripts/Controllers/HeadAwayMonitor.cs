using System.Collections.Generic;
using NeuroAdaptiveVR.Core;
using NeuroAdaptiveVR.Data;
using UnityEngine;
using UnityEngine.XR;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Phase 3, F3.3: notices when the participant looks away from the task and
    /// emits HEAD_AWAY / HEAD_RETURNED (EVENT_CONTRACT.md 5.10). Also measures,
    /// every frame, how fast the head and the controller rays turn, which the
    /// response system uses for idle time.
    ///
    /// The angles are those of the head's forward relative to the direction from
    /// the head to the Learning Board's centre, recomputed each frame from the
    /// current head position. The state machine lives in HeadAwayDetector (plain
    /// C#, tested by harness case X4); this component only feeds it and emits.
    ///
    /// Runs from the first state after S0 until the session ends, in every state
    /// (S4 included: Phase 4 needs the episodes wherever there is EEG), and only
    /// while the headset is tracked. Thresholds are provisional and marked
    /// *to validate*.
    /// </summary>
    public class HeadAwayMonitor : MonoBehaviour
    {
        private const string Log = "[HeadAwayMonitor]";

        [SerializeField] private BehaviorTelemetryController telemetry;
        [SerializeField] private GameFlowController gameFlow;
        [Tooltip("The participant's head (Main Camera).")]
        [SerializeField] private Transform head;
        [Tooltip("Centre of the task: the Learning Board canvas.")]
        [SerializeField] private Transform board;
        [Tooltip("Left and right controllers; their forward is the ray.")]
        [SerializeField] private Transform[] controllers;

        [Header("Provisional thresholds — TO VALIDATE in the phase test (7-8 Oct)")]
        [SerializeField] private HeadAwayThresholds thresholds = HeadAwayThresholds.Default;
        [Tooltip("Off only for Editor tests without a headset.")]
        [SerializeField] private bool requireHeadsetTracking = true;
        [Tooltip("Angular speeds are measured over this window, not frame to frame: per-frame " +
                 "differences are dominated by tracking jitter (30 Sep headset pass: idle was 0 in " +
                 "every trial with 5 and 10 deg/s thresholds).")]
        [SerializeField] private float speedWindowSeconds = 0.25f;

        public float HeadDegPerSec { get; private set; }
        public float RayDegPerSec { get; private set; }
        public bool Tracked { get; private set; }
        public float YawDeg { get; private set; }
        public float PitchDeg { get; private set; }

        private HeadAwayDetector _detector;

        private struct Pose
        {
            public double T;
            public Vector3 Head;
            public Vector3[] Rays;   // null entry = controller not tracked in that frame
        }
        private readonly List<Pose> _history = new();

        private void Awake()
        {
            if (telemetry == null) telemetry = FindAnyObjectByType<BehaviorTelemetryController>();
            if (gameFlow == null) gameFlow = FindAnyObjectByType<GameFlowController>();
            if (head == null && Camera.main != null) head = Camera.main.transform;
            if (board == null)
            {
                var b = GameObject.Find("BoardCanvas");
                if (b != null) board = b.transform;
            }
            if (controllers == null || controllers.Length == 0)
            {
                var found = new List<Transform>();
                foreach (var n in new[] { "Left Controller", "Right Controller" })
                    foreach (var t in FindObjectsByType<Transform>(FindObjectsInactive.Include))
                        if (t.name == n) { found.Add(t); break; }
                controllers = found.ToArray();
            }
            _detector = new HeadAwayDetector(thresholds);
            if (head == null || board == null)
                Debug.LogError($"{Log} Missing head or board: HEAD_AWAY will not be measured.");
        }

        private void Update()
        {
            if (head == null || board == null) return;
            _detector.Thresholds = thresholds;   // Inspector edits apply live
            double now = Time.realtimeSinceStartupAsDouble;

            // Angular speeds, for idle time: the angle turned over the last
            // speedWindowSeconds, divided by that time. Jitter does not add up
            // over a window the way it does frame to frame.
            Vector3 fwd = head.forward;
            var pose = new Pose { T = now, Head = fwd, Rays = new Vector3[controllers.Length] };
            var tracked = new bool[controllers.Length];
            for (int i = 0; i < controllers.Length; i++)
            {
                var c = controllers[i];
                tracked[i] = c != null && c.gameObject.activeInHierarchy;
                if (tracked[i]) pose.Rays[i] = c.forward;
            }
            _history.Add(pose);
            // Keep the newest pose that is at least one window old, and drop the rest.
            while (_history.Count > 2 && now - _history[1].T >= speedWindowSeconds) _history.RemoveAt(0);
            var old = _history[0];
            double span = now - old.T;
            if (span > 1e-3)
            {
                HeadDegPerSec = (float)(Vector3.Angle(old.Head, fwd) / span);
                float ray = 0f;
                for (int i = 0; i < controllers.Length; i++)
                    if (tracked[i] && old.Rays[i] != Vector3.zero)
                        ray = Mathf.Max(ray, (float)(Vector3.Angle(old.Rays[i], pose.Rays[i]) / span));
                RayDegPerSec = ray;
            }

            if (gameFlow == null || gameFlow.CurrentState == GameFlowState.S0_SessionInitialization) return;

            Tracked = !requireHeadsetTracking || HeadsetTracked();
            if (!Tracked)
            {
                Emit(_detector.ForceClose(now, "TRACKING_LOST"));
                return;
            }

            Vector3 toBoard = board.position - head.position;
            YawDeg = Mathf.DeltaAngle(Yaw(toBoard), Yaw(fwd));
            PitchDeg = Pitch(fwd) - Pitch(toBoard);
            Emit(_detector.Step(now, YawDeg, PitchDeg));
        }

        private void OnDisable()
        {
            if (_detector != null) Emit(_detector.ForceClose(Time.realtimeSinceStartupAsDouble, "SESSION_END"));
        }

        private static float Yaw(Vector3 v) => Mathf.Atan2(v.x, v.z) * Mathf.Rad2Deg;
        private static float Pitch(Vector3 v) => Mathf.Asin(Mathf.Clamp(v.normalized.y, -1f, 1f)) * Mathf.Rad2Deg;

        private static bool HeadsetTracked()
        {
            var dev = InputDevices.GetDeviceAtXRNode(XRNode.Head);
            return dev.isValid && dev.TryGetFeatureValue(CommonUsages.isTracked, out bool t) && t;
        }

        private void Emit(HeadAwayDetector.Result? result)
        {
            if (result == null || telemetry == null) return;
            var r = result.Value;
            var th = thresholds;
            if (r.Kind == HeadAwayDetector.Kind.Away)
            {
                telemetry.Emit(TelemetryEvents.HeadAway, new Dictionary<string, object>
                {
                    { "episode", r.Episode },
                    { "onset_offset_ms", r.OnsetOffsetMs },
                    { "yaw_deg", Round1(r.YawDeg) },
                    { "pitch_deg", Round1(r.PitchDeg) },
                    { "limit", r.Limit },
                    { "yaw_limit_deg", th.YawLimitDeg },
                    { "pitch_up_limit_deg", th.PitchUpLimitDeg },
                    { "pitch_down_limit_deg", th.PitchDownLimitDeg },
                    { "min_away_ms", th.MinAwayMs },
                });
                Debug.Log($"{Log} HEAD_AWAY #{r.Episode} ({r.Limit}) yaw {r.YawDeg:0.0} pitch {r.PitchDeg:0.0}");
            }
            else
            {
                telemetry.Emit(TelemetryEvents.HeadReturned, new Dictionary<string, object>
                {
                    { "episode", r.Episode },
                    { "duration_ms", r.DurationMs },
                    { "max_abs_yaw_deg", Round1(r.MaxAbsYawDeg) },
                    { "max_pitch_up_deg", Round1(r.MaxPitchUpDeg) },
                    { "max_pitch_down_deg", Round1(r.MaxPitchDownDeg) },
                    { "reason", r.Reason },
                    { "hysteresis_deg", th.HysteresisDeg },
                    { "min_return_ms", th.MinReturnMs },
                });
                Debug.Log($"{Log} HEAD_RETURNED #{r.Episode} after {r.DurationMs} ms ({r.Reason})");
            }
        }

        private static float Round1(float v) => Mathf.Round(v * 10f) / 10f;
    }
}

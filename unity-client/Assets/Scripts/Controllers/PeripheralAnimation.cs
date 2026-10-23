using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// How one peripheral animal moves while PeripheralEventScheduler shows it
    /// (Diseno_Sala_ESL.md §10.2; D-F6-22, D-F6-23, D-F6-27, D-F6-28). Blender makes
    /// the mesh, Unity moves it: this object stays at the rest pose and keeps the
    /// telemetry id (PeripheralEvent_*); its child "Model" travels along the §10.2
    /// path. Parts named Wing* or Head* under Model flap or turn. Wing
    /// pivots sit at the shoulder in Model axes, at the pose of the Blender mesh (bird:
    /// folded; butterfly: flat), and swing about the body axis (23B and 26B animation sheets).
    ///
    /// Paths are in world coordinates (room v148, eye at 1.60 m), quadratic Béziers
    /// (start, control, end):
    /// - Bird: in along (pathStart, pathControl, rest) in inSeconds, perched
    ///   restSeconds, out along the same curve reversed in outSeconds (0.4 / 0.7 / 0.4).
    /// - Butterfly: in along (pathStart, pathControl, rest), then out along (rest,
    ///   outControl, outEnd); no rest; a ±4 cm vertical ripple at 1 Hz on top.
    /// - Cat: the one exception to "Unity moves it" (D-F6-38). Its rigged 25B mesh plays
    ///   the baked EVENTO clip of its window (8.08 s, D-F6-39): it walks in along the
    ///   outer sill, stands turning its head towards the room, turns round and walks
    ///   out, the root's walk baked in the clip. Model stays put at the stop, facing
    ///   along the sill; nothing here moves its bones.
    ///
    /// Every path starts and ends hidden (behind the paper half and the curtain, or
    /// beyond 42°), so an animal never pops in or out (rule 9 of
    /// Diseno_UI_Kanji_Studio_v1.md). Periodic motion stays at or under 3 Hz. The pose
    /// is a pure function of the time since it was shown: same seed, same animal,
    /// same movement; the harness samples it (X9, E13).
    /// </summary>
    public class PeripheralAnimation : MonoBehaviour
    {
        public enum Kind { Bird, Cat, Butterfly }

        [SerializeField] private Kind kind = Kind.Bird;
        [SerializeField] private Vector3 pathStart;
        [SerializeField] private Vector3 pathControl;
        [Tooltip("Butterfly only: the way out.")]
        [SerializeField] private Vector3 outControl;
        [SerializeField] private Vector3 outEnd;
        [SerializeField] private float inSeconds = 0.4f;
        [SerializeField] private float restSeconds = 0.7f;
        [SerializeField] private float outSeconds = 0.4f;
        [Tooltip("Cat only: the baked EVENTO clip of this window (D-F6-38).")]
        [SerializeField] private AnimationClip bakedClip;

        // CatGaitHz: the step rate of the baked walk (25B sheet), under the 3 Hz rule.
        private const float WingHz = 3f, CatGaitHz = 1.5f, RippleHz = 1f, RippleM = 0.04f;
        /// <summary>A flying bird's wings, raised from folded (0°) to glide, beating ±35° within the sheet's 10°-80°.</summary>
        public const float OpenWingDeg = 45f;
        /// <summary>The butterfly's wings never close below 10° (26B sheet: 10°-80°).</summary>
        public const float ButterflyMinWingDeg = 10f;

        // Not kept across editor reloads, so a mesh swapped in by the editor tools is picked up.
        [System.NonSerialized] private Transform _model;
        [System.NonSerialized] private Transform[] _wings, _heads;
        [System.NonSerialized] private Quaternion[] _wingRest, _headRest;
        private float _shownAt;

        public float DurationSeconds => kind == Kind.Cat && bakedClip != null ? bakedClip.length : inSeconds + restSeconds + outSeconds;
        public float RestSeconds => restSeconds;
        public float RateHz => Mathf.Max(kind == Kind.Cat ? CatGaitHz : WingHz, RippleHz);
        public Kind AnimalKind => kind;
        public AnimationClip BakedClip => bakedClip;
        public Transform Model => Init() ? _model : null;

        private void Awake() => Init();

        // Lazy so the harness can sample poses in edit mode, where Awake does not run on inactive objects.
        private bool Init()
        {
            if (_model != null) return true;
            _model = transform.Find("Model");
            if (_model == null) { Debug.LogError($"[PeripheralAnimation] {name} has no Model child."); enabled = false; return false; }
            _wings = Parts("Wing"); _heads = Parts("Head");
            // Wing pivots are built at the mesh's own pose (PeripheralMeshIntegration): their rest is identity, never the pose last sampled.
            _wingRest = System.Array.ConvertAll(_wings, _ => Quaternion.identity); _headRest = Rest(_heads);
            return true;
        }

        private Transform[] Parts(string prefix)
        {
            var list = new System.Collections.Generic.List<Transform>();
            foreach (var t in _model.GetComponentsInChildren<Transform>(true))
                if (t != _model && t.name.StartsWith(prefix)) list.Add(t);
            return list.ToArray();
        }

        private static Quaternion[] Rest(Transform[] ts)
        {
            var q = new Quaternion[ts.Length];
            for (int i = 0; i < ts.Length; i++) q[i] = ts[i].localRotation;
            return q;
        }

        private void OnEnable()
        {
            _shownAt = Time.time;
            Pose(0f);
        }

        private void Update() => Pose(Time.time - _shownAt);

        private static Vector3 Bezier(Vector3 a, Vector3 c, Vector3 b, float u)
        {
            u = Mathf.Clamp01(u);
            float v = 1f - u;
            return v * v * a + 2f * v * u * c + u * u * b;
        }

        private static float Smooth(float x) { x = Mathf.Clamp01(x); return x * x * (3f - 2f * x); }

        /// <summary>World position of the model at t seconds after being shown, and whether it is travelling.</summary>
        public Vector3 PathAt(float t, out bool moving)
        {
            Vector3 rest = transform.position;
            moving = true;
            switch (kind)
            {
                case Kind.Butterfly:
                    Vector3 p = t < inSeconds
                        ? Bezier(pathStart, pathControl, rest, Smooth(t / inSeconds))
                        : Bezier(rest, outControl, outEnd, Smooth((t - inSeconds - restSeconds) / outSeconds));
                    return p + new Vector3(0f, RippleM * Mathf.Sin(2f * Mathf.PI * RippleHz * t), 0f);
                default: // bird
                    if (t < inSeconds) return Bezier(pathStart, pathControl, rest, Smooth(t / inSeconds));
                    if (t < inSeconds + restSeconds) { moving = false; return rest; }
                    return Bezier(pathStart, pathControl, rest, Smooth(1f - (t - inSeconds - restSeconds) / outSeconds));
            }
        }

        /// <summary>The pose at t seconds after being shown; public so the harness can sample it.</summary>
        public void Pose(float t)
        {
            if (!Init()) return;
            if (kind == Kind.Cat)
            {
                if (bakedClip != null && _model.childCount > 0) bakedClip.SampleAnimation(_model.GetChild(0).gameObject, Mathf.Min(t, bakedClip.length));
                return;
            }
            Vector3 world = PathAt(t, out bool moving);
            Vector3 ahead = PathAt(t + 0.02f, out _);
            _model.position = world;
            Vector3 dir = ahead - world; dir.y = 0f;
            if (moving && dir.sqrMagnitude > 1e-8f) _model.rotation = Quaternion.LookRotation(dir.normalized);
            else if (!moving) _model.rotation = Quaternion.LookRotation(Vector3.back);

            float tin = t - inSeconds;
            switch (kind)
            {
                case Kind.Bird:        // wings open, gliding with a beat of at most 3 Hz in flight; folded along the body (the mesh's pose) and a head turn when perched
                    Swing(_wings, _wingRest, moving ? OpenWingDeg + 35f * Mathf.Sin(2f * Mathf.PI * WingHz * t) : 0f, Vector3.forward, true);
                    Swing(_heads, _headRest, moving ? 0f : 25f * Mathf.Sin(Mathf.PI * Mathf.Clamp01(tin / restSeconds)), Vector3.up, false);
                    break;
                case Kind.Butterfly:   // wings at 3 Hz the whole time
                    Swing(_wings, _wingRest, ButterflyMinWingDeg + 60f * Mathf.Abs(Mathf.Sin(Mathf.PI * WingHz * t)), Vector3.forward, true);
                    break;
            }
        }

        /// <summary>Rotates parts about a local axis; mirrored parts (name ends in L) swing the other way.</summary>
        private static void Swing(Transform[] parts, Quaternion[] rest, float deg, Vector3 axis, bool mirror)
        {
            for (int i = 0; i < parts.Length; i++)
            {
                float d = mirror && parts[i].name.EndsWith("L") ? -deg : deg;
                parts[i].localRotation = rest[i] * Quaternion.AngleAxis(d, axis);
            }
        }
    }
}

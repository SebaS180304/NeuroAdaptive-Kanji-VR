using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// How one peripheral animal moves while PeripheralEventScheduler shows it
    /// (D-F6-22, D-F6-23, D-F6-27, D-F6-28). Blender makes the mesh, Unity moves it:
    /// this object stays at the rest pose (the old sphere's position, so the
    /// telemetry name and the seeded draw keep one entry per position), and its
    /// child "Model" travels in and out. Parts named Wing*, Tail* or Head* under
    /// Model flap or sway.
    ///
    /// No pop-in and no luminance change (rule 9 of Diseno_UI_Kanji_Studio_v1.md):
    /// every animal enters and leaves from outside the view or behind something
    /// (entryOffset), never by appearing in place. Periodic motion stays at or
    /// under 3 Hz. Timing is deterministic from the moment it is shown, so the
    /// same seed shows the same animal doing the same thing.
    /// </summary>
    public class PeripheralAnimation : MonoBehaviour
    {
        public enum Kind { Bird, Cat, Butterfly }

        [SerializeField] private Kind kind = Kind.Bird;

        [Tooltip("Total time visible: bird 1.5 s, cat 4.0 s, butterfly 3.0 s.")]
        [SerializeField] private float durationSeconds = 1.5f;

        [Tooltip("Where the model starts and ends, relative to the rest pose: outside the view or behind a wall.")]
        [SerializeField] private Vector3 entryOffset = new(0.9f, 0.6f, 1.2f);

        [Tooltip("Where it leaves to; zero = the way it came.")]
        [SerializeField] private Vector3 exitOffset = Vector3.zero;

        [Tooltip("Seconds still at the rest pose (bird about 0.7 s).")]
        [SerializeField] private float restSeconds = 0.7f;

        [Tooltip("Flap or sway rate; the design caps it at 3 Hz.")]
        [SerializeField, Range(0.5f, 3f)] private float rateHz = 3f;

        private Transform _model;
        private Transform[] _wings, _tails, _heads;
        private Quaternion[] _wingRest, _tailRest, _headRest;
        private float _shownAt;

        public float DurationSeconds => durationSeconds;
        public float RestSeconds => restSeconds;
        public float RateHz => rateHz;
        public Kind AnimalKind => kind;
        public Transform Model => Init() ? _model : null;

        private void Awake() => Init();

        // Lazy so the harness can sample poses in edit mode, where Awake does not run on inactive objects.
        private bool Init()
        {
            if (_model != null) return true;
            _model = transform.Find("Model");
            if (_model == null) { Debug.LogError($"[PeripheralAnimation] {name} has no Model child."); enabled = false; return false; }
            _wings = Parts("Wing"); _tails = Parts("Tail"); _heads = Parts("Head");
            _wingRest = Rest(_wings); _tailRest = Rest(_tails); _headRest = Rest(_heads);
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

        /// <summary>The pose at t seconds after being shown; public so the harness can sample it.</summary>
        public void Pose(float t)
        {
            if (!Init()) return;
            float travel = Mathf.Max(0.01f, (durationSeconds - restSeconds) * 0.5f);
            Vector3 exit = exitOffset == Vector3.zero ? entryOffset : exitOffset;
            Vector3 offset;
            bool moving;
            if (t < travel) { offset = Vector3.Lerp(entryOffset, Vector3.zero, Smooth(t / travel)); moving = true; }
            else if (t < travel + restSeconds) { offset = Vector3.zero; moving = false; }
            else { offset = Vector3.Lerp(Vector3.zero, exit, Smooth((t - travel - restSeconds) / travel)); moving = true; }

            // The butterfly never flies straight: a small vertical wobble on its path, at the flap rate.
            if (kind == Kind.Butterfly) offset += new Vector3(0f, 0.03f * Mathf.Sin(2f * Mathf.PI * rateHz * 0.5f * t), 0f);
            _model.localPosition = offset;
            if (offset.sqrMagnitude > 1e-6f && kind != Kind.Cat)
                _model.localRotation = Quaternion.LookRotation(new Vector3(-offset.x, 0f, -offset.z).normalized + new Vector3(0f, 0f, 1e-4f));
            else
                _model.localRotation = Quaternion.identity;

            float phase = Mathf.Sin(2f * Mathf.PI * rateHz * t);
            switch (kind)
            {
                case Kind.Bird:        // wings beat while flying, folded while perched
                    Swing(_wings, _wingRest, moving ? 55f * phase : 0f, Vector3.forward, true);
                    break;
                case Kind.Butterfly:   // wings beat the whole time
                    Swing(_wings, _wingRest, 60f * Mathf.Abs(phase), Vector3.forward, true);
                    break;
                case Kind.Cat:         // tail sways, head turns slowly once towards the room
                    Swing(_tails, _tailRest, 20f * phase, Vector3.up, false);
                    float look = Mathf.Clamp01((t - travel) / Mathf.Max(0.01f, restSeconds));
                    Swing(_heads, _headRest, 25f * Mathf.Sin(Mathf.PI * look), Vector3.up, false);
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

        private static float Smooth(float x) { x = Mathf.Clamp01(x); return x * x * (3f - 2f * x); }
    }
}

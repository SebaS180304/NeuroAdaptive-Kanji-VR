using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using TMPro;
using UnityEngine;
using UnityEngine.XR;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// MEASUREMENT TOOL (F5a, D7 · Planteamiento_Tecnico_F5a.md §7.1). Not in the
    /// scene: it is added at runtime through the MCP for a measurement pass and
    /// leaves nothing behind when Play stops.
    ///
    /// Every <see cref="sampleIntervalSeconds"/> it writes the head yaw and pitch
    /// relative to the head→board direction, computed exactly as HeadAwayMonitor
    /// does, so the numbers can be used as thresholds without conversion. The
    /// right controller's A button adds a mark (with a short haptic pulse); B
    /// adds an UNDO mark that cancels the previous one.
    ///
    /// <see cref="DumpTargets"/> writes, for every target of the walk (board,
    /// cards, Hint button, props, movers, peripherals, windows), the angular box
    /// of its renderers (or RectTransform) seen from the current head position:
    /// that is where the target IS, while the samples say where the head
    /// actually POINTS when looking at it.
    ///
    /// <see cref="SetPrompts"/> (optional) shows the current target of the walk in
    /// the headset, below the board centre: A confirms it and moves to the next
    /// one, B goes back. Every sample carries the id of the prompt on screen, so
    /// the walk labels itself and continuous segments (reading, quick glances)
    /// can be analysed whole.
    ///
    /// Output: unity-client/Logs/HeadProbe/ (ignored by git).
    /// </summary>
    public class HeadAngleProbe : MonoBehaviour
    {
        private const string Log = "[HeadAngleProbe]";
        private static readonly CultureInfo Inv = CultureInfo.InvariantCulture;

        [SerializeField] private Transform head;
        [SerializeField] private Transform board;
        [SerializeField] private float sampleIntervalSeconds = 0.05f;

        public string SamplesPath { get; private set; }
        public string TargetsPath { get; private set; }
        public int Marks { get; private set; }
        public int Samples { get; private set; }

        private StreamWriter _samples;
        private double _start, _nextSample;
        private bool _aWas, _bWas;
        private string _pendingMark = "";
        private string[] _promptIds = Array.Empty<string>();
        private string[] _promptTexts = Array.Empty<string>();
        private int _prompt;
        private TextMeshPro _label;

        public string CurrentPromptId => _prompt < _promptIds.Length ? _promptIds[_prompt] : "";

        private void Awake()
        {
            if (head == null && Camera.main != null) head = Camera.main.transform;
            if (board == null)
            {
                var b = GameObject.Find("BoardCanvas");
                if (b != null) board = b.transform;
            }
            string dir = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "Logs", "HeadProbe"));
            Directory.CreateDirectory(dir);
            string stamp = DateTime.Now.ToString("yyyyMMdd_HHmmss", Inv);
            SamplesPath = Path.Combine(dir, $"head_probe_{stamp}_samples.csv");
            TargetsPath = Path.Combine(dir, $"head_probe_{stamp}_targets.csv");
            _samples = new StreamWriter(SamplesPath, false, new UTF8Encoding(false));
            _samples.WriteLine("t_ms,yaw_deg,pitch_deg,head_x,head_y,head_z,head_deg_s,tracked,mark,mark_kind,prompt");
            _start = Time.realtimeSinceStartupAsDouble;
            _nextSample = _start;
            Debug.Log($"{Log} Writing {SamplesPath}");
        }

        private Vector3 _lastFwd;
        private double _lastT;

        private void Update()
        {
            if (head == null || board == null) return;
            double now = Time.realtimeSinceStartupAsDouble;

            var right = InputDevices.GetDeviceAtXRNode(XRNode.RightHand);
            bool a = right.isValid && right.TryGetFeatureValue(CommonUsages.primaryButton, out bool av) && av;
            bool b = right.isValid && right.TryGetFeatureValue(CommonUsages.secondaryButton, out bool bv) && bv;
            if (a && !_aWas) Mark("MARK", right);
            if (b && !_bWas) Mark("UNDO", right);
            _aWas = a;
            _bWas = b;

            if (now < _nextSample && _pendingMark.Length == 0) return;
            _nextSample = now + sampleIntervalSeconds;

            Vector3 fwd = head.forward;
            Vector3 toBoard = board.position - head.position;
            float yaw = Mathf.DeltaAngle(Yaw(toBoard), Yaw(fwd));
            float pitch = Pitch(fwd) - Pitch(toBoard);
            float speed = _lastT > 0 && now > _lastT ? (float)(Vector3.Angle(_lastFwd, fwd) / (now - _lastT)) : 0f;
            _lastFwd = fwd;
            _lastT = now;

            var hd = InputDevices.GetDeviceAtXRNode(XRNode.Head);
            bool tracked = hd.isValid && hd.TryGetFeatureValue(CommonUsages.isTracked, out bool tr) && tr;
            var p = head.position;
            string kind = _pendingMark;
            string promptId = _pendingPromptId ?? CurrentPromptId;
            _samples.WriteLine(string.Join(",",
                ((int)Math.Round((now - _start) * 1000.0)).ToString(Inv),
                F(yaw), F(pitch), F(p.x, 3), F(p.y, 3), F(p.z, 3), F(speed), tracked ? "1" : "0",
                kind.Length > 0 ? Marks.ToString(Inv) : "", kind, promptId));
            Samples++;
            _pendingMark = "";
            _pendingPromptId = null;
        }

        private string _pendingPromptId;

        private void Mark(string kind, InputDevice device)
        {
            if (kind == "MARK") Marks++;
            _pendingMark = kind;
            _pendingPromptId = CurrentPromptId;   // the mark belongs to the target it confirms
            if (_promptIds.Length > 0)
            {
                _prompt = kind == "MARK" ? Math.Min(_prompt + 1, _promptIds.Length) : Math.Max(_prompt - 1, 0);
                RefreshLabel();
            }
            device.SendHapticImpulse(0, kind == "MARK" ? 0.6f : 0.3f, kind == "MARK" ? 0.08f : 0.25f);
            Debug.Log($"{Log} {kind} {Marks}");
        }

        /// <summary>Shows the walk in the headset. ids go to the CSV; texts to the label.</summary>
        public void SetPrompts(string[] ids, string[] texts)
        {
            _promptIds = ids ?? Array.Empty<string>();
            _promptTexts = texts ?? Array.Empty<string>();
            _prompt = 0;
            if (_label == null && board != null && head != null)
            {
                var go = new GameObject("HeadAngleProbe Prompt");
                go.transform.SetParent(transform, false);
                Vector3 toHead = (head.position - board.position).normalized;
                go.transform.position = board.position - board.up * 0.30f + toHead * 0.04f;
                go.transform.rotation = board.rotation;
                _label = go.AddComponent<TextMeshPro>();
                _label.fontSize = 0.9f;
                _label.alignment = TextAlignmentOptions.Center;
                _label.color = new Color(1f, 0.85f, 0.25f);
                _label.outlineWidth = 0.25f;
                _label.outlineColor = Color.black;
                _label.rectTransform.sizeDelta = new Vector2(1.4f, 0.3f);
            }
            RefreshLabel();
        }

        private void RefreshLabel()
        {
            if (_label == null) return;
            _label.text = _prompt < _promptTexts.Length
                ? $"{_prompt + 1}/{_promptTexts.Length} · {_promptTexts[_prompt]}\n<size=60%>A = listo · B = atrás</size>"
                : "Fin. Avísale a Claude.";
        }

        /// <summary>Angular boxes of the walk targets from the current head position.</summary>
        public string DumpTargets()
        {
            if (head == null || board == null) return "missing head or board";
            var rows = new List<string> { "target,group,active,yaw_min,yaw_max,pitch_min,pitch_max,yaw_centre,pitch_centre,dist_m" };
            void Add(Transform t, string group)
            {
                if (t == null) return;
                var corners = Corners(t);
                if (corners.Count == 0) return;
                Vector3 toBoard = board.position - head.position;
                float yMin = 999, yMax = -999, pMin = 999, pMax = -999;
                Vector3 centre = Vector3.zero;
                foreach (var c in corners)
                {
                    Vector3 d = c - head.position;
                    float y = Mathf.DeltaAngle(Yaw(toBoard), Yaw(d));
                    float pt = Pitch(d) - Pitch(toBoard);
                    yMin = Mathf.Min(yMin, y); yMax = Mathf.Max(yMax, y);
                    pMin = Mathf.Min(pMin, pt); pMax = Mathf.Max(pMax, pt);
                    centre += c;
                }
                centre /= corners.Count;
                Vector3 dc = centre - head.position;
                rows.Add(string.Join(",", t.name, group, t.gameObject.activeInHierarchy ? "1" : "0",
                    F(yMin), F(yMax), F(pMin), F(pMax),
                    F(Mathf.DeltaAngle(Yaw(toBoard), Yaw(dc))), F(Pitch(dc) - Pitch(toBoard)), F(dc.magnitude, 2)));
            }

            Add(board, "TASK");
            foreach (var n in new[] { "Card1", "Card2", "Card3", "Card4", "HintButton" }) Add(Find(n), "TASK");
            foreach (var prop in FindObjectsByType<Controllers.EnvironmentProp>(FindObjectsInactive.Include))
                Add(prop.transform, prop.transform.parent != null && prop.transform.parent.name == "Movers" ? "MOVER" : "PROP");
            foreach (var n in new[] { "PeripheralEvent_WindowLeft", "PeripheralEvent_WindowRight", "PeripheralEvent_Shelf" }) Add(Find(n), "PERIPHERAL");
            foreach (var n in new[] { "WindowFrame_Left", "WindowFrame_Right" }) Add(Find(n), "ROOM");

            File.WriteAllLines(TargetsPath, rows, new UTF8Encoding(false));
            Debug.Log($"{Log} Targets written: {TargetsPath} ({rows.Count - 1})");
            return TargetsPath;
        }

        private static Transform Find(string name)
        {
            foreach (var t in FindObjectsByType<Transform>(FindObjectsInactive.Include))
                if (t.name == name) return t;
            return null;
        }

        private static List<Vector3> Corners(Transform t)
        {
            var list = new List<Vector3>();
            if (t is RectTransform rt && t.GetComponentInChildren<Renderer>(true) == null)
            {
                var c = new Vector3[4];
                rt.GetWorldCorners(c);
                list.AddRange(c);
                return list;
            }
            foreach (var r in t.GetComponentsInChildren<Renderer>(true))
            {
                if (r is ParticleSystemRenderer) continue;
                var b = r.bounds;
                for (int i = 0; i < 8; i++)
                    list.Add(new Vector3(
                        (i & 1) == 0 ? b.min.x : b.max.x,
                        (i & 2) == 0 ? b.min.y : b.max.y,
                        (i & 4) == 0 ? b.min.z : b.max.z));
            }
            return list;
        }

        private void OnDestroy() => Close();
        private void OnApplicationQuit() => Close();

        private void Close()
        {
            if (_samples == null) return;
            _samples.Flush();
            _samples.Dispose();
            _samples = null;
            Debug.Log($"{Log} Closed: {Samples} samples, {Marks} marks.");
        }

        public void Flush() => _samples?.Flush();

        private static float Yaw(Vector3 v) => Mathf.Atan2(v.x, v.z) * Mathf.Rad2Deg;
        private static float Pitch(Vector3 v) => Mathf.Asin(Mathf.Clamp(v.normalized.y, -1f, 1f)) * Mathf.Rad2Deg;
        private static string F(float v, int digits = 1) => Math.Round(v, digits).ToString(Inv);
    }
}

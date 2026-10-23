using System.Globalization;
using System.IO;
using NeuroAdaptiveVR.Data;
using UnityEngine;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// Frame rate per block of the session, written as the run goes (D-F6-57: "72 Hz sin tirones").
    /// On 23 Oct a headset run through Link stopped in S5 while the editor was compiling a command to
    /// sample the frame rate live; this measures instead, with nothing to run during the session. At every
    /// state change (and when Play stops) it logs one line and appends it to Logs/framerate.csv next to
    /// Assets: block, seconds, mean fps, frames over 20 ms and the worst frame.
    /// </summary>
    public class FrameRateLog : MonoBehaviour
    {
        /// <summary>The numbers of one block, from frame times only (harness case X15).</summary>
        public class Stats
        {
            public int Frames, Over20Ms;
            public float Seconds, WorstMs;
            public float MeanFps => Seconds > 0f ? Frames / Seconds : 0f;

            public void Add(float deltaSeconds)
            {
                Frames++;
                Seconds += deltaSeconds;
                float ms = deltaSeconds * 1000f;
                if (ms > 20f) Over20Ms++;
                if (ms > WorstMs) WorstMs = ms;
            }
        }

        private GameFlowController _flow;
        private GameFlowState _state;
        private Stats _stats = new();
        private string _path;

        private void Awake()
        {
            _flow = FindAnyObjectByType<GameFlowController>();
            _path = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "Logs", "framerate.csv"));
            Directory.CreateDirectory(Path.GetDirectoryName(_path));
            if (!File.Exists(_path)) File.WriteAllText(_path, "logged_at,block,seconds,mean_fps,frames,frames_over_20ms,worst_ms\n");
        }

        private void Update()
        {
            var state = _flow != null ? _flow.CurrentState : default;
            if (state != _state) { Write(); _state = state; _stats = new Stats(); }
            _stats.Add(Time.unscaledDeltaTime);
        }

        private void OnDisable() => Write();

        private void Write()
        {
            if (_stats.Frames == 0) return;
            var c = CultureInfo.InvariantCulture;
            string line = string.Format(c, "{0:yyyy-MM-ddTHH:mm:ss},{1},{2:F1},{3:F1},{4},{5},{6:F1}",
                                        System.DateTime.Now, _state, _stats.Seconds, _stats.MeanFps, _stats.Frames, _stats.Over20Ms, _stats.WorstMs);
            Debug.Log($"[FrameRate] {_state} · {_stats.Seconds:F0} s · {_stats.MeanFps:F1} fps · {_stats.Over20Ms} frames > 20 ms · worst {_stats.WorstMs:F0} ms");
            File.AppendAllText(_path, line + "\n");
            _stats = new Stats();
        }
    }
}

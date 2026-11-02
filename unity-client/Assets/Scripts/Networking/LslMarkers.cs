using System;
using System.Collections.Generic;
using Newtonsoft.Json;
using UnityEngine;

namespace NeuroAdaptiveVR.Networking
{
    /// <summary>
    /// The LSL marker stream of the session (F4, D-F6-74; Planteamiento_Tecnico_F4.md §2.1). LabRecorder
    /// records it next to the AURA EEG in the session's XDF, so every event lands on the EEG's clock.
    /// One string channel, irregular rate; each sample is a JSON object: "event" (the event type) plus
    /// the event's own payload (trial_id and the rest), as sent to the backend. Stamped with LSL's
    /// local clock at the moment of the push.
    ///
    /// Recorded in the three conditions (F4 §1, principle 1). If liblsl does not load, it logs once and
    /// the session goes on without markers: the XDF then misses the stream and the session does not count
    /// as multimodal (P9 of D-F6-127), which the backend records.
    /// </summary>
    public static class LslMarkers
    {
        public const string StreamName = "UnityMarkers";
        public const string StreamType = "Markers";
        /// <summary>Survives a restart of Unity, so LabRecorder picks the stream up again.</summary>
        public static readonly string SourceId = $"neuroadaptive-unity-{Environment.MachineName}";

        private static LSL.StreamOutlet _outlet;
        private static bool _failed;

        public static void Push(string eventType, IDictionary<string, object> payload = null)
        {
            var outlet = Outlet();
            if (outlet == null) return;
            var sample = new Dictionary<string, object>(payload ?? new Dictionary<string, object>()) { ["event"] = eventType };
            outlet.push_sample(new[] { JsonConvert.SerializeObject(sample) });
        }

        private static LSL.StreamOutlet Outlet()
        {
            if (_outlet != null || _failed) return _outlet;
            try
            {
                var info = new LSL.StreamInfo(StreamName, StreamType, 1, LSL.LSL.IRREGULAR_RATE,
                                              LSL.channel_format_t.cf_string, SourceId);
                _outlet = new LSL.StreamOutlet(info);
            }
            catch (Exception e)   // a missing liblsl, or any error of its own: never stop the session
            {
                _failed = true;
                Debug.LogError($"[LslMarkers] No LSL marker stream ({e.GetType().Name}: {e.Message}). " +
                               "The session goes on; its XDF will not count as multimodal.");
            }
            return _outlet;
        }
    }
}

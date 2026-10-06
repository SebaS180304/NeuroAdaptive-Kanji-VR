using System;
using System.Collections.Generic;
using UnityEngine;

namespace NeuroAdaptiveVR.Data
{
    /// <summary>
    /// Thresholds of DISTRACTOR_INTERACTION (F5a, D5; EVENT_CONTRACT.md 5.11).
    /// Set in the Inspector of DistractorMonitor, carried in every row, and
    /// marked *to validate* like those of HEAD_AWAY.
    /// </summary>
    [Serializable]
    public struct DistractorThresholds
    {
        [Tooltip("TO VALIDATE. A dwell on the room counts from this length on.")]
        public int DwellMinMs;
        [Tooltip("TO VALIDATE. Margin around each object's angular box. The head points short of what the " +
                 "eyes look at (measured 6 Oct: 2-5 deg below low objects), so the box has to be wider than the object.")]
        public float BoxMarginDeg;
        [Tooltip("TO VALIDATE. A dwell survives a break shorter than this (tracking jitter, a glance back).")]
        public int DwellBreakMs;
        [Tooltip("TO VALIDATE. Turn toward a peripheral event that counts as orienting.")]
        public float OrientingMinDeg;
        [Tooltip("TO VALIDATE. Window after a peripheral event in which the turn is looked for.")]
        public int OrientingWindowMs;

        public static DistractorThresholds Default => new()
        {
            DwellMinMs = 1000, BoxMarginDeg = 3f, DwellBreakMs = 200,
            OrientingMinDeg = 10f, OrientingWindowMs = 2000,
        };
    }

    /// <summary>
    /// Angular box of one room object seen from the head, in the HeadAwayMonitor
    /// frame (yaw/pitch relative to the head→board direction).
    /// </summary>
    public struct AngularBox
    {
        public string Name;
        public string Group;          // PROP, MOVER, PERIPHERAL
        public float YawMin, YawMax, PitchMin, PitchMax;

        public float CentreYaw => (YawMin + YawMax) * 0.5f;
        public float CentrePitch => (PitchMin + PitchMax) * 0.5f;

        /// <summary>Angular distance from (yaw, pitch) to the box; 0 inside.</summary>
        public float DistanceTo(float yaw, float pitch)
        {
            float dy = Math.Max(Math.Max(YawMin - yaw, 0f), yaw - YawMax);
            float dp = Math.Max(Math.Max(PitchMin - pitch, 0f), pitch - PitchMax);
            return (float)Math.Sqrt(dy * dy + dp * dp);
        }

        public float DistanceToCentre(float yaw, float pitch)
        {
            float dy = yaw - CentreYaw, dp = pitch - CentrePitch;
            return (float)Math.Sqrt(dy * dy + dp * dp);
        }
    }

    /// <summary>
    /// DWELL (D5, variant A): the head stays on the room, outside the task region
    /// of D7 and within <see cref="DistractorThresholds.BoxMarginDeg"/> of an
    /// active prop, mover or peripheral, for at least DwellMinMs. One dwell is
    /// one continuous stretch, even if the head drifts from one object to the
    /// next; its object is the one the head was nearest to for longest.
    ///
    /// Which object is a best guess. Measured on 6 Oct, the head lands within
    /// the margin of SOME active object for almost every head-turned look at the
    /// room, but often of the neighbour (plant → lamp, chair → curtain): the eyes
    /// do the last few degrees. `env_dwell_ms` in the estimator only needs the
    /// first; the object name is for reading the session, not for statistics.
    ///
    /// Plain C# so the harness can drive it frame by frame (case X7).
    /// </summary>
    public sealed class DwellDetector
    {
        public struct Result
        {
            public string ObjectName, ObjectGroup;
            public double OnsetT;
            public int DurationMs;
            public float BoxDistanceDeg;      // nearest the head got to the object's box (0 = inside)
            public float CentreDistanceDeg;   // nearest the head got to the object's centre
        }

        public DistractorThresholds Thresholds;
        public bool InDwell => _start.HasValue;

        private double? _start;
        private double _lastOn;
        private readonly Dictionary<string, double> _timeOn = new();
        private readonly Dictionary<string, (string group, float box, float centre)> _best = new();
        private double _lastT;

        public DwellDetector(DistractorThresholds thresholds) { Thresholds = thresholds; }

        /// <summary>
        /// One frame. `outsideTask`: the head is outside the D7 task region and
        /// tracked. `boxes`: the active room objects this frame.
        /// </summary>
        public Result? Step(double t, float yaw, float pitch, bool outsideTask, IReadOnlyList<AngularBox> boxes)
        {
            double dt = _lastT > 0 ? Math.Max(0, t - _lastT) : 0;
            _lastT = t;

            int nearest = -1;
            float nearestDist = float.MaxValue;
            if (outsideTask && boxes != null)
                for (int i = 0; i < boxes.Count; i++)
                {
                    float d = boxes[i].DistanceTo(yaw, pitch);
                    if (d < nearestDist) { nearestDist = d; nearest = i; }
                }
            bool on = nearest >= 0 && nearestDist <= Thresholds.BoxMarginDeg;

            if (on)
            {
                var b = boxes[nearest];
                if (!_start.HasValue) { _start = t; _timeOn.Clear(); _best.Clear(); dt = 0; }
                _lastOn = t;
                _timeOn[b.Name] = (_timeOn.TryGetValue(b.Name, out var s) ? s : 0) + dt;
                float centre = b.DistanceToCentre(yaw, pitch);
                if (!_best.TryGetValue(b.Name, out var prev))
                    _best[b.Name] = (b.Group, nearestDist, centre);
                else
                    _best[b.Name] = (b.Group, Math.Min(prev.box, nearestDist), Math.Min(prev.centre, centre));
                return null;
            }

            if (_start.HasValue && (t - _lastOn) * 1000.0 >= Thresholds.DwellBreakMs) return Close();
            return null;
        }

        /// <summary>Closes an open dwell (tracking lost, session end). Null if it was too short.</summary>
        public Result? ForceClose() => _start.HasValue ? Close() : null;

        private Result? Close()
        {
            double start = _start.Value;
            int ms = (int)Math.Round((_lastOn - start) * 1000.0);
            _start = null;
            if (ms < Thresholds.DwellMinMs || _timeOn.Count == 0) return null;

            string name = null;
            double most = -1;
            foreach (var kv in _timeOn)
                if (kv.Value > most || (kv.Value == most && string.CompareOrdinal(kv.Key, name) < 0)) { most = kv.Value; name = kv.Key; }
            var best = _best[name];
            return new Result
            {
                ObjectName = name, ObjectGroup = best.group, OnsetT = start, DurationMs = ms,
                BoxDistanceDeg = best.box, CentreDistanceDeg = best.centre,
            };
        }
    }

    /// <summary>
    /// ORIENTING (D5, variant B): within OrientingWindowMs of a PERIPHERAL_EVENT,
    /// the head turns at least OrientingMinDeg toward the object that appeared.
    /// The turn is how much the angular distance from the head to the object
    /// shrank since the event fired. Decided when the window ends; no turn, no
    /// row (the rate is counted against PERIPHERAL_EVENT).
    /// </summary>
    public sealed class OrientingDetector
    {
        public struct Result
        {
            public string ObjectName;
            public int EventIndex;
            public double OnsetT;
            public float TurnDeg;
            public int PeakMs;        // from the peripheral event to the largest turn
        }

        public DistractorThresholds Thresholds;
        public bool Pending => _onset.HasValue;

        private double? _onset;
        private string _name;
        private int _index;
        private float _startDist, _maxTurn;
        private double _peakT;

        public OrientingDetector(DistractorThresholds thresholds) { Thresholds = thresholds; }

        /// <summary>
        /// A peripheral event fired. Closes a still-open window first (null if it
        /// had no turn). Distances are head→object-centre at this frame.
        /// </summary>
        public Result? Begin(double t, string objectName, int eventIndex, float headToObjectDeg)
        {
            var previous = _onset.HasValue ? Decide() : null;
            _onset = t;
            _name = objectName;
            _index = eventIndex;
            _startDist = headToObjectDeg;
            _maxTurn = 0f;
            _peakT = t;
            return previous;
        }

        /// <summary>One frame of a pending window. Returns the row when the window ends with a turn.</summary>
        public Result? Step(double t, float headToObjectDeg, bool tracked)
        {
            if (!_onset.HasValue) return null;
            if (tracked)
            {
                float turn = _startDist - headToObjectDeg;
                if (turn > _maxTurn) { _maxTurn = turn; _peakT = t; }
            }
            if ((t - _onset.Value) * 1000.0 < Thresholds.OrientingWindowMs) return null;
            return Decide();
        }

        private Result? Decide()
        {
            var r = new Result
            {
                ObjectName = _name, EventIndex = _index, OnsetT = _onset.Value, TurnDeg = _maxTurn,
                PeakMs = (int)Math.Round((_peakT - _onset.Value) * 1000.0),
            };
            _onset = null;
            return r.TurnDeg >= Thresholds.OrientingMinDeg ? r : (Result?)null;
        }
    }
}

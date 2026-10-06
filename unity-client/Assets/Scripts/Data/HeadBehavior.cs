using System;
using System.Collections.Generic;
using UnityEngine;

namespace NeuroAdaptiveVR.Data
{
    /// <summary>
    /// Thresholds of the head-away detector (EVENT_CONTRACT.md 5.10). Set in the
    /// Inspector of HeadAwayMonitor; every row carries the values it was measured
    /// with.
    ///
    /// F5a, D7 (6 Oct): calibrated with two HeadAngleProbe passes in the headset
    /// (Medicion_D7_HeadAway.md). The limits form the task region: every task
    /// fixation measured (board, cards, Hint, reading, scanning the cards) stays
    /// inside, and every head-turned look at the room leaves it. Still *to
    /// validate* with participants. What no head threshold can see: looks made
    /// with the eyes only (the head moved less than 5 deg), and targets at
    /// 19-23 deg of yaw, which overlap card 4 (20.5 deg).
    /// </summary>
    [Serializable]
    public struct HeadAwayThresholds
    {
        [Tooltip("TO VALIDATE. |yaw| beyond this, relative to the board, is outside the task region. " +
                 "Measured 6 Oct: card 4 at 20.6, windows and room props from 26 on.")]
        public float YawLimitDeg;
        [Tooltip("TO VALIDATE. Pitch above the board direction beyond this is outside. " +
                 "Measured 6 Oct: board centre 6.6, natural reading under 1.5, clock 18-20.")]
        public float PitchUpLimitDeg;
        [Tooltip("TO VALIDATE. Pitch below the board direction beyond this is outside. Measured 6 Oct: the head " +
                 "stays above -11 on the cards (the eyes do the rest); boxes -23, floor -40 to -55.")]
        public float PitchDownLimitDeg;
        [Tooltip("TO VALIDATE. Margin the head must come back inside before an episode can close. " +
                 "3, so that coming back to card 4 (20.5 deg) closes it.")]
        public float HysteresisDeg;
        [Tooltip("TO VALIDATE. Time outside before HEAD_AWAY is confirmed. Quick glances at the " +
                 "window measured 0.45-0.73 s outside (6 Oct): 500 missed half of them.")]
        public int MinAwayMs;
        [Tooltip("TO VALIDATE. Time back inside before HEAD_RETURNED is confirmed.")]
        public int MinReturnMs;

        public static HeadAwayThresholds Default => new()
        {
            YawLimitDeg = 24f, PitchUpLimitDeg = 12f, PitchDownLimitDeg = 15f,
            HysteresisDeg = 3f, MinAwayMs = 300, MinReturnMs = 200,
        };
    }

    /// <summary>
    /// The head-away state machine, with no Unity scene behind it so the harness
    /// can drive it frame by frame (case X4). HeadAwayMonitor feeds it the head
    /// angles relative to the board and turns what it returns into events.
    ///
    /// Inside -> (outside for MinAwayMs) -> AWAY, dated back to the first frame
    /// outside. Away -> (inside the band minus the hysteresis for MinReturnMs)
    /// -> RETURNED, with the duration measured to the first frame back inside.
    /// Leaving the band for less than MinAwayMs produces nothing.
    /// </summary>
    public sealed class HeadAwayDetector
    {
        public enum Kind { Away, Returned }

        public struct Result
        {
            public Kind Kind;
            public int Episode;
            public int OnsetOffsetMs;     // AWAY: negative, from the first frame outside to now
            public int DurationMs;        // RETURNED
            public float YawDeg, PitchDeg;
            public string Limit;          // AWAY: YAW, PITCH_UP, PITCH_DOWN
            public string Reason;         // RETURNED: RETURNED, TRACKING_LOST, SESSION_END
            public float MaxAbsYawDeg, MaxPitchUpDeg, MaxPitchDownDeg;
        }

        public HeadAwayThresholds Thresholds;
        public bool IsAway { get; private set; }
        public int Episodes { get; private set; }

        private double? _outSince;      // first frame outside (candidate or confirmed episode)
        private double? _backSince;     // first frame back inside while away
        private string _limit;
        private float _maxYaw, _maxUp, _maxDown;

        public HeadAwayDetector(HeadAwayThresholds thresholds) { Thresholds = thresholds; }

        /// <summary>One frame. `t` in seconds; angles relative to the head->board direction.</summary>
        public Result? Step(double t, float yawDeg, float pitchDeg)
        {
            var th = Thresholds;
            string limit = Math.Abs(yawDeg) > th.YawLimitDeg ? "YAW"
                         : pitchDeg > th.PitchUpLimitDeg ? "PITCH_UP"
                         : pitchDeg < -th.PitchDownLimitDeg ? "PITCH_DOWN"
                         : null;
            bool outside = limit != null;
            bool wellInside = Math.Abs(yawDeg) < th.YawLimitDeg - th.HysteresisDeg
                              && pitchDeg < th.PitchUpLimitDeg - th.HysteresisDeg
                              && pitchDeg > -(th.PitchDownLimitDeg - th.HysteresisDeg);

            if (!IsAway)
            {
                if (!outside) { _outSince = null; return null; }
                if (_outSince == null)
                {
                    _outSince = t;
                    _limit = limit;
                    _maxYaw = _maxUp = _maxDown = 0f;
                }
                Track(yawDeg, pitchDeg);
                if ((t - _outSince.Value) * 1000.0 < th.MinAwayMs) return null;

                IsAway = true;
                Episodes++;
                _backSince = null;
                return new Result
                {
                    Kind = Kind.Away, Episode = Episodes,
                    OnsetOffsetMs = -(int)Math.Round((t - _outSince.Value) * 1000.0),
                    YawDeg = yawDeg, PitchDeg = pitchDeg, Limit = _limit,
                };
            }

            Track(yawDeg, pitchDeg);
            if (!wellInside) { _backSince = null; return null; }
            if (_backSince == null) _backSince = t;
            if ((t - _backSince.Value) * 1000.0 < th.MinReturnMs) return null;
            return Close(_backSince.Value, "RETURNED");
        }

        /// <summary>Closes an open episode for another reason (tracking lost, session end).</summary>
        public Result? ForceClose(double t, string reason)
        {
            if (!IsAway) { _outSince = null; return null; }
            return Close(t, reason);
        }

        private Result Close(double backAt, string reason)
        {
            var r = new Result
            {
                Kind = Kind.Returned, Episode = Episodes,
                DurationMs = (int)Math.Round((backAt - _outSince.Value) * 1000.0),
                Reason = reason,
                MaxAbsYawDeg = _maxYaw, MaxPitchUpDeg = _maxUp, MaxPitchDownDeg = _maxDown,
            };
            IsAway = false;
            _outSince = null;
            _backSince = null;
            return r;
        }

        private void Track(float yaw, float pitch)
        {
            _maxYaw = Math.Max(_maxYaw, Math.Abs(yaw));
            _maxUp = Math.Max(_maxUp, pitch);
            _maxDown = Math.Max(_maxDown, -pitch);
        }
    }

    /// <summary>
    /// Idle time in a trial's response window (EVENT_CONTRACT.md 5.10). A frame is
    /// idle when the head and every tracked ray turn slower than their thresholds;
    /// only runs of at least MinMs count. Plain C# so the harness can test it (X5).
    /// </summary>
    public sealed class IdleTracker
    {
        [Serializable]
        public struct Thresholds
        {
            [Tooltip("TO VALIDATE. A run of still frames counts as idle from this length on.")]
            public int MinMs;
            [Tooltip("TO VALIDATE. Head angular speed below this is still.")]
            public float HeadDegPerSec;
            [Tooltip("TO VALIDATE. Ray angular speed below this is still (every tracked controller).")]
            public float RayDegPerSec;

            public static Thresholds Default => new() { MinMs = 1000, HeadDegPerSec = 5f, RayDegPerSec = 10f };
        }

        public Thresholds Limits;
        public int IdleMs { get; private set; }
        public int Episodes { get; private set; }
        public int LongestMs { get; private set; }

        private double _run;   // seconds of the current still run
        private double _headSum, _raySum;
        private int _frames;

        /// <summary>Mean speeds over the window, for calibrating the thresholds (logged, not emitted).</summary>
        public float MeanHeadDegPerSec => _frames > 0 ? (float)(_headSum / _frames) : 0f;
        public float MeanRayDegPerSec => _frames > 0 ? (float)(_raySum / _frames) : 0f;

        public IdleTracker(Thresholds limits) { Limits = limits; }

        public void Reset() { IdleMs = 0; Episodes = 0; LongestMs = 0; _run = 0; _headSum = _raySum = 0; _frames = 0; }

        public void Step(float dt, float headDegPerSec, float rayDegPerSec)
        {
            _headSum += headDegPerSec; _raySum += rayDegPerSec; _frames++;
            bool still = headDegPerSec < Limits.HeadDegPerSec && rayDegPerSec < Limits.RayDegPerSec;
            if (still) { _run += dt; return; }
            CloseRun();
        }

        /// <summary>Closes the current run (end of the response window).</summary>
        public void Finish() => CloseRun();

        private void CloseRun()
        {
            int ms = (int)Math.Round(_run * 1000.0);
            _run = 0;
            if (ms < Limits.MinMs) return;
            IdleMs += ms;
            Episodes++;
            LongestMs = Math.Max(LongestMs, ms);
        }

        public Dictionary<string, object> Fields() => new()
        {
            { "idle_ms", IdleMs },
            { "idle_episodes", Episodes },
            { "idle_longest_ms", LongestMs },
            { "idle_min_ms", Limits.MinMs },
            { "idle_head_deg_s", Limits.HeadDegPerSec },
            { "idle_ray_deg_s", Limits.RayDegPerSec },
        };
    }
}

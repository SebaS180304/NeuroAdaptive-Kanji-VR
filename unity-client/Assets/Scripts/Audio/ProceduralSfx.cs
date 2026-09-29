using System.Collections.Generic;
using UnityEngine;

namespace NeuroAdaptiveVR.Audio
{
    /// <summary>
    /// Procedural sound effects of the trials (UI design v1.3, D4 and section 4).
    /// Generated once at start and cached: no audio files, and the exact
    /// synthesis is in the code that the spec can cite.
    ///
    /// Synthesis (design section 4): sine at f + 0.18 x sine at 2f (triangle
    /// for the waveform marked so); 6 ms exponential attack; exponential decay
    /// to -80 dB at the end of each note; level as amplitude 10^(dB/20);
    /// mono, 44.1 kHz.
    ///
    /// Before the demo only three clips exist: select, correct and incorrect.
    /// Every sound has a timestamp that telemetry can rebuild (design rule 10):
    /// select plays in the frame of ANSWER_SELECTED, and the result sound's
    /// measured offset travels in TRIAL_COMPLETED. The rest of the set (stage,
    /// place, done) arrives with design P4.
    ///
    /// One 2D AudioSource (spatialBlend 0), no mixer. If something sounds loud
    /// in the headset, lower that clip's level here, not the master volume.
    /// </summary>
    [RequireComponent(typeof(AudioSource))]
    public class ProceduralSfx : MonoBehaviour
    {
        public enum Clip { Select, Correct, Incorrect }

        /// <summary>Clip lengths from design section 4, used by the harness to check the feedback window.</summary>
        public const int SelectMs = 60, CorrectMs = 90 + 380, IncorrectMs = 120 + 260;

        private const int Rate = 44100;
        private const float AttackSeconds = 0.006f;
        private const float HarmonicGain = 0.18f;
        private const float TailDb = -80f;

        private AudioSource _source;
        private readonly Dictionary<Clip, AudioClip> _clips = new();

        private void Awake()
        {
            _source = GetComponent<AudioSource>();
            _source.playOnAwake = false;
            _source.spatialBlend = 0f;
            _source.loop = false;
            Build();
        }

        /// <summary>Plays a clip now and returns its length in ms (0 if it could not play).</summary>
        public int Play(Clip clip)
        {
            if (_source == null || !_clips.TryGetValue(clip, out var c) || c == null) return 0;
            _source.PlayOneShot(c);
            return LengthMs(clip);
        }

        public int LengthMs(Clip clip)
            => _clips.TryGetValue(clip, out var c) && c != null ? Mathf.RoundToInt(c.length * 1000f) : 0;

        // ------------------------------------------------------------------

        private struct Note
        {
            public float Hz, Start, Duration;
            public Note(float hz, float start, float duration) { Hz = hz; Start = start; Duration = duration; }
        }

        private void Build()
        {
            // select: A5 880 Hz, 60 ms, -22 dB, triangle
            _clips[Clip.Select] = Render("sfx_select", -22f, true, new Note(880f, 0f, 0.060f));
            // correct: E5 659.3 then B5 987.8 Hz, 90 ms + 380 ms, -16 dB, sine
            _clips[Clip.Correct] = Render("sfx_correct", -16f, false,
                new Note(659.3f, 0f, 0.090f), new Note(987.8f, 0.090f, 0.380f));
            // incorrect: A3 220 then E3 164.8 Hz, 120 ms + 260 ms, -20 dB, sine
            _clips[Clip.Incorrect] = Render("sfx_incorrect", -20f, false,
                new Note(220f, 0f, 0.120f), new Note(164.8f, 0.120f, 0.260f));
        }

        private static AudioClip Render(string name, float levelDb, bool triangle, params Note[] notes)
        {
            float end = 0f;
            foreach (var n in notes) end = Mathf.Max(end, n.Start + n.Duration);
            int total = Mathf.CeilToInt(end * Rate);
            var data = new float[total];

            float amp = Mathf.Pow(10f, levelDb / 20f) / (1f + HarmonicGain);   // peak of the two partials = level
            float tailK = Mathf.Log(Mathf.Pow(10f, TailDb / 20f));             // ln(1e-4)

            foreach (var n in notes)
            {
                int s0 = Mathf.RoundToInt(n.Start * Rate);
                int len = Mathf.RoundToInt(n.Duration * Rate);
                for (int i = 0; i < len && s0 + i < total; i++)
                {
                    float t = i / (float)Rate;
                    float attack = 1f - Mathf.Exp(-5f * t / AttackSeconds);   // ~99 % at 6 ms
                    float decay = Mathf.Exp(tailK * t / n.Duration);          // 1 -> -80 dB at the end
                    float w = Wave(triangle, n.Hz, t) + HarmonicGain * Wave(triangle, 2f * n.Hz, t);
                    data[s0 + i] += amp * attack * decay * w;
                }
            }

            var clip = AudioClip.Create(name, total, 1, Rate, false);
            clip.SetData(data, 0);
            return clip;
        }

        private static float Wave(bool triangle, float hz, float t)
        {
            float phase = hz * t;
            if (!triangle) return Mathf.Sin(2f * Mathf.PI * phase);
            float x = phase - Mathf.Floor(phase);            // 0..1
            return 4f * Mathf.Abs(x - 0.5f) - 1f;            // triangle -1..1
        }
    }
}

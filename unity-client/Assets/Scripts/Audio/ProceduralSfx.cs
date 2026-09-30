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
    /// The whole set of design section 4: select, correct and incorrect (D4,
    /// trials), and since P4 (30 September) stage, place and done. Every sound
    /// has a timestamp that telemetry can rebuild (design rule 10): select
    /// plays in the frame of ANSWER_SELECTED and the result sound's measured
    /// offset travels in TRIAL_COMPLETED; place, incorrect and done in the
    /// assembly play in the frame of ASSEMBLY_SEGMENT_PLACED /
    /// ASSEMBLY_COMPLETED; stage's lead before the next stage travels in
    /// STATE_ENTERED.transition_sound_lead_ms (P7). There is no hint sound
    /// (design 7.7).
    ///
    /// One 2D AudioSource (spatialBlend 0), no mixer. If something sounds loud
    /// in the headset, lower that clip's level here, not the master volume.
    /// </summary>
    [RequireComponent(typeof(AudioSource))]
    public class ProceduralSfx : MonoBehaviour
    {
        public enum Clip { Select, Correct, Incorrect, Stage, Place, Done }

        /// <summary>Clip lengths from design section 4, used by the harness.</summary>
        public const int SelectMs = 60, CorrectMs = 90 + 380, IncorrectMs = 120 + 260,
                         StageMs = 1200, PlaceMs = 80, DoneMs = 4 * 90 + 500;

        /// <summary>Notes of the stage chord (D4 A4 E5). Kept public so the harness can
        /// check that stage shares no frequency with the S4 eyes-closed chime.</summary>
        public static readonly float[] StageHz = { 293.7f, 440f, 659.3f };

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
            foreach (var kv in Synthesize()) _clips[kv.Key] = kv.Value;
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

        /// <summary>Renders every clip of the set. Public so the harness can measure them in the Editor.</summary>
        public static Dictionary<Clip, AudioClip> Synthesize()
        {
            var clips = new Dictionary<Clip, AudioClip>();
            // select: A5 880 Hz, 60 ms, -22 dB, triangle
            clips[Clip.Select] = Render("sfx_select", -22f, true, new Note(880f, 0f, 0.060f));
            // correct: E5 659.3 then B5 987.8 Hz, 90 ms + 380 ms, -16 dB, sine
            clips[Clip.Correct] = Render("sfx_correct", -16f, false,
                new Note(659.3f, 0f, 0.090f), new Note(987.8f, 0.090f, 0.380f));
            // incorrect: A3 220 then E3 164.8 Hz, 120 ms + 260 ms, -20 dB, sine
            clips[Clip.Incorrect] = Render("sfx_incorrect", -20f, false,
                new Note(220f, 0f, 0.120f), new Note(164.8f, 0.120f, 0.260f));

            // stage: D4 A4 E5 together, 1.2 s, -26 dB, sine. Three notes at once
            // would peak at three times the level, so each gets a third.
            clips[Clip.Stage] = Render("sfx_stage", -26f, false, StageHz.Length,
                new Note(StageHz[0], 0f, 1.2f), new Note(StageHz[1], 0f, 1.2f), new Note(StageHz[2], 0f, 1.2f));
            // place: G5 784 Hz, 80 ms, -20 dB, triangle
            clips[Clip.Place] = Render("sfx_place", -20f, true, new Note(784f, 0f, 0.080f));
            // done: D5 E5 G5 B5 D6, one every 90 ms, 140 ms each, the last 500 ms, -16 dB, sine.
            // Neighbouring notes overlap by 50 ms, but a note has decayed below
            // -45 dB by then, so the full level stays (X6 checks the peak).
            clips[Clip.Done] = Render("sfx_done", -16f, false,
                new Note(587.3f, 0.00f, 0.140f), new Note(659.3f, 0.09f, 0.140f),
                new Note(784.0f, 0.18f, 0.140f), new Note(987.8f, 0.27f, 0.140f),
                new Note(1174.7f, 0.36f, 0.500f));
            return clips;
        }

        private static AudioClip Render(string name, float levelDb, bool triangle, params Note[] notes)
            => Render(name, levelDb, triangle, 1, notes);

        /// <param name="voices">How many notes can sound at once: each is scaled by 1/voices
        /// so the clip's peak stays at <paramref name="levelDb"/>.</param>
        private static AudioClip Render(string name, float levelDb, bool triangle, int voices, params Note[] notes)
        {
            float end = 0f;
            foreach (var n in notes) end = Mathf.Max(end, n.Start + n.Duration);
            int total = Mathf.CeilToInt(end * Rate);
            var data = new float[total];

            float amp = Mathf.Pow(10f, levelDb / 20f) / (1f + HarmonicGain) / Mathf.Max(1, voices);   // peak = level
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

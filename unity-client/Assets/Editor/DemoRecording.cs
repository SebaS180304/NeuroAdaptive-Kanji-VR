using System.IO;
using NeuroAdaptiveVR.Core;
using UnityEditor;
using UnityEditor.Recorder;
using UnityEditor.Recorder.Encoder;
using UnityEditor.Recorder.Input;
using UnityEngine;

namespace NeuroAdaptiveVR.EditorTools
{
    /// <summary>
    /// Records each demo shot to its own file (Plan_Grabacion_Demo_29oct.md §2): MP4, 1920×1080, 30 fps, from the
    /// Game view, one camera per pass. The DemoDirector says when a shot starts and ends; nothing to click.
    /// </summary>
    [InitializeOnLoad]
    public static class DemoRecording
    {
        public const string Folder = "Recordings/29oct";

        private static RecorderController _controller;

        static DemoRecording()
        {
            DemoDirector.ShotStarted += Begin;
            DemoDirector.ShotEnded += End;
            EditorApplication.playModeStateChanged += s => { if (s == PlayModeStateChange.ExitingPlayMode) End(); };
        }

        /// <summary>T6_orbit_1, T6_orbit_2, …: the first attempt number not on disk yet, so a retake never overwrites.</summary>
        public static string NextFile(string folder, string stem)
        {
            int attempt = 1;
            while (File.Exists(Path.Combine(folder, $"{stem}_{attempt}.mp4"))) attempt++;
            return $"{stem}_{attempt}";
        }

        private static void Begin(string stem)
        {
            End();
            Directory.CreateDirectory(Folder);
            string file = NextFile(Folder, stem);

            var movie = ScriptableObject.CreateInstance<MovieRecorderSettings>();
            movie.name = file;
            movie.Enabled = true;
            movie.EncoderSettings = new CoreEncoderSettings
            {
                Codec = CoreEncoderSettings.OutputCodec.MP4,
                EncodingQuality = CoreEncoderSettings.VideoEncodingQuality.High,
            };
            movie.ImageInputSettings = new GameViewInputSettings { OutputWidth = 1920, OutputHeight = 1080 };
            movie.CaptureAudio = false;   // the narration is recorded apart (guion §3.4)
            movie.OutputFile = Path.GetFullPath(Path.Combine(Folder, file));   // the Recorder adds .mp4

            var settings = ScriptableObject.CreateInstance<RecorderControllerSettings>();
            settings.AddRecorderSettings(movie);
            settings.SetRecordModeToManual();
            // The shots run on real time (C3, the object approach), so the clip follows the clock, capped at 30 fps.
            settings.FrameRatePlayback = FrameRatePlayback.Variable;
            settings.FrameRate = 30f;
            settings.CapFrameRate = true;

            _controller = new RecorderController(settings);
            _controller.PrepareRecording();
            bool ok = _controller.StartRecording();
            Debug.Log(ok ? $"[DemoRecording] REC {Folder}/{file}.mp4" : $"[DemoRecording] Could not start {file}");
        }

        private static void End()
        {
            if (_controller == null) return;
            if (_controller.IsRecording()) _controller.StopRecording();
            _controller = null;
            Debug.Log($"[DemoRecording] stopped · {Directory.GetFiles(Folder, "*.mp4").Length} clips in {Folder}");
        }
    }
}

using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using NeuroAdaptiveVR.Controllers;
using NeuroAdaptiveVR.Data;
using UnityEditor;
using UnityEngine;
using Debug = UnityEngine.Debug;

namespace NeuroAdaptiveVR.EditorTools
{
    /// <summary>
    /// Generates PLACEHOLDER target-reading clips for the 40 kanji with the
    /// Japanese voice installed in Windows, and assigns them to the
    /// KanjiLearningItems that have no recording yet.
    ///
    /// WHY IT EXISTS (decided 24 September)
    /// ------------------------------------
    /// Spec 5.2 requires the target reading to be heard by every participant in
    /// S5, and there are no recordings. A silent S5 would not meet 5.2; a TTS
    /// clip does, and is replaced by a native recording later without touching
    /// code. The cloud workspace has no network egress to any speech service,
    /// so the synthesis runs here, offline, through System.Speech in PowerShell.
    ///
    /// THREE RULES
    /// -----------
    /// 1. Every generated clip is named "tts_{KANJI_ID}". That prefix is how
    ///    PronunciationAudioController.SourceOf tells TTS from a recording, and
    ///    KANJI_EXPOSED carries the answer: a synthetic clip must never be
    ///    mistaken for a recording in the analysis.
    /// 2. It NEVER overwrites a clip that is not its own. An item whose
    ///    targetReadingAudio is a real recording is skipped and reported.
    /// 3. The text spoken is the contract's targetReading, read through
    ///    KanjiItemGenerator.LoadContract -- the same reader, not a second one.
    /// </summary>
    public static class TtsPlaceholderGenerator
    {
        private const string Log = "[TTS]";
        private const string OutFolder = "Assets/Audio/TTS";
        private const string Voice = "Microsoft Haruka Desktop";

        // -2 on SAPI's -10..10 scale: a little slower than conversational, for
        // learners hearing the reading for the first time. TO VALIDATE.
        private const int Rate = -2;

        [MenuItem("Tools/NeuroAdaptive VR/Generar audio TTS placeholder (Haruka)", priority = 110)]
        public static void Generate()
        {
            var contract = KanjiItemGenerator.LoadContract();
            if (contract == null) return;

            string projectRoot = Path.GetDirectoryName(Application.dataPath);
            string outDir = Path.Combine(projectRoot, OutFolder);
            Directory.CreateDirectory(outDir);

            string tempDir = Path.Combine(projectRoot, "Temp");
            string inFile = Path.Combine(tempDir, "tts_input.txt");
            string script = Path.Combine(tempDir, "tts_generate.ps1");

            var lines = new StringBuilder();
            foreach (var r in contract.Kanji)
                lines.Append(r.Id).Append('\t').Append(r.TargetReading).Append('\n');
            File.WriteAllText(inFile, lines.ToString(), new UTF8Encoding(false));
            File.WriteAllText(script, Script, new UTF8Encoding(false));

            var psi = new ProcessStartInfo
            {
                FileName = "powershell.exe",
                Arguments = $"-NoProfile -ExecutionPolicy Bypass -File \"{script}\" " +
                            $"-InFile \"{inFile}\" -OutDir \"{outDir}\" -Voice \"{Voice}\" -Rate {Rate}",
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
            };

            string stdout, stderr;
            using (var p = Process.Start(psi))
            {
                stdout = p.StandardOutput.ReadToEnd();
                stderr = p.StandardError.ReadToEnd();
                if (!p.WaitForExit(180000))
                {
                    Debug.LogError($"{Log} PowerShell did not finish in 180 s.");
                    return;
                }
                if (p.ExitCode != 0 || !string.IsNullOrWhiteSpace(stderr))
                {
                    Debug.LogError($"{Log} PowerShell failed (exit {p.ExitCode}).\n{stderr}\n" +
                                   $"Is '{Voice}' installed? Check with System.Speech GetInstalledVoices().");
                    return;
                }
            }

            // Measured on the first run (24 September): peaks ranged from 14 % of
            // full scale (ひ) to 43 % (ガク), and every clip carried ~1 s of
            // trailing silence. Unequal loudness between items breaks the
            // "equivalent initial instruction" of spec 7.6 as surely as unequal
            // timing would, so every clip is trimmed and peak-normalised.
            int processed = 0;
            foreach (var r in contract.Kanji)
            {
                string wav = Path.Combine(outDir, $"{PronunciationAudioController.TtsClipPrefix}{r.Id}.wav");
                if (File.Exists(wav) && TrimAndNormalize(wav)) processed++;
            }
            Debug.Log($"{Log} {processed} clips trimmed to speech +{PadSeconds * 1000:0} ms and normalised to {TargetPeak * 100:0} % peak.");

            AssetDatabase.Refresh();
            Assign(contract, stdout);
        }

        private const float TargetPeak = 0.8f;
        private const float PadSeconds = 0.05f;
        private const float SilenceFraction = 0.05f;   // of the clip's own peak

        /// <summary>
        /// Rewrites a 16-bit PCM mono WAV (the format the PowerShell script
        /// asks SAPI for) trimmed to its speech and scaled to TargetPeak.
        /// Anything else is left untouched and reported.
        /// </summary>
        private static bool TrimAndNormalize(string path)
        {
            byte[] bytes = File.ReadAllBytes(path);
            int fmt = FindChunk(bytes, "fmt "), data = FindChunk(bytes, "data");
            if (fmt < 0 || data < 0) { Debug.LogWarning($"{Log} {Path.GetFileName(path)}: not a plain WAV, left as is."); return false; }

            short channels = System.BitConverter.ToInt16(bytes, fmt + 10);
            int rate = System.BitConverter.ToInt32(bytes, fmt + 12);
            short bits = System.BitConverter.ToInt16(bytes, fmt + 22);
            if (channels != 1 || bits != 16) { Debug.LogWarning($"{Log} {Path.GetFileName(path)}: {channels} ch / {bits} bit, left as is."); return false; }

            int len = System.BitConverter.ToInt32(bytes, data + 4) / 2;
            var s = new short[len];
            System.Buffer.BlockCopy(bytes, data + 8, s, 0, len * 2);

            int peak = 1;
            foreach (var v in s) peak = System.Math.Max(peak, System.Math.Abs((int)v));
            int thr = (int)(peak * SilenceFraction);
            int first = 0, last = len - 1;
            while (first < len && System.Math.Abs((int)s[first]) < thr) first++;
            while (last > first && System.Math.Abs((int)s[last]) < thr) last--;
            int pad = (int)(rate * PadSeconds);
            first = System.Math.Max(0, first - pad);
            last = System.Math.Min(len - 1, last + pad);

            float gain = TargetPeak * 32767f / peak;
            int n = last - first + 1;
            var outBytes = new byte[44 + n * 2];
            void W(int at, string t) { for (int i = 0; i < 4; i++) outBytes[at + i] = (byte)t[i]; }
            W(0, "RIFF"); System.BitConverter.GetBytes(36 + n * 2).CopyTo(outBytes, 4); W(8, "WAVE");
            W(12, "fmt "); System.BitConverter.GetBytes(16).CopyTo(outBytes, 16);
            System.BitConverter.GetBytes((short)1).CopyTo(outBytes, 20);
            System.BitConverter.GetBytes((short)1).CopyTo(outBytes, 22);
            System.BitConverter.GetBytes(rate).CopyTo(outBytes, 24);
            System.BitConverter.GetBytes(rate * 2).CopyTo(outBytes, 28);
            System.BitConverter.GetBytes((short)2).CopyTo(outBytes, 32);
            System.BitConverter.GetBytes((short)16).CopyTo(outBytes, 34);
            W(36, "data"); System.BitConverter.GetBytes(n * 2).CopyTo(outBytes, 40);
            for (int i = 0; i < n; i++)
            {
                int v = (int)System.Math.Round(s[first + i] * gain);
                v = System.Math.Max(-32768, System.Math.Min(32767, v));
                System.BitConverter.GetBytes((short)v).CopyTo(outBytes, 44 + i * 2);
            }
            File.WriteAllBytes(path, outBytes);
            return true;
        }

        private static int FindChunk(byte[] b, string id)
        {
            int i = 12;
            while (i + 8 <= b.Length)
            {
                if (b[i] == id[0] && b[i + 1] == id[1] && b[i + 2] == id[2] && b[i + 3] == id[3]) return i;
                i += 8 + System.BitConverter.ToInt32(b, i + 4);
            }
            return -1;
        }

        private static void Assign(KanjiContentContract contract, string stdout)
        {
            int assigned = 0, unchanged = 0;
            var skippedAuthored = new List<string>();
            var missing = new List<string>();

            foreach (var r in contract.Kanji)
            {
                var clip = AssetDatabase.LoadAssetAtPath<AudioClip>($"{OutFolder}/{PronunciationAudioController.TtsClipPrefix}{r.Id}.wav");
                var item = AssetDatabase.LoadAssetAtPath<KanjiLearningItem>($"{KanjiItemGenerator.ItemFolder}/{r.Id}.asset");
                if (clip == null || item == null) { missing.Add(r.Id); continue; }

                var current = item.targetReadingAudio;
                if (current == clip) { unchanged++; continue; }
                if (current != null && PronunciationAudioController.SourceOf(current) == "AUTHORED")
                {
                    skippedAuthored.Add($"{r.Id} ({current.name})");
                    continue;
                }

                item.targetReadingAudio = clip;
                EditorUtility.SetDirty(item);
                assigned++;
            }

            AssetDatabase.SaveAssets();

            Debug.Log($"{Log} {contract.Kanji.Count} readings · {assigned} assigned · {unchanged} already assigned · " +
                      $"{skippedAuthored.Count} kept because they are recordings" +
                      (skippedAuthored.Count > 0 ? $": {string.Join(", ", skippedAuthored)}" : "") +
                      (missing.Count > 0 ? $"\n{Log} MISSING clip or item for: {string.Join(", ", missing)}" : "") +
                      $"\n{Log} PowerShell said:\n{stdout}");
        }

        private const string Script = @"param([string]$InFile, [string]$OutDir, [string]$Voice, [int]$Rate)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice($Voice)
$s.Rate = $Rate
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(22050, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$n = 0
foreach ($line in [System.IO.File]::ReadAllLines($InFile, [System.Text.Encoding]::UTF8)) {
  if ($line.Trim() -eq '') { continue }
  $p = $line -split ""`t""
  $path = Join-Path $OutDir ('tts_' + $p[0] + '.wav')
  $s.SetOutputToWaveFile($path, $fmt)
  $s.Speak($p[1])
  $s.SetOutputToNull()
  $n++
}
$s.Dispose()
Write-Output (""generated "" + $n + "" clips with "" + $Voice)
";
    }
}

using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// D-F6-139 (correction): the board's font, NotoSansCJKjp-Regular SDF, is Dynamic. The first time a
    /// character shows, TMP rasterizes its glyph and reads the OpenType tables (≈ 250 ms), and in the
    /// Editor it also rewrites and reimports the asset (≈ 830 ms): the S2 hourglass and the worst frames
    /// of S1, S2, S4 and S9 (T2 diagnosis, 4 Nov). Adding every character the board can show in S0 moves
    /// that cost to the load, before the participant sees anything.
    /// </summary>
    public static class FontPrewarm
    {
        /// <summary>Non-ASCII symbols the board's own texts use (stage title "·", the MENU "≡", …).</summary>
        public const string UiSymbols = "·≡—→";

        /// <summary>Printable ASCII, the UI symbols and every character of the content contract
        /// (kanji, readings, meanings and lures).</summary>
        public static string Characters(string contentJson)
        {
            var set = new SortedSet<char>(UiSymbols);
            for (char c = ' '; c <= '~'; c++) set.Add(c);
            foreach (char c in contentJson ?? string.Empty)
                if (!char.IsControl(c) && !char.IsSurrogate(c)) set.Add(c);
            return new string(set.ToArray());
        }

        /// <summary>Adds the characters to the font; returns how many it gained.</summary>
        public static int Run(TMP_FontAsset font, string characters)
        {
            if (font == null) return 0;
            int before = font.characterTable.Count;
            // TryAddCharacters returns false and echoes the input as "missing" when everything was already
            // there, so what is really missing is asked afterwards.
            font.TryAddCharacters(characters, out _);
            string missing = new string(characters.Where(c => !font.HasCharacter(c)).ToArray());
            if (missing.Length > 0)
                Debug.LogWarning($"[FontPrewarm] {font.name} has no glyph for: {missing}");
            return font.characterTable.Count - before;
        }
    }
}

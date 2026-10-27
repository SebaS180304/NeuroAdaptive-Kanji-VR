using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Speaker icon of the audio-hint indicator (D-F6-89, Diseno_UI_Kanji_Studio_v1.md §9.5): a box and a cone with
    /// two sound arcs, white on transparent so the Image tints it. Generated in code like PillSprite: no image file.
    /// </summary>
    public static class SpeakerSprite
    {
        private const int Size = 128;
        private static Sprite _sprite;

        public static Sprite Get()
        {
            if (_sprite != null) return _sprite;
            var tex = new Texture2D(Size, Size, TextureFormat.RGBA32, false)
            {
                wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear, name = "speaker",
            };
            var px = new Color32[Size * Size];
            for (int y = 0; y < Size; y++)
            for (int x = 0; x < Size; x++)
            {
                // u, v in [-1, 1], v up; anti-aliased by one pixel (2 / Size in these units).
                float u = (x + 0.5f) / Size * 2f - 1f, v = (y + 0.5f) / Size * 2f - 1f, aa = 2f / Size;
                float box = Inside(-0.80f - u, u + 0.45f, Mathf.Abs(v) - 0.24f, aa);
                float halfCone = 0.24f + (u + 0.45f) / 0.50f * (0.62f - 0.24f);   // widens from 0.24 to 0.62
                float cone = Inside(-0.45f - u, u - 0.05f, Mathf.Abs(v) - halfCone, aa);
                float r = Mathf.Sqrt((u - 0.05f) * (u - 0.05f) + v * v);
                bool ahead = u > 0.12f && Mathf.Abs(v) < (u - 0.05f) * 1.1f;
                float arcs = ahead ? Mathf.Max(Ring(r, 0.36f, 0.07f, aa), Ring(r, 0.62f, 0.07f, aa)) : 0f;
                float a = Mathf.Max(Mathf.Max(box, cone), arcs);
                px[y * Size + x] = new Color32(255, 255, 255, (byte)Mathf.RoundToInt(a * 255f));
            }
            tex.SetPixels32(px);
            tex.Apply(false, true);
            _sprite = Sprite.Create(tex, new Rect(0, 0, Size, Size), new Vector2(0.5f, 0.5f), 100f);
            _sprite.name = "speaker";
            return _sprite;
        }

        // 1 where every signed distance is negative (inside), with a soft edge of width aa.
        private static float Inside(float a, float b, float c, float aa)
            => Mathf.Clamp01(0.5f - Mathf.Max(a, Mathf.Max(b, c)) / aa);

        private static float Ring(float r, float radius, float halfWidth, float aa)
            => Mathf.Clamp01(0.5f - (Mathf.Abs(r - radius) - halfWidth) / aa);
    }
}

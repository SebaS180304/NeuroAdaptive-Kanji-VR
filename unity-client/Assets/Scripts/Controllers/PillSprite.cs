using System.Collections.Generic;
using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Runtime sprites for chips with fully rounded ends (UI design v1.3, P3 and
    /// P1): a filled pill and a pill outline, 9-sliced so one sprite serves any
    /// width. Generated in code, like the procedural sounds: no image files.
    ///
    /// The texture is 2r x 2r pixels with a 100 px/unit sprite, so on a canvas
    /// with reference 100 px/unit one pixel is one canvas unit: a chip of height
    /// 2r gets round ends, and the outline is exactly `ring` units wide.
    /// </summary>
    public static class PillSprite
    {
        private static readonly Dictionary<(int, int), Sprite> Cache = new();

        /// <param name="radius">Half the chip height, in canvas units.</param>
        /// <param name="ring">0 for a filled pill; otherwise the outline width.</param>
        public static Sprite Get(float radius, float ring = 0f)
        {
            int r = Mathf.Max(2, Mathf.RoundToInt(radius));
            int w = Mathf.Max(0, Mathf.RoundToInt(ring));
            if (Cache.TryGetValue((r, w), out var cached) && cached != null) return cached;

            int size = 2 * r;
            var tex = new Texture2D(size, size, TextureFormat.RGBA32, false)
            {
                wrapMode = TextureWrapMode.Clamp,
                filterMode = FilterMode.Bilinear,
                name = w == 0 ? $"pill_{r}" : $"pill_{r}_ring{w}",
            };
            var px = new Color32[size * size];
            for (int y = 0; y < size; y++)
            for (int x = 0; x < size; x++)
            {
                float dx = x + 0.5f - r, dy = y + 0.5f - r;
                float d = Mathf.Sqrt(dx * dx + dy * dy);
                float outer = Mathf.Clamp01(r - d + 0.5f);                 // 1 inside, anti-aliased edge
                float a = w == 0 ? outer : outer * Mathf.Clamp01(d - (r - w) + 0.5f);
                px[y * size + x] = new Color32(255, 255, 255, (byte)Mathf.RoundToInt(a * 255f));
            }
            tex.SetPixels32(px);
            tex.Apply(false, true);

            var border = new Vector4(r - 1, r - 1, r - 1, r - 1);
            var sprite = Sprite.Create(tex, new Rect(0, 0, size, size), new Vector2(0.5f, 0.5f),
                                       100f, 0, SpriteMeshType.FullRect, border);
            sprite.name = tex.name;
            Cache[(r, w)] = sprite;
            return sprite;
        }
    }
}

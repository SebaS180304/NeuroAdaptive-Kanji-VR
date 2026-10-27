using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace NeuroAdaptiveVR.EditorTools
{
    /// <summary>
    /// Curtain sheets of the pilot (D-F6-50, D-F6-53): the 16B sheet arrives as one quad, which a vertex wind
    /// cannot bend, so it gets a grid over the same rectangle with the same UVs, and the NeuroAdaptive/CurtainWind
    /// material: the sheet's texture and colour with alpha 0.90, fixed. EnvironmentMotion feeds its wind time.
    /// Called by JapaneseRoomIntegration for each 16B_Cortina_Hoja slot.
    /// </summary>
    public static class CurtainWind
    {
        private const string Dir = "Assets/Art/JapaneseRoom/Generated";
        private const int Columns = 12, Rows = 24;
        public const float Alpha = 0.90f;   // D-F6-53: transmittance ≤ 10 %, the same in every level and session

        // D-F6-61 (camino a, Diseno_Sala_ESL.md §10.2): d = A · hang² · G(t) · R(x, t), towards the room only, with
        // G = 0.75 + 0.25 sin(2π t / 6 s) and R = 0.75 + 0.25 sin(2π (x / 0.45 m − t / 4 s)). Written as
        // (1 − depth) + depth · sin, both peak at 1, so d peaks at A also at the ±40 % fallback.
        // A = 12 cm since 27 Oct (D-F6-85, approved by Sebas in the headset; was 6 cm).
        public const float Amplitude = 0.12f, GustSeconds = 6f, GustDepth = 0.25f;

        // D-F6-85: each sheet drawn towards its wall by 25 % of its 0.95 m width (approved in the headset, 27 Oct).
        public const float DrawMeters = 0.25f * 0.95f;
        public const float RippleDepth = 0.25f, RippleWaveLength = 0.45f, RippleSeconds = 4f;

        /// <summary>Displacement towards the room (m) at x across the sheet, hang 0 at the bar to 1 at the hem,
        /// at wind time t: the same formula as the shader, sampled by the harness (X13).</summary>
        public static float Displacement(float x, float hang, float t, float rippleDepth = RippleDepth)
        {
            float gust = 1f - GustDepth + GustDepth * Mathf.Sin(2f * Mathf.PI * t / GustSeconds);
            float ripple = 1f - rippleDepth + rippleDepth * Mathf.Sin(2f * Mathf.PI * (x / RippleWaveLength - t / RippleSeconds));
            return Amplitude * hang * hang * gust * ripple;
        }

        /// <summary>The D-F6-61 values on the material; alpha stays where Apply put it.</summary>
        public static void Configure(Material mat)
        {
            mat.SetFloat("_WindAmplitude", Amplitude);
            mat.SetFloat("_GustPeriod", GustSeconds);
            mat.SetFloat("_GustDepth", GustDepth);
            mat.SetFloat("_RippleDepth", RippleDepth);
            mat.SetFloat("_RippleWaveLength", RippleWaveLength);
            mat.SetFloat("_RipplePeriod", RippleSeconds);
            EditorUtility.SetDirty(mat);
        }

        public static void Apply(GameObject sheet)
        {
            var mf = sheet.GetComponentInChildren<MeshFilter>(true);
            var mr = mf != null ? mf.GetComponent<MeshRenderer>() : null;
            if (mf == null || mr == null || mf.sharedMesh == null) { Debug.LogError($"[Cortinas] {sheet.name} has no mesh."); return; }
            if (!AssetDatabase.IsValidFolder(Dir)) AssetDatabase.CreateFolder("Assets/Art/JapaneseRoom", "Generated");

            var meshPath = $"{Dir}/{sheet.name}_Grid.asset";
            var grid = AssetDatabase.LoadAssetAtPath<Mesh>(meshPath);
            if (grid == null || mf.sharedMesh != grid)
            {
                var built = Grid(grid != null && mf.sharedMesh == grid ? grid : mf.sharedMesh, sheet.name + "_Grid");
                if (grid == null) AssetDatabase.CreateAsset(built, meshPath);
                else { EditorUtility.CopySerialized(built, grid); Object.DestroyImmediate(built); }
                grid = AssetDatabase.LoadAssetAtPath<Mesh>(meshPath);
            }
            mf.sharedMesh = grid;

            var matPath = $"{Dir}/M_Curtain_Wind.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
            var source = mr.sharedMaterial;
            if (mat == null)
            {
                mat = new Material(Shader.Find("NeuroAdaptive/CurtainWind"));
                AssetDatabase.CreateAsset(mat, matPath);
            }
            if (source != null && source != mat)
            {
                if (source.HasProperty("_BaseMap")) mat.SetTexture("_BaseMap", source.GetTexture("_BaseMap"));
                var c = source.HasProperty("_BaseColor") ? source.GetColor("_BaseColor") : Color.white;
                mat.SetColor("_BaseColor", new Color(c.r, c.g, c.b, Alpha));
            }
            var b = grid.bounds;
            mat.SetFloat("_TopY", b.max.y);
            mat.SetFloat("_Height", b.size.y);
            Configure(mat);
            mr.sharedMaterial = mat;
        }

        // The quad's rectangle split into Columns × Rows, with the quad's UVs interpolated bilinearly.
        private static Mesh Grid(Mesh quad, string name)
        {
            var v = quad.vertices; var uv = quad.uv; var n = quad.normals;
            var b = quad.bounds;
            int across = b.size.x >= b.size.z ? 0 : 2;   // the sheet's width runs along x or z; its height along y
            Vector2 Uv(float a, float y)
            {
                // nearest corner of the quad to (a, y) in the sheet's plane
                int best = 0; float bd = float.MaxValue;
                for (int i = 0; i < v.Length; i++)
                {
                    float d = (v[i][across] - a) * (v[i][across] - a) + (v[i].y - y) * (v[i].y - y);
                    if (d < bd) { bd = d; best = i; }
                }
                return uv.Length > best ? uv[best] : Vector2.zero;
            }
            float a0 = b.min[across], a1 = b.max[across], y0 = b.min.y, y1 = b.max.y;
            Vector2 uvA0Y0 = Uv(a0, y0), uvA1Y0 = Uv(a1, y0), uvA0Y1 = Uv(a0, y1), uvA1Y1 = Uv(a1, y1);
            float depth = b.center[2 - across];
            var verts = new List<Vector3>(); var uvs = new List<Vector2>(); var norms = new List<Vector3>(); var tris = new List<int>();
            for (int r = 0; r <= Rows; r++)
                for (int c = 0; c <= Columns; c++)
                {
                    float s = (float)c / Columns, t = (float)r / Rows;
                    var p = Vector3.zero; p[across] = Mathf.Lerp(a0, a1, s); p.y = Mathf.Lerp(y0, y1, t); p[2 - across] = depth;
                    verts.Add(p);
                    uvs.Add(Vector2.Lerp(Vector2.Lerp(uvA0Y0, uvA1Y0, s), Vector2.Lerp(uvA0Y1, uvA1Y1, s), t));
                    norms.Add(n.Length > 0 ? n[0] : Vector3.forward);
                }
            for (int r = 0; r < Rows; r++)
                for (int c = 0; c < Columns; c++)
                {
                    int i = r * (Columns + 1) + c;
                    tris.AddRange(new[] { i, i + Columns + 1, i + 1, i + 1, i + Columns + 1, i + Columns + 2 });
                }
            var m = new Mesh { name = name };
            m.SetVertices(verts); m.SetUVs(0, uvs); m.SetNormals(norms); m.SetTriangles(tris, 0);
            m.RecalculateBounds();
            return m;
        }
    }
}

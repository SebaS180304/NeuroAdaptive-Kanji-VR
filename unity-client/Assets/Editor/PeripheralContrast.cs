using System.Collections.Generic;
using System.Linq;
using System.Text;
using NeuroAdaptiveVR.Controllers;
using UnityEditor;
using UnityEngine;

namespace NeuroAdaptiveVR.EditorTools
{
    /// <summary>
    /// Contrast of the silhouettes and animals against what is behind them, seen from the eye (D-F6-93: ≥ 2.7:1,
    /// the contrast against the old sky). Each peripheral is posed at rest and rendered from the eye at 1.60 m twice,
    /// shown and hidden: the pixels that change are the figure. Ratio = (L1 + 0.05) / (L2 + 0.05), L the mean relative
    /// luminance (linear sRGB) of those pixels with the figure and, at the same pixels, without it.
    /// </summary>
    public static class PeripheralContrast
    {
        public const float Minimum = 2.7f;
        private const int Size = 256;
        private static readonly Vector3 Eye = new(0f, 1.6f, 0f);

        public struct Row { public string Name; public float Figure, Background, Ratio; public int Pixels; }

        // Rest poses: bird perched, butterfly at its turning point, cat standing with its head turned (2.71–3.71 s, §10.2).
        private static float RestTime(PeripheralAnimation a) => a.AnimalKind switch
        {
            PeripheralAnimation.Kind.Cat => 3.2f,
            PeripheralAnimation.Kind.Butterfly => 2.8f,   // end of the way in (2.8 + 3.2 s, D-F6-48)
            _ => a.DurationSeconds / 2f,
        };

        public static List<Row> Measure()
        {
            var rows = new List<Row>();
            var layer = GameObject.Find("EnvironmentalLayer");
            var targets = new List<(string name, GameObject go, System.Action pose)>();
            foreach (var t in layer.GetComponentsInChildren<Transform>(true).Where(t => t.name == "24B_Silueta"))
                targets.Add((t.parent.name, t.gameObject, null));
            foreach (var a in layer.GetComponentsInChildren<PeripheralAnimation>(true))
                targets.Add((a.name, a.gameObject, () => a.Pose(RestTime(a))));

            foreach (var (name, go, pose) in targets)
            {
                var chain = new List<GameObject>();
                for (var t = go.transform; t != null; t = t.parent) if (!t.gameObject.activeSelf) chain.Add(t.gameObject);
                // The sampled pose moves the model and the cat's bones: put every transform back afterwards.
                var saved = go.GetComponentsInChildren<Transform>(true).Select(t => (t, t.localPosition, t.localRotation, t.localScale)).ToList();
                foreach (var g in chain) g.SetActive(true);
                pose?.Invoke();
                var renderers = go.GetComponentsInChildren<Renderer>(true).Where(r => r.enabled).ToArray();
                var b = renderers.Select(r => r.bounds).Aggregate((x, y) => { x.Encapsulate(y); return x; });
                var with = Render(b);
                foreach (var r in renderers) r.enabled = false;
                var without = Render(b);
                foreach (var r in renderers) r.enabled = true;
                foreach (var g in chain) g.SetActive(false);
                foreach (var (t, lp, lr, ls) in saved) { t.localPosition = lp; t.localRotation = lr; t.localScale = ls; }
                rows.Add(Compare(name, with, without));
            }
            return rows;
        }

        private static Color[] Render(Bounds b)
        {
            var go = new GameObject("ContrastCam") { hideFlags = HideFlags.HideAndDontSave };
            var cam = go.AddComponent<Camera>();
            cam.enabled = false;
            cam.nearClipPlane = 0.05f;
            go.transform.position = Eye;
            go.transform.LookAt(b.center);
            float angle = Mathf.Atan2(b.extents.magnitude, Vector3.Distance(Eye, b.center)) * Mathf.Rad2Deg;
            cam.fieldOfView = Mathf.Clamp(angle * 2.4f, 2f, 60f);
            var rt = RenderTexture.GetTemporary(Size, Size, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB);
            cam.targetTexture = rt;
            cam.Render();
            var prev = RenderTexture.active; RenderTexture.active = rt;
            var tex = new Texture2D(Size, Size, TextureFormat.RGBA32, false, false);
            tex.ReadPixels(new Rect(0, 0, Size, Size), 0, 0);
            RenderTexture.active = prev;
            var px = tex.GetPixels();
            Object.DestroyImmediate(tex); cam.targetTexture = null; RenderTexture.ReleaseTemporary(rt); Object.DestroyImmediate(go);
            return px;
        }

        private static float Lum(Color c)   // c in sRGB, as read from an sRGB target
            => 0.2126f * c.linear.r + 0.7152f * c.linear.g + 0.0722f * c.linear.b;

        private static Row Compare(string name, Color[] with, Color[] without)
        {
            double lf = 0, lb = 0; int n = 0;
            for (int i = 0; i < with.Length; i++)
            {
                var d = with[i] - without[i];
                if (Mathf.Abs(d.r) + Mathf.Abs(d.g) + Mathf.Abs(d.b) < 0.02f) continue;   // unchanged: not the figure
                lf += Lum(with[i]); lb += Lum(without[i]); n++;
            }
            if (n == 0) return new Row { Name = name, Pixels = 0 };
            float f = (float)(lf / n), bg = (float)(lb / n);
            return new Row { Name = name, Figure = f, Background = bg, Pixels = n,
                             Ratio = (Mathf.Max(f, bg) + 0.05f) / (Mathf.Min(f, bg) + 0.05f) };
        }

        public static string Table(IEnumerable<Row> rows)
        {
            var sb = new StringBuilder();
            foreach (var r in rows)
                sb.AppendLine($"{r.Name,-36} figura {r.Figure:F3}  fondo {r.Background:F3}  {r.Ratio:F2}:1  ({r.Pixels} px){(r.Ratio < Minimum ? "  < 2,7" : "")}");
            return sb.ToString();
        }

        [MenuItem("Tools/NeuroAdaptive VR/Medir contraste de perifericos", priority = 305)]
        public static void Run()
        {
            if (EditorApplication.isPlaying) { Debug.LogError("[Contraste] Not in Play mode."); return; }
            Debug.Log("[Contraste] D-F6-93, desde el ojo a 1,60 m\n" + Table(Measure()));
        }
    }
}

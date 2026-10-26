using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace NeuroAdaptiveVR.EditorTools
{
    /// <summary>
    /// The rice-field background behind the windows (D-F6-86), in place of the sky texture on
    /// Studio/Room/Exterior_Front. The image is Sebas's (ChatGPT, original art) and is the final one
    /// (Sebas, 26 Oct). It stays static and unlit, with no collider, the same in every condition and
    /// ESL level, and it does not touch the room lighting. The panel keeps the image's aspect, and its
    /// horizon (the far edge of the fields) sits at eye height, so the perspective matches the player
    /// camera at 1.60 m.
    /// </summary>
    public static class RiceFieldBackdrop
    {
        private const string Source = @"C:\Users\drdom\Documents\NeuroAdaptativeVR\Claude outputs\fondo_arrozal\Arrozales inundados entre montañas nubladas.png";
        public const string TexturePath = "Assets/Art/JapaneseRoom/Exterior/arrozal_v1.png";
        public const string MaterialPath = "Assets/Art/JapaneseRoom/Exterior/M_ExteriorRiceField.mat";
        public const string Backdrop = "Studio/Room/Exterior_Front";
        public const bool IsFinal = true;            // D-F6-86: final image, not a placeholder

        public const float Aspect = 2172f / 724f;    // the image, 3:1
        public const float HorizonFromTop = 0.56f;   // far edge of the fields, measured on the image
        public const float EyeHeight = 1.60f;
        public const float Width = 20f, Distance = 10f, Depth = 0.2f;   // the sky panel's width and distance, kept

        // D-F6-93: against the field the 24B grey (#868C9A) falls from 2.8 / 2.6:1 (sky) to 1.2 / 1.0:1. This slate keeps
        // both silhouettes at >= 2.7:1 from the eye (PeripheralContrast: 3.26 / 2.87). Its own material: the FBX's is read-only.
        public const string SilhouetteMaterialPath = "Assets/Art/Peripheral/M_Silueta_Arrozal.mat";
        public static readonly Color Silhouette = new Color32(0x34, 0x36, 0x3B, 0xFF);

        // D-F6-97: the window birds no worse than against the sky (1.37 / 1.48:1 at ESL HIGH). Lighter never passes the
        // left window, so every bird material is scaled down in linear colour: 0.40 is the edge (1.49 right), 0.38 keeps
        // a margin. Own copies, on the two window birds only: the shelf bird (indoors) keeps the FBX materials.
        public const float WindowBirdScale = 0.38f;
        public static readonly string[] WindowBirds = { "PeripheralEvent_WindowLeft", "PeripheralEvent_WindowRight" };

        public static float Height => Width / Aspect;

        private static void WindowBirdColour()
        {
            var layer = GameObject.Find("EnvironmentalLayer");
            var copies = new System.Collections.Generic.Dictionary<string, Material>();
            foreach (var bird in layer.GetComponentsInChildren<Transform>(true).Where(t => WindowBirds.Contains(t.name)))
                foreach (var r in bird.GetComponentsInChildren<Renderer>(true))
                {
                    Undo.RecordObject(r, "Arrozal");
                    r.sharedMaterials = r.sharedMaterials.Select(m => Copy(m, copies)).ToArray();
                }
            AssetDatabase.SaveAssets();
        }

        // The FBX material's colour times WindowBirdScale, in linear space; reused when it already exists.
        private static Material Copy(Material source, System.Collections.Generic.Dictionary<string, Material> copies)
        {
            string baseName = source.name.EndsWith("_Arrozal") ? source.name.Substring(0, source.name.Length - 8) : source.name;
            if (copies.TryGetValue(baseName, out var done)) return done;
            string path = $"Assets/Art/Peripheral/{baseName}_Arrozal.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            var original = AssetDatabase.LoadAllAssetsAtPath("Assets/Art/Peripheral/23B_Pajaro.fbx").OfType<Material>().First(m => m.name == baseName);
            if (mat == null) { mat = new Material(original) { name = baseName + "_Arrozal" }; AssetDatabase.CreateAsset(mat, path); }
            var c = original.GetColor("_BaseColor").linear;
            mat.SetColor("_BaseColor", new Color(c.r * WindowBirdScale, c.g * WindowBirdScale, c.b * WindowBirdScale, c.a).gamma);
            EditorUtility.SetDirty(mat);
            return copies[baseName] = mat;
        }

        private static void SilhouetteColour()
        {
            var layer = GameObject.Find("EnvironmentalLayer");
            var renderers = layer.GetComponentsInChildren<MeshRenderer>(true);
            var mat = AssetDatabase.LoadAssetAtPath<Material>(SilhouetteMaterialPath);
            foreach (var r in renderers)
            {
                if (r.name != "SM_24B_Silueta") continue;
                if (mat == null)
                {
                    mat = new Material(r.sharedMaterial) { name = "M_Silueta_Arrozal" };
                    AssetDatabase.CreateAsset(mat, SilhouetteMaterialPath);
                }
                Undo.RecordObject(r, "Arrozal");
                r.sharedMaterial = mat;
            }
            if (mat == null) return;
            mat.SetColor("_BaseColor", Silhouette);
            EditorUtility.SetDirty(mat);
            AssetDatabase.SaveAssets();
        }
        public static float CentreY => EyeHeight + HorizonFromTop * Height - Height / 2f;

        [MenuItem("Tools/NeuroAdaptive VR/Integrar fondo de arrozal", priority = 304)]
        public static void Run()
        {
            if (EditorApplication.isPlaying) { Debug.LogError("[Arrozal] Not in Play mode."); return; }
            var panel = GameObject.Find(Backdrop);
            if (panel == null) { Debug.LogError($"[Arrozal] {Backdrop} not found."); return; }

            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(Path.Combine(Application.dataPath, "..", TexturePath))));
            File.Copy(Source, Path.GetFullPath(Path.Combine(Application.dataPath, "..", TexturePath)), true);
            AssetDatabase.ImportAsset(TexturePath);
            var imp = (TextureImporter)AssetImporter.GetAtPath(TexturePath);
            imp.textureType = TextureImporterType.Default;
            imp.sRGBTexture = true;
            imp.wrapMode = TextureWrapMode.Clamp;
            imp.mipmapEnabled = true;                                   // seen from 4–10 m: no shimmer
            imp.maxTextureSize = 4096;
            imp.npotScale = TextureImporterNPOTScale.None;              // keep 2172 x 724, not 2048 x 512
            imp.textureCompression = TextureImporterCompression.CompressedHQ;
            imp.SaveAndReimport();

            var mat = AssetDatabase.LoadAssetAtPath<Material>(MaterialPath);
            if (mat == null)
            {
                mat = new Material(Shader.Find("Universal Render Pipeline/Unlit")) { name = "M_ExteriorRiceField" };
                AssetDatabase.CreateAsset(mat, MaterialPath);
            }
            mat.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(TexturePath));
            // The cube's room-facing (−Z) face carries its UVs turned 180°: turn them back.
            mat.SetTextureScale("_BaseMap", new Vector2(-1f, -1f));
            mat.SetTextureOffset("_BaseMap", Vector2.one);
            mat.SetColor("_BaseColor", Color.white);
            EditorUtility.SetDirty(mat);
            AssetDatabase.SaveAssets();

            var r = panel.GetComponent<MeshRenderer>();
            Undo.RecordObject(r, "Arrozal");
            r.sharedMaterial = mat;   // shadows as the sky panel had them: the room lighting does not change
            Undo.RecordObject(panel.transform, "Arrozal");
            panel.transform.SetPositionAndRotation(new Vector3(0f, CentreY, Distance), Quaternion.identity);
            panel.transform.localScale = new Vector3(Width, Height, Depth);
            foreach (var c in panel.GetComponents<Collider>()) Undo.DestroyObjectImmediate(c);

            SilhouetteColour();
            WindowBirdColour();
            EditorSceneManager.MarkSceneDirty(panel.scene);
            Debug.Log($"[Arrozal] {TexturePath} on {Backdrop}: {Width:F2} x {Height:F3} m at z {Distance}, centre y {CentreY:F3}, horizon at {EyeHeight} m; final = {IsFinal}");
        }
    }
}

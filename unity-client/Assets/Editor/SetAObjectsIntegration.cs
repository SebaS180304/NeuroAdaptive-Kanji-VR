using System.IO;
using System.Linq;
using NeuroAdaptiveVR.Data;
using UnityEditor;
using UnityEngine;

namespace NeuroAdaptiveVR.EditorTools
{
    /// <summary>
    /// Stage-1 objects of S5 for set A (D-F6-20, D-F6-26): 月 車 火 竹 石, and set B
    /// (D-F6-43): 山 門 女 手 雨, from the modelling chat's KanjiLessonAssets export.
    /// All five of a set or none: if one is missing, nothing of that set is assigned and
    /// its sessions keep the labelled placeholders for all five (never real and
    /// placeholder mixed in one session). A pre-test substitute
    /// has no object and keeps its placeholder, declared. Same object in every
    /// condition and ESL level: it lives in the kanji's KanjiLearningItem, not in the
    /// Environmental Layer. KanjiDiscoveryController instantiates it at objectAnchor;
    /// the models' pivot is the centre of their envelope, front −Z (ESTADO.md). 07 門's
    /// leaves are separate meshes pivoted on their hinges and never open (no animation).
    /// </summary>
    public static class SetAObjectsIntegration
    {
        private const string ArtDir = "Assets/Art/KanjiLessonAssets";
        private const string ExportRoot = @"C:\Users\drdom\Documents\JapaneseVR\KanjiLessonAssets";   // NN_CODE/export/KANJI_NN_CODE.fbx
        private static readonly (string kanjiId, string code)[] SetA =
        {
            ("KANJI_TSUKI", "01_TSUKI"), ("KANJI_KURUMA", "02_KURUMA"), ("KANJI_HI", "03_HI"),
            ("KANJI_TAKE", "04_TAKE"), ("KANJI_ISHI", "05_ISHI"),
        };

        private static readonly (string kanjiId, string code)[] SetB =
        {
            ("KANJI_YAMA", "06_YAMA"), ("KANJI_MON", "07_MON"), ("KANJI_ONNA", "08_ONNA"),
            ("KANJI_TE", "09_TE"), ("KANJI_AME", "10_AME"),
        };

        [MenuItem("Tools/NeuroAdaptive VR/Integrar objetos del set A", priority = 301)]
        public static void Run() => Integrate("A", SetA);

        [MenuItem("Tools/NeuroAdaptive VR/Integrar objetos del set B", priority = 302)]
        public static void RunSetB() => Integrate("B", SetB);

        /// <summary>
        /// Hint and C3 images of set A (D-F6-63, D-F6-64; Diseno_UI_Kanji_Studio_v1.md §11.1): P, F1, F2 and M per
        /// kanji from KanjiLessonAssets/NN_CODE/pistas/A_NN_CODE_{P,F1,F2,M}.png, validated by Sebas (D-F6-30,
        /// COORDINACION_27oct.md §0). Only those exact names are copied: other files in pistas/ are drafts. A
        /// missing image leaves its field empty, so its cells stay PLACEHOLDER with their chip (§9.6).
        /// </summary>
        [MenuItem("Tools/NeuroAdaptive VR/Integrar pistas del set A", priority = 304)]
        public static void RunHintsSetA() => IntegrateHints("A", SetA);

        private static void IntegrateHints(string set, (string kanjiId, string code)[] kanji)
        {
            const string hintDir = ArtDir + "/Hints";
            if (!AssetDatabase.IsValidFolder(hintDir)) AssetDatabase.CreateFolder(ArtDir, "Hints");
            var codes = new[] { "P", "F1", "F2", "M" };
            foreach (var (_, code) in kanji)
                foreach (var c in codes)
                {
                    var src = Path.Combine(ExportRoot, code, "pistas", $"{set}_{code}_{c}.png");
                    if (File.Exists(src)) File.Copy(src, Path.GetFullPath(Path.Combine(Application.dataPath, "..", hintDir, Path.GetFileName(src))), true);
                }
            AssetDatabase.Refresh();

            var missing = new System.Collections.Generic.List<string>();
            foreach (var (kanjiId, code) in kanji)
            {
                var item = AssetDatabase.LoadAssetAtPath<KanjiLearningItem>($"Assets/Resources/kanji/{kanjiId}.asset");
                if (item == null) { Debug.LogError($"[Pistas {set}] No KanjiLearningItem {kanjiId}"); return; }
                Sprite Load(string c)
                {
                    var path = $"{hintDir}/{set}_{code}_{c}.png";
                    if (!(AssetImporter.GetAtPath(path) is TextureImporter imp)) { missing.Add($"{code}_{c}"); return null; }
                    imp.textureType = TextureImporterType.Sprite;
                    imp.spriteImportMode = SpriteImportMode.Single;
                    imp.alphaIsTransparency = true;
                    imp.mipmapEnabled = false;   // shown at a fixed size on the board
                    imp.maxTextureSize = 1024;
                    imp.textureCompression = TextureImporterCompression.CompressedHQ;
                    imp.SaveAndReimport();
                    return AssetDatabase.LoadAssetAtPath<Sprite>(path);
                }
                Undo.RecordObject(item, $"Set {set} hints");
                item.visualAssociationSprite = Load("P");
                item.transformationForm1Sprite = Load("F1");
                item.transformationForm2Sprite = Load("F2");
                item.meaningLinkSprite = Load("M");
                EditorUtility.SetDirty(item);
            }
            AssetDatabase.SaveAssets();
            if (missing.Count > 0) Debug.LogWarning($"[Pistas {set}] Missing, stay PLACEHOLDER: " + string.Join(", ", missing));
            else Debug.Log($"[Pistas {set}] {kanji.Length * codes.Length} images assigned (AUTHORED).");
        }

        private static void Integrate(string set, (string kanjiId, string code)[] kanji)
        {
            foreach (var (_, code) in kanji)
            {
                var src = Path.Combine(ExportRoot, code, "export", $"KANJI_{code}.fbx");
                if (File.Exists(src)) File.Copy(src, Path.GetFullPath(Path.Combine(Application.dataPath, "..", ArtDir, Path.GetFileName(src))), true);
            }
            AssetDatabase.Refresh();
            var models = AssetDatabase.FindAssets("t:Model", new[] { ArtDir }).Select(AssetDatabase.GUIDToAssetPath).ToList();
            var found = kanji.Select(s => (s.kanjiId, s.code, path: models.FirstOrDefault(m => Path.GetFileName(m).Contains(s.code)))).ToList();
            var missing = found.Where(f => f.path == null).Select(f => f.code).ToList();
            if (missing.Count > 0)
            {
                Debug.LogError($"[Set {set}] Missing " + string.Join(", ", missing) + ": nothing assigned, all five stay placeholders (D-F6-26).");
                return;
            }

            const string prefabDir = ArtDir + "/Prefabs";
            if (!AssetDatabase.IsValidFolder(prefabDir)) AssetDatabase.CreateFolder(ArtDir, "Prefabs");
            foreach (var (kanjiId, code, path) in found)
            {
                var imp = (ModelImporter)AssetImporter.GetAtPath(path);
                imp.bakeAxisConversion = true; imp.addCollider = false; imp.importAnimation = false;
                imp.importCameras = false; imp.importLights = false;
                imp.SaveAndReimport();

                var instance = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(path));
                foreach (var c in instance.GetComponentsInChildren<Collider>(true)) Object.DestroyImmediate(c);
                // The cart is read from above: its top to the player, the axle vertical (+90° X in Blender, ESTADO.md 02).
                if (code == "02_KURUMA") instance.transform.rotation = Quaternion.Euler(-90f, 0f, 0f);
                var prefab = PrefabUtility.SaveAsPrefabAsset(instance, $"{prefabDir}/{code}.prefab");
                Object.DestroyImmediate(instance);

                var item = AssetDatabase.LoadAssetAtPath<KanjiLearningItem>($"Assets/Resources/kanji/{kanjiId}.asset");
                if (item == null) { Debug.LogError($"[Set {set}] No KanjiLearningItem {kanjiId}"); return; }
                Undo.RecordObject(item, $"Set {set} objects");
                item.anchorObjectPrefab = prefab;
                EditorUtility.SetDirty(item);
                Debug.Log($"[Set {set}] {kanjiId} <- {prefab.name} ({path})");
            }
            AssetDatabase.SaveAssets();
        }
    }
}

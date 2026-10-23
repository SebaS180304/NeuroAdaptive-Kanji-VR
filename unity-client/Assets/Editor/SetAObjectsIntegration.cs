using System.IO;
using System.Linq;
using NeuroAdaptiveVR.Data;
using UnityEditor;
using UnityEngine;

namespace NeuroAdaptiveVR.EditorTools
{
    /// <summary>
    /// Stage-1 objects of S5 for set A (D-F6-20, D-F6-26): 月 車 火 竹 石 from the
    /// modelling chat's KanjiLessonAssets export. All five or none: if one is missing,
    /// nothing is assigned and the session keeps the labelled placeholders for all
    /// five (never real and placeholder mixed in one session). A pre-test substitute
    /// has no object and keeps its placeholder, declared. Same object in every
    /// condition and ESL level: it lives in the kanji's KanjiLearningItem, not in the
    /// Environmental Layer. KanjiDiscoveryController instantiates it at objectAnchor;
    /// the models' pivot is the centre of their envelope, front −Z (ESTADO.md).
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

        [MenuItem("Tools/NeuroAdaptive VR/Integrar objetos del set A", priority = 301)]
        public static void Run()
        {
            foreach (var (_, code) in SetA)
            {
                var src = Path.Combine(ExportRoot, code, "export", $"KANJI_{code}.fbx");
                if (File.Exists(src)) File.Copy(src, Path.GetFullPath(Path.Combine(Application.dataPath, "..", ArtDir, Path.GetFileName(src))), true);
            }
            AssetDatabase.Refresh();
            var models = AssetDatabase.FindAssets("t:Model", new[] { ArtDir }).Select(AssetDatabase.GUIDToAssetPath).ToList();
            var found = SetA.Select(s => (s.kanjiId, s.code, path: models.FirstOrDefault(m => Path.GetFileName(m).Contains(s.code)))).ToList();
            var missing = found.Where(f => f.path == null).Select(f => f.code).ToList();
            if (missing.Count > 0)
            {
                Debug.LogError("[Set A] Missing " + string.Join(", ", missing) + ": nothing assigned, all five stay placeholders (D-F6-26).");
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
                if (item == null) { Debug.LogError($"[Set A] No KanjiLearningItem {kanjiId}"); return; }
                Undo.RecordObject(item, "Set A objects");
                item.anchorObjectPrefab = prefab;
                EditorUtility.SetDirty(item);
                Debug.Log($"[Set A] {kanjiId} <- {prefab.name} ({path})");
            }
            AssetDatabase.SaveAssets();
        }
    }
}

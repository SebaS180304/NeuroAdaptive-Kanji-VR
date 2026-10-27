using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using NeuroAdaptiveVR.Controllers;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace NeuroAdaptiveVR.EditorTools
{
    /// <summary>
    /// Puts the Japanese room v148 into JapaneseLearningStudio (D-F6-25, D-F6-42;
    /// Plan_Integracion_Sala_Japonesa.md §3–§4) from the re-export of the approved file,
    /// guided by its manifest.json: one FBX per slot, already in Unity coordinates
    /// (unity_pos, unity_rot_y_deg). Each ESL slot keeps its GameObject, its
    /// EnvironmentProp and its name (telemetry and harness use them): it moves to the
    /// manifest pose at scale 1 and its primitive children are replaced by the model.
    /// The podium (18B) goes to ControlsIntro, which shows it in S2 only. Everything else
    /// is fixed under Studio/Room/JapaneseRoom. The old primitive room is switched off,
    /// not deleted, so a revert of this commit is the only undo needed.
    ///
    /// Import: Bake Axis Conversion on (axis test of 20 Oct), no colliders (props never
    /// cut the ray), no animation, cameras or lights. The textures every .fbm carries a
    /// copy of are copied once into Textures/, where the FBX importer finds them.
    /// </summary>
    public static class JapaneseRoomIntegration
    {
        // The room of the phase test: JapaneseVR_v226.blend with the upright 18B v2 (D-F6-45).
        private const string ExportDir = @"C:\Users\drdom\Documents\JapaneseVR\export\Sala_v148_20261023_1139";
        private const string ArtDir = "Assets/Art/JapaneseRoom";
        public const string ManifestCopy = ArtDir + "/manifest.json";

        private const string Props = "Studio/EnvironmentalLayer/Props/";
        private const string Movers = "Studio/EnvironmentalLayer/Movers/";
        private const string Fixed = "Studio/Room/JapaneseRoom/";
        private const string Podium = "18B_Atril";
        // Slots placed off their manifest pose for the pilot (D-F6-54, D-F6-55): the clock leaves the task region
        // for the front wall over the left window, and the Fuji painting moves 0.25 m towards the board to make room.
        // The board gives box centres (z 3.875 / 3.885); the pivots stay on the wall at z 3.90, faces against it.
        private static readonly Dictionary<string, Vector3> Moved = new()
        {
            { "08_Reloj", new Vector3(-3.05f, 2.22f, 3.90f) },
            { "11_Cuadro_Fuji", new Vector3(-2.241f, 2.20f, 3.90f) },
        };

        // ESL slots (Plan_Integracion_Sala_Japonesa.md §3). A slot with several slots of the
        // manifest (the four piles of boxes) stays at the origin and each pile keeps its pose.
        private static readonly Dictionary<string, string> Slots = new()
        {
            { "09B_Andon", Props + "FloorLamp_T1" },          // hung from the beam, no light (spec 8.3)
            { "07_Bonsai", Props + "Plant_T1" },
            { "03_Fuzukue", Props + "SideTable_T1" },
            { "13B_Caligrafia", Props + "DeskItems_T2" },     // paper without kanji
            { "11_Cuadro_Fuji", Props + "WallPicture_T2" },
            { "10_Repisa_Maneki", Props + "WallShelf_T2" },
            { "22B_Papelera", Props + "Wastebasket_T2" },
            { "05_Librero", Props + "Bookshelf_T3" },         // out of view, accepted (decision 8)
            { "04_Zaisu", Props + "Chair_T3" },
            { "LAY_06D", Props + "StackedBoxes_T3" },
            { "LAY_06E", Props + "StackedBoxes_T3" },
            { "LAY_06F", Props + "StackedBoxes_T3" },
            { "LAY_06S", Props + "StackedBoxes_T3" },
            { "08_Reloj", Props + "WallClock_T3" },
            { "16B_Cortina_Hoja_Izq", Movers + "CurtainLeft_T2" },
            { "16B_Cortina_Hoja_Der", Movers + "CurtainRight_T2" },
        };
        private static readonly HashSet<string> Group = new() { "LAY_06D", "LAY_06E", "LAY_06F", "LAY_06S" };

        [Serializable] public class Manifest { public bool dirty_at_start; public bool ok; public Hueco[] huecos; }
        [Serializable] public class Hueco { public string hueco; public string fbx; public float[] unity_pos; public float unity_rot_y_deg; }

        public static Manifest LoadManifest()
            => File.Exists(ManifestCopy) ? JsonUtility.FromJson<Manifest>(File.ReadAllText(ManifestCopy)) : null;

        public static Vector3 Position(Hueco h)
            => Moved.TryGetValue(h.hueco, out var moved) ? moved : new Vector3(h.unity_pos[0], h.unity_pos[1], h.unity_pos[2]);

        /// <summary>The transform that stands at the slot's manifest pose: the ESL slot, the pile inside it, or the fixed piece.</summary>
        public static Transform Placed(string hueco)
        {
            if (hueco == Podium)
            {
                var intro = UnityEngine.Object.FindFirstObjectByType<ControlsIntro>(FindObjectsInactive.Include);
                var model = intro == null ? null : new SerializedObject(intro).FindProperty("podiumModel").objectReferenceValue as GameObject;
                return model == null ? null : model.transform;
            }
            if (!Slots.TryGetValue(hueco, out var slot)) return Find(Fixed + hueco);
            var t = Find(slot);
            return t == null || !Group.Contains(hueco) ? t : t.Find(hueco);
        }

        [MenuItem("Tools/NeuroAdaptive VR/Integrar sala japonesa v148", priority = 300)]
        public static void Run()
        {
            if (EditorApplication.isPlaying) { Debug.LogError("[Sala v148] Not in Play mode."); return; }
            var manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(Path.Combine(ExportDir, "manifest.json")));
            if (manifest.dirty_at_start || !manifest.ok) { Debug.LogError("[Sala v148] The manifest is not clean (D-F6-42): nothing done."); return; }

            CopyExport();
            var report = new List<string>();
            foreach (var h in manifest.huecos)
            {
                var path = $"{ArtDir}/{h.hueco}.fbx";
                ConfigureImporter(path);
                var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (asset == null) { report.Add($"MISSING {path}"); continue; }

                Transform parent;
                if (!Slots.TryGetValue(h.hueco, out var slot)) parent = FindOrCreate("Studio/Room/JapaneseRoom");   // fixed pieces and the podium
                else
                {
                    var target = FindOrCreate(slot);
                    if (!target.Cast<Transform>().Any(c => c.name.StartsWith("LAY_06") || c.name == Path.GetFileNameWithoutExtension(path)))
                        foreach (Transform child in target.Cast<Transform>().ToList()) Undo.DestroyObjectImmediate(child.gameObject);   // the primitives, once
                    Undo.RecordObject(target, "Sala v148");
                    target.localScale = Vector3.one;
                    if (Group.Contains(h.hueco)) target.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
                    parent = target;
                }

                var old = parent.Find(h.hueco);
                if (old != null) Undo.DestroyObjectImmediate(old.gameObject);
                var model = (GameObject)PrefabUtility.InstantiatePrefab(asset, parent);
                model.name = h.hueco;
                foreach (var c in model.GetComponentsInChildren<Collider>(true)) UnityEngine.Object.DestroyImmediate(c);
                if (h.hueco.StartsWith("16B_Cortina_Hoja")) CurtainWind.Apply(model);   // wind and alpha 0.90 (D-F6-50, D-F6-53)
                foreach (var screen in model.GetComponentsInChildren<MeshRenderer>(true).Where(r => r.name.EndsWith("_Interfaz")))
                    screen.gameObject.SetActive(false);   // the board and podium canvases are the interface (§3); the plane would z-fight them

                // The pose goes on the slot when the slot is the model's own root, else on the model.
                var posed = parent.GetComponent<EnvironmentProp>() != null && !Group.Contains(h.hueco) ? parent : model.transform;
                if (posed != model.transform) model.transform.SetLocalPositionAndRotation(Vector3.zero, Quaternion.identity);
                posed.SetPositionAndRotation(Position(h), Quaternion.Euler(0f, h.unity_rot_y_deg, 0f));
                if (h.hueco.StartsWith("16B_Cortina_Hoja"))
                    posed.position += new Vector3(Mathf.Sign(posed.position.x) * CurtainWind.DrawMeters, 0f, 0f);   // drawn towards the wall (D-F6-85)
                report.Add($"{h.hueco} -> {AnimationPath(posed)} at {Position(h):F3} rotY {h.unity_rot_y_deg}");

                if (h.hueco == Podium)
                {
                    model.SetActive(false);   // ControlsIntro shows it in S2 only
                    var intro = UnityEngine.Object.FindFirstObjectByType<ControlsIntro>(FindObjectsInactive.Include);
                    var so = new SerializedObject(intro);
                    so.FindProperty("podiumModel").objectReferenceValue = model;
                    so.ApplyModifiedProperties();
                }
            }

            // The old primitive room goes dark, not away: reverting this commit restores it.
            foreach (Transform old in Find("Studio/Room"))
                if (old.name != "JapaneseRoom" && old.name != "CatShelves" && old.name != "Exterior_Front")   // sills: D-F6-32; backdrop: not in the export
                { Undo.RecordObject(old.gameObject, "Sala v148"); old.gameObject.SetActive(false); }
            var floor = Find("Studio/Floor").GetComponent<MeshRenderer>();
            Undo.RecordObject(floor, "Sala v148");
            floor.enabled = false;   // keeps its collider

            EditorSceneManager.MarkSceneDirty(UnityEngine.SceneManagement.SceneManager.GetActiveScene());
            Debug.Log($"[Sala v148] {manifest.huecos.Length} slots from {ExportDir}\n" + string.Join("\n", report));
        }

        // FBX once each, the .fbm textures once into Textures/, and the manifest as the record the harness checks.
        private static void CopyExport()
        {
            var root = Path.GetFullPath(Path.Combine(Application.dataPath, "..", ArtDir));
            Directory.CreateDirectory(Path.Combine(root, "Textures"));
            var huecos = Path.Combine(ExportDir, "huecos");
            foreach (var fbx in Directory.GetFiles(huecos, "*.fbx")) File.Copy(fbx, Path.Combine(root, Path.GetFileName(fbx)), true);
            foreach (var png in Directory.GetFiles(huecos, "*.png", SearchOption.AllDirectories))
            {
                File.Copy(png, Path.Combine(root, "Textures", Path.GetFileName(png)), true);   // every .fbm carries the same copies
            }
            File.Copy(Path.Combine(ExportDir, "manifest.json"), Path.Combine(root, "manifest.json"), true);
            AssetDatabase.Refresh();
        }

        private static void ConfigureImporter(string path)
        {
            if (!(AssetImporter.GetAtPath(path) is ModelImporter imp)) return;
            bool changed = !imp.bakeAxisConversion || imp.addCollider || imp.importAnimation || imp.importCameras || imp.importLights;
            imp.bakeAxisConversion = true;     // with it the root arrives unrotated, facing −Z, unmirrored (20 Oct)
            imp.addCollider = false;
            imp.importAnimation = false;       // Unity moves things (D-F6-27)
            imp.importCameras = false;
            imp.importLights = false;          // the ESL never touches lighting (spec 8.3)
            if (changed) imp.SaveAndReimport();
        }

        private static string AnimationPath(Transform t) => t.parent == null ? t.name : AnimationPath(t.parent) + "/" + t.name;

        private static Transform Find(string path) { var go = GameObject.Find(path); return go == null ? null : go.transform; }

        private static Transform FindOrCreate(string path)
        {
            var found = Find(path);
            if (found != null) return found;
            int cut = path.LastIndexOf('/');
            var parent = FindOrCreate(path.Substring(0, cut));
            var go = new GameObject(path.Substring(cut + 1));
            Undo.RegisterCreatedObjectUndo(go, "Sala v148");
            go.transform.SetParent(parent, false);
            return go.transform;
        }
    }
}

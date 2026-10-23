using System.IO;
using System.Linq;
using NeuroAdaptiveVR.Controllers;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace NeuroAdaptiveVR.EditorTools
{
    /// <summary>
    /// Puts the Blender meshes of the bird (23B), the butterfly (26B) and the silhouette
    /// (24B) in place of their box stand-ins (D-F6-27, D-F6-28; animation sheets in
    /// JapaneseVR/references/JapaneseVRScene). Unity moves them: PeripheralAnimation
    /// carries each event's Model along its §10.2 path, EnvironmentMotion walks the
    /// silhouettes on their current trajectory. The meshes face −Z (Blender −Y), Model
    /// travels facing +Z, so each mesh is turned 180°; its wings hang from pivots named
    /// WingL / WingR at the shoulder, in Model axes, like the stand-ins had. The cat
    /// (25B) is not here: it plays its own baked clips (D-F6-38).
    /// </summary>
    public static class PeripheralMeshIntegration
    {
        private const string ExportDir = @"C:\Users\drdom\Documents\JapaneseVR\export";   // never the FALLIDO_* files
        private const string ArtDir = "Assets/Art/Peripheral";
        private const string Bird = "23B_Pajaro", Butterfly = "26B_Mariposa", Silhouette = "24B_Silueta";

        [MenuItem("Tools/NeuroAdaptive VR/Integrar pajaro, mariposa y silueta", priority = 302)]
        public static void Run()
        {
            if (EditorApplication.isPlaying) { Debug.LogError("[Perifericos] Not in Play mode."); return; }
            var root = Path.GetFullPath(Path.Combine(Application.dataPath, "..", ArtDir));
            Directory.CreateDirectory(root);
            foreach (var n in new[] { Bird, Butterfly, Silhouette }) File.Copy(Path.Combine(ExportDir, n + ".fbx"), Path.Combine(root, n + ".fbx"), true);
            AssetDatabase.Refresh();

            var events = GameObject.Find("Studio/EnvironmentalLayer/PeripheralEvents").transform;
            int done = 0;
            foreach (var anim in events.GetComponentsInChildren<PeripheralAnimation>(true))
            {
                if (anim.AnimalKind == PeripheralAnimation.Kind.Cat) continue;
                var model = anim.transform.Find("Model");
                Replace(model, anim.AnimalKind == PeripheralAnimation.Kind.Bird ? Bird : Butterfly, Quaternion.Euler(0f, 180f, 0f));
                foreach (var wing in model.GetComponentsInChildren<MeshRenderer>(true).Where(r => r.name.Contains("_Ala")).ToList())
                {
                    var pivot = new GameObject(wing.name.EndsWith("Izq") ? "WingL" : "WingR").transform;   // Izq = the animal's left = −X of Model
                    Undo.RegisterCreatedObjectUndo(pivot.gameObject, "Perifericos");
                    pivot.SetParent(model, false);
                    pivot.SetPositionAndRotation(wing.transform.position, model.rotation);
                    wing.transform.SetParent(pivot, true);
                }
                done++;
            }

            foreach (var name in new[] { "OutsideFigureLeft_T3", "OutsideFigureRight_T3" })
            {
                var slot = GameObject.Find("Studio/EnvironmentalLayer/Movers/" + name).transform;
                var axis = new SerializedObject(slot.GetComponent<EnvironmentMotion>()).FindProperty("traverseAxis").vector3Value;
                Replace(slot, Silhouette, Quaternion.LookRotation(-axis));   // its front (−Z) faces the way it walks: seen side-on from the room (24B sheet, note 1)
                done++;
            }

            EditorSceneManager.MarkSceneDirty(UnityEngine.SceneManagement.SceneManager.GetActiveScene());
            Debug.Log($"[Perifericos] {done} objects now carry their Blender mesh.");
        }

        // The stand-in's children go; the mesh goes in at the parent's origin, unpacked so its wings can get their pivots.
        private static void Replace(Transform parent, string code, Quaternion localRotation)
        {
            var path = $"{ArtDir}/{code}.fbx";
            var imp = (ModelImporter)AssetImporter.GetAtPath(path);
            if (!imp.bakeAxisConversion || imp.importAnimation || imp.addCollider)
            {
                imp.bakeAxisConversion = true; imp.addCollider = false; imp.importAnimation = false;
                imp.importCameras = false; imp.importLights = false;
                imp.SaveAndReimport();
            }
            foreach (Transform child in parent.Cast<Transform>().ToList()) Undo.DestroyObjectImmediate(child.gameObject);
            var mesh = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(path), parent);
            PrefabUtility.UnpackPrefabInstance(mesh, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            mesh.transform.SetLocalPositionAndRotation(Vector3.zero, localRotation);
            foreach (var c in mesh.GetComponentsInChildren<Collider>(true)) Object.DestroyImmediate(c);
        }
    }
}

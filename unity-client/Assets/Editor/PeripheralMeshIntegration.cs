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
    /// WingL / WingR at the shoulder, in Model axes, like the stand-ins had.
    ///
    /// The cat (25B) has its own menu: the one rigged mesh, imported Generic with its four
    /// baked clips; each window plays its EVENTO clip and the two CAMINATA clips stay
    /// unused (D-F6-38). Its root is the stop on the outer sill, and the clip walks it
    /// in from 0.47 m along local +Z (Blender +Y), so Model turns that way out along the sill.
    /// </summary>
    public static class PeripheralMeshIntegration
    {
        private const string ExportDir = @"C:\Users\drdom\Documents\JapaneseVR\export";   // never the FALLIDO_* files
        private const string ArtDir = "Assets/Art/Peripheral";
        private const string Bird = "23B_Pajaro", Butterfly = "26B_Mariposa", Silhouette = "24B_Silueta", Cat = "25B_Gato";
        private const float SillTop = 0.665f, SillFront = 4.02f, SillDepth = 0.40f;   // Diseno_Sala_ESL.md §10.2; D-F6-40

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

        [MenuItem("Tools/NeuroAdaptive VR/Integrar gato", priority = 303)]
        public static void RunCat()
        {
            if (EditorApplication.isPlaying) { Debug.LogError("[Gato] Not in Play mode."); return; }
            File.Copy(Path.Combine(ExportDir, Cat + ".fbx"), Path.GetFullPath(Path.Combine(Application.dataPath, "..", ArtDir, Cat + ".fbx")), true);
            AssetDatabase.Refresh();
            var path = $"{ArtDir}/{Cat}.fbx";
            Configure(path, animated: true);
            var clips = AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>().Where(c => !c.name.StartsWith("__preview__")).ToList();

            var events = GameObject.Find("Studio/EnvironmentalLayer/PeripheralEvents").transform;
            foreach (var anim in events.GetComponentsInChildren<PeripheralAnimation>(true).Where(a => a.AnimalKind == PeripheralAnimation.Kind.Cat))
            {
                float side = Mathf.Sign(anim.transform.position.x);
                Undo.RecordObject(anim.transform, "Gato");
                anim.transform.position = new Vector3(anim.transform.position.x, SillTop, anim.transform.position.z);   // the root stands on the sill
                var model = anim.transform.Find("Model");
                Undo.RecordObject(model, "Gato");
                model.SetLocalPositionAndRotation(Vector3.zero, Quaternion.identity);
                Replace(model, Cat, Quaternion.Euler(0f, side * 90f, 0f), animated: true);   // local +Z (where it comes from) points out along the sill
                var clip = clips.Single(c => c.name.EndsWith(side > 0f ? "EVENTO_VentanaDerecha" : "EVENTO_VentanaIzquierda"));
                var so = new SerializedObject(anim);
                so.FindProperty("bakedClip").objectReferenceValue = clip;
                so.ApplyModifiedProperties();
                anim.Pose(0f);
                Debug.Log($"[Gato] {anim.name} plays {clip.name} ({clip.length:F3} s)");
            }

            // D-F6-32, D-F6-40: the provisional outer sill, at least 0.40 m deep from the window frame.
            foreach (var shelf in GameObject.Find("Studio/Room/CatShelves").GetComponentsInChildren<MeshRenderer>(true))
            {
                Undo.RecordObject(shelf.transform, "Gato");
                var s = shelf.transform.localScale;
                shelf.transform.localScale = new Vector3(s.x, s.y, SillDepth);
                shelf.transform.position = new Vector3(shelf.transform.position.x, SillTop - s.y * 0.5f, SillFront + SillDepth * 0.5f);
            }
            EditorSceneManager.MarkSceneDirty(UnityEngine.SceneManagement.SceneManager.GetActiveScene());
        }

        // The stand-in's children go; the mesh goes in at the parent's origin, unpacked so its wings can get their pivots.
        private static void Replace(Transform parent, string code, Quaternion localRotation, bool animated = false)
        {
            var path = $"{ArtDir}/{code}.fbx";
            Configure(path, animated);
            foreach (Transform child in parent.Cast<Transform>().ToList()) Undo.DestroyObjectImmediate(child.gameObject);
            var mesh = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(path), parent);
            PrefabUtility.UnpackPrefabInstance(mesh, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            mesh.transform.SetLocalPositionAndRotation(Vector3.zero, localRotation);
            foreach (var c in mesh.GetComponentsInChildren<Collider>(true)) Object.DestroyImmediate(c);
        }

        private static void Configure(string path, bool animated)
        {
            var imp = (ModelImporter)AssetImporter.GetAtPath(path);
            if (!imp.bakeAxisConversion || imp.importAnimation != animated || imp.addCollider)
            {
                imp.bakeAxisConversion = true; imp.addCollider = false; imp.importAnimation = animated;
                imp.importCameras = false; imp.importLights = false;
                if (animated)
                {
                    imp.animationType = ModelImporterAnimationType.Generic;
                    imp.animationCompression = ModelImporterAnimationCompression.Off;   // the baked IK keeps its paws on the sill
                }
                imp.SaveAndReimport();
            }
        }
    }
}

using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using NeuroAdaptiveVR.Data;
using UnityEditor;
using UnityEngine;

namespace NeuroAdaptiveVR.EditorTools
{
    /// <summary>
    /// Crea y verifica los KanjiLearningItem a partir de
    /// Assets/Resources/kanji_content.json.
    ///
    /// QUE HACE Y QUE NO
    /// -----------------
    /// Escribe UN campo: `kanjiId`. Nada mas. Los assets no llevan copia de los
    /// datos generados --ver el comentario de cabecera de KanjiLearningItem-- asi
    /// que no hay nada que "actualizar" en una segunda pasada: correr esto dos
    /// veces seguidas no cambia un solo byte.
    ///
    /// Eso es lo que hace segura la otra mitad: el ensamblaje, las referencias a
    /// clips y prefabs, el orden de trazos. La herramienta no puede pisarlos
    /// porque no los escribe.
    ///
    /// NO BORRA NADA. Un asset cuyo id ya no esta en el contrato se reporta como
    /// huerfano y se deja donde esta. Dos razones: puede llevar horas de autoria
    /// --segmentos colocados, audio grabado-- y AssetDatabase.DeleteAsset abre un
    /// dialogo modal, que desde una llamada del MCP cuelga el Editor.
    /// </summary>
    public static class KanjiItemGenerator
    {
        private const string ContractPath = "Assets/Resources/kanji_content.json";

        // Dentro de Resources, y al lado del contrato, porque KanjiContentController
        // los descubre con Resources.LoadAll en vez de recibirlos arrastrados a una
        // lista del Inspector. Cuarenta assets arrastrados a mano son cuarenta
        // ocasiones de que falte uno y nadie lo note -- y ademas son autoria a mano
        // del dataset, que es justo lo que spec 14 prohibe.
        private const string ItemFolder = "Assets/Resources/Kanji";
        private const string Log = "[KanjiItemGenerator]";

        [MenuItem("Tools/NeuroAdaptive VR/Regenerar KanjiLearningItems", priority = 100)]
        public static void Generate() => Run(dryRun: false);

        [MenuItem("Tools/NeuroAdaptive VR/Validar KanjiLearningItems", priority = 101)]
        public static void Validate() => Run(dryRun: true);

        // ------------------------------------------------------------------

        public static bool Run(bool dryRun)
        {
            var contract = LoadContract();
            if (contract == null) return false;
            if (!ValidateContract(contract)) return false;

            if (!dryRun && !AssetDatabase.IsValidFolder(ItemFolder))
                CreateFolderRecursive(ItemFolder);

            var existing = LoadExistingItems(out bool idsAreSane);
            if (!idsAreSane) return false;

            var created = new List<string>();
            var relinked = new List<string>();

            foreach (var record in contract.Kanji)
            {
                if (existing.TryGetValue(record.Id, out var item))
                {
                    // Ya esta y ya apunta a su fila. No se toca: cualquier
                    // escritura aqui marcaria el asset como sucio y produciria
                    // ruido en el diff de git sin cambiar nada.
                    existing.Remove(record.Id);
                    continue;
                }

                string path = $"{ItemFolder}/{record.Id}.asset";

                // Caso intermedio: el archivo existe con el nombre correcto pero su
                // kanjiId esta vacio o mal. Pasa cuando alguien crea el asset a mano
                // desde el menu Create. Se reconecta en vez de crear un duplicado --
                // el contenido autorado que llevara dentro se conserva.
                var onDisk = AssetDatabase.LoadAssetAtPath<KanjiLearningItem>(path);
                if (onDisk != null)
                {
                    if (dryRun) { relinked.Add($"{record.Id} ({record.Label})"); continue; }
                    onDisk.kanjiId = record.Id;
                    EditorUtility.SetDirty(onDisk);
                    relinked.Add($"{record.Id} ({record.Label})");
                    continue;
                }

                if (dryRun) { created.Add($"{record.Id} ({record.Label})"); continue; }

                var fresh = ScriptableObject.CreateInstance<KanjiLearningItem>();
                fresh.kanjiId = record.Id;
                AssetDatabase.CreateAsset(fresh, path);
                created.Add($"{record.Id} ({record.Label})");
            }

            // Lo que quedo en `existing` no tiene fila en el contrato.
            var orphans = existing.Keys.OrderBy(k => k).ToList();

            if (!dryRun)
            {
                AssetDatabase.SaveAssets();
                AssetDatabase.Refresh();
            }

            Report(dryRun, contract, created, relinked, orphans);
            return orphans.Count == 0;
        }

        // ------------------------------------------------------------------
        // Carga y validacion del contrato
        // ------------------------------------------------------------------

        private static KanjiContentContract LoadContract()
        {
            if (!File.Exists(ContractPath))
            {
                Debug.LogError($"{Log} No existe {ContractPath}. Se genera con " +
                               "`docker compose run --rm kanji-tools python tools/kanji_metrics.py --export`, " +
                               "no a mano.");
                return null;
            }

            try
            {
                return JsonConvert.DeserializeObject<KanjiContentContract>(
                    File.ReadAllText(ContractPath));
            }
            catch (JsonException e)
            {
                Debug.LogError($"{Log} {ContractPath} no se pudo leer: {e.Message}");
                return null;
            }
        }

        /// <summary>
        /// Se comprueba antes de escribir un solo asset. Un contrato malo que
        /// produce 40 assets a medias es peor que un contrato malo que no produce
        /// ninguno: el primero deja el proyecto en un estado que hay que deshacer
        /// a mano.
        /// </summary>
        private static bool ValidateContract(KanjiContentContract c)
        {
            if (c.Kanji == null || c.Kanji.Count == 0)
            {
                Debug.LogError($"{Log} El contrato no trae kanji.");
                return false;
            }

            var sinId = c.Kanji.Where(k => string.IsNullOrWhiteSpace(k.Id)).ToList();
            if (sinId.Count > 0)
            {
                Debug.LogError($"{Log} {sinId.Count} filas sin `id`: " +
                               $"{string.Join(", ", sinId.Select(k => k.Character))}. " +
                               "El JSON es de antes de que KANJI_IDS existiera; hay que regenerarlo.");
                return false;
            }

            // La guarda equivalente ya corre al importar kanji_metrics.py. Se repite
            // aqui porque este lado puede recibir un JSON viejo, escrito antes de
            // que aquella guarda existiera, y ese es justo el caso que importa.
            var dup = c.Kanji.GroupBy(k => k.Id).Where(g => g.Count() > 1).ToList();
            if (dup.Count > 0)
            {
                foreach (var g in dup)
                    Debug.LogError($"{Log} id repetido en el contrato: '{g.Key}' lo usan " +
                                   $"{string.Join(" y ", g.Select(k => k.Character))}. " +
                                   "Compartirian asset y compartirian llave foranea en la base.");
                return false;
            }

            int esperados = c.Sets.Values.Sum(v => v.Count) + c.Reserve.Count + c.Tutorial.Count;
            if (c.Kanji.Count != esperados)
                Debug.LogWarning($"{Log} El contrato trae {c.Kanji.Count} filas pero sus " +
                                 $"pools suman {esperados}. No impide generar, pero uno de " +
                                 "los dos esta mal.");

            return true;
        }

        // ------------------------------------------------------------------
        // Assets existentes
        // ------------------------------------------------------------------

        private static Dictionary<string, KanjiLearningItem> LoadExistingItems(out bool sane)
        {
            sane = true;
            var map = new Dictionary<string, KanjiLearningItem>();
            var vistos = new Dictionary<string, string>();

            foreach (var guid in AssetDatabase.FindAssets("t:KanjiLearningItem"))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                var item = AssetDatabase.LoadAssetAtPath<KanjiLearningItem>(path);
                if (item == null || string.IsNullOrWhiteSpace(item.kanjiId)) continue;

                if (vistos.TryGetValue(item.kanjiId, out string anterior))
                {
                    // Dos assets con el mismo id: el join de KanjiContentController
                    // devolveria uno de los dos segun el orden de carga, que no es
                    // estable. Se para aqui, sin escribir nada.
                    Debug.LogError($"{Log} '{item.kanjiId}' esta en dos assets: {anterior} y " +
                                   $"{path}. Hay que quedarse con uno antes de regenerar.", item);
                    sane = false;
                    continue;
                }

                vistos[item.kanjiId] = path;
                map[item.kanjiId] = item;
            }

            return map;
        }

        private static void CreateFolderRecursive(string folder)
        {
            var partes = folder.Split('/');
            string acumulado = partes[0];           // "Assets"
            for (int i = 1; i < partes.Length; i++)
            {
                string siguiente = $"{acumulado}/{partes[i]}";
                if (!AssetDatabase.IsValidFolder(siguiente))
                    AssetDatabase.CreateFolder(acumulado, partes[i]);
                acumulado = siguiente;
            }
        }

        // ------------------------------------------------------------------

        private static void Report(bool dryRun, KanjiContentContract c,
                                   List<string> created, List<string> relinked,
                                   List<string> orphans)
        {
            string modo = dryRun ? "VALIDACION (no se escribio nada)" : "REGENERACION";
            int sinCambios = c.Kanji.Count - created.Count - relinked.Count;

            Debug.Log($"{Log} {modo} · contrato v{c.SchemaVersion} · {c.Kanji.Count} filas\n" +
                      $"  creados: {created.Count}\n" +
                      $"  reconectados: {relinked.Count}\n" +
                      $"  ya correctos: {sinCambios}\n" +
                      $"  huerfanos: {orphans.Count}" +
                      (created.Count > 0 ? $"\n  -> {string.Join(", ", created)}" : "") +
                      (relinked.Count > 0 ? $"\n  reconectados -> {string.Join(", ", relinked)}" : ""));

            foreach (string id in orphans)
                Debug.LogWarning($"{Log} '{id}' tiene asset pero ya no esta en el contrato. " +
                                 "No se borra: puede llevar autoria dentro. Revisalo y borralo " +
                                 "a mano si sobra.");
        }
    }
}

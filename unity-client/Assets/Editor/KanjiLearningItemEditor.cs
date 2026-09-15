using System.Collections.Generic;
using System.IO;
using Newtonsoft.Json;
using NeuroAdaptiveVR.Data;
using UnityEditor;
using UnityEngine;

namespace NeuroAdaptiveVR.EditorTools
{
    /// <summary>
    /// Encabezado de solo lectura para KanjiLearningItem.
    ///
    /// El asset guarda un id y nada mas del lado generado, asi que sin esto el
    /// Inspector mostraria "KANJI_TSUKI" y ningun kanji -- y elegir el AudioClip
    /// correcto de entre cuarenta seria adivinar.
    ///
    /// Lo que se pinta arriba NO esta guardado en el asset: se lee de
    /// Assets/Resources/kanji_content.json cada vez. Por eso no puede quedarse
    /// desactualizado y por eso es gris y no editable. Es una ventana al dato, no
    /// una copia suya.
    /// </summary>
    [CustomEditor(typeof(KanjiLearningItem))]
    [CanEditMultipleObjects]
    public class KanjiLearningItemEditor : UnityEditor.Editor
    {
        public override void OnInspectorGUI()
        {
            var item = (KanjiLearningItem)target;
            DrawContractHeader(item);
            EditorGUILayout.Space();
            DrawDefaultInspector();
        }

        private void DrawContractHeader(KanjiLearningItem item)
        {
            if (string.IsNullOrWhiteSpace(item.kanjiId))
            {
                EditorGUILayout.HelpBox(
                    "Sin kanjiId. Este asset no esta unido a ninguna fila del contrato.\n" +
                    "Tools > NeuroAdaptive VR > Regenerar KanjiLearningItems lo conecta si " +
                    "su nombre de archivo coincide con un id.",
                    MessageType.Warning);
                return;
            }

            var record = KanjiContractCache.Find(item.kanjiId);
            if (record == null)
            {
                EditorGUILayout.HelpBox(
                    $"'{item.kanjiId}' no aparece en kanji_content.json.\n" +
                    "O el id esta mal escrito, o el contrato se regenero sin este kanji. " +
                    "En sesion, este asset nunca se usaria.",
                    MessageType.Error);
                return;
            }

            var caja = new GUIStyle(EditorStyles.helpBox) { padding = new RectOffset(10, 10, 8, 8) };
            EditorGUILayout.BeginVertical(caja);

            var grande = new GUIStyle(EditorStyles.label)
            {
                fontSize = 34,
                fixedHeight = 44,
                alignment = TextAnchor.MiddleLeft,
            };

            EditorGUILayout.BeginHorizontal();
            EditorGUILayout.LabelField(record.Character, grande, GUILayout.Width(52));
            EditorGUILayout.BeginVertical();
            EditorGUILayout.LabelField(record.Meaning, EditorStyles.boldLabel);
            EditorGUILayout.LabelField($"{record.TargetReading}   ·   {record.Pool}   ·   " +
                                       $"{record.TextbookLesson}", EditorStyles.miniLabel);
            EditorGUILayout.EndVertical();
            EditorGUILayout.EndHorizontal();

            EditorGUILayout.LabelField(
                $"{record.Strokes} trazos · {record.Morae} moras · " +
                $"{record.AssemblyGroups} grupos · {record.CommonReadings} lecturas · " +
                $"perimetrica {record.PerimetricComplexity:0.#} · " +
                $"imageabilidad {Score(record.ImageabilityGlyph)}/{Score(record.ImageabilityObject)}",
                EditorStyles.miniLabel);

            EditorGUILayout.LabelField(
                "Generado · vive en kanji_content.json, no en este asset",
                EditorStyles.centeredGreyMiniLabel);

            // Chequeo barato que cuesta cero y atrapa el error mas probable de
            // autoria: los grupos de ensamblaje entran en la banda de balance de
            // 4.1, asi que segmentar de mas o de menos rompe el balance del set.
            if (item.assemblySegments != null && item.assemblySegments.Count > 0 &&
                item.assemblySegments.Count != record.AssemblyGroups)
            {
                EditorGUILayout.HelpBox(
                    $"Hay {item.assemblySegments.Count} segmentos autorados pero el contrato " +
                    $"cuenta {record.AssemblyGroups} grupos de ensamblaje para este kanji. " +
                    "Ese numero entra en la banda de balance de los sets (spec 4.1).",
                    MessageType.Warning);
            }

            EditorGUILayout.EndVertical();
        }

        private static string Score(int? v) => v.HasValue ? v.Value.ToString() : "-";
    }

    /// <summary>
    /// Lee kanji_content.json una vez y lo relee cuando el archivo cambia en
    /// disco. Sin esto, cada repintado del Inspector deserializaria 40 filas.
    ///
    /// La invalidacion es por fecha de modificacion y no por un boton de
    /// "recargar": regenerar el contrato desde Docker no pasa por Unity, asi que
    /// un cache que solo se limpiara desde el Editor mostraria datos viejos
    /// justo despues de la operacion que los cambia.
    /// </summary>
    internal static class KanjiContractCache
    {
        private const string ContractPath = "Assets/Resources/kanji_content.json";

        private static Dictionary<string, KanjiContentRecord> _porId;
        private static System.DateTime _stamp;

        internal static KanjiContentRecord Find(string id)
        {
            Refresh();
            return _porId != null && _porId.TryGetValue(id, out var r) ? r : null;
        }

        private static void Refresh()
        {
            if (!File.Exists(ContractPath)) { _porId = null; return; }

            var actual = File.GetLastWriteTimeUtc(ContractPath);
            if (_porId != null && actual == _stamp) return;

            try
            {
                var c = JsonConvert.DeserializeObject<KanjiContentContract>(
                    File.ReadAllText(ContractPath));
                _porId = new Dictionary<string, KanjiContentRecord>();
                foreach (var r in c.Kanji)
                {
                    if (string.IsNullOrWhiteSpace(r.Id)) continue;
                    _porId[r.Id] = r;   // los duplicados los caza KanjiItemGenerator
                }
                _stamp = actual;
            }
            catch (JsonException)
            {
                // El Inspector no es sitio para gritar: si el JSON esta roto, el
                // generador lo dice con detalle cuando se corre.
                _porId = null;
            }
        }
    }
}

using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using NeuroAdaptiveVR.Data;
using UnityEngine;

namespace NeuroAdaptiveVR.Controllers
{
    /// <summary>
    /// Carga el contenido de kanji y lo entrega ya unido (spec seccion 14).
    ///
    /// Es el unico sitio del proyecto que lee kanji_content.json en runtime y el
    /// unico que junta cada fila con su KanjiLearningItem. De aqui sale un
    /// KanjiItem y nadie mas vuelve a tocar ninguno de los dos lados.
    ///
    /// NADA SE CABLEA A MANO
    /// ---------------------
    /// No hay una lista de 40 assets arrastrada en el Inspector. Spec 14:
    /// "Nothing in the kanji dataset is authored by hand in the Editor" --y
    /// arrastrar cuarenta cosas a un campo es exactamente eso, ademas de un
    /// sitio donde falta uno y nadie lo nota. Los assets se descubren con
    /// Resources.LoadAll y se unen por id.
    ///
    /// Por eso viven en Assets/Resources/kanji/, al lado del JSON: es lo que
    /// hace que la carga sea identica en el Editor, en Quest Link y en un build
    /// de Android, sin codigo por plataforma.
    /// </summary>
    public class KanjiContentController : MonoBehaviour
    {
        private const string ContractResource = "kanji_content";
        // Minuscula: es como esta la carpeta en disco y en git. Con "Kanji"
        // funcionaba en Windows por la insensibilidad a mayusculas del sistema
        // de archivos, y en Linux habria devuelto cero assets -- con el sintoma
        // "40 kanji sin KanjiLearningItem", que apunta a contenido faltante y no
        // a una ruta mal escrita.
        private const string ItemsResourceFolder = "kanji";
        private const string Log = "[KanjiContent]";

        [Header("Carga")]
        [Tooltip("Cargar en Awake. Desactivalo solo si algo tiene que fijar la seed antes.")]
        [SerializeField] private bool loadOnAwake = true;

        // [NonSerialized] no es decoracion. Sin el, Unity resucita a medias este
        // estado al recargar el dominio --al recompilar, o al entrar y salir de
        // Play-- y el resultado es un contrato zombi:
        //
        //   Kanji      -> List de clases [Serializable]: SOBREVIVE, 40 filas
        //   Sets       -> Dictionary: Unity no lo serializa, vuelve VACIO
        //   _byId      -> Dictionary: vuelve VACIO
        //
        // Encontrado el 15 de septiembre por el arnes de pruebas, que vio C1
        // decir "0 kanji" y C6 leer la tipografia del mismo contrato en la misma
        // llamada. Sin esa contradiccion no habria dado ninguna senal: Set("A")
        // devolvia vacio y el error se leia como "falta contenido", no como
        // "el objeto que dice estar cargado no lo esta".
        [NonSerialized] private KanjiContentContract _contract;
        [NonSerialized] private readonly Dictionary<string, KanjiItem> _byId = new();
        [NonSerialized] private readonly Dictionary<string, KanjiItem> _byCharacter = new();

        /// <summary>
        /// Cargado de verdad: hay contrato Y hay indice.
        ///
        /// La version anterior solo miraba `_contract != null`, que es la mitad
        /// del hecho. Un `IsLoaded` que dice true sobre un indice vacio manda a
        /// todo el que confia en el a trabajar sobre cero kanji, y cada consumidor
        /// lo reporta como "falta contenido" en vez de como lo que es.
        /// </summary>
        public bool IsLoaded => _contract != null && _byId.Count > 0;
        public KanjiContentContract Contract => _contract;

        private void Awake()
        {
            if (loadOnAwake) Load();
        }

        // ------------------------------------------------------------------
        // Carga
        // ------------------------------------------------------------------

        public bool Load()
        {
            var asset = Resources.Load<TextAsset>(ContractResource);
            if (asset == null)
            {
                Debug.LogError($"{Log} No hay Resources/{ContractResource}.json. Se genera con " +
                               "`docker compose run --rm kanji-tools python tools/kanji_metrics.py --export`.");
                return false;
            }

            try
            {
                _contract = JsonConvert.DeserializeObject<KanjiContentContract>(asset.text);
            }
            catch (JsonException e)
            {
                _contract = null;
                Debug.LogError($"{Log} El contrato no se pudo leer: {e.Message}");
                return false;
            }

            var assetsById = LoadAssetsById();

            _byId.Clear();
            _byCharacter.Clear();
            var sinAsset = new List<string>();

            foreach (var record in _contract.Kanji)
            {
                if (string.IsNullOrWhiteSpace(record.Id))
                {
                    Debug.LogError($"{Log} Fila sin id ({record.Character}). El contrato es " +
                                   "anterior a KANJI_IDS: hay que regenerarlo.");
                    continue;
                }

                assetsById.TryGetValue(record.Id, out var so);
                if (so == null) sinAsset.Add(record.Id);

                var item = new KanjiItem(record, so);
                _byId[record.Id] = item;
                _byCharacter[record.Character] = item;
            }

            // Warning y no error: sin assets el contenido sigue siendo correcto
            // --significado, lectura y metricas salen del contrato-- y el ciclo de
            // trials corre igual. Lo que no hay es audio ni modelos, y eso tiene
            // que verse en consola, no descubrirse en el visor.
            if (sinAsset.Count > 0)
                Debug.LogWarning($"{Log} {sinAsset.Count} de {_contract.Kanji.Count} kanji sin " +
                                 $"KanjiLearningItem: {string.Join(", ", sinAsset.Take(8))}" +
                                 (sinAsset.Count > 8 ? " ..." : "") +
                                 ". Tools > NeuroAdaptive VR > Regenerar KanjiLearningItems los crea.");

            Debug.Log($"{Log} Contrato v{_contract.SchemaVersion} cargado · {_byId.Count} kanji · " +
                      $"{_contract.Kanji.Count - sinAsset.Count} con assets · " +
                      $"sets {string.Join("/", _contract.Sets.Select(s => $"{s.Key}:{s.Value.Count}"))}");

            return true;
        }

        /// <summary>
        /// Descubre los assets y caza los ids repetidos. Dos assets con el mismo
        /// id no son un empate que haya que deshacer eligiendo: el orden de
        /// Resources.LoadAll no esta garantizado, asi que la sesion usaria uno u
        /// otro segun el dia.
        /// </summary>
        private Dictionary<string, KanjiLearningItem> LoadAssetsById()
        {
            var map = new Dictionary<string, KanjiLearningItem>();

            foreach (var so in Resources.LoadAll<KanjiLearningItem>(ItemsResourceFolder))
            {
                if (so == null) continue;
                if (string.IsNullOrWhiteSpace(so.kanjiId))
                {
                    Debug.LogWarning($"{Log} '{so.name}' no tiene kanjiId. Se ignora.", so);
                    continue;
                }
                if (map.TryGetValue(so.kanjiId, out var anterior))
                {
                    Debug.LogError($"{Log} '{so.kanjiId}' esta en dos assets ({anterior.name} y " +
                                   $"{so.name}). Cual se usa dependeria del orden de carga.", so);
                    continue;
                }
                map[so.kanjiId] = so;
            }

            return map;
        }

        // ------------------------------------------------------------------
        // Consulta
        // ------------------------------------------------------------------

        public KanjiItem ById(string kanjiId)
            => kanjiId != null && _byId.TryGetValue(kanjiId, out var i) ? i : null;

        public KanjiItem ByCharacter(string character)
            => character != null && _byCharacter.TryGetValue(character, out var i) ? i : null;

        public IEnumerable<KanjiItem> All => _byId.Values;

        /// <summary>
        /// Los cinco kanji de un set experimental, EN EL ORDEN DEL CONTRATO.
        ///
        /// El orden importa y por eso no se devuelve un conjunto: la secuencia de
        /// trials se reconstruye desde la seed (spec 6.1), y una reconstruccion
        /// que parte de un orden distinto no reconstruye nada.
        /// </summary>
        public IReadOnlyList<KanjiItem> Set(string setName)
        {
            if (_contract == null || !_contract.Sets.TryGetValue(setName, out var chars))
            {
                Debug.LogError($"{Log} No existe el set '{setName}'.");
                return System.Array.Empty<KanjiItem>();
            }
            return chars.Select(ByCharacter).Where(i => i != null).ToList();
        }

        public IReadOnlyList<KanjiItem> Tutorial =>
            _contract == null
                ? System.Array.Empty<KanjiItem>()
                : _contract.Tutorial.Select(ByCharacter).Where(i => i != null).ToList();

        public IReadOnlyList<KanjiItem> Reserve =>
            _contract == null
                ? System.Array.Empty<KanjiItem>()
                : _contract.Reserve.Select(ByCharacter).Where(i => i != null).ToList();

        /// <summary>
        /// Nombres de los sets experimentales, ordenados. Se leen del contrato en
        /// vez de escribirse como {"A","B","C"}: si algun dia hay un cuarto set,
        /// esto no es el sitio donde haya que acordarse de anadirlo.
        /// </summary>
        public IReadOnlyList<string> SetNames =>
            _contract == null
                ? System.Array.Empty<string>()
                : _contract.Sets.Keys.OrderBy(k => k).ToList();

        /// <summary>
        /// Elige el set de una sesion a partir de su seed.
        ///
        /// La seed es experiment_sessions.random_seed, que existe en la base desde
        /// M1. Que la asignacion salga de ahi y no de un sorteo en runtime es lo
        /// que permite reconstruir una sesion entera desde su fila (spec 6.1).
        /// </summary>
        public string AssignSetName(int sessionSeed)
        {
            var names = SetNames;
            if (names.Count == 0) return null;
            return names[new System.Random(sessionSeed).Next(names.Count)];
        }

        /// <summary>
        /// Los kanji de reserva que pueden reemplazar a `item` dentro de `setName`,
        /// segun la tabla derivada de spec 13.2.
        ///
        /// La tabla la calcula tools/kanji_metrics.py y el build falla si algun
        /// kanji experimental se queda sin sustituto, asi que una lista vacia aqui
        /// significa que el contrato es viejo o que el kanji no es de ese set --no
        /// es un caso a resolver en runtime.
        /// </summary>
        public IReadOnlyList<KanjiItem> SubstitutesFor(string setName, KanjiItem item)
        {
            if (_contract == null || item == null) return System.Array.Empty<KanjiItem>();

            if (!_contract.SubstitutionTable.TryGetValue(setName, out var porKanji) ||
                !porKanji.TryGetValue(item.Character, out var chars))
            {
                Debug.LogWarning($"{Log} {item} no tiene entrada de sustitucion en el set " +
                                 $"'{setName}'.");
                return System.Array.Empty<KanjiItem>();
            }

            return chars.Select(ByCharacter).Where(i => i != null).ToList();
        }
    }
}

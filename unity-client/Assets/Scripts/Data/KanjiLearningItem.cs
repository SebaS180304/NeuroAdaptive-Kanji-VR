using System;
using System.Collections.Generic;
using UnityEngine;

namespace NeuroAdaptiveVR.Data
{
    /// <summary>
    /// La mitad de un kanji del estudio que un archivo JSON no puede llevar
    /// (spec v1.2 seccion 4.3).
    ///
    /// QUE VIVE AQUI Y QUE NO
    /// ----------------------
    /// La regla es de una linea: aqui esta todo lo que 4.3 pide y
    /// kanji_content.json NO trae. Nada mas.
    ///
    /// Fuera, en el JSON generado por tools/kanji_metrics.py: el caracter, el
    /// significado, la lectura objetivo, trazos, moras, grupos de ensamblaje,
    /// lecturas comunes, complejidad perimetrica, las dos imageabilidades, el
    /// tipo de descubrimiento, la leccion y el set.
    ///
    /// Aqui: el id que une las dos mitades, las referencias a assets de Unity
    /// --que son GUIDs del proyecto y no caben en un contrato de contenido-- y
    /// el contenido pedagogico que todavia no esta congelado en ninguna tabla.
    ///
    /// POR QUE NO LLEVA TAMBIEN LOS CAMPOS GENERADOS
    /// ---------------------------------------------
    /// Spec 14 es explicito: "Nothing in the kanji dataset is authored by hand in
    /// the Editor". Copiar los valores del JSON a estos assets --aunque lo hiciera
    /// una herramienta-- pondria la complejidad perimetrica de 月 en dos archivos
    /// versionados a la vez. Mientras la herramienta corriera despues de cada
    /// cambio estarian de acuerdo; el dia que alguien regenerara el JSON y no los
    /// assets, el Learning Board mostraria un numero y el analisis usaria otro, y
    /// nada fallaria. Es la forma exacta de los fallos que este proyecto lleva
    /// encontrando desde M1.
    ///
    /// El coste es que el Inspector, por si solo, mostraria un id y ningun kanji.
    /// Eso lo resuelve KanjiLearningItemEditor, que lee el JSON y pinta el
    /// caracter, el significado y la lectura como encabezado de solo lectura. Se
    /// ve el dato sin tener una segunda copia de el.
    /// </summary>
    [CreateAssetMenu(fileName = "KANJI_", menuName = "NeuroAdaptive VR/Kanji Learning Item")]
    public class KanjiLearningItem : ScriptableObject
    {
        // ------------------------------------------------------------------
        // La union
        // ------------------------------------------------------------------

        [Header("Identidad")]
        [Tooltip("Id estable del kanji: la llave que une este asset con su fila de " +
                 "kanji_content.json, y lo que viaja como kanji_id en la telemetria.\n\n" +
                 "Lo escribe Tools > NeuroAdaptive VR > Regenerar KanjiLearningItems. " +
                 "Es el unico campo del asset que la herramienta toca, y el unico que " +
                 "no se edita a mano: cambiarlo aqui desconecta el asset de su fila " +
                 "sin que nada avise hasta que falte un kanji en una sesion.")]
        public string kanjiId;

        // ------------------------------------------------------------------
        // Pedagogico que el contrato no congela (spec 4.3)
        // ------------------------------------------------------------------

        [Header("Pedagogico · autorado")]
        [Tooltip("Lecturas del libro. NO es lo que se evalua --eso es la lectura " +
                 "objetivo, que vive en el JSON--. Estan aqui porque 4.3 las pide " +
                 "como dato pedagogico y porque justifican por que se eligio la " +
                 "lectura objetivo que se eligio.")]
        public string kunyomi;
        public string onyomi;

        [Tooltip("Orden de trazos, del Basic Kanji Book. Uno por trazo. El numero de " +
                 "trazos si esta en el JSON; la secuencia no.")]
        public List<string> strokeOrder = new();

        [Tooltip("Palabras de ejemplo. No se usan en Fase 2.")]
        public List<string> exampleWords = new();

        [Tooltip("Ejemplos en contexto. No se usan en Fase 2.")]
        public List<string> contextExamples = new();

        [Tooltip("Objeto o concepto de anclaje que aparece en la Object/Association " +
                 "Area. Ej: 月 -> luna creciente. Es la descripcion en texto; el " +
                 "modelo esta mas abajo.")]
        public string visualAssociation;

        // ------------------------------------------------------------------
        // Ensamblaje (spec 4.3 / 5.3)
        // ------------------------------------------------------------------

        [Header("Ensamblaje · autorado")]
        [Tooltip("2-4 segmentos grandes, en orden. Sin reconocimiento de trazo " +
                 "(spec 5.3). El JSON trae CUANTOS grupos son --entra en la banda de " +
                 "balance-- pero no cuales ni donde van.\n\n" +
                 "Una sola lista de structs y no cuatro listas paralelas de segmentos, " +
                 "orden, posiciones y assets: cuatro listas pueden acabar con " +
                 "longitudes distintas, y el error aparece al colocar el tercer " +
                 "segmento de un kanji concreto, semanas despues.")]
        public List<AssemblySegment> assemblySegments = new();

        // ------------------------------------------------------------------
        // Assets
        // ------------------------------------------------------------------

        [Header("Assets · autorado")]
        [Tooltip("Lectura objetivo grabada. En la exposicion inicial suena para todos " +
                 "los participantes sin excepcion (spec 9.2).")]
        public AudioClip targetReadingAudio;

        [Tooltip("Modelo 3D del objeto de anclaje, para la Object/Association Area.")]
        public GameObject anchorObjectPrefab;

        [Tooltip("Animacion objeto -> forma simplificada -> kanji (spec 5.1).")]
        public AnimationClip transformationAnimation;

        [Tooltip("Imagen de la asociacion visual, para el cue VISUAL_ASSOCIATION.")]
        public Sprite visualAssociationSprite;

        // ------------------------------------------------------------------
        // Lo que NO va aqui
        // ------------------------------------------------------------------
        //
        // Estado por participante -- clasificacion de pre-test, replacement tier,
        // asignacion de sesion, historial de trials. Spec 4.3 es explicito: "must
        // not be stored on the shared ScriptableObject asset; they belong to
        // session state".
        //
        // Un ScriptableObject es un asset compartido. Escribir ahi la clasificacion
        // de pre-test la deja persistida en el Editor y filtrandose de un
        // participante al siguiente, sin que nada lo indique. La version anterior
        // de esta clase tenia `knowledgeClassification` y ese era el fallo.
        //
        // Distractores -- se derivan del set en tiempo de ejecucion (spec 6.1):
        // cada trial saca sus opciones incorrectas de los otros cuatro kanji del
        // mismo set. Guardarlos por item duplicaria un dato que ya esta en la
        // composicion del set.
        //
        // Cues de asistencia -- 4.3 los lista como campo del item, pero 9.1 los
        // decide por TIPO DE TRIAL y no por kanji: en T3 no hay audio de la lectura
        // objetivo antes de responder, sea cual sea el kanji. Un campo por item no
        // podria expresar eso. La matriz vive en LearningAssistanceController; lo
        // que si vive aqui son los assets que realizan los cues.
    }

    /// <summary>Un grupo de trazos del ensamblaje guiado (spec 5.3).</summary>
    [Serializable]
    public class AssemblySegment
    {
        [Tooltip("Id estable. Viaja en la telemetria de ensamblaje.")]
        public string segmentId;

        [Tooltip("Descripcion legible. Ej: 'marco exterior', 'trazos interiores'.")]
        public string description;

        [Tooltip("Posicion del slot destino, relativa al centro del board.")]
        public Vector3 slotPosition;

        [Tooltip("Prefab o sprite del segmento. En Fase 2 es placeholder.")]
        public GameObject segmentAsset;
    }

    /// <summary>
    /// Como se introduce el kanji en S5 (spec 5.1). El valor viene del JSON.
    ///
    /// En Fase 2 los 35 kanji del estudio son pictograficos, de las cuatro
    /// lecciones "Kanji made from pictures", y todos tienen derivacion de cuatro
    /// etapas. KanjiDiscoveryController NO ramifica. El enum existe porque Fase 3
    /// puede reabrir el pool, no porque hoy haya dos caminos.
    /// </summary>
    public enum DiscoveryType
    {
        None,
        Pictographic,
        Contextual,
    }

    /// <summary>Pool al que pertenece el kanji (spec 4.1 y 4.2). Viene del JSON.</summary>
    public enum ExperimentalSet
    {
        A,
        B,
        C,
        Reserve,
        Tutorial,
    }

    /// <summary>
    /// Clasificacion de pre-test (spec 13.2).
    ///
    /// Vive aqui como tipo, pero el VALOR es estado de sesion por participante y
    /// no puede guardarse en el KanjiLearningItem. Ver el comentario del final de
    /// esa clase.
    /// </summary>
    public enum KnowledgeClassification
    {
        Unknown,
        PartiallyKnown,
        Known,
    }
}

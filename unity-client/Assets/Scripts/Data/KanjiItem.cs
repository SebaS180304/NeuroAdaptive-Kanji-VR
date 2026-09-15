using UnityEngine;

namespace NeuroAdaptiveVR.Data
{
    /// <summary>
    /// Un kanji completo, en tiempo de ejecucion: la fila del contrato mas el
    /// asset con lo que el contrato no puede llevar.
    ///
    /// POR QUE EXISTE
    /// --------------
    /// Los datos de un kanji viven a proposito en dos archivos --el JSON
    /// generado y el ScriptableObject autorado-- porque uno es contenido
    /// derivado y el otro son referencias a assets de Unity. Eso es correcto en
    /// disco y muy incomodo en el codigo: sin esto, cada consumidor recibiria
    /// dos objetos y tendria que acordarse de cual pregunta a cual.
    ///
    /// Aqui se unen una vez, en KanjiContentController, y de ahi en adelante
    /// circula un solo objeto. No guarda copia de nada: cada propiedad delega.
    ///
    /// Es de solo lectura porque el contenido de una sesion no cambia durante
    /// la sesion. El estado por participante --clasificacion de pre-test,
    /// historial-- vive en el estado de sesion, no aqui (spec 4.3).
    /// </summary>
    public sealed class KanjiItem
    {
        /// <summary>La fila del contrato. Nunca null.</summary>
        public readonly KanjiContentRecord Content;

        /// <summary>
        /// El asset con audio, prefabs y segmentos. PUEDE SER NULL: el banco de
        /// pruebas arma items sin assets para poder ejercitar el ciclo antes de
        /// que exista una sola grabacion. Las propiedades de assets devuelven
        /// null en ese caso en vez de reventar.
        /// </summary>
        public readonly KanjiLearningItem Assets;

        public KanjiItem(KanjiContentRecord content, KanjiLearningItem assets)
        {
            Content = content ?? throw new System.ArgumentNullException(nameof(content));
            Assets = assets;
        }

        // ------------------------------------------------------------------
        // Contenido (del JSON)
        // ------------------------------------------------------------------

        /// <summary>Lo que viaja como kanji_id en la telemetria.</summary>
        public string KanjiId => Content.Id;

        public string Character => Content.Character;

        /// <summary>
        /// El significado que se ensena y se evalua.
        ///
        /// Spec 4.3 lista "Meaning" y "Target Meaning" por separado, pero la
        /// tabla congelada asigna UNO por kanji, asi que el significado de
        /// diccionario y el objetivo son el mismo texto. Se expone una sola
        /// propiedad en vez de dos identicas: dos campos que siempre valen lo
        /// mismo son dos campos que algun dia no lo valdran, sin que nada avise.
        /// Si Fase 3 necesita separarlos, la separacion va en el contrato.
        /// </summary>
        public string Meaning => Content.Meaning;

        /// <summary>La UNICA lectura que se ensena y se evalua (spec 4.3).</summary>
        public string TargetReading => Content.TargetReading;

        public ExperimentalSet Pool => Content.Pool;
        public DiscoveryType DiscoveryType => Content.DiscoveryType;

        // ------------------------------------------------------------------
        // Assets (del ScriptableObject)
        // ------------------------------------------------------------------

        public AudioClip TargetReadingAudio => Assets != null ? Assets.targetReadingAudio : null;
        public GameObject AnchorObjectPrefab => Assets != null ? Assets.anchorObjectPrefab : null;
        public AnimationClip TransformationAnimation => Assets != null ? Assets.transformationAnimation : null;
        public Sprite VisualAssociationSprite => Assets != null ? Assets.visualAssociationSprite : null;
        public string VisualAssociation => Assets != null ? Assets.visualAssociation : null;

        public System.Collections.Generic.IReadOnlyList<AssemblySegment> AssemblySegments =>
            Assets != null ? Assets.assemblySegments : System.Array.Empty<AssemblySegment>();

        /// <summary>True si este item todavia no tiene assets autorados.</summary>
        public bool IsContentOnly => Assets == null;

        public override string ToString() => $"{Character} ({KanjiId})";
    }
}

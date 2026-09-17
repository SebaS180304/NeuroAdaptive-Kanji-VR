using System;
using System.Collections.Generic;
using System.Linq;
using NeuroAdaptiveVR.Data;
using UnityEngine;

namespace NeuroAdaptiveVR.Core
{
    /// <summary>
    /// Genera la secuencia de trials de un bloque (spec 6.1).
    ///
    /// CLASE PURA, SIN MonoBehaviour
    /// -----------------------------
    /// No toca la escena, no busca componentes y no emite telemetria: recibe los
    /// items, los parametros y la seed, y devuelve un TrialPlan. Asi el arnes de
    /// pruebas lo ejercita en edit mode, sin entrar en Play.
    ///
    /// Eso no es comodidad. Lo que solo se puede probar jugando se prueba poco, y
    /// las propiedades que este componente tiene que garantizar --determinismo,
    /// separacion minima, cobertura del cruce-- son justo las que no se ven
    /// jugando: hay que mirar la secuencia entera y compararla con otra.
    ///
    /// LO QUE NO HACE
    /// --------------
    /// Adaptarse. Spec 6.1 es explicito: el espaciado es predeterminado y no es
    /// adaptativo en el MVP. El plan se genera una vez y nadie lo altera durante
    /// la sesion.
    /// </summary>
    public static class TrialSequenceGenerator
    {
        /// <summary>
        /// Cuantas veces se reintenta ordenar antes de rendirse con la separacion.
        /// Cada intento usa una seed derivada, asi que el resultado sigue siendo
        /// funcion de la seed original.
        /// </summary>
        private const int MaxOrderingAttempts = 24;

        private const string Log = "[TrialSequence]";

        // Etiquetas de los sorteos. Separan los flujos aleatorios entre si: ver
        // Derive() al final del archivo.
        private const int TagOptions  = 1;
        private const int TagExtras   = 2;
        private const int TagTypeMix  = 3;
        private const int TagKanjiMix = 4;
        private const int TagOrder    = 5;

        /// <summary>
        /// Construye el plan de un bloque.
        /// </summary>
        /// <param name="state">El estado que lo va a correr. Da el prefijo del trial_id.</param>
        /// <param name="set">Los cinco kanji del set de la sesion, en orden del contrato.</param>
        /// <param name="totalTrials">
        /// Cuantos trials. 15 o mas incluye el cruce completo (5 kanji x 3 tipos)
        /// mas los extras; menos de 15 reparte por tipo lo mas parejo posible.
        /// </param>
        /// <param name="minLag">Separacion minima entre dos apariciones del mismo kanji.</param>
        /// <param name="seed">experiment_sessions.random_seed, pasada por StableHash.</param>
        public static TrialPlan Build(GameFlowState state, IReadOnlyList<KanjiItem> set,
                                      int totalTrials, int minLag, int seed)
        {
            if (set == null || set.Count < 4)
            {
                Debug.LogError($"{Log} Hacen falta al menos 4 kanji para construir " +
                               "cuatro opciones distintas (spec 9.3). Recibidos: " +
                               (set?.Count ?? 0) + ".");
                return new TrialPlan(state, seed, minLag, Array.Empty<PlannedTrial>(), 0);
            }
            if (totalTrials <= 0)
            {
                Debug.LogError($"{Log} totalTrials = {totalTrials}.");
                return new TrialPlan(state, seed, minLag, Array.Empty<PlannedTrial>(), 0);
            }

            var pares = ComposePairs(set, totalTrials, seed);
            var ordenados = Order(pares, minLag, seed, out int intentos);

            var trials = new List<PlannedTrial>(ordenados.Count);
            for (int i = 0; i < ordenados.Count; i++)
            {
                var (item, tipo) = ordenados[i];
                // La seed de las opciones se deriva de la posicion, no del
                // generador compartido: asi el orden de las opciones del trial 7
                // es el mismo aunque cambie el numero total de trials.
                var opciones = BuildOptions(set, item, tipo, Derive(seed, TagOptions, i));
                trials.Add(new PlannedTrial(i + 1, item, tipo, opciones));
            }

            var plan = new TrialPlan(state, seed, minLag, trials, intentos);
            Debug.Log($"{Log} {plan.Summary()}");

            if (plan.ShortestLag() < minLag && plan.Count > set.Count)
                Debug.LogWarning($"{Log} No se pudo respetar la separacion minima de {minLag} " +
                                 $"en {MaxOrderingAttempts} intentos; la mas corta quedo en " +
                                 $"{plan.ShortestLag()}. Con {set.Count} kanji y {plan.Count} trials " +
                                 "el margen es estrecho: bajar minLag o subir el numero de trials.");

            return plan;
        }

        // ------------------------------------------------------------------
        // Composicion: QUE trials hay, todavia sin orden
        // ------------------------------------------------------------------

        /// <summary>
        /// Decide el multiconjunto de pares (kanji, tipo).
        ///
        /// Dos regimenes, y la frontera esta en el cruce completo:
        ///
        /// - **total >= 15**: las 15 combinaciones van como base, y los extras se
        ///   sortean encima. Esto garantiza que CADA par (kanji, tipo) se mide al
        ///   menos una vez. Importa para el analisis: la pregunta abierta de
        ///   imageabilidad se contesta comparando kanji dentro del mismo
        ///   participante, y si el sorteo dejara a 火 sin ningun T3, esa
        ///   comparacion perderia una celda sin que nadie lo notara hasta el final.
        ///
        /// - **total &lt; 15** (S6, calibracion con 9): no cabe el cruce, asi que se
        ///   reparte lo mas parejo posible POR TIPO --tres de cada uno en el caso
        ///   de 9-- y los kanji se reparten dentro de cada tipo. La calibracion
        ///   mide tiempos de respuesta base, no cobertura de items.
        /// </summary>
        private static List<(KanjiItem item, RetrievalTrialType type)> ComposePairs(
            IReadOnlyList<KanjiItem> set, int total, int seed)
        {
            var tipos = new[]
            {
                RetrievalTrialType.MeaningToKanji,
                RetrievalTrialType.KanjiToMeaning,
                RetrievalTrialType.KanjiToReading,
            };

            var cruce = (from item in set from tipo in tipos select (item, tipo)).ToList();
            var salida = new List<(KanjiItem, RetrievalTrialType)>();

            if (total >= cruce.Count)
            {
                salida.AddRange(cruce);

                // Los extras se sortean del cruce, sin reponer hasta agotarlo, para
                // que el segundo pase sea tan parejo como el primero.
                var rng = new System.Random(Derive(seed, TagExtras, 0));
                var baraja = Shuffle(cruce.ToList(), rng);
                for (int i = 0; salida.Count < total; i++)
                    salida.Add(baraja[i % baraja.Count]);
            }
            else
            {
                // Reparto por tipo: 9 -> 3/3/3; 10 -> 4/3/3.
                var rngTipo = new System.Random(Derive(seed, TagTypeMix, 0));
                var porTipo = tipos.ToDictionary(t => t, _ => total / tipos.Length);
                var sobrantes = Shuffle(tipos.ToList(), rngTipo);
                for (int i = 0; i < total % tipos.Length; i++) porTipo[sobrantes[i]]++;

                foreach (var tipo in tipos)
                {
                    var rngKanji = new System.Random(Derive(seed, TagKanjiMix, (int)tipo));
                    var baraja = Shuffle(set.ToList(), rngKanji);
                    for (int i = 0; i < porTipo[tipo]; i++)
                        salida.Add((baraja[i % baraja.Count], tipo));
                }
            }

            return salida;
        }

        // ------------------------------------------------------------------
        // Orden: separacion minima entre apariciones del mismo kanji
        // ------------------------------------------------------------------

        /// <summary>
        /// Coloca los pares respetando la separacion minima.
        ///
        /// Voraz con barajado sembrado: en cada posicion se mira la lista
        /// barajada de lo que queda y se toma el primero cuyo kanji no aparezca
        /// en las ultimas `minLag` posiciones. Si no hay ninguno --callejon sin
        /// salida, que solo pasa cerca del final-- se reintenta la secuencia
        /// entera con una seed derivada.
        ///
        /// POR QUE NO SE APRIETA MAS LA SEPARACION. Con cinco kanji, exigir
        /// separacion 4 deja una sola solucion posible: la rotacion fija
        /// 1-2-3-4-5-1-2-3-4-5. Eso es exactamente lo que 6.1 prohibe al pedir
        /// "pseudorandomized rather than fixed", y un participante que detecta la
        /// rotacion deja de recuperar de memoria y empieza a predecir.
        /// </summary>
        private static List<(KanjiItem item, RetrievalTrialType type)> Order(
            List<(KanjiItem item, RetrievalTrialType type)> pares, int minLag, int seed,
            out int intentos)
        {
            List<(KanjiItem, RetrievalTrialType)> mejor = null;
            int mejorLag = -1;

            for (intentos = 1; intentos <= MaxOrderingAttempts; intentos++)
            {
                var rng = new System.Random(Derive(seed, TagOrder, intentos));
                var restantes = Shuffle(pares.ToList(), rng);
                var salida = new List<(KanjiItem, RetrievalTrialType)>(pares.Count);
                bool ok = true;

                while (restantes.Count > 0)
                {
                    int elegido = -1;
                    for (int i = 0; i < restantes.Count; i++)
                    {
                        if (LagOk(salida, restantes[i].item.KanjiId, minLag)) { elegido = i; break; }
                    }

                    if (elegido < 0) { ok = false; elegido = 0; }   // callejon: se coloca igual

                    salida.Add(restantes[elegido]);
                    restantes.RemoveAt(elegido);
                }

                int lag = ShortestLag(salida);
                if (ok && lag >= minLag) { return salida; }

                // Se guarda el mejor intento por si ninguno cumple: una secuencia
                // con la separacion algo corta es mejor que ninguna secuencia.
                if (lag > mejorLag) { mejorLag = lag; mejor = salida; }
            }

            intentos = MaxOrderingAttempts;
            return mejor;
        }

        private static bool LagOk(List<(KanjiItem item, RetrievalTrialType type)> colocados,
                                  string kanjiId, int minLag)
        {
            int desde = Math.Max(0, colocados.Count - minLag);
            for (int i = desde; i < colocados.Count; i++)
                if (colocados[i].item.KanjiId == kanjiId) return false;
            return true;
        }

        private static int ShortestLag(List<(KanjiItem item, RetrievalTrialType type)> lista)
        {
            var ultima = new Dictionary<string, int>();
            int peor = int.MaxValue;
            for (int i = 0; i < lista.Count; i++)
            {
                string id = lista[i].item.KanjiId;
                if (ultima.TryGetValue(id, out int antes)) peor = Math.Min(peor, i - antes);
                ultima[id] = i;
            }
            return peor;
        }

        // ------------------------------------------------------------------
        // Opciones
        // ------------------------------------------------------------------

        /// <summary>
        /// El objetivo mas tres distractores del MISMO set (spec 6.1), barajados.
        ///
        /// Lo que hace segura la derivacion son los chequeos intra-set: dentro de
        /// cada set las cinco lecturas, los cinco significados y las cinco formas
        /// son distintos, verificado por tools/kanji_metrics.py y por los casos
        /// S4 del arnes. Sin esa garantia un trial podria presentar dos opciones
        /// correctas, con ids distintos, y nada lo detectaria.
        /// </summary>
        public static List<TrialOption> BuildOptions(IReadOnlyList<KanjiItem> set, KanjiItem target,
                                                     RetrievalTrialType trialType, int seed)
        {
            var rng = new System.Random(seed);
            var distractores = Shuffle(set.Where(i => i.KanjiId != target.KanjiId).ToList(), rng)
                               .Take(3).ToList();

            var elegidos = new List<KanjiItem> { target };
            elegidos.AddRange(distractores);
            elegidos = Shuffle(elegidos, rng);

            return elegidos
                .Select(i => new TrialOption(i.KanjiId, OptionText(i, trialType),
                                             i.KanjiId == target.KanjiId))
                .ToList();
        }

        /// <summary>
        /// Que se muestra en la tarjeta depende del tipo: en T1 la respuesta es un
        /// kanji, en T2 un significado, en T3 una lectura (spec 6).
        /// </summary>
        private static string OptionText(KanjiItem item, RetrievalTrialType trialType) => trialType switch
        {
            RetrievalTrialType.MeaningToKanji => item.Character,
            RetrievalTrialType.KanjiToMeaning => item.Meaning,
            RetrievalTrialType.KanjiToReading => item.TargetReading,
            _ => item.Character,
        };

        // ------------------------------------------------------------------

        private static List<T> Shuffle<T>(List<T> items, System.Random rng)
        {
            for (int i = items.Count - 1; i > 0; i--)
            {
                int j = rng.Next(i + 1);
                (items[i], items[j]) = (items[j], items[i]);
            }
            return items;
        }

        /// <summary>
        /// Deriva una seed de la seed de la sesion mas una etiqueta y un indice.
        ///
        /// Existe para que los distintos sorteos --composicion, orden, opciones de
        /// cada trial-- no compartan un generador cuyo estado dependa del orden en
        /// que se llamaron. Ese fue el fallo del caso E7 del arnes el 15 de
        /// septiembre: un generador perezoso compartido hacia que el mismo codigo
        /// diera resultados distintos segun lo que hubiera corrido antes.
        /// </summary>
        private static int Derive(int seed, int tag, int index)
        {
            unchecked { return StableHash.Of($"{seed}:{tag}:{index}"); }
        }
    }
}

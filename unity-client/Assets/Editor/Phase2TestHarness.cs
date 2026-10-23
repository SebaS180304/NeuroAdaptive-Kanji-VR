using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using NeuroAdaptiveVR.Audio;
using NeuroAdaptiveVR.Controllers;
using NeuroAdaptiveVR.Core;
using NeuroAdaptiveVR.Data;
using NeuroAdaptiveVR.Networking;
using UnityEditor;
using UnityEngine;

namespace NeuroAdaptiveVR.EditorTools
{
    /// <summary>
    /// Arnes de pruebas de Fase 2. Corre en edit mode, no escribe nada y
    /// reporta PASS/FAIL por caso.
    ///
    /// QUE CUBRE Y QUE NO
    /// ------------------
    /// Solo lo que se puede decidir sin que nadie responda un trial: el
    /// contrato de contenido, los sets, la derivacion de distractores, la
    /// tabla de sustitucion, la capacidad y la contencion del ESL, el
    /// determinismo de la seed y el cableado de la escena.
    ///
    /// Lo que NO cubre, a proposito: que la telemetria llegue a la base con el
    /// payload correcto. Eso no se puede comprobar desde aqui y es justo donde
    /// este proyecto ha fallado mas veces --un `esl: "OFF"` por fallback es
    /// indistinguible de un OFF real hasta que se mira la fila--. Va en el
    /// protocolo manual y en database/verify_esl_content.sql.
    ///
    /// UNA ADVERTENCIA SOBRE EL CASO DE LA MATRIZ LAL
    /// ----------------------------------------------
    /// El caso L1 compara LearningAssistanceController contra una tabla que
    /// transcribi del spec. Comparte mi lectura del spec con el codigo que
    /// comprueba, asi que **no es verificacion independiente**: detecta que
    /// alguien cambie la tabla sin querer, no que la tabla este bien. La
    /// comprobacion independiente es la de verify_trials_v1.sql, que mira los
    /// cues que realmente se concedieron en una sesion.
    ///
    /// El caso L2 si es independiente: sale de la regla de 9.1 --"support is
    /// trial-aware so that a cue never directly reveals the target
    /// response"-- y no de la tabla.
    /// </summary>
    public static class Phase2TestHarness
    {
        private sealed class Case
        {
            public string Id;
            public string Title;
            public bool Passed;
            public string Detail;
        }

        private static List<Case> _cases;

        [MenuItem("Tools/NeuroAdaptive VR/Correr pruebas de Fase 2", priority = 200)]
        public static void Run()
        {
            _cases = new List<Case>();

            var content = UnityEngine.Object.FindAnyObjectByType<KanjiContentController>();
            if (content == null)
            {
                Debug.LogError("[Pruebas F2] No hay KanjiContentController en la escena abierta. " +
                               "Abre JapaneseLearningStudio.");
                return;
            }
            // Se mira ANTES de cargar, y se confia en IsLoaded en vez de llamar a
            // Load() sin condiciones. Es deliberado: si el arnes recargara siempre,
            // nunca volveria a ver el estado del que se queja este caso.
            //
            // El 15 de septiembre aqui salio un contrato zombi -- IsLoaded decia
            // true con el indice vacio, porque Unity resucita a medias el estado
            // al recargar el dominio. Ver el comentario de los campos del
            // controlador.
            bool deciaEstarCargado = content.IsLoaded;
            int indiceAntes = content.All.Count();
            Check("C0", "Si el contenido dice estar cargado, su indice no esta vacio",
                  !deciaEstarCargado || indiceAntes > 0,
                  $"IsLoaded={deciaEstarCargado} · indice={indiceAntes}");

            if (!content.IsLoaded && !content.Load())
            {
                Debug.LogError("[Pruebas F2] El contrato no carga. Nada mas tiene sentido hasta arreglarlo.");
                Report();
                return;
            }

            ContentCases(content);
            SetCases(content);
            SubstitutionCases(content);
            EffectiveSetCases(content);
            SequenceCases(content);
            AssociationCases(content);
            AssemblyCases(content);
            EnvironmentCases();
            AssistanceCases();
            MatrixCases();
            WiringCases(content);
            HapticCases();
            StimulusTelemetryCases(content);
            HeadBehaviorCases();
            DistractorCases();
            PeripheralAnimalCases();
            SetAObjectCases();
            JapaneseRoomCases();
            ProactiveCueCases();
            AdaptationLoopCases();
            ReconnectionCases();
            SoundSetCases();
            BaselineEyeCases();

            Report();
        }

        // ==================================================================
        // Contenido
        // ==================================================================

        private static void ContentCases(KanjiContentController c)
        {
            var items = c.All.ToList();
            var contrato = c.Contract;

            Check("C1", "El contrato trae 40 filas con id unico",
                  items.Count == 40 && items.Select(i => i.KanjiId).Distinct().Count() == 40,
                  $"{items.Count} items, {items.Select(i => i.KanjiId).Distinct().Count()} ids distintos");

            var sinAsset = items.Where(i => i.IsContentOnly).Select(i => i.KanjiId).ToList();
            Check("C2", "Cada fila del contrato tiene su KanjiLearningItem",
                  sinAsset.Count == 0,
                  sinAsset.Count == 0 ? "los 40 unidos" : $"sin asset: {Join(sinAsset)}");

            // Por que importa: el id acaba en nombres de archivo, en URLs del
            // backend y en claves de Postgres. Un caracter fuera de ASCII ahi
            // funciona hasta que algo en la cadena no lo trata igual.
            var raros = items.Where(i => !i.KanjiId.All(ch => ch == '_' || (ch >= 'A' && ch <= 'Z')))
                             .Select(i => i.KanjiId).ToList();
            Check("C3", "Todos los kanji_id son ASCII en mayusculas",
                  raros.Count == 0, raros.Count == 0 ? "ok" : Join(raros));

            var sinLectura = items.Where(i => string.IsNullOrWhiteSpace(i.TargetReading) ||
                                              string.IsNullOrWhiteSpace(i.Meaning))
                                  .Select(i => i.KanjiId).ToList();
            Check("C4", "Ninguna fila viene sin significado o sin lectura objetivo",
                  sinLectura.Count == 0, sinLectura.Count == 0 ? "ok" : Join(sinLectura));

            // Las dos excepciones declaradas de la regla de lectura objetivo
            // (spec 4.3). Si alguna cambiara sin querer, el estudio estaria
            // ensenando una lectura que el libro marca como rara.
            var mon = c.ByCharacter("門");
            var niku = c.ByCharacter("肉");
            Check("C5", "Las dos excepciones de lectura objetivo siguen en pie (門→もん, 肉→にく)",
                  mon != null && mon.TargetReading == "もん" &&
                  niku != null && niku.TargetReading == "にく",
                  $"門→{mon?.TargetReading} · 肉→{niku?.TargetReading}");

            Check("C6", "El contrato declara la tipografia con la que se midio",
                  contrato != null && !string.IsNullOrWhiteSpace(contrato.Font),
                  contrato?.Font ?? "(vacio)");
        }

        // ==================================================================
        // Sets y distractores
        // ==================================================================

        private static void SetCases(KanjiContentController c)
        {
            var nombres = c.SetNames;
            Check("S1", "Hay tres sets de cinco kanji",
                  nombres.Count == 3 && nombres.All(n => c.Set(n).Count == 5),
                  Join(nombres.Select(n => $"{n}:{c.Set(n).Count}")));

            var todos = nombres.SelectMany(n => c.Set(n).Select(i => i.KanjiId)).ToList();
            Check("S2", "Ningun kanji esta en dos sets",
                  todos.Distinct().Count() == todos.Count,
                  todos.Count == todos.Distinct().Count()
                      ? "15 distintos"
                      : Join(todos.GroupBy(x => x).Where(g => g.Count() > 1).Select(g => g.Key)));

            Check("S3", "Reserva 20 y tutorial 5, sin solaparse con los experimentales",
                  c.Reserve.Count == 20 && c.Tutorial.Count == 5 &&
                  !c.Reserve.Any(r => todos.Contains(r.KanjiId)) &&
                  !c.Tutorial.Any(t => todos.Contains(t.KanjiId)),
                  $"reserva {c.Reserve.Count} · tutorial {c.Tutorial.Count}");

            // ESTE es el caso que hace segura la derivacion de distractores.
            //
            // Cada trial toma sus tres opciones incorrectas de los otros cuatro
            // kanji del mismo set (spec 6.1). Si dos kanji del mismo set
            // compartieran lectura, un trial T3 mostraria la respuesta correcta
            // dos veces y el participante acertaria o fallaria por un motivo que
            // no es el que se mide. Nada en el codigo del trial lo detectaria:
            // las dos opciones tendrian ids distintos.
            foreach (var n in nombres)
            {
                var set = c.Set(n);
                var lecturas = set.Select(i => i.TargetReading).ToList();
                var significados = set.Select(i => i.Meaning).ToList();
                var caracteres = set.Select(i => i.Character).ToList();

                Check($"S4-{n}", $"Set {n}: las cinco lecturas, significados y formas son distintos",
                      lecturas.Distinct().Count() == 5 &&
                      significados.Distinct().Count() == 5 &&
                      caracteres.Distinct().Count() == 5,
                      $"lecturas {lecturas.Distinct().Count()}/5 · " +
                      $"significados {significados.Distinct().Count()}/5 · " +
                      $"formas {caracteres.Distinct().Count()}/5 — {Join(lecturas)}");
            }

            // Un set con menos de cuatro items no puede producir cuatro
            // opciones, y §9.3 fija cuatro sin excepcion.
            Check("S5", "Cada set puede producir cuatro opciones distintas",
                  nombres.All(n => c.Set(n).Count >= 4), "ok");
        }

        // ==================================================================
        // Sustitucion (spec 13.2)
        // ==================================================================

        private static void SubstitutionCases(KanjiContentController c)
        {
            var problemas = new List<string>();
            int minSust = int.MaxValue, maxSust = 0;

            foreach (var n in c.SetNames)
            {
                var set = c.Set(n);
                foreach (var item in set)
                {
                    var subs = c.SubstitutesFor(n, item);
                    minSust = Mathf.Min(minSust, subs.Count);
                    maxSust = Mathf.Max(maxSust, subs.Count);

                    if (subs.Count < 3)
                        problemas.Add($"{item.Character} en {n} tiene {subs.Count}");

                    // La sustitucion tiene que dejar el set igual de jugable:
                    // si el reemplazo comparte lectura o significado con alguno
                    // de los cuatro que se quedan, el trial vuelve a tener dos
                    // opciones correctas -- el mismo fallo de S4, pero solo en
                    // los participantes que reciban esa sustitucion.
                    var resto = set.Where(i => i.KanjiId != item.KanjiId).ToList();
                    foreach (var r in subs)
                    {
                        if (resto.Any(x => x.TargetReading == r.TargetReading))
                            problemas.Add($"{r.Character} sustituiria a {item.Character} en {n} " +
                                          $"y comparte lectura {r.TargetReading} con el resto");
                        if (resto.Any(x => x.Meaning == r.Meaning))
                            problemas.Add($"{r.Character} sustituiria a {item.Character} en {n} " +
                                          $"y comparte significado '{r.Meaning}'");
                    }
                }
            }

            Check("R1", "Cada kanji experimental tiene al menos tres sustitutos",
                  !problemas.Any(p => p.Contains("tiene")),
                  $"rango {minSust}-{maxSust} sustitutos");

            Check("R2", "Ningun sustituto colisiona con los cuatro que se quedan",
                  !problemas.Any(p => p.Contains("comparte")),
                  problemas.Count == 0 ? "ok" : Join(problemas.Where(p => p.Contains("comparte")).Take(4)));

            // La unica restriccion explicita del spec 4.2: "日 may only replace 火,
            // because both are read ひ".
            //
            // OJO CON COMO SE COMPRUEBA. La frase del spec suena global, pero solo
            // puede serlo dentro del set donde vive 火. Si 日 entrara en el set B
            // los dos nunca coincidirian en una sesion, porque 火 es del set A, y
            // la colision ひ no puede ocurrir. La primera version de este caso
            // afirmaba la version global y marcaba FAIL sobre una tabla correcta:
            // el error era mio, no del script.
            //
            // Lo que se comprueba es la propiedad que de verdad protege el trial:
            // dentro del set que contiene a 火, el unico hueco que 日 puede ocupar
            // es el de 火. Que eso se cumpla no es una regla aparte en el codigo:
            // sale sola de la condicion (1) de 13.2, porque para cualquier otro
            // hueco del set A los cuatro que se quedan incluyen a 火.
            var setDeFuego = c.SetNames.FirstOrDefault(n => c.Set(n).Any(i => i.Character == "火"));
            if (setDeFuego == null)
            {
                Check("R3", "El set que contiene 火 existe", false, "火 no esta en ningun set");
            }
            else
            {
                var huecos = c.Set(setDeFuego)
                              .Where(item => c.SubstitutesFor(setDeFuego, item).Any(s => s.Character == "日"))
                              .Select(item => item.Character).ToList();

                Check("R3", $"En el set {setDeFuego}, 日 solo puede reemplazar a 火 (spec 4.2)",
                      huecos.Count == 1 && huecos[0] == "火",
                      huecos.Count == 0
                          ? "日 no puede reemplazar a nadie en ese set"
                          : $"puede reemplazar a: {Join(huecos)}");
            }
        }

        // ==================================================================
        // Generador de secuencia (spec 6.1)
        // ==================================================================

        // ==================================================================
        // Set efectivo (kanji_items, Task 1.8 del plan del portal)
        // ==================================================================

        /// <summary>
        /// The backend sends the session's effective set: the assigned set with each
        /// pre-test substitute in its original's position. Unity must play exactly
        /// that list, in that order, and draw distractors only from it.
        /// </summary>
        private static void EffectiveSetCases(KanjiContentController c)
        {
            var setA = c.Set("A");
            if (setA.Count < 5) { Check("K0", "El set A tiene cinco kanji", false, $"{setA.Count}"); return; }
            var sub = c.SubstitutesFor("A", setA[1]).FirstOrDefault();
            if (sub == null) { Check("K0", "El segundo kanji de A tiene un sustituto", false, "ninguno"); return; }

            var chars = setA.Select(i => i.Character).ToList();
            chars[1] = sub.Character;
            string json = "{\"id\":\"s1\",\"assigned_kanji_set\":\"A\",\"random_seed\":\"777\"," +
                          "\"condition\":\"STATIC\",\"visit_number\":1,\"kanji_items\":[" +
                          string.Join(",", chars.Select(ch => $"\"{ch}\"")) + "]}";

            var parsed = SessionBootstrap.ReadKanjiItems(json);
            Check("K1", "El bootstrap lee kanji_items de la sesion, en orden",
                  parsed != null && parsed.SequenceEqual(chars),
                  parsed == null ? "null" : Join(parsed));
            Check("K2", "Sin kanji_items (o null) el bootstrap no inventa una lista",
                  SessionBootstrap.ReadKanjiItems("{\"id\":\"s1\"}") == null &&
                  SessionBootstrap.ReadKanjiItems("{\"id\":\"s1\",\"kanji_items\":null}") == null,
                  "ausente y null -> null");

            SessionContext.Reset();
            SessionContext.Install("s1", "A", "777", "STATIC", "1", parsed);
            var items = c.Items(SessionContext.KanjiItems);
            Check("K3", "El contenido devuelve el set efectivo con el sustituto en su posicion",
                  items.Select(i => i.Character).SequenceEqual(chars) && items[1].KanjiId == sub.KanjiId,
                  Join(items.Select(i => i.Character)));

            var plan = TrialSequenceGenerator.Build(GameFlowState.S7_ExperimentalRetrieval, items, 20, 2, 777);
            var ids = new HashSet<string>(items.Select(i => i.KanjiId));
            var fuera = plan.Trials.SelectMany(t => t.Options.Select(o => o.OptionId).Prepend(t.Target.KanjiId))
                            .Where(id => !ids.Contains(id)).Distinct().ToList();
            Check("K4", "Objetivos y distractores salen solo del set efectivo",
                  fuera.Count == 0 && plan.Trials.Any(t => t.Target.KanjiId == sub.KanjiId),
                  fuera.Count == 0 ? $"{plan.Count} trials, el sustituto {sub.Character} aparece" : $"fuera del set: {Join(fuera)}");

            SessionContext.Reset();
            Check("K5", "Reset borra el set efectivo (no pasa de un Play al siguiente)",
                  SessionContext.KanjiItems == null, "KanjiItems == null");
        }

        private static void SequenceCases(KanjiContentController c)
        {
            var set = c.Set("A");
            if (set.Count < 5) { Check("Q0", "El set A tiene cinco kanji", false, $"{set.Count}"); return; }

            const int seedA = 20260909;
            const int seedB = 777;
            const int minLag = 2;

            var p1 = TrialSequenceGenerator.Build(GameFlowState.S7_ExperimentalRetrieval, set, 20, minLag, seedA);
            var p2 = TrialSequenceGenerator.Build(GameFlowState.S7_ExperimentalRetrieval, set, 20, minLag, seedA);
            var pB = TrialSequenceGenerator.Build(GameFlowState.S7_ExperimentalRetrieval, set, 20, minLag, seedB);

            Check("Q1", "Misma seed produce la misma secuencia, opciones y orden incluidos",
                  Fingerprint(p1) == Fingerprint(p2),
                  $"{p1.Count} trials · huella {Fingerprint(p1).GetHashCode():X8}");

            // Sin este caso, Q1 pasaria igual si el generador ignorara la seed.
            Check("Q2", "Seeds distintas producen secuencias distintas",
                  Fingerprint(p1) != Fingerprint(pB),
                  Fingerprint(p1) == Fingerprint(pB) ? "identicas" : $"seed {seedA} != seed {seedB}");

            Check("Q3", $"Ningun kanji se repite con separacion menor que {minLag}",
                  p1.ShortestLag() >= minLag,
                  $"separacion mas corta {p1.ShortestLag()} · {p1.OrderingAttempts} intento(s)");

            // 5 kanji x 3 tipos = 15. Con 20 trials el cruce completo cabe, y que
            // quepa no basta: hay que comprobar que efectivamente esta.
            Check("Q4", "Un plan de 20 cubre los 15 pares (kanji, tipo)",
                  p1.DistinctPairs == 15, $"{p1.DistinctPairs}/15 pares");

            var malFormados = p1.Trials.Where(t =>
                t.Options.Count != 4 ||
                t.Options.Count(o => o.IsCorrect) != 1 ||
                t.Options.Select(o => o.OptionId).Distinct().Count() != 4).ToList();

            Check("Q5", "Todos los trials traen 4 opciones, una correcta, sin ids repetidos",
                  malFormados.Count == 0,
                  malFormados.Count == 0 ? $"{p1.Count} trials revisados"
                                         : $"{malFormados.Count} mal formados");

            var idsDelSet = set.Select(i => i.KanjiId).ToHashSet();
            var fuera = p1.Trials.SelectMany(t => t.Options.Select(o => o.OptionId))
                                 .Where(id => !idsDelSet.Contains(id)).Distinct().ToList();

            Check("Q6", "Todos los distractores salen del mismo set que el objetivo",
                  fuera.Count == 0, fuera.Count == 0 ? "ok" : Join(fuera));

            // S8: spec 7.9 da el numero exacto -- 5 kanji x 3 tipos, sin extras.
            var s8 = TrialSequenceGenerator.Build(GameFlowState.S8_ImmediateAssessment, set, 15, minLag, seedA);
            bool cadaParUnaVez = s8.Trials
                .GroupBy(t => $"{t.Target.KanjiId}|{t.TrialType}")
                .All(g => g.Count() == 1);

            Check("Q7", "El plan de S8 es el cruce completo exacto: 15 trials, cada par una vez",
                  s8.Count == 15 && s8.DistinctPairs == 15 && cadaParUnaVez,
                  $"{s8.Count} trials · {s8.DistinctPairs} pares · sin repetir: {cadaParUnaVez}");

            // S6: 9 trials, tres por tipo (decision del 16 de septiembre, pendiente
            // de justificar con investigacion).
            var s6 = TrialSequenceGenerator.Build(GameFlowState.S6_GuidedPracticeCalibration, set, 9, minLag, seedA);
            var porTipo = s6.Trials.GroupBy(t => t.TrialType).ToDictionary(g => g.Key, g => g.Count());
            Check("Q8", "El plan de S6 son 9 trials repartidos tres por tipo",
                  s6.Count == 9 && porTipo.Count == 3 && porTipo.Values.All(v => v == 3),
                  Join(porTipo.Select(kv => $"{kv.Key}:{kv.Value}")));

            // El hash tiene que ser estable: si no lo fuera, dos corridas de la
            // misma sesion darian secuencias distintas y la seed no serviria de nada.
            Check("Q9", "StableHash devuelve el mismo valor para el mismo texto",
                  StableHash.Of("20260909") == StableHash.Of("20260909") &&
                  StableHash.Of("piloto-p03") != StableHash.Of("piloto-p04") &&
                  StableHash.Of("20260909") != 0,
                  $"\"20260909\" -> {StableHash.Of("20260909")}");
        }

        /// <summary>
        /// Huella de un plan: todo lo que tiene que ser identico entre dos
        /// generaciones con la misma seed. Incluye el ORDEN de las opciones, no
        /// solo cuales son -- una reconstruccion que baraja distinto no
        /// reconstruye la misma tarea.
        /// </summary>
        // ==================================================================
        // S5 guided association (decision D3, 24 September)
        // ==================================================================

        private static void AssociationCases(KanjiContentController c)
        {
            var set = c.Set("A");
            if (set.Count < 5) { Check("A0", "El set A tiene cinco kanji", false, $"{set.Count}"); return; }

            var s5 = GameFlowState.S5_StandardizedLearning;
            int seed = TrialSequenceGenerator.BlockSeed(StableHash.Of("20260909"), s5);
            var p1 = TrialSequenceGenerator.BuildOnePerKanji(s5, set, seed);
            var p2 = TrialSequenceGenerator.BuildOnePerKanji(s5, set, seed);

            // A1 is the case that matters: trial i belongs to kanji i, so every
            // kanji gets exactly one association, right after its exposure.
            bool enOrden = p1.Count == set.Count;
            for (int i = 0; enOrden && i < set.Count; i++)
                enOrden = p1.Trials[i].Target.KanjiId == set[i].KanjiId;
            Check("A1", "S5 planea exactamente un trial por kanji, en el orden del set",
                  enOrden,
                  string.Join(" ", p1.Trials.Select(t => t.Target.Character + ":" + t.TrialType)));

            Check("A2", "Misma seed produce la misma asociacion, tipos y opciones incluidos",
                  Fingerprint(p1) == Fingerprint(p2),
                  $"{p1.Count} trials");

            // Five kanji, three types: balanced before shuffling, so 2/2/1.
            // A pure random draw could give five of one type, and S5
            // instruction would then differ between participants by chance.
            var porTipo = p1.Trials.GroupBy(t => t.TrialType).ToDictionary(g => g.Key, g => g.Count());
            bool balanceado = porTipo.Count == 3 && porTipo.Values.All(n => n >= 1 && n <= 2);
            Check("A3", "Los tipos de la asociacion quedan repartidos 2/2/1",
                  balanceado,
                  string.Join(" · ", porTipo.Select(kv => $"{kv.Key}={kv.Value}")));

            bool opcionesOk = p1.Trials.All(t => t.Options.Count == 4 && t.Options.Count(o => o.IsCorrect) == 1);
            Check("A4", "Cada trial de asociacion trae 4 opciones con exactamente una correcta",
                  opcionesOk, opcionesOk ? "5/5" : "hay trials mal formados");

            // The reason BlockSeed exists: blocks must not share their draws.
            int baseSeed = StableHash.Of("20260909");
            var seeds = new[] { s5, GameFlowState.S6_GuidedPracticeCalibration,
                                GameFlowState.S7_ExperimentalRetrieval, GameFlowState.S8_ImmediateAssessment }
                        .Select(st => TrialSequenceGenerator.BlockSeed(baseSeed, st)).ToList();
            Check("A5", "Cada bloque (S5-S8) tiene su propia seed derivada",
                  seeds.Distinct().Count() == seeds.Count && !seeds.Contains(baseSeed),
                  string.Join(", ", seeds));
        }

        // ==================================================================
        // Guided assembly (spec 5.3, D2)
        // ==================================================================

        private static void AssemblyCases(KanjiContentController c)
        {
            var all = c.All.ToList();
            int seed = TrialSequenceGenerator.BlockSeed(StableHash.Of("20260909"), GameFlowState.S5_StandardizedLearning);
            var plans = all.Select(k => (k, p: AssemblyPlan.For(k, seed))).ToList();

            // G1 is the one that matters: the piece count is part of the
            // balance band of spec 4.1, so it must come from the contract.
            var malContados = plans.Where(x => !x.p.Authored && x.p.Count != x.k.AssemblyGroups)
                                   .Select(x => x.k.Character).ToList();
            Check("G1", "Cada kanji sin segmentos autorados tiene tantos huecos como assemblyGroups",
                  malContados.Count == 0,
                  malContados.Count == 0 ? $"{all.Count} kanji" : string.Join(" ", malContados));

            // Only kanji that can reach S5: experimental and reserve (a reserve
            // item can substitute into a set). Tutorial kanji never get an
            // assembly -- and 一 has a single stroke group, so it could not.
            var tutorial = new HashSet<string>(c.Tutorial.Select(k => k.KanjiId));
            var enS5 = plans.Where(x => !tutorial.Contains(x.k.KanjiId)).ToList();
            var conProblema = enS5.Where(x => x.p.Problem != null).Select(x => $"{x.k.Character}: {x.p.Problem}").ToList();
            Check("G2", "Todo kanji que puede llegar a S5 tiene un plan de ensamblaje valido (2-4 segmentos, ids unicos)",
                  conProblema.Count == 0,
                  conProblema.Count == 0 ? $"{enS5.Count} kanji (sin los {tutorial.Count} del tutorial)" : string.Join(" · ", conProblema.Take(5)));

            bool mismoOrden = all.All(k => string.Join(",", AssemblyPlan.For(k, seed).RowOrder) ==
                                           string.Join(",", AssemblyPlan.For(k, seed).RowOrder));
            Check("G3", "Misma seed produce el mismo orden de la fila de segmentos",
                  mismoOrden, mismoOrden ? "ok" : "el orden cambia entre llamadas");

            bool permutacion = plans.All(x => x.p.RowOrder.OrderBy(i => i).SequenceEqual(Enumerable.Range(0, x.p.Count)));
            Check("G4", "La fila contiene cada segmento exactamente una vez",
                  permutacion, permutacion ? "ok" : "hay filas con segmentos repetidos o faltantes");

            // No row may equal slot order, or the participant can place left to
            // right without reading the shapes (17/40 did before 28 September).
            var identidad = plans.Where(x => x.p.Count > 1 && x.p.RowOrder.SequenceEqual(Enumerable.Range(0, x.p.Count)))
                                 .Select(x => x.k.Character).ToList();
            Check("G5", "Ninguna fila sale en el orden de los huecos",
                  identidad.Count == 0,
                  $"{identidad.Count}/{plans.Count(x => x.p.Count > 1)} filas en orden de huecos" +
                  (identidad.Count > 0 ? ": " + string.Join(" ", identidad) : ""));
        }

        private static string Fingerprint(TrialPlan plan)
            => string.Join(";", plan.Trials.Select(t =>
                   $"{t.Sequence}:{t.Target.KanjiId}:{t.TrialType}:" +
                   string.Join(",", t.Options.Select(o => o.OptionId))));

        // ==================================================================
        // Matriz del Apendice A
        // ==================================================================

        private static void MatrixCases()
        {
            // S8 es la medida primaria de aprendizaje inmediato y se define por
            // ser "no-assistance" (spec 7.9). Hasta el 16 de septiembre aceptaba
            // LAL=HIGH sin protestar.
            string conAyuda = StateLevelMatrix.Violation(
                GameFlowState.S8_ImmediateAssessment,
                StimulationOrAssistanceLevel.Focus, StimulationOrAssistanceLevel.High);

            Check("M1", "S8 con LAL=HIGH se reporta como violacion del Apendice A",
                  conAyuda != null, conAyuda ?? "NO detectada");

            string correcto = StateLevelMatrix.Violation(
                GameFlowState.S8_ImmediateAssessment,
                StimulationOrAssistanceLevel.Focus, StimulationOrAssistanceLevel.Off);

            Check("M2", "S8 con FOCUS/OFF es admisible",
                  correcto == null, correcto ?? "ok");

            // El otro lado: una matriz que dijera que todo esta mal tambien
            // pasaria M1. Se comprueba que los pares nominales de la tabla de
            // spec 7 pasen todos.
            var nominales = new (GameFlowState s, StimulationOrAssistanceLevel esl, StimulationOrAssistanceLevel lal)[]
            {
                (GameFlowState.S1_WelcomeOrientation, StimulationOrAssistanceLevel.Low, StimulationOrAssistanceLevel.Off),
                (GameFlowState.S3_SystemValidation, StimulationOrAssistanceLevel.Minimal, StimulationOrAssistanceLevel.Off),
                (GameFlowState.S4_EEGBaseline, StimulationOrAssistanceLevel.Baseline, StimulationOrAssistanceLevel.Off),
                (GameFlowState.S5_StandardizedLearning, StimulationOrAssistanceLevel.Low, StimulationOrAssistanceLevel.Off),
                (GameFlowState.S6_GuidedPracticeCalibration, StimulationOrAssistanceLevel.Medium, StimulationOrAssistanceLevel.Medium),
                (GameFlowState.S7_ExperimentalRetrieval, StimulationOrAssistanceLevel.Medium, StimulationOrAssistanceLevel.Medium),
                (GameFlowState.S9_SessionSummary, StimulationOrAssistanceLevel.Low, StimulationOrAssistanceLevel.Off),
            };
            var rechazados = nominales
                .Where(n => StateLevelMatrix.Violation(n.s, n.esl, n.lal) != null)
                .Select(n => n.s.ToString()).ToList();

            Check("M3", "Los pares nominales de la tabla de spec 7 son todos admisibles",
                  rechazados.Count == 0, rechazados.Count == 0 ? $"{nominales.Length} pares" : Join(rechazados));
        }

        // ==================================================================
        // ESL
        // ==================================================================

        private static void EnvironmentCases()
        {
            var esl = UnityEngine.Object.FindAnyObjectByType<EnvironmentalStimulationController>();
            if (esl == null)
            {
                Check("E0", "Hay un EnvironmentalStimulationController en la escena", false, "ausente");
                return;
            }

            var so = new SerializedObject(esl);
            var rootProp = so.FindProperty("environmentalLayerRoot").objectReferenceValue as Transform;
            Check("E0", "El ESL tiene su environmentalLayerRoot asignado",
                  rootProp != null, rootProp == null ? "NULL" : rootProp.name);
            if (rootProp == null) return;

            var perfiles = new List<EnvironmentProfile>();
            var pProp = so.FindProperty("profiles");
            for (int i = 0; i < pProp.arraySize; i++)
                perfiles.Add(pProp.GetArrayElementAtIndex(i).objectReferenceValue as EnvironmentProfile);

            Check("E1", "No hay perfiles nulos ni dos perfiles para el mismo nivel",
                  perfiles.All(p => p != null) &&
                  perfiles.Select(p => p.level).Distinct().Count() == perfiles.Count,
                  Join(perfiles.Select(p => p == null ? "NULL" : p.level.ToString())));

            // Los seis niveles que el Apendice A usa en algun estado. Un nivel
            // sin perfil no se aplica --el controlador lo rechaza en vez de
            // aceptarlo sin efecto-- asi que faltar uno significa que ese estado
            // no puede montarse.
            var necesarios = new[]
            {
                StimulationOrAssistanceLevel.Low, StimulationOrAssistanceLevel.Medium,
                StimulationOrAssistanceLevel.High, StimulationOrAssistanceLevel.Focus,
                StimulationOrAssistanceLevel.Minimal, StimulationOrAssistanceLevel.Baseline,
            };
            var faltan = necesarios.Where(l => perfiles.All(p => p == null || p.level != l)).ToList();
            Check("E2", "Existe perfil para los seis niveles del Apendice A",
                  faltan.Count == 0, faltan.Count == 0 ? "ok" : Join(faltan.Select(f => f.ToString())));

            // CAPACIDAD. Un perfil que pide mas objetos de los que hay en la
            // escena no falla: activa los que puede y sigue. El nivel resultante
            // seria mas bajo que el que la telemetria declara, que es
            // exactamente la clase de discrepancia silenciosa que este proyecto
            // lleva encontrando desde M1.
            foreach (var grupo in new[] { "Props", "Movers" })
            {
                var t = rootProp.Find(grupo);
                if (t == null) { Check($"E3-{grupo}", $"Existe {grupo}", false, "no existe"); continue; }
                var todos = t.GetComponentsInChildren<EnvironmentProp>(true);

                var cortos = new List<string>();
                foreach (var p in perfiles.Where(p => p != null))
                {
                    int pedido = grupo == "Props" ? p.propCountMax : p.moverCountMax;
                    int elegibles = todos.Count(x => x.Tier <= p.maxTier);
                    if (pedido > elegibles)
                        cortos.Add($"{p.level} pide {pedido} y hay {elegibles} con tier<={p.maxTier}");
                }

                Check($"E3-{grupo}", $"Ningun perfil pide mas {grupo} de los que hay en la escena",
                      cortos.Count == 0,
                      cortos.Count == 0
                          ? $"{todos.Length} objetos · tiers {Join(todos.GroupBy(x => x.Tier).OrderBy(g => g.Key).Select(g => $"T{g.Key}x{g.Count()}"))}"
                          : Join(cortos));
            }

            // Eventos perifericos: el scheduler usa los hijos directos del
            // contenedor, no componentes EnvironmentProp.
            var pe = rootProp.Find("PeripheralEvents");
            int hijos = pe == null ? 0 : pe.childCount;
            bool alguienLosPide = perfiles.Any(p => p != null && p.HasPeripheralEvents);
            Check("E4", "Si algun perfil pide eventos perifericos, hay objetos que disparar",
                  !alguienLosPide || hijos > 0,
                  $"contenedor con {hijos} objetos · los piden " +
                  Join(perfiles.Where(p => p != null && p.HasPeripheralEvents).Select(p => p.level.ToString())));

            // CONTENCION (spec 8.3). La frontera es estructural: lo que ESL
            // puede tocar es exactamente lo que cuelga del root.
            var sueltos = UnityEngine.Object
                .FindObjectsByType<EnvironmentProp>(FindObjectsInactive.Include, FindObjectsSortMode.None)
                .Where(p => !p.transform.IsChildOf(rootProp)).Select(p => p.name).ToList();
            Check("E5", "Ningun EnvironmentProp cuelga fuera de la Environmental Layer",
                  sueltos.Count == 0, sueltos.Count == 0 ? "ok" : Join(sueltos));

            // Y al reves: lo que ESL NO puede tocar no debe colgar de ahi.
            var prohibidos = new[] { "LearningBoard", "ResponseArea", "Floor", "Directional Light" };
            var dentro = prohibidos.Where(n =>
            {
                var go = GameObject.Find(n);
                return go != null && go.transform.IsChildOf(rootProp);
            }).ToList();
            Check("E6", "El board, la Response Area, el suelo y la luz estan FUERA de la layer",
                  dentro.Count == 0, dentro.Count == 0 ? "ok" : Join(dentro));

            DeterminismCase(esl, rootProp);
            VisibleBandCase(rootProp);
        }

        /// <summary>
        /// Misma seed, mismo entorno (spec 6.1). Se aplica un nivel dos veces y
        /// se compara que objetos quedaron activos.
        ///
        /// Guarda y restaura el estado activo de todo, porque esto corre en edit
        /// mode sobre la escena abierta: una prueba que deja la escena distinta
        /// de como la encontro es una prueba que hay que deshacer a mano.
        /// </summary>
        private static void DeterminismCase(EnvironmentalStimulationController esl, Transform root)
        {
            var props = root.GetComponentsInChildren<EnvironmentProp>(true);
            var estadoPrevio = props.ToDictionary(p => p, p => p.gameObject.activeSelf);
            var nivelPrevio = esl.CurrentLevel;

            try
            {
                // La seed se fija ANTES DE CADA aplicacion, no solo antes de la
                // segunda. La primera version de este caso no lo hacia y paso o
                // fallo segun lo que hubiera corrido antes en el mismo dominio:
                // el generador es perezoso y guarda su estado entre llamadas, asi
                // que "aplicar MEDIUM" dos veces seguidas consume posiciones
                // distintas de la misma secuencia. Una prueba cuyo resultado
                // depende de lo que paso antes no mide lo que dice medir.
                const int seedA = 20260909;
                const int seedB = 777;

                var primera = AplicarYLeer(esl, props, StimulationOrAssistanceLevel.Medium, seedA);
                var segunda = AplicarYLeer(esl, props, StimulationOrAssistanceLevel.Medium, seedA);
                var otraSeed = AplicarYLeer(esl, props, StimulationOrAssistanceLevel.Medium, seedB);
                var alto = AplicarYLeer(esl, props, StimulationOrAssistanceLevel.High, seedA);

                Check("E7", "MEDIUM con la misma seed activa el mismo conjunto",
                      primera.SequenceEqual(segunda),
                      $"{primera.Count} objetos · {Join(primera.Take(4))}");

                // La otra mitad, y la que impide que E7 pase por el motivo
                // equivocado: si el sorteo ignorara la seed, dos seeds distintas
                // darian el mismo conjunto y E7 seguiria en verde.
                //
                // Con 6 elegibles y 6 pedidos en MEDIUM el conjunto puede coincidir
                // legitimamente --se activan todos--, asi que lo que se compara es
                // el ORDEN de activacion, que si depende de la seed.
                Check("E8", "Dos seeds distintas no producen la misma seleccion",
                      !primera.SequenceEqual(otraSeed) ||
                      primera.Count == props.Count(p => p.Tier <= 2),
                      primera.SequenceEqual(otraSeed)
                          ? $"identicos, pero MEDIUM activa los {primera.Count} elegibles: no hay donde elegir"
                          : $"seed {seedA} y seed {seedB} difieren");

                Check("E8b", "HIGH activa mas objetos que MEDIUM",
                      alto.Count > segunda.Count,
                      $"MEDIUM {segunda.Count} · HIGH {alto.Count}");

                // F3.2 (30 sep): each level has its own generator derived from the
                // session seed. The room of a level must not depend on which
                // levels were applied before it -- with the old shared generator
                // the S5 room changed depending on whether S2 had run.
                esl.SetSeed(seedA);
                esl.SetLevel(StimulationOrAssistanceLevel.Low, betweenTrials: true);
                var lowPrimero = props.Where(p => p.gameObject.activeSelf).Select(p => p.name).OrderBy(x => x).ToList();
                esl.SetLevel(StimulationOrAssistanceLevel.High, betweenTrials: true);
                esl.SetLevel(StimulationOrAssistanceLevel.Medium, betweenTrials: true);
                esl.SetLevel(StimulationOrAssistanceLevel.Low, betweenTrials: true);
                var lowDespues = props.Where(p => p.gameObject.activeSelf).Select(p => p.name).OrderBy(x => x).ToList();
                Check("E11", "Un nivel da la misma sala sin importar que niveles se aplicaron antes",
                      lowPrimero.SequenceEqual(lowDespues),
                      $"LOW {Join(lowPrimero)} · tras HIGH y MEDIUM {Join(lowDespues)}");

                // The motion phase is part of the reconstruction: same seed, same
                // phase; another seed, another phase.
                var mover = props.FirstOrDefault(p => p.GetComponent<EnvironmentMotion>() != null);
                if (mover != null)
                {
                    float fA1 = EnvironmentMotion.PhaseFor(seedA, mover.name);
                    float fA2 = EnvironmentMotion.PhaseFor(seedA, mover.name);
                    float fB = EnvironmentMotion.PhaseFor(seedB, mover.name);
                    Check("E12", "La fase de movimiento sale de la seed: misma seed, misma fase; otra seed, otra fase",
                          Mathf.Approximately(fA1, fA2) && !Mathf.Approximately(fA1, fB),
                          $"{mover.name}: {fA1:0.000} / {fA2:0.000} / seed {seedB}: {fB:0.000}");
                }
                else
                {
                    Check("E12", "La fase de movimiento sale de la seed", false, "no hay ningun EnvironmentMotion en la capa");
                }

                esl.SetLevel(StimulationOrAssistanceLevel.Focus, betweenTrials: true);
                int enFocus = props.Count(p => p.gameObject.activeSelf);
                Check("E9", "FOCUS deja el entorno vacio sin tocar la iluminacion",
                      enFocus == 0, $"{enFocus} objetos activos en FOCUS");

                // El guard de 10.2 en su propia casa.
                var antes = esl.CurrentLevel;
                esl.SetLevel(StimulationOrAssistanceLevel.High, betweenTrials: false);
                Check("E10", "El ESL rechaza cambiar de nivel a media respuesta (spec 10.2)",
                      esl.CurrentLevel == antes,
                      $"nivel antes {antes} · despues {esl.CurrentLevel} (se espera un LogError arriba)");
            }
            finally
            {
                // El orden importa: SetLevel vuelve a tocar que objetos estan
                // activos, asi que restaurar el nivel PRIMERO y el estado visible
                // despues. Al reves, la ultima palabra la tendria el perfil y la
                // escena quedaria distinta de como se encontro.
                esl.ClearSeedOverride();
                if (nivelPrevio != StimulationOrAssistanceLevel.Off)
                    esl.SetLevel(nivelPrevio, betweenTrials: true);

                foreach (var kv in estadoPrevio)
                    if (kv.Key != null) kv.Key.gameObject.SetActive(kv.Value);
            }
        }

        /// <summary>
        /// Fija la seed, aplica el nivel y devuelve que objetos quedaron activos,
        /// ordenados. Fijar la seed cada vez es lo que hace que dos llamadas sean
        /// comparables: el generador del controlador es perezoso y conserva su
        /// estado entre aplicaciones.
        /// </summary>
        private static List<string> AplicarYLeer(EnvironmentalStimulationController esl,
                                                 EnvironmentProp[] props,
                                                 StimulationOrAssistanceLevel nivel,
                                                 int seed)
        {
            esl.SetSeed(seed);
            esl.SetLevel(nivel, betweenTrials: true);
            return props.Where(p => p.gameObject.activeSelf)
                        .Select(p => p.name).OrderBy(x => x).ToList();
        }

        // ==================================================================
        // LAL
        // ==================================================================

        private static void AssistanceCases()
        {
            // Tabla transcrita del spec 9.1. Ver la advertencia de la cabecera:
            // esto detecta un cambio accidental, no valida la lectura del spec.
            var esperado = new Dictionary<(StimulationOrAssistanceLevel, RetrievalTrialType), LalCue>
            {
                {(StimulationOrAssistanceLevel.Off,  RetrievalTrialType.MeaningToKanji), LalCue.None},
                {(StimulationOrAssistanceLevel.Off,  RetrievalTrialType.KanjiToMeaning), LalCue.None},
                {(StimulationOrAssistanceLevel.Off,  RetrievalTrialType.KanjiToReading), LalCue.None},
                {(StimulationOrAssistanceLevel.Low,  RetrievalTrialType.MeaningToKanji), LalCue.None},
                {(StimulationOrAssistanceLevel.Low,  RetrievalTrialType.KanjiToMeaning), LalCue.None},
                {(StimulationOrAssistanceLevel.Low,  RetrievalTrialType.KanjiToReading), LalCue.None},
                {(StimulationOrAssistanceLevel.Medium, RetrievalTrialType.MeaningToKanji), LalCue.TargetReadingAudio},
                {(StimulationOrAssistanceLevel.Medium, RetrievalTrialType.KanjiToMeaning), LalCue.TargetReadingAudio},
                {(StimulationOrAssistanceLevel.Medium, RetrievalTrialType.KanjiToReading), LalCue.VisualAssociation},
                {(StimulationOrAssistanceLevel.High, RetrievalTrialType.MeaningToKanji),
                    LalCue.VisualTransformation | LalCue.TargetReadingAudio},
                {(StimulationOrAssistanceLevel.High, RetrievalTrialType.KanjiToMeaning),
                    LalCue.ReverseSemanticAssociation | LalCue.TargetReadingAudio},
                {(StimulationOrAssistanceLevel.High, RetrievalTrialType.KanjiToReading),
                    LalCue.VisualAssociation | LalCue.VisualTransformation},
            };

            var fallos = esperado
                .Where(kv => LearningAssistanceController.AvailableCues(kv.Key.Item2, kv.Key.Item1) != kv.Value)
                .Select(kv => $"{kv.Key.Item1}/{kv.Key.Item2}: " +
                              $"{LearningAssistanceController.AvailableCues(kv.Key.Item2, kv.Key.Item1)} " +
                              $"!= {kv.Value}")
                .ToList();

            Check("L1", "Las 12 celdas de la matriz 9.1 coinciden con la tabla del spec",
                  fallos.Count == 0, fallos.Count == 0 ? "12/12" : Join(fallos));

            // INDEPENDIENTE de la tabla: sale de la regla de 9.1, "a cue never
            // directly reveals the target response". En T3 la respuesta ES la
            // lectura, asi que el audio queda prohibido en cualquier nivel --
            // incluidos los que ni siquiera son de LAL.
            var niveles = (StimulationOrAssistanceLevel[])
                Enum.GetValues(typeof(StimulationOrAssistanceLevel));
            var filtrados = niveles
                .Where(l => (LearningAssistanceController.AvailableCues(
                                RetrievalTrialType.KanjiToReading, l) & LalCue.TargetReadingAudio) != 0)
                .ToList();

            Check("L2", "Ningun nivel de LAL concede audio de la lectura en un trial T3",
                  filtrados.Count == 0,
                  filtrados.Count == 0 ? $"probados los {niveles.Length} niveles" : Join(filtrados.Select(f => f.ToString())));

            var lal = UnityEngine.Object.FindAnyObjectByType<LearningAssistanceController>();
            if (lal != null)
            {
                var antes = lal.CurrentLevel;
                lal.SetLevel(StimulationOrAssistanceLevel.High, betweenTrials: false);
                Check("L3", "El LAL rechaza cambiar de nivel a media respuesta (spec 10.2)",
                      lal.CurrentLevel == antes,
                      $"nivel antes {antes} · despues {lal.CurrentLevel} (se espera un LogError arriba)");
                lal.SetLevel(antes, betweenTrials: true);
            }
            else Check("L3", "Hay un LearningAssistanceController en la escena", false, "ausente");
        }

        // ==================================================================
        // Cableado
        // ==================================================================

        private static void WiringCases(KanjiContentController content)
        {
            var root = content.gameObject;

            var requeridos = new (string nombre, bool presente)[]
            {
                ("GameFlowController", root.GetComponent<GameFlowController>() != null),
                ("BehaviorTelemetryController", root.GetComponent<BehaviorTelemetryController>() != null),
                ("ResponseSystemController", root.GetComponent<ResponseSystemController>() != null),
                ("LearningAssistanceController", root.GetComponent<LearningAssistanceController>() != null),
                ("EnvironmentalStimulationController", root.GetComponent<EnvironmentalStimulationController>() != null),
                ("PronunciationAudioController", root.GetComponent<PronunciationAudioController>() != null),
            };
            var ausentes = requeridos.Where(r => !r.presente).Select(r => r.nombre).ToList();
            Check("W1", "Los seis controladores viven en el mismo GameObject que el contenido",
                  ausentes.Count == 0, ausentes.Count == 0 ? root.name : Join(ausentes));

            // El bloque de contexto de cada evento se arma leyendo estas tres
            // referencias. Si alguna es null, el payload sale con el valor por
            // omision del enum --y para el ESL ese valor es OFF, que es
            // indistinguible de un OFF real una vez esta en la base.
            var tel = root.GetComponent<BehaviorTelemetryController>();
            if (tel != null)
            {
                var so = new SerializedObject(tel);
                var faltan = new[] { "gameFlow", "stimulation", "assistance" }
                    .Where(n => so.FindProperty(n).objectReferenceValue == null).ToList();
                Check("W2", "La telemetria tiene sus tres fuentes de contexto cableadas",
                      faltan.Count == 0,
                      faltan.Count == 0
                          ? "gameFlow, stimulation, assistance"
                          : $"NULL: {Join(faltan)} — el payload saldria con el valor por omision");
            }

            var presenters = UnityEngine.Object
                .FindObjectsByType<MonoBehaviour>(FindObjectsInactive.Include, FindObjectsSortMode.None)
                .Where(m => m is ITrialPresenter).Select(m => m.GetType().Name).ToList();
            Check("W3", "Hay al menos un ITrialPresenter en la escena",
                  presenters.Count > 0, Join(presenters));

            // Without it S5 silently falls back to the cut-off behaviour (no
            // assembly, KANJI_EXPOSED.assembly = NOT_IMPLEMENTED).
            bool ensamblaje = root.GetComponent<KanjiAssemblyController>() != null;
            Check("W4", "El ensamblaje guiado esta en SessionRoot (S5 no lo salta)",
                  ensamblaje, ensamblaje ? root.name : "falta KanjiAssemblyController");
        }

        // ==================================================================
        // ESL visible band (Phase 3, F3.1)
        // ==================================================================

        // Fixed eye of the rig: the camera is anchored at 1.60 m at the origin (D-F6-25,
        // provisional; 1.36 m until 22 Oct).
        private static readonly Vector3 Eye = new Vector3(0f, 1.60f, 0f);

        // Measured in the headset on 28 September (Diseno_Sala_ESL.md 8): the
        // visible field is +-42 deg, +-40 deg while fixating the board. The board
        // spans +-21.8 deg. What is outside the band does not stimulate: the
        // participant cannot see it without turning the head.
        private const float BandInnerDeg = 22f;
        private const float BandOuterDeg = 40f;

        // A prop may sit behind the answer cards (they cover it) but never in
        // front of them. Margin around the card row, in degrees.
        private const float CardMarginDeg = 1f;
        private const float CardPlaneDepth = 0.08f;

        private const int MoverSamples = 24;

        private struct AngularBox
        {
            public float H0, H1, V0, V1, ZMin;
        }

        private static AngularBox AngularOf(IEnumerable<Vector3> worldPoints)
        {
            var box = new AngularBox { H0 = 999f, H1 = -999f, V0 = 999f, V1 = -999f, ZMin = 999f };
            foreach (var w in worldPoints)
            {
                var d = w - Eye;
                float h = Mathf.Atan2(d.x, d.z) * Mathf.Rad2Deg;
                float v = Mathf.Atan2(d.y, new Vector2(d.x, d.z).magnitude) * Mathf.Rad2Deg;
                box.H0 = Mathf.Min(box.H0, h); box.H1 = Mathf.Max(box.H1, h);
                box.V0 = Mathf.Min(box.V0, v); box.V1 = Mathf.Max(box.V1, v);
                box.ZMin = Mathf.Min(box.ZMin, w.z);
            }
            return box;
        }

        /// <summary>Oriented box of a mesh in world space, from the transform as it is now.</summary>
        private static IEnumerable<Vector3> MeshCorners(MeshFilter mf)
        {
            var b = mf.sharedMesh.bounds;
            var m = mf.transform.localToWorldMatrix;
            for (int i = 0; i < 8; i++)
                yield return m.MultiplyPoint3x4(new Vector3(
                    (i & 1) == 0 ? b.min.x : b.max.x,
                    (i & 2) == 0 ? b.min.y : b.max.y,
                    (i & 4) == 0 ? b.min.z : b.max.z));
        }

        /// <summary>
        /// E13. The ESL layout stays where it was decided, and nothing covers the
        /// answer cards.
        ///
        /// History. Until M2 the layer was laid out for 25-50 deg from the
        /// datasheet FOV and two props covered the outer cards; F3.1 (28 Sep)
        /// moved everything into the visible band 22-40 deg and this case
        /// enforced that band. On 1 Oct Sebas moved props by hand -- the wall
        /// clock to the centre above the board, the wastebasket and the chair
        /// outwards -- and decided that layout is the new one. The band is no
        /// longer a rule for every object, so the case now guards the LAYOUT OF
        /// RECORD: each object's angular extent from the eye, measured per mesh
        /// and, for movers, over their whole path, must match the table below
        /// within LayoutToleranceDeg. Moving an object on purpose means updating
        /// its row here (and Diseno_Sala_ESL.md); moving one by accident fails.
        /// On 5 Oct MIRAI asked for one more tier-2 prop so that MEDIUM (4-6 of
        /// the tier-2 pool) stops showing the same six props for every seed:
        /// DeskItems_T2, books, paper, mug and pen cup on the side table.
        /// Objects outside 22-40 deg are listed in the detail, as information.
        /// </summary>
        private static readonly Dictionary<string, (float h0, float h1, float v0, float v1)> LayoutOfRecord = new()
        {
            // Room v148 with the eye at 1.60 m (D-F6-25), measured in Unity on 23 Oct 2026 from the eye
            // (0, 1.60, 0), the meshes of the approved re-export (D-F6-33); degrees, + right / + up.
            // Differences > 1 deg from Diseno_Sala_ESL.md §10.3 are explained in the day draft: the clock
            // at 2.50 m (decision 9), the silhouettes on their current path, the bird mesh smaller than its box.
            { "FloorLamp_T1",               (-35.3f, -24.9f,  11.5f, 34.2f) },
            { "Plant_T1",                   (-37.6f, -28.0f, -25.5f, -11.3f) },
            { "Wastebasket_T2",             ( 26.4f,  31.3f, -22.2f, -16.4f) },
            { "Bookshelf_T3",               (-52.3f, -40.9f, -20.5f, -4.4f) },   // out of view, accepted (decision 8)
            { "WallPicture_T2",             (-35.8f, -29.3f,   4.8f, 10.2f) },
            { "SideTable_T1",               ( 30.2f,  43.1f, -21.5f, -14.1f) },
            { "WallShelf_T2",               ( 29.3f,  37.0f,   4.8f, 10.6f) },
            { "Chair_T3",                   ( 36.3f,  45.6f, -22.3f, -13.8f) },
            { "StackedBoxes_T3",            (-44.2f, -26.1f, -23.3f, -8.7f) },   // now on the left (v148)
            { "WallClock_T3",               ( -2.1f,   3.1f,  10.5f, 15.6f) },
            { "DeskItems_T2",               ( 30.8f,  41.8f, -16.6f, -14.0f) },
            { "CurtainLeft_T2",             (-41.0f, -29.1f, -14.0f,  4.7f) },
            { "OutsideFigureLeft_T3",       (-39.5f, -24.7f, -11.1f, -1.4f) },
            { "CurtainRight_T2",            ( 29.1f,  41.0f, -14.0f,  4.7f) },
            { "OutsideFigureRight_T3",      ( 24.7f,  39.5f, -11.1f, -1.4f) },
            // Peripheral animals (Diseno_Sala_ESL.md §10.2) over their whole path, with their Blender
            // meshes; the cat over its baked clip. The birds keep the spheres' ids.
            { "PeripheralEvent_WindowLeft",           (-34.0f, -26.4f, -11.0f, -2.8f) },
            { "PeripheralEvent_WindowRight",          ( 26.4f,  34.0f, -11.0f, -2.8f) },
            { "PeripheralEvent_Shelf",                ( 34.1f,  45.7f,   8.3f, 12.3f) },
            { "PeripheralEvent_CatWindowLeft",        (-35.1f, -26.3f, -11.5f, -6.4f) },
            { "PeripheralEvent_CatWindowRight",       ( 26.3f,  35.1f, -11.5f, -6.4f) },
            { "PeripheralEvent_ButterflyWindowLeft",  (-32.6f, -25.4f,  -3.4f,  0.2f) },
            { "PeripheralEvent_ButterflyWindowRight", ( 25.4f,  32.6f,  -3.4f,  0.2f) },
        };

        private const float LayoutToleranceDeg = 0.5f;

        private static void VisibleBandCase(Transform root)
        {
            var cards = UnityEngine.Object
                .FindObjectsByType<Canvas>(FindObjectsInactive.Include)
                .FirstOrDefault(c => c.name == "ResponseCanvas");
            if (cards == null)
            {
                Check("E13", "El layout del ESL es el de registro y nada tapa las tarjetas", false, "no hay ResponseCanvas");
                return;
            }
            var corners = new Vector3[4];
            ((RectTransform)cards.transform).GetWorldCorners(corners);
            var cardBox = AngularOf(corners);
            float cardPlane = corners.Max(c => c.z) + CardPlaneDepth;

            var problems = new List<string>();
            var outsideBand = new List<string>();
            var seen = new HashSet<string>();

            // Union of the angular boxes of every mesh of an object (and, for a
            // mover, of every sampled pose); flags the card overlap per pose.
            var baked = new Mesh();
            AngularBox Measure(Transform obj, out bool overCards)
            {
                var box = new AngularBox { H0 = 999f, H1 = -999f, V0 = 999f, V1 = -999f, ZMin = 999f };
                bool covers = false;
                void Add()
                {
                    // The cat's skinned mesh is baked at the sampled pose: its renderer only updates once a frame.
                    var shapes = obj.GetComponentsInChildren<MeshFilter>(true).Where(mf => mf.sharedMesh != null).Select(MeshCorners)
                        .Concat(obj.GetComponentsInChildren<SkinnedMeshRenderer>(true).Select(sk =>
                        {
                            sk.BakeMesh(baked, true);
                            return baked.vertices.Select(v => sk.transform.TransformPoint(v)).ToArray().AsEnumerable();
                        }));
                    foreach (var shape in shapes)
                    {
                        var a = AngularOf(shape);
                        box.H0 = Mathf.Min(box.H0, a.H0); box.H1 = Mathf.Max(box.H1, a.H1);
                        box.V0 = Mathf.Min(box.V0, a.V0); box.V1 = Mathf.Max(box.V1, a.V1);
                        box.ZMin = Mathf.Min(box.ZMin, a.ZMin);
                        covers |= a.ZMin < cardPlane
                            && a.H1 > cardBox.H0 - CardMarginDeg && a.H0 < cardBox.H1 + CardMarginDeg
                            && a.V1 > cardBox.V0 - CardMarginDeg && a.V0 < cardBox.V1 + CardMarginDeg;
                    }
                }

                var motion = obj.GetComponent<EnvironmentMotion>();
                var animal = obj.GetComponent<PeripheralAnimation>();
                if (animal != null)
                {
                    // A peripheral animal, over its whole path (Diseno_Sala_ESL.md §10.2–§10.3).
                    try
                    {
                        for (int i = 0; i <= MoverSamples; i++) { animal.Pose(animal.DurationSeconds * i / MoverSamples); Add(); }
                    }
                    finally { animal.Pose(0f); }
                }
                else if (motion == null) Add();
                else
                {
                    var restPos = obj.localPosition;
                    var restRot = obj.localRotation;
                    try
                    {
                        for (int i = 0; i <= MoverSamples; i++)
                        {
                            motion.PoseAt(restPos, restRot, (float)i / MoverSamples, out var p, out var r);
                            obj.localPosition = p;
                            obj.localRotation = r;
                            Add();
                        }
                    }
                    finally
                    {
                        obj.localPosition = restPos;
                        obj.localRotation = restRot;
                    }
                }
                overCards = covers;
                return box;
            }

            foreach (var group in new[] { "Props", "Movers", "PeripheralEvents" })
            {
                var g = root.Find(group);
                if (g == null) continue;
                foreach (Transform obj in g)
                {
                    seen.Add(obj.name);
                    var a = Measure(obj, out bool overCards);
                    if (overCards) problems.Add($"{obj.name} covers the cards");

                    if (!LayoutOfRecord.TryGetValue(obj.name, out var rec))
                        problems.Add($"{obj.name} is not in the layout of record (h [{a.H0:F1},{a.H1:F1}] v [{a.V0:F1},{a.V1:F1}])");
                    else if (Mathf.Abs(a.H0 - rec.h0) > LayoutToleranceDeg || Mathf.Abs(a.H1 - rec.h1) > LayoutToleranceDeg ||
                             Mathf.Abs(a.V0 - rec.v0) > LayoutToleranceDeg || Mathf.Abs(a.V1 - rec.v1) > LayoutToleranceDeg)
                        problems.Add($"{obj.name} moved: h [{a.H0:F1},{a.H1:F1}] v [{a.V0:F1},{a.V1:F1}], " +
                                     $"record h [{rec.h0:F1},{rec.h1:F1}] v [{rec.v0:F1},{rec.v1:F1}]");

                    bool crosses = a.H0 < 0f && a.H1 > 0f;
                    float inner = crosses ? 0f : Mathf.Min(Mathf.Abs(a.H0), Mathf.Abs(a.H1));
                    float outer = Mathf.Max(Mathf.Abs(a.H0), Mathf.Abs(a.H1));
                    if (inner < BandInnerDeg || outer > BandOuterDeg)
                        outsideBand.Add($"{obj.name} {inner:F1}-{outer:F1}");
                }
            }
            foreach (var name in LayoutOfRecord.Keys)
                if (!seen.Contains(name)) problems.Add($"{name} missing from the scene");

            Check("E13", "El layout del ESL es el de registro (sala v148, 23 oct) y nada tapa las tarjetas",
                  seen.Count > 0 && problems.Count == 0,
                  problems.Count == 0
                      ? $"{seen.Count} objetos en su sitio · fuera de 22-40 (informativo): " +
                        (outsideBand.Count == 0 ? "ninguno" : Join(outsideBand))
                      : Join(problems.Distinct()));
            UnityEngine.Object.DestroyImmediate(baked);
        }

        // ==================================================================
        // No controller vibration (UI design v1.3, rule 7)
        // ==================================================================

        /// <summary>
        /// X1. Vibration is a somatosensory and mechanical stimulus the EEG does not
        /// need, so no controller vibrates in any game state: every
        /// SimpleHapticFeedback in the scene is disabled (inactive ones included, so
        /// re-enabling an interactor cannot bring it back), and no script under
        /// Assets/Scripts calls SendHapticImpulse. Matched by type name so the
        /// editor assembly does not need a reference to XRI.
        /// </summary>
        private static void HapticCases()
        {
            var enabledHaptics = new List<string>();
            int total = 0;
            foreach (var b in UnityEngine.Object.FindObjectsByType<Behaviour>(FindObjectsInactive.Include))
            {
                if (b == null || b.GetType().Name != "SimpleHapticFeedback") continue;
                total++;
                if (b.enabled) enabledHaptics.Add(AnimationUtility.CalculateTransformPath(b.transform, null));
            }

            var callers = new List<string>();
            foreach (var f in System.IO.Directory.GetFiles("Assets/Scripts", "*.cs", System.IO.SearchOption.AllDirectories))
                if (System.IO.File.ReadAllText(f).Contains("SendHapticImpulse"))
                    callers.Add(System.IO.Path.GetFileName(f));

            Check("X1", "Ningun mando vibra: todo SimpleHapticFeedback deshabilitado y ningun script llama a SendHapticImpulse",
                  enabledHaptics.Count == 0 && callers.Count == 0,
                  enabledHaptics.Count == 0 && callers.Count == 0
                      ? $"{total} SimpleHapticFeedback, todos deshabilitados · 0 llamadas"
                      : Join(enabledHaptics.Select(x => "habilitado: " + x).Concat(callers.Select(x => "llama: " + x))));
        }

        // ==================================================================
        // Stimulus telemetry for the EEG (UI design v1.3, section 8)
        // ==================================================================

        /// <summary>
        /// X2. TRIAL_COMPLETED carries the seven stimulus fields, and the rules
        /// hold: without feedback there is no reading, no result sound and no
        /// animation; a result sound always carries its offset.
        /// X3. For every reading clip in the contract, the result sound is due
        /// at L + 150 ms and ends inside feedbackSeconds (design D4 asks for the
        /// list of kanji that would not fit, instead of stretching anything).
        /// The measured offset is checked at run time by ResponseSystemController,
        /// which warns when it lands more than one frame from the plan.
        /// </summary>
        private static void StimulusTelemetryCases(KanjiContentController content)
        {
            var problems = new List<string>();

            var shown = StimulusTelemetry.TrialCompletedFields(true, true, "TTS_PLACEHOLDER", 450, true, 600, 470);
            foreach (var k in StimulusTelemetry.TrialCompletedKeys)
                if (!shown.ContainsKey(k)) problems.Add("falta " + k);
            if ((string)shown[StimulusTelemetry.KeyResultSound] != StimulusTelemetry.ResultCorrect) problems.Add("acierto sin CORRECT");
            if ((string)shown[StimulusTelemetry.KeyCardAnimation] != StimulusTelemetry.CorrectPop) problems.Add("acierto sin CORRECT_POP");

            var wrong = StimulusTelemetry.TrialCompletedFields(true, false, "TTS_PLACEHOLDER", 450, true, 600, 380);
            if ((string)wrong[StimulusTelemetry.KeyResultSound] != StimulusTelemetry.ResultIncorrect) problems.Add("error sin INCORRECT");
            if ((string)wrong[StimulusTelemetry.KeyCardAnimation] != StimulusTelemetry.None) problems.Add("error con animacion");

            var hidden = StimulusTelemetry.TrialCompletedFields(false, true, "TTS_PLACEHOLDER", 450, true, 600, 470);
            foreach (var k in StimulusTelemetry.TrialCompletedKeys)
                if (!hidden.ContainsKey(k)) problems.Add("sin feedback falta " + k);
            if ((string)hidden[StimulusTelemetry.KeyResultSound] != StimulusTelemetry.None
                || (string)hidden[StimulusTelemetry.KeyCardAnimation] != StimulusTelemetry.None
                || hidden[StimulusTelemetry.KeyResultSoundOffsetMs] != null
                || (int)hidden[StimulusTelemetry.KeyFeedbackAudioMs] != 0)
                problems.Add("sin feedback deja sonido, animacion o lectura");

            var silent = StimulusTelemetry.TrialCompletedFields(true, true, "NONE", 0, false, 0, 0);
            if (silent[StimulusTelemetry.KeyResultSoundOffsetMs] != null) problems.Add("offset sin sonido");

            Check("X2", "TRIAL_COMPLETED lleva los 7 campos de estimulos y sus reglas (sin feedback: NONE)",
                  problems.Count == 0, problems.Count == 0 ? "ok" : Join(problems));

            // X3: every reading clip leaves room for the result sound.
            float feedbackSeconds = 1.5f;
            var rs = content.GetComponent<ResponseSystemController>();
            if (rs != null)
            {
                var p = new SerializedObject(rs).FindProperty("feedbackSeconds");
                if (p != null) feedbackSeconds = p.floatValue;
            }
            int windowMs = Mathf.RoundToInt(feedbackSeconds * 1000f);
            int longest = Math.Max(ProceduralSfx.CorrectMs, ProceduralSfx.IncorrectMs);
            var late = new List<string>();
            int maxL = 0, clips = 0;
            foreach (var item in content.All)
            {
                var clip = item.TargetReadingAudio;
                if (clip == null) continue;
                clips++;
                int l = Mathf.RoundToInt(clip.length * 1000f);
                maxL = Math.Max(maxL, l);
                if (StimulusTelemetry.PlannedResultOffsetMs(l) + longest > windowMs)
                    late.Add($"{item.Character} L={l}");
            }
            Check("X3", $"Toda lectura + 150 ms + sonido de resultado cabe en feedbackSeconds ({windowMs} ms)",
                  late.Count == 0,
                  late.Count == 0
                      ? $"{clips} clips · L max {maxL} ms · peor caso {StimulusTelemetry.PlannedResultOffsetMs(maxL) + longest} ms"
                      : "no caben: " + Join(late));
        }

        // ==================================================================
        // Head away and idle time (Phase 3, F3.3; EVENT_CONTRACT.md 5.10)
        // ==================================================================

        /// <summary>
        /// X4. The head-away state machine, driven frame by frame at 72 Hz with the
        /// default thresholds: a glance shorter than min_away_ms emits nothing; a
        /// real look-away emits HEAD_AWAY dated back to the first frame outside;
        /// the return waits min_return_ms with hysteresis; losing tracking closes
        /// the episode; episodes are numbered. Since F5a (D7) it also replays the
        /// head angles measured in the headset on 6 Oct (two HeadAngleProbe passes):
        /// every task fixation stays inside, every head-turned look at the room
        /// leaves, and a quick 0.45 s glance at the window counts.
        /// X5. Idle time: still runs shorter than idle_min_ms do not count, longer
        /// ones do, and any movement breaks a run.
        /// </summary>
        private static void HeadBehaviorCases()
        {
            var p = new List<string>();
            var th = HeadAwayThresholds.Default;
            var d = new HeadAwayDetector(th);
            const double dt = 1.0 / 72.0;
            double t = 0;
            var events = new List<HeadAwayDetector.Result>();
            void Run(double seconds, float yaw, float pitch)
            {
                int n = (int)Math.Round(seconds / dt);
                for (int i = 0; i < n; i++) { t += dt; var r = d.Step(t, yaw, pitch); if (r != null) events.Add(r.Value); }
            }

            Run(1.0, 0f, 0f);                 // looking at the board
            Run(0.2, -30f, 0f);               // glance at the window: 200 ms < min_away_ms
            Run(0.5, 0f, 0f);
            if (events.Count != 0) p.Add($"una mirada de 200 ms emitio {events.Count}");

            Run(1.0, -29.7f, 5.5f);           // left window, head turned (measured 6 Oct): 1 s
            var away = events.Find(e => e.Kind == HeadAwayDetector.Kind.Away);
            if (events.Count != 1 || away.Episode != 1 || away.Limit != "YAW") p.Add("no hubo HEAD_AWAY #1 por YAW");
            else if (Math.Abs(away.OnsetOffsetMs + th.MinAwayMs) > 20) p.Add($"onset {away.OnsetOffsetMs} ms, se esperaba ~-{th.MinAwayMs}");

            Run(0.3, th.YawLimitDeg - th.HysteresisDeg / 2f, 0f);   // inside the limit, inside the hysteresis band: not back
            if (events.Count != 1) p.Add("volvio dentro de la histeresis");
            Run(0.1, 20.5f, -5.5f);           // back on card 4, but for less than min_return_ms
            Run(0.2, -29.7f, 5.5f);           // out again: still the same episode
            Run(0.6, 0f, 0f);                 // back for good
            var ret = events.Find(e => e.Kind == HeadAwayDetector.Kind.Returned);
            if (events.Count != 2 || ret.Episode != 1 || ret.Reason != "RETURNED") p.Add("no hubo HEAD_RETURNED #1");
            else if (Math.Abs(ret.DurationMs - 1600) > 30) p.Add($"duracion {ret.DurationMs} ms, se esperaba ~1600");
            else if (Math.Abs(ret.MaxAbsYawDeg - 29.7f) > 0.01f) p.Add("max yaw mal");

            Run(1.0, -2.6f, -54.7f);          // the floor (measured): episode 2
            var closed = d.ForceClose(t, "TRACKING_LOST");
            if (!(events.Count == 3 && events[2].Episode == 2 && events[2].Limit == "PITCH_DOWN")) p.Add("no hubo HEAD_AWAY #2 por PITCH_DOWN");
            if (closed == null || closed.Value.Reason != "TRACKING_LOST" || closed.Value.Episode != 2) p.Add("perder tracking no cerro el episodio");
            if (d.ForceClose(t, "SESSION_END") != null) p.Add("cerro dos veces");
            Run(0.6, 0f, 0f);

            // Task fixations measured with the head turned (6 Oct, both passes) plus the
            // extremes of natural reading and of scanning the cards: never away.
            var task = new (string name, float yaw, float pitch)[]
            {
                ("board", -2.3f, 6.6f), ("tarjeta 1", -16.6f, -5.5f), ("tarjeta 4", 20.6f, -8.2f),
                ("Hint", 18.5f, -1.1f), ("Hint", 15.9f, 1.6f), ("leer el board", 3.4f, 1.3f),
                ("recorrer tarjetas", -15.5f, -10.8f), ("recorrer tarjetas", 12.6f, 0.7f),
                ("tarjeta 4 fija", 20.9f, -18.5f),   // check session, S7-013: fired with pitch down 15
            };
            foreach (var x in task)
            {
                int before = events.Count;
                Run(1.0, x.yaw, x.pitch);
                if (events.Count != before) p.Add($"mirar {x.name} ({x.yaw}, {x.pitch}) conto como apartar la vista");
            }
            Run(0.6, 0f, 0f);

            // Room targets of the v148 room (D-F6-25): their centres from the eye at 1.60 m, relative to
            // the board direction, measured in Unity on 23 Oct (D-F6-33; Medicion_D7_HeadAway.md §8).
            // Each one leaves, by its limit. The task above did not move: it went up 0.24 m with the eye.
            var room = new (string name, float yaw, float pitch, string limit)[]
            {
                ("repisa", 33.2f, 5.1f, "YAW"), ("planta", -32.6f, -21.0f, "YAW"),
                ("ventana derecha", 27.1f, -7.3f, "YAW"), ("silla", 41.1f, -20.4f, "YAW"),
                ("cajas", -35.4f, -17.7f, "YAW"), ("techo", 0.0f, 45.1f, "PITCH_UP"),
                ("tatami delante", 0.0f, -55.7f, "PITCH_DOWN"),
            };
            // The v148 clock sits inside the task region (7.9-12.9 deg up, centre 10.5): looking at it is not
            // HEAD_AWAY with the frozen thresholds. Listed so the harness says so, not as a rule (duda 7 para PM).
            var insideNow = new (string name, float yaw, float pitch)[] { ("reloj", 0.5f, 10.5f) };
            foreach (var x in insideNow)
            {
                int before = events.Count;
                Run(1.0, x.yaw, x.pitch);
                if (events.Count != before) p.Add($"{x.name} ({x.yaw}, {x.pitch}) ya sale de la region: actualizar Medicion_D7 §8");
            }
            Run(0.6, 0f, 0f);
            int roomOk = 0;
            foreach (var x in room)
            {
                int before = events.Count;
                Run(1.0, x.yaw, x.pitch);
                Run(0.6, 0f, 0f);
                bool ok = events.Count == before + 2 && events[before].Kind == HeadAwayDetector.Kind.Away
                          && events[before].Limit == x.limit && events[before + 1].Kind == HeadAwayDetector.Kind.Returned;
                if (ok) roomOk++; else p.Add($"mirar {x.name} ({x.yaw}, {x.pitch}) no fue HEAD_AWAY por {x.limit}");
            }

            int beforeGlance = events.Count;
            Run(0.45, -26.8f, 0f);            // the shortest quick glance at the window that was measured
            Run(0.6, 0f, 0f);
            if (events.Count != beforeGlance + 2) p.Add("una mirada rapida de 450 ms a la ventana no conto");

            Check("X4", "HEAD_AWAY/RETURNED: umbral, permanencia, histeresis, onset, cierre por tracking, numeracion; tarea medida en visor (D7), sala v148 en Unity (D-F6-33)",
                  p.Count == 0, p.Count == 0 ? $"{events.Count} eventos · retorno #1 en {ret.DurationMs} ms · onset {away.OnsetOffsetMs} ms · tarea {task.Length}/{task.Length} dentro · sala {roomOk}/{room.Length} fuera · dentro de la region: {string.Join(", ", insideNow.Select(x => x.name))} (duda 7)" : Join(p));

            var q = new List<string>();
            var idle = new IdleTracker(IdleTracker.Thresholds.Default);
            void Idle(double seconds, float head, float ray)
            {
                int n = (int)Math.Round(seconds / dt);
                for (int i = 0; i < n; i++) idle.Step((float)dt, head, ray);
            }
            Idle(0.8, 1f, 1f);               // 800 ms still: does not count
            Idle(0.1, 20f, 1f);              // head moves
            Idle(1.5, 1f, 2f);               // 1.5 s still: counts
            Idle(0.1, 1f, 30f);              // ray moves
            Idle(2.0, 0f, 0f);               // 2 s still, closed by Finish
            idle.Finish();
            if (idle.Episodes != 2) q.Add($"{idle.Episodes} episodios, se esperaban 2");
            if (Math.Abs(idle.IdleMs - 3500) > 30) q.Add($"idle {idle.IdleMs} ms, se esperaba ~3500");
            if (Math.Abs(idle.LongestMs - 2000) > 30) q.Add($"el mas largo {idle.LongestMs} ms");
            var f = idle.Fields();
            foreach (var k in new[] { "idle_ms", "idle_episodes", "idle_longest_ms", "idle_min_ms", "idle_head_deg_s", "idle_ray_deg_s" })
                if (!f.ContainsKey(k)) q.Add("falta " + k);
            Check("X5", "Idle time: tramos quietos cortos no cuentan, los largos si, cualquier movimiento corta",
                  q.Count == 0, q.Count == 0 ? $"{idle.IdleMs} ms en {idle.Episodes} tramos (mas largo {idle.LongestMs})" : Join(q));
        }

        // ==================================================================
        // Sound set (UI design v1.3, section 4 and P4)
        // ==================================================================

        /// <summary>
        /// X6. The six clips of the set exist with the lengths of design section 4,
        /// none peaks above its level, the stage chord shares no pitch with the S4
        /// eyes-closed chime (within 3 %), and the assembly finds the shared set
        /// in the scene instead of making its own sounds.
        /// </summary>
        private static void SoundSetCases()
        {
            var q = new List<string>();
            var clips = ProceduralSfx.Synthesize();
            var want = new Dictionary<ProceduralSfx.Clip, (int ms, float db)>
            {
                { ProceduralSfx.Clip.Select, (ProceduralSfx.SelectMs, -22f) },
                { ProceduralSfx.Clip.Correct, (ProceduralSfx.CorrectMs, -16f) },
                { ProceduralSfx.Clip.Incorrect, (ProceduralSfx.IncorrectMs, -20f) },
                { ProceduralSfx.Clip.Stage, (ProceduralSfx.StageMs, -16f) },
                { ProceduralSfx.Clip.Place, (ProceduralSfx.PlaceMs, -20f) },
                { ProceduralSfx.Clip.Done, (ProceduralSfx.DoneMs, -16f) },
            };
            var peaks = new List<string>();
            foreach (var kv in want)
            {
                if (!clips.TryGetValue(kv.Key, out var c) || c == null) { q.Add("falta " + kv.Key); continue; }
                int ms = Mathf.RoundToInt(c.length * 1000f);
                if (Math.Abs(ms - kv.Value.ms) > 1) q.Add($"{kv.Key} dura {ms} ms, se esperaban {kv.Value.ms}");
                var data = new float[c.samples];
                c.GetData(data, 0);
                float peak = data.Max(Math.Abs);
                float limit = Mathf.Pow(10f, kv.Value.db / 20f) * 1.01f;
                if (peak > limit) q.Add($"{kv.Key} pico {20f * Mathf.Log10(peak):0.0} dB, nivel {kv.Value.db} dB");
                peaks.Add($"{kv.Key} {20f * Mathf.Log10(Mathf.Max(peak, 1e-6f)):0.0} dB");
                UnityEngine.Object.DestroyImmediate(c);
            }
            foreach (var hz in ProceduralSfx.StageHz)
                if (Math.Abs(hz - SessionFlowRunner.ChimeHz) / SessionFlowRunner.ChimeHz < 0.03f)
                    q.Add($"stage usa {hz} Hz, igual que el chime de S4");

            var assembly = UnityEngine.Object.FindObjectsByType<KanjiAssemblyController>(FindObjectsInactive.Include);
            var sets = UnityEngine.Object.FindObjectsByType<ProceduralSfx>(FindObjectsInactive.Include);
            if (assembly.Length > 0 && sets.Length == 0) q.Add("hay ensamblaje y ningun ProceduralSfx en la escena");

            Check("X6", "Set de sonidos: 6 clips con su duracion y nivel; stage no comparte tono con el chime de S4",
                  q.Count == 0, q.Count == 0 ? Join(peaks) : Join(q));
        }

        /// <summary>
        /// B1-B2. The S4 eye closes once and stays closed (an eye that reopens or
        /// loops would put motion on the board for the whole closed segment), and
        /// the drawing shows an iris when open and only the lid line when closed.
        /// </summary>
        private static void BaselineEyeCases()
        {
            const float hold = 0.5f, close = 1f;
            var q = new List<string>();
            if (StudioTrialPresenter.EyeOpenness(0f, hold, close) != 1f) q.Add("no empieza abierto");
            if (StudioTrialPresenter.EyeOpenness(hold, hold, close) != 1f) q.Add("cierra antes de la pausa");
            float prev = 1f;
            for (float t = 0f; t <= 45f; t += 0.05f)
            {
                float o = StudioTrialPresenter.EyeOpenness(t, hold, close);
                if (o > prev) { q.Add($"se reabre en t={t:0.00}"); break; }
                prev = o;
            }
            if (StudioTrialPresenter.EyeOpenness(hold + close, hold, close) != 0f) q.Add("no termina cerrado");
            if (StudioTrialPresenter.EyeOpenness(45f, hold, close) != 0f) q.Add("no sigue cerrado a los 45 s");
            Check("B1", "El ojo de S4 empieza abierto, cierra una vez y se queda cerrado", q.Count == 0, Join(q));

            q.Clear();
            const int w = 256, h = 128;
            var px = new Color32[w * h];
            byte At(float x, float y) => px[(int)(y * (h - 1)) * w + (int)(x * (w - 1))].a;
            // Middle of the lash at X=+0.2 half-widths, under the closed lid (256x128 texture).
            bool Lash() { for (int y = 12; y <= 17; y++) for (int x = 150; x <= 155; x++) if (px[y * w + x].a > 200) return true; return false; }
            StudioTrialPresenter.PaintEye(px, w, h, 1f);
            if (At(0.5f, 0.5f) < 200) q.Add("abierto: el centro (iris) no se ve");
            if (At(0.02f, 0.95f) > 0) q.Add("abierto: la esquina no es transparente");
            if (Lash()) q.Add("abierto: ya tiene pestanas");
            StudioTrialPresenter.PaintEye(px, w, h, 0f);
            if (At(0.5f, 0.5f) > 0) q.Add("cerrado: el iris sigue visible");
            bool lid = false;
            for (int y = 0; y < h / 2; y++) lid |= px[y * w + w / 2].a > 200;
            if (!lid) q.Add("cerrado: no hay linea del parpado bajo el centro");
            if (!Lash()) q.Add("cerrado: no hay pestanas");
            Check("B2", "El dibujo del ojo: iris visible abierto; cerrado, el parpado con pestanas", q.Count == 0, Join(q));
        }

        // ==================================================================

        // ==================================================================
        // DISTRACTOR_INTERACTION (F5a, D5; EVENT_CONTRACT.md 5.11)
        // ==================================================================

        /// <summary>
        /// X7. DWELL and ORIENTING, driven at 72 Hz with the head angles measured
        /// on 6 Oct and the boxes of the registry layout seen from the eye. DWELL:
        /// a look at the clock counts, a short one does not, a break shorter than
        /// dwell_break_ms does not split it, the task region and the floor never
        /// count, an inactive prop does not count, a low object counts with the
        /// head 5 deg above its box (pitch margin), tracking loss closes it.
        /// ORIENTING: a turn toward the peripheral within the window counts, a
        /// small turn or a late one does not.
        /// </summary>
        private static void DistractorCases()
        {
            var p = new List<string>();
            var th = DistractorThresholds.Default;
            var task = HeadAwayThresholds.Default;
            bool Outside(float y, float pt) => Math.Abs(y) > task.YawLimitDeg || pt > task.PitchUpLimitDeg || pt < -task.PitchDownLimitDeg;
            Data.AngularBox Box(string n, string g, float y0, float y1, float p0, float p1)
                => new Data.AngularBox { Name = n, Group = g, YawMin = y0, YawMax = y1, PitchMin = p0, PitchMax = p1 };
            var clock = Box("WallClock_T3", "PROP", -2.9f, 2.9f, 13.1f, 18.5f);
            var lamp = Box("FloorLamp_T1", "PROP", -29.2f, -22.2f, -27.2f, 3.2f);
            var plant = Box("Plant_T1", "PROP", -38.3f, -23.2f, -34.6f, -9.3f);
            var high = new List<Data.AngularBox> { clock, lamp, plant };
            var noPlant = new List<Data.AngularBox> { clock };
            var withPlant = new List<Data.AngularBox> { clock, plant };   // without the lamp, whose box the plant look also falls in

            var d = new DwellDetector(th);
            const double dt = 1.0 / 72.0;
            double t = 0;
            var dwells = new List<DwellDetector.Result>();
            void Run(double seconds, float yaw, float pitch, List<Data.AngularBox> boxes)
            {
                int n = (int)Math.Round(seconds / dt);
                for (int i = 0; i < n; i++) { t += dt; var r = d.Step(t, yaw, pitch, Outside(yaw, pitch), boxes); if (r != null) dwells.Add(r.Value); }
            }

            Run(1.0, 0f, 0f, high);                       // the board
            Run(1.5, -2.5f, 20.3f, high);                 // the clock, head-turned (measured)
            Run(0.4, 0f, 0f, high);
            if (dwells.Count != 1 || dwells[0].ObjectName != "WallClock_T3" || Math.Abs(dwells[0].DurationMs - 1500) > 30)
                p.Add($"mirar el reloj 1.5 s dio {dwells.Count} DWELL" + (dwells.Count > 0 ? $" ({dwells[0].ObjectName}, {dwells[0].DurationMs} ms)" : ""));

            Run(0.8, -2.5f, 20.3f, high);                 // too short
            Run(0.4, 0f, 0f, high);
            if (dwells.Count != 1) p.Add("una mirada de 800 ms al reloj conto");

            Run(0.7, -2.5f, 20.3f, high);                 // 0.7 + break 0.1 + 0.6: one dwell
            Run(0.1, 0f, 0f, high);
            Run(0.6, -2.5f, 20.3f, high);
            Run(0.4, 0f, 0f, high);
            if (dwells.Count != 2 || Math.Abs(dwells[1].DurationMs - 1400) > 30)
                p.Add("un corte de 100 ms partio el DWELL o no lo cerro");

            Run(2.0, -23.1f, 2.5f, high);                 // the lamp from inside the task region (measured)
            Run(2.0, -2.6f, -54.7f, high);                // the floor: away, but not the room
            Run(0.4, 0f, 0f, high);
            if (dwells.Count != 2) p.Add("la region de tarea o el piso dieron DWELL");

            Run(1.5, -26.7f, -7.1f, noPlant);             // the plant while it is inactive
            Run(0.4, 0f, 0f, noPlant);
            if (dwells.Count != 2) p.Add("un prop inactivo dio DWELL");
            Run(1.5, -26.7f, -7.1f, withPlant);           // the plant while active (2.2 deg below its box)
            Run(0.4, 0f, 0f, withPlant);
            if (dwells.Count != 3 || dwells[2].ObjectName != "Plant_T1") p.Add("mirar la planta activa no dio DWELL");

            var sideTable = Box("SideTable_T1", "PROP", 25.4f, 39.0f, -27.7f, -13.0f);
            var withTable = new List<Data.AngularBox> { clock, sideTable };
            Run(1.5, 26.6f, -8.0f, withTable);            // the side table: head 5 deg above its box (measured)
            Run(0.4, 0f, 0f, withTable);
            if (dwells.Count != 4 || dwells[3].ObjectName != "SideTable_T1") p.Add("mirar la mesa lateral (5 grados sobre su caja) no dio DWELL");

            Run(1.2, -2.5f, 20.3f, high);                 // tracking lost in the middle of a dwell
            var forced = d.ForceClose();
            if (forced == null || forced.Value.ObjectName != "WallClock_T3") p.Add("perder tracking no cerro el DWELL");

            // ORIENTING: a peripheral at the right window (registry centre 31.4, 0.5).
            var o = new OrientingDetector(th);
            float Dist(float y, float pt) => (float)Math.Sqrt((y - 31.4f) * (y - 31.4f) + (pt - 0.5f) * (pt - 0.5f));
            var turns = new List<OrientingDetector.Result>();
            void Orient(double seconds, float yaw, float pitch)
            {
                int n = (int)Math.Round(seconds / dt);
                for (int i = 0; i < n; i++) { t += dt; var r = o.Step(t, Dist(yaw, pitch), true); if (r != null) turns.Add(r.Value); }
            }
            o.Begin(t, "PeripheralEvent_WindowRight", 1, Dist(0f, 0f));
            Orient(0.4, 0f, 0f);
            Orient(1.8, 20f, 1f);                         // turns 20 deg toward it
            if (turns.Count != 1 || turns[0].EventIndex != 1 || turns[0].TurnDeg < th.OrientingMinDeg)
                p.Add("girar 20 grados hacia el periferico no dio ORIENTING");
            else if (Math.Abs(turns[0].PeakMs - 400) > 30) p.Add($"pico a {turns[0].PeakMs} ms, se esperaba ~400");

            o.Begin(t, "PeripheralEvent_WindowRight", 2, Dist(0f, 0f));
            Orient(2.2, 5f, 0f);                          // 5 deg: not orienting
            o.Begin(t, "PeripheralEvent_WindowRight", 3, Dist(0f, 0f));
            Orient(2.1, 0f, 0f);
            Orient(1.0, 25f, 0f);                         // turns after the window
            if (turns.Count != 1) p.Add($"un giro de 5 grados o uno tardio dio ORIENTING ({turns.Count - 1})");

            Check("X7", "DISTRACTOR_INTERACTION: DWELL fuera de la region de tarea, corte, prop inactivo, tracking; ORIENTING en ventana",
                  p.Count == 0, p.Count == 0
                      ? $"{dwells.Count + 1} DWELL (reloj {dwells[0].DurationMs} ms, planta {dwells[2].BoxDistanceDeg:0.0} y mesa {dwells[3].BoxDistanceDeg:0.0} grados de su caja) · ORIENTING giro {turns[0].TurnDeg:0.0} grados, pico {turns[0].PeakMs} ms"
                      : Join(p));
        }

        // ==================================================================
        // D9 · proactive cues (Plan_Fase5a.md §4, approved by MIRAI 13 Oct)
        // ==================================================================
        private static void ProactiveCueCases()
        {
            var p = new List<string>();
            string Seq(Func<int> next, int n) => string.Join(",", Enumerable.Range(0, n).Select(_ => next()));

            var w = new ProactiveCueWindow();
            if (Seq(w.NextTrial, 2) != "0,0") p.Add("ventana cerrada dio cue");
            w.Open();
            if (Seq(w.NextTrial, 4) != "1,2,3,0") p.Add("la ventana no dura exactamente 3 trials");
            w.Open(); w.NextTrial(); w.Open();
            if (w.NextTrial() != 1) p.Add("una subida nueva no reabre la ventana en 1");

            var go = new GameObject("HarnessLAL_D9") { hideFlags = HideFlags.HideAndDontSave };
            try
            {
                var lal = go.AddComponent<LearningAssistanceController>();
                var M = StimulationOrAssistanceLevel.Medium;
                var H = StimulationOrAssistanceLevel.High;
                var L = StimulationOrAssistanceLevel.Low;
                Func<int> adaptive = () => lal.BeginTrialProactive(true);

                lal.SetLevel(M, true); lal.SetLevel(H, true, proactiveCues: true);
                string a = Seq(adaptive, 5);
                if (a != "1,2,3,0,0") p.Add($"subida con proactive_cues: {a}, se esperaba 1,2,3,0,0");

                lal.SetLevel(M, true); lal.SetLevel(H, true);
                if (adaptive() != 0) p.Add("subida sin proactive_cues abrio ventana");

                lal.SetLevel(M, true); lal.SetLevel(H, false, proactiveCues: true);   // blocked: LogError expected
                if (lal.CurrentLevel != M || adaptive() != 0) p.Add("un cambio bloqueado a media respuesta abrio ventana");

                lal.SetLevel(H, true, proactiveCues: true); adaptive(); lal.SetLevel(M, true);
                if (adaptive() != 0) p.Add("bajar LAL no cerro la ventana");

                lal.SetLevel(L, true); lal.SetLevel(M, true, proactiveCues: true);
                if (lal.BeginTrialProactive(false) != 0) p.Add("STATIC / fuera de S7 dio cue proactivo");
                if (adaptive() != 0) p.Add("salir del contexto adaptativo no cerro la ventana");

                lal.SetLevel(L, true); lal.SetLevel(M, true, proactiveCues: true); adaptive(); adaptive();
                lal.SetLevel(H, true, proactiveCues: true);
                string b = Seq(adaptive, 4);
                if (b != "1,2,3,0") p.Add($"segunda subida: {b}, se esperaba ventana nueva 1,2,3,0");
            }
            finally { UnityEngine.Object.DestroyImmediate(go); }

            if (CueTelemetry.TriggerOf(2, false) != CueTelemetry.Proactive
                || CueTelemetry.TriggerOf(1, true) != CueTelemetry.Proactive
                || CueTelemetry.TriggerOf(0, true) != CueTelemetry.OnRequest
                || CueTelemetry.TriggerOf(0, false) != null)
                p.Add("cue_trigger no sigue PROACTIVE > ON_REQUEST > null");

            Check("X8", "D9: cue proactivo solo en los 3 trials tras una subida de LAL con proactive_cues; nunca fuera de S7 adaptativo",
                  p.Count == 0, p.Count == 0 ? "ventana 1,2,3 · reabre con cada subida · se cierra al bajar o fuera de S7 adaptativo" : Join(p));
        }

        // ==================================================================
        // F5a loop: applying the backend's DECISION (Planteamiento_Tecnico_F5a.md §8.2)
        // ==================================================================
        private static void AdaptationLoopCases()
        {
            IncomingMessage Dec(string action, string dim, string to, string trial = "S7-009")
                => new IncomingMessage { Type = "DECISION", DecisionId = "d-test", TrialId = trial, Action = action,
                                         Dimension = dim, FromLevel = "MEDIUM", ToLevel = to, ProactiveCues = dim == "LAL" };
            var lalUp = Dec("CHANGE_ASSISTANCE", "LAL", "HIGH");
            var eslDown = Dec("CHANGE_ENVIRONMENT", "ESL", "LOW");
            AdaptationApply.Outcome R(bool allowed, bool inTrial, IncomingMessage d, bool next = true)
                => AdaptationApply.Resolve(allowed, inTrial, d, next, out _, out _);

            Check("AD1", "STATIC o fuera de S7 adaptativo: no se espera ni se aplica ninguna decision",
                  R(false, false, lalUp) == AdaptationApply.Outcome.NotApplicable
                  && R(false, false, null) == AdaptationApply.Outcome.NotApplicable,
                  $"con decision {R(false, false, lalUp)} · sin decision {R(false, false, null)}");

            Check("AD2", "Nunca durante un trial: con un trial abierto el cambio se salta como GUARD",
                  R(true, true, lalUp) == AdaptationApply.Outcome.SkipGuard
                  && AdaptationApply.ReasonOf(AdaptationApply.Outcome.SkipGuard) == "GUARD",
                  $"{R(true, true, lalUp)}");

            var p = new List<string>();
            if (R(true, false, null) != AdaptationApply.Outcome.SkipTimeout) p.Add("sin decision no dio TIMEOUT");
            var go = new GameObject("HarnessAdaptationClient") { hideFlags = HideFlags.HideAndDontSave };
            try
            {
                var client = go.AddComponent<AdaptationClient>();
                client.Accept(Dec("NO_CHANGE", null, null, "S7-004"));
                if (!client.TryTake("S7-004", out var got) || got.Action != "NO_CHANGE") p.Add("no guardo la decision por trial_id");
                if (client.TryTake("S7-004", out _)) p.Add("la misma decision se pudo tomar dos veces");
                client.MarkSkipped("S7-005");
                client.Accept(Dec("CHANGE_ASSISTANCE", "LAL", "HIGH", "S7-005"));
                if (client.TryTake("S7-005", out _) || client.LateDiscarded != 1) p.Add("una decision tardia no se descarto");
                client.Accept(new IncomingMessage { Type = "ACK", Id = "1" });
                if (client.TryTake(null, out _)) p.Add("un ACK se tomo como decision");
            }
            finally { UnityEngine.Object.DestroyImmediate(go); }
            Check("AD3", "Decision tardia: sin decision a tiempo es TIMEOUT y la que llega despues se descarta",
                  p.Count == 0, p.Count == 0 ? "TIMEOUT · descartada al llegar tarde · una sola toma por trial" : Join(p));

            var q = new List<string>();
            if (R(true, false, Dec("NO_CHANGE", null, null)) != AdaptationApply.Outcome.Nothing) q.Add("NO_CHANGE emitio algo");
            if (R(true, false, lalUp, next: false) != AdaptationApply.Outcome.SkipNotAllowed) q.Add("cambio sin trial siguiente no se salto");
            if (R(true, false, Dec("CHANGE_ASSISTANCE", "ESL", "HIGH")) != AdaptationApply.Outcome.SkipInvalid) q.Add("accion y dimension cruzadas no fue INVALID");
            if (R(true, false, Dec("CHANGE_ASSISTANCE", "LAL", "OFF")) != AdaptationApply.Outcome.SkipInvalid) q.Add("LAL a OFF no fue INVALID");
            if (R(true, false, Dec("CHANGE_ENVIRONMENT", "ESL", "BOGUS")) != AdaptationApply.Outcome.SkipInvalid) q.Add("nivel desconocido no fue INVALID");
            Check("AD4", "NO_CHANGE no emite nada; sin trial siguiente o con una decision ilegible, se salta",
                  q.Count == 0, q.Count == 0 ? "NO_CHANGE · NOT_ALLOWED · INVALID (3 casos)" : Join(q));

            var a1 = AdaptationApply.Resolve(true, false, lalUp, true, out bool esl1, out var to1);
            var a2 = AdaptationApply.Resolve(true, false, eslDown, true, out bool esl2, out var to2);
            Check("AD5", "Entre trials, un cambio legible se aplica en su dimension y nivel",
                  a1 == AdaptationApply.Outcome.Apply && !esl1 && to1 == StimulationOrAssistanceLevel.High
                  && a2 == AdaptationApply.Outcome.Apply && esl2 && to2 == StimulationOrAssistanceLevel.Low,
                  $"LAL {a1} {to1} · ESL {a2} {to2}");
        }

        // ==================================================================
        // F5a · WebSocket reconnection (14 Oct; drop of 98752f4e on 7 Oct)
        // ==================================================================
        private static void ReconnectionCases()
        {
            var p = new List<string>();
            var q = new OutgoingQueue(3);
            for (int i = 1; i <= 5; i++)
                q.Enqueue(new OutgoingMessage { Type = "SESSION_EVENT", EventType = $"E{i}" });
            if (q.Count != 3 || q.Dropped != 2) p.Add($"capacidad 3 con 5 eventos: {q.Count} en cola, {q.Dropped} descartados");
            var drained = q.DrainAll();
            string order = string.Join(",", drained.Select(m => m.EventType));
            if (order != "E1,E2,E3") p.Add($"orden al vaciar {order}, se esperaba E1,E2,E3 (se conservan los mas viejos)");
            if (q.Count != 0 || q.Dropped != 0) p.Add("vaciar no reinicio la cola y el contador");
            if (q.Enqueue(null)) p.Add("acepto un mensaje nulo");
            Check("N1", "Cola sin conexion: conserva el orden, tiene tope, cuenta lo descartado y se vacia completa",
                  p.Count == 0, p.Count == 0 ? "3 en orden · 2 descartados contados · reinicio al vaciar" : Join(p));

            var delays = Enumerable.Range(0, 7).Select(ReconnectPolicy.DelaySeconds).ToList();
            string seq = string.Join(", ", delays.Select(d => d.ToString("0.0", System.Globalization.CultureInfo.InvariantCulture)));
            Check("N2", "Reintentos de reconexion: 0.5, 1, 2, 4 s y luego cada 5 s, sin rendirse",
                  seq == "0.5, 1.0, 2.0, 4.0, 5.0, 5.0, 5.0", seq);
        }

        /// <summary>
        /// X9. The peripheral events are animals (D-F6-28): the seven entries of the draw (bird
        /// x3 at the old sphere positions, cat x2, butterfly x2, so a uniform draw gives
        /// 3/7, 2/7, 2/7), each with its length (1.5 / 4.0 / 3.0 s); every one starts and
        /// ends away from its rest pose (it enters, never pops in), rests where it was put,
        /// and nothing moves faster than 3 Hz.
        /// </summary>
        private static void PeripheralAnimalCases()
        {
            var p = new List<string>();
            var layer = GameObject.Find("EnvironmentalLayer");
            var container = layer == null ? null : layer.transform.Find("PeripheralEvents");
            if (container == null) { Check("X9", "Eventos perifericos: animales", false, "no hay PeripheralEvents"); return; }
            var entries = container.Cast<Transform>().ToList();
            var anims = entries.Select(t => t.GetComponent<PeripheralAnimation>()).ToList();
            if (anims.Any(a => a == null)) p.Add("hay eventos sin PeripheralAnimation: " + Join(entries.Where(t => t.GetComponent<PeripheralAnimation>() == null).Select(t => t.name)));
            var ok = anims.Where(a => a != null).ToList();
            int Count(PeripheralAnimation.Kind k) => ok.Count(a => a.AnimalKind == k);
            if (entries.Count != 7 || Count(PeripheralAnimation.Kind.Bird) != 3 || Count(PeripheralAnimation.Kind.Cat) != 2 || Count(PeripheralAnimation.Kind.Butterfly) != 2)
                p.Add($"sorteo: {entries.Count} entradas, pajaro {Count(PeripheralAnimation.Kind.Bird)}, gato {Count(PeripheralAnimation.Kind.Cat)}, mariposa {Count(PeripheralAnimation.Kind.Butterfly)} (se esperan 7: 3/2/2)");
            var length = new Dictionary<PeripheralAnimation.Kind, float> {
                { PeripheralAnimation.Kind.Bird, 1.5f }, { PeripheralAnimation.Kind.Cat, 8.08f }, { PeripheralAnimation.Kind.Butterfly, 3.0f } };
            foreach (var a in ok)
            {
                if (Mathf.Abs(a.DurationSeconds - length[a.AnimalKind]) > 0.01f) p.Add($"{a.name} dura {a.DurationSeconds:F3} s");
                if (a.RateHz > 3f) p.Add($"{a.name} se mueve a {a.RateHz} Hz");
                if (a.Model == null) { p.Add($"{a.name} sin Model"); continue; }
                if (a.AnimalKind == PeripheralAnimation.Kind.Cat) { CatCase(a, p); continue; }
                a.Pose(0f);
                float start = a.Model.localPosition.magnitude;
                a.Pose((a.DurationSeconds - a.RestSeconds) * 0.5f + a.RestSeconds * 0.5f);
                float rest = a.Model.localPosition.magnitude;
                a.Pose(a.DurationSeconds);
                float end = a.Model.localPosition.magnitude;
                a.Pose(0f);
                if (start < 0.3f || end < 0.3f) p.Add($"{a.name} aparece o desaparece en su sitio (inicio {start:F2} m, final {end:F2} m)");
                if (rest > 0.05f) p.Add($"{a.name} no reposa en su sitio ({rest:F2} m)");
                if (a.AnimalKind != PeripheralAnimation.Kind.Cat)
                {
                    // D-F6-27: the Blender mesh, never a box or a sphere; wing pivots at rest are the mesh's own pose.
                    var prims = a.Model.GetComponentsInChildren<MeshFilter>(true).Where(f => f.sharedMesh == null || f.sharedMesh.name == "Cube" || f.sharedMesh.name == "Sphere").ToList();
                    if (prims.Count > 0) p.Add($"{a.name} sigue con primitivas ({prims.Count})");
                    var wings = a.Model.GetComponentsInChildren<Transform>(true).Where(t => t.name.StartsWith("Wing")).ToList();
                    float Spread() => wings.Count == 0 ? 0f : wings.Min(w => Quaternion.Angle(w.localRotation, Quaternion.identity));
                    float Widest() => wings.Count == 0 ? 0f : wings.Max(w => Quaternion.Angle(w.localRotation, Quaternion.identity));
                    float lo = 180f, hi = 0f, inS = (a.DurationSeconds - a.RestSeconds) * 0.5f;   // the bird goes in and out in the same time
                    for (float t = 0f; t < a.DurationSeconds; t += 0.02f)
                    {
                        bool flying = a.AnimalKind == PeripheralAnimation.Kind.Butterfly || t < inS - 0.02f || t > inS + a.RestSeconds + 0.02f;
                        if (!flying) continue;
                        a.Pose(t);
                        lo = Mathf.Min(lo, Spread()); hi = Mathf.Max(hi, Widest());
                    }
                    a.Pose((a.DurationSeconds - a.RestSeconds) * 0.5f + a.RestSeconds * 0.5f);
                    float perched = Widest();
                    a.Pose(0f);
                    if (wings.Count != 2) p.Add($"{a.name}: {wings.Count} alas");
                    // §10.2 and the animation sheets: bird 0° folded when perched, 10°-80° in flight; butterfly 10°-80° all the time.
                    else if (a.AnimalKind == PeripheralAnimation.Kind.Bird && (perched > 1f || lo < 9.9f || hi > 80.1f)) p.Add($"{a.name}: alas {perched:F0} grados posado, {lo:F0}-{hi:F0} en vuelo");
                    else if (a.AnimalKind == PeripheralAnimation.Kind.Butterfly && (lo < 9.9f || hi > 80.1f)) p.Add($"{a.name}: alas {lo:F0}-{hi:F0} grados");
                }
            }
            // D-F6-28: not one sphere left in the v148 room; the silhouettes are 24B, facing the way they walk.
            var studio = GameObject.Find("Studio");
            var spheres = studio == null ? new List<MeshFilter>() : studio.GetComponentsInChildren<MeshFilter>(false).Where(f => f.sharedMesh != null && f.sharedMesh.name == "Sphere" && f.GetComponent<MeshRenderer>().enabled).ToList();
            if (spheres.Count > 0) p.Add("esferas en la sala: " + Join(spheres.Select(f => f.transform.parent.name + "/" + f.name)));
            foreach (var name in new[] { "OutsideFigureLeft_T3", "OutsideFigureRight_T3" })
            {
                var fig = GameObject.Find("Studio/EnvironmentalLayer/Movers/" + name);
                var mesh = fig == null ? null : fig.GetComponentsInChildren<MeshFilter>(true).FirstOrDefault(f => f.name == "SM_24B_Silueta");
                var motion = fig == null ? null : fig.GetComponent<EnvironmentMotion>();
                if (mesh == null || motion == null) { p.Add($"{name} sin la malla 24B"); continue; }
                var axis = new SerializedObject(motion).FindProperty("traverseAxis").vector3Value;
                if (Vector3.Angle(-mesh.transform.forward, axis) > 1f) p.Add($"{name} no mira hacia donde camina");
            }
            Check("X9", "Eventos perifericos: animales (D-F6-28): sorteo 3/2/2, duraciones, entran y salen, reposan en su sitio, <= 3 Hz",
                  p.Count == 0, p.Count == 0 ? Join(entries.Select(t => t.name)) : Join(p));
        }

        /// <summary>
        /// X9, the cat (D-F6-38 - D-F6-40): the rigged 25B mesh playing its window's baked
        /// EVENTO clip (8.08 s, the root's walk inside it). It starts and ends hidden 0.47 m
        /// beyond its stop, stands at the stop while it turns its head, and nothing of the
        /// old box cat is left.
        /// </summary>
        private static void CatCase(PeripheralAnimation a, List<string> p)
        {
            var skin = a.Model.GetComponentInChildren<SkinnedMeshRenderer>(true);
            if (skin == null || a.Model.GetComponentsInChildren<MeshFilter>(true).Length > 0) { p.Add($"{a.name} no es la malla 25B con su rig"); return; }
            string side = a.transform.position.x > 0f ? "EVENTO_VentanaDerecha" : "EVENTO_VentanaIzquierda";
            if (a.BakedClip == null || !a.BakedClip.name.EndsWith(side)) { p.Add($"{a.name} reproduce {(a.BakedClip == null ? "nada" : a.BakedClip.name)}, no {side}"); return; }
            var baked = new Mesh();
            float Away(float t)   // horizontal distance from the stop to the middle of the body
            {
                a.Pose(t);
                skin.BakeMesh(baked, true);
                var c = skin.transform.TransformPoint(baked.bounds.center) - a.transform.position;
                c.y = 0f;
                return c.magnitude;
            }
            float start = Away(0f), stand = Away(3.2f), end = Away(a.DurationSeconds);
            a.Pose(0f);
            UnityEngine.Object.DestroyImmediate(baked);
            if (start < 0.35f || end < 0.35f) p.Add($"{a.name} aparece o desaparece a la vista (inicio {start:F2} m, final {end:F2} m de la parada)");
            if (stand > 0.12f) p.Add($"{a.name} no se para en su sitio ({stand:F2} m)");
        }

        /// <summary>
        /// X10. Stage-1 objects of S5 for set A (D-F6-20, D-F6-26): five prefabs with the
        /// reference envelope (±1 cm), pivot at the centre, no collider. All five kanji
        /// carry an object or none does (never real and placeholder mixed in a session),
        /// and a reference box is never assigned: boxes are scaffolding, not test content.
        /// </summary>
        private static void SetAObjectCases()
        {
            var p = new List<string>();
            var rows = new (string kanji, string code, Vector3 size)[]
            {
                ("KANJI_TSUKI", "01_TSUKI", new Vector3(0.23f, 0.30f, 0.08f)), ("KANJI_KURUMA", "02_KURUMA", new Vector3(0.40f, 0.18f, 0.24f)),
                ("KANJI_HI", "03_HI", new Vector3(0.24f, 0.30f, 0.16f)), ("KANJI_TAKE", "04_TAKE", new Vector3(0.24f, 0.35f, 0.12f)),
                ("KANJI_ISHI", "05_ISHI", new Vector3(0.30f, 0.28f, 0.18f)),
            };
            int assigned = 0, boxes = 0;
            foreach (var r in rows)
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>($"Assets/Art/KanjiLessonAssets/Prefabs/{r.code}.prefab");
                if (prefab == null) { p.Add($"falta el prefab {r.code}"); continue; }
                bool isBox = prefab.transform.Find("Model_Box") != null;
                if (isBox) boxes++;
                var renderers = prefab.GetComponentsInChildren<Renderer>(true);
                if (renderers.Length == 0) { p.Add($"{r.code} sin malla"); continue; }
                var b = renderers[0].bounds;
                foreach (var rr in renderers) b.Encapsulate(rr.bounds);
                if (Vector3.Distance(b.size, r.size) > 0.0173f) p.Add($"{r.code} mide {b.size:F2}, referencia {r.size:F2}");   // 1 cm per axis
                if (b.center.magnitude > 0.01f) p.Add($"{r.code} pivote fuera del centro ({b.center:F3})");
                if (prefab.GetComponentsInChildren<Collider>(true).Length > 0) p.Add($"{r.code} tiene collider");
                var item = AssetDatabase.LoadAssetAtPath<KanjiLearningItem>($"Assets/Resources/kanji/{r.kanji}.asset");
                if (item != null && item.anchorObjectPrefab != null)
                {
                    assigned++;
                    if (item.anchorObjectPrefab.transform.Find("Model_Box") != null) p.Add($"{r.kanji} tiene asignada una caja");
                }
            }
            if (assigned != 0 && assigned != rows.Length) p.Add($"{assigned}/5 kanji con objeto: se mezclan real y placeholder (D-F6-26)");
            Check("X10", "Objetos de S5 del set A: cinco prefabs del tamano de referencia, los cinco asignados o ninguno, nunca una caja (D-F6-26)",
                  p.Count == 0, p.Count == 0 ? $"{rows.Length - boxes} modelos, {boxes} cajas · asignados {assigned}/5" : Join(p));
        }

        /// <summary>
        /// X11. The v148 room is the one in the re-export from the approved file (D-F6-42):
        /// every slot of its manifest stands at its manifest position and Y rotation (the
        /// clock at 2.50 m, decision 9) with its model as a child, ESL slots at scale 1,
        /// the podium model handed to ControlsIntro, no collider on any model, and the old
        /// primitive room switched off (the cat sills and the exterior backdrop stay).
        /// </summary>
        private static void JapaneseRoomCases()
        {
            var p = new List<string>();
            var manifest = JapaneseRoomIntegration.LoadManifest();
            if (manifest == null) { Check("X11", "Sala v148 del manifest", false, "no hay " + JapaneseRoomIntegration.ManifestCopy); return; }
            if (manifest.dirty_at_start) p.Add("el manifest viene de un .blend con cambios sin guardar");
            int placed = 0;
            foreach (var h in manifest.huecos.Where(h => !JapaneseRoomIntegration.Pending.Contains(h.hueco)))
            {
                var t = JapaneseRoomIntegration.Placed(h.hueco);
                if (t == null) { p.Add($"{h.hueco} no esta en la escena"); continue; }
                var want = JapaneseRoomIntegration.Position(h);
                if (Vector3.Distance(t.position, want) > 0.001f) p.Add($"{h.hueco} en {t.position:F3}, manifest {want:F3}");
                if (Mathf.Abs(Mathf.DeltaAngle(t.eulerAngles.y, h.unity_rot_y_deg)) > 0.1f) p.Add($"{h.hueco} gira {t.eulerAngles.y:F1}, manifest {h.unity_rot_y_deg:F1}");
                if (t.GetComponent<EnvironmentProp>() != null && t.localScale != Vector3.one) p.Add($"{t.name} con escala {t.localScale:F2}");
                if (t.GetComponentsInChildren<MeshRenderer>(true).Length == 0 && t.GetComponentsInChildren<SkinnedMeshRenderer>(true).Length == 0) p.Add($"{h.hueco} sin malla");
                if (t.GetComponentsInChildren<Collider>(true).Length > 0) p.Add($"{h.hueco} tiene collider");
                var model = t.name == h.hueco ? t : t.Find(h.hueco);
                if (model != null)
                    foreach (var child in model.GetComponentsInChildren<Transform>(true).Where(c => c != model))
                    {
                        var src = PrefabUtility.GetCorrespondingObjectFromSource(child);
                        if (src != null)
                        {
                            var (wantPos, wantRot) = JapaneseRoomIntegration.ExpectedPose(src);
                            if (Vector3.Distance(child.localPosition, wantPos) > 0.0005f || Quaternion.Angle(child.localRotation, wantRot) > 0.1f)
                                p.Add($"{h.hueco}/{child.name} con la pose del FBX sin corregir (ejes de Blender)");
                        }
                        if (child.name.EndsWith("_Interfaz") && child.gameObject.activeSelf) p.Add($"{h.hueco}/{child.name} encendido sobre el canvas");
                    }
                placed++;
            }
            var intro = UnityEngine.Object.FindFirstObjectByType<ControlsIntro>(FindObjectsInactive.Include);
            var podium = intro == null ? null : new SerializedObject(intro).FindProperty("podiumModel").objectReferenceValue;
            if ((podium == null) != JapaneseRoomIntegration.Pending.Contains("18B_Atril")) p.Add(podium == null ? "ControlsIntro sin el atril 18B" : "el atril 18B esta asignado y espera su re-export");
            var room = GameObject.Find("Studio/Room");
            if (room != null)
                foreach (Transform c in room.transform)
                    if (c.gameObject.activeSelf && c.name != "JapaneseRoom" && c.name != "CatShelves" && c.name != "Exterior_Front") p.Add($"sala vieja encendida: {c.name}");
            var floor = GameObject.Find("Studio/Floor");
            if (floor != null && floor.GetComponent<MeshRenderer>().enabled) p.Add("el piso viejo se ve");
            Check("X11", "Sala v148 del re-export aprobado: cada hueco en su sitio del manifest, sin collider, sala vieja apagada (D-F6-42)",
                  p.Count == 0, p.Count == 0 ? $"{placed}/{manifest.huecos.Length} huecos · pendientes: {Join(JapaneseRoomIntegration.Pending)}" : Join(p));
        }

        private static void Check(string id, string title, bool passed, string detail)
            => _cases.Add(new Case { Id = id, Title = title, Passed = passed, Detail = detail });

        private static string Join(IEnumerable<string> xs) => string.Join(", ", xs.ToArray());

        private static void Report()
        {
            int ok = _cases.Count(c => c.Passed);
            var sb = new StringBuilder();
            sb.AppendLine($"[Pruebas F2] {ok}/{_cases.Count} PASS");
            foreach (var c in _cases)
                sb.AppendLine($"  {(c.Passed ? "PASS" : "FAIL")}  {c.Id}  {c.Title}  ·  {c.Detail}");

            if (ok == _cases.Count) Debug.Log(sb.ToString());
            else Debug.LogError(sb.ToString());
        }
    }
}

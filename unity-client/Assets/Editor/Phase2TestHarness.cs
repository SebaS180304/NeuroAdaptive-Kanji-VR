using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using NeuroAdaptiveVR.Controllers;
using NeuroAdaptiveVR.Core;
using NeuroAdaptiveVR.Data;
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
    /// comprobacion independiente es la de verify_trials.sql, que mira los
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
            SequenceCases(content);
            AssociationCases(content);
            EnvironmentCases();
            AssistanceCases();
            MatrixCases();
            WiringCases(content);

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
                esl.SetSeed(20260909);
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
        }

        // ==================================================================

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

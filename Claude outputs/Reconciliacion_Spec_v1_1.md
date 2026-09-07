# Reconciliación del Game Flow v1 → v1.1

Fecha: 3 de septiembre de 2026. Lista precisa de ediciones al
`NeuroAdaptive_VR_Game_Flow_v1_Unity_Design_Specification.docx` para que refleje
las decisiones tomadas entre el 26 y el 28 de agosto.

**Por qué importa ahora:** el spec es el documento que rige implementación, y la
Fase 2 consiste en construir la escena y el core learning loop. Hoy el documento
todavía describe S6 como Kanji Hunt y lo lista en el alcance MUST. Empezar Fase 2
desde este texto significa construir exactamente la mecánica que se decidió
eliminar.

Las ediciones están separadas por urgencia: las del bloque A afectan lo que se
construye **esta quincena**; las del bloque B afectan Fases 4-5 y pueden esperar,
pero conviene aplicarlas en la misma pasada para no emitir dos versiones.

---

## Bloque A · Bloquean Fase 2

### A1 · §5.4 Guided Association and Guided Practice

**Texto actual:**

> Guided Practice exposes the learner to reusable VR interactions such as Kanji
> Hunt, optional Object Matching, and optional short Assembly recall.
>
> Kanji Hunt is the preferred calibration mechanic because it naturally produces
> response time, head orientation, visual search, and distractor-interaction
> data.

**Reemplazar por:**

> Guided Practice presents seated recognition trials that reuse the same three
> retrieval trial types and the same response mechanic as the Experimental
> Retrieval Block.
>
> Reusing the S7 mechanic is the deliberate choice for calibration: response
> times from a seated multiple-choice trial are directly comparable to those of
> the retrieval block, whereas response times from a spatial visual-search task
> are not. Same-task calibration makes the S6 → S7 comparison valid.

**Conservar sin cambios** la tercera frase del párrafo ("During Guided Practice,
ESL and LAL are set to MEDIUM, data are collected, but adaptation remains
disabled").

### A2 · §7.7 S6 — Guided Practice / Calibration

**Texto actual de *Experience / interaction*:**

> Preferred mandatory activity: Kanji Hunt. Optional rotating mechanics: Object
> Matching and short Assembly recall.

**Reemplazar por:**

> Seated recognition practice over the five learned kanji, using the same three
> retrieval trial types (Meaning → Kanji, Kanji → Meaning, Kanji → Reading) and
> the same response mechanic as S7, presented at the Learning Board / Response
> Area. No locomotion and no spatial search.

**Ampliar la línea de *Controller behavior*** — el texto actual dice que la
salida es "the initial task-response calibration profile for the current
session". Añadir:

> Output is twofold: the initial task-response calibration profile (behavioral)
> and an in-task EEG load reference measured under the same ESL/LAL = MEDIUM
> conditions as S7. The rest EEG baseline from S4 alone is a weaker normalizer
> than a task reference obtained with the same mechanic.

La línea de *Data collected* ya incluye "synchronized EEG windows", así que es
compatible sin cambios.

### A3 · §15 MVP Scope Protection and Optional Enhancements

En la fila **MUST — Game Flow v1**, sustituir `Kanji Hunt calibration` por
`seated recognition calibration (S6)`.

En la fila **SHOULD — if schedule allows**, eliminar `Improved object matching`.

En la fila **COULD — future**, añadir `Kanji Hunt`, `Object Matching` y
`spatial search mechanics`.

**Motivo a registrar:** la eliminación responde a tres razones acumuladas — el
riesgo de desplazamiento físico de electrodos secos durante búsqueda espacial
sostenida, el ahorro de dos sistemas de interacción completos en el presupuesto
de 16 semanas, y el confort del participante en visitas que pueden llegar a
60-75 minutos con preparación de electrodos.

---

## Bloque B · Afectan Fases 4-5

### B1 · §16 Parameters Still Requiring Validation

| Parámetro | Valor actual | Reemplazar por |
| --- | --- | --- |
| EEG features available from WAVEX | `TBD` | Engagement Index global (beta/(alpha+theta)), theta frontal relativo y theta/beta ratio relativo, los tres normalizados contra el baseline individual de S4 y contrastables contra la referencia en tarea de S6. Montaje objetivo: 6 canales EEG frontal-central más 2 de EOG, sujeto a confirmación de posiciones alcanzables con el visor puesto. |
| EEG quality thresholds | `GOOD / ACCEPTABLE / POOR conceptual states` | Definidos operacionalmente por: porcentaje de muestras sin saturar y libres de artefacto en la ventana, ausencia de solape con `HEAD_AWAY`, y desviación estándar dentro de rango fisiológico. Los umbrales numéricos siguen dependiendo de pruebas de hardware. |

Añadir además una fila nueva:

| Parámetro | Valor propuesto | Fuente de validación |
| --- | --- | --- |
| Baseline de S4 | 60 s ojos abiertos + 45 s ojos cerrados | Prueba de bloqueo alfa; el aumento de alfa al cerrar los ojos valida por sesión que el EEG registra corteza real |

### B2 · §7.5 S4 — Individual EEG Baseline

Cambiar la duración objetivo de `60–90 seconds` a `60 s eyes-open + 45 s
eyes-closed`, y añadir a *Data collected*:

> Eyes-open / eyes-closed alpha ratio, recorded as a per-session EEG validity
> check. A participant whose alpha power does not rise on eye closure has
> suspect signal for that session regardless of reported impedance.

### B3 · §10.2 Adaptation timing constraints

Modificar la ventana de observación inicial. Texto actual:

> at least 3 completed trials or approximately 20–30 seconds of usable task data

**Reemplazar el "or" por un "and":** exigir ambas condiciones —al menos 3 trials
completados **y** un mínimo de segundos de EEG libre de artefacto, sugerencia
inicial 15 s— extendiendo la ventana automáticamente si no se cumple, y
registrando cada extensión como evento.

Añadir una restricción nueva al final de la sección:

> Adaptation is disabled during the final trials of S7 (provisional: last 4), so
> that the last adaptation event always has a clean post-observation window for
> outcome classification. Without this tail, late adaptations can only ever be
> classified UNCERTAIN.

### B4 · §10.1 EEG quality gate and fallback

Añadir una regla de análisis, no solo de operación:

> A pre-registered inclusion threshold determines whether a MULTIMODAL session
> counts as multimodal for analysis. A session that spent most of its decision
> windows in BEHAVIOR_FALLBACK is functionally a BEHAVIOR_ADAPTIVE session, and
> including it as multimodal dilutes the study's primary contrast. The threshold
> is fixed before the pilot, not after inspecting the data.

Añadir también la advertencia sobre confusión con ESL:

> EEG quality is expected to degrade as ESL rises, because higher ESL means more
> peripheral motion and therefore more ocular and head-movement artifact. The
> proportion of usable EEG windows must be reported broken down by ESL level,
> and the relationship treated as a hypothesis the pilot measures rather than an
> implementation detail.

### B5 · §1.2 Design maturity

La fila `EEG feature set | To validate` puede pasar a
`Proposed, pending hardware confirmation`, con la nota:
`Feature set defined in Investigacion_EEG_Integracion_Neurociencia.md; depends
on confirming reachable electrode positions (question A2 to Mirai).`

---

## Lo que NO cambia

Conviene dejarlo dicho para que la v1.1 no se lea como un rediseño:

- Los tres tipos de trial de recuperación siguen siendo exactamente esos tres.
- ESL y LAL siguen siendo las únicas dos dimensiones adaptativas, con la misma
  separación de responsabilidades y las mismas prohibiciones de §8.3 y §9.3.
- S7 sigue siendo el único estado donde la adaptación puede actuar.
- La regla de una sola dimensión por evento de adaptación, el cooldown y la
  histéresis se mantienen.
- El escenario sigue siendo una sola escena modular.

## Trazabilidad

| Edición | Documento de origen |
| --- | --- |
| A1, A2, A3 | `Correccion_Alcance_EEG_Actividades.md` §3, §6 |
| B1 | `Investigacion_EEG_Integracion_Neurociencia.md` §5 · `Correcciones_Planteamiento_Post_Investigacion_EEG.md` §1.2 |
| B2 | `Correcciones_Planteamiento_Post_Investigacion_EEG.md` §2.1 |
| B3 | `Correcciones_Planteamiento_Post_Investigacion_EEG.md` §2.2, §3.2 |
| B4 | `Correcciones_Planteamiento_Post_Investigacion_EEG.md` §4.1, §4.2 |
| B5 | `Correcciones_Planteamiento_Post_Investigacion_EEG.md` §0 |

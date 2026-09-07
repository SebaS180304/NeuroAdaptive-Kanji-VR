# Plan de arranque · Fase 2 · Learning Experience Core

Fecha: 3 de septiembre de 2026. Entregable de la fase: **Static VR Learning
Prototype**. Hito al que apunta: **M2 · Instrumented Learning Prototype**,
25 de septiembre.

Criterio de salida de M2, textual del anteproyecto: *"Un usuario puede aprender y
practicar kanji y todos los eventos relevantes quedan registrados."*

## 0 · Prerrequisito que bloquea

Aplicar el bloque A de `Reconciliacion_Spec_v1_1.md` antes de escribir código de
escena. Son tres ediciones al spec y evitan construir Kanji Hunt y Object
Matching, que salieron del alcance.

## 1 · La decisión que hay que tomar primero: cuáles son los 15 kanji

Todo lo demás depende de esto. Los modelos 3D, las grabaciones de audio, la
segmentación de trazos para el ensamblaje y los distractores de las opciones
múltiples se derivan del conjunto elegido. Es la decisión con más dependencias
aguas abajo y la que más cuesta cambiar tarde.

Restricciones que ya impone el spec:

- **15 kanji experimentales** repartidos en **3 sets balanceados por número de
  trazos** (uno por condición, para que ningún participante vea el mismo
  contenido dos veces entre visitas).
- **Pool de tutorial**: 一, 二, 三 principalmente, con 四 y 五 como práctica
  adicional. Ya está fijado.
- **Pool de reserva** para reemplazar kanji que un participante ya conozca.
- Cada kanji necesita una vía de descubrimiento defendible: **pictográfica**
  (3D → forma simplificada → kanji, como 木 o 山) o **contextual** (cuando la
  transformación directa sería engañosa, como 学).
- Una **lectura objetivo** por kanji, con audio estandarizado.
- Segmentación en **2–4 grupos de trazos** para el ensamblaje guiado.

Producto de este paso: una tabla con los 15 kanji, su set asignado, número de
trazos, significado, lectura objetivo, tipo de descubrimiento y segmentación
propuesta. Conviene revisarla con alguien que sepa japonés antes de encargar
assets.

## 2 · Frentes de trabajo, y cuál es el de mayor apalancamiento

### 2.1 El sistema de respuesta — hacerlo primero

Tras el rediseño de S6, el mismo mecanismo de respuesta se usa en **cuatro
estados**: la asociación guiada de S5, el reconocimiento sentado de S6, los
trials de recuperación de S7 y el assessment de S8. Es el componente más
reutilizado del proyecto.

Construirlo bien una vez —presentación del prompt, N opciones, selección,
confirmación, feedback, y emisión del evento correspondiente— rinde en cuatro
lugares. Construirlo cuatro veces mal es la forma más rápida de perder la fase.

Los tres tipos de trial (T1 Meaning→Kanji, T2 Kanji→Meaning, T3 Kanji→Reading)
son variaciones de presentación sobre el mismo mecanismo, no mecanismos
distintos. La única regla dura es la de T3: **el audio de la lectura objetivo
nunca puede reproducirse antes de la respuesta**.

### 2.2 Escena Japanese Learning Studio

Una sola escena modular con las cinco zonas funcionales: Learning Board,
Object/Association Area, Interaction Table, Response Area y Environmental Layer.

La Environmental Layer merece atención desde ahora aunque ESL no adapte hasta
Fase 5: es la capa cuya densidad de props, objetos en movimiento y eventos
periféricos van a variar. Conviene estructurarla desde el principio como algo
parametrizable por nivel, no como decoración fija que después haya que
desmontar.

### 2.3 Modelo de datos: KanjiLearningItem

Hoy es una clase C# stub. Debe convertirse en ScriptableObjects reales, uno por
kanji, con todos los campos que consume el flujo: identificador, glifo,
significado, lectura objetivo, referencia al audio, tipo de descubrimiento,
referencia al modelo 3D, segmentación de trazos, y set asignado.

El principio del anteproyecto es que el contenido sea **data-driven**: debe
poderse sustituir un kanji sin tocar código.

### 2.4 Mecánicas de S5

Discovery (pictográfico o contextual), reproducción del audio estandarizado,
ensamblaje guiado por grupos de trazos, y asociación guiada. Es la secuencia que
se repite para cada uno de los cinco kanji de la sesión.

### 2.5 Contenido — arranca en paralelo desde el día uno

Modelos 3D de los objetos/conceptos, animaciones de transformación pictográfica,
y grabaciones de audio estandarizadas de las lecturas.

**Este es el cuello de botella clásico de la fase.** No es trabajo de código,
tiene tiempo de producción propio, y si se descubre en la semana 4 que faltan
las grabaciones, la fase se cae. El anteproyecto ya lo lista como actividad
transversal; conviene tratarlo como tal y no como algo que se hace al final.

Una salida pragmática para no bloquear el desarrollo: definir *placeholders*
desde el inicio —primitivas para los 3D, audio sintetizado provisional— con la
condición explícita de que el contenido definitivo entra antes del dry run, no
antes del piloto.

## 3 · Lo que NO entra en Fase 2

Conviene tenerlo escrito para resistir la tentación:

- Adaptación real de ESL/LAL — los controladores existen y se pueden fijar por
  configuración, pero no deciden nada hasta Fase 5.
- Integración de EEG/WAVEX — Fase 4.
- El vocabulario completo de eventos conductuales — es Fase 3; en Fase 2 basta
  con que el flujo funcione y emita los eventos que ya existen.
- Handwriting recognition, reconocimiento de voz, NPCs — fuera del MVP entero.

## 4 · Orden sugerido

1. Aplicar el bloque A del spec.
2. Fijar la tabla de los 15 kanji y revisarla con alguien que sepa japonés.
3. Construir el sistema de respuesta con los tres tipos de trial.
4. Armar la escena con sus cinco zonas y la Environmental Layer parametrizable.
5. Convertir KanjiLearningItem en ScriptableObjects y cargar el contenido.
6. Implementar la secuencia de S5.
7. Encadenar S5 → S6 → S7 → S8 con el flujo ya funcionando de punta a punta.

Los puntos 2 y 5 dependen del contenido; el 3 y el 4 no, así que pueden avanzar
en paralelo mientras se resuelve la autoría.

## 5 · Riesgos de esta fase

**El contenido pedagógico llega tarde.** Es el riesgo principal. Mitigación:
placeholders desde el día uno y fecha límite explícita para el contenido real.

**El sistema de respuesta se construye a medida de S7 y luego no encaja en S5,
S6 y S8.** Mitigación: diseñarlo contra los cuatro casos de uso desde el
principio, no adaptarlo después.

**La Environmental Layer se construye como decoración fija.** Mitigación:
parametrizar por nivel desde el inicio, aunque los tres niveles se vean
idénticos hasta Fase 5.

**El spec queda desfasado otra vez.** Mitigación: aplicar el bloque B de la
reconciliación en la misma pasada que el bloque A, aunque afecte a fases
posteriores.

## 6 · Trabajo que corre en paralelo, fuera de Fase 2

- Las cuatro preguntas pendientes a Mirai (A2, A5, A7, A13). Sin bloqueo mutuo
  con Fase 2, pero con el tiempo de espera más largo del proyecto.
- Diseño experimental, consentimiento informado y procedimiento de ética. El
  anteproyecto lo marca como dependencia crítica y sigue sin comité confirmado.
  No bloquea Fase 2, sí bloquea el piloto.
- Reclutamiento de los 5–10 participantes.

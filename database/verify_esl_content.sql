-- Verificacion del ESL y del contenido de kanji contra los datos grabados.
--
-- Complementa a las otras dos:
--   verify_events.sql   comprueba la FORMA del payload (que los campos esten)
--   verify_trials.sql   comprueba el COMPORTAMIENTO del trial y la matriz 9.1
--   este                comprueba el ENTORNO y QUE KANJI se usaron
--
-- Por que hace falta mirar la base y no basta con el arnes del Editor: el
-- arnes demuestra que el ESL activa los objetos correctos en la escena. No
-- puede demostrar que el nivel que activo esos objetos sea el mismo que quedo
-- escrito en la fila. Esa discrepancia ya ocurrio --el 9 de septiembre la
-- telemetria estampaba esl=OFF por fallback mientras la escena obedecia a
-- otro nivel-- y es invisible desde dentro de Unity.
--
-- El caso peor sigue siendo el mismo: OFF es el valor por omision del enum Y
-- el valor del fallback, asi que un cableado roto y un OFF legitimo producen
-- filas identicas. Por eso las corridas de prueba se hacen con un nivel que
-- NO sea OFF.
--
-- Uso en PowerShell (Windows):
--   Get-Content database\verify_esl_content.sql | docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr
--
-- Uso en bash / Git Bash:
--   docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr < database/verify_esl_content.sql

\set ON_ERROR_STOP on
\pset pager off

\echo ''
\echo '=============================================================='
\echo '1. Que niveles de ESL llegaron, y cuantos eventos con cada uno'
\echo '=============================================================='
\echo 'Si la corrida se hizo con ESL=MEDIUM y aqui solo aparece OFF, el'
\echo 'EnvironmentalStimulationController no esta cableado a la telemetria.'

SELECT
    e.payload ->> 'esl'                      AS esl,
    e.payload ->> 'lal'                      AS lal,
    count(*)                                 AS eventos,
    count(DISTINCT e.payload ->> 'trial_id') AS trials
FROM session_events e
GROUP BY 1, 2
ORDER BY 3 DESC;

\echo ''
\echo '=============================================================='
\echo '2. ENVIRONMENT_APPLIED: un evento por cada aplicacion de nivel'
\echo '=============================================================='
\echo 'prop_count y mover_count tienen que caer dentro del rango del perfil'
\echo 'que dice profile_name. Un conteo por debajo del minimo significa que'
\echo 'la escena no tiene suficientes objetos de ese tier: el nivel aplicado'
\echo 'es mas bajo que el que la fila declara.'

SELECT
    e.id,
    e.payload ->> 'esl'                          AS esl_contexto,
    e.payload ->> 'profile_name'                 AS perfil,
    (e.payload ->> 'prop_count')::int            AS props,
    (e.payload ->> 'mover_count')::int           AS movers,
    (e.payload ->> 'max_tier')::int              AS max_tier,
    (e.payload ->> 'peripheral_interval_min_ms')::int AS int_min_ms,
    (e.payload ->> 'peripheral_interval_max_ms')::int AS int_max_ms,
    (e.payload ->> 'seed')::bigint               AS seed
FROM session_events e
WHERE e.event_type = 'ENVIRONMENT_APPLIED'
ORDER BY e.id;

\echo ''
\echo '-- El nivel del contexto y el perfil aplicado tienen que concordar.'
\echo '-- Filas aqui = la escena obedece a un perfil y el dato dice otro nivel.'

SELECT
    e.id,
    e.payload ->> 'esl'          AS esl_contexto,
    e.payload ->> 'profile_name' AS perfil
FROM session_events e
WHERE e.event_type = 'ENVIRONMENT_APPLIED'
  AND upper(e.payload ->> 'profile_name') NOT LIKE '%' || upper(e.payload ->> 'esl') || '%';

\echo ''
\echo '=============================================================='
\echo '3. FOCUS y MINIMAL tienen que llegar con el entorno vacio'
\echo '=============================================================='
\echo 'Spec 7.9 describe Focus Mode como "environment darkened/neutralized",'
\echo 'y la interpretacion adoptada el 10 de septiembre es: cero props y cero'
\echo 'eventos perifericos, SIN tocar la iluminacion (3.3 y 8.3 la ponen fuera'
\echo 'de ESL). Filas aqui contradicen esa interpretacion.'

SELECT
    e.id,
    e.payload ->> 'esl'                AS esl,
    (e.payload ->> 'prop_count')::int  AS props,
    (e.payload ->> 'mover_count')::int AS movers
FROM session_events e
WHERE e.event_type = 'ENVIRONMENT_APPLIED'
  AND e.payload ->> 'esl' IN ('FOCUS', 'MINIMAL', 'BASELINE')
  AND ((e.payload ->> 'prop_count')::int > 0 OR (e.payload ->> 'mover_count')::int > 0);

\echo ''
\echo '=============================================================='
\echo '4. PERIPHERAL_EVENT: ocurren donde deben y no donde no deben'
\echo '=============================================================='
\echo 'Spec 8.1: LOW ninguno, MEDIUM ~1 cada 25-35 s, HIGH ~1 cada 10-15 s.'
\echo 'Un evento periferico con esl=LOW o FOCUS es una distraccion que actuo'
\echo 'sobre la sesion fuera de la manipulacion.'

SELECT
    e.payload ->> 'esl'                  AS esl,
    count(*)                             AS eventos,
    min((e.payload ->> 'event_index')::int) AS primer_indice,
    max((e.payload ->> 'event_index')::int) AS ultimo_indice
FROM session_events e
WHERE e.event_type = 'PERIPHERAL_EVENT'
GROUP BY 1
ORDER BY 1;

\echo ''
\echo '-- Intervalos reales entre eventos perifericos consecutivos, en segundos.'
\echo '-- Se comparan contra el rango que declaro el ENVIRONMENT_APPLIED vigente.'

WITH pe AS (
    SELECT
        e.id,
        e.payload ->> 'esl'                          AS esl,
        (e.payload ->> 'session_elapsed_ms')::bigint AS t_ms,
        lag((e.payload ->> 'session_elapsed_ms')::bigint)
            OVER (ORDER BY (e.payload ->> 'session_elapsed_ms')::bigint) AS t_prev_ms
    FROM session_events e
    WHERE e.event_type = 'PERIPHERAL_EVENT'
      AND jsonb_typeof(e.payload -> 'session_elapsed_ms') = 'number'
)
SELECT esl,
       count(*)                                        AS intervalos,
       round(min(t_ms - t_prev_ms) / 1000.0, 1)        AS min_s,
       round(avg(t_ms - t_prev_ms) / 1000.0, 1)        AS media_s,
       round(max(t_ms - t_prev_ms) / 1000.0, 1)        AS max_s
FROM pe
WHERE t_prev_ms IS NOT NULL
GROUP BY esl
ORDER BY esl;

\echo ''
\echo '=============================================================='
\echo '5. Los kanji usados vienen del contrato y de UN SOLO set'
\echo '=============================================================='
\echo 'Una sesion ensena un set (spec 4.1). Si aqui aparecen kanji_id de dos'
\echo 'sets, la asignacion no esta respetando el set de la sesion -- y los'
\echo 'distractores intra-set dejan de ser intra-set.'
\echo ''
\echo 'La lista de abajo esta escrita a mano a proposito: es la unica forma de'
\echo 'que esta consulta sea independiente del codigo que produjo las filas.'
\echo 'Si el reparto cambia, esta consulta tiene que fallar y obligar a'
\echo 'actualizarla; una consulta que se regenerara sola no comprobaria nada.'

WITH sets(nombre, kanji_id) AS (
    VALUES
        ('A','KANJI_TSUKI'), ('A','KANJI_KURUMA'), ('A','KANJI_HI'),
        ('A','KANJI_TAKE'),  ('A','KANJI_ISHI'),
        ('B','KANJI_YAMA'),  ('B','KANJI_MON'),    ('B','KANJI_ONNA'),
        ('B','KANJI_TE'),    ('B','KANJI_AME'),
        ('C','KANJI_HITO'),  ('C','KANJI_ASHI'),   ('C','KANJI_USHI'),
        ('C','KANJI_NIKU'),  ('C','KANJI_HANA')
),
usados AS (
    SELECT DISTINCT e.payload ->> 'kanji_id' AS kanji_id
    FROM session_events e
    WHERE e.payload ? 'kanji_id'
)
SELECT
    coalesce(s.nombre, '(fuera del reparto experimental)') AS set_o_pool,
    count(*)                                               AS kanji_distintos,
    string_agg(u.kanji_id, ', ' ORDER BY u.kanji_id)       AS ids
FROM usados u
LEFT JOIN sets s ON s.kanji_id = u.kanji_id
GROUP BY 1
ORDER BY 1;

\echo ''
\echo '-- Cuantos trials por kanji. Con la rotacion del banco de pruebas el'
\echo '-- reparto no tiene por que ser uniforme, pero un kanji con cero trials'
\echo '-- en una corrida larga apunta a un generador de objetivo sesgado.'

SELECT
    e.payload ->> 'kanji_id'  AS kanji_id,
    count(DISTINCT e.payload ->> 'trial_id') AS trials,
    string_agg(DISTINCT e.payload ->> 'trial_type', ', ') AS tipos
FROM session_events e
WHERE e.event_type = 'TRIAL_STARTED'
GROUP BY 1
ORDER BY 2 DESC, 1;

\echo ''
\echo '=============================================================='
\echo '6. kanji_char y kanji_id no pueden contradecirse'
\echo '=============================================================='
\echo 'DEUDA CONOCIDA: TRIAL_STARTED y ANSWER_SELECTED llevan kanji_char en el'
\echo 'payload ademas del kanji_id del bloque de contexto. Son dos formas del'
\echo 'mismo hecho en la misma fila, que es la clase de duplicacion que este'
\echo 'proyecto lleva persiguiendo. Mientras siga ahi, al menos que se'
\echo 'compruebe que concuerdan.'

WITH esperado(kanji_id, kanji_char) AS (
    VALUES
        ('KANJI_TSUKI','月'), ('KANJI_KURUMA','車'), ('KANJI_HI','火'),
        ('KANJI_TAKE','竹'),  ('KANJI_ISHI','石'),
        ('KANJI_YAMA','山'),  ('KANJI_MON','門'),    ('KANJI_ONNA','女'),
        ('KANJI_TE','手'),    ('KANJI_AME','雨'),
        ('KANJI_HITO','人'),  ('KANJI_ASHI','足'),   ('KANJI_USHI','牛'),
        ('KANJI_NIKU','肉'),  ('KANJI_HANA','花'),
        ('KANJI_NICHI','日')
)
SELECT
    e.id,
    e.payload ->> 'trial_id'   AS trial_id,
    e.payload ->> 'kanji_id'   AS kanji_id,
    e.payload ->> 'kanji_char' AS kanji_char_en_payload,
    x.kanji_char               AS kanji_char_esperado
FROM session_events e
JOIN esperado x ON x.kanji_id = e.payload ->> 'kanji_id'
WHERE e.payload ? 'kanji_char'
  AND e.payload ->> 'kanji_char' IS DISTINCT FROM x.kanji_char;


\echo ''
\echo '=============================================================='
\echo '7. Matriz del Apendice A: el par estado-nivel que de verdad llego'
\echo '=============================================================='
\echo 'Unity ya comprueba esto al entrar a cada estado, pero esa comprobacion'
\echo 'y el codigo comprobado comparten mi lectura del spec. Esta consulta es'
\echo 'independiente: la tabla de abajo esta transcrita a mano del spec 7 y se'
\echo 'contrasta contra los pares que quedaron escritos en la base.'
\echo ''
\echo 'S8 es el caso que importa: se define por ser "no-assistance" y es la'
\echo 'medida primaria de aprendizaje inmediato. Un S8 con LAL distinto de OFF'
\echo 'no produce un dato malo -- produce un dato que mide otra cosa.'

WITH permitido(state, esl_ok, lal_ok) AS (
    VALUES
        ('S1_WELCOME_ORIENTATION',         ARRAY['LOW'],                     ARRAY['OFF']),
        ('S2_VR_TUTORIAL',                 ARRAY['LOW'],                     ARRAY['OFF']),
        ('S3_SYSTEM_VALIDATION',           ARRAY['MINIMAL'],                 ARRAY['OFF']),
        ('S4_EEG_BASELINE',                ARRAY['BASELINE'],                ARRAY['OFF']),
        ('S5_STANDARDIZED_LEARNING',       ARRAY['LOW'],                     ARRAY['OFF']),
        ('S6_GUIDED_PRACTICE_CALIBRATION', ARRAY['MEDIUM'],                  ARRAY['MEDIUM']),
        ('S7_EXPERIMENTAL_RETRIEVAL',      ARRAY['LOW','MEDIUM','HIGH'],     ARRAY['LOW','MEDIUM','HIGH']),
        ('S8_IMMEDIATE_ASSESSMENT',        ARRAY['FOCUS','LOW'],             ARRAY['OFF']),
        ('S9_SESSION_SUMMARY',             ARRAY['LOW'],                     ARRAY['OFF'])
)
SELECT
    e.payload ->> 'state'  AS estado,
    e.payload ->> 'esl'    AS esl,
    e.payload ->> 'lal'    AS lal,
    count(*)               AS eventos,
    CASE
        WHEN NOT (e.payload ->> 'esl' = ANY(p.esl_ok)) THEN 'ESL fuera de la matriz'
        WHEN NOT (e.payload ->> 'lal' = ANY(p.lal_ok)) THEN 'LAL fuera de la matriz'
    END                    AS problema
FROM session_events e
JOIN permitido p ON p.state = e.payload ->> 'state'
WHERE NOT (e.payload ->> 'esl' = ANY(p.esl_ok))
   OR NOT (e.payload ->> 'lal' = ANY(p.lal_ok))
GROUP BY 1, 2, 3, 5
ORDER BY 1;

\echo ''
\echo 'Cero filas = todos los bloques corrieron con el par que el spec pide.'
\echo ''
\echo '=============================================================='
\echo '8. La secuencia planeada frente a la que ocurrio'
\echo '=============================================================='
\echo 'TRIAL_SEQUENCE_GENERATED dice que se planeo; los TRIAL_STARTED dicen'
\echo 'que paso. Que difieran no es un error: una sesion abortada en el trial'
\echo '12 de 20 produce exactamente esa diferencia, y es el dato que dice'
\echo 'donde se corto.'

SELECT
    e.payload ->> 'block_state'                   AS bloque,
    e.payload ->> 'kanji_set'                     AS kanji_set,
    e.payload ->> 'seed_raw'                      AS seed_raw,
    (e.payload ->> 'trial_count')::int            AS planeados,
    (e.payload ->> 'distinct_pairs')::int         AS pares_cubiertos,
    (e.payload ->> 'min_lag_requested')::int      AS separacion_pedida,
    (e.payload ->> 'min_lag_achieved')::int       AS separacion_lograda,
    (e.payload ->> 'ordering_attempts')::int      AS intentos,
    jsonb_array_length(e.payload -> 'sequence')   AS filas_en_la_secuencia
FROM session_events e
WHERE e.event_type = 'TRIAL_SEQUENCE_GENERATED'
ORDER BY e.id;

\echo ''
\echo '-- Planeados contra arrancados, por bloque.'

WITH plan AS (
    SELECT e.payload ->> 'block_state' AS bloque,
           (e.payload ->> 'trial_count')::int AS planeados
    FROM session_events e WHERE e.event_type = 'TRIAL_SEQUENCE_GENERATED'
),
corridos AS (
    SELECT e.payload ->> 'state' AS bloque, count(*) AS arrancados
    FROM session_events e WHERE e.event_type = 'TRIAL_STARTED' GROUP BY 1
)
SELECT p.bloque, p.planeados, coalesce(c.arrancados, 0) AS arrancados,
       p.planeados - coalesce(c.arrancados, 0)          AS sin_correr
FROM plan p LEFT JOIN corridos c ON c.bloque = p.bloque
ORDER BY p.bloque;

\echo ''
\echo '-- separacion_lograda menor que separacion_pedida significa que el'
\echo '-- generador no pudo respetar el espaciado: la secuencia sirve, pero la'
\echo '-- garantia es mas debil de lo que se pidio.'

\echo ''
\echo '=============================================================='
\echo '9. Resumen'
\echo '=============================================================='

SELECT
    (SELECT count(*) FROM session_events)                                        AS eventos_totales,
    (SELECT count(*) FROM session_events WHERE event_type = 'ENVIRONMENT_APPLIED') AS environment_applied,
    (SELECT count(*) FROM session_events WHERE event_type = 'PERIPHERAL_EVENT')    AS peripheral_event,
    (SELECT count(DISTINCT payload ->> 'esl') FROM session_events)                 AS niveles_esl_distintos,
    (SELECT count(DISTINCT payload ->> 'kanji_id')
       FROM session_events WHERE payload ? 'kanji_id')                            AS kanji_distintos,
    (SELECT count(DISTINCT payload ->> 'trial_id')
       FROM session_events WHERE payload ? 'trial_id')                            AS trials_distintos;

\echo ''
\echo 'Lectura rapida: si niveles_esl_distintos es 1 y ese nivel es OFF, la'
\echo 'corrida no demuestra nada sobre el ESL -- repitela fijando un nivel que'
\echo 'no sea OFF en el Trial Debug Runner.'
\echo ''

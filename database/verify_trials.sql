-- Verificacion del sistema de respuesta (T1/T2/T3) contra los datos grabados.
-- Complementa a verify_events.sql, que comprueba la FORMA del payload; esto
-- comprueba el COMPORTAMIENTO: que cada trial este completo y sea coherente
-- consigo mismo, y que la asistencia concedida coincida con la tabla 9.1 del
-- spec.
--
-- Por que contra la base y no contra el codigo: la matriz de LAL ya se
-- verifico celda por celda contra un modelo del propio C#, y ese chequeo no
-- es independiente -- comparte mi lectura del spec. Esto mira lo que
-- realmente sucedio en una sesion.
--
-- Uso en PowerShell (Windows):
--   Get-Content database\verify_trials.sql | docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr

\set ON_ERROR_STOP on

\echo '=== 0. Trials de la sesion mas reciente ==='
WITH s AS (SELECT id FROM experiment_sessions ORDER BY created_at DESC LIMIT 1)
SELECT
    e.payload ->> 'state'                          AS estado,
    e.payload ->> 'lal'                            AS lal,
    e.payload ->> 'trial_type'                     AS tipo,
    count(*) FILTER (WHERE e.event_type = 'TRIAL_STARTED')    AS iniciados,
    count(*) FILTER (WHERE e.event_type = 'ANSWER_SELECTED')  AS respondidos,
    count(*) FILTER (WHERE e.event_type = 'TRIAL_COMPLETED')  AS cerrados,
    count(*) FILTER (WHERE e.event_type = 'HINT_REQUESTED')   AS hints
FROM session_events e
WHERE e.session_id = (SELECT id FROM s) AND e.payload ? 'trial_id'
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;

\echo ''
\echo '=== 1. INFRACCION: trials incompletos ==='
\echo 'Debe devolver 0 filas. Un TRIAL_STARTED sin su ANSWER_SELECTED y su'
\echo 'TRIAL_COMPLETED es un trial que se abrio y nunca se cerro.'
WITH s AS (SELECT id FROM experiment_sessions ORDER BY created_at DESC LIMIT 1),
     t AS (
       SELECT payload ->> 'trial_id' AS trial_id,
              count(*) FILTER (WHERE event_type = 'TRIAL_STARTED')   AS started,
              count(*) FILTER (WHERE event_type = 'ANSWER_SELECTED') AS answered,
              count(*) FILTER (WHERE event_type = 'TRIAL_COMPLETED') AS completed
       FROM session_events
       WHERE session_id = (SELECT id FROM s) AND payload ? 'trial_id'
       GROUP BY 1)
SELECT * FROM t WHERE started <> 1 OR answered <> 1 OR completed <> 1 ORDER BY trial_id;

\echo ''
\echo '=== 2. INFRACCION: incoherencia dentro del mismo trial ==='
\echo 'Debe devolver 0 filas. ANSWER_SELECTED y TRIAL_COMPLETED tienen que'
\echo 'coincidir en is_correct y en response_time_ms: son dos vistas del mismo'
\echo 'hecho y no pueden discrepar.'
WITH s AS (SELECT id FROM experiment_sessions ORDER BY created_at DESC LIMIT 1),
     a AS (SELECT payload ->> 'trial_id' AS tid,
                  payload ->> 'is_correct' AS ok,
                  payload ->> 'response_time_ms' AS rt,
                  payload ->> 'selected_option' AS sel
           FROM session_events
           WHERE session_id = (SELECT id FROM s) AND event_type = 'ANSWER_SELECTED'),
     c AS (SELECT payload ->> 'trial_id' AS tid,
                  payload ->> 'is_correct' AS ok,
                  payload ->> 'response_time_ms' AS rt,
                  (payload ->> 'hint_count')::int AS hints
           FROM session_events
           WHERE session_id = (SELECT id FROM s) AND event_type = 'TRIAL_COMPLETED'),
     h AS (SELECT payload ->> 'trial_id' AS tid, count(*) AS emitidos
           FROM session_events
           WHERE session_id = (SELECT id FROM s) AND event_type = 'HINT_REQUESTED'
           GROUP BY 1)
SELECT a.tid, a.ok AS ok_answer, c.ok AS ok_completed,
       a.rt AS rt_answer, c.rt AS rt_completed,
       c.hints AS hint_count, COALESCE(h.emitidos, 0) AS hints_emitidos
FROM a JOIN c ON c.tid = a.tid LEFT JOIN h ON h.tid = a.tid
WHERE a.ok <> c.ok OR a.rt <> c.rt OR c.hints <> COALESCE(h.emitidos, 0)
ORDER BY a.tid;

\echo ''
\echo '=== 3. INFRACCION: opciones mal formadas ==='
\echo 'Debe devolver 0 filas. Cuatro opciones exactas (spec 9.3: LAL no puede'
\echo 'cambiar el numero), la correcta entre ellas, y la elegida tambien.'
WITH s AS (SELECT id FROM experiment_sessions ORDER BY created_at DESC LIMIT 1),
     st AS (SELECT payload ->> 'trial_id' AS tid,
                   payload -> 'options' AS opts,
                   payload ->> 'correct_option' AS correct
            FROM session_events
            WHERE session_id = (SELECT id FROM s) AND event_type = 'TRIAL_STARTED'),
     an AS (SELECT payload ->> 'trial_id' AS tid, payload ->> 'selected_option' AS sel
            FROM session_events
            WHERE session_id = (SELECT id FROM s) AND event_type = 'ANSWER_SELECTED')
SELECT st.tid,
       jsonb_array_length(st.opts)                    AS n_opciones,
       NOT (st.opts ? st.correct)                     AS correcta_ausente,
       NOT (st.opts ? an.sel)                         AS elegida_ausente,
       st.opts
FROM st LEFT JOIN an ON an.tid = st.tid
WHERE jsonb_array_length(st.opts) <> 4
   OR NOT (st.opts ? st.correct)
   OR (an.sel IS NOT NULL AND NOT (st.opts ? an.sel))
ORDER BY st.tid;

\echo ''
\echo '=== 4. INFRACCION: audio pre-respuesta en un trial T3 ==='
\echo 'Debe devolver 0 filas. Es la regla dura de spec 5.2 y 9.2: en'
\echo 'Kanji -> Reading la respuesta ES la lectura, asi que el audio la'
\echo 'revelaria. Ningun HINT_REQUESTED de un T3 puede conceder audio.'
WITH s AS (SELECT id FROM experiment_sessions ORDER BY created_at DESC LIMIT 1)
SELECT payload ->> 'trial_id' AS trial_id,
       payload ->> 'lal'      AS lal,
       payload -> 'hint_type' AS cues_concedidos
FROM session_events
WHERE session_id = (SELECT id FROM s)
  AND event_type = 'HINT_REQUESTED'
  AND payload ->> 'trial_type' = 'T3_KANJI_TO_READING'
  AND payload -> 'hint_type' ? 'TARGET_READING_AUDIO'
ORDER BY 1;

\echo ''
\echo '=== 5. INFRACCION: la asistencia concedida no coincide con spec 9.1 ==='
\echo 'Debe devolver 0 filas. Compara los cues realmente concedidos contra la'
\echo 'tabla del spec, transcrita aqui de forma independiente del codigo C#.'
WITH s AS (SELECT id FROM experiment_sessions ORDER BY created_at DESC LIMIT 1),
     -- Array vacio es '[]', no '{}': '{}' es un objeto vacio y
     -- jsonb_array_elements_text sobre un objeto aborta la consulta.
     spec (lal, tipo, esperado) AS (VALUES
       ('OFF',    'T1_MEANING_TO_KANJI',  '[]'::jsonb),
       ('OFF',    'T2_KANJI_TO_MEANING',  '[]'::jsonb),
       ('OFF',    'T3_KANJI_TO_READING',  '[]'::jsonb),
       ('LOW',    'T1_MEANING_TO_KANJI',  '[]'::jsonb),
       ('LOW',    'T2_KANJI_TO_MEANING',  '[]'::jsonb),
       ('LOW',    'T3_KANJI_TO_READING',  '[]'::jsonb),
       ('MEDIUM', 'T1_MEANING_TO_KANJI',  '["TARGET_READING_AUDIO"]'::jsonb),
       ('MEDIUM', 'T2_KANJI_TO_MEANING',  '["TARGET_READING_AUDIO"]'::jsonb),
       ('MEDIUM', 'T3_KANJI_TO_READING',  '["VISUAL_ASSOCIATION"]'::jsonb),
       ('HIGH',   'T1_MEANING_TO_KANJI',  '["TARGET_READING_AUDIO","VISUAL_TRANSFORMATION"]'::jsonb),
       ('HIGH',   'T2_KANJI_TO_MEANING',  '["TARGET_READING_AUDIO","REVERSE_SEMANTIC_ASSOCIATION"]'::jsonb),
       ('HIGH',   'T3_KANJI_TO_READING',  '["VISUAL_ASSOCIATION","VISUAL_TRANSFORMATION"]'::jsonb)
     ),
     -- Los dos lados se ordenan antes de comparar: el orden de los cues en el
     -- payload es de presentacion, no de contenido.
     spec_sorted AS (
       SELECT lal, tipo,
              COALESCE((SELECT jsonb_agg(y ORDER BY y)
                          FROM jsonb_array_elements_text(esperado) AS y), '[]'::jsonb) AS esperado
       FROM spec),
     obs AS (
       SELECT DISTINCT
              payload ->> 'lal'         AS lal,
              payload ->> 'trial_type'  AS tipo,
              COALESCE((SELECT jsonb_agg(x ORDER BY x)
                          FROM jsonb_array_elements_text(payload -> 'hint_type') AS x),
                       '[]'::jsonb)     AS concedido
       FROM session_events
       WHERE session_id = (SELECT id FROM s)
         AND event_type = 'HINT_REQUESTED'
         AND jsonb_typeof(payload -> 'hint_type') = 'array')
SELECT obs.lal, obs.tipo, obs.concedido, spec_sorted.esperado AS segun_spec_9_1
FROM obs JOIN spec_sorted ON spec_sorted.lal = obs.lal AND spec_sorted.tipo = obs.tipo
WHERE obs.concedido <> spec_sorted.esperado
ORDER BY obs.lal, obs.tipo;

\echo ''
\echo '=== 6. Cobertura: que celdas de la matriz 9.1 se han ejercitado ==='
\echo 'Para cerrar la verificacion hacen falta las 9 celdas (o 12 con OFF).'
\echo 'Una celda sin probar no es una celda correcta.'
WITH s AS (SELECT id FROM experiment_sessions ORDER BY created_at DESC LIMIT 1)
SELECT payload ->> 'lal' AS lal, payload ->> 'trial_type' AS tipo, count(*) AS hints
FROM session_events
WHERE session_id = (SELECT id FROM s) AND event_type = 'HINT_REQUESTED'
GROUP BY 1, 2 ORDER BY 1, 2;

\echo ''
\echo '=== 7. Resumen ==='
\echo 'Las cuatro columnas de infracciones deben ser 0.'
WITH s AS (SELECT id FROM experiment_sessions ORDER BY created_at DESC LIMIT 1),
     e AS (SELECT * FROM session_events WHERE session_id = (SELECT id FROM s)),
     t AS (SELECT payload ->> 'trial_id' AS tid,
                  count(*) FILTER (WHERE event_type='TRIAL_STARTED')   AS st,
                  count(*) FILTER (WHERE event_type='ANSWER_SELECTED') AS an,
                  count(*) FILTER (WHERE event_type='TRIAL_COMPLETED') AS co
           FROM e WHERE payload ? 'trial_id' GROUP BY 1)
SELECT
    (SELECT count(*) FROM t)                                        AS trials,
    (SELECT count(*) FROM t WHERE st<>1 OR an<>1 OR co<>1)           AS incompletos,
    (SELECT count(*) FROM e WHERE event_type='TRIAL_STARTED'
       AND jsonb_array_length(payload -> 'options') <> 4)            AS opciones_malas,
    (SELECT count(*) FROM e WHERE event_type='HINT_REQUESTED'
       AND payload ->> 'trial_type' = 'T3_KANJI_TO_READING'
       AND payload -> 'hint_type' ? 'TARGET_READING_AUDIO')          AS audio_en_t3,
    (SELECT count(DISTINCT (payload ->> 'lal', payload ->> 'trial_type'))
       FROM e WHERE event_type='HINT_REQUESTED')                     AS celdas_9_1_cubiertas;

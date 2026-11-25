-- Verificacion del contrato de payload de eventos (v1).
-- Documento normativo: database/EVENT_CONTRACT.md
--
-- Comprueba los payloads que efectivamente llegaron, no el codigo que los
-- mando. Es la comprobacion del criterio de aceptacion 8 de Fase 2: cada
-- evento debe traer su bloque de contexto, y los eventos de trial ademas el
-- bloque de trial, porque son los identificadores que Fase 3 va a usar como
-- llaves foraneas al promover estas filas a tablas relacionales.
--
-- Por que hace falta una consulta y no basta con revisar el codigo: la
-- columna `payload` es JSONB y acepta cualquier cosa sin protestar. El paso 0
-- de esta fase encontro dos contratos que el codigo afirmaba cumplir y no
-- cumplia, y ninguno de los dos dio error.
--
-- Uso en PowerShell (Windows):
--   Get-Content database\verify_events.sql | docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr
--
-- Uso en bash / Git Bash:
--   docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr < database/verify_events.sql

\set ON_ERROR_STOP on

\echo '=== 0. Sesion evaluada (la mas reciente) ==='
SELECT id, condition, status, current_state, created_at
FROM experiment_sessions
ORDER BY created_at DESC
LIMIT 1;

\echo ''
\echo '=== 1. Distribucion de event_type en esa sesion ==='
SELECT
    e.event_type,
    count(*)                                        AS eventos,
    count(*) FILTER (WHERE e.payload ? 'trial_id')  AS con_trial
FROM session_events e
WHERE e.session_id = (SELECT id FROM experiment_sessions ORDER BY created_at DESC LIMIT 1)
GROUP BY e.event_type
ORDER BY eventos DESC;

\echo ''
\echo '=== 2. INFRACCION: eventos sin bloque de contexto completo ==='
\echo 'Debe devolver 0 filas. Todo evento lleva schema_version, state,'
\echo 'session_elapsed_ms, esl y lal -- sin excepcion.'
SELECT
    e.id,
    e.event_type,
    NOT (e.payload ? 'schema_version')      AS falta_schema_version,
    NOT (e.payload ? 'state')               AS falta_state,
    NOT (e.payload ? 'session_elapsed_ms')  AS falta_elapsed,
    NOT (e.payload ? 'esl')                 AS falta_esl,
    NOT (e.payload ? 'lal')                 AS falta_lal,
    e.payload
FROM session_events e
WHERE e.session_id = (SELECT id FROM experiment_sessions ORDER BY created_at DESC LIMIT 1)
  AND NOT (e.payload ?& array['schema_version', 'state', 'session_elapsed_ms', 'esl', 'lal'])
ORDER BY e.id;

\echo ''
\echo '=== 3. INFRACCION: eventos de trial sin bloque de trial completo ==='
\echo 'Debe devolver 0 filas. Un evento de trial sin trial_id es exactamente'
\echo 'la fila que Fase 3 no va a poder migrar.'
SELECT
    e.id,
    e.event_type,
    NOT (e.payload ? 'trial_id')        AS falta_trial_id,
    NOT (e.payload ? 'trial_type')      AS falta_trial_type,
    NOT (e.payload ? 'trial_sequence')  AS falta_trial_sequence,
    NOT (e.payload ? 'kanji_id')        AS falta_kanji_id,
    e.payload
FROM session_events e
WHERE e.session_id = (SELECT id FROM experiment_sessions ORDER BY created_at DESC LIMIT 1)
  AND e.event_type IN ('TRIAL_STARTED', 'ANSWER_SELECTED', 'HINT_REQUESTED', 'TRIAL_COMPLETED')
  AND NOT (e.payload ?& array['trial_id', 'trial_type', 'trial_sequence', 'kanji_id'])
ORDER BY e.id;

\echo ''
\echo '=== 4. INFRACCION: session_elapsed_ms sin instante cero ==='
\echo 'Debe devolver 0 filas. Un -1 significa que SessionBootstrap no instalo'
\echo 'el session_clock_started_at, y esos eventos no se pueden alinear con'
\echo 'ventanas de EEG en Fase 4.'
-- El CASE no es adorno: sin el, un session_elapsed_ms que llegara como texto
-- reventaria el cast a bigint y abortaria el script entero (ON_ERROR_STOP).
-- Postgres no garantiza el orden de evaluacion de un OR, pero si el de un CASE.
SELECT
    e.id,
    e.event_type,
    jsonb_typeof(e.payload -> 'session_elapsed_ms') AS tipo,
    e.payload ->> 'session_elapsed_ms'              AS elapsed
FROM session_events e
WHERE e.session_id = (SELECT id FROM experiment_sessions ORDER BY created_at DESC LIMIT 1)
  AND e.payload ? 'session_elapsed_ms'
  AND CASE WHEN jsonb_typeof(e.payload -> 'session_elapsed_ms') = 'number'
           THEN (e.payload ->> 'session_elapsed_ms')::bigint < 0
           ELSE true END
ORDER BY e.id;

\echo ''
\echo '=== 5. INFRACCION: session_elapsed_ms no cuadra con el reloj del servidor ==='
\echo 'Debe devolver 0 filas. Compara el elapsed que reporta Unity contra el que'
\echo 'se deduce de los timestamps del backend. Detecta el caso que la consulta 4'
\echo 'NO detecta: un cero de sesion desplazado por zona horaria da un elapsed'
\echo 'positivo y plausible en apariencia -- 32400000 ms son las nueve horas de'
\echo 'JST -- y pasaria el filtro de "no es -1" sin problema.'
\echo 'Tolerancia 5 s: cubre latencia de red y encolado, no un error de zona.'
SELECT
    e.id,
    e.event_type,
    (e.payload ->> 'session_elapsed_ms')::bigint AS elapsed_reportado,
    round(EXTRACT(EPOCH FROM (e.server_received_at - s.session_clock_started_at)) * 1000)
        AS elapsed_segun_servidor,
    round(EXTRACT(EPOCH FROM (e.server_received_at - s.session_clock_started_at)) * 1000)
        - (e.payload ->> 'session_elapsed_ms')::bigint AS diferencia_ms
FROM session_events e
JOIN experiment_sessions s ON s.id = e.session_id
WHERE e.session_id = (SELECT id FROM experiment_sessions ORDER BY created_at DESC LIMIT 1)
  AND s.session_clock_started_at IS NOT NULL
  AND jsonb_typeof(e.payload -> 'session_elapsed_ms') = 'number'
  AND abs(round(EXTRACT(EPOCH FROM (e.server_received_at - s.session_clock_started_at)) * 1000)
          - (e.payload ->> 'session_elapsed_ms')::bigint) > 5000
ORDER BY e.id;

\echo ''
\echo '=== 6. INFRACCION: valores de enum que no son el valor de cable ==='
\echo 'Debe devolver 0 filas. Los estados van en SCREAMING_SNAKE_CASE, no con'
\echo 'el nombre del miembro de C# -- es el bug corregido el 7 de septiembre.'
SELECT e.id, e.event_type, e.payload ->> 'state' AS state_reportado
FROM session_events e
WHERE e.session_id = (SELECT id FROM experiment_sessions ORDER BY created_at DESC LIMIT 1)
  AND e.payload ? 'state'
  AND (e.payload ->> 'state') !~ '^S[0-9]+(_[A-Z]+)+$'
ORDER BY e.id;

\echo ''
\echo '=== 7. Versiones de contrato presentes ==='
\echo 'Varias versiones a la vez no es un error, pero Fase 3 tiene que'
\echo 'contemplarlas todas al migrar.'
SELECT
    e.payload ->> 'schema_version' AS schema_version,
    count(*)                       AS eventos,
    min(e.server_received_at)      AS desde,
    max(e.server_received_at)      AS hasta
FROM session_events e
WHERE e.payload ? 'schema_version'
GROUP BY 1
ORDER BY 1;

\echo ''
\echo '=== 8. Resumen del criterio de aceptacion 8 ==='
\echo 'Las cuatro columnas de infracciones deben ser 0.'
WITH s AS (SELECT * FROM experiment_sessions ORDER BY created_at DESC LIMIT 1),
     e AS (SELECT * FROM session_events WHERE session_id = (SELECT id FROM s))
SELECT
    (SELECT count(*) FROM e)                                       AS eventos_totales,
    (SELECT count(*) FROM e
      WHERE NOT (payload ?& array['schema_version','state',
                                  'session_elapsed_ms','esl','lal']))  AS sin_contexto,
    (SELECT count(*) FROM e
      WHERE event_type IN ('TRIAL_STARTED','ANSWER_SELECTED',
                           'HINT_REQUESTED','TRIAL_COMPLETED')
        AND NOT (payload ?& array['trial_id','trial_type',
                                  'trial_sequence','kanji_id']))       AS sin_trial,
    (SELECT count(*) FROM e
      WHERE payload ? 'session_elapsed_ms'
        AND CASE WHEN jsonb_typeof(payload -> 'session_elapsed_ms') = 'number'
                 THEN (payload ->> 'session_elapsed_ms')::bigint < 0
                 ELSE true END)                                        AS sin_reloj,
    (SELECT count(*) FROM e
      WHERE (SELECT session_clock_started_at FROM s) IS NOT NULL
        AND jsonb_typeof(payload -> 'session_elapsed_ms') = 'number'
        AND abs(round(EXTRACT(EPOCH FROM (server_received_at
              - (SELECT session_clock_started_at FROM s))) * 1000)
              - (payload ->> 'session_elapsed_ms')::bigint) > 5000)     AS reloj_desfasado;

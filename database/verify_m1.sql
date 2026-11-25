-- Verificacion del criterio de salida de M1 (Technical Feasibility).
--
-- Comprueba que el round trip Unity -> WebSocket -> backend -> PostgreSQL
-- funciono: que la sesion existe, que llego el STATE_ENTERED, y -- lo mas
-- importante -- que su payload viene lleno y no vacio.
--
-- Uso en PowerShell (Windows)
--
--   Get-Content database\verify_m1.sql | docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr
--
-- Uso en bash / Git Bash:
--
--   docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr < database/verify_m1.sql
--
-- En pgAdmin (http://localhost:8081): abrir el Query Tool sobre la base
-- neuroadaptive_vr y pegar SOLO las sentencias SELECT. Las lineas que
-- empiezan con \echo son meta-comandos de psql; pgAdmin no las entiende
-- y va a marcar error de sintaxis.
--
-- NOTA (7 sep 2026, paso 0 de Fase 2): las consultas 2 y 3 referenciaban
-- una columna `server_timestamp` que nunca existio. La columna real de
-- session_events se llama `server_received_at` -- asi esta en
-- app/models/system_event.py, en database/schema.sql y en la migracion
-- alembic 0001_initial_schema. Con el nombre viejo, este script fallaba
-- con "column does not exist" justo en la consulta 3, que es la evidencia
-- de cierre de M1.
--
-- En la misma pasada se corrigio el calculo del offset. Decia
-- EXTRACT(MILLISECOND FROM (server - client)), que en Postgres devuelve
-- solo el campo de segundos+milisegundos del intervalo: descarta minutos
-- y horas sin avisar. Un desfase de 1 min 200 ms se reportaba como 200.
-- EXTRACT(EPOCH FROM ...) * 1000 si da el total real en milisegundos.

\echo '=== 1. Ultimas sesiones creadas ==='
SELECT id, condition, status, current_state, visit_number, created_at
FROM experiment_sessions
ORDER BY created_at DESC
LIMIT 5;

\echo ''
\echo '=== 2. Eventos de sesion recientes ==='
SELECT id, event_type, payload, client_timestamp, server_received_at
FROM session_events
ORDER BY id DESC
LIMIT 10;

\echo ''
\echo '=== 3. CRITERIO DE SALIDA M1 ==='
\echo 'Debe devolver al menos una fila con payload_ok = true.'
\echo 'payload_ok = false significa que el evento llego pero con payload vacio,'
\echo 'que era el bug del protocolo (payload_json vs payload).'
SELECT
    id,
    event_type,
    payload,
    (payload ? 'state')                    AS payload_ok,
    payload ->> 'state'                    AS estado_reportado,
    client_timestamp,
    server_received_at,
    EXTRACT(EPOCH FROM (server_received_at - client_timestamp)) * 1000
        AS offset_aprox_ms
FROM session_events
WHERE event_type = 'STATE_ENTERED'
ORDER BY id DESC
LIMIT 5;

\echo ''
\echo '=== 4. Eventos de validacion tecnica (S3) ==='
SELECT component, status, detail, created_at
FROM system_validation_events
ORDER BY created_at DESC
LIMIT 5;

\echo ''
\echo '=== 5. Resumen ==='
SELECT
    (SELECT count(*) FROM participants)              AS participantes,
    (SELECT count(*) FROM experiment_sessions)       AS sesiones,
    (SELECT count(*) FROM session_events)            AS eventos_sesion,
    (SELECT count(*) FROM system_validation_events)  AS eventos_validacion,
    (SELECT count(*) FROM session_events
      WHERE event_type = 'STATE_ENTERED'
        AND payload ? 'state')                       AS state_entered_con_payload;

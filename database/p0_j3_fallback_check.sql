-- p0_j3_fallback_check.sql -- J3 (D-F6-174), one real fallback per session. Read only. Works offline.
-- PowerShell, repo root:
--   Get-Content database\p0_j3_fallback_check.sql | docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr -v sid=<id prefix>

\echo '== A - Heartbeat: run it DURING S7, after the cut. Expected age_s < 10 (live.py alive); eeg_gap_ms grows after the cut'
SELECT left(session_id::text, 8) AS session, heartbeat_at,
       round(EXTRACT(EPOCH FROM now() - heartbeat_at)::numeric, 1) AS age_s, eeg_gap_ms
FROM eeg_sessions WHERE session_id::text LIKE :'sid' || '%';

\echo '== B - EEG_STATUS events. Expected: CONNECTED ... then LOST after the cut; never PROCESS_DOWN'
SELECT e.id, e.payload ->> 'status' AS status, (e.payload ->> 'session_elapsed_ms')::int AS elapsed_ms,
       e.payload ->> 'eeg_gap_ms' AS gap_ms, e.payload ->> 'heartbeat_age_s' AS hb_age_s, e.payload ->> 'source' AS source
FROM session_events e
WHERE e.event_type = 'EEG_STATUS' AND e.session_id::text LIKE :'sid' || '%' ORDER BY e.id;

\echo '== C - S7 decisions. Expected: before the cut at least one eeg_counted t; after it eeg_counted f with a fallback, and the session goes on'
SELECT d.trial_sequence AS seq, d.decided_elapsed_ms AS elapsed_ms, d.action, d.reason_code,
       d.eeg_counted, d.eeg_effect, e.payload -> 'eeg' ->> 'fallback' AS fallback, d.decision_latency_ms AS latency_ms
FROM adaptation_decisions d JOIN session_events e ON e.id = d.source_event_id
WHERE d.session_id::text LIKE :'sid' || '%' ORDER BY d.decided_elapsed_ms;

\echo '== D - Session: expected COMPLETED (or still running) with condition MULTIMODAL_ADAPTIVE'
SELECT left(id::text, 8) AS session, condition, status, current_state, completed_at
FROM experiment_sessions WHERE id::text LIKE :'sid' || '%';

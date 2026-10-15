-- F5a loop check for the latest BEHAVIOR_ADAPTIVE session: its live decisions
-- (ADAPTATION_DECISION, written by the backend), what Unity did with them,
-- the D9 cues per S7 trial and the O4 outcomes.
-- Run: docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr < database/check_loop.sql

\echo '== Latest adaptive session'
SELECT id, condition, created_at
FROM experiment_sessions
WHERE condition = 'BEHAVIOR_ADAPTIVE'
ORDER BY created_at DESC LIMIT 1;

\echo '== Live decisions (one per S7 answer)'
WITH s AS (SELECT id FROM experiment_sessions WHERE condition = 'BEHAVIOR_ADAPTIVE'
           ORDER BY created_at DESC LIMIT 1)
SELECT e.payload->>'trial_id'            AS trial,
       e.payload->>'learner_state'       AS state,
       e.payload->>'cause'               AS cause,
       e.payload->>'confidence'          AS conf,
       e.payload->>'action'              AS action,
       e.payload->>'from_level'          AS from_lvl,
       e.payload->>'to_level'            AS to_lvl,
       e.payload->>'reason_code'         AS reason,
       e.payload->>'decision_latency_ms' AS latency_ms
FROM session_events e JOIN s ON e.session_id = s.id
WHERE e.event_type = 'ADAPTATION_DECISION'
ORDER BY e.id;

\echo '== Applied / skipped in Unity'
WITH s AS (SELECT id FROM experiment_sessions WHERE condition = 'BEHAVIOR_ADAPTIVE'
           ORDER BY created_at DESC LIMIT 1)
SELECT e.event_type,
       e.payload->>'decision_trial_id'       AS decided_at,
       e.payload->>'applied_before_trial_id' AS before_trial,
       e.payload->>'dimension'               AS dim,
       e.payload->>'from_level'              AS from_lvl,
       e.payload->>'to_level'                AS to_lvl,
       e.payload->>'reason'                  AS skip_reason,
       e.payload->>'waited_ms'               AS waited_ms
FROM session_events e JOIN s ON e.session_id = s.id
WHERE e.event_type IN ('ADAPTATION_APPLIED', 'ADAPTATION_SKIPPED')
ORDER BY e.id;

\echo '== Cues per S7 trial (D9)'
WITH s AS (SELECT id FROM experiment_sessions WHERE condition = 'BEHAVIOR_ADAPTIVE'
           ORDER BY created_at DESC LIMIT 1)
SELECT e.payload->>'trial_id'        AS trial,
       e.payload->>'lal'             AS lal,
       e.payload->>'cue_trigger'     AS cue_trigger,
       e.payload->>'proactive_index' AS proactive_idx,
       e.payload->>'hint_count'      AS hints,
       e.payload->'cues_presented'   AS cues
FROM session_events e JOIN s ON e.session_id = s.id
WHERE e.event_type = 'TRIAL_COMPLETED' AND e.payload->>'trial_id' LIKE 'S7-%'
ORDER BY e.id;

\echo '== Outcomes (O4: the 3 cooldown trials after each change)'
WITH s AS (SELECT id FROM experiment_sessions WHERE condition = 'BEHAVIOR_ADAPTIVE'
           ORDER BY created_at DESC LIMIT 1)
SELECT e.payload->>'decision_trial_id'    AS decided_at,
       e.payload->'pre'->>'state'          AS pre_state,
       e.payload->'post'->>'state'         AS post_state,
       e.payload->>'outcome'               AS outcome,
       e.payload->>'outcome_reason'        AS reason,
       e.payload->>'outcome_explanation'   AS explanation
FROM session_events e JOIN s ON e.session_id = s.id
WHERE e.event_type = 'ADAPTATION_OUTCOME'
ORDER BY e.id;

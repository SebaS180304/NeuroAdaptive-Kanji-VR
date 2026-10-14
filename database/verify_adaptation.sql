-- verify_adaptation.sql -- F5a adaptation loop (migration 0003)
-- Planteamiento_Tecnico_F5a.md §8.3 and Plan_Fase5a.md §5 (criteria 3, 4, 5, 11, 12).
-- Read only. Every check prints rows only when something is wrong, except the
-- summaries (sections 1 and 6).
--
-- Usage (PowerShell, repo root):
--   Get-Content database\verify_adaptation.sql | docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr
-- One session only: add  -v sid=<id prefix>  (default: every session since 13 Oct).

\if :{?sid}
\else
\set sid ''
\endif

CREATE TEMP VIEW target AS
SELECT s.id, s.condition FROM experiment_sessions s
WHERE (:'sid' <> '' AND s.id::text LIKE :'sid' || '%')
   OR (:'sid' = ''  AND s.created_at >= TIMESTAMPTZ '2026-10-13 00:00+09');

\echo '== 1 · Summary per session'
SELECT left(t.id::text, 8) AS session, t.condition,
       (SELECT count(*) FROM trials x WHERE x.session_id = t.id
          AND x.block_state = 'S7_EXPERIMENTAL_RETRIEVAL' AND x.answered_elapsed_ms IS NOT NULL) AS s7_answered,
       (SELECT count(*) FROM adaptation_decisions d WHERE d.session_id = t.id) AS decisions,
       (SELECT count(*) FROM adaptation_decisions d WHERE d.session_id = t.id AND d.action <> 'NO_CHANGE') AS changes,
       (SELECT count(*) FROM adaptation_applications a WHERE a.session_id = t.id AND a.result = 'APPLIED') AS applied,
       (SELECT count(*) FROM adaptation_applications a WHERE a.session_id = t.id AND a.result = 'SKIPPED') AS skipped,
       (SELECT count(*) FROM trials x WHERE x.session_id = t.id AND x.cue_trigger = 'PROACTIVE') AS proactive_trials
FROM target t ORDER BY 1;

\echo '== 2 · STATIC never adapts (criterion 5): expected no rows'
SELECT left(t.id::text, 8) AS session, 'decision' AS what, d.trial_id FROM target t
JOIN adaptation_decisions d ON d.session_id = t.id WHERE t.condition = 'STATIC'
UNION ALL
SELECT left(t.id::text, 8), 'application', a.decision_trial_id FROM target t
JOIN adaptation_applications a ON a.session_id = t.id WHERE t.condition = 'STATIC'
UNION ALL
SELECT left(t.id::text, 8), 'proactive cue', x.trial_id FROM target t
JOIN trials x ON x.session_id = t.id WHERE t.condition = 'STATIC' AND x.cue_trigger = 'PROACTIVE';

\echo '== 3 · Adaptive S7: one decision per answered trial: expected no rows'
SELECT left(t.id::text, 8) AS session, x.trial_id, 'answered without decision' AS problem
FROM target t JOIN trials x ON x.session_id = t.id
WHERE t.condition <> 'STATIC' AND x.block_state = 'S7_EXPERIMENTAL_RETRIEVAL'
  AND x.answered_elapsed_ms IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM adaptation_decisions d WHERE d.session_id = t.id AND d.trial_id = x.trial_id);

\echo '== 4 · Every APPLIED has its change decision, and lands between trials (criterion 3): expected no rows'
SELECT left(a.session_id::text, 8) AS session, a.decision_trial_id, a.applied_before_trial_id,
       CASE
         WHEN d.decision_id IS NULL THEN 'no decision with that decision_id'
         WHEN d.action = 'NO_CHANGE' THEN 'applied a NO_CHANGE'
         WHEN d.to_level IS DISTINCT FROM a.to_level THEN 'applied level differs from the decision'
         WHEN a.elapsed_ms < closed.completed_elapsed_ms THEN 'applied before its trial closed'
         WHEN a.elapsed_ms > nxt.started_elapsed_ms THEN 'applied after the next trial started'
       END AS problem
FROM adaptation_applications a
JOIN target t ON t.id = a.session_id
LEFT JOIN adaptation_decisions d ON d.session_id = a.session_id AND d.decision_id = a.decision_id
LEFT JOIN trials closed ON closed.session_id = a.session_id AND closed.trial_id = a.decision_trial_id
LEFT JOIN trials nxt    ON nxt.session_id = a.session_id AND nxt.trial_id = a.applied_before_trial_id
WHERE a.result = 'APPLIED'
  AND (d.decision_id IS NULL OR d.action = 'NO_CHANGE' OR d.to_level IS DISTINCT FROM a.to_level
       OR a.elapsed_ms < closed.completed_elapsed_ms OR a.elapsed_ms > nxt.started_elapsed_ms);

\echo '== 5 · Changes without an APPLIED row (skipped, pending or lost)'
SELECT left(v.session_id::text, 8) AS session, v.trial_id, v.action, v.from_level, v.to_level,
       v.unity_result, v.skip_reason
FROM v_adaptations v JOIN target t ON t.id = v.session_id
WHERE v.action <> 'NO_CHANGE' AND v.unity_result IS DISTINCT FROM 'APPLIED'
ORDER BY 1, 2;

\echo '== 6 · Latency (criterion 12): backend decision and Unity wait, ms'
SELECT left(t.id::text, 8) AS session, count(d.*) AS decisions,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY d.decision_latency_ms)::numeric, 1) AS decision_p50,
       round(percentile_cont(0.95) WITHIN GROUP (ORDER BY d.decision_latency_ms)::numeric, 1) AS decision_p95,
       round(max(d.decision_latency_ms)::numeric, 1) AS decision_max,
       (SELECT max(a.waited_ms) FROM adaptation_applications a WHERE a.session_id = t.id) AS unity_wait_max,
       (SELECT count(*) FROM adaptation_applications a WHERE a.session_id = t.id AND a.skip_reason = 'TIMEOUT') AS timeouts
FROM target t JOIN adaptation_decisions d ON d.session_id = t.id
GROUP BY t.id ORDER BY 1;

\echo '== 7 · D9: PROACTIVE only in the 3 trials after an applied LAL raise, indexed 1..3 (criterion 11): expected no rows'
WITH raises AS (
    SELECT a.session_id, x.trial_sequence AS first_seq
    FROM adaptation_applications a
    JOIN trials x ON x.session_id = a.session_id AND x.trial_id = a.applied_before_trial_id
    WHERE a.result = 'APPLIED' AND a.dimension = 'LAL' AND a.proactive_cues
),
expected AS (
    SELECT r.session_id, r.first_seq + k - 1 AS seq, k AS idx
    FROM raises r CROSS JOIN generate_series(1, 3) k
)
SELECT left(x.session_id::text, 8) AS session, x.trial_id, x.cue_trigger, x.proactive_index,
       e.idx AS expected_index
FROM trials x
JOIN target t ON t.id = x.session_id
LEFT JOIN expected e ON e.session_id = x.session_id AND e.seq = x.trial_sequence
WHERE x.block_state = 'S7_EXPERIMENTAL_RETRIEVAL' AND x.completed_event_id IS NOT NULL
  AND x.contract_version IS NOT NULL
  AND ((x.cue_trigger IS NOT DISTINCT FROM 'PROACTIVE') <> (e.idx IS NOT NULL)
       OR x.proactive_index IS DISTINCT FROM e.idx)
  -- trials closed before the D9 fields existed carry no cue_trigger at all
  AND EXISTS (SELECT 1 FROM trials y WHERE y.session_id = x.session_id AND y.cue_trigger IS NOT NULL
              UNION ALL SELECT 1 FROM raises r WHERE r.session_id = x.session_id);

\echo '== 8 · Open projection errors of the 0003 event types: expected no rows'
SELECT left(p.session_id::text, 8) AS session, p.event_type, p.error_code, count(*) AS n, min(p.detail) AS example
FROM projection_errors p JOIN target t ON t.id = p.session_id
WHERE p.resolved_at IS NULL
  AND p.event_type IN ('DISTRACTOR_INTERACTION', 'ADAPTATION_DECISION', 'ADAPTATION_APPLIED',
                       'ADAPTATION_SKIPPED', 'ADAPTATION_OUTCOME', 'ANSWER_SELECTED', 'TRIAL_COMPLETED')
GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;

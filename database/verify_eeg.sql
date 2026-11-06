-- verify_eeg.sql -- F4 S2: a session recorded with the AURA cap (migrations 0010-0012)
-- Planteamiento_Tecnico_F4.md §2-§4; D-F6-127 (P7, P9, A-7), D-F6-149 (rule B), D-F6-156, D-F6-157, D-F6-159.
-- Read only. One block per check; each says what it expects.
--
-- Usage (PowerShell, repo root):
--   Get-Content database\verify_eeg.sql | docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr -v sid=<id prefix>
-- Without -v sid: every session that has an eeg_sessions row.

\if :{?sid}
\else
\set sid ''
\endif

CREATE TEMP VIEW target AS
SELECT s.id, s.condition, s.status, e.*
FROM experiment_sessions s JOIN eeg_sessions e ON e.session_id = s.id
WHERE :'sid' = '' OR s.id::text LIKE :'sid' || '%';

\echo '== 1 · XDF, both streams (P9) and the epochs rule (D-F6-156): expected xdf, AURA and UnityMarkers t, sound_s 0.5'
SELECT left(t.id::text, 8) AS session, t.condition, t.status,
       t.xdf_path IS NOT NULL AS xdf, t.stream_info ? 'AURA' AS aura, t.stream_info ? 'UnityMarkers' AS markers,
       t.filter_params ->> 'sound_s' AS sound_s, t.filter_params ->> 'epochs_version' AS epochs_rule,
       (SELECT count(*) FROM eeg_epochs p WHERE p.session_id = t.id) AS epochs
FROM target t ORDER BY 1;

\echo '== 2 · Sync (F4 §2.4, D-F6-157): |offset| <= 100 ms and |drift| < 50 ms, or empty with its reason'
SELECT left(t.id::text, 8) AS session, t.sync_offset_ms AS offset_ms, t.sync_drift_ms AS drift_ms,
       CASE WHEN t.sync_offset_ms IS NULL THEN 'n/a'
            WHEN abs(t.sync_offset_ms) <= 100 THEN 'ok' ELSE 'OUT' END AS offset_check,
       CASE WHEN t.sync_drift_ms IS NULL THEN 'n/a'
            WHEN abs(t.sync_drift_ms) < 50 THEN 'ok' ELSE 'OUT' END AS drift_check,
       (SELECT count(*) FROM jsonb_array_elements(t.sync_detail -> 'taps') x WHERE (x ->> 'valid')::boolean) AS clear_taps,
       jsonb_array_length(coalesce(t.sync_detail -> 'taps', '[]')) AS taps,
       coalesce(t.sync_detail ->> 'reason', CASE WHEN t.sync_detail IS NULL THEN 'sync.py not run' END) AS reason
FROM target t ORDER BY 1;

\echo '== 3 · S4 alpha (D-F6-155): expected passed t'
SELECT left(t.id::text, 8) AS session, t.alpha_ratio, t.alpha_passed AS passed, t.not_counted_reason
FROM target t ORDER BY 1;

\echo '== 4 · S6 (A-7): expected >= 6 non-POOR epochs'
SELECT left(t.id::text, 8) AS session,
       count(p.*) FILTER (WHERE p.quality <> 'POOR') AS s6_non_poor, count(p.*) AS s6_epochs,
       CASE WHEN count(p.*) FILTER (WHERE p.quality <> 'POOR') >= 6 THEN 'ok' ELSE 'SHORT' END AS check
FROM target t LEFT JOIN eeg_epochs p ON p.session_id = t.id AND p.game_state = 'S6_GUIDED_PRACTICE_CALIBRATION'
GROUP BY t.id ORDER BY 1;

-- P7 (D-F6-127): the EEG counts in a decision window with >= 2 non-POOR epochs and >= 5 s of clean chunks,
-- each second once. Window = 3 consecutive S7 trials, sliding, from the first one's start to the last one's
-- end; an epoch is in it when it lies entirely inside. Without the "last 15 s" of D-F6-151 (window.py, Mon 9),
-- so it compares with the EEG chat's 5 Nov figures (b5bcf5bd, rule B: 61 %).
CREATE TEMP VIEW s7_windows AS
SELECT w.*,
       (SELECT count(*) FROM eeg_epochs p WHERE p.session_id = w.session_id AND p.quality <> 'POOR'
          AND p.start_ms >= w.lo AND p.end_ms <= w.hi) AS non_poor,
       (SELECT coalesce(sum(upper(r) - lower(r)), 0) / 1000.0 FROM unnest((
          SELECT range_agg(int4range(p.start_ms + (k - 1) * 1000, p.start_ms + k * 1000))
          FROM eeg_epochs p, generate_subscripts(p.chunk_clean, 1) k
          WHERE p.session_id = w.session_id AND p.chunk_clean[k] AND p.start_ms >= w.lo AND p.end_ms <= w.hi)) r) AS clean_s
FROM (SELECT x.session_id, x.trial_id,
             lag(x.started_elapsed_ms, 2) OVER o AS lo, x.completed_elapsed_ms AS hi
      FROM trials x JOIN target t ON t.id = x.session_id
      WHERE x.block_state = 'S7_EXPERIMENTAL_RETRIEVAL'
      WINDOW o AS (PARTITION BY x.session_id ORDER BY x.started_elapsed_ms)) w
WHERE w.lo IS NOT NULL AND w.hi IS NOT NULL;

\echo '== 5 · S7 windows where the EEG counts (P7; A-7 asks >= 60 %)'
SELECT left(t.id::text, 8) AS session, count(w.*) AS windows,
       count(w.*) FILTER (WHERE w.non_poor >= 2 AND w.clean_s >= 5) AS eeg_counts,
       round(100.0 * count(w.*) FILTER (WHERE w.non_poor >= 2 AND w.clean_s >= 5) / nullif(count(w.*), 0)) AS pct,
       CASE WHEN count(w.*) = 0 THEN 'n/a'
            WHEN count(w.*) FILTER (WHERE w.non_poor >= 2 AND w.clean_s >= 5) >= 0.6 * count(w.*) THEN 'ok'
            ELSE 'SHORT' END AS check
FROM target t LEFT JOIN s7_windows w ON w.session_id = t.id
GROUP BY t.id ORDER BY 1;

\echo '== 6 · Usable epochs per ESL level and state (information)'
SELECT left(t.id::text, 8) AS session, p.game_state, p.esl_level,
       count(*) FILTER (WHERE p.quality <> 'POOR') AS non_poor, count(*) AS epochs,
       round(100.0 * count(*) FILTER (WHERE p.quality <> 'POOR') / count(*)) AS pct
FROM target t JOIN eeg_epochs p ON p.session_id = t.id
GROUP BY t.id, p.game_state, p.esl_level ORDER BY 1, 2, 3;

\echo '== 7 · A-7, multimodal session valid: S4 alpha passes AND S7 P7 >= 60 % AND S6 >= 6 non-POOR'
SELECT left(t.id::text, 8) AS session,
       CASE WHEN t.alpha_passed IS NULL OR w.windows = 0 THEN 'n/a'
            WHEN t.alpha_passed AND w.counts >= 0.6 * w.windows AND s6.n >= 6 THEN 'VALID'
            ELSE 'NOT VALID' END AS a7,
       t.alpha_passed AS s4_alpha, w.counts || '/' || w.windows AS s7_p7, s6.n AS s6_non_poor
FROM target t
CROSS JOIN LATERAL (SELECT count(*) AS windows, count(*) FILTER (WHERE non_poor >= 2 AND clean_s >= 5) AS counts
                    FROM s7_windows WHERE session_id = t.id) w
CROSS JOIN LATERAL (SELECT count(*) AS n FROM eeg_epochs p WHERE p.session_id = t.id
                    AND p.game_state = 'S6_GUIDED_PRACTICE_CALIBRATION' AND p.quality <> 'POOR') s6
ORDER BY 1;

\echo '== 8 · FRAME_HITCH per state: n/a here. It travels only in the XDF (UnityMarkers), not in the database;'
\echo '       epochs.py already drops the chunks of every hitch > 100 ms (D-F6-129).'

-- verify_assembly_v1.sql -- guided assembly telemetry (spec 5.3, decisions
-- D2/D4), over the schema v1 tables (F3.4). Same checks as
-- verify_assembly.sql (JSONB events); both are kept until Phase 3 closes.
--
-- Checks the MOST RECENT session, like the other verify_*.sql. The session
-- must be projected (live in the backend, or SELECT project_session('<uuid>')).
--
-- Usage (PowerShell, repo root):
--   Get-Content database\verify_assembly_v1.sql | docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr
--
-- Queries 0 and 3 are the checks: any row they return is an error.
-- Difference with the JSONB version: attempts and closures are matched by
-- exposure_index (0 = the S2 example), not by kanji_id, so a kanji
-- assembled twice cannot hide a miscount.

\set ON_ERROR_STOP on

CREATE TEMP VIEW s AS
SELECT id FROM experiment_sessions ORDER BY created_at DESC LIMIT 1;

-- 0. CHECK: assembly and exposure events that did not project
SELECT event_id, event_type, error_code, detail
FROM projection_errors
WHERE session_id = (SELECT id FROM s) AND resolved_at IS NULL
  AND event_type IN ('ASSEMBLY_SEGMENT_PLACED', 'ASSEMBLY_COMPLETED', 'KANJI_EXPOSED')
ORDER BY event_id;

-- 1. One row per placement attempt (right and wrong)
SELECT exposure_index AS exp, kanji_id AS kanji, attempt, slot_index AS slot,
       segment_id AS segment, expected_segment_id AS expected, is_correct AS ok,
       hint_shown AS hint, selected_ms AS sel_ms, placed_ms
FROM assembly_attempts
WHERE session_id = (SELECT id FROM s)
ORDER BY exposure_index, attempt;

-- 2. Closures: the S2 example (exp 0) plus one per kanji of the set
SELECT exposure_index AS exp, state, kanji_id AS kanji, duration_ms AS dur_ms,
       incorrect_attempts AS wrong, segment_count AS segs, segments_placed AS placed,
       hints_shown AS hints, row_order, forced_by_researcher AS forced
FROM assemblies
WHERE session_id = (SELECT id FROM s)
ORDER BY exposure_index;

-- 3. CHECK: incorrect_attempts == wrong placements, segment_count == right
--    placements (unless forced by the researcher), same kanji on both sides
WITH placed AS (
  SELECT exposure_index, min(kanji_id) AS kanji, count(DISTINCT kanji_id) AS kanjis,
         count(*) FILTER (WHERE NOT is_correct) AS wrong,
         count(*) FILTER (WHERE is_correct)     AS right
  FROM assembly_attempts WHERE session_id = (SELECT id FROM s)
  GROUP BY 1)
SELECT d.exposure_index AS exp, d.kanji_id AS kanji, p.kanji AS placed_kanji,
       d.incorrect_attempts AS completed_wrong, p.wrong AS placed_wrong,
       d.segment_count AS segs, p.right AS placed_right, d.forced_by_researcher AS forced
FROM assemblies d LEFT JOIN placed p USING (exposure_index)
WHERE d.session_id = (SELECT id FROM s)
  AND (d.incorrect_attempts IS DISTINCT FROM COALESCE(p.wrong, 0)::smallint
    OR (NOT d.forced_by_researcher AND d.segment_count IS DISTINCT FROM COALESCE(p.right, 0)::smallint)
    OR p.kanjis > 1
    OR (p.kanji IS NOT NULL AND p.kanji <> d.kanji_id))
UNION ALL
-- attempts of an exposure that never closed (an aborted session leaves these;
-- in a complete session it is an error)
SELECT p.exposure_index, NULL, p.kanji, NULL, p.wrong, NULL, p.right, NULL
FROM placed p
WHERE NOT EXISTS (SELECT 1 FROM assemblies d
                  WHERE d.session_id = (SELECT id FROM s) AND d.exposure_index = p.exposure_index)
ORDER BY 1;

-- 4. KANJI_EXPOSED: audio source and assembly mode
SELECT exposure_index AS exp, kanji_id AS kanji, audio_source AS audio,
       assembly_mode AS assembly, exposure_ms
FROM kanji_exposures
WHERE session_id = (SELECT id FROM s)
ORDER BY exposure_index;

-- 5. Context during assembly (expected: S2 for exp 0, S5 for the rest; ESL
--    and LAL from the state visit the attempt falls in)
SELECT 'ASSEMBLY_SEGMENT_PLACED' AS event_type, a.state, ss.esl, ss.lal, count(*)
FROM assembly_attempts a
LEFT JOIN LATERAL (SELECT esl, lal FROM session_states x
                   WHERE x.session_id = a.session_id AND x.entered_elapsed_ms <= a.elapsed_ms
                   ORDER BY x.entered_elapsed_ms DESC LIMIT 1) ss ON TRUE
WHERE a.session_id = (SELECT id FROM s)
GROUP BY 1, 2, 3, 4
UNION ALL
SELECT 'ASSEMBLY_COMPLETED', a.state, ss.esl, ss.lal, count(*)
FROM assemblies a
LEFT JOIN LATERAL (SELECT esl, lal FROM session_states x
                   WHERE x.session_id = a.session_id AND x.entered_elapsed_ms <= a.completed_elapsed_ms
                   ORDER BY x.entered_elapsed_ms DESC LIMIT 1) ss ON TRUE
WHERE a.session_id = (SELECT id FROM s)
GROUP BY 1, 2, 3, 4
ORDER BY 1, 2;

-- verify_assembly.sql -- guided assembly telemetry (spec 5.3, decisions D2/D4)
-- Checks the MOST RECENT session, like the other verify_*.sql.
-- Field names follow database/EVENT_CONTRACT.md §5.1.
--
-- Usage (PowerShell, repo root):
--   Get-Content database\verify_assembly.sql | docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr
--
-- Query 3 is the check: any row it returns is an error.

\set ON_ERROR_STOP on
\set sid '(SELECT id FROM experiment_sessions ORDER BY created_at DESC LIMIT 1)'

-- 1. One row per placement attempt (right and wrong)
SELECT id, payload->>'kanji_id' AS kanji, payload->>'attempt' AS attempt,
       payload->>'slot_index' AS slot, payload->>'segment_id' AS segment,
       payload->>'expected_segment_id' AS expected, payload->>'is_correct' AS ok,
       payload->>'hint_shown' AS hint, payload->>'selected_ms' AS sel_ms,
       payload->>'placed_ms' AS placed_ms
FROM session_events
WHERE session_id = :sid AND event_type = 'ASSEMBLY_SEGMENT_PLACED'
ORDER BY id;

-- 2. Five closures, one per kanji of the set
SELECT id, payload->>'kanji_id' AS kanji, payload->>'duration_ms' AS dur_ms,
       payload->>'incorrect_attempts' AS wrong, payload->>'segment_count' AS segs,
       payload->>'segments_placed' AS placed, payload->>'hints_shown' AS hints,
       payload->'row_order' AS row_order, payload->>'forced_by_researcher' AS forced
FROM session_events
WHERE session_id = :sid AND event_type = 'ASSEMBLY_COMPLETED'
ORDER BY id;

-- 3. Cross-check: incorrect_attempts == wrong placements, segment_count == correct placements.
--    Any row returned is an ERROR.
WITH placed AS (
  SELECT payload->>'kanji_id' AS kanji,
         count(*) FILTER (WHERE (payload->>'is_correct')::boolean = false) AS wrong,
         count(*) FILTER (WHERE (payload->>'is_correct')::boolean = true)  AS right
  FROM session_events WHERE session_id = :sid AND event_type = 'ASSEMBLY_SEGMENT_PLACED'
  GROUP BY 1),
done AS (
  SELECT payload->>'kanji_id' AS kanji,
         (payload->>'incorrect_attempts')::int AS wrong,
         (payload->>'segment_count')::int AS segs,
         (payload->>'forced_by_researcher')::boolean AS forced
  FROM session_events WHERE session_id = :sid AND event_type = 'ASSEMBLY_COMPLETED')
SELECT d.kanji, d.wrong AS completed_wrong, p.wrong AS placed_wrong,
       d.segs, p.right AS placed_right, d.forced
FROM done d LEFT JOIN placed p USING (kanji)
WHERE d.wrong IS DISTINCT FROM coalesce(p.wrong, 0)
   OR (NOT d.forced AND d.segs IS DISTINCT FROM coalesce(p.right, 0));

-- 4. KANJI_EXPOSED: audio source and assembly mode
SELECT payload->>'kanji_id' AS kanji, payload->>'audio_source' AS audio,
       payload->>'assembly' AS assembly
FROM session_events WHERE session_id = :sid AND event_type = 'KANJI_EXPOSED' ORDER BY id;

-- 5. Context not falling back to OFF during S5 (expected: S5 / LOW / OFF-by-matrix for LAL)
SELECT event_type, payload->>'state' AS state, payload->>'esl' AS esl,
       payload->>'lal' AS lal, count(*)
FROM session_events
WHERE session_id = :sid AND event_type LIKE 'ASSEMBLY_%'
GROUP BY 1,2,3,4;

import { execSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

// Checkpoint B (tasks/todo.md): the pre-test feeds the VR loop. A participant pre-tested in
// the portal runs Unity with their effective set, and sets B and C assemble from real
// segments. Checked on the headset sessions in the database, not on fixtures.

const repo = fileURLToPath(new URL('../../..', import.meta.url))

function psql(sql: string): string[][] {
  // One line: on Windows the shell drops everything after a newline in the -c argument.
  const out = execSync(`docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr -At -F "|" -c "${sql.replace(/\s+/g, ' ')}"`, {
    cwd: repo, encoding: 'utf-8',
  })
  return out.trim().split('\n').filter(Boolean).map((l) => l.split('|'))
}

// B and C segments were cut and added to the assets on 19 Oct (archived Task 1.9); older
// sessions assembled from placeholders and are not corrected.
const SEGMENTS_CUT = '2026-10-20 00:00+09'

test('a substituted participant sees the substitute in every block, never the original', () => {
  const rows = psql(`SELECT s.id, k.original_kanji_id, k.substitute_kanji_id,
      count(*) FILTER (WHERE t.kanji_id = k.substitute_kanji_id),
      count(*) FILTER (WHERE t.kanji_id = k.original_kanji_id)
    FROM kanji_substitutions k
    JOIN participants p ON p.id = k.participant_id
    JOIN experiment_sessions s ON s.participant_id = k.participant_id AND s.assigned_kanji_set::text = k.set_name::text
      AND s.created_at > p.pretest_completed_at
    JOIN trials t ON t.session_id = s.id AND t.block_state <> 'S2_VR_TUTORIAL'
    GROUP BY 1, 2, 3`)
  expect(rows.length, 'no session of a substituted participant has trials yet').toBeGreaterThan(0)
  for (const [session, original, substitute, withSubstitute, withOriginal] of rows) {
    expect(Number(withSubstitute), `${session.slice(0, 8)}: no trial of ${substitute}`).toBeGreaterThan(0)
    expect(Number(withOriginal), `${session.slice(0, 8)}: ${original} still shown`).toBe(0)
  }
})

test('sets B and C assemble from real segments', () => {
  const sets = psql(`SELECT DISTINCT s.assigned_kanji_set FROM experiment_sessions s
    JOIN assemblies a ON a.session_id = s.id WHERE s.created_at >= '${SEGMENTS_CUT}'`).map(([set]) => set)
  expect(sets).toEqual(expect.arrayContaining(['B', 'C']))

  // A placeholder is allowed only for a substitute: the reserve beyond the 10 first choices has no segments yet (Task 1.10).
  const placeholders = psql(`SELECT left(s.id::text, 8), a.kanji_id FROM assemblies a
    JOIN experiment_sessions s ON s.id = a.session_id
    WHERE s.created_at >= '${SEGMENTS_CUT}' AND s.assigned_kanji_set IN ('B', 'C') AND NOT a.segments_authored
      AND a.kanji_id NOT IN (SELECT substitute_kanji_id FROM kanji_substitutions k WHERE k.participant_id = s.participant_id)`)
  expect(placeholders, placeholders.map((r) => r.join(' ')).join('; ')).toEqual([])
})

import { execSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

// Checkpoint C (tasks/todo.md): a real BEHAVIOR_ADAPTIVE F5a session can be rebuilt on
// screen without pgAdmin, and what the screen shows matches verify_projection and
// verify_adaptation (0 discrepancies). Runs on every completed BEHAVIOR_ADAPTIVE session
// in the database, comparing the screen with SQL, not with the API it is built on.

const repo = fileURLToPath(new URL('../../..', import.meta.url))

function psql(sql: string): string[][] {
  // One line: on Windows the shell drops everything after a newline in the -c argument.
  const out = execSync(`docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr -At -F "|" -c "${sql.replace(/\s+/g, ' ')}"`, {
    cwd: repo, encoding: 'utf-8',
  })
  return out.trim().split('\n').filter(Boolean).map((l) => l.split('|'))
}
const one = (sql: string) => psql(sql)[0]?.[0] ?? ''

const SESSIONS = psql(`SELECT id FROM experiment_sessions WHERE condition = 'BEHAVIOR_ADAPTIVE' AND status = 'COMPLETED' ORDER BY created_at`)
  .map(([id]) => id!)

test('there is at least one completed BEHAVIOR_ADAPTIVE session to rebuild', () => {
  expect(SESSIONS.length).toBeGreaterThan(0)
})

for (const id of SESSIONS) {
  test.describe(`session ${id.slice(0, 8)}`, () => {
    test('verify_projection and verify_adaptation find 0 discrepancies', () => {
      for (const fn of ['verify_projection_fn', 'verify_adaptation_fn']) {
        // session_id, check, detail: one row per discrepancy.
        const rows = psql(`SELECT * FROM ${fn}('${id}')`)
        expect(rows, `${fn}: ${rows.map((r) => r.slice(1).join(': ')).join('; ')}`).toEqual([])
      }
    })

    test('the Session View shows what the database holds', async ({ page }) => {
      const trials = Number(one(`SELECT count(*) FROM trials WHERE session_id = '${id}'`))
      const [env, lal, skipped] = psql(`SELECT count(*) FILTER (WHERE action = 'CHANGE_ENVIRONMENT'), count(*) FILTER (WHERE action = 'CHANGE_ASSISTANCE'),
        (SELECT count(*) FROM adaptation_applications WHERE session_id = '${id}' AND result = 'SKIPPED')
        FROM adaptation_decisions WHERE session_id = '${id}'`)[0]!.map(Number)
      const decisions = Number(one(`SELECT count(*) FROM adaptation_decisions WHERE session_id = '${id}'`))
      const accuracy = one(`SELECT round(accuracy * 100, 1) FROM v_session_overview WHERE session_id = '${id}'`)
      const openErrors = Number(one(`SELECT count(*) FROM projection_errors WHERE session_id = '${id}' AND resolved_at IS NULL`))
      const times = (n: number) => `${n} ${n === 1 ? 'time' : 'times'}`

      await page.goto(`/sessions/${id}`)

      // Header and summary (V1.2).
      await expect(page.getByText(new RegExp(`${trials} trials from S\\d to S\\d\\. The system changed the environment ${times(env!)} ` +
        `and the assistance ${times(lal!)}; Unity skipped ${skipped} of those changes\\.`))).toBeVisible()
      await expect(page.getByRole('complementary', { name: 'Session facts' }))
        .toContainText(openErrors === 0 ? 'No open projection errors' : `${openErrors} open projection error`)
      await expect(page.getByRole('region', { name: 'Where the time went' })).toContainText(`${accuracy} %`)
      await expect(page.getByRole('region', { name: 'Adaptations' }))
        .toContainText(`${decisions} decisions in S7. ${env! + lal!} changed something.`)

      // Timeline (V1.3): drawn, and the lanes this session recorded do not say otherwise.
      const timeline = page.getByRole('region', { name: 'Session timeline' })
      await timeline.locator('canvas').waitFor()
      for (const lane of ['Game Flow', 'Trials', 'Adaptations'])
        await expect(timeline.getByText(lane, { exact: true }).first()).toBeVisible()
      await expect(timeline.getByText('Not recorded in this session')).toHaveCount(
        Number(one(`SELECT (NOT EXISTS (SELECT 1 FROM session_events WHERE session_id = '${id}' AND event_type = 'HINT_REQUESTED')
          AND NOT EXISTS (SELECT 1 FROM session_events WHERE session_id = '${id}' AND event_type = 'TRIAL_STARTED'))::int
          + (NOT EXISTS (SELECT 1 FROM session_events WHERE session_id = '${id}' AND event_type IN ('PERIPHERAL_EVENT', 'DISTRACTOR_INTERACTION')))::int
          + (NOT EXISTS (SELECT 1 FROM session_events WHERE session_id = '${id}' AND event_type = 'HEAD_AWAY'))::int
          + (NOT EXISTS (SELECT 1 FROM session_events WHERE session_id = '${id}' AND event_type = 'ENVIRONMENT_APPLIED'))::int`)))

      // Trials tab (V1.4): one row per trial, tutorial included.
      await page.getByLabel('Hide tutorial (S2)').uncheck()
      await expect(page.getByRole('table', { name: 'Trials', exact: true }).getByRole('rowheader')).toHaveCount(trials)

      // Adaptations tab (V1.5): every decision; each change with its stored outcome.
      await page.getByRole('tab', { name: 'Adaptations' }).click()
      await page.getByLabel('Show decisions with no change').check()
      const adaptations = page.getByRole('table', { name: 'Adaptations', exact: true })
      await expect(adaptations.getByRole('rowheader')).toHaveCount(decisions)
      for (const [trial, outcome] of psql(`SELECT trial_id, COALESCE(outcome, 'Not recorded') FROM adaptation_decisions
          WHERE session_id = '${id}' AND action <> 'NO_CHANGE'`)) {
        const label = outcome === 'Not recorded' ? outcome : outcome![0] + outcome!.slice(1).toLowerCase()
        const row = adaptations.getByRole('row').filter({ has: page.getByRole('rowheader', { name: trial, exact: true }) })
        await expect(row).toContainText(label)
      }

      // Plan tab (V1.6): completed trials per block, and no gap in a complete session.
      await page.getByRole('tab', { name: 'Plan and execution' }).click()
      const plan = page.getByRole('table', { name: 'Plan and execution', exact: true })
      for (const [block, planned, completed] of psql(`SELECT left(p.block_state::text, 2), count(*), count(t.completed_event_id)
          FROM planned_trials p LEFT JOIN trials t ON t.session_id = p.session_id AND t.trial_id = p.trial_id
          WHERE p.session_id = '${id}' GROUP BY 1 ORDER BY 1`))
        await expect(plan.getByRole('img', { name: `${block}: ${completed} of ${planned} planned trials completed` })).toBeVisible()
      await expect(page.getByRole('complementary', { name: 'Where the session stopped' }))
        .toContainText('Every planned trial was completed, in every block.')
    })
  })
}

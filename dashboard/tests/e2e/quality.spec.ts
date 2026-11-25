import { expect, test } from '@playwright/test'

type Quality = {
  projected_sessions: number; clean_sessions: number; resolved_errors: number
  checks: { name: string; rows: { session_id: string }[] }[]; open_errors: unknown[]; not_projected: unknown[]
}

// V1.7 against the real database: the page shows the API's counts, and a check that needs
// review opens from the keyboard onto its affected sessions.
test('Data quality shows the real counts and opens a check that needs review', async ({ page, request }) => {
  const q = (await (await request.get('/api/research/quality')).json()) as Quality
  await page.goto('/quality')
  const lead = q.clean_sessions === q.projected_sessions
    ? 'Every projected session has no open errors and passes every check.'
    : `${q.clean_sessions} of ${q.projected_sessions} projected sessions have no open errors and pass every check.`
  await expect(page.locator('header p')).toContainText(lead)
  await expect(page.getByRole('region', { name: 'Open errors by code' }))
    .toContainText(`${q.resolved_errors.toLocaleString('en-US')} resolved by re-projection so far`)

  const checks = page.getByRole('table', { name: 'Verification checks' })
  for (const c of q.checks)
    await expect(checks.getByRole('row', { name: new RegExp(c.name) })).toContainText(c.rows.length ? 'Needs review' : 'Pass')

  const review = q.checks.find((c) => c.rows.length > 0)
  test.skip(!review, 'every check passes: nothing to open')
  const button = checks.getByRole('row', { name: new RegExp(review!.name) }).getByRole('button', { name: 'Show affected sessions' })
  await button.focus()
  await page.keyboard.press('Enter')
  await expect(button).toHaveAttribute('aria-expanded', 'true')
  await expect(checks.getByRole('link', { name: review!.rows[0]!.session_id.slice(0, 8) }).first()).toBeVisible()
})

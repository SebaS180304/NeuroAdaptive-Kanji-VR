import { expect, test } from '@playwright/test'

// Screen check: the participant list works from the keyboard alone.
test('keyboard reaches the filters, then each participant code, in order', async ({ page }) => {
  await page.goto('/participants')
  await page.getByRole('table').waitFor()
  const reached: string[] = []
  for (let i = 0; i < 10; i++) {
    await page.keyboard.press('Tab')
    reached.push(await page.evaluate(() => {
      const el = document.activeElement as HTMLElement
      return el.getAttribute('aria-label') ?? el.closest('label')?.textContent?.trim() ?? el.textContent?.trim() ?? ''
    }))
  }
  const filters = ['Participant code', 'Pre-test', 'Has sessions in', 'Only with notes for the researcher']
  const at = reached.findIndex((r) => r.startsWith('Participant code'))
  expect(at).toBeGreaterThan(0)                                            // after the rail
  expect(reached.slice(at, at + 4).map((r, i) => r.startsWith(filters[i]!))).toEqual([true, true, true, true])
  const firstCode = await page.getByRole('table').getByRole('link').first().textContent()
  expect(reached[at + 4]).toBe(firstCode)

  await page.keyboard.press('Shift+Tab')
  await page.keyboard.press('Tab')
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/participants\/[0-9a-f-]{36}$/)
})

// V1.8 on the participant with the most sessions: every session is a row, in order, and
// only the completed ones are trend points, ticked by their row number.
test('the Participant View lists every session and draws only the completed ones', async ({ page, request }) => {
  type Row = { id: string; session_count: number }
  type Session = { session_id: string; status: string; accuracy: number | null }
  const rows = (await (await request.get('/api/research/participants')).json()) as Row[]
  const p = rows.reduce((a, b) => (b.session_count > a.session_count ? b : a))
  const detail = (await (await request.get(`/api/research/participants/${p.id}`)).json()) as { sessions: Session[] }

  await page.goto(`/participants/${p.id}`)
  const table = page.getByRole('table', { name: 'Sessions in order' })
  await expect(table.locator('tbody tr')).toHaveCount(detail.sessions.length)
  const points = detail.sessions
    .map((s, i) => [i + 1, s] as const)
    .filter(([, s]) => s.status === 'COMPLETED' && s.accuracy !== null)
    .map(([n, s]) => `${n} ${(s.accuracy! * 100).toFixed(1)} %`)
  await expect(page.getByRole('img', { name: /^Accuracy per completed session/ }))
    .toHaveAttribute('aria-label', `Accuracy per completed session: ${points.join(', ')}`)

  // Each row reads the Session View's own accuracy.
  for (const [i, s] of detail.sessions.slice(0, 3).entries()) {
    const summary = await (await request.get(`/api/research/sessions/${s.session_id}`)).json()
    const cell = table.locator('tbody tr').nth(i).locator('td').nth(5)
    await expect(cell).toHaveText(summary.accuracy === null ? '—' : `${(summary.accuracy * 100).toFixed(1)} %`)
  }

  // Keyboard: the measure toggle.
  await page.getByRole('button', { name: 'Accuracy' }).focus()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('button', { name: 'Response time' })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('button', { name: 'Response time' })).toHaveAttribute('aria-pressed', 'true')
})

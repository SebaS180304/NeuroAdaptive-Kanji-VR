import { expect, test } from '@playwright/test'

// Screen check: the session list works from the keyboard alone.
test('keyboard reaches the filters, then the first session, and opens it', async ({ page }) => {
  await page.goto('/sessions')
  await page.getByRole('table').waitFor()
  const reached: string[] = []
  for (let i = 0; i < 20; i++) {
    await page.keyboard.press('Tab')
    reached.push(await page.evaluate(() => {
      const el = document.activeElement as HTMLElement
      return el.getAttribute('aria-label') ?? el.closest('label')?.textContent?.trim() ?? el.textContent?.trim() ?? ''
    }))
  }
  const at = reached.indexOf('Participant')
  expect(at).toBeGreaterThan(0)                                            // after the rail
  // A date input has three tab stops (year, month, day) in Chromium.
  const order = ['Participant', 'Condition', 'Status', 'Recorded from', 'Recorded to', 'Clear filters']
  const seen = reached.slice(at).filter((r, i, all) => r !== all[i - 1])
  expect(seen.slice(0, 6).map((r, i) => r.startsWith(order[i]!))).toEqual(order.map(() => true))
  const firstSession = await page.getByRole('table').getByRole('rowheader').first().textContent()
  expect(seen[6]).toBe(firstSession)

  const link = page.getByRole('table').getByRole('link', { name: firstSession! })
  await link.focus()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/sessions\/[0-9a-f-]{36}$/)
})

// Screen check: the Session View header works from the keyboard alone, on a real adaptive session.
test('Session View: keyboard reaches the back link and the participant', async ({ page, request }) => {
  const sessions = await (await request.get('/api/research/sessions?condition=BEHAVIOR_ADAPTIVE&status=COMPLETED')).json()
  test.skip(sessions.length === 0, 'no completed adaptive session')
  const s = sessions[0]
  await page.goto(`/sessions/${s.session_id}`)
  await page.getByRole('region', { name: 'Adaptations' }).waitFor()
  const reached: string[] = []
  for (let i = 0; i < 8; i++) {
    await page.keyboard.press('Tab')
    reached.push(await page.evaluate(() => document.activeElement?.textContent?.trim() ?? ''))
  }
  expect(reached.slice(4, 6)).toEqual(['Sessions', s.external_code])           // after the 4 rail items
  await page.getByRole('main').getByRole('link', { name: 'Sessions' }).focus()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/sessions$/)
})

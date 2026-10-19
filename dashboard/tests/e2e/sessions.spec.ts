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

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

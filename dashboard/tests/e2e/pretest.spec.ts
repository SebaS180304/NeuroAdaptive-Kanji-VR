import { execSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { expect, test, type Page } from '@playwright/test'

// V1.10 register, against the real backend: TEST_PRETEST is registered by keyboard
// only and deleted again (the API has no delete route, so through psql).
const CODE = 'TEST_PRETEST'
const repo = fileURLToPath(new URL('../../..', import.meta.url))
const removeTestParticipant = () =>
  execSync(
    `docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr -c "DELETE FROM participants WHERE external_code = '${CODE}'"`,
    { cwd: repo, stdio: 'ignore' },
  )

test.describe.configure({ mode: 'serial' })   // both tests use the same code
test.beforeEach(removeTestParticipant)
test.afterEach(removeTestParticipant)

/** Press Tab until the focused element matches, as a keyboard user would. */
async function tabTo(page: Page, matches: (el: { tag: string; label: string; type: string }) => boolean) {
  for (let i = 0; i < 60; i++) {
    await page.keyboard.press('Tab')
    const el = await page.evaluate(() => {
      const a = document.activeElement as HTMLInputElement
      return { tag: a.tagName, type: a.type ?? '', label: (a.labels?.[0]?.textContent ?? a.textContent ?? '').trim() }
    })
    if (matches(el)) return
  }
  throw new Error('focus never reached the element')
}

test('a new participant is registered by keyboard only, and the inclusion notice appears', async ({ page }) => {
  await page.goto('/pretest/register')
  await tabTo(page, (el) => el.label === 'Participant code')
  await page.keyboard.type(CODE)
  await tabTo(page, (el) => el.type === 'checkbox')
  await page.keyboard.press('Space')

  // Each question: Tab into its group, Space picks the focused pill, arrows move.
  await tabTo(page, (el) => el.label.endsWith('18–24'))
  await page.keyboard.press('ArrowRight')                          // 25–34
  await tabTo(page, (el) => el.label.endsWith('No'))               // Japanese study
  await page.keyboard.press('ArrowRight')                          // Yes
  await tabTo(page, (el) => el.label.endsWith('No'))               // kanji
  await page.keyboard.press('Space')
  await tabTo(page, (el) => el.label.endsWith('No'))               // VR
  await page.keyboard.press('Space')
  await tabTo(page, (el) => el.label === 'Save registration')
  await page.keyboard.press('Enter')

  const notice = page.getByRole('status', { name: 'For the researcher: previous Japanese study reported' })
  await expect(notice).toBeVisible()
  await expect(page.getByRole('button', { name: 'Save registration' })).toBeDisabled()

  await page.goto('/pretest')
  const row = page.getByRole('row', { name: new RegExp(CODE) })
  await expect(row).toContainText('Not started')
  await expect(row.getByRole('link', { name: 'Start' })).toBeVisible()
})

test('the same code twice is refused under the code field', async ({ page }) => {
  for (const attempt of [1, 2]) {
    await page.goto('/pretest/register')
    await page.getByLabel('Participant code').fill(CODE)
    await page.getByLabel(/Consent was obtained/).check()
    await page.getByRole('group', { name: /studied Japanese/ }).getByText('No', { exact: true }).click()
    await page.getByRole('button', { name: 'Save registration' }).click()
    if (attempt === 1) await expect(page).toHaveURL(/\/pretest\/[0-9a-f-]{36}$/)
  }
  await expect(page.getByText('This code is already registered. Open it from the participant list instead.')).toBeVisible()
})

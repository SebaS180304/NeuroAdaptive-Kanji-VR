import { execSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
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

// ---------------------------------------------------------------------------
// One kanji, done and pause (Task 1.6).


const content = JSON.parse(readFileSync(`${repo}/unity-client/Assets/Resources/kanji_content.json`, 'utf-8')) as {
  kanji: { id: string; kanji: string; meaning: string; targetReading: string; experimentalSet: string | null }[]
}
const charOf = Object.fromEntries(content.kanji.map((k) => [k.id, k.kanji]))
// What the participant must never see: any reading or meaning, a set name, the word "substitute".
const SECRETS = new RegExp(
  [...content.kanji.flatMap((k) => [`\\b${k.meaning}\\b`, k.targetReading]), '\\bset [abc]\\b', 'substitute'].join('|'),
  'i',
)

async function noSecrets(page: Page) {
  const text = await page.evaluate(() => document.body.innerText)
  expect(text.match(SECRETS)?.[0] ?? null).toBeNull()
}

async function register(page: Page): Promise<string> {
  const resp = await page.request.post('/api/participants', {
    data: { external_code: CODE, consent_obtained: true, previous_japanese_experience: false },
  })
  expect(resp.status()).toBe(201)
  return (await resp.json()).id
}

const answeredIs = (page: Page, n: number) => expect(page.locator('[aria-live]')).toHaveText(`${n} answered`)
const shownKanji = (page: Page) => page.getByRole('img', { name: 'Kanji to answer' }).textContent()

async function saveByKeyboard(page: Page) {
  await tabTo(page, (el) => el.label === 'Save and next')
  await page.keyboard.press('Enter')
}

function psql(sql: string): string[][] {
  const out = execSync(`docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr -At -F "|" -c "${sql}"`, {
    cwd: repo, encoding: 'utf-8',
  })
  return out.trim().split('\n').filter(Boolean).map((l) => l.split('|'))
}

test('a full pre-test runs by keyboard only, shows nothing it must not, and the DB matches', async ({ page }) => {
  const id = await register(page)
  await page.goto(`/pretest/${id}`)
  const done = page.getByRole('heading', { level: 1, name: "That's all. Thank you." })
  const given: [string, string][] = []

  for (let n = 0; ; n++) {
    await expect(page.getByRole('img', { name: 'Kanji to answer' }).or(done)).toBeVisible()
    await noSecrets(page)
    if (await done.isVisible()) break
    const kanji = (await shownKanji(page))!
    if (n === 0) {
      // Yes: type, check, flip one result, save the verdict.
      await page.keyboard.press('3')
      await tabTo(page, (el) => el.label === 'Reading, in kana or romaji')
      await page.keyboard.type('x')
      await tabTo(page, (el) => el.label === 'Meaning, in English')
      await page.keyboard.type('x')
      await tabTo(page, (el) => el.label === 'Check')
      await page.keyboard.press('Enter')
      await expect(page.getByText('Incorrect')).toHaveCount(2)
      await noSecrets(page)
      await tabTo(page, (el) => el.label === 'Mark reading correct')
      await page.keyboard.press('Enter')
      given.push([kanji, 'YES|t|f'])
    } else {
      await page.keyboard.press('1')
      given.push([kanji, 'NO||'])
    }
    await saveByKeyboard(page)
    await answeredIs(page, n + 1)
  }

  await expect(page.getByRole('region', { name: 'For the researcher' })).toContainText(`${given.length} kanji`)
  const rows = psql(`SELECT r.kanji_id, r.self_report, r.reading_correct, r.meaning_correct FROM kanji_pretest_responses r
    JOIN participants p ON p.id = r.participant_id WHERE p.external_code = '${CODE}' ORDER BY r.seq`)
  expect(given.length).toBeGreaterThanOrEqual(15)
  expect(rows.map(([kid, ...rest]) => [charOf[kid!], rest.join('|')])).toEqual(given)
  const kept = psql(`SELECT count(*) FROM kanji_substitutions s JOIN participants p ON p.id = s.participant_id
    WHERE p.external_code = '${CODE}'`)[0]![0]
  const state = await (await page.request.get(`/api/participants/${id}/pretest`)).json()
  expect(Number(kept)).toBe(state.substitutions.length + state.flagged.length)
})

test('Pause, then Resume, continues at the same kanji', async ({ page }) => {
  const id = await register(page)
  await page.goto(`/pretest/${id}`)
  for (const n of [1, 2]) {
    await page.getByRole('img', { name: 'Kanji to answer' }).waitFor()
    await page.keyboard.press('1')
    await saveByKeyboard(page)
    await answeredIs(page, n)
  }
  const before = await shownKanji(page)
  await page.getByRole('link', { name: 'Pause' }).click()
  await expect(page.getByRole('status', { name: 'Paused at 2 answered' })).toBeVisible()
  await page.getByRole('row', { name: new RegExp(CODE) }).getByRole('link', { name: 'Resume' }).click()
  await expect(page.getByRole('status', { name: 'Picking up where you left off' })).toBeVisible()
  expect(await shownKanji(page)).toBe(before)
})

test('a save from a second tab makes the first show the 409 notice and carry on', async ({ page, context }) => {
  const id = await register(page)
  const other = await context.newPage()
  await page.goto(`/pretest/${id}`)
  await other.goto(`/pretest/${id}`)
  const first = await shownKanji(page)
  expect(await shownKanji(other)).toBe(first)

  await other.keyboard.press('1')
  await other.getByRole('button', { name: 'Save and next' }).click()
  await answeredIs(other, 1)

  await page.keyboard.press('1')
  await page.getByRole('button', { name: 'Save and next' }).click()
  await expect(page.getByRole('status', { name: 'This kanji was already saved' })).toBeVisible()
  await answeredIs(page, 1)
  expect(await shownKanji(page)).toBe(await shownKanji(other))
  expect(await shownKanji(page)).not.toBe(first)
})

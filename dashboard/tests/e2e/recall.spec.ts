import { execSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

// V1.12 Block R free recall (BR3), against the real backend: TEST_RECALL gets a pre-test, a completed visit 1 and
// a visit 2 that evaluates it; deleted again through psql (the API has no delete route).
const CODE = 'TEST_RECALL'
const API = 'http://127.0.0.1:8000'
const repo = fileURLToPath(new URL('../../..', import.meta.url))
const psql = (sql: string) =>
  execSync(`docker compose exec -T db psql -U neuroadaptive -d neuroadaptive_vr -Atc "${sql}"`, { cwd: repo, encoding: 'utf8' })
const removeTestParticipant = () => psql(`DELETE FROM participants WHERE external_code = '${CODE}'`)

async function post(path: string, body: unknown) {
  const resp = await fetch(`${API}${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!resp.ok) throw new Error(`${path}: ${resp.status} ${await resp.text()}`)
  return resp.json()
}

let visit2 = ''

test.beforeAll(async () => {
  removeTestParticipant()
  const { id: pid } = await post('/participants', { external_code: CODE, consent_obtained: true })
  let state = await (await fetch(`${API}/participants/${pid}/pretest`)).json()
  while (state.next) state = await post(`/participants/${pid}/pretest/responses`, { kanji_id: state.next.kanji_id, self_report: 'NO' })
  const session = (visit: number, set: string) =>
    post('/sessions', { participant_id: pid, condition: 'STATIC', assigned_kanji_set: set, visit_number: visit, random_seed: `e2e-${visit}` })
  const v1 = await session(1, 'A')
  psql(`UPDATE experiment_sessions SET status = 'COMPLETED', completed_at = now() WHERE id = '${v1.id}'`)
  visit2 = (await session(2, 'B')).id
})
test.afterAll(removeTestParticipant)

test('the researcher marks two kanji, saves, and finds them after a reload', async ({ page }) => {
  await page.goto(`/sessions/${visit2}`)
  await page.getByRole('link', { name: 'Free recall' }).click()
  await expect(page.getByRole('heading', { name: 'Free recall' })).toBeVisible()
  await expect(page.getByRole('status')).toHaveText('Nothing marked. Not saved yet.')

  const row = (kanji: string) => page.getByRole('row', { name: new RegExp(kanji) })
  await row('竹').getByRole('button', { name: /Meaning/ }).click()
  await row('月').getByRole('button', { name: /Reading/ }).click()
  await expect(row('竹').getByText('1st')).toBeVisible()
  await expect(row('月').getByText('2nd')).toBeVisible()
  await page.getByRole('button', { name: 'Save free recall' }).click()
  await expect(page.getByRole('status')).toContainText('2 of 5 kanji recalled.')
  await expect(page.getByRole('button', { name: 'Save changes' })).toBeVisible()

  await page.reload()
  await expect(row('竹').getByRole('button', { name: /Meaning/ })).toHaveAttribute('aria-pressed', 'true')
  await expect(row('月').getByRole('button', { name: /Reading/ })).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByRole('status')).toHaveText(/^Saved at \d\d:\d\d\. 2 of 5 kanji recalled\./)
  expect(psql(`SELECT count(*) FROM session_events WHERE session_id = '${visit2}' AND event_type = 'BLOCK_R_FREE_RECALL'`).trim()).toBe('1')
})

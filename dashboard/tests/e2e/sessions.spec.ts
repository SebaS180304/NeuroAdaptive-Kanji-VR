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

// Status words (design-system.md V1.8): an aborted session names its last recorded state,
// in V1.1 and in the Session View facts.
test('an aborted session reads "Aborted in [state]" in the list and the Session View', async ({ page, request }) => {
  type Row = { session_id: string; last_state: string | null }
  const rows = (await (await request.get('/api/research/sessions?status=ABORTED')).json()) as Row[]
  const s = rows.find((r) => r.last_state)
  test.skip(!s, 'needs an aborted session with a recorded state')
  const words = `Aborted in ${s!.last_state!.slice(0, 2)}`

  await page.goto('/sessions')
  await expect(page.getByRole('row', { name: new RegExp(s!.session_id.slice(0, 8)) })).toContainText(words)
  await page.goto(`/sessions/${s!.session_id}`)
  await expect(page.getByRole('complementary', { name: 'Session facts' })).toContainText(words)
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

// V1.3: the full real F5a session renders without lag, and S7 can be isolated by keyboard.
test('timeline draws a full adaptive session quickly and zooms to S7', async ({ page, request }) => {
  const sessions = await (await request.get('/api/research/sessions?condition=BEHAVIOR_ADAPTIVE&status=COMPLETED')).json()
  test.skip(sessions.length === 0, 'no completed adaptive session')
  const t0 = Date.now()
  await page.goto(`/sessions/${sessions[0].session_id}`)
  const timeline = page.getByRole('region', { name: 'Session timeline' })
  await timeline.locator('canvas').waitFor()
  expect(Date.now() - t0).toBeLessThan(3000)

  const longTasks = await page.evaluate(() => new Promise<number>((resolve) => {
    let worst = 0
    new PerformanceObserver((l) => l.getEntries().forEach((e) => { worst = Math.max(worst, e.duration) }))
      .observe({ type: 'longtask', buffered: true })
    setTimeout(() => resolve(worst), 500)
  }))
  expect(longTasks).toBeLessThan(200)

  await timeline.getByRole('button', { name: 'Only S7' }).focus()
  await page.keyboard.press('Enter')
  await expect(timeline.getByRole('button', { name: 'Only S7' })).toHaveAttribute('aria-pressed', 'true')
  await expect(timeline.getByText(/^Showing \d\d:\d\d to \d\d:\d\d of the session\.$/)).toBeAttached()
})

// V1.4: selection syncs between the Trials table and the timeline, both ways.
test('selecting a trial in the table or the timeline selects it in the other', async ({ page, request }) => {
  const sessions = await (await request.get('/api/research/sessions?condition=BEHAVIOR_ADAPTIVE&status=COMPLETED')).json()
  test.skip(sessions.length === 0, 'no completed adaptive session')
  const id = sessions[0].session_id
  const timeline = await (await request.get(`/api/research/sessions/${id}/timeline`)).json()
  await page.goto(`/sessions/${id}`)
  const chartBox = page.getByRole('region', { name: 'Session timeline' })
  await chartBox.locator('canvas').waitFor()
  const table = page.getByRole('table', { name: 'Trials' })

  // Table to timeline: the row's button, by keyboard.
  const first = table.getByRole('button', { name: /^S7-\d{3}$/ }).first()
  const firstId = (await first.textContent())!
  await first.focus()
  await page.keyboard.press('Enter')
  await expect(first).toHaveAttribute('aria-pressed', 'true')
  await expect(chartBox.getByText(new RegExp(`Selected trial ${firstId} at`))).toBeAttached()

  // Timeline to table: click the middle of the longest S7 trial bar, zoomed to S7.
  await chartBox.getByRole('button', { name: 'Only S7' }).click()
  // The S7 window as the screen computes it: first S7 entry to its exit.
  const s7State = timeline.states.find((s: { state: string }) => s.state.startsWith('S7'))
  const s7 = timeline.trials.filter((t: { trial_id: string; end_ms: number | null }) => t.trial_id.startsWith('S7') && t.end_ms !== null)
  const longest = s7.reduce((x: { start_ms: number; end_ms: number }, y: { start_ms: number; end_ms: number }) =>
    y.end_ms - y.start_ms > x.end_ms - x.start_ms ? y : x)
  const canvas = chartBox.locator('canvas')
  const box = (await canvas.boundingBox())!
  const inset = 24
  const [from, to] = [s7State.start_ms, s7State.end_ms ?? timeline.session_end_ms]
  const mid = (longest.start_ms + longest.end_ms) / 2
  const x = inset + ((mid - from) / (to - from)) * (box.width - 2 * inset)
  await canvas.click({ position: { x, y: 40 + 32 + 32 + 8 + 8 } })        // the Trials lane's bar slot
  await expect(table.getByRole('button', { name: longest.trial_id })).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByRole('complementary', { name: 'Selected trial' })).toContainText(`Trial ${longest.trial_id}`)
})

// V1.5: every decision of the real session is listed, and a row expands by keyboard.
test('the Adaptations tab lists every decision and expands a row by keyboard', async ({ page, request }) => {
  const sessions = await (await request.get('/api/research/sessions?condition=BEHAVIOR_ADAPTIVE&status=COMPLETED')).json()
  test.skip(sessions.length === 0, 'no completed adaptive session')
  const id = sessions[0].session_id
  const every = await (await request.get(`/api/research/sessions/${id}/adaptations?include_no_change=true`)).json()
  const detail = await (await request.get(`/api/research/sessions/${id}`)).json()
  expect(every.length).toBe(detail.decision_count)                     // the API lists every decision row

  await page.goto(`/sessions/${id}`)
  const tab = page.getByRole('tab', { name: 'Adaptations' })
  await tab.focus()
  await page.keyboard.press('Enter')
  const table = page.getByRole('table', { name: 'Adaptations', exact: true })
  await table.waitFor()
  const changes = every.filter((a: { action: string }) => a.action !== 'NO_CHANGE').length
  await expect(table.getByRole('rowheader')).toHaveCount(changes)
  await page.getByLabel('Show decisions with no change').check()
  await expect(table.getByRole('rowheader')).toHaveCount(every.length)

  const first = table.getByRole('button', { name: /^Show indicators for / }).first()
  await first.focus()
  await page.keyboard.press('Enter')
  await expect(first).toHaveAttribute('aria-expanded', 'true')
  await expect(table.getByRole('region', { name: /^Decision after S7-\d{3}$/ })).toContainText('Reason code')
})

// V1.6: an aborted session shows where it stopped; a complete one shows no gap.
test('the Plan tab shows where an aborted session stopped, and no gap in a complete one', async ({ page, request }) => {
  type Block = { completed: number; planned: number }
  const plan = async (id: string) => (await (await request.get(`/api/research/sessions/${id}/plan`)).json()) as { blocks: Block[] }
  let cut: string | null = null
  for (const s of await (await request.get('/api/research/sessions?status=ABORTED')).json())
    if ((await plan(s.session_id)).blocks.some((b) => b.completed < b.planned)) { cut = s.session_id; break }
  const complete = (await (await request.get('/api/research/sessions?condition=BEHAVIOR_ADAPTIVE&status=COMPLETED')).json())[0]
  test.skip(!cut || !complete, 'needs an aborted session with a cut block and a completed one')

  await page.goto(`/sessions/${cut}`)
  await page.getByRole('tab', { name: 'Plan and execution' }).click()
  const table = page.getByRole('table', { name: 'Plan and execution', exact: true })
  await expect(table.locator('tr[class*="warn-tint"]')).toHaveCount(1)
  await expect(page.getByRole('complementary', { name: 'Where the session stopped' }))
    .toContainText(/S\d stopped (after S\d-\d{3}|before its first completed trial)\./)
  await expect(page.getByRole('complementary', { name: 'Where the session stopped' })).toContainText('Session statusAborted')

  await page.goto(`/sessions/${complete.session_id}`)
  await page.getByRole('tab', { name: 'Plan and execution' }).click()
  await page.getByRole('table', { name: 'Plan and execution', exact: true }).waitFor()
  await expect(page.locator('tr[class*="warn-tint"]')).toHaveCount(0)
  await expect(page.getByRole('complementary', { name: 'Where the session stopped' }))
    .toContainText('Every planned trial was completed, in every block.')
})

// V1.9: both CSV files download from the keyboard menu, with the API's fields as headers.
test('Export CSV downloads trials and adaptations with the API fields as headers', async ({ page, request }) => {
  const sessions = await (await request.get('/api/research/sessions?condition=BEHAVIOR_ADAPTIVE&status=COMPLETED')).json()
  test.skip(sessions.length === 0, 'no completed adaptive session')
  const id = sessions[0].session_id
  await page.goto(`/sessions/${id}`)
  const button = page.getByRole('button', { name: 'Export CSV' })

  for (const [kind, nth] of [['trials', 0], ['adaptations', 1]] as const) {
    await button.focus()
    await page.keyboard.press('Enter')
    for (let i = 0; i < nth; i++) await page.keyboard.press('ArrowDown')
    const [download] = await Promise.all([page.waitForEvent('download'), page.keyboard.press('Enter')])
    expect(download.suggestedFilename()).toBe(`session-${id.slice(0, 8)}-${kind}.csv`)
    const raw = await (await import('node:fs/promises')).readFile((await download.path())!, 'utf-8')
    expect(raw.charCodeAt(0)).toBe(0xfeff)                              // the BOM Excel needs to read UTF-8 (kanji)
    const text = raw.slice(1)
    const header = text.split('\n')[0]!.split(',')
    const api = await (await request.get(`/api/research/sessions/${id}/${kind}${kind === 'adaptations' ? '?include_no_change=true' : ''}`)).json()
    expect(header).toEqual(Object.keys(api[0]))
    expect(text.trim().split('\n').length - 1).toBe(api.length)
  }
  await button.focus()
  await page.keyboard.press('Enter')
  await page.keyboard.press('Escape')
  await expect(page.getByRole('menu')).toHaveCount(0)
  await expect(button).toBeFocused()
})

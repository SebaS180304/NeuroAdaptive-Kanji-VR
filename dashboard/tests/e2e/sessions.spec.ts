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

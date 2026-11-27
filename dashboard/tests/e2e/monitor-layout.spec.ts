import { expect, test, type Page } from '@playwright/test'

// D-F6-323 (4)-(5), D-F6-328: the live monitor's layout, measured in a real browser. An invented session
// (DEMO01, no participant data) served by route mocks, traces on, at 1440 x 900 and 1920 x 1080.
// CAPTURE_DIR=<folder> also saves the screenshots for Diseño web.

const SID = 'aaaaaaaa-0000-4000-8000-000000000001'
const ST = ['S1_WELCOME_ORIENTATION', 'S2_VR_TUTORIAL', 'S3_SYSTEM_VALIDATION', 'S4_EEG_BASELINE', 'S5_STANDARDIZED_LEARNING',
  'S6_GUIDED_PRACTICE_CALIBRATION', 'S7_EXPERIMENTAL_RETRIEVAL', 'S8_IMMEDIATE_ASSESSMENT', 'S9_SESSION_SUMMARY']
const MS = [0, 40_000, 130_000, 185_000, 308_000, 514_000, 637_000, 740_000, 805_000]
const STAGE = { S5: [4, 318_000], S7: [6, 699_000], S8: [7, 752_000] } as const
const FIXED = ['Signal quality', 'System', 'Live indices', 'Sync', 'Channel traces, 8 channels, last 20 seconds']

function snapshot(stage: keyof typeof STAGE) {
  const [k, now] = STAGE[stage]
  let seed = 7
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647)
  const stateAt = (t: number) => ST[MS.filter((m) => m <= t).length - 1]!
  const epochs = []
  for (let t = 140_000, i = 0; t < now - 1_200; t += 2_500, i++) {
    const st = stateAt(t), s7 = st === ST[6], poor = rnd() < 0.08, ei = -1.6 + (rnd() - 0.5) * 0.5, th = -2.2 + (rnd() - 0.5) * 0.6
    const trial = s7 ? `S7-${String(Math.min(20, 1 + Math.floor((t - MS[6]!) / 5_000))).padStart(3, '0')}` : null
    epochs.push({ i, start_ms: t, end_ms: t + 2_000, state: st, trial_id: trial, valid: !poor, grey: false, excluded: null,
      unit: s7 ? 'z' : 'ln', ei: poor ? null : s7 ? (ei + 1.6) * 3 : ei, theta: poor ? null : s7 ? (th + 2.2) * 3 : th,
      ln_ei: poor ? null : ei, ln_theta: poor ? null : th })
  }
  const decisions = []
  for (let n = 3; n <= 20 && MS[6]! + n * 5_000 <= now; n++) {
    decisions.push({ trial_id: `S7-${String(n).padStart(3, '0')}`, trial_sequence: n, decided_elapsed_ms: MS[6]! + n * 5_000,
      learner_state: 'STABLE', action: n === 5 ? 'CHANGE_ASSISTANCE' : 'NO_CHANGE', dimension: n === 5 ? 'LAL' : null,
      from_level: n === 5 ? 'MEDIUM' : null, to_level: n === 5 ? 'LOW' : null, esl: 'MEDIUM', lal: n >= 5 ? 'LOW' : 'MEDIUM',
      reason_code: 'STABLE', eeg_counted: n % 4 !== 0, eeg_ei_z: (rnd() - 0.5) * 2.4, eeg_theta_z: (rnd() - 0.5) * 2, eeg_effect: 'NEUTRAL' })
  }
  return {
    generated_at: new Date().toISOString(),
    session: { session_id: SID, external_code: 'DEMO01', condition: 'MULTIMODAL_ADAPTIVE', set: 'C', visit: 1, status: 'IN_PROGRESS',
      stage: ST[k], stage_entered_ms: MS[k], elapsed_ms: now },
    sync: { clear_taps: 5, taps: 5, offset_ms: 21.2, robust_spread_ms: 14.0 },
    indices: { reference: { source: 'S6', fallback: false, n_epochs: 49 },
      last: k === 6 ? { trial_id: 'S7-011', counted: true, ei_z: -0.6, ei_band: 'Normal', theta_z: 0.4, theta_band: 'Normal' } : null,
      windows: { counted: 8, with_eeg: 9 }, trace: [],
      session: { view: 'window', stages: ST.map((state, j) => ({ state, ms: MS[j]! })).filter((x) => x.ms <= now),
        eyes_closed_ms: [245_000, 290_000],
        // the longest ICA line, to see it cut at 1440 (D-F6-328 (2) (a))
        ica: { identified: false, corr: 0.55, reason: null, switched_to_nosound_at: null, switch_reason: null,
          at_ms: MS[5]! + 1_000, switch_ms: null, switch_channel: null },
        epochs } },
    decisions: [...decisions].reverse(),
    events: Array.from({ length: 30 }, (_, j) => ({ elapsed_ms: now - j * 3_000, event_type: j % 3 ? 'ANSWER_SELECTED' : 'TRIAL_STARTED',
      trial_id: null, flag: null })),
    system: { heartbeat_age_s: 1.1, eeg_gap_ms: 80, bad_channel: null, bad_channel_from_ms: null,
      alpha_ratio: { P3: 1.5, Pz: 1.6, P4: 1.5 }, alpha_passed: true, not_counted_reason: null },
    signal_quality: { channels: ['Fp1', 'F3', 'Fz', 'F4', 'Cz', 'P3', 'Pz', 'P4'].map((label) => ({ label, l60_uv: 60, rms_uv: 15,
      over_pct: 0, status: 'OK', flat: false, sync_tap: false, mark_60: false })), session_60_uv: 61, session_60_status: 'OK', age_s: 1 },
  }
}

function traces(now: number) {
  const bins = []
  for (let t = now - 20_000; t <= now; t += 40) {
    const v = 10 * Math.sin(t / 90)
    bins.push({ t_ms: t, mins: Array(8).fill(v - 8), maxs: Array(8).fill(v + 8) })
  }
  return { on: true, reason: null, labels: ['Fp1', 'F3', 'Fz', 'F4', 'Cz', 'P3', 'Pz', 'P4'], bins,
    now: { t_ms: now, taps: [], rms_uv: Array(8).fill(15), age_s: 0.1 }, stages: [], excluded: null }
}

async function open(page: Page, stage: keyof typeof STAGE, w: number, h: number) {
  await page.setViewportSize({ width: w, height: h })
  const snap = snapshot(stage)
  await page.route('**/api/research/sessions/*/live/traces*', (r) => r.fulfill({ json: traces(snap.session.elapsed_ms) }))
  await page.route('**/api/research/sessions/*/live', (r) => r.fulfill({ json: snap }))
  await page.route('**/api/research/live/current', (r) => r.fulfill({ json: { session_id: SID, external_code: 'DEMO01' } }))
  await page.goto(`/monitor/${SID}`)
  await page.getByText('Updates with each epoch, every 2.5 s.').waitFor()
  await page.waitForTimeout(400)
}

const box = async (page: Page, name: string) => (await page.getByRole('region', { name, exact: true }).boundingBox())!

async function capture(page: Page, name: string) {
  if (process.env.CAPTURE_DIR) await page.screenshot({ path: `${process.env.CAPTURE_DIR}/${name}` })
}

test('D-F6-323 (4): on a taller screen only Events and Decisions grow; nothing scrolls', async ({ page }) => {
  await open(page, 'S7', 1440, 900)   // the drawing's size: no scroll
  expect(await page.evaluate(() => document.documentElement.scrollHeight <= innerHeight && document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await capture(page, 'Monitor_S7_1440x900_27nov.png')
  // the same width, two heights: only the height may change (a wider column wraps its text in fewer lines)
  await open(page, 'S7', 1920, 900)
  const small: Record<string, { height: number }> = {}
  for (const n of [...FIXED, 'Events', 'Adaptation decisions']) small[n] = await box(page, n)
  await open(page, 'S7', 1920, 1080)
  for (const n of FIXED) expect(Math.abs((await box(page, n)).height - small[n]!.height), n).toBeLessThanOrEqual(1)
  expect((await box(page, 'Events')).height - small.Events!.height).toBeGreaterThanOrEqual(170)
  expect((await box(page, 'Adaptation decisions')).height - small['Adaptation decisions']!.height).toBeGreaterThanOrEqual(170)
  expect(await page.evaluate(() => document.documentElement.scrollHeight <= innerHeight && document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await expect(page.getByRole('region', { name: 'Events' }).getByRole('listitem').first()).toBeVisible()
  await capture(page, 'Monitor_alto_completo_1920x1080_S7_27nov.png')
})

for (const [w, h] of [[1440, 900], [1920, 1080]] as const) {
  test(`12:15 point 1: Live indices ends on the same pixel in S5, S7 and S8 at ${w} x ${h}`, async ({ page }) => {
    const bottoms: number[] = []
    for (const stage of ['S5', 'S7', 'S8'] as const) {
      await open(page, stage, w, h)
      const b = await box(page, 'Live indices')
      bottoms.push(Math.round(b.y + b.height))
      // the chips never shrink or wrap; only the ICA line gives way, cut with «…» (D-F6-328 (2) (a))
      const chips = page.getByTestId('chip-row').locator('> span').filter({ hasNot: page.getByTestId('ica-line') })
      for (const c of await chips.all()) expect((await c.boundingBox())!.height, `${stage} chip`).toBeLessThanOrEqual(23)
      await capture(page, `MI_fuera_S7_${stage}_${w}x${h}_27nov.png`)
    }
    expect(new Set(bottoms).size, `bottoms ${bottoms.join(', ')}`).toBe(1)
  })
}

test('12:15 points 3-4: "Trial 11" shows at 1440, and no axis or tick uses a hyphen for minus', async ({ page }) => {
  await open(page, 'S7', 1440, 900)
  await expect(page.getByLabel('Trials').getByText('Trial 11')).toBeAttached()
  for (const stage of ['S5', 'S7'] as const) {
    await open(page, stage, 1440, 900)
    for (const name of ['Live indices', 'Channel traces, 8 channels, last 20 seconds']) {
      const texts = await page.getByRole('region', { name, exact: true }).locator('text, span').allTextContents()
      const hyphen = texts.filter((t) => /(^|[\s(])-\d/.test(t))
      expect(hyphen, `${stage} ${name}`).toEqual([])
      expect(texts.some((t) => t.includes('−')), `${stage} ${name} has U+2212`).toBe(true)
    }
  }
})

import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { json, mockApi } from '@/test/api'
import { renderApp } from '@/test/render'

const SID = 'b7d2e019-0000-0000-0000-000000000000'

const snapshot = (over: object = {}) => ({
  generated_at: '2026-11-20T10:21:47+09:00',
  session: {
    session_id: SID, external_code: 'P03', condition: 'MULTIMODAL_ADAPTIVE', set: 'B', visit: 2, status: 'IN_PROGRESS',
    stage: 'S7_EXPERIMENTAL_RETRIEVAL', stage_entered_ms: 1_200_000, elapsed_ms: 1_307_000,
  },
  sync: { clear_taps: 5, taps: 5, offset_ms: 14.4, robust_spread_ms: 17.8 },
  indices: {
    reference: { source: 'S6', fallback: false, n_epochs: 18 },
    last: { trial_id: 'S7-011', counted: true, ei_z: -1.3, ei_band: 'Low', theta_z: 0.1, theta_band: 'Normal' },
    windows: { counted: 8, with_eeg: 9 },
    trace: [{ start_ms: 1_210_000, ei_z: -0.4, theta_z: 0.2 }, { start_ms: 1_212_500, ei_z: -1.2, theta_z: 0.1 }],
  },
  decisions: [
    { trial_id: 'S7-011', trial_sequence: 11, decided_elapsed_ms: 1_302_000, learner_state: 'STABLE', action: 'NO_CHANGE',
      dimension: null, from_level: null, to_level: null, esl: 'MEDIUM', lal: 'LOW', reason_code: 'STABLE',
      eeg_counted: true, eeg_ei_z: -1.3, eeg_theta_z: 0.1, eeg_effect: 'ONLY_ALERT' },
    { trial_id: 'S7-009', trial_sequence: 9, decided_elapsed_ms: 1_287_000, learner_state: 'DISENGAGED',
      action: 'CHANGE_ASSISTANCE', dimension: 'LAL', from_level: 'MEDIUM', to_level: 'LOW', esl: 'MEDIUM', lal: 'MEDIUM',
      reason_code: 'DISENGAGED', eeg_counted: true, eeg_ei_z: -1.3, eeg_theta_z: 0.0, eeg_effect: 'CONFIRMED' },
  ],
  events: [
    { elapsed_ms: 1_306_000, event_type: 'ANSWER_SELECTED', trial_id: 'S7-012', flag: null },
    { elapsed_ms: 1_291_000, event_type: 'HEAD_AWAY', trial_id: null, flag: 'look' },
    { elapsed_ms: 1_287_000, event_type: 'ADAPTATION_DECISION', trial_id: 'S7-009', flag: 'decision' },
  ],
  system: { heartbeat_age_s: 1.2, eeg_gap_ms: 120, bad_channel: null, bad_channel_from_ms: null,
    alpha_ratio: { P3: 4.9, Pz: 3.6, P4: 4.0 }, alpha_passed: true, not_counted_reason: null },
  signal_quality: null,
  ...over,
})

afterEach(() => vi.unstubAllGlobals())

describe('V1.13 live session monitor (M1c)', () => {
  it('shows the top bar, read-only line, sync, indices, decisions, events and system of one session', async () => {
    mockApi({ [`GET /api/research/sessions/${SID}/live`]: () => json(snapshot()) })
    renderApp(`/monitor/${SID}`)

    expect(await screen.findByText('S7 Adaptive practice')).toBeInTheDocument()
    expect(screen.getByText('Read only. Nothing on this screen changes the session.')).toBeInTheDocument()
    const top = screen.getByRole('banner')
    expect(within(top).getByText('b7d2e019')).toBeInTheDocument()
    expect(within(top).getByText('P03')).toBeInTheDocument()
    expect(within(top).getByText('21:47')).toBeInTheDocument()   // 1 307 000 ms

    const sync = screen.getByRole('region', { name: 'Sync' })
    expect(within(sync).getByText('5 of 5 clear')).toBeInTheDocument()
    expect(within(sync).getByText('14.4 ms')).toBeInTheDocument()

    const ind = screen.getByRole('region', { name: 'Live indices' })
    expect(within(ind).getByText('Low')).toBeInTheDocument()
    expect(within(ind).getByText('−1.3')).toBeInTheDocument()
    expect(within(ind).getByText('8 of 9 windows (89 %)')).toBeInTheDocument()
    expect(within(ind).getByText('S6 (18 epochs not POOR)')).toBeInTheDocument()

    const dec = screen.getByRole('region', { name: 'Adaptation decisions' })
    expect(within(dec).getByText('After 9')).toBeInTheDocument()
    expect(within(dec).getByText('EEG_CONFIRMED')).toBeInTheDocument()

    const ev = screen.getByRole('region', { name: 'Events' })
    expect(within(ev).getByText('HEAD_AWAY')).toBeInTheDocument()

    const sq = screen.getByRole('region', { name: 'Signal quality' })
    expect(within(sq).getByText(/Waiting for live\.py/)).toBeInTheDocument()

    const sys = screen.getByRole('region', { name: 'System' })
    expect(within(sys).getByText('P3 4.9, Pz 3.6, P4 4.0. Passes (≥ 1.2)')).toBeInTheDocument()
    expect(within(sys).getByText('None')).toBeInTheDocument()   // excluded channel
  })

  it('Full width (D-F6-301 (6)): fills a wider screen, 900 px high, columns 5 / 6 / 5 of 16 in the same order', async () => {
    mockApi({ [`GET /api/research/sessions/${SID}/live`]: () => json(snapshot()) })
    renderApp(`/monitor/${SID}`)
    const main = await screen.findByRole('main')
    expect(main.className).toContain('grid-cols-[minmax(0,5fr)_minmax(0,6fr)_minmax(0,5fr)]')
    const frame = main.parentElement!
    const classes = Array.from(frame.classList)
    expect(classes).toEqual(expect.arrayContaining(['w-full', 'min-w-[1440px]', 'h-[900px]']))
    expect(classes).not.toContain('w-[1440px]')
    const cols = Array.from(main.children).map((c) => Array.from(c.querySelectorAll('section')).map((s) => s.getAttribute('aria-label')))
    expect(cols).toEqual([['Signal quality', 'System'], ['Live indices', 'Adaptation decisions'], ['Sync', 'Channel traces, 8 channels, last 20 seconds', 'Events']])
  })

  it('says Not counted without a band, and Reference after S6 before the first decision', async () => {
    const s = snapshot({ indices: { reference: null, last: null, windows: { counted: 0, with_eeg: 0 }, trace: [] } })
    mockApi({ [`GET /api/research/sessions/${SID}/live`]: () => json(s) })
    renderApp(`/monitor/${SID}`)
    const ind = await screen.findByRole('region', { name: 'Live indices' })
    expect(within(ind).getAllByText('Reference after S6').length).toBeGreaterThan(0)
  })

  it('MI on: the whole session per epoch, chips, the S6 line and the legend (D-F6-277, D-F6-280)', async () => {
    const S = (n: number) => ['S1_WELCOME_ORIENTATION', 'S4_EEG_BASELINE', 'S5_STANDARDIZED_LEARNING',
      'S6_GUIDED_PRACTICE_CALIBRATION', 'S7_EXPERIMENTAL_RETRIEVAL'][n]!
    const ep = (i: number, state: string, valid: boolean, unit: 'ln' | 'z', ei: number | null, trial: string | null = null) =>
      ({ i, start_ms: i * 2500, state, trial_id: trial, valid, grey: false, excluded: null, unit, ei, theta: ei })
    const session = {
      stages: [0, 1, 2, 3, 4].map((n) => ({ state: S(n), ms: n * 100_000 })),
      eyes_closed_ms: [160_000, 205_000],
      ica: { identified: false, corr: 0.55, reason: 'corr with Fp1 0.55 < 0.7', switched_to_nosound_at: null, switch_reason: null },
      epochs: [ep(1, S(0), true, 'ln', -1.0), ep(41, S(1), true, 'ln', -0.9), ep(85, S(2), true, 'z', 0.3),
        ep(121, S(3), false, 'ln', null), ep(122, S(3), true, 'ln', -1.1), ep(161, S(4), true, 'z', -0.4, 'S7-001'),
        ep(162, S(4), false, 'z', null, 'S7-001')],
    }
    const s = snapshot({ indices: { ...snapshot().indices, session } })
    mockApi({ [`GET /api/research/sessions/${SID}/live`]: () => json(s) })
    renderApp(`/monitor/${SID}`)
    const ind = await screen.findByRole('region', { name: 'Live indices' })
    expect(within(ind).getByText('For viewing only. Decisions use 3-trial windows from S7.')).toBeInTheDocument()
    expect(within(ind).getByText('Rule: (2) fallback')).toBeInTheDocument()
    expect(within(ind).getByText('z vs S6 (rule 2)')).toBeInTheDocument()
    expect(within(ind).getByText('EEG counted in 8 of 9')).toBeInTheDocument()
    expect(within(ind).getAllByText('ICA not found, rule (2) from here').length).toBe(1)
    expect(within(ind).getByText('Not valid under the active rule')).toBeInTheDocument()
    expect(within(ind).getAllByText('After trial 11').length).toBe(2)   // a readout beside each strip's name
    // one segment per epoch, by colour: the invalid ones are red (D-F6-293 (6)); 2 strips
    expect(ind.querySelectorAll('[data-epoch="invalid"]').length).toBe(2 * 2)
    expect(ind.querySelectorAll('[data-point]').length).toBe(2 * 2)   // decisions at trials 11 and 9, in each strip
  })

  it('MI on: an epoch with no state yet (before the first STATE_ENTERED) does not break the monitor', async () => {
    const base = snapshot()
    const s = { ...base, indices: { ...base.indices, session: { stages: [], eyes_closed_ms: null, ica: null,
      epochs: [{ i: 0, start_ms: 0, state: null, trial_id: null, valid: false, grey: false, excluded: null, unit: 'z', ei: null, theta: null }] } } }
    mockApi({ [`GET /api/research/sessions/${SID}/live`]: () => json(s) })
    renderApp(`/monitor/${SID}`)
    const ind = await screen.findByRole('region', { name: 'Live indices' })
    expect(ind.querySelectorAll('[data-epoch]').length).toBe(2)
  })

  it('MI on before S4: says the indices start at the end of S3 (D-F6-293 (4))', async () => {
    const base = snapshot()
    const s = { ...base, session: { ...base.session, stage: 'S2_VR_TUTORIAL' },
      indices: { reference: null, last: null, windows: { counted: 0, with_eeg: 0 }, trace: [],
        session: { stages: [{ state: 'S1_WELCOME_ORIENTATION', ms: 0 }, { state: 'S2_VR_TUTORIAL', ms: 40_000 }],
          eyes_closed_ms: null, ica: null, epochs: [] } }, decisions: [] }
    mockApi({ [`GET /api/research/sessions/${SID}/live`]: () => json(s) })
    renderApp(`/monitor/${SID}`)
    const ind = await screen.findByRole('region', { name: 'Live indices' })
    expect(within(ind).getByText('Indices from the end of S3')).toBeInTheDocument()
    expect(within(ind).getByText('Raw, no reference yet')).toBeInTheDocument()
    expect(within(ind).queryByText(/Rule:/)).not.toBeInTheDocument()
  })

  // ---------- MI outside S7 (D-F6-308 (3), D-F6-309 (4), D-F6-320): view "window" from MONITOR_INDICES_WINDOW ----------
  const ST = { s1: 'S1_WELCOME_ORIENTATION', s4: 'S4_EEG_BASELINE', s5: 'S5_STANDARDIZED_LEARNING',
    s6: 'S6_GUIDED_PRACTICE_CALIBRATION', s7: 'S7_EXPERIMENTAL_RETRIEVAL', s8: 'S8_IMMEDIATE_ASSESSMENT' }
  const wep = (i: number, state: string, start: number, ln: number | null, over: object = {}) => ({
    i, start_ms: start, end_ms: start + 2000, state, trial_id: null, valid: ln != null, grey: false, excluded: null,
    unit: 'ln', ei: ln, theta: ln, ln_ei: ln, ln_theta: ln, ...over })
  const windowSnap = (stage: string, elapsed: number, session: object, over: object = {}) => {
    const base = snapshot()
    return { ...base, session: { ...base.session, stage, elapsed_ms: elapsed },
      indices: { ...base.indices, session: { view: 'window', eyes_closed_ms: null, ica: null, ...session } }, ...over }
  }
  const showIndices = async (s: object) => {
    mockApi({ [`GET /api/research/sessions/${SID}/live`]: () => json(s) })
    renderApp(`/monitor/${SID}`)
    return screen.findByRole('region', { name: 'Live indices' })
  }

  it('MI window outside S7: the last 20 s in ln on a fixed scale, with a stage line and no z', async () => {
    const s = windowSnap(ST.s5, 225_000, {
      stages: [{ state: ST.s1, ms: 0 }, { state: ST.s4, ms: 100_000 }, { state: ST.s5, ms: 210_000 }],
      epochs: [wep(1, ST.s4, 100_000, -1.0), wep(2, ST.s4, 206_000, -1.2),
        wep(3, ST.s5, 212_000, -1.5, { ln_theta: -2.0 }), wep(4, ST.s5, 214_500, -1.0, { ln_theta: -3.5 })],
    })
    const ind = await showIndices(s)
    const ei = within(ind).getByRole('img', { name: 'Engagement Index, last 20 seconds, log values' })
    const th = within(ind).getByRole('img', { name: 'Theta (Fz), last 20 seconds, log values' })
    expect(ei.querySelectorAll('[data-dot]').length).toBe(3)       // the epoch at 100 s is out of the window
    expect(ei.querySelectorAll('[data-join]').length).toBe(1)      // no join across the S5 line
    expect(within(ei).getByText('S5')).toBeInTheDocument()
    const tick = (svg: Element, v: string) => Number(svg.querySelector(`[data-tick="${v}"]`)!.getAttribute('y1'))
    const cy = (svg: Element, i: number) => Number(svg.querySelector(`[data-dot="${i}"]`)!.getAttribute('cy'))
    expect(cy(ei, 3)).toBeCloseTo((tick(ei, '-3.0') + tick(ei, '0.0')) / 2)   // −1.5 is the middle of −3.0..0.0
    expect(cy(th, 4)).toBeCloseTo(tick(th, '-3.5'))                         // fixed scale, not fitted to the data
    for (const t of ['−3.0', '−1.5', '0.0', '−3.5', '−2.0', '−0.5', '−20 s', '−4', 'Now']) {
      expect(within(ind).getAllByText(t).length).toBeGreaterThan(0)
    }
    expect(within(ind).getByText('Raw, no decisions yet')).toBeInTheDocument()
    expect(within(ind).getByText('Updates with each epoch, every 2.5 s.')).toBeInTheDocument()
    expect(within(ind).queryByText('Lead line (−1.5)')).not.toBeInTheDocument()
    expect(within(ind).queryByText(/EEG counted/)).not.toBeInTheDocument()
    expect(within(ind).queryByText(/After trial/)).not.toBeInTheDocument()
  })

  it('MI window: the ICA status line beside the rule chip, in its four forms', async () => {
    const at = 852_000   // 00:14:12
    const s6 = { stages: [{ state: ST.s6, ms: 851_000 }], epochs: [wep(1, ST.s6, 860_000, -1.0)] }
    const line = async (ica: object | null, stage = ST.s6) => {
      const ind = await showIndices(windowSnap(stage, 870_000, { ...s6, ica }))
      const text = within(ind).getByTestId('ica-line').textContent
      document.body.innerHTML = ''
      return text
    }
    expect(await line(null)).toBe('Fitting ICA')
    expect(await line({ identified: true, corr: 0.79, at_ms: at, switch_ms: null, switch_channel: null,
      switched_to_nosound_at: null })).toBe('ICA applied at 00:14:12, r 0.79')
    expect(await line({ identified: false, corr: 0.55, at_ms: at, switch_ms: null, switch_channel: null,
      switched_to_nosound_at: null })).toBe('ICA not found at 00:14:12, rule (2) from here')
    expect(await line({ identified: true, corr: 0.8, at_ms: at, switch_ms: 1_180_000, switch_channel: 'Cz',
      switched_to_nosound_at: 9.5 }, ST.s8)).toBe('Cz excluded at 00:19:40, rule (2) from here')
    expect(await line({ identified: true, corr: 0.8, at_ms: at, switch_ms: 1_180_000, switch_channel: null,
      switched_to_nosound_at: 9.5 }, ST.s8)).toBe('Rule (2) from 00:19:40')   // provisional text (D-F6-320 (3) (b))
  })

  it('MI window: a switch to rule (2) with no time yet still reads as rule (2), as the reference chip (//review)', async () => {
    const ica = { identified: true, corr: 0.8, at_ms: 852_000, switch_ms: null, switch_channel: 'Cz', switched_to_nosound_at: 9.5 }
    const ind = await showIndices(windowSnap(ST.s7, 1_307_000, { stages: [{ state: ST.s7, ms: 1_200_000 }], ica, epochs: [] }))
    expect(within(ind).getByText('Rule: (2) fallback')).toBeInTheDocument()
    expect(within(ind).getByText('z vs S6 (rule 2)')).toBeInTheDocument()
    expect(within(ind).getByTestId('ica-line').textContent).toBe('Cz excluded at —, rule (2) from here')
  })

  it('MI window in S7: stage S7 alone in z against S6, its decision points, and the S8–S9 chip after it', async () => {
    const s7 = 1_200_000
    const session = {
      stages: [{ state: ST.s6, ms: 1_100_000 }, { state: ST.s7, ms: s7 }],
      ica: { identified: true, corr: 0.8, at_ms: 1_101_000, switch_ms: null, switch_channel: null, switched_to_nosound_at: null },
      epochs: [wep(1, ST.s6, 1_190_000, -1.0),
        wep(2, ST.s7, s7 + 5_000, -1.0, { unit: 'z', ei: -0.4, theta: 0.2, trial_id: 'S7-001' }),
        wep(3, ST.s7, s7 + 7_500, -1.0, { unit: 'z', ei: -1.2, theta: 0.1, trial_id: 'S7-002' })],
    }
    const ind = await showIndices(windowSnap(ST.s7, 1_307_000, session))
    const ei = within(ind).getByRole('img', { name: 'Engagement Index, stage S7, z against S6' })
    expect(ei.querySelectorAll('[data-epoch]').length).toBe(2)     // no S6 epoch in the S7 view
    expect(ei.querySelectorAll('[data-point]').length).toBe(2)     // decisions at trials 11 and 9
    expect(within(ei).getByText('Lead line (−1.5)')).toBeInTheDocument()
    expect(within(ind).getByText('Trial 1')).toBeInTheDocument()
    expect(within(ind).getByText('z vs S6 (ICA)')).toBeInTheDocument()
    expect(within(ind).getByText('EEG counted in 8 of 9')).toBeInTheDocument()
    expect(within(ind).getAllByText('After trial 11').length).toBe(2)
    expect(within(ind).getByTestId('ica-line').textContent).toBe('ICA applied at 00:18:21, r 0.80')
    document.body.innerHTML = ''
    const after = await showIndices(windowSnap(ST.s8, 1_600_000, { ...session, stages: [...session.stages,
      { state: ST.s8, ms: 1_590_000 }], epochs: [...session.epochs, wep(9, ST.s8, 1_592_000, -1.1)] }))
    expect(within(after).getByText('Raw, no decisions after S7')).toBeInTheDocument()
    expect(within(after).getByRole('img', { name: 'Engagement Index, last 20 seconds, log values' })).toBeInTheDocument()
  })

  it('/monitor follows the session in progress, and waits when there is none', async () => {
    mockApi({ 'GET /api/research/live/current': () => json({ detail: 'no session in progress' }, 404) })
    renderApp('/monitor')
    expect(await screen.findByText('Waiting for a new session')).toBeInTheDocument()
  })
})

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

  it('says Not counted without a band, and Reference after S6 before the first decision', async () => {
    const s = snapshot({ indices: { reference: null, last: null, windows: { counted: 0, with_eeg: 0 }, trace: [] } })
    mockApi({ [`GET /api/research/sessions/${SID}/live`]: () => json(s) })
    renderApp(`/monitor/${SID}`)
    const ind = await screen.findByRole('region', { name: 'Live indices' })
    expect(within(ind).getAllByText('Reference after S6').length).toBeGreaterThan(0)
  })

  it('/monitor follows the session in progress, and waits when there is none', async () => {
    mockApi({ 'GET /api/research/live/current': () => json({ detail: 'no session in progress' }, 404) })
    renderApp('/monitor')
    expect(await screen.findByText('Waiting for a new session')).toBeInTheDocument()
  })
})

import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { json, mockApi } from '@/test/api'
import { renderApp } from '@/test/render'
import { clippedLastSecond, columns, nowLabel, WINDOW_MS } from './traceMath'

const SID = 'b7d2e019-0000-0000-0000-000000000000'
const LABELS = ['Fp1', 'F3', 'Fz', 'F4', 'Cz', 'P3', 'Pz', 'P4']
const bin = (t_ms: number, lo = -10, hi = 10) => ({ t_ms, mins: Array(8).fill(lo), maxs: Array(8).fill(hi) })

const live = {
  generated_at: '2026-11-26T20:00:00+09:00',
  session: { session_id: SID, external_code: 'TEST2603', condition: 'STATIC', set: 'A', visit: 1, status: 'IN_PROGRESS',
    stage: 'S3_SYSTEM_VALIDATION', stage_entered_ms: 30_000, elapsed_ms: 41_000 },
  sync: null, indices: { reference: null, last: null, windows: { counted: 0, with_eeg: 0 }, trace: [] },
  decisions: [], events: [], system: null, signal_quality: null,
}

afterEach(() => vi.unstubAllGlobals())

describe('Channel traces, pure parts (TR4)', () => {
  it('min/max per pixel column over the last 20 s, gaps stay empty', () => {
    const now = 40_000
    const cols = columns([bin(now - WINDOW_MS - 40), bin(now - 10_000, -5, 7), bin(now - 9_990, -9, 3), bin(now)], 0, 200, now)
    expect(cols).toHaveLength(200)
    expect(cols[100]).toEqual({ lo: -9, hi: 7 })   // two bins in one pixel: min of mins, max of maxs
    expect(cols[199]).toEqual({ lo: -10, hi: 10 })
    expect(cols.filter(Boolean)).toHaveLength(2)    // the bin older than 20 s is not drawn
  })

  it('«▲» only for a sample out of the lane in the last second, at the chosen scale', () => {
    const now = 40_000
    expect(clippedLastSecond([bin(now - 500, -20, 152)], 4, now, 100)).toBe(true)
    expect(clippedLastSecond([bin(now - 500, -20, 152)], 4, now, 200)).toBe(false)
    expect(clippedLastSecond([bin(now - 1500, -20, 152)], 4, now, 100)).toBe(false)
  })

  it('the value column: whole µV, mV from 1 mV, ▲, — and excluded', () => {
    expect(nowLabel(15.4, false, false)).toBe('15')
    expect(nowLabel(2400, false, false)).toBe('2.4 mV')
    expect(nowLabel(35, true, false)).toBe('35 ▲')
    expect(nowLabel(null, false, false)).toBe('—')
    expect(nowLabel(12, false, true)).toBe('excluded')
  })
})

describe('Channel traces panel (TR4)', () => {
  it('sits between Sync and Events, with the scale pills and each channel’s «Now» value', async () => {
    mockApi({
      [`GET /api/research/sessions/${SID}/live`]: () => json(live),
      [`GET /api/research/sessions/${SID}/live/traces?since=-1`]: () => json({
        on: true, reason: null, labels: LABELS, bins: [bin(40_000), bin(40_040, -10, 160)],
        now: { rms_uv: [15, 14, 13, 12, 2400, null, 11, 10], t_ms: 40_040, taps: [39_000], age_s: 0.3 },
        stages: [{ state: 'S3_SYSTEM_VALIDATION', ms: 30_000 }], excluded: 'Pz' }),
    })
    renderApp(`/monitor/${SID}`)
    const panel = await screen.findByRole('region', { name: 'Channel traces, 8 channels, last 20 seconds' })
    expect(await within(panel).findByText('Live, every 0.25 s')).toBeInTheDocument()
    expect(within(panel).getByRole('button', { name: '±100 µV' })).toHaveAttribute('aria-pressed', 'true')
    const values = within(within(panel).getByRole('list', { name: 'µV rms, 1 s' })).getAllByRole('listitem').map((li) => li.textContent)
    expect(values).toEqual(['15 ▲', '14 ▲', '13 ▲', '12 ▲', '2.4 mV ▲', '—', 'excluded', '10 ▲'])
    const right = screen.getByRole('region', { name: 'Sync' }).parentElement!
    expect(Array.from(right.querySelectorAll('section')).map((s) => s.getAttribute('aria-label')))
      .toEqual(['Sync', 'Channel traces, 8 channels, last 20 seconds', 'Events'])
  })

  it('switch off: only the title and where the raw signal is, and no more polling', async () => {
    const calls = mockApi({
      [`GET /api/research/sessions/${SID}/live`]: () => json(live),
      [`GET /api/research/sessions/${SID}/live/traces?since=-1`]: () => json({
        on: false, reason: 'Channel traces are off (EEG_MONITOR_TRACES)', labels: LABELS, bins: [], now: null, stages: [],
        excluded: null }),
    })
    renderApp(`/monitor/${SID}`)
    const panel = await screen.findByRole('region', { name: 'Channel traces' })
    expect(within(panel).getByText('Channel traces are off for this session.')).toBeInTheDocument()
    expect(within(panel).getByText('The raw signal is in the AURA software.')).toBeInTheDocument()
    await new Promise((r) => setTimeout(r, 700))   // past two 250 ms polls
    expect(calls.filter((c) => c.key.includes('/live/traces'))).toHaveLength(1)
  })
})

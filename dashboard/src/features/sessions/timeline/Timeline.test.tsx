import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { Schemas } from '@/api/client'
import { json, mockApi } from '@/test/api'
import { renderApp } from '@/test/render'

vi.mock('./TimelineChart', () => ({ AXIS_HEIGHT: 28, TimelineChart: () => null }))   // no canvas in jsdom

const ID = 'a5748886-55f2-408b-9779-d88b935773e9'
const DETAIL = {
  session_id: ID, participant_id: 'p1', external_code: 'DEV_UNITY', condition: 'STATIC', status: 'ABORTED',
  visit_number: 1, created_at: '2026-10-15T09:06:00Z', projection_status: 'PROJECTED', trial_count: 1,
  decision_count: null, accuracy: null, open_error_count: 0, kanji_set: 'A', started_at: null,
  first_block: 'S5_STANDARDIZED_LEARNING', last_block: 'S5_STANDARDIZED_LEARNING', states: [],
  mean_rt_ms: null, rt_cv_mean: null, hint_requests: 0, proactive_hints: 0, head_away_count: null,
  head_away_ms: null, adaptations: null,
}

function show(timeline: Schemas['SessionTimeline']) {
  mockApi({
    [`GET /api/research/sessions/${ID}`]: () => json(DETAIL),
    [`GET /api/research/sessions/${ID}/timeline`]: () => json(timeline),
  })
  renderApp(`/sessions/${ID}`)
}

const BASE: Schemas['SessionTimeline'] = {
  session_end_ms: 400_000,
  states: [
    { state: 'S5_STANDARDIZED_LEARNING', start_ms: 0, end_ms: 100_000 },
    { state: 'S7_EXPERIMENTAL_RETRIEVAL', start_ms: 100_000, end_ms: 300_000 },
  ],
  environment: null,
  assistance: [],
  trials: [{ trial_id: 'S7-001', block_state: 'S7_EXPERIMENTAL_RETRIEVAL', start_ms: 110_000, end_ms: 115_000, is_correct: true }],
}

describe('timeline (V1.3, lanes 1-4)', () => {
  it('labels the lanes in order and says why a lane is empty', async () => {
    show(BASE)
    const t = await screen.findByRole('region', { name: 'Session timeline' })
    expect(await within(t).findByRole('heading', { name: 'Timeline' })).toBeInTheDocument()
    expect(within(t).getAllByText(/^(Game Flow|Environment|Assistance|Trials)$/).map((e) => e.textContent))
      .toEqual(['Game Flow', 'Environment', 'Assistance', 'Trials'])
    expect(t).toHaveTextContent('Not recorded in this session')     // environment
    expect(t).toHaveTextContent('Nothing in this session')          // assistance
    expect(within(t).getAllByText(/^(Correct|Incorrect|Not answered|Not completed \(session ended\))$/).map((e) => e.textContent))
      .toEqual(['Correct', 'Incorrect', 'Not answered', 'Not completed (session ended)'])
  })

  it('switches between the whole session and S7 from the keyboard', async () => {
    const user = userEvent.setup()
    show(BASE)
    const whole = await screen.findByRole('button', { name: 'Whole session' })
    const s7 = screen.getByRole('button', { name: 'Only S7' })
    expect(whole).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByText('Showing 00:00 to 06:40 of the session.')).toBeInTheDocument()
    s7.focus()
    await user.keyboard('{Enter}')
    expect(s7).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByText('Showing 01:40 to 05:00 of the session.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Zoom in' }))
    expect(screen.getByText('Showing 02:30 to 04:10 of the session.')).toBeInTheDocument()
    await user.click(whole)
    expect(screen.getByRole('button', { name: 'Zoom out' })).toBeDisabled()
  })

  it('disables Only S7 when the session never reached it', async () => {
    show({ ...BASE, states: BASE.states!.slice(0, 1) })
    expect(await screen.findByRole('button', { name: 'Only S7' })).toBeDisabled()
  })
})

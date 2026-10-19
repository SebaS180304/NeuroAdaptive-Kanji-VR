import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { Schemas } from '@/api/client'
import { json, mockApi } from '@/test/api'
import { renderApp } from '@/test/render'

vi.mock('../timeline/TimelineChart', () => ({ AXIS_HEIGHT: 28, PLOT_INSET: 24, TimelineChart: () => null }))   // no canvas in jsdom

type Plan = Schemas['SessionPlan']
type Block = Plan['blocks'][number]
const ID = 'a5748886-55f2-408b-9779-d88b935773e9'

const block = (code: string, state: string, statuses: string, over: Partial<Block> = {}): Block => {
  const trials = [...statuses].map((c, i) => ({
    trial_id: `${code}-${String(i + 1).padStart(3, '0')}`,
    status: ({ C: 'COMPLETED', S: 'STARTED', N: 'NEVER_SHOWN' } as const)[c as 'C' | 'S' | 'N'],
  }))
  return {
    block_state: state, kanji_set: 'A', block_seed: '196156604', planned: trials.length,
    started: trials.filter((t) => t.status !== 'NEVER_SHOWN').length, completed: trials.filter((t) => t.status === 'COMPLETED').length,
    min_lag_requested: 2, min_lag_achieved: 3, kanji_repeats: true, trials, ...over,
  }
}
const ABORTED: Plan = {
  last_state: 'S6_GUIDED_PRACTICE_CALIBRATION', last_state_ms: 557_677,
  blocks: [
    block('S2', 'S2_VR_TUTORIAL', 'CCC'),
    block('S5', 'S5_STANDARDIZED_LEARNING', 'CCCCC', { min_lag_achieved: null, kanji_repeats: false, min_lag_requested: 0 }),
    block('S6', 'S6_GUIDED_PRACTICE_CALIBRATION', 'CCCSNNNNN'),
  ],
}
const COMPLETE: Plan = {
  last_state: 'S9_SESSION_SUMMARY', last_state_ms: 385_009,
  blocks: [
    block('S2', 'S2_VR_TUTORIAL', 'CCC'), block('S5', 'S5_STANDARDIZED_LEARNING', 'CCCCC'),
    block('S6', 'S6_GUIDED_PRACTICE_CALIBRATION', 'CCCCCCCCC'), block('S7', 'S7_EXPERIMENTAL_RETRIEVAL', 'CCCC'),
    block('S8', 'S8_IMMEDIATE_ASSESSMENT', 'CCC'),
  ],
}

async function show(plan: Plan, status = 'ABORTED') {
  mockApi({
    [`GET /api/research/sessions/${ID}`]: () => json({
      session_id: ID, participant_id: 'p1', external_code: 'DEV_UNITY', condition: 'STATIC', status, visit_number: 1,
      created_at: '2026-10-14T09:06:00Z', projection_status: 'PROJECTED', trial_count: 12, decision_count: null,
      accuracy: null, open_error_count: 0, kanji_set: 'A', started_at: null, first_block: 'S2_VR_TUTORIAL',
      last_block: 'S6_GUIDED_PRACTICE_CALIBRATION', states: [], mean_rt_ms: null, rt_cv_mean: null, hint_requests: 0,
      proactive_hints: 0, head_away_count: null, head_away_ms: null, adaptations: null,
    }),
    [`GET /api/research/sessions/${ID}/timeline`]: () => json({
      session_end_ms: null, states: null, environment: null, assistance: null, trials: null,
      hints: null, peripherals: null, distractors: null, head_away: null, adaptations: null,
    }),
    [`GET /api/research/sessions/${ID}/trials?window_n=3`]: () => json([]),
    [`GET /api/research/sessions/${ID}/plan`]: () => json(plan),
  })
  renderApp(`/sessions/${ID}`)
  await userEvent.setup().click(await screen.findByRole('tab', { name: 'Plan and execution' }))
  return screen.findByRole('table', { name: 'Plan and execution' })
}

describe('Plan and execution tab (V1.6)', () => {
  it('shows one row per block with its trial squares and counts', async () => {
    const table = await show(ABORTED)
    expect(within(table).getAllByRole('columnheader').map((h) => h.textContent)).toEqual([
      'Block', 'Planned trials, in order', 'Planned', 'Started', 'Completed', 'Seed', 'Min lag',
    ])
    const s6 = within(table).getByRole('row', { name: /S6/ })
    expect(within(s6).getByRole('img', { name: 'S6: 3 of 9 planned trials completed' })).toBeInTheDocument()
    const squares = within(s6).getByRole('img').querySelectorAll('[data-status]')
    expect(Array.from(squares).map((q) => q.getAttribute('data-status')).join(',')).toBe(
      'COMPLETED,COMPLETED,COMPLETED,STARTED,NEVER_SHOWN,NEVER_SHOWN,NEVER_SHOWN,NEVER_SHOWN,NEVER_SHOWN')
    expect(s6).toHaveTextContent('9431961566043 of 2 requested')   // counts, seed, min lag
    expect(s6).toHaveClass('bg-(--color-warn-tint)')                             // the cut block
    expect(within(table).getByRole('row', { name: /S2/ })).not.toHaveClass('bg-(--color-warn-tint)')
    expect(within(table).getByRole('row', { name: /S5/ })).toHaveTextContent('No kanji repeats')
  })

  it('an aborted session says where it stopped', async () => {
    await show(ABORTED)
    const note = screen.getByRole('complementary', { name: 'Where the session stopped' })
    expect(note).toHaveTextContent(
      'S6 stopped after S6-003. S6-004 started but has no completion, and S6-005 to S6-009 were planned and never shown. ' +
      'No plan was generated for S7 and S8.')
    expect(note).toHaveTextContent('Last state reachedS6, at 09:17.677')
    expect(note).toHaveTextContent('Session statusAborted')
    expect(note).toHaveTextContent('Kanji setA')
    expect(screen.queryByRole('complementary', { name: 'Selected trial' })).toBeNull()
  })

  it('a complete session shows no gap', async () => {
    const table = await show(COMPLETE, 'COMPLETED')
    expect(within(table).getAllByRole('row').filter((r) => r.className.includes('warn-tint'))).toHaveLength(0)
    expect(screen.getByRole('complementary', { name: 'Where the session stopped' }))
      .toHaveTextContent('Every planned trial was completed, in every block.')
  })
})

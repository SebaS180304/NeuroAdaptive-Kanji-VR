import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { Schemas } from '@/api/client'
import { json, mockApi } from '@/test/api'
import { renderApp } from '@/test/render'

vi.mock('../timeline/TimelineChart', () => ({ AXIS_HEIGHT: 28, PLOT_INSET: 24, TimelineChart: () => null }))   // no canvas in jsdom

type Adaptation = Schemas['ResearchAdaptation']
const ID = 'a5748886-55f2-408b-9779-d88b935773e9'

const base: Adaptation = {
  decision_id: '', trial_id: '', decided_elapsed_ms: 0, learner_state: 'STABLE', cause: null, confidence: 1,
  action: 'NO_CHANGE', dimension: null, from_level: null, to_level: null, proactive_cues: false, reason_code: 'STABLE',
  explanation: 'Stable at the current levels.', unity_result: null, skip_reason: null, applied_before_trial_id: null,
  cooldown_until_trial: null, cooldown_until_trial_id: null, outcome: null, estimator_version: 'behavior-v1',
  rules_version: 'rules-v1', indicators: { n: 3 }, thresholds: { rules: { cooldown_trials: 3 } },
}
const CHANGES: Adaptation[] = [
  { ...base, decision_id: 'd4', trial_id: 'S7-004', learner_state: 'DISENGAGED', cause: 'AWAY', confidence: 0.8,
    action: 'CHANGE_ASSISTANCE', dimension: 'LAL', from_level: 'MEDIUM', to_level: 'HIGH', proactive_cues: true,
    reason_code: 'DISENGAGED_AWAY', explanation: 'Raised the assistance from MEDIUM to HIGH: 9 s looking away.',
    unity_result: 'APPLIED', applied_before_trial_id: 'S7-005', cooldown_until_trial: 7, cooldown_until_trial_id: 'S7-007',
    outcome: 'POSITIVE', indicators: { away_ms: 9000, trial_ids: ['S7-002', 'S7-003'] } },
  { ...base, decision_id: 'd10', trial_id: 'S7-010', learner_state: 'STABLE', action: 'CHANGE_ASSISTANCE',
    dimension: 'LAL', from_level: 'HIGH', to_level: 'MEDIUM', unity_result: 'SKIPPED', skip_reason: 'TIMEOUT', outcome: null },
  { ...base, decision_id: 'd12', trial_id: 'S7-012', learner_state: 'OVERLOADED', cause: 'IMPULSIVE', confidence: 0.6,
    action: 'CHANGE_ENVIRONMENT', dimension: 'ESL', from_level: 'MEDIUM', to_level: 'LOW', unity_result: 'APPLIED',
    applied_before_trial_id: 'S7-013', cooldown_until_trial: 15, cooldown_until_trial_id: null, outcome: 'UNCERTAIN' },
]
const EVERY = [{ ...base, decision_id: 'd1', trial_id: 'S7-001' }, ...CHANGES]

function show(condition = 'BEHAVIOR_ADAPTIVE') {
  mockApi({
    [`GET /api/research/sessions/${ID}`]: () => json({
      session_id: ID, participant_id: 'p1', external_code: 'DEV_UNITY', condition, status: 'COMPLETED', visit_number: 1,
      created_at: '2026-10-15T09:06:00Z', projection_status: 'PROJECTED', trial_count: 0, decision_count: 4,
      accuracy: null, open_error_count: 0, kanji_set: 'A', started_at: null, first_block: null, last_block: null,
      states: [], mean_rt_ms: null, rt_cv_mean: null, hint_requests: null, proactive_hints: null,
      head_away_count: null, head_away_ms: null, adaptations: null,
    }),
    [`GET /api/research/sessions/${ID}/timeline`]: () => json({
      session_end_ms: null, states: null, environment: null, assistance: null, trials: null,
      hints: null, peripherals: null, distractors: null, head_away: null, adaptations: null,
    }),
    [`GET /api/research/sessions/${ID}/trials?window_n=3`]: () => json([]),
    [`GET /api/research/sessions/${ID}/adaptations?include_no_change=false`]: () => json(CHANGES),
    [`GET /api/research/sessions/${ID}/adaptations?include_no_change=true`]: () => json(EVERY),
  })
  renderApp(`/sessions/${ID}`)
}

async function openTab() {
  const user = userEvent.setup()
  show()
  await user.click(await screen.findByRole('tab', { name: 'Adaptations' }))
  return { user, table: await screen.findByRole('table', { name: 'Adaptations' }) }
}

const trials = (t: HTMLElement) => within(t).getAllByRole('rowheader').map((r) => r.textContent)

describe('Adaptations tab (V1.5)', () => {
  it('lists the decisions that changed something, full width with no inspector', async () => {
    const { table } = await openTab()
    expect(within(table).getAllByRole('columnheader').map((h) => h.textContent)).toEqual([
      'Expand', 'After trial', 'Estimated state', 'Cause', 'Confidence', 'Change', 'In Unity', 'Cooldown until', 'Outcome',
    ])
    expect(trials(table)).toEqual(['S7-004', 'S7-010', 'S7-012'])
    expect(screen.getByText(/^3 decisions changed something in S7\./)).toBeInTheDocument()
    expect(screen.queryByRole('complementary', { name: 'Selected trial' })).toBeNull()
    expect(screen.getByRole('region', { name: 'Session tables' })).toHaveClass('min-[1056px]:col-span-16')

    const row = within(table).getByRole('row', { name: /S7-004/ })
    expect(row).toHaveTextContent('Disengaged')
    expect(row).toHaveTextContent('Away')
    expect(row).toHaveTextContent('0.80')
    expect(row).toHaveTextContent('Assistance LAL Medium to High, proactive cues')
    expect(row).toHaveTextContent('Applied before S7-005')
    expect(row).toHaveTextContent('S7-007')
    expect(within(table).getByRole('row', { name: /S7-010/ })).toHaveTextContent('Skipped: timeout')
    expect(within(table).getByRole('row', { name: /S7-012/ })).toHaveTextContent('trial 15, not run')
  })

  it('outcome chips carry a shape as well as a colour; a missing outcome says "Not recorded"', async () => {
    const { table } = await openTab()
    const chip = (id: string) => within(within(table).getByRole('row', { name: new RegExp(id) })).getByText(/Positive|Not recorded|Uncertain/)
    expect(chip('S7-004')).toHaveTextContent('Positive')
    expect(chip('S7-004').querySelector('[data-shape]')).toHaveAttribute('data-shape', 'dot')
    expect(chip('S7-010')).toHaveTextContent('Not recorded')
    expect(chip('S7-010')).toHaveClass('border-dashed')
    expect(chip('S7-012').querySelector('[data-shape]')).toHaveAttribute('data-shape', 'hatched-square')
  })

  it('a row expands to the explanation, the versions and the stored indicators and thresholds', async () => {
    const { user, table } = await openTab()
    const expand = within(table).getByRole('button', { name: 'Show indicators for S7-004' })
    expect(expand).toHaveAttribute('aria-expanded', 'false')
    await user.click(expand)
    expect(expand).toHaveAttribute('aria-expanded', 'true')
    const detail = within(table).getByRole('region', { name: 'Decision after S7-004' })
    expect(detail).toHaveTextContent('Why the system changed')
    expect(detail).toHaveTextContent('Raised the assistance from MEDIUM to HIGH: 9 s looking away.')
    expect(detail).toHaveTextContent('Reason code DISENGAGED_AWAY, estimator behavior-v1, rules rules-v1')
    expect(detail).toHaveTextContent('away_ms9000')
    expect(detail).toHaveTextContent('trial_ids["S7-002","S7-003"]')
    expect(detail).toHaveTextContent('rules.cooldown_trials3')
  })

  it('shows decisions with no change on request', async () => {
    const { user } = await openTab()
    await user.click(screen.getByLabelText('Show decisions with no change'))
    expect(trials(await screen.findByRole('table', { name: 'Adaptations' }))).toEqual(['S7-001', 'S7-004', 'S7-010', 'S7-012'])
    const row = within(screen.getByRole('table', { name: 'Adaptations' })).getByRole('row', { name: /S7-001/ })
    expect(row).toHaveTextContent('No change')
    expect(within(row).getByTitle('No change, so no outcome')).toHaveTextContent('—')
  })

  it('a static session says the system makes no decisions', async () => {
    const user = userEvent.setup()
    show('STATIC')
    await user.click(await screen.findByRole('tab', { name: 'Adaptations' }))
    expect(screen.getByRole('tabpanel')).toHaveTextContent('Static session: the system makes no decisions.')
    expect(screen.queryByRole('table', { name: 'Adaptations' })).toBeNull()
  })
})

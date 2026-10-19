import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { Schemas } from '@/api/client'
import { json, mockApi } from '@/test/api'
import { renderApp } from '@/test/render'
import { flatten } from './flatten'

vi.mock('../timeline/TimelineChart', () => ({ AXIS_HEIGHT: 28, PLOT_INSET: 24, TimelineChart: () => null }))   // no canvas in jsdom

type Trial = Schemas['ResearchTrial']
const ID = 'a5748886-55f2-408b-9779-d88b935773e9'

const base: Trial = {
  trial_id: '', block_state: 'S7_EXPERIMENTAL_RETRIEVAL', trial_sequence: 1, trial_type: 'T1_MEANING_TO_KANJI',
  kanji_id: 'KANJI_YAMA', kanji_char: '山', is_primary_analysis: true, started_elapsed_ms: 200_000, esl: 'MEDIUM',
  lal: 'MEDIUM', env_profile: 'ESL_Medium', prop_count: 5, mover_count: 1, is_correct: true, response_time_ms: 2100,
  timed_out: false, hint_count: 0, cue_trigger: null, idle_ms: 400, head_away_count: null, head_away_ms: null,
  peripheral_event_count: 2, distractor_dwell_ms: 0, window_n: 3, window_accuracy: 0.6667, window_rt_mean: 2000,
  window_rt_cv: 0.2, learner_state: null, cause: null, decision_confidence: null, decision_action: null,
  reason_code: null, explanation: null, dimension: null, from_level: null, to_level: null, unity_result: null,
  skip_reason: null, applied_before_trial_id: null, cooldown_until_trial: null, cooldown_until_trial_id: null,
  outcome: null, estimator_version: null, rules_version: null, indicators: null, thresholds: null,
}
const TRIALS: Trial[] = [
  { ...base, trial_id: 'S2-001', block_state: 'S2_VR_TUTORIAL', is_primary_analysis: false, started_elapsed_ms: 10_000 },
  { ...base, trial_id: 'S7-006', learner_state: 'DISENGAGED', cause: 'AWAY', decision_confidence: 0.8,
    decision_action: 'CHANGE_ENVIRONMENT', reason_code: 'DISENGAGED_AWAY',
    explanation: 'Lowered the environment from MEDIUM to LOW: 14.5 s looking away from the task.',
    dimension: 'ESL', from_level: 'MEDIUM', to_level: 'LOW', unity_result: 'APPLIED', applied_before_trial_id: 'S7-007',
    cooldown_until_trial: 9, cooldown_until_trial_id: 'S7-009', outcome: 'NEUTRAL', estimator_version: 'behavior-v1',
    rules_version: 'rules-v1', indicators: { away_ms: 14500, acc: 0.67 }, thresholds: { away_ms: 8000 } },
  { ...base, trial_id: 'S7-007', is_correct: false, cue_trigger: 'PROACTIVE', hint_count: 1, started_elapsed_ms: 210_000 },
]
const DETAIL = {
  session_id: ID, participant_id: 'p1', external_code: 'DEV_UNITY', condition: 'BEHAVIOR_ADAPTIVE', status: 'COMPLETED',
  visit_number: 1, created_at: '2026-10-15T09:06:00Z', projection_status: 'PROJECTED', trial_count: 3,
  decision_count: 1, accuracy: 0.5, open_error_count: 0, kanji_set: 'A', started_at: null,
  first_block: 'S2_VR_TUTORIAL', last_block: 'S7_EXPERIMENTAL_RETRIEVAL', states: [], mean_rt_ms: 2100,
  rt_cv_mean: null, hint_requests: 0, proactive_hints: 1, head_away_count: null, head_away_ms: null, adaptations: null,
}

function show() {
  const calls = mockApi({
    [`GET /api/research/sessions/${ID}`]: () => json(DETAIL),
    [`GET /api/research/sessions/${ID}/timeline`]: () => json({
      session_end_ms: null, states: null, environment: null, assistance: null, trials: null,
      hints: null, peripherals: null, distractors: null, head_away: null, adaptations: null,
    }),
    [`GET /api/research/sessions/${ID}/trials?window_n=3`]: () => json(TRIALS),
    [`GET /api/research/sessions/${ID}/trials?window_n=5`]: () => json(TRIALS.map((t) => ({ ...t, window_n: 5, window_accuracy: 0.8 }))),
  })
  renderApp(`/sessions/${ID}`)
  return calls
}

const ids = (t: HTMLElement) => within(t).getAllByRole('button', { name: /^S\d-\d{3}/ }).map((b) => b.textContent)

describe('indicators and thresholds as stored', () => {
  it('lists nested values one per line under dotted keys', () => {
    expect(flatten({ n: 3, rules: { cooldown_trials: 3, windows: [1, 2] }, label: 'x', none: null })).toEqual([
      ['n', '3'], ['rules.cooldown_trials', '3'], ['rules.windows', '[1,2]'], ['label', 'x'], ['none', 'null'],
    ])
  })
})

describe('Trials tab and inspector (V1.4)', () => {
  it('shows the twelve columns, with the tutorial hidden by default', async () => {
    show()
    const table = await screen.findByRole('table', { name: 'Trials' })
    expect(within(table).getAllByRole('columnheader').map((h) => h.textContent)).toEqual([
      'Trial', 'Type', 'Kanji', 'ESL', 'LAL', 'RT (ms)', 'Answer', 'Idle (ms)', 'Away (ms)', 'Hints', 'Estimated state', 'Action',
    ])
    expect(ids(table)).toEqual(['S7-006', 'S7-007'])
    const row = within(table).getByRole('row', { name: /S7-006/ })
    expect(row).toHaveTextContent('Meaning to kanji')
    expect(row).toHaveTextContent('Disengaged')
    expect(row).toHaveTextContent('Change environment')
    expect(within(row).getByTitle('Head-away was not recorded in this session')).toHaveTextContent('—')
    expect(within(table).getByRole('row', { name: /S7-007/ })).toHaveTextContent('1 (proactive)')
  })

  it('marks the tutorial and lets it be shown', async () => {
    const user = userEvent.setup()
    show()
    const table = await screen.findByRole('table', { name: 'Trials' })
    await user.click(screen.getByLabelText('Hide tutorial (S2)'))
    expect(ids(table)).toEqual(['S2-001', 'S7-006', 'S7-007'])
    expect(within(table).getByRole('row', { name: /S2-001/ })).toHaveTextContent('Tutorial')
  })

  it('selecting a trial fills the inspector, decision included', async () => {
    const user = userEvent.setup()
    show()
    const inspector = await screen.findByRole('complementary', { name: 'Selected trial' })
    expect(inspector).toHaveTextContent('Select a trial in the table or the timeline')
    await user.click(await screen.findByRole('button', { name: 'S7-006' }))
    expect(screen.getByRole('button', { name: 'S7-006' })).toHaveAttribute('aria-pressed', 'true')
    expect(within(inspector).getByRole('heading', { level: 2 })).toHaveTextContent('Trial S7-006')
    expect(inspector).toHaveTextContent('started at 03:20.000')
    expect(inspector).toHaveTextContent('Lowered the environment from MEDIUM to LOW: 14.5 s looking away from the task.')
    expect(inspector).toHaveTextContent('Disengaged, confidence 0.80')
    expect(inspector).toHaveTextContent('ESL Medium to Low')
    expect(inspector).toHaveTextContent('Applied before S7-007')
    expect(inspector).toHaveTextContent('S7-009')
    expect(inspector).toHaveTextContent('Neutral')
    expect(inspector).toHaveTextContent('66.7 %')
    await user.click(within(inspector).getByRole('button', { name: 'Show indicators and thresholds' }))
    expect(inspector).toHaveTextContent('away_ms14500')
    expect(inspector).toHaveTextContent('away_ms8000')
  })

  it('a trial with no decision says so in the inspector', async () => {
    const user = userEvent.setup()
    show()
    await user.click(await screen.findByRole('button', { name: 'S7-007' }))
    const inspector = screen.getByRole('complementary', { name: 'Selected trial' })
    expect(inspector).not.toHaveTextContent('Why the system changed')
    expect(inspector).toHaveTextContent('No decision after this trial')
  })

  it('the window size changes the aggregates', async () => {
    const user = userEvent.setup()
    const calls = show()
    await user.click(await screen.findByRole('button', { name: 'S7-006' }))
    await user.selectOptions(screen.getByLabelText('Window'), '5 trials')
    expect(calls.map((c) => c.key)).toContain(`GET /api/research/sessions/${ID}/trials?window_n=5`)
    expect(await within(screen.getByRole('complementary', { name: 'Selected trial' })).findByText('80.0 %')).toBeInTheDocument()
  })

  it('the other tabs are reserved until their tasks, and tabs move with the arrow keys', async () => {
    const user = userEvent.setup()
    show()
    const trialsTab = await screen.findByRole('tab', { name: 'Trials' })
    expect(trialsTab).toHaveAttribute('aria-selected', 'true')
    trialsTab.focus()
    await user.keyboard('{ArrowRight}')
    const adaptations = screen.getByRole('tab', { name: 'Adaptations' })
    expect(adaptations).toHaveAttribute('aria-selected', 'true')
    expect(adaptations).toHaveFocus()
    expect(screen.getByRole('tabpanel')).toHaveTextContent('available in a later version')
  })
})

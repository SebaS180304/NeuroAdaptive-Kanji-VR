import { screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { Schemas } from '@/api/client'
import { json, mockApi } from '@/test/api'
import { renderApp } from '@/test/render'

type Detail = Schemas['ResearchSessionDetail']

vi.mock('./timeline/TimelineChart', () => ({ AXIS_HEIGHT: 28, PLOT_INSET: 24, TimelineChart: () => null }))   // no canvas in jsdom

const ID = 'a5748886-55f2-408b-9779-d88b935773e9'
const ADAPTIVE: Detail = {
  session_id: ID, participant_id: 'p1', external_code: 'DEV_UNITY', condition: 'BEHAVIOR_ADAPTIVE',
  status: 'COMPLETED', visit_number: 1, created_at: '2026-10-15T09:06:00Z', projection_status: 'PROJECTED',
  trial_count: 52, decision_count: 20, accuracy: 0.7959, open_error_count: 0, last_state: 'S9_SESSION_SUMMARY', kanji_set: 'A',
  started_at: '2026-10-15T09:06:00Z', first_block: 'S2_VR_TUTORIAL', last_block: 'S8_IMMEDIATE_ASSESSMENT',
  states: [
    { state: 'S0_SYSTEM_CHECK', entered_elapsed_ms: 0, exited_elapsed_ms: 60_000 },
    { state: 'S5_STANDARDIZED_LEARNING', entered_elapsed_ms: 60_000, exited_elapsed_ms: 120_000 },
    { state: 'S7_EXPERIMENTAL_RETRIEVAL', entered_elapsed_ms: 120_000, exited_elapsed_ms: 300_000 },
    { state: 'S9_SESSION_END', entered_elapsed_ms: 300_000, exited_elapsed_ms: null },   // the end, not a cut
  ],
  mean_rt_ms: 3003.1, rt_cv_mean: 0.3317, hint_requests: 2, proactive_hints: 1,
  head_away_count: 14, head_away_ms: 37_618,
  adaptations: {
    decisions: 20, environment_changes: 2, assistance_changes: 1, skipped_by_unity: 1,
    outcome_positive: 1, outcome_neutral: 1, outcome_negative: 0, outcome_uncertain: 0, outcome_not_recorded: 1,
  },
}
const STATIC: Detail = {
  ...ADAPTIVE, condition: 'STATIC', decision_count: null, adaptations: null,
  head_away_count: null, head_away_ms: null, rt_cv_mean: null, open_error_count: 2,
  states: [...ADAPTIVE.states.slice(0, 2), { state: 'S7_EXPERIMENTAL_RETRIEVAL', entered_elapsed_ms: 120_000, exited_elapsed_ms: null }],
}

function show(detail: Detail | null) {
  mockApi({
    [`GET /api/research/sessions/${ID}`]: () => (detail ? json(detail) : json({ detail: 'session not found' }, 404)),
    [`GET /api/research/sessions/${ID}/timeline`]: () =>
      json({ session_end_ms: null, states: null, environment: null, assistance: null, trials: null }),
  })
  renderApp(`/sessions/${ID}`)
}

describe('Session View header and summary (V1.2)', () => {
  it('builds the lead sentence and the facts from the data', async () => {
    show(ADAPTIVE)
    expect(await screen.findByRole('heading', { level: 1, name: 'Session a5748886' })).toBeInTheDocument()
    expect(await screen.findByText(
      'Behavior-adaptive session, visit 1, kanji set A. 52 trials from S2 to S8. The system changed the ' +
      'environment 2 times and the assistance 1 time; Unity skipped 1 of those changes.',
    )).toBeInTheDocument()
    const facts = screen.getByRole('complementary', { name: 'Session facts' })
    expect(within(facts).getByRole('link', { name: 'DEV_UNITY' })).toHaveAttribute('href', '/participants/p1')
    expect(facts).toHaveTextContent('Completed')
    expect(facts).toHaveTextContent('No open projection errors')
    expect(within(screen.getByRole('main')).getByRole('link', { name: 'Sessions' })).toHaveAttribute('href', '/sessions')
  })

  it('shows where the time went: states, accuracy and behavior', async () => {
    show(ADAPTIVE)
    const time = await screen.findByRole('region', { name: 'Where the time went' })
    expect(within(time).getByRole('img', { name: 'Duration per Game Flow state: S0 1:00, S5 1:00, S7 3:00' })).toBeInTheDocument()
    expect(time).toHaveTextContent('79.6 %')
    expect(time).toHaveTextContent('S7 took 60 % of the session.')
    const behavior = within(time).getByRole('table', { name: 'Behavior over answered trials' })
    expect(within(behavior).getByRole('row', { name: /Mean response time/ })).toHaveTextContent('3003 ms')
    expect(within(behavior).getByRole('row', { name: /variability/ })).toHaveTextContent('0.33 CV')
    expect(within(behavior).getByRole('row', { name: /Head-away/ })).toHaveTextContent('14 episodes37.6 s in total')
    expect(within(behavior).getByRole('row', { name: /Hints/ })).toHaveTextContent('2 requests1 proactive')
  })

  it('counts the adaptations by action and outcome', async () => {
    show(ADAPTIVE)
    const block = await screen.findByRole('region', { name: 'Adaptations' })
    expect(block).toHaveTextContent('20 decisions in S7. 3 changed something.')
    expect(within(block).getByText('Change environment').parentElement).toHaveTextContent('2')
    expect(within(block).getByText('Skipped by Unity').parentElement).toHaveTextContent('1')
    expect(within(block).getByRole('img', { name: /Outcomes: 1 positive, 1 neutral, 0 negative, 0 uncertain, 1 not recorded/ })).toBeInTheDocument()
    expect(block).toHaveTextContent('S6 calibration profile: available in a later version.')
  })

  it('a static session has no adaptations, and not-recorded values show a dash with the reason', async () => {
    show(STATIC)
    const block = await screen.findByRole('region', { name: 'Adaptations' })
    expect(block).toHaveTextContent('No adaptations in a static session.')
    expect(screen.getByText(/^Static session, visit 1, kanji set A\. 52 trials from S2 to S8\.$/)).toBeInTheDocument()
    const behavior = screen.getByRole('table', { name: 'Behavior over answered trials' })
    expect(within(behavior).getAllByTitle('Head-away was not recorded in this session')).toHaveLength(2)
    expect(within(behavior).getByTitle('Not enough answered trials for a window')).toHaveTextContent('—')
    expect(screen.getByRole('img', { name: /S7 not finished/ })).toBeInTheDocument()
    expect(screen.getByRole('complementary', { name: 'Session facts' })).toHaveTextContent('2 open projection errors')
  })

  it('an unknown session says so', async () => {
    show(null)
    expect(await screen.findByRole('alert')).toHaveTextContent('Session not found')
  })
})

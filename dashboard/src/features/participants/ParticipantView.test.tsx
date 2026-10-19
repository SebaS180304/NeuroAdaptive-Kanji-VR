import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Schemas } from '@/api/client'
import { json, mockApi } from '@/test/api'
import { renderApp } from '@/test/render'

vi.mock('./TrendChart', async (actual) => ({ ...(await actual()), TrendChart: () => null }))   // no canvas in jsdom

type Detail = Schemas['ResearchParticipantDetail']
type Row = Detail['sessions'][number]

const session: Row = {
  session_id: '', participant_id: 'p1', external_code: 'P01', condition: 'STATIC', status: 'COMPLETED',
  visit_number: 1, created_at: '2026-10-14T05:00:00Z', projection_status: 'PROJECTED', trial_count: 60,
  decision_count: null, accuracy: 0.8, open_error_count: 0, last_state: 'S9_SESSION_SUMMARY',
  mean_rt_ms: 1834.4, head_away_count: 3, head_away_ms: 12_400, before_pretest: false,
}
const DONE: Detail = {
  id: 'p1', external_code: 'P01', created_at: '2026-10-01T03:00:00Z', pretest_status: 'COMPLETED',
  pretest_answered: 18, pretest_completed_at: '2026-10-12T05:00:00Z', session_count: 3,
  conditions: ['STATIC', 'BEHAVIOR_ADAPTIVE'], last_session_at: '2026-10-16T05:00:00Z', last_session_accuracy: 0.9,
  previous_japanese_experience: true, flagged_count: 1,
  sessions: [
    { ...session, session_id: 'aaaaaaaa-0000-0000-0000-000000000001', created_at: '2026-10-10T05:00:00Z', before_pretest: true },
    { ...session, session_id: 'bbbbbbbb-0000-0000-0000-000000000002', condition: 'BEHAVIOR_ADAPTIVE', status: 'ABORTED',
      last_state: 'S7_EXPERIMENTAL_RETRIEVAL', decision_count: 4, accuracy: 0.5, head_away_count: null, head_away_ms: null },
    { ...session, session_id: 'cccccccc-0000-0000-0000-000000000003', condition: 'BEHAVIOR_ADAPTIVE', decision_count: 20,
      accuracy: 0.9, created_at: '2026-10-16T05:00:00Z' },
  ],
  substitutions: [
    { set_name: 'A', original: '山', substitute: '川' },
    { set_name: 'B', original: '水', substitute: null },
  ],
}

function show(detail: Detail) {
  mockApi({ [`GET /api/research/participants/${detail.id}`]: () => json(detail) })
  renderApp(`/participants/${detail.id}`)
}

const facts = () => screen.findByRole('complementary', { name: 'Participant facts' })

describe('participant view (V1.8)', () => {
  beforeEach(() => show(DONE))

  it('says which sessions came before the pre-test, and counts them in the facts', async () => {
    expect(await screen.findByText(
      '1 of 3 sessions was recorded before the pre-test and used the default set. Later sessions used the confirmed set.',
    )).toBeInTheDocument()
    const f = await facts()
    expect(f).toHaveTextContent('Completed 2026-10-12')
    expect(f).toHaveTextContent('2 completed, 1 aborted')
    expect(f).toHaveTextContent('Static, Behavior-adaptive')
    expect(f).toHaveTextContent('Previous Japanese study reported')
    expect(f).toHaveTextContent('Kanji kept with no substitute')
    expect(f).toHaveTextContent('1 session recorded before the pre-test')
  })

  it('lists the sessions in order with the shared status words', async () => {
    const t = await screen.findByRole('table', { name: 'Sessions in order' })
    const rows = within(t).getAllByRole('row').slice(1)
    expect(rows.map((r) => within(r).getAllByRole('cell')[0]!.textContent)).toEqual(['1', '2', '3'])
    expect(rows[0]).toHaveTextContent('Before the pre-test')
    expect(rows[1]).toHaveTextContent('Aborted in S7')
    expect(rows[0]).toHaveTextContent('80.0 %')
    expect(rows[0]).toHaveTextContent('1834 ms')
    expect(rows[0]).toHaveTextContent('3 (12.4 s)')
    expect(within(rows[1]!).getByTitle('Head-away was not recorded in this session')).toHaveTextContent('—')
    expect(within(rows[0]!).getByTitle('No adaptations in a static session')).toHaveTextContent('—')
    expect(within(t).getByRole('link', { name: 'cccccccc' })).toHaveAttribute(
      'href', '/sessions/cccccccc-0000-0000-0000-000000000003')
  })

  it('shows the kanji the pre-test replaced, and the ones kept', async () => {
    const t = await screen.findByRole('table', { name: 'Kanji replaced by the pre-test' })
    expect(within(t).getByRole('row', { name: /山/ })).toHaveTextContent('A山川')
    expect(within(t).getByRole('row', { name: /水/ })).toHaveTextContent('No valid substitute: kept and flagged')
    expect(screen.getByText('Learner profile across sessions: available in a later version.')).toBeInTheDocument()
  })

  it('draws completed sessions only, numbered as in the table, and switches the measure', async () => {
    const user = userEvent.setup()
    const trend = await screen.findByRole('img', { name: /^Accuracy per completed session/ })
    expect(trend).toHaveAccessibleName('Accuracy per completed session: 1 80.0 %, 3 90.0 %')
    expect(screen.getByText('Completed sessions only; aborted ones are listed in the table below.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Response time' }))
    expect(screen.getByRole('button', { name: 'Response time' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('img', { name: /^Mean response time per completed session/ })).toHaveAccessibleName(
      'Mean response time per completed session: 1 1834 ms, 3 1834 ms')
  })
})

describe('participant view, pre-test not complete', () => {
  it('offers the pre-test and says the default set is in use', async () => {
    show({ ...DONE, pretest_status: 'IN_PROGRESS', pretest_answered: 6, pretest_completed_at: null, flagged_count: null,
      sessions: [], substitutions: [], session_count: 0, conditions: [] })
    expect(await screen.findByText(
      'The pre-test is in progress (6 kanji answered). Sessions use the default set until it is completed. No sessions recorded yet.',
    )).toBeInTheDocument()
    const f = await facts()
    expect(f).toHaveTextContent("Not complete. Unity can't start a session yet.")
    expect(within(f).getByRole('link', { name: 'Open the pre-test' })).toHaveAttribute('href', '/pretest')
    expect(screen.getByText('No completed sessions yet.')).toBeInTheDocument()
  })

  it('names a pre-test not started', async () => {
    show({ ...DONE, pretest_status: 'NOT_STARTED', pretest_answered: 0, pretest_completed_at: null, flagged_count: null,
      substitutions: [] })
    expect(await screen.findByText(/^The pre-test hasn't been started\. Sessions use the default kanji set until it is completed\.$/))
      .toBeInTheDocument()
  })
})

describe('participant view, every session before the pre-test', () => {
  it('names no later sessions', async () => {
    show({ ...DONE, sessions: DONE.sessions.map((s) => ({ ...s, before_pretest: true })) })
    expect(await screen.findByText(/^All 3 sessions were recorded before the pre-test and used the default set\.$/))
      .toBeInTheDocument()
  })

  it('with a single session', async () => {
    show({ ...DONE, sessions: [{ ...DONE.sessions[0]!, before_pretest: true }] })
    expect(await screen.findByText(/^The only session was recorded before the pre-test and used the default set\.$/))
      .toBeInTheDocument()
  })
})

describe('participant view, pre-test completed and no sessions', () => {
  it('says how many kanji were replaced', async () => {
    show({ ...DONE, sessions: [] })
    expect(await screen.findByText(/^The pre-test is complete, with 1 kanji replaced\. No sessions recorded yet\.$/))
      .toBeInTheDocument()
  })

  it('or that none needed replacing', async () => {
    show({ ...DONE, sessions: [], substitutions: [] })
    expect(await screen.findByText(
      /^The pre-test is complete and no kanji needed replacing\. No sessions recorded yet\.$/)).toBeInTheDocument()
  })
})

describe('participant view, every session after the pre-test', () => {
  it('says how many kanji were replaced, or that none were', async () => {
    const after = DONE.sessions.map((s) => ({ ...s, before_pretest: false }))
    show({ ...DONE, sessions: after })
    expect(await screen.findByText('Every session used the kanji set confirmed by the pre-test, with 1 kanji replaced.'))
      .toBeInTheDocument()
  })

  it('or that none needed replacing', async () => {
    const after = DONE.sessions.map((s) => ({ ...s, before_pretest: false }))
    show({ ...DONE, sessions: after, substitutions: [] })
    expect(await screen.findByText(
      'Every session used the kanji set confirmed by the pre-test. No kanji needed replacing.')).toBeInTheDocument()
  })
})

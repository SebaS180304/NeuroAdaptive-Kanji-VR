import { cleanup, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Schemas } from '@/api/client'
import { json, mockApi } from '@/test/api'
import { renderApp } from '@/test/render'

vi.mock('./TrendChart', async (actual) => ({ ...(await actual()), TrendChart: () => null }))   // no canvas in jsdom

type Detail = Schemas['ResearchParticipantDetail']
type Row = Detail['sessions'][number]
type Profile = Schemas['LearnerProfile']
type Group = Schemas['ProfileAdaptationGroup']

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

const A = 'aaaaaaaa-0000-0000-0000-000000000001'
const C = 'cccccccc-0000-0000-0000-000000000003'
const cal = (session_id: string, correct: number) => ({
  session_id, rt_ref: { T1_MEANING_TO_KANJI: 2300, T2_KANJI_TO_MEANING: 1500, T3_KANJI_TO_READING: 2100 },
  rt_ref_global: 2049, rt_spread: 0.2, acc_ref: correct / 8, idle_eff_ref: null, away_ref_ms: 412, env_dwell_ref_ms: 180,
  orienting_rate_ref: null, n_trials: 8, n_valid_rt: 8, reliability: 1, correct, n: 8,
  fallback_types: session_id === C ? ['T2_KANJI_TO_MEANING'] : [],
})
const trend = (session_id: string, condition: Row['condition'], s7_correct: number, created_at: string) => ({
  session_id, condition, kanji_set: 'A', created_at, s7_trials: 20, s7_correct, s7_mean_rt_ms: 2400,
  no_change: condition === 'STATIC' ? null : 18, decisions_recorded: condition === 'STATIC' ? null : true,
})
const RAISED: Group = {
  key: 'OVERLOADED.NONE.LAL.UP', learner_state: 'OVERLOADED', cause: null, dimension: 'LAL', direction: 'UP', count: 1,
  outcomes: { POSITIVE: 1 }, outcome_reasons: { POSITIVE: { RESOLVED: 1 } }, decisions: { [C]: ['S7-006'] },
  last_decided_at: '2026-10-16T05:10:00+00:00',
}
const PROFILE: Profile = {
  participant_id: 'p1', profile_version: 'v1', computed_at: '2026-10-16T06:00:00Z', session_ids: [A, C],
  profile: {
    calibrations: [cal(A, 6), cal(C, 7)],
    adaptations: [RAISED],
    trend: [trend(A, 'STATIC', 15, '2026-10-10T05:00:00Z'), trend(C, 'BEHAVIOR_ADAPTIVE', 17, '2026-10-16T05:00:00Z')],
  },
}
const EMPTY: Profile = { participant_id: 'p1', profile_version: null, computed_at: null, session_ids: [], profile: null }

function show(detail: Detail, profile: Profile = PROFILE) {
  mockApi({
    [`GET /api/research/participants/${detail.id}`]: () => json(detail),
    [`GET /api/research/participants/${detail.id}/profile`]: () => json(profile),
  })
  renderApp(`/participants/${detail.id}`)
}

async function learnerProfile() {
  const region = await screen.findByRole('region', { name: 'Learner Profile' })
  await waitFor(() => expect(within(region).queryByText('Loading the profile…')).not.toBeInTheDocument())
  return region
}

const facts = () => screen.findByRole('region', { name: 'Pre-test and kanji sets' })

describe('participant view (V1.8)', () => {
  beforeEach(() => show(DONE))

  it('says which sessions came before the pre-test, and counts them in the facts', async () => {
    expect(await screen.findByText(
      '1 of 3 sessions was recorded before the pre-test and used the default set. Later sessions used the confirmed set, with 1 kanji replaced.',
    )).toBeInTheDocument()
    const f = await facts()
    expect(f).toHaveTextContent('Completed 2026-10-12')
    // The sessions fact and the conditions sit in the header, right of the title (F-PROFILE).
    const header = screen.getByLabelText('Sessions and conditions')
    expect(header).toHaveTextContent('2 completed, 1 aborted')
    expect(header).toHaveTextContent('Static')
    expect(header).toHaveTextContent('Behavior-adaptive')
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
    expect(screen.queryByText(/available in a later version/)).not.toBeInTheDocument()   // the profile is here now
  })

  it('draws the profile trend: completed sessions numbered as in the table, correct of 20', async () => {
    const user = userEvent.setup()
    const chart = await screen.findByRole('img', { name: /^Correct in S7 per completed session/ })
    expect(chart).toHaveAccessibleName('Correct in S7 per completed session: 1 15 of 20, 3 17 of 20')
    await user.click(screen.getByRole('button', { name: 'Response time' }))
    expect(screen.getByRole('button', { name: 'Response time' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('img', { name: /^Mean response time in S7/ })).toHaveAccessibleName(
      'Mean response time in S7 per completed session: 1 2400 ms, 3 2400 ms')
    expect(screen.getAllByRole('img', { name: /per completed session/ })).toHaveLength(1)   // one chart on the page
  })
})

describe('learner profile (F-PROFILE)', () => {
  it('comes first, says what it covers and never mentions aborted sessions', async () => {
    show(DONE)
    const p = await learnerProfile()
    expect(within(p).getByRole('heading', { name: 'Learner Profile' })).toBeInTheDocument()
    expect(p).toHaveTextContent('A summary of 2 completed sessions. It describes what happened in windows of trials')
    expect(p).toHaveTextContent('Updated 2026-10-16, profile v1')
    expect(p.textContent).not.toMatch(/abort/i)
  })

  it('answers the three questions with the latest practice, the groups and the trend', async () => {
    show(DONE)
    const p = await learnerProfile()
    expect(p).toHaveTextContent('In practice (S6) of the latest session, P01 answered 7 of 8 correctly, taking about 2.0 s per answer')
    expect(within(p).getByRole('row', { name: /Correct in practice/ })).toHaveTextContent('7 of 86–7 of 8')
    expect(within(p).getByLabelText('Too few T2 trials in practice; this uses the overall median.')).toBeInTheDocument()
    expect(p).toHaveTextContent('From practice (S6) of 2 completed sessions: 1 STATIC, 1 adaptive.')
    expect(p).toHaveTextContent('When answers got slower and less accurate than in practice (estimated overload), assistance (LAL) was raised 1 time.')
    expect(within(p).getByText('Too few to tell')).toBeInTheDocument()
    expect(within(p).getByTitle('POSITIVE, RESOLVED')).toHaveTextContent('Recovered after: 1')
    expect(within(p).getByRole('link', { name: 'See 1 decision' })).toHaveAttribute('href', `/sessions/${C}?tab=adaptations`)
    expect(p).toHaveTextContent('From 1 completed adaptive session. STATIC sessions never adapt')
    expect(p).toHaveTextContent('Two sessions so far: 15 then 17 correct in S7, 2.4 then 2.4 s per answer. Too few for a trend.')
  })

  it('lists the sessions of a group that spans several, newest first', async () => {
    const user = userEvent.setup()
    const both: Group = { ...RAISED, count: 3, outcomes: { POSITIVE: 3 }, outcome_reasons: { POSITIVE: { RESOLVED: 3 } },
      decisions: { [A]: ['S7-004'], [C]: ['S7-006', 'S7-012'] } }
    show(DONE, { ...PROFILE, profile: { ...PROFILE.profile!, adaptations: [both] } })
    const p = await learnerProfile()
    expect(p).toHaveTextContent('assistance (LAL) was raised 3 times; recovered after 3 of 3.')
    const button = within(p).getByRole('button', { name: 'See 3 decisions in 2 sessions' })
    expect(button).toHaveAttribute('aria-expanded', 'false')
    await user.click(button)
    expect(button).toHaveAttribute('aria-expanded', 'true')
    const lines = within(within(p).getByRole('list', { name: 'Decisions by session' })).getAllByRole('listitem')
    expect(lines.map((l) => l.textContent)).toEqual(['Session 3 (2026-10-16)2 decisions', 'Session 1 (2026-10-10)1 decision'])
    expect(within(lines[0]!).getByRole('link', { name: '2 decisions' })).toHaveAttribute('href', `/sessions/${C}?tab=adaptations`)
  })

  it('shows at most 3 groups, the rest behind a button', async () => {
    const user = userEvent.setup()
    const groups = ['A', 'B', 'C', 'D'].map((k) => ({ ...RAISED, key: k }))
    show(DONE, { ...PROFILE, profile: { ...PROFILE.profile!, adaptations: groups } })
    const p = await learnerProfile()
    expect(within(p).getAllByRole('link', { name: 'See 1 decision' })).toHaveLength(3)
    await user.click(within(p).getByRole('button', { name: 'Show 1 more group' }))
    expect(within(p).getAllByRole('link', { name: 'See 1 decision' })).toHaveLength(4)
  })

  it('with STATIC sessions only, says adaptations are not expected', async () => {
    show(DONE, { ...PROFILE, profile: { ...PROFILE.profile!, adaptations: [],
      trend: PROFILE.profile!.trend.map((t) => ({ ...t, condition: 'STATIC' as const, no_change: null, decisions_recorded: null })) } })
    expect(await learnerProfile()).toHaveTextContent(
      'No adaptations: both sessions so far were STATIC, and STATIC never adapts. Usual performance and the results across sessions come from them.')
  })

  it('with adaptive sessions and no change, says how often the system checked', async () => {
    show(DONE, { ...PROFILE, profile: { ...PROFILE.profile!, adaptations: [] } })
    const p = await learnerProfile()
    expect(p).toHaveTextContent('No adaptations in 1 adaptive session. The system checked 18 times and kept the levels each time.')
    expect(within(p).getByRole('link', { name: 'See 18 decisions' })).toHaveAttribute('href', `/sessions/${C}?tab=adaptations`)
  })

  it('marks older sessions with no adaptation record, never as 0', async () => {
    const old = { ...PROFILE.profile!.trend[1]!, decisions_recorded: false, no_change: 0 }
    show(DONE, { ...PROFILE, profile: { ...PROFILE.profile!, adaptations: [], trend: [PROFILE.profile!.trend[0]!, old] } })
    const p = await learnerProfile()
    expect(within(p).getByTitle(/^Adaptations weren't recorded before 13 Oct/)).toHaveTextContent('1 older session has no adaptation record.')
    expect(p.textContent).not.toMatch(/checked 0 times/)
  })

  it('with no completed session: one panel, the same with no row or an empty one', async () => {
    for (const profile of [EMPTY, { ...PROFILE, session_ids: [], profile: { calibrations: [], adaptations: [], trend: [] } }]) {
      show(DONE, profile)
      const p = await learnerProfile()
      expect(within(p).getByRole('heading', { name: 'No profile yet.' })).toBeInTheDocument()
      expect(p).toHaveTextContent('A summary of the completed sessions. It describes what happened')
      expect(p).toHaveTextContent('No profile computed')
      expect(p).toHaveTextContent('P01 has no completed session yet. The profile appears after the first one. Pre-test done on 2026-10-12.')
      expect(p.textContent).not.toMatch(/abort|failed|incomplete|dropped|didn't finish/i)
      cleanup()
    }
  })
})

describe('participant view, pre-test not complete', () => {
  it('offers the pre-test and says the default set is in use', async () => {
    show({ ...DONE, pretest_status: 'IN_PROGRESS', pretest_answered: 6, pretest_completed_at: null, flagged_count: null,
      sessions: [], substitutions: [], session_count: 0, conditions: [] }, EMPTY)
    expect(await screen.findByText(
      'The pre-test is in progress (6 kanji answered). No sessions recorded yet.',
    )).toBeInTheDocument()
    const f = await facts()
    expect(f).toHaveTextContent("Not complete. Unity can't start a session yet.")
    expect(within(f).getByRole('link', { name: 'Open the pre-test' })).toHaveAttribute('href', '/pretest')
    expect(await learnerProfile()).toHaveTextContent('P01 has no completed session yet. The profile appears after the first one.')
    expect((await learnerProfile()).textContent).not.toMatch(/Pre-test done/)
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

describe('participant view, some sessions before the pre-test and none replaced', () => {
  it('ends the sentence without a count', async () => {
    show({ ...DONE, substitutions: [] })
    expect(await screen.findByText(
      '1 of 3 sessions was recorded before the pre-test and used the default set. Later sessions used the confirmed set.',
    )).toBeInTheDocument()
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

import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'
import type { Schemas } from '@/api/client'
import { json, mockApi } from '@/test/api'
import { renderApp } from '@/test/render'

type Row = Schemas['ResearchSession']

const base: Row = {
  session_id: '', participant_id: 'p1', external_code: 'P01', condition: 'STATIC', status: 'COMPLETED',
  visit_number: 1, created_at: '2026-10-14T05:00:00Z', projection_status: 'PROJECTED',
  trial_count: 60, decision_count: null, accuracy: 0.8163, open_error_count: 0,
  last_state: 'S9_SESSION_SUMMARY',
}
const ROWS: Row[] = [
  { ...base, session_id: 'aaaaaaaa-0000-0000-0000-000000000001', condition: 'BEHAVIOR_ADAPTIVE', decision_count: 12 },
  { ...base, session_id: 'bbbbbbbb-0000-0000-0000-000000000002', status: 'ABORTED', open_error_count: 3,
    last_state: 'S7_EXPERIMENTAL_RETRIEVAL', created_at: '2026-10-10T05:00:00Z' },
  { ...base, session_id: 'cccccccc-0000-0000-0000-000000000003', participant_id: 'p2', external_code: 'OBS_01',
    status: 'CREATED', projection_status: 'NOT_PROJECTED', trial_count: null, accuracy: null, visit_number: 2, last_state: null,
    created_at: '2026-10-05T05:00:00Z' },
  { ...base, session_id: 'dddddddd-0000-0000-0000-000000000004', participant_id: 'p2', external_code: 'OBS_01',
    condition: 'BEHAVIOR_ADAPTIVE', status: 'CREATED', projection_status: 'NO_DATA', trial_count: null,
    accuracy: null, last_state: null, created_at: '2026-10-01T05:00:00Z' },
]

beforeEach(() => {
  mockApi({ 'GET /api/research/sessions': () => json(ROWS) })
})

async function table() {
  renderApp('/sessions')
  return screen.findByRole('table')
}

const ids = (t: HTMLElement) =>
  within(t).queryAllByRole('rowheader').map((h) => h.textContent)

describe('session list (V1.1)', () => {
  it('shows one row per session, not-projected ones included', async () => {
    const t = await table()
    expect(ids(t)).toEqual(['aaaaaaaa', 'bbbbbbbb', 'cccccccc', 'dddddddd'])
    const a = within(t).getByRole('row', { name: /aaaaaaaa/ })
    expect(a).toHaveTextContent('Behavior-adaptive')
    expect(a).toHaveTextContent('Completed')
    expect(a).toHaveTextContent('81.6 %')
    expect(a).toHaveTextContent('12')
    expect(a).toHaveTextContent('No open errors')
    expect(within(t).getByRole('row', { name: /bbbbbbbb/ })).toHaveTextContent('Aborted in S7')
    expect(within(t).getByRole('row', { name: /bbbbbbbb/ })).toHaveTextContent('3 open errors')
    expect(within(t).getByRole('row', { name: /cccccccc/ })).toHaveTextContent('Not projected')
    expect(within(t).getByRole('row', { name: /cccccccc/ })).toHaveTextContent('Not started')
    expect(within(t).getByRole('row', { name: /dddddddd/ })).toHaveTextContent('No data')
    expect(screen.getByText(/^4 sessions from 2 participants\./)).toBeInTheDocument()
  })

  it('shows not-recorded values as a dash with the reason, never zero', async () => {
    const t = await table()
    const b = within(t).getByRole('row', { name: /bbbbbbbb/ })
    expect(within(b).getByTitle('No adaptations in a static session')).toHaveTextContent('—')
    const c = within(t).getByRole('row', { name: /cccccccc/ })
    expect(within(c).getAllByTitle('Not projected')).toHaveLength(2)        // trials, accuracy
    const d = within(t).getByRole('row', { name: /dddddddd/ })
    expect(within(d).getAllByTitle('No data recorded')).toHaveLength(3)    // trials, adaptations, accuracy
  })

  it('links the session and the participant', async () => {
    const t = await table()
    expect(within(t).getByRole('link', { name: 'aaaaaaaa' })).toHaveAttribute(
      'href', '/sessions/aaaaaaaa-0000-0000-0000-000000000001')
    expect(within(t).getAllByRole('link', { name: 'OBS_01' })[0]).toHaveAttribute('href', '/participants/p2')
  })

  it('counts sessions by condition, and not projected apart', async () => {
    await table()
    const bar = screen.getByRole('figure', { name: 'Sessions by condition' })
    expect(bar).toHaveTextContent('Static 1')
    expect(bar).toHaveTextContent('Behavior-adaptive 1')
    expect(bar).toHaveTextContent('Not projected 2')
  })

  it('combines the filters, and clears them', async () => {
    const user = userEvent.setup()
    const t = await table()
    await user.type(screen.getByLabelText('Participant'), 'obs')
    expect(ids(t)).toEqual(['cccccccc', 'dddddddd'])
    await user.selectOptions(screen.getByLabelText('Condition'), 'Static')
    expect(ids(t)).toEqual(['cccccccc'])
    await user.selectOptions(screen.getByLabelText('Status'), 'Completed')
    expect(ids(t)).toEqual([])
    expect(screen.getByText('No session matches these filters.')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(ids(t)).toHaveLength(4)
    await user.selectOptions(screen.getByLabelText('Status'), 'Not projected')
    expect(ids(t)).toEqual(['cccccccc', 'dddddddd'])
    await user.selectOptions(screen.getByLabelText('Status'), 'Not started')
    expect(ids(t)).toEqual(['cccccccc', 'dddddddd'])
    await user.click(screen.getByRole('button', { name: 'Clear filters' }))

    await user.type(screen.getByLabelText('Recorded from'), '2026-10-05')
    await user.type(screen.getByLabelText('Recorded to'), '2026-10-10')
    expect(ids(t)).toEqual(['bbbbbbbb', 'cccccccc'])
  })
})

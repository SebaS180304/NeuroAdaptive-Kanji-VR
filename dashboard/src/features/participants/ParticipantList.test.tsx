import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Schemas } from '@/api/client'
import { renderApp } from '@/test/render'

type Row = Schemas['ResearchParticipant']

const base: Row = {
  id: '', external_code: '', created_at: '2026-10-10T03:00:00Z', pretest_status: 'NOT_STARTED',
  pretest_answered: 0, pretest_completed_at: null, session_count: 0, conditions: [],
  last_session_at: null, last_session_accuracy: null, previous_japanese_experience: null, flagged_count: null,
}
const ROWS: Row[] = [
  { ...base, id: 'p1', external_code: 'P01', pretest_status: 'COMPLETED', pretest_answered: 18,
    pretest_completed_at: '2026-10-12T05:00:00Z', session_count: 2, conditions: ['STATIC', 'BEHAVIOR_ADAPTIVE'],
    last_session_at: '2026-10-14T05:00:00Z', last_session_accuracy: 0.8163, flagged_count: 1 },
  { ...base, id: 'p2', external_code: 'P02', pretest_status: 'IN_PROGRESS', pretest_answered: 3,
    previous_japanese_experience: true },
  { ...base, id: 'p3', external_code: 'OBS_01', session_count: 1, conditions: ['STATIC'],
    last_session_at: '2026-10-05T07:19:29Z', last_session_accuracy: null, flagged_count: null },
]

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    expect(url).toBe('/api/research/participants')
    return new Response(JSON.stringify(ROWS), { status: 200 })
  }))
})
afterEach(() => vi.unstubAllGlobals())

async function table() {
  renderApp('/participants')
  return screen.findByRole('table')
}

function codes(t: HTMLElement) {
  return within(t).queryAllByRole('link').map((a) => a.textContent)
}

describe('participant list (V1.11)', () => {
  it('shows one row per participant with the figures from the API', async () => {
    const t = await table()
    expect(codes(t)).toEqual(['P01', 'P02', 'OBS_01'])
    const p1 = within(t).getByRole('row', { name: /P01/ })
    expect(p1).toHaveTextContent('Completed 2026-10-12')
    expect(p1).toHaveTextContent('Static')
    expect(p1).toHaveTextContent('Behavior-adaptive')
    expect(p1).toHaveTextContent('81.6 %')
    expect(p1).toHaveTextContent('Kanji kept with no substitute')
    const p2 = within(t).getByRole('row', { name: /P02/ })
    expect(p2).toHaveTextContent('In progress, 3 answered')
    expect(p2).toHaveTextContent('Previous Japanese study reported')
    expect(screen.getByText(/^3 participants registered\./)).toBeInTheDocument()
  })

  it('shows a missing value as a dash with its reason, never as zero', async () => {
    const t = await table()
    const obs = within(t).getByRole('row', { name: /OBS_01/ })
    const dash = within(obs).getByTitle('No answered trials in the last session')
    expect(dash).toHaveTextContent('—')
    expect(within(within(t).getByRole('row', { name: /P02/ })).getAllByTitle('No sessions yet')).toHaveLength(2)
  })

  it('links each code to its participant page', async () => {
    const t = await table()
    expect(within(t).getByRole('link', { name: 'P02' })).toHaveAttribute('href', '/participants/p2')
  })

  it('filters by code, pre-test status, condition and notes', async () => {
    const user = userEvent.setup()
    const t = await table()
    await user.type(screen.getByLabelText('Participant code'), 'p0')
    expect(codes(t)).toEqual(['P01', 'P02'])
    await user.clear(screen.getByLabelText('Participant code'))

    await user.selectOptions(screen.getByLabelText('Pre-test'), 'In progress')
    expect(codes(t)).toEqual(['P02'])
    await user.selectOptions(screen.getByLabelText('Pre-test'), 'Any status')

    await user.selectOptions(screen.getByLabelText('Has sessions in'), 'Static')
    expect(codes(t)).toEqual(['P01', 'OBS_01'])
    await user.selectOptions(screen.getByLabelText('Has sessions in'), 'Any condition')

    await user.click(screen.getByLabelText('Only with notes for the researcher'))
    expect(codes(t)).toEqual(['P01', 'P02'])
  })

  it('summarises the pre-test status of everyone in the status bar', async () => {
    await table()
    const bar = screen.getByRole('figure', { name: 'Pre-test status of all participants' })
    expect(bar).toHaveTextContent('Pre-test completed 1')
    expect(bar).toHaveTextContent('In progress 1')
    expect(bar).toHaveTextContent('Not started 1')
  })
})

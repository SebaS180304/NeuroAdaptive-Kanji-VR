import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Schemas } from '@/api/client'
import { json, mockApi, offline } from '@/test/api'
import { renderApp } from '@/test/render'

type Row = Schemas['ResearchParticipant']
const base: Row = {
  id: '', external_code: '', created_at: '2026-10-10T03:00:00Z', pretest_status: 'NOT_STARTED',
  pretest_answered: 0, pretest_completed_at: null, session_count: 0, conditions: [],
  last_session_at: null, last_session_accuracy: null, previous_japanese_experience: null, flagged_count: null,
}
const ROWS: Row[] = [
  { ...base, id: 'p1', external_code: 'P01' },
  { ...base, id: 'p2', external_code: 'P02', pretest_status: 'IN_PROGRESS', pretest_answered: 4 },
  { ...base, id: 'p3', external_code: 'P03', pretest_status: 'COMPLETED', pretest_answered: 18,
    pretest_completed_at: '2026-10-12T05:00:00Z', flagged_count: 0 },
]

afterEach(() => vi.unstubAllGlobals())

describe('pre-test, pick a participant (V1.10)', () => {
  it('gives each participant the action for its status', async () => {
    mockApi({ 'GET /api/research/participants': () => json(ROWS) })
    renderApp('/pretest')
    const table = await screen.findByRole('table')
    const action = (code: string) => within(within(table).getByRole('row', { name: new RegExp(code) })).getByRole('link')
    expect(action('P01')).toHaveTextContent('Start')
    expect(action('P01')).toHaveAttribute('href', '/pretest/p1')
    expect(action('P02')).toHaveTextContent('Resume')
    expect(within(table).getByRole('row', { name: /P02/ })).toHaveTextContent('In progress, 4 answered')
    expect(action('P03')).toHaveTextContent('View result')
    expect(screen.getByRole('link', { name: 'Register a participant' })).toHaveAttribute('href', '/pretest/register')
  })

  it('says when no participant has the searched code, and offers to register', async () => {
    mockApi({ 'GET /api/research/participants': () => json(ROWS) })
    renderApp('/pretest')
    await screen.findByRole('table')
    await userEvent.type(screen.getByLabelText('Participant code'), 'P99')
    const notice = screen.getByRole('status', { name: 'No participant with code P99' })
    expect(within(notice).getByRole('link', { name: 'Register' })).toHaveAttribute('href', '/pretest/register')
  })

  it('says when the backend cannot be reached, and tries again', async () => {
    let up = false
    mockApi({ 'GET /api/research/participants': () => (up ? json(ROWS) : offline()) })
    renderApp('/pretest')
    const alert = await screen.findByRole('alert', { name: "Can't reach the backend" })
    up = true
    await userEvent.click(within(alert).getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
  })
})

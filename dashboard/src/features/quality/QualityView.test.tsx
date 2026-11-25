import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import type { Schemas } from '@/api/client'
import { json, mockApi } from '@/test/api'
import { renderApp } from '@/test/render'

type Quality = Schemas['DataQuality']
type Err = Quality['open_errors'][number]

const S1 = 'aaaaaaaa-0000-0000-0000-000000000001'
const err = (i: number, code: string): Err => ({
  id: i, event_id: 1000 + i, session_id: S1, event_type: 'STATE_ENTERED', error_code: code,
  detail: `detail ${i}`, session_elapsed_ms: 61_234,
})
const CLEAN: Quality = {
  projected_sessions: 45, clean_sessions: 45, open_by_code: {}, resolved_errors: 9810,
  checks: ['verify_projection', 'verify_adaptation', 'verify_trials', 'verify_assembly', 'verify_reproducibility']
    .map((name) => ({ name, rows: [] })),
  open_errors: [], not_projected: [],
}
const ISSUES: Quality = {
  ...CLEAN,
  clean_sessions: 38,
  open_by_code: { UNKNOWN_ENUM: 60, NEW_CODE: 1 },
  checks: CLEAN.checks.map((c) => c.name === 'verify_trials'
    ? { ...c, rows: Array.from({ length: 12 }, (_, i) => ({ session_id: S1, check: 'trials/consistency', detail: `row ${i + 1}` })) }
    : c),
  open_errors: [...Array.from({ length: 60 }, (_, i) => err(i + 1, 'UNKNOWN_ENUM')), err(61, 'NEW_CODE')],
  not_projected: [
    { session_id: 'bbbbbbbb-0000-0000-0000-000000000002', participant_id: 'p1', external_code: 'OBS_01',
      created_at: '2026-09-15T05:00:00Z', projection_status: 'NO_DATA' },
  ],
}

function show(q: Quality) {
  mockApi({ 'GET /api/research/quality': () => json(q) })
  renderApp('/quality')
}

describe('data quality (V1.7)', () => {
  it('with nothing open: every check passes, the bars stay at 0 and the empty states show', async () => {
    show(CLEAN)
    expect(await screen.findByText('Every projected session has no open errors and passes every check.')).toBeInTheDocument()
    const bars = screen.getByRole('region', { name: 'Open errors by code' })
    for (const code of ['MISSING_FIELD', 'UNKNOWN_ENUM', 'ORPHAN_EVENT', 'DUPLICATE', 'FK_VIOLATION'])
      expect(bars).toHaveTextContent(`${code}0`)
    expect(bars).toHaveTextContent('9,810 resolved by re-projection so far')
    expect(screen.getByText('No errors to resolve. 9,810 resolved by re-projection so far.')).toBeInTheDocument()
    expect(screen.getByText('Every recorded session is projected.')).toBeInTheDocument()
    const checks = screen.getByRole('table', { name: 'Verification checks' })
    expect(within(checks).getAllByText('Pass')).toHaveLength(5)
  })

  it('counts open errors by code, the five first and any other after', async () => {
    show(ISSUES)
    expect(await screen.findByText(
      '38 of 45 projected sessions have no open errors and pass every check. 1 session is not projected; it is listed at the end.',
    )).toBeInTheDocument()
    const bars = screen.getByRole('region', { name: 'Open errors by code' })
    expect(bars.textContent).toMatch(/MISSING_FIELD0UNKNOWN_ENUM60ORPHAN_EVENT0DUPLICATE0FK_VIOLATION0NEW_CODE1/)
  })

  it('expands a check that needs review, 10 rows at a time', async () => {
    const user = userEvent.setup()
    show(ISSUES)
    const checks = await screen.findByRole('table', { name: 'Verification checks' })
    const row = within(checks).getByRole('row', { name: /verify_trials/ })
    expect(row).toHaveTextContent('12Needs review')
    await user.click(within(row).getByRole('button', { name: 'Show affected sessions' }))
    expect(within(checks).getAllByText(/^trials\/consistency: row \d+$/)).toHaveLength(10)
    expect(within(checks).getAllByRole('link', { name: 'aaaaaaaa' })[0]).toHaveAttribute('href', `/sessions/${S1}`)
    await user.click(within(checks).getByRole('button', { name: 'Show all 12' }))
    expect(within(checks).getAllByText(/^trials\/consistency: row \d+$/)).toHaveLength(12)
  })

  it('pages the open errors by 50, after the code filter', async () => {
    const user = userEvent.setup()
    show(ISSUES)
    const table = await screen.findByRole('table', { name: 'Errors to resolve' })
    expect(within(table).getAllByRole('row')).toHaveLength(51)
    expect(screen.getByText('Showing 1–50 of 61')).toBeInTheDocument()
    expect(within(table).getAllByRole('row')[1]).toHaveTextContent('01:01.234')
    await user.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByText('Showing 51–61 of 61')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
    await user.selectOptions(screen.getByLabelText('Code'), 'NEW_CODE')
    expect(screen.getByText('Showing 1–1 of 1')).toBeInTheDocument()
  })

  it('lists the sessions with no projection', async () => {
    show(ISSUES)
    const t = await screen.findByRole('table', { name: 'Sessions not projected' })
    const row = within(t).getAllByRole('row')[1]!
    expect(row).toHaveTextContent('No events recorded')
    expect(within(row).getByRole('link', { name: 'OBS_01' })).toHaveAttribute('href', '/participants/p1')
    expect(within(row).getByTitle('No reason recorded')).toHaveTextContent('—')
  })
})

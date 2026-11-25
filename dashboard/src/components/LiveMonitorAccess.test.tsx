import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { json, mockApi } from '@/test/api'
import { renderApp } from '@/test/render'

// V1.13 access (design-system.md, D-F6-272; Contenido_UI_Monitor_Accesos.md §1, §2) and V1.13 sessionEnded (§3.1).

const SID = 'b7d2e019-0000-0000-0000-000000000000'
const never = () => new Promise<Response>(() => {})

afterEach(() => vi.unstubAllGlobals())

describe('rail entry "Live monitor" (§1)', () => {
  it('is the second item, says Live and names the running session', async () => {
    mockApi({
      'GET /api/research/live/current': () => json({ session_id: SID, external_code: 'P03' }),
      'GET /api/research/sessions?': never,
    })
    renderApp('/quality')
    const item = await screen.findByRole('link', { name: 'Live monitor, session in progress' })
    const rail = screen.getByRole('navigation', { name: 'Main' })
    expect(within(rail).getAllByRole('link')[1]).toBe(item)
    expect(item).toHaveAttribute('href', '/monitor')
    expect(item).not.toHaveAttribute('target')
    expect(item).toHaveAttribute('title', 'Opens the live session monitor for P03, session b7d2e019. Read-only.')
    expect(within(item).getByText('Live')).toBeInTheDocument()
  })

  it('without a session (or a backend that does not answer) shows the ring and stays clickable', async () => {
    mockApi({ 'GET /api/research/live/current': () => json({ detail: 'no session in progress' }, 404) })
    renderApp('/pretest')
    const item = await screen.findByRole('link', { name: 'Live monitor, no session in progress' })
    expect(item).toHaveAttribute('title', 'No session in progress. The monitor will show the next session when it starts.')
    expect(within(item).queryByText('Live')).toBeNull()
  })
})

describe('the monitor', () => {
  const snapshot = (status: string) => ({
    generated_at: '2026-11-20T10:21:47+09:00',
    session: { session_id: SID, external_code: 'P03', condition: 'MULTIMODAL_ADAPTIVE', set: 'B', visit: 2, status,
      stage: 'S9_SESSION_SUMMARY', stage_entered_ms: 1, elapsed_ms: 2_000, completed_at: '2026-11-20T01:21:47Z' },
    sync: null, indices: { reference: null, last: null, windows: { counted: 0, with_eeg: 0 }, trace: [] },
    decisions: [], events: [], system: null, signal_quality: null,
  })

  it('on /monitor/<id>, a session that ended says so and links to its view; the panels go stale (§3.1)', async () => {
    mockApi({ [`GET /api/research/sessions/${SID}/live`]: () => json(snapshot('COMPLETED')) })
    renderApp(`/monitor/${SID}`)
    expect(await screen.findByText('This session has ended')).toBeInTheDocument()
    expect(screen.getByText(/Session b7d2e019 closed at \d\d:\d\d:\d\d\. Its data is in the session view\./)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open session view' })).toHaveAttribute('href', `/sessions/${SID}`)
    expect(screen.getByRole('region', { name: 'Sync' }).className).toMatch(/border-dashed/)
    expect(screen.queryByText('Read only. Nothing on this screen changes the session.')).toBeNull()
  })

  it('a running session shows no banner and fresh panels', async () => {
    mockApi({ [`GET /api/research/sessions/${SID}/live`]: () => json(snapshot('IN_PROGRESS')) })
    renderApp(`/monitor/${SID}`)
    expect(await screen.findByText('Read only. Nothing on this screen changes the session.')).toBeInTheDocument()
    expect(screen.queryByText('This session has ended')).toBeNull()
    expect(screen.getByRole('region', { name: 'Sync' }).className).not.toMatch(/border-dashed/)
  })

  it('/monitor without a session waits, with the §3 line', async () => {
    mockApi({ 'GET /api/research/live/current': () => json({ detail: 'no session in progress' }, 404) })
    renderApp('/monitor')
    expect(await screen.findByText('Waiting for a new session')).toBeInTheDocument()
    expect(screen.getByText('The monitor will show the next session when it starts. Nothing to do here.')).toBeInTheDocument()
  })
})

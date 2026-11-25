import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mockApi } from './test/api'
import { renderApp } from './test/render'

describe('app shell', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows the rail with the five entries, in order (Live monitor second, D-F6-268)', () => {
    renderApp('/sessions')
    const rail = screen.getByRole('navigation', { name: 'Main' })
    expect(within(rail).getAllByRole('link').map((a) => a.textContent)).toEqual([
      'Sessions', 'Live monitor', 'Participants', 'Pre-test', 'Data quality',
    ])
    expect(within(rail).getByText('Runs locally on the lab machine')).toBeInTheDocument()
  })

  it('shows the logo above the name in the rail, decorative, one per theme (Brand, D-F6-269 (1))', () => {
    renderApp('/sessions')
    const rail = screen.getByRole('navigation', { name: 'Main' })
    const icons = Array.from(rail.querySelectorAll('img'))
    expect(icons.map((i) => i.getAttribute('src'))).toEqual(['/brand/andon_icon_light_32.png', '/brand/andon_icon_dark_32.png'])
    expect(icons.every((i) => i.getAttribute('alt') === '' && i.width === 32)).toBe(true)
    expect(within(rail).getByText('NeuroAdaptive VR')).toBeInTheDocument()
  })

  it('marks the rail item of the current section', () => {
    mockApi({ 'GET /api/research/quality': () => new Promise<Response>(() => {}) })   // stays loading
    renderApp('/quality')
    expect(screen.getByRole('heading', { level: 1, name: 'Data quality' })).toBeInTheDocument()
    const rail = screen.getByRole('navigation', { name: 'Main' })
    expect(within(rail).getByRole('link', { current: 'page' })).toHaveTextContent('Data quality')
  })

  it('opens on the session list', () => {
    renderApp('/')
    expect(screen.getByRole('heading', { level: 1, name: 'Sessions' })).toBeInTheDocument()
  })

  it('renders the tokens page in both themes, outside the rail', () => {
    const { container } = renderApp('/tokens')
    expect(container.querySelector('[data-theme="light"]')).not.toBeNull()
    expect(container.querySelector('[data-theme="dark"]')).not.toBeNull()
    expect(screen.queryByRole('navigation', { name: 'Main' })).toBeNull()
  })
})

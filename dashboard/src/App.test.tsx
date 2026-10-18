import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { renderApp } from './test/render'

describe('app shell', () => {
  it('shows the rail with the four sections, in order', () => {
    renderApp('/sessions')
    const rail = screen.getByRole('navigation', { name: 'Main' })
    expect(within(rail).getAllByRole('link').map((a) => a.textContent)).toEqual([
      'Sessions', 'Participants', 'Pre-test', 'Data quality',
    ])
    expect(within(rail).getByText('Runs locally on the lab machine')).toBeInTheDocument()
  })

  it.each([
    ['/sessions', 'Sessions', 'Sessions'],
    ['/sessions/6eb2bd5c', 'Session', 'Sessions'],
    ['/participants/abc', 'Participant', 'Participants'],
    ['/pretest', 'Kanji pre-test', 'Pre-test'],
    ['/quality', 'Data quality', 'Data quality'],
  ])('%s renders its reserved screen and marks its rail item', (path, title, item) => {
    renderApp(path)
    expect(screen.getByRole('heading', { level: 1, name: title })).toBeInTheDocument()
    expect(screen.getByText(/available in a later version\.$/)).toBeInTheDocument()
    const rail = screen.getByRole('navigation', { name: 'Main' })
    expect(within(rail).getByRole('link', { current: 'page' })).toHaveTextContent(item)
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

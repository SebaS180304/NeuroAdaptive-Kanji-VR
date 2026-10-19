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

  it('marks the rail item of the current section', () => {
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

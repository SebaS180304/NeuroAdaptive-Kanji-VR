import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { ExportMenu } from './ExportMenu'

const ID = 'a5748886-55f2-408b-9779-d88b935773e9'

describe('Export CSV menu (V1.9)', () => {
  it('opens by keyboard, moves with the arrows and closes with Esc', async () => {
    const user = userEvent.setup()
    render(<ExportMenu sessionId={ID} condition="BEHAVIOR_ADAPTIVE" />)
    const button = screen.getByRole('button', { name: 'Export CSV' })
    expect(button).toHaveAttribute('aria-haspopup', 'menu')
    expect(screen.queryByRole('menu')).toBeNull()

    button.focus()
    await user.keyboard('{Enter}')
    expect(button).toHaveAttribute('aria-expanded', 'true')
    const [trials, adaptations] = screen.getAllByRole('menuitem')
    expect(trials).toHaveTextContent('Trials (CSV)')
    expect(trials).toHaveFocus()
    expect(trials).toHaveAttribute('href', `/api/research/sessions/${ID}/export.csv?kind=trials`)
    expect(trials).toHaveAttribute('download')
    expect(adaptations).toHaveAttribute('href', `/api/research/sessions/${ID}/export.csv?kind=adaptations`)

    await user.keyboard('{ArrowDown}')
    expect(adaptations).toHaveFocus()
    await user.keyboard('{ArrowDown}')                              // wraps
    expect(trials).toHaveFocus()
    await user.keyboard('{ArrowUp}')
    expect(adaptations).toHaveFocus()

    await user.keyboard('{Escape}')
    expect(screen.queryByRole('menu')).toBeNull()
    expect(button).toHaveFocus()
    expect(button).toHaveAttribute('aria-expanded', 'false')
  })

  it('ArrowUp on the button opens at the last item; a click outside closes', async () => {
    const user = userEvent.setup()
    render(<><ExportMenu sessionId={ID} condition="BEHAVIOR_ADAPTIVE" /><p>outside</p></>)
    screen.getByRole('button', { name: 'Export CSV' }).focus()
    await user.keyboard('{ArrowUp}')
    expect(screen.getByRole('menuitem', { name: /Adaptations/ })).toHaveFocus()
    await user.click(screen.getByText('outside'))
    expect(screen.queryByRole('menu')).toBeNull()
  })

  it('in a static session Adaptations is disabled, with its reason', async () => {
    const user = userEvent.setup()
    render(<ExportMenu sessionId={ID} condition="STATIC" />)
    await user.click(screen.getByRole('button', { name: 'Export CSV' }))
    const adaptations = screen.getByRole('menuitem', { name: /Adaptations \(CSV\)/ })
    expect(adaptations).toHaveAttribute('aria-disabled', 'true')
    expect(adaptations).not.toHaveAttribute('href')
    expect(adaptations).toHaveTextContent('No adaptations in a static session')
  })
})

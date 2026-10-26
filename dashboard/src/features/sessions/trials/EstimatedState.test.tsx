import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EstimatedState, stateLabel } from './EstimatedState'

describe('EstimatedState', () => {
  it('shows UNDERCHALLENGED by its short name, with the enum in the tooltip (Contenido_UI_F-PROFILE.md §3.8)', () => {
    render(<EstimatedState state="UNDERCHALLENGED" reason="Not recorded" />)
    expect(screen.getByText('Low challenge (estimated)')).toHaveAttribute('title', 'UNDERCHALLENGED')
    expect(stateLabel('DISENGAGED')).toBe('Disengaged')
  })
})

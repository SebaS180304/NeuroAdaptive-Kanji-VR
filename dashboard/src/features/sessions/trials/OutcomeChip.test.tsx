import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { OutcomeChip } from './OutcomeChip'

describe('OutcomeChip', () => {
  it('"Not recorded": 1 px dashed border-strong, no fill, no mark, muted text (design-system.md, D-F6-96)', () => {
    render(<OutcomeChip outcome={null} label="Not recorded: 2" title="No outcome was recorded for these changes" />)
    const chip = screen.getByText('Not recorded: 2')
    expect(chip).toHaveClass('h-6', 'border', 'border-dashed', 'border-(--color-border-strong)', 'text-(--color-text-muted)')
    expect(chip.className).not.toMatch(/\bbg-/)
    expect(chip.querySelector('[data-shape]')).toBeNull()
    expect(chip).toHaveAttribute('title', 'No outcome was recorded for these changes')
  })
})

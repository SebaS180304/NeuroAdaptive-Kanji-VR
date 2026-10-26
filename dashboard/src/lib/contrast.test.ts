import { describe, expect, it } from 'vitest'
import tokens from '@/styles/tokens.css?raw'
import { contrastRatio, readTokens } from './contrast'

const light = readTokens(tokens, 'light')
const dark = readTokens(tokens, 'dark')

// The pairs measured in design-system.md ("Measured contrast"), to one decimal.
const measured: [string, Record<string, string>, string, string, number][] = [
  ['Ink on Paper', light, '--color-text', '--color-bg', 16.9],
  ['Slate on Paper', light, '--color-text-muted', '--color-bg', 6.4],
  ['Lagoon on Paper', light, '--color-accent', '--color-bg', 5.9],
  ['Ink on Saffron', light, '--color-on-cta', '--color-cta', 9.0],
  ['dark text on surface', dark, '--color-text', '--color-surface', 14.4],
  ['dark muted on surface', dark, '--color-text-muted', '--color-surface', 6.5],
  ['dark chip', dark, '--color-on-accent-tint', '--color-accent-tint', 8.0],
  ['dark active nav', dark, '--color-on-accent', '--color-accent', 7.9],
  ['on alert tint, light', light, '--color-on-alert-tint', '--color-alert-tint', 6.5],
  ['on alert tint, dark', dark, '--color-on-alert-tint', '--color-alert-tint', 8.5],
  ['multimodal chip, light', light, '--color-on-condition-multimodal-tint', '--color-condition-multimodal-tint', 6.4],
  ['multimodal chip, dark', dark, '--color-on-condition-multimodal-tint', '--color-condition-multimodal-tint', 8.1],
  ['low challenge on white', light, '--color-state-underchallenged', '--color-surface', 6.9],
  ['low challenge on Paper', light, '--color-state-underchallenged', '--color-bg', 6.4],
  ['dark low challenge on surface', dark, '--color-state-underchallenged', '--color-surface', 6.5],
]

// Control borders (corrected Oct 18): non-text contrast, 3:1 minimum.
const borders: [string, Record<string, string>, string, number][] = [
  ['on white', light, '--color-surface', 3.3],
  ['on Paper', light, '--color-bg', 3.1],
  ['on dark surface', dark, '--color-surface', 3.8],
  ['on dark raised', dark, '--color-surface-raised', 3.5],
]

describe('design tokens', () => {
  // Within 0.1: design-system.md rounds two pairs differently (5.95 is "5.9", 14.35 is "14.4").
  it.each(measured)('%s matches design-system.md and passes AA', (_, theme, fg, bg, ratio) => {
    const computed = contrastRatio(theme[fg]!, theme[bg]!)
    expect(Math.abs(computed - ratio)).toBeLessThan(0.1)
    expect(computed).toBeGreaterThanOrEqual(4.5)
  })

  it.each(borders)('border-strong %s matches design-system.md and passes 3:1', (_, theme, bg, ratio) => {
    const computed = contrastRatio(theme['--color-border-strong']!, theme[bg]!)
    expect(Math.abs(computed - ratio)).toBeLessThan(0.1)
    expect(computed).toBeGreaterThanOrEqual(3)
  })

  it('defines every token in both themes, and the dark media block matches the attribute block', () => {
    const media = readTokens(tokens, 'dark-media')
    expect(Object.keys(dark).sort()).toEqual(Object.keys(media).sort())
    for (const [name, value] of Object.entries(dark)) expect(media[name], name).toBe(value)
    for (const name of Object.keys(dark)) expect(light, name).toHaveProperty(name)
  })
})

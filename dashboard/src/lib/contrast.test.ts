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
]

describe('design tokens', () => {
  // Within 0.1: design-system.md rounds two pairs differently (5.95 is "5.9", 14.35 is "14.4").
  it.each(measured)('%s matches design-system.md and passes AA', (_, theme, fg, bg, ratio) => {
    const computed = contrastRatio(theme[fg]!, theme[bg]!)
    expect(Math.abs(computed - ratio)).toBeLessThan(0.1)
    expect(computed).toBeGreaterThanOrEqual(4.5)
  })

  it('defines every token in both themes, and the dark media block matches the attribute block', () => {
    const media = readTokens(tokens, 'dark-media')
    expect(Object.keys(dark).sort()).toEqual(Object.keys(media).sort())
    for (const [name, value] of Object.entries(dark)) expect(media[name], name).toBe(value)
    for (const name of Object.keys(dark)) expect(light, name).toHaveProperty(name)
  })
})

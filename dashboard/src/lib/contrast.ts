// WCAG 2.x contrast, used by the tokens page and its test to check the pairs
// measured in design-system.md against the values in tokens.css.

function luminance(hex: string): number {
  const n = Number.parseInt(hex.slice(1), 16)
  const channel = (c: number) => {
    const s = c / 255
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
  }
  return 0.2126 * channel((n >> 16) & 255) + 0.7152 * channel((n >> 8) & 255) + 0.0722 * channel(n & 255)
}

export function contrastRatio(fg: string, bg: string): number {
  const [hi, lo] = [luminance(fg), luminance(bg)].sort((a, b) => b - a) as [number, number]
  return (hi + 0.05) / (lo + 0.05)
}

const BLOCK_START = {
  light: ":root,\n[data-theme='light'] {",
  dark: "[data-theme='dark'] {",
  'dark-media': ":root:not([data-theme='light']) {",
} as const

/** The hex color tokens of one theme block of tokens.css, by name. */
export function readTokens(css: string, theme: keyof typeof BLOCK_START): Record<string, string> {
  const text = css.replace(/\r\n/g, '\n')
  const start = text.indexOf(BLOCK_START[theme])
  if (start < 0) throw new Error(`tokens.css has no ${theme} block`)
  const body = text.slice(start, text.indexOf('}', start))
  return Object.fromEntries([...body.matchAll(/(--color-[\w-]+):\s*(#[0-9a-f]{6});/gi)].map((m) => [m[1], m[2]]))
}

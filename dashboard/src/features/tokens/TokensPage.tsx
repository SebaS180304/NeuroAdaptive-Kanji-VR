import tokensCss from '@/styles/tokens.css?raw'
import { contrastRatio, readTokens } from '@/lib/contrast'

// Development reference (Task 1.3): every color token in both themes, the
// contrast pairs measured in design-system.md recomputed from tokens.css, and the
// type and shape tokens. Values are read from the stylesheet, never retyped here.

type Theme = 'light' | 'dark'

const PAIRS: { label: string; theme: Theme; fg: string; bg: string; measured: number }[] = [
  { label: 'Ink on Paper', theme: 'light', fg: '--color-text', bg: '--color-bg', measured: 16.9 },
  { label: 'Slate on Paper', theme: 'light', fg: '--color-text-muted', bg: '--color-bg', measured: 6.4 },
  { label: 'Lagoon on Paper', theme: 'light', fg: '--color-accent', bg: '--color-bg', measured: 5.9 },
  { label: 'Ink on Saffron', theme: 'light', fg: '--color-on-cta', bg: '--color-cta', measured: 9.0 },
  { label: 'On alert tint', theme: 'light', fg: '--color-on-alert-tint', bg: '--color-alert-tint', measured: 6.5 },
  { label: 'Text on surface', theme: 'dark', fg: '--color-text', bg: '--color-surface', measured: 14.4 },
  { label: 'Muted on surface', theme: 'dark', fg: '--color-text-muted', bg: '--color-surface', measured: 6.5 },
  { label: 'Chip', theme: 'dark', fg: '--color-on-accent-tint', bg: '--color-accent-tint', measured: 8.0 },
  { label: 'Active nav', theme: 'dark', fg: '--color-on-accent', bg: '--color-accent', measured: 7.9 },
  { label: 'On alert tint', theme: 'dark', fg: '--color-on-alert-tint', bg: '--color-alert-tint', measured: 8.5 },
]

const TYPE = [
  ['type-display', 'Display, Newsreader 500, 36/40 px, −0.72 px', 'Session timeline'],
  ['type-title', 'Title, Newsreader 500, 22/28 px, −0.22 px', 'Where the time went'],
  ['type-subtitle', 'Subtitle, Newsreader 500, 18/24 px, −0.18 px', 'Why the system changed'],
  ['type-lead', 'Lead, Public Sans 400, 16/24 px', 'A summary sentence built from the data.'],
  ['type-figure', 'Figure, Public Sans 600, 24/32 px, −0.24 px', '1284 ms'],
  ['type-body', 'Body, Public Sans 400, 14/20 px, +0.16 px', 'The system changed the environment after S7-007.'],
  ['type-caption', 'Caption, Public Sans 400, 12/16 px, +0.32 px', 'Window of 3 trials'],
  ['type-mono', 'Mono, JetBrains Mono 400, 12/16 px, IDs and times only', 'S7-007  14:32.118'],
] as const

const SHAPES = [
  ['Panel, 2 px', 'h-12 rounded-(--radius-panel) border bg-(--color-surface)'],
  ['Input, 4 px', 'h-10 rounded-(--radius-input) border border-(--color-border-strong)'],
  ['Button and chip, pill', 'h-8 rounded-(--radius-pill) bg-(--color-cta)'],
  ['Data bar, 1 px', 'h-2 rounded-(--radius-bar) bg-(--color-accent)'],
  ['Raised (inspector, popovers)', 'h-12 rounded-(--radius-input) bg-(--color-surface-raised) shadow-(--shadow-raised)'],
] as const

function ThemeColumn({ theme }: { theme: Theme }) {
  const colors = readTokens(tokensCss, theme)
  return (
    <section
      data-theme={theme}
      aria-label={theme === 'light' ? 'Light theme' : 'Dark theme'}
      className="flex flex-col gap-8 bg-(--color-bg) p-8 text-(--color-text)"
    >
      <h2 className="type-display m-0">{theme === 'light' ? 'Light' : 'Dark'}</h2>

      <ul className="m-0 grid list-none grid-cols-[repeat(auto-fill,minmax(232px,1fr))] gap-x-8 gap-y-4 p-0">
        {Object.entries(colors).map(([name, hex]) => (
          <li key={name} className="grid grid-cols-[32px_minmax(0,1fr)] items-center gap-4">
            <span
              aria-hidden="true"
              className="size-8 rounded-(--radius-panel) border border-(--color-border)"
              style={{ background: `var(${name})` }}
            />
            <span className="flex min-w-0 flex-col">
              <span className="type-mono truncate">{name}</span>
              <span className="type-mono text-(--color-text-muted)">{hex}</span>
            </span>
          </li>
        ))}
      </ul>

      <table className="type-body w-full border-collapse">
        <caption className="type-title pb-4 text-left">Contrast, as measured in design-system.md</caption>
        <thead>
          <tr className="type-caption text-(--color-text-muted)">
            <th scope="col" className="h-10 border-b px-4 text-left font-medium">Pair</th>
            <th scope="col" className="h-10 border-b px-4 text-right font-medium">Measured</th>
            <th scope="col" className="h-10 border-b px-4 text-right font-medium">From tokens.css</th>
          </tr>
        </thead>
        <tbody>
          {PAIRS.filter((p) => p.theme === theme).map((p) => {
            const ratio = contrastRatio(colors[p.fg]!, colors[p.bg]!)
            return (
              <tr key={p.label} className="border-b border-(--color-border-subtle)">
                <th scope="row" className="h-10 px-4 text-left font-normal">
                  <span className="inline-flex items-center gap-3">
                    <span
                      aria-hidden="true"
                      className="type-caption inline-flex h-6 items-center rounded-(--radius-panel) px-2"
                      style={{ color: `var(${p.fg})`, background: `var(${p.bg})` }}
                    >
                      Aa
                    </span>
                    {p.label}
                  </span>
                </th>
                <td className="px-4 text-right">{p.measured.toFixed(1)}:1</td>
                <td className="px-4 text-right">{ratio.toFixed(1)}:1</td>
              </tr>
            )
          })}
        </tbody>
      </table>

      <div className="flex flex-col gap-4">
        <h3 className="type-title m-0">Type</h3>
        {TYPE.map(([cls, spec, sample]) => (
          <div key={cls} className="flex flex-col gap-1 border-b border-(--color-border-subtle) pb-3">
            <span className={cls}>{sample}</span>
            <span className="type-caption text-(--color-text-muted)">{spec}</span>
          </div>
        ))}
        <div className="flex flex-col gap-1">
          <span lang="ja" className="type-kanji-display">月</span>
          <span className="type-caption text-(--color-text-muted)">Kanji display, Noto Serif JP 500, 176/192 px</span>
        </div>
      </div>

      <div className="flex flex-col gap-4">
        <h3 className="type-title m-0">Shape and elevation</h3>
        {SHAPES.map(([label, cls]) => (
          <div key={label} className="grid grid-cols-[96px_minmax(0,1fr)] items-center gap-4">
            <div className={cls} />
            <span>{label}</span>
          </div>
        ))}
      </div>
    </section>
  )
}

export function TokensPage() {
  return (
    <main className="grid min-h-screen grid-cols-1 min-[1056px]:grid-cols-2">
      <h1 className="sr-only">Design tokens</h1>
      <ThemeColumn theme="light" />
      <ThemeColumn theme="dark" />
    </main>
  )
}

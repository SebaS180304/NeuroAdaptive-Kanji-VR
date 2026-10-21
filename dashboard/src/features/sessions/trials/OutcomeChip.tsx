import type { CSSProperties } from 'react'

// design-system.md V1.5: outcome chips carry a shape as well as a colour.
type Chip = { box: string; mark: string; shape: string; label: string; style?: CSSProperties }

const CHIP: Record<string, Chip> = {
  POSITIVE: { box: 'bg-(--color-accent-tint) text-(--color-on-accent-tint)', mark: 'size-2 rounded-full bg-(--color-outcome-positive)', shape: 'dot', label: 'Positive' },
  NEUTRAL: { box: 'bg-(--color-border-subtle) text-(--color-text-secondary)', mark: 'size-2 rounded-full border-[1.5px] border-(--color-text-muted)', shape: 'ring', label: 'Neutral' },
  NEGATIVE: { box: 'bg-(--color-alert-tint) text-(--color-on-alert-tint)', mark: 'size-2 bg-(--color-outcome-negative)', shape: 'square', label: 'Negative' },
  UNCERTAIN: {
    box: 'border border-(--color-border-strong) bg-(--color-surface) text-(--color-text-secondary)',
    mark: 'size-2 border border-(--color-text-muted)', shape: 'hatched-square', label: 'Uncertain',
    style: { background: 'var(--hatch-outcome-uncertain)' },
  },
}
const NOT_RECORDED: Chip = { box: 'border border-dashed border-(--color-border-strong) text-(--color-text-muted)', mark: '', shape: 'none', label: 'Not recorded' }

/** label and title replace the enum's words, e.g. the Learner Profile's "Recovered after: 2". */
export function OutcomeChip({ outcome, label, title }: { outcome: string | null; label?: string; title?: string }) {
  const c = (outcome && CHIP[outcome]) || NOT_RECORDED
  return (
    <span title={title} className={`type-caption inline-flex h-6 items-center gap-2 rounded-(--radius-pill) px-2.5 font-medium whitespace-nowrap ${c.box}`}>
      {c.mark && <span aria-hidden="true" data-shape={c.shape} className={c.mark} style={c.style} />}
      {label ?? c.label}
    </span>
  )
}

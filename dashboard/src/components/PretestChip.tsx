import type { Schemas } from '@/api/client'
import { formatDate } from '@/lib/format'

type Participant = Schemas['ResearchParticipant']

const chip =
  'type-caption inline-flex items-center gap-2 rounded-(--radius-pill) whitespace-nowrap font-medium'

// The status chip carries a shape as well as a word (design-system.md, V1.10).
export function PretestChip({ p }: { p: Participant }) {
  if (p.pretest_status === 'COMPLETED')
    return (
      <span className={`${chip} h-7 bg-(--color-border-subtle) px-3 text-(--color-text-secondary)`}>
        <span aria-hidden="true" className="size-2 rounded-full bg-(--color-text-secondary)" />
        Completed {formatDate(p.pretest_completed_at!)}
      </span>
    )
  if (p.pretest_status === 'IN_PROGRESS')
    return (
      <span className={`${chip} h-7 bg-(--color-accent-tint) px-3 text-(--color-on-accent-tint)`}>
        <span
          aria-hidden="true"
          className="size-2.5 rotate-45 rounded-full border-[5px] border-(--color-accent) border-b-(--color-surface) border-l-(--color-surface)"
        />
        In progress, {p.pretest_answered} answered
      </span>
    )
  return (
    <span className={`${chip} h-7 border border-dashed border-(--color-border-strong) px-3 text-(--color-text-secondary)`}>
      <span aria-hidden="true" className="size-2 rounded-full border-[1.5px] border-(--color-text-muted)" />
      Not started
    </span>
  )
}


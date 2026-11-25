import type { Schemas } from '@/api/client'

export type Condition = Schemas['ResearchParticipant']['conditions'][number]

export const CONDITION_LABEL: Record<Condition, string> = {
  STATIC: 'Static',
  BEHAVIOR_ADAPTIVE: 'Behavior-adaptive',
  MULTIMODAL_ADAPTIVE: 'Multimodal-adaptive',
}
// design-system.md "Condition chip" (multimodal drawn Oct 18).
const CONDITION_CHIP: Record<Condition, string> = {
  STATIC: 'bg-(--color-border-subtle) text-(--color-text-secondary)',
  BEHAVIOR_ADAPTIVE: 'bg-(--color-accent-tint) text-(--color-on-accent-tint)',
  MULTIMODAL_ADAPTIVE:
    'border border-(--color-condition-multimodal) bg-(--color-condition-multimodal-tint) text-(--color-on-condition-multimodal-tint)',
}

export function ConditionChip({ c }: { c: Condition }) {
  return (
    <span
      className={`type-caption inline-flex h-6 items-center gap-2 rounded-(--radius-pill) px-2.5 font-medium whitespace-nowrap ${CONDITION_CHIP[c]}`}
    >
      {CONDITION_LABEL[c]}
    </span>
  )
}

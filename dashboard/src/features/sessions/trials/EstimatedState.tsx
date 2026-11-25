import { Missing } from '@/components/Missing'

// design-system.md V1.5: a 10 px dot in the state's token, then the label.
const STATE_DOT: Record<string, string> = {
  STABLE: 'bg-(--color-state-stable)', DISENGAGED: 'bg-(--color-state-disengaged)', OVERLOADED: 'bg-(--color-state-overloaded)',
  UNDERCHALLENGED: 'bg-(--color-state-underchallenged)',
}

// Short names that differ from the enum (Contenido_UI_F-PROFILE.md §3.8); the enum goes in the tooltip.
const SHORT: Record<string, string> = { UNDERCHALLENGED: 'Low challenge (estimated)' }

export const stateLabel = (state: string) => SHORT[state] ?? state[0] + state.slice(1).toLowerCase()

export function EstimatedState({ state, reason }: { state: string | null; reason: string }) {
  if (!state) return <Missing reason={reason} />
  return (
    <span className="inline-flex items-center gap-2 whitespace-nowrap">
      <span aria-hidden="true" className={`size-2.5 rounded-full ${STATE_DOT[state] ?? 'bg-(--color-text-muted)'}`} />
      <span title={SHORT[state] ? state : undefined}>{stateLabel(state)}</span>
    </span>
  )
}

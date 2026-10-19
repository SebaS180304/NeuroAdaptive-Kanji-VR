import type { Schemas } from '@/api/client'

export type SessionStatus = Schemas['ResearchSession']['status']

// design-system.md V1.8 "Session status words": one rule for V1.1, V1.8 and the Session
// View, plain text with no chip or color. The V1.1 status filter uses the same words.
export const SESSION_STATUS_LABEL: Record<SessionStatus, string> = {
  COMPLETED: 'Completed',
  ABORTED: 'Aborted',
  IN_PROGRESS: 'In progress',
  CREATED: 'Not started',
}

/** "Aborted in S7" when the last state is recorded, else the plain word. */
export function sessionStatusText(status: SessionStatus, lastState: string | null): string {
  return status === 'ABORTED' && lastState ? `Aborted in ${lastState.slice(0, 2)}` : SESSION_STATUS_LABEL[status]
}

import { useQuery } from '@tanstack/react-query'
import { NavLink } from 'react-router'
import { getJson, type Schemas } from '@/api/client'

// V1.13 access (design-system.md, validated D-F6-272; texts Contenido_UI_Monitor_Accesos.md §1 and §2). Links only:
// they change nothing in the session, the recording, the engine or live.py (D-F6-268, D-F6-271 (2)).

/** The "live signal" line of V1.13 access, 16 px, in currentColor. */
export function SignalIcon() {
  return (
    <svg aria-hidden="true" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor"
      strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1.5 8.5h3l1.5-4 3 7 1.5-3h4" />
    </svg>
  )
}

/** The session the monitor follows (D-F6-270 (3): the IN_PROGRESS one with the latest event); null when none or unreachable. */
export function useCurrentSession() {
  const q = useQuery({
    queryKey: ['live', 'current'],
    queryFn: () => getJson<Schemas['LiveCurrent']>('/research/live/current'),
    refetchInterval: 5000,
    retry: false,
  })
  return q.isError ? null : (q.data ?? null)   // never claims a session it can't see
}

/** §1: second rail item, "Live monitor"; a dot + "Live" with a running session, an empty ring without. Never disabled. */
export function RailMonitorItem() {
  const current = useCurrentSession()
  const tooltip = current
    ? `Opens the live session monitor for ${current.external_code}, session ${current.session_id.slice(0, 8)}. Read-only.`
    : 'No session in progress. The monitor will show the next session when it starts.'
  return (
    <NavLink
      to="/monitor"
      title={tooltip}
      aria-label={current ? 'Live monitor, session in progress' : 'Live monitor, no session in progress'}
      className={({ isActive }) =>
        `group flex h-10 items-center gap-3 rounded-(--radius-pill) px-4 no-underline outline-offset-2 focus-visible:outline-2 focus-visible:outline-(--color-accent) ${
          isActive ? 'active bg-(--color-accent) font-medium text-(--color-on-accent)' : 'text-(--color-sidebar-text)'
        }`
      }
    >
      <SignalIcon />
      Live monitor
      <span aria-hidden="true" className="ml-auto inline-flex items-center gap-1.5">
        {current ? (
          <>
            <span className="size-2 rounded-full bg-[#3FB7C2] group-[.active]:bg-(--color-on-accent)" />
            <span className="type-caption font-medium text-(--color-sidebar-muted) group-[.active]:text-(--color-on-accent)">Live</span>
          </>
        ) : (
          <span className="size-2 rounded-full border border-(--color-sidebar-muted)" />
        )}
      </span>
    </NavLink>
  )
}

/** §2: only on an IN_PROGRESS session, in Export CSV's place; opens /monitor/<id> in a new window. */
export function SessionMonitorLink({ sessionId }: { sessionId: string }) {
  return (
    <a
      href={`/monitor/${sessionId}`}
      target="_blank"
      rel="noopener"
      aria-label={`Open live monitor for session ${sessionId.slice(0, 8)}`}
      title="Signal quality, live indices, events and adaptation decisions for this session, as it runs. Read-only: it does not change the session. Opens in a new window."
      className="type-body inline-flex h-8 items-center gap-2 rounded-(--radius-pill) border border-(--color-accent) bg-(--color-surface) px-4 font-semibold text-(--color-accent) no-underline"
    >
      <SignalIcon />
      Open live monitor
      <svg aria-hidden="true" width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.25"
        strokeLinecap="round" strokeLinejoin="round">
        <path d="M7 1.5h3.5V5M10.5 1.5 5.5 6.5M9 7.5v3H1.5V3h3" />
      </svg>
    </a>
  )
}

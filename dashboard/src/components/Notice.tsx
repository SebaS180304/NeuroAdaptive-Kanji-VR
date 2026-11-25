import { useId, type ReactNode } from 'react'
import { Link } from 'react-router'

// design-system.md "Notices" (V1.10 States): a 2 px panel, an 18 px icon, a bold
// title, one sentence and an optional outline-pill action. Errors use role
// "alert", the rest "status". Never color alone: each kind has its own icon.

type Kind = 'info' | 'warning' | 'error' | 'neutral'

const KIND: Record<Kind, { box: string; icon: string; path: string }> = {
  info: { box: 'bg-(--color-accent-tint)', icon: 'text-(--color-on-accent-tint)', path: 'M8 1.5a6.5 6.5 0 1 0 0 13a6.5 6.5 0 1 0 0-13M8 7v4.5M8 4.6v.3' },
  warning: { box: 'bg-(--color-warn-tint)', icon: 'text-(--color-lal-high)', path: 'M8 1.8L15 14H1zM8 6.2v3.8M8 11.6v.3' },
  error: { box: 'bg-(--color-alert-tint)', icon: 'text-(--color-on-alert-tint)', path: 'M8 1.5a6.5 6.5 0 1 0 0 13a6.5 6.5 0 1 0 0-13M5.5 5.5l5 5M10.5 5.5l-5 5' },
  neutral: { box: 'border border-(--color-border) bg-(--color-bg)', icon: 'text-(--color-text-muted)', path: 'M8 1.5a6.5 6.5 0 1 0 0 13M8 4.5V8l2.5 1.5' },
}

const actionClass =
  'type-body inline-flex h-8 shrink-0 items-center whitespace-nowrap rounded-(--radius-pill) border border-(--color-text) bg-transparent px-4 font-medium text-(--color-text) no-underline'

export type NoticeAction = { label: string } & ({ to: string } | { onClick: () => void })

export function Notice({
  kind, title, children, action, className = '',
}: { kind: Kind; title: string; children?: ReactNode; action?: NoticeAction; className?: string }) {
  const titleId = useId()
  const k = KIND[kind]
  return (
    <div
      role={kind === 'error' ? 'alert' : 'status'}
      aria-labelledby={titleId}
      className={`type-body flex items-start gap-3 rounded-(--radius-panel) p-4 text-(--color-text) ${k.box} ${className}`}
    >
      <svg aria-hidden="true" width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" className={`mt-px shrink-0 ${k.icon}`}>
        <path d={k.path} />
      </svg>
      <div className="flex flex-1 flex-col gap-1">
        <span id={titleId} className="font-semibold">{title}</span>
        {children && <span className="text-(--color-text-secondary)">{children}</span>}
      </div>
      {action &&
        ('to' in action ? (
          <Link to={action.to} className={actionClass}>{action.label}</Link>
        ) : (
          <button type="button" onClick={action.onClick} className={actionClass}>{action.label}</button>
        ))}
    </div>
  )
}

/** "Backend offline" from the V1.10 States sheet, shared by every screen. */
export function OfflineNotice({ onRetry, className }: { onRetry?: () => void; className?: string }) {
  return (
    <Notice
      kind="error"
      title="Can't reach the backend"
      action={onRetry && { label: 'Try again', onClick: onRetry }}
      className={className}
    >
      Nothing was saved. Check that Docker is running on this PC, then try again.
    </Notice>
  )
}

export function LoadingNotice({ title, className }: { title: string; className?: string }): ReactNode {
  return <Notice kind="neutral" title={title} className={className} />
}

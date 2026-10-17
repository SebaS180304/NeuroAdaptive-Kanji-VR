import type { ReactNode } from 'react'
import { NavLink, Outlet } from 'react-router'

// The navigation rail of the *Session list* artboard: 240 px, items 40 px pills,
// active = accent fill. Icons are the artboard's own 16 px strokes.
const ITEMS: { to: string; label: string; icon: ReactNode }[] = [
  { to: '/sessions', label: 'Sessions', icon: <path d="M2 4h12M2 8h12M2 12h8" /> },
  {
    to: '/participants',
    label: 'Participants',
    icon: (
      <>
        <circle cx="8" cy="5.5" r="2.5" />
        <path d="M3 13.5c.8-2.4 2.8-3.5 5-3.5s4.2 1.1 5 3.5" />
      </>
    ),
  },
  {
    to: '/pretest',
    label: 'Pre-test',
    icon: (
      <>
        <rect x="2.5" y="2.5" width="11" height="11" rx="1" />
        <path d="M5.5 8l1.8 1.8L10.5 6" />
      </>
    ),
  },
  { to: '/quality', label: 'Data quality', icon: <path d="M8 2l5 2v4c0 3-2.2 5-5 6-2.8-1-5-3-5-6V4z" /> },
]

function Rail() {
  return (
    <nav
      aria-label="Main"
      className="flex w-(--rail-width) shrink-0 flex-col gap-2 bg-(--color-sidebar) px-4 py-6 text-(--color-sidebar-text)"
    >
      <div className="flex flex-col gap-1 px-2 pb-6">
        <span className="type-title">NeuroAdaptive VR</span>
        <span className="type-caption text-(--color-sidebar-muted)">Research dashboard</span>
      </div>
      {ITEMS.map(({ to, label, icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            `flex h-10 items-center gap-3 rounded-(--radius-pill) px-4 no-underline outline-offset-2 focus-visible:outline-2 focus-visible:outline-(--color-accent) ${
              isActive ? 'bg-(--color-accent) font-medium text-(--color-on-accent)' : 'text-(--color-sidebar-text)'
            }`
          }
        >
          <svg aria-hidden="true" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
            {icon}
          </svg>
          {label}
        </NavLink>
      ))}
      <div className="flex-1" />
      <p className="type-caption m-0 px-2 text-(--color-sidebar-muted)">Runs locally on the lab machine</p>
    </nav>
  )
}

export function AppShell() {
  return (
    <div className="flex min-h-screen">
      <Rail />
      <main className="grid min-w-0 flex-1 grid-cols-16 content-start gap-x-8 gap-y-8 px-8 pt-8 pb-16">
        <Outlet />
      </main>
    </div>
  )
}

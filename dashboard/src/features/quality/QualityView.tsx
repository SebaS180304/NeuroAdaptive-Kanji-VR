import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'
import { getJson, type Schemas } from '@/api/client'
import { Missing } from '@/components/Missing'
import { LoadingNotice, OfflineNotice } from '@/components/Notice'
import { formatDate } from '@/lib/format'
import { clockMs } from '@/features/sessions/timeline/lanes'

// V1.7 Data quality, artboard *V1.7 Data quality* and its dark variant (canvas version 27),
// with design-system.md "V1.7 and V1.8: cases from real data".

type Quality = Schemas['DataQuality']
type Check = Quality['checks'][number]

// Always these five, in this order; a code outside them is appended.
const CODES = ['MISSING_FIELD', 'UNKNOWN_ENUM', 'ORPHAN_EVENT', 'DUPLICATE', 'FK_VIOLATION']
const WHAT: Record<string, string> = {
  verify_projection: 'Events against projected rows, value by value',
  verify_adaptation: 'Decisions, applications and outcomes',
  verify_trials: 'Trial rows against the JSONB version',
  verify_assembly: 'Assembly attempts and completions',
  verify_reproducibility: 'Seeds and planned sequences',
}
const PAGE = 50
const STEP = 10

const count = (n: number) => n.toLocaleString('en-US')
const cell = 'type-caption h-10 border-y px-6 text-left font-medium whitespace-nowrap text-(--color-text-muted)'
const sessionLink = (id: string) => (
  <Link to={`/sessions/${id}`} className="text-(--color-accent) hover:text-(--color-accent-hover)">{id.slice(0, 8)}</Link>
)

function lead(q: Quality): string {
  const all = q.clean_sessions === q.projected_sessions
    ? 'Every projected session has no open errors and passes every check.'
    : `${q.clean_sessions} of ${q.projected_sessions} projected sessions have no open errors and pass every check.`
  const n = q.not_projected.length
  if (n === 0) return all
  return `${all} ${n === 1 ? '1 session is not projected; it is listed' : `${n} sessions are not projected; they are listed`} at the end.`
}

function CodeBars({ q }: { q: Quality }) {
  const codes = [...CODES, ...Object.keys(q.open_by_code).filter((c) => !CODES.includes(c))]
  const max = Math.max(1, ...Object.values(q.open_by_code))
  return (
    <section
      aria-label="Open errors by code"
      className="col-span-16 flex flex-col gap-4 border-t-2 border-(--color-text) pt-6 min-[1056px]:col-span-7"
    >
      <h2 className="type-title m-0">Open projection errors</h2>
      <p className="type-body m-0 text-(--color-text-secondary)">
        An event that fails to project is kept in the log and listed here until a re-projection resolves it.
      </p>
      <div className="type-body flex flex-col gap-2">
        {codes.map((c) => {
          const n = q.open_by_code[c] ?? 0
          return (
            <div key={c} className="grid grid-cols-[136px_minmax(0,1fr)_40px] items-center gap-4">
              <span className="type-mono">{c}</span>
              <div className="h-2 rounded-(--radius-bar) bg-(--color-border-subtle)">
                <div className="h-2 rounded-(--radius-bar) bg-(--color-alert)" style={{ width: `${(n / max) * 100}%` }} />
              </div>
              <span className="text-right text-(--color-text-muted)">{n}</span>
            </div>
          )
        })}
      </div>
      <p className="type-caption m-0 text-(--color-text-muted)">{count(q.resolved_errors)} resolved by re-projection so far</p>
    </section>
  )
}

function CheckRow({ c }: { c: Check }) {
  const [open, setOpen] = useState(false)
  const [all, setAll] = useState(false)
  const n = c.rows.length
  return (
    <>
      <tr className="border-b border-(--color-border-subtle)">
        <td className="w-10 pl-4">
          {n > 0 && (
            <button
              type="button"
              aria-expanded={open}
              aria-label="Show affected sessions"
              onClick={() => setOpen(!open)}
              className="inline-flex size-6 items-center justify-center rounded-(--radius-input) border border-(--color-border-strong) bg-(--color-surface) text-(--color-text)"
            >
              <svg aria-hidden="true" width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.6">
                <path d={open ? 'M3 7.5l3-3 3 3' : 'M3 4.5l3 3 3-3'} />
              </svg>
            </button>
          )}
        </td>
        <th scope="row" className="type-mono h-12 pr-4 pl-2 text-left font-normal">{c.name}</th>
        <td className="px-4 text-(--color-text-secondary)">{WHAT[c.name] ?? <Missing reason="No description" />}</td>
        <td className="px-4 text-right">{n}</td>
        <td className="pr-6 pl-4">
          <span className="inline-flex items-center gap-2 whitespace-nowrap">
            <span aria-hidden="true" className={`size-2 rounded-full ${n ? 'bg-(--color-quality-warn)' : 'bg-(--color-quality-ok)'}`} />
            {n ? 'Needs review' : 'Pass'}
          </span>
        </td>
      </tr>
      {open && (
        <tr className="border-b border-(--color-border-subtle) bg-(--color-explain-bg)">
          <td />
          <td colSpan={4} className="py-4 pr-6 pl-2">
            <div className="flex flex-col gap-2">
              <span className="type-caption text-(--color-text-muted)">Affected sessions, {STEP} at a time</span>
              {(all ? c.rows : c.rows.slice(0, STEP)).map((r, i) => (
                <div key={i} className="grid grid-cols-[112px_minmax(0,1fr)] items-baseline gap-4">
                  <span className="type-mono">{sessionLink(r.session_id)}</span>
                  <span className="text-(--color-text-secondary)">{r.check}: {r.detail ?? '—'}</span>
                </div>
              ))}
              {!all && n > STEP && (
                <button
                  type="button"
                  onClick={() => setAll(true)}
                  className="type-body h-8 self-start rounded-(--radius-pill) border border-(--color-accent) px-4 font-medium text-(--color-on-accent-tint)"
                >
                  Show all {n}
                </button>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

function Checks({ checks }: { checks: Check[] }) {
  return (
    <section aria-label="Verification checks" className="col-span-16 overflow-x-auto rounded-(--radius-panel) border bg-(--color-surface) min-[1056px]:col-span-9">
      <table className="type-body w-full min-w-[560px] border-collapse">
        <caption className="type-title px-6 pt-6 pb-2 text-left">Verification checks</caption>
        <thead>
          <tr>
            <th scope="col" className="w-10 border-b pl-4"><span className="sr-only">Details</span></th>
            {[['Check', 'pl-2 pr-4 text-left'], ['What it compares', 'px-4 text-left'], ['Discrepancies', 'px-4 text-right'], ['Result', 'pl-4 pr-6 text-left']].map(([h, cls]) => (
              <th key={h} scope="col" className={`type-caption h-10 border-b font-medium whitespace-nowrap text-(--color-text-muted) ${cls}`}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {checks.map((c) => <CheckRow key={c.name} c={c} />)}
        </tbody>
      </table>
    </section>
  )
}

function Errors({ q }: { q: Quality }) {
  const [code, setCode] = useState('')
  const [page, setPage] = useState(0)
  const codes = [...CODES, ...Object.keys(q.open_by_code).filter((c) => !CODES.includes(c))]
  const rows = q.open_errors.filter((e) => !code || e.error_code === code)
  const shown = rows.slice(page * PAGE, (page + 1) * PAGE)
  return (
    <section aria-label="Open errors" className="col-span-16 overflow-x-auto rounded-(--radius-panel) border bg-(--color-surface)">
      <div className="flex flex-wrap items-center justify-between gap-4 px-6 pt-6 pb-4">
        <h2 className="type-title m-0">Errors to resolve</h2>
        <label className="type-body flex items-center gap-2 text-(--color-text-secondary)">
          Code
          <select
            value={code}
            onChange={(e) => { setCode(e.target.value); setPage(0) }}
            className="type-body h-8 rounded-(--radius-input) border border-(--color-border-strong) bg-(--color-surface) px-2 text-(--color-text)"
          >
            <option value="">All codes</option>
            {codes.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
      </div>
      {q.open_errors.length === 0 ? (
        <p className="type-body m-0 px-6 pb-6 text-(--color-text-muted)">
          No errors to resolve. {count(q.resolved_errors)} resolved by re-projection so far.
        </p>
      ) : (
        <>
          <table aria-label="Errors to resolve" className="type-body w-full min-w-[960px] border-collapse">
            <thead>
              <tr>{['Event', 'Session', 'Code', 'Detail', 'At'].map((h) => <th key={h} scope="col" className={cell}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {shown.map((e) => (
                <tr key={e.id} className="border-b border-(--color-border-subtle)">
                  <td className="type-mono h-12 px-6">{e.event_id}</td>
                  <td className="type-mono px-6">{sessionLink(e.session_id)}</td>
                  <td className="type-mono px-6">{e.error_code}</td>
                  <td className="px-6 text-(--color-text-secondary)">{e.detail ?? <Missing reason="No detail recorded" />}</td>
                  <td className="type-mono px-6">
                    {e.session_elapsed_ms !== null ? clockMs(e.session_elapsed_ms) : <Missing reason="The event has no session time" />}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length === 0 ? (
            <p className="type-body m-0 px-6 py-4 text-(--color-text-muted)">No open errors with this code.</p>
          ) : (
            <div className="flex items-center justify-between gap-4 px-6 py-4">
              <span className="type-body text-(--color-text-secondary)">
                Showing {page * PAGE + 1}–{page * PAGE + shown.length} of {rows.length}
              </span>
              <div className="flex gap-2">
                {[['Previous', page - 1, page === 0], ['Next', page + 1, (page + 1) * PAGE >= rows.length]].map(([label, to, off]) => (
                  <button
                    key={String(label)}
                    type="button"
                    disabled={Boolean(off)}
                    onClick={() => setPage(Number(to))}
                    className="type-body h-8 rounded-(--radius-pill) border border-(--color-text) px-4 font-medium text-(--color-text) disabled:border-(--color-border) disabled:font-normal disabled:text-(--color-text-muted)"
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </section>
  )
}

function NotProjected({ sessions }: { sessions: Quality['not_projected'] }) {
  return (
    <section aria-label="Sessions not projected" className="col-span-16 overflow-x-auto rounded-(--radius-panel) border bg-(--color-surface)">
      <div className="flex flex-col gap-1 px-6 pt-6 pb-4">
        <h2 className="type-title m-0">Sessions not projected</h2>
        {sessions.length > 0 && (
          <p className="type-body m-0 text-(--color-text-secondary)">
            They have no rows in the analysis tables, so the checks above don't cover them.
          </p>
        )}
      </div>
      {sessions.length === 0 ? (
        <p className="type-body m-0 px-6 pb-6 text-(--color-text-muted)">Every recorded session is projected.</p>
      ) : (
        <table aria-label="Sessions not projected" className="type-body w-full min-w-[960px] border-collapse">
          <thead>
            <tr>{['Session', 'Participant', 'Recorded', 'Status', 'Reason'].map((h) => <th key={h} scope="col" className={cell}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.session_id} className="border-b border-(--color-border-subtle)">
                <td className="type-mono h-12 px-6">{sessionLink(s.session_id)}</td>
                <td className="type-mono px-6">
                  <Link to={`/participants/${s.participant_id}`} className="text-(--color-accent) hover:text-(--color-accent-hover)">
                    {s.external_code}
                  </Link>
                </td>
                <td className="px-6 whitespace-nowrap">{formatDate(s.created_at)}</td>
                <td className="px-6">{s.projection_status === 'NO_DATA' ? 'No events recorded' : 'Not projected'}</td>
                {/* The API records no reason yet; the column is drawn for when it does. */}
                <td className="px-6"><Missing reason="No reason recorded" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

export function QualityView() {
  const { data, error, isPending, refetch } = useQuery({
    queryKey: ['research', 'quality'],
    queryFn: () => getJson<Quality>('/research/quality'),
  })
  return (
    <>
      <header className="col-span-16 flex flex-col gap-4 min-[1056px]:col-span-11">
        <h1 className="type-display m-0">Data quality</h1>
        {data && <p className="type-lead m-0 max-w-[680px] text-(--color-text-secondary)">{lead(data)}</p>}
      </header>
      {isPending && <LoadingNotice title="Running the checks…" className="col-span-16" />}
      {error && <OfflineNotice onRetry={() => void refetch()} className="col-span-16" />}
      {data && (
        <>
          <CodeBars q={data} />
          <Checks checks={data.checks} />
          <Errors q={data} />
          <NotProjected sessions={data.not_projected} />
        </>
      )}
    </>
  )
}

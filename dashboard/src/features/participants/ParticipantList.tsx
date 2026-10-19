import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'
import { getJson, type Schemas } from '@/api/client'
import { CONDITION_LABEL, ConditionChip, type Condition } from '@/components/ConditionChip'
import { Missing } from '@/components/Missing'
import { LoadingNotice, OfflineNotice } from '@/components/Notice'
import { PretestChip } from '@/components/PretestChip'
import { formatDate, formatPercent } from '@/lib/format'

// V1.11 Participant list, artboard *V1.11 Participant list (proposed)*, light and dark.

type Participant = Schemas['ResearchParticipant']
type PretestStatus = Participant['pretest_status']

const STATUS_LABEL: Record<PretestStatus, string> = {
  COMPLETED: 'Completed',
  IN_PROGRESS: 'In progress',
  NOT_STARTED: 'Not started',
}

function notes(p: Participant): string[] {
  return [
    ...(p.previous_japanese_experience ? ['Previous Japanese study reported'] : []),
    ...(p.flagged_count ? ['Kanji kept with no substitute'] : []),
  ]
}

function StatusBar({ participants }: { participants: Participant[] }) {
  const count = (s: PretestStatus) => participants.filter((p) => p.pretest_status === s).length
  const [done, progress, none] = [count('COMPLETED'), count('IN_PROGRESS'), count('NOT_STARTED')]
  return (
    <figure
      aria-label="Pre-test status of all participants"
      className="col-span-16 m-0 flex flex-col gap-2 self-end border-t-2 border-(--color-text) pt-4 min-[1056px]:col-span-7"
    >
      <div
        role="img"
        aria-label={`Pre-test: ${done} completed, ${progress} in progress, ${none} not started`}
        className="flex h-4 gap-0.5"
      >
        {done > 0 && <div style={{ flex: done }} className="bg-(--color-trial-correct)" />}
        {progress > 0 && <div style={{ flex: progress }} className="bg-(--color-accent)" />}
        {none > 0 && <div style={{ flex: none }} className="border border-dashed border-(--color-distractor)" />}
      </div>
      <figcaption className="type-caption flex flex-wrap gap-4 text-(--color-text-muted)">
        <span>Pre-test completed {done}</span>
        <span>In progress {progress}</span>
        <span>Not started {none}</span>
      </figcaption>
    </figure>
  )
}

const field = 'type-caption flex flex-col gap-2 text-(--color-text-muted)'
const control =
  'type-body h-10 rounded-(--radius-input) border border-(--color-border-strong) bg-(--color-surface) text-(--color-text)'

const COLUMNS: [string, 'left' | 'right'][] = [
  ['Participant', 'left'], ['Registered', 'left'], ['Pre-test', 'left'], ['Sessions', 'right'],
  ['Conditions', 'left'], ['Last session', 'left'], ['Last accuracy', 'right'], ['Notes for the researcher', 'left'],
]

export function ParticipantList() {
  const { data, error, isPending, refetch } = useQuery({
    queryKey: ['research', 'participants'],
    queryFn: () => getJson<Participant[]>('/research/participants'),
  })
  const [code, setCode] = useState('')
  const [status, setStatus] = useState<PretestStatus | ''>('')
  const [condition, setCondition] = useState<Condition | ''>('')
  const [onlyNotes, setOnlyNotes] = useState(false)

  const rows = (data ?? []).filter(
    (p) =>
      p.external_code.toLowerCase().includes(code.trim().toLowerCase()) &&
      (!status || p.pretest_status === status) &&
      (!condition || p.conditions.includes(condition)) &&
      (!onlyNotes || notes(p).length > 0),
  )

  return (
    <>
      <header className="col-span-16 flex flex-col gap-2 min-[1056px]:col-span-9">
        <h1 className="type-display m-0">Participants</h1>
        {data && (
          <p className="type-lead m-0 text-(--color-text-secondary)">
            {data.length} {data.length === 1 ? 'participant' : 'participants'} registered. Open one to see their
            sessions, how they changed across visits, and the kanji their pre-test replaced.
          </p>
        )}
      </header>
      {data && <StatusBar participants={data} />}

      {isPending && <LoadingNotice title="Loading participants…" className="col-span-16" />}
      {error && <OfflineNotice onRetry={() => void refetch()} className="col-span-16" />}

      {data && (
        <>
          <form aria-label="Filters" className="col-span-16 flex flex-wrap items-end gap-4" onSubmit={(e) => e.preventDefault()}>
            <label className={`${field} flex-[1_1_240px]`}>
              Participant code
              <input
                type="search"
                placeholder="External code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className={`${control} px-3`}
              />
            </label>
            <label className={`${field} flex-[1_1_200px]`}>
              Pre-test
              <select value={status} onChange={(e) => setStatus(e.target.value as PretestStatus | '')} className={`${control} px-2`}>
                <option value="">Any status</option>
                {(['COMPLETED', 'IN_PROGRESS', 'NOT_STARTED'] as const).map((s) => (
                  <option key={s} value={s}>{STATUS_LABEL[s]}</option>
                ))}
              </select>
            </label>
            <label className={`${field} flex-[1_1_200px]`}>
              Has sessions in
              <select value={condition} onChange={(e) => setCondition(e.target.value as Condition | '')} className={`${control} px-2`}>
                <option value="">Any condition</option>
                {(Object.keys(CONDITION_LABEL) as Condition[]).map((c) => (
                  <option key={c} value={c}>{CONDITION_LABEL[c]}</option>
                ))}
              </select>
            </label>
            <label className="type-body flex h-10 items-center gap-2 text-(--color-text-secondary)">
              <input
                type="checkbox"
                checked={onlyNotes}
                onChange={(e) => setOnlyNotes(e.target.checked)}
                className="accent-(--color-accent)"
              />
              Only with notes for the researcher
            </label>
          </form>

          <section
            aria-label="Participants table"
            className="col-span-16 overflow-x-auto rounded-(--radius-panel) border bg-(--color-surface)"
          >
            <table className="type-body w-full min-w-[1040px] border-collapse">
              <thead>
                <tr>
                  {COLUMNS.map(([label, align]) => (
                    <th
                      key={label}
                      scope="col"
                      className={`type-caption h-10 border-b px-4 font-medium whitespace-nowrap text-(--color-text-muted) ${align === 'right' ? 'text-right' : 'text-left'}`}
                    >
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((p) => {
                  const noSessions = p.session_count === 0
                  return (
                    <tr key={p.id} className="border-b border-(--color-border-subtle)">
                      <th scope="row" className="type-mono h-14 px-4 text-left font-normal">
                        <Link to={`/participants/${p.id}`} className="text-(--color-accent) hover:text-(--color-accent-hover)">
                          {p.external_code}
                        </Link>
                      </th>
                      <td className="px-4 whitespace-nowrap">{formatDate(p.created_at)}</td>
                      <td className="px-4"><PretestChip p={p} /></td>
                      <td className="px-4 text-right">{p.session_count}</td>
                      <td className="px-4">
                        <span className="inline-flex flex-wrap gap-1">
                          {p.conditions.map((c) => (
                            <ConditionChip key={c} c={c} />
                          ))}
                        </span>
                      </td>
                      <td className="px-4 whitespace-nowrap">
                        {p.last_session_at ? formatDate(p.last_session_at) : <Missing reason="No sessions yet" />}
                      </td>
                      <td className="px-4 text-right">
                        {p.last_session_accuracy !== null ? (
                          formatPercent(p.last_session_accuracy)
                        ) : (
                          <Missing reason={noSessions ? 'No sessions yet' : 'No answered trials in the last session'} />
                        )}
                      </td>
                      <td className="px-4 text-(--color-text-secondary)">
                        <span className="flex flex-col gap-1">
                          {notes(p).map((n) => (
                            <span key={n} className="inline-flex items-center gap-2">
                              <svg aria-hidden="true" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="var(--color-lal-high)" strokeWidth="1.6">
                                <path d="M8 1.8L15 14H1z" />
                                <path d="M8 6.2v3.8M8 11.6v.3" />
                              </svg>
                              {n}
                            </span>
                          ))}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
            {rows.length === 0 && (
              <p className="type-body m-0 px-4 py-6 text-(--color-text-muted)">
                {data.length === 0 ? 'No participants registered yet.' : 'No participant matches these filters.'}
              </p>
            )}
          </section>
        </>
      )}
    </>
  )
}

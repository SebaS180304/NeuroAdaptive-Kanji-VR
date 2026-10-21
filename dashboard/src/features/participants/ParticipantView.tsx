import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { ApiError, getJson, type Schemas } from '@/api/client'
import { ConditionChip } from '@/components/ConditionChip'
import { Missing } from '@/components/Missing'
import { LoadingNotice, Notice, OfflineNotice } from '@/components/Notice'
import { sessionStatusText } from '@/components/SessionStatus'
import { formatDate, formatPercent } from '@/lib/format'
import { LearnerProfile } from './LearnerProfile'
import { NoteList, participantNotes } from './notes'

// V1.8 Participant View, artboard *V1.8 Participant View* and its dark variant (canvas
// version 27), with design-system.md "V1.7 and V1.8: cases from real data". Since F-PROFILE
// (canvas 37-39) the Learner Profile comes first, under the header; its "Across sessions"
// replaces the old trend chart, and the sessions fact and conditions sit right of the title.

type Detail = Schemas['ResearchParticipantDetail']
type Row = Detail['sessions'][number]

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`

function lead(p: Detail): string {
  const n = p.sessions.length
  const before = p.sessions.filter((s) => s.before_pretest).length
  const replaced = p.substitutions.filter((s) => s.substitute !== null).length
  // Before the pre-test is complete, "No sessions recorded yet." takes the second sentence's place.
  const none = 'No sessions recorded yet.'
  if (p.pretest_status === 'NOT_STARTED')
    return `The pre-test hasn't been started. ${n === 0 ? none : 'Sessions use the default kanji set until it is completed.'}`
  if (p.pretest_status === 'IN_PROGRESS')
    // No "of [n]": the pre-test has no fixed length (each known kanji pulls in reserves).
    return `The pre-test is in progress (${p.pretest_answered} kanji answered). ${n === 0 ? none : 'Sessions use the default set until it is completed.'}`
  if (n === 0)
    return replaced > 0
      ? `The pre-test is complete, with ${replaced} kanji replaced. ${none}`
      : `The pre-test is complete and no kanji needed replacing. ${none}`
  // "Later sessions" only when there are some: a participant can have none after the pre-test.
  if (before === n)
    return n === 1
      ? 'The only session was recorded before the pre-test and used the default set.'
      : `All ${n} sessions were recorded before the pre-test and used the default set.`
  if (before > 0)
    return `${before} of ${n} sessions ${before === 1 ? 'was' : 'were'} recorded before the pre-test and used the default set. Later sessions used the confirmed set${replaced > 0 ? `, with ${replaced} kanji replaced` : ''}.`
  return replaced > 0
    ? `Every session used the kanji set confirmed by the pre-test, with ${replaced} kanji replaced.`
    : 'Every session used the kanji set confirmed by the pre-test. No kanji needed replacing.'
}

function sessionsFact(sessions: Row[]): string {
  const count = (s: Row['status']) => sessions.filter((x) => x.status === s).length
  if (sessions.length === 0) return 'None yet'
  return [
    `${count('COMPLETED')} completed, ${count('ABORTED')} aborted`,
    ...(count('IN_PROGRESS') ? [`${count('IN_PROGRESS')} in progress`] : []),
    ...(count('CREATED') ? [`${count('CREATED')} not started`] : []),
  ].join(', ')
}

function Facts({ p }: { p: Detail }) {
  const before = p.sessions.filter((s) => s.before_pretest).length
  const notes = [
    ...participantNotes(p),
    ...(before > 0 ? [`${plural(before, 'session', 'sessions')} recorded before the pre-test`] : []),
  ]
  return (
    <aside aria-label="Participant facts" className="col-span-16 min-[1056px]:col-span-6">
      <dl className="type-body m-0 grid grid-cols-[120px_minmax(0,1fr)] gap-x-4 gap-y-2">
        <dt className="text-(--color-text-muted)">Pre-test</dt>
        {p.pretest_completed_at ? (
          <dd className="m-0 flex items-center gap-2">
            <span aria-hidden="true" className="size-2 rounded-full bg-(--color-trial-correct)" />
            Completed {formatDate(p.pretest_completed_at)}
          </dd>
        ) : (
          <dd className="m-0 flex flex-col items-start gap-2">
            <span>Not complete. Unity can't start a session yet.</span>
            <Link
              to="/pretest"
              className="type-body inline-flex h-8 items-center rounded-(--radius-pill) bg-(--color-cta) px-4 font-semibold text-(--color-on-cta) no-underline"
            >
              Open the pre-test
            </Link>
          </dd>
        )}
        <dt className="text-(--color-text-muted)">Notes</dt>
        <dd className="m-0">{notes.length ? <NoteList notes={notes} /> : 'None'}</dd>
      </dl>
    </aside>
  )
}

function Substitutions({ p }: { p: Detail }) {
  return (
    <section
      aria-label="Pre-test substitutions"
      className="col-span-16 flex flex-col gap-4 border-t-2 border-(--color-text) pt-6 min-[1056px]:col-span-6"
    >
      <h2 className="type-title m-0">Kanji replaced by the pre-test</h2>
      {p.substitutions.length > 0 ? (
        <>
          <p className="type-body m-0 text-(--color-text-secondary)">
            Known kanji were swapped for the closest reserve kanji before the first visit.
          </p>
          <table aria-label="Kanji replaced by the pre-test" className="type-body w-full border-collapse">
            <thead>
              <tr>
                {['Set', 'Known', 'Used instead'].map((h) => (
                  <th key={h} scope="col" className="type-caption h-8 border-b text-left font-medium text-(--color-text-muted)">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {p.substitutions.map((s) => (
                <tr key={s.original} className="border-b border-(--color-border-subtle)">
                  <td className="h-12">{s.set_name}</td>
                  <td className="font-(family-name:--font-kanji) text-[22px] font-medium">{s.original}</td>
                  {s.substitute ? (
                    <td className="font-(family-name:--font-kanji) text-[22px] font-medium">{s.substitute}</td>
                  ) : (
                    <td className="text-(--color-text-muted)">No valid substitute: kept and flagged</td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : (
        <p className="type-body m-0 text-(--color-text-secondary)">
          {p.pretest_completed_at ? 'No kanji needed replacing.' : 'Shown once the pre-test is complete.'}
        </p>
      )}
    </section>
  )
}

const COLUMNS: [string, 'left' | 'right'][] = [
  ['#', 'right'], ['Session', 'left'], ['Condition', 'left'], ['Recorded', 'left'], ['Status', 'left'],
  ['Accuracy', 'right'], ['Mean RT', 'right'], ['Adaptations', 'right'], ['Head-away', 'right'],
]

const notRecorded = (s: Row) =>
  s.projection_status === 'NO_DATA' ? 'No data recorded' : s.projection_status === 'NOT_PROJECTED' ? 'Not projected' : null

function SessionsTable({ sessions }: { sessions: Row[] }) {
  return (
    <section aria-label="Sessions of this participant" className="col-span-16 overflow-x-auto rounded-(--radius-panel) border bg-(--color-surface)">
      <table className="type-body w-full min-w-[960px] border-collapse">
        <caption className="type-title px-6 pt-6 pb-4 text-left">Sessions in order</caption>
        <thead>
          <tr>
            {COLUMNS.map(([label, align]) => (
              <th
                key={label}
                scope="col"
                className={`type-caption h-10 border-y px-4 font-medium whitespace-nowrap text-(--color-text-muted) ${align === 'right' ? 'text-right' : 'text-left'}`}
              >
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sessions.map((s, i) => {
            const gap = notRecorded(s)
            return (
              <tr key={s.session_id} className="border-b border-(--color-border-subtle)">
                <td className="h-14 px-4 text-right">{i + 1}</td>
                <td className="type-mono px-4">
                  <Link to={`/sessions/${s.session_id}`} className="text-(--color-accent) hover:text-(--color-accent-hover)">
                    {s.session_id.slice(0, 8)}
                  </Link>
                </td>
                <td className="px-4"><ConditionChip c={s.condition} /></td>
                <td className="px-4 whitespace-nowrap">
                  {formatDate(s.created_at)}
                  {s.before_pretest && <span className="type-caption block text-(--color-text-muted)">Before the pre-test</span>}
                </td>
                <td className="px-4 whitespace-nowrap">{sessionStatusText(s.status, s.last_state)}</td>
                <td className="px-4 text-right">
                  {s.accuracy !== null ? formatPercent(s.accuracy) : <Missing reason={gap ?? 'No answered trials'} />}
                </td>
                <td className="px-4 text-right whitespace-nowrap">
                  {s.mean_rt_ms !== null ? `${Math.round(s.mean_rt_ms)} ms` : <Missing reason={gap ?? 'No answered trials'} />}
                </td>
                <td className="px-4 text-right">
                  {s.decision_count !== null ? (
                    s.decision_count
                  ) : (
                    <Missing reason={s.condition === 'STATIC' ? 'No adaptations in a static session' : gap ?? 'No decisions recorded'} />
                  )}
                </td>
                <td className="px-4 text-right whitespace-nowrap">
                  {s.head_away_count !== null && s.head_away_ms !== null ? (
                    <>
                      {s.head_away_count} <span className="text-(--color-text-muted)">({(s.head_away_ms / 1000).toFixed(1)} s)</span>
                    </>
                  ) : (
                    <Missing reason="Head-away was not recorded in this session" />
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      {sessions.length === 0 && <p className="type-body m-0 px-6 pb-6 text-(--color-text-muted)">No sessions recorded yet.</p>}
    </section>
  )
}

export function ParticipantView() {
  const { participantId } = useParams()
  const { data, error, isPending, refetch } = useQuery({
    queryKey: ['research', 'participants', participantId],
    queryFn: () => getJson<Detail>(`/research/participants/${participantId}`),
  })
  const notFound = error instanceof ApiError && (error.status === 404 || error.status === 422)

  return (
    <>
      <header className="col-span-16 flex flex-col gap-4 min-[1056px]:col-span-10">
        <Link to="/participants" className="type-caption text-(--color-accent) no-underline hover:text-(--color-accent-hover)">Participants</Link>
        <h1 className="type-display m-0">
          Participant {data && <span className="font-mono text-[30px] tracking-[-0.6px]">{data.external_code}</span>}
        </h1>
      </header>
      {data && (
        <div aria-label="Sessions and conditions" className="type-body col-span-16 flex flex-col gap-2 self-end min-[1056px]:col-span-6 min-[1056px]:items-end">
          <div className="flex flex-wrap gap-2">
            {data.conditions.length ? data.conditions.map((c) => <ConditionChip key={c} c={c} />) : <Missing reason="No sessions yet" />}
          </div>
          <span className="text-(--color-text-secondary)">{sessionsFact(data.sessions)}</span>
        </div>
      )}

      {isPending && <LoadingNotice title="Loading the participant…" className="col-span-16" />}
      {notFound && (
        <Notice kind="error" title="Participant not found" action={{ label: 'Back to participants', to: '/participants' }} className="col-span-16">
          No participant has this id. It may have been deleted.
        </Notice>
      )}
      {error && !notFound && <OfflineNotice onRetry={() => void refetch()} className="col-span-16" />}

      {data && (
        <>
          <LearnerProfile p={data} />
          <p className="type-lead col-span-16 m-0 max-w-[640px] text-(--color-text-secondary) min-[1056px]:col-span-10">{lead(data)}</p>
          <Facts p={data} />
          <Substitutions p={data} />
          <SessionsTable sessions={data.sessions} />
        </>
      )}
    </>
  )
}

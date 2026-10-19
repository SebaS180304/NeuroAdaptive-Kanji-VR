import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { ApiError, getJson, type Schemas } from '@/api/client'
import { CONDITION_LABEL, ConditionChip, type Condition } from '@/components/ConditionChip'
import { Missing } from '@/components/Missing'
import { LoadingNotice, Notice, OfflineNotice } from '@/components/Notice'
import { sessionStatusText } from '@/components/SessionStatus'
import { formatDate, formatPercent } from '@/lib/format'
import { NoteList, participantNotes } from './notes'
import { formatMeasure, SHAPE, TrendChart, type Measure, type TrendPoint } from './TrendChart'

// V1.8 Participant View, artboard *V1.8 Participant View* and its dark variant (canvas
// version 27), with design-system.md "V1.7 and V1.8: cases from real data".

type Detail = Schemas['ResearchParticipantDetail']
type Row = Detail['sessions'][number]

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`

function lead(p: Detail): string {
  const n = p.sessions.length
  const before = p.sessions.filter((s) => s.before_pretest).length
  const replaced = p.substitutions.filter((s) => s.substitute !== null).length
  const none = n === 0 ? ' No sessions recorded yet.' : ''
  if (p.pretest_status === 'NOT_STARTED')
    return `The pre-test hasn't been started. Sessions use the default kanji set until it is completed.${none}`
  if (p.pretest_status === 'IN_PROGRESS')
    // shortcut: no "of [n]" as drawn, since the pre-test has no fixed length (each known kanji
    // pulls in reserves); add it if the design chat settles what the total is.
    return `The pre-test is in progress (${p.pretest_answered} kanji answered). Sessions use the default set until it is completed.${none}`
  if (n === 0) return 'No sessions recorded yet.'
  if (before > 0)
    // "Later sessions" only when there are some: a participant can have none after the pre-test.
    return `${before} of ${n} sessions ${before === 1 ? 'was' : 'were'} recorded before the pre-test and used the default set.${before < n ? ' Later sessions used the confirmed set.' : ''}`
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
    <aside aria-label="Participant facts" className="col-span-16 self-end min-[1056px]:col-span-6">
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
        <dt className="text-(--color-text-muted)">Sessions</dt>
        <dd className="m-0">{sessionsFact(p.sessions)}</dd>
        <dt className="text-(--color-text-muted)">Conditions</dt>
        <dd className="m-0">{p.conditions.length ? p.conditions.map((c) => CONDITION_LABEL[c]).join(', ') : <Missing reason="No sessions yet" />}</dd>
        <dt className="text-(--color-text-muted)">Notes</dt>
        <dd className="m-0">{notes.length ? <NoteList notes={notes} /> : 'None'}</dd>
      </dl>
    </aside>
  )
}

const MEASURES: [Measure, string, string][] = [
  ['accuracy', 'Accuracy', 'Accuracy per completed session'],
  ['rt', 'Response time', 'Mean response time per completed session'],
]

// Legend marks drawn as small SVGs, in the chart's shapes.
function Mark({ c }: { c: Condition }) {
  const fill = `var(${SHAPE[c].token})`
  return (
    <svg aria-hidden="true" width="12" height="12" viewBox="0 0 12 12">
      {c === 'STATIC' && <rect x="1" y="1" width="10" height="10" fill={fill} />}
      {c === 'BEHAVIOR_ADAPTIVE' && <circle cx="6" cy="6" r="5" fill={fill} />}
      {c === 'MULTIMODAL_ADAPTIVE' && <polygon points="6,0.5 11.5,11 0.5,11" fill={fill} />}
    </svg>
  )
}

function Trend({ p }: { p: Detail }) {
  const [measure, setMeasure] = useState<Measure>('accuracy')
  // Only COMPLETED sessions are drawn; n is the row's # in "Sessions in order".
  const points: TrendPoint[] = p.sessions.flatMap((s, i) => {
    const value = measure === 'accuracy' ? s.accuracy : s.mean_rt_ms
    return s.status === 'COMPLETED' && value !== null
      ? [{ n: i + 1, condition: s.condition, value, date: formatDate(s.created_at), visit: s.visit_number }]
      : []
  })
  const present = (Object.keys(SHAPE) as Condition[]).filter((c) => points.some((pt) => pt.condition === c))
  const name = MEASURES.find(([m]) => m === measure)![2]
  return (
    <section
      aria-label="Trend across sessions"
      className="col-span-16 flex flex-col gap-4 rounded-(--radius-panel) border bg-(--color-surface) p-6 min-[1056px]:col-span-10"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <h2 className="type-title m-0">Across sessions</h2>
        <div role="group" aria-label="Measure" className="flex gap-2">
          {MEASURES.map(([m, label]) => (
            <button
              key={m}
              type="button"
              aria-pressed={measure === m}
              onClick={() => setMeasure(m)}
              className={`type-body h-8 rounded-(--radius-pill) border px-4 ${
                measure === m
                  ? 'border-(--color-accent) bg-(--color-accent-tint) font-medium text-(--color-on-accent-tint)'
                  : 'border-(--color-border-strong) bg-(--color-surface) text-(--color-text)'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      {points.length === 0 ? (
        <p className="type-body m-0 text-(--color-text-muted)">No completed sessions yet.</p>
      ) : (
        <div role="img" aria-label={`${name}: ${points.map((pt) => `${pt.n} ${formatMeasure(measure, pt.value)}`).join(', ')}`}>
          <TrendChart points={points} measure={measure} />
        </div>
      )}
      <div className="type-caption flex flex-wrap gap-6 text-(--color-text-muted)">
        {present.map((c) => (
          <span key={c} className="flex items-center gap-2"><Mark c={c} />{CONDITION_LABEL[c]}</span>
        ))}
        <span>Completed sessions only; aborted ones are listed in the table below.</span>
      </div>
    </section>
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
      <p className="type-caption m-0 text-(--color-text-muted)">Learner profile across sessions: available in a later version.</p>
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
        {data && <p className="type-lead m-0 max-w-[640px] text-(--color-text-secondary)">{lead(data)}</p>}
      </header>
      {data && <Facts p={data} />}

      {isPending && <LoadingNotice title="Loading the participant…" className="col-span-16" />}
      {notFound && (
        <Notice kind="error" title="Participant not found" action={{ label: 'Back to participants', to: '/participants' }} className="col-span-16">
          No participant has this id. It may have been deleted.
        </Notice>
      )}
      {error && !notFound && <OfflineNotice onRetry={() => void refetch()} className="col-span-16" />}

      {data && (
        <>
          <Trend p={data} />
          <Substitutions p={data} />
          <SessionsTable sessions={data.sessions} />
        </>
      )}
    </>
  )
}

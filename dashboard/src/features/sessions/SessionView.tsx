import { useQuery } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router'
import { ApiError, getJson, type Schemas } from '@/api/client'
import { CONDITION_LABEL, type Condition } from '@/components/ConditionChip'
import { Missing } from '@/components/Missing'
import { LoadingNotice, Notice, OfflineNotice } from '@/components/Notice'
import { formatDate, formatDuration, formatPercent, formatTime } from '@/lib/format'
import { Timeline } from './timeline/Timeline'
import { SessionTables } from './trials/SessionTables'

// V1.2 Session View header and summary, artboard *Session View* (light and dark).

type Detail = Schemas['ResearchSessionDetail']
type Adaptations = NonNullable<Detail['adaptations']>

const STATUS_LABEL: Record<Detail['status'], string> = {
  COMPLETED: 'Completed', IN_PROGRESS: 'In progress', ABORTED: 'Aborted', CREATED: 'Created',
}
// design-system.md "Condition chip", the 32 px size of the facts block.
const CONDITION_PILL: Record<Condition, string> = {
  STATIC: 'bg-(--color-border-subtle) text-(--color-text-secondary)',
  BEHAVIOR_ADAPTIVE: 'bg-(--color-accent-tint) text-(--color-on-accent-tint)',
  MULTIMODAL_ADAPTIVE:
    'border border-(--color-condition-multimodal) bg-(--color-condition-multimodal-tint) text-(--color-on-condition-multimodal-tint)',
}

/** "S7_EXPERIMENTAL_RETRIEVAL" → "S7". */
const code = (state: string) => state.slice(0, 2)
const times = (n: number) => `${n} ${n === 1 ? 'time' : 'times'}`

function lead(s: Detail): string {
  const parts = [
    `${CONDITION_LABEL[s.condition]} session, visit ${s.visit_number}${s.kanji_set ? `, kanji set ${s.kanji_set}` : ''}.`,
    s.trial_count === null
      ? 'No trials recorded.'
      : s.first_block && s.last_block
        ? `${s.trial_count} trials from ${code(s.first_block)} to ${code(s.last_block)}.`
        : `${s.trial_count} trials.`,
  ]
  const a = s.adaptations
  if (a)
    parts.push(
      `The system changed the environment ${times(a.environment_changes)} and the assistance ` +
        `${times(a.assistance_changes)}; Unity skipped ${a.skipped_by_unity} of those changes.`,
    )
  return parts.join(' ')
}

function quality(s: Detail): [string, string] {
  if (s.open_error_count > 0)
    return ['bg-(--color-quality-error)', `${s.open_error_count} open projection ${s.open_error_count === 1 ? 'error' : 'errors'}`]
  if (s.projection_status === 'NO_DATA') return ['bg-(--color-outcome-neutral)', 'No data']
  if (s.projection_status === 'NOT_PROJECTED') return ['bg-(--color-outcome-neutral)', 'Not projected']
  return ['bg-(--color-quality-ok)', 'No open projection errors']
}

function Facts({ s }: { s: Detail }) {
  const [dot, label] = quality(s)
  return (
    <aside aria-label="Session facts" className="col-span-16 flex flex-col gap-4 self-end min-[1056px]:col-span-6">
      <dl className="type-body m-0 grid grid-cols-[120px_minmax(0,1fr)] gap-x-4 gap-y-2">
        <dt className="text-(--color-text-muted)">Participant</dt>
        <dd className="type-mono m-0">
          <Link to={`/participants/${s.participant_id}`} className="text-(--color-accent) hover:text-(--color-accent-hover)">
            {s.external_code}
          </Link>
        </dd>
        <dt className="text-(--color-text-muted)">Recorded</dt>
        <dd className="m-0">
          {formatDate(s.created_at)}, {s.started_at ? formatTime(s.started_at) : <Missing reason="The session clock never started" />}
        </dd>
        <dt className="text-(--color-text-muted)">Status</dt>
        <dd className="m-0">{STATUS_LABEL[s.status]}</dd>
        <dt className="text-(--color-text-muted)">Data quality</dt>
        <dd className="m-0 flex items-center gap-2">
          <span aria-hidden="true" className={`size-2 rounded-full ${dot}`} />
          {label}
        </dd>
      </dl>
      <div className="flex flex-wrap gap-2">
        <span className={`type-body inline-flex h-8 items-center rounded-(--radius-pill) px-4 font-medium ${CONDITION_PILL[s.condition]}`}>
          {CONDITION_LABEL[s.condition]}
        </span>
      </div>
    </aside>
  )
}

// design-system.md "Where the time went": S7 in --color-text, the learning blocks darker than the rest.
function stateFill(state: string): string {
  const c = code(state)
  if (c === 'S7') return 'bg-(--color-text)'
  if (c === 'S5' || c === 'S6' || c === 'S8') return 'bg-(--color-condition-static)'
  return 'bg-(--color-outcome-neutral)'
}

function StateStrip({ states: all }: { states: Detail['states'] }) {
  // S9 is where a session ends: no exit there is not a cut.
  const states = all.filter((v) => !(code(v.state) === 'S9' && v.exited_elapsed_ms === null))
  const ms = (v: Detail['states'][number]) => (v.exited_elapsed_ms === null ? null : v.exited_elapsed_ms - v.entered_elapsed_ms)
  const total = states.reduce((sum, v) => sum + (ms(v) ?? 0), 0)
  const label = states.map((v) => `${code(v.state)} ${ms(v) === null ? 'not finished' : formatDuration(ms(v)!)}`).join(', ')
  return (
    <div className="flex flex-col gap-2">
      <div role="img" aria-label={`Duration per Game Flow state: ${label}`} className="flex h-8 gap-0.5">
        {states.map((v) =>
          ms(v) === null ? (
            // Cut in this state: its length is unknown, so it gets a fixed hatched stub.
            <div key={v.entered_elapsed_ms} className="w-4 shrink-0 border border-(--color-border-strong)" style={{ background: 'var(--hatch-outcome-uncertain)' }} />
          ) : (
            <div key={v.entered_elapsed_ms} style={{ flex: ms(v)! }} className={stateFill(v.state)} />
          ),
        )}
      </div>
      <div aria-hidden="true" className="type-caption flex gap-0.5 text-(--color-text-muted)">
        {states.map((v) => {
          const key = code(v.state) === 'S7'
          // Like the artboard, a state too narrow for its label goes unlabelled (the image's name lists them all).
          const wide = key || ms(v) === null || (total > 0 && ms(v)! / total >= 0.04)
          return (
            <span
              key={v.entered_elapsed_ms}
              style={ms(v) === null ? undefined : { flex: ms(v)! }}
              className={`min-w-0 overflow-hidden whitespace-nowrap ${ms(v) === null ? 'w-4 shrink-0' : ''} ${key ? 'font-semibold text-(--color-text)' : ''}`}
            >
              {wide ? code(v.state) : ''}
            </span>
          )
        })}
      </div>
    </div>
  )
}

/** "S7 took 60 % of the session." for the state with the most recorded time. */
function longestState(states: Detail['states']): string | null {
  const total = new Map<string, number>()
  for (const v of states)
    if (v.exited_elapsed_ms !== null) total.set(code(v.state), (total.get(code(v.state)) ?? 0) + v.exited_elapsed_ms - v.entered_elapsed_ms)
  const sum = [...total.values()].reduce((a, b) => a + b, 0)
  if (sum === 0) return null
  const [state, ms] = [...total].reduce((a, b) => (b[1] > a[1] ? b : a))
  return `${state} took ${Math.round((ms / sum) * 100)} % of the session.`
}

function Figure({ label, value, unit, note }: { label: string; value: ReactNode; unit?: string; note: ReactNode }) {
  return (
    <tr className="border-t border-(--color-border-subtle)">
      <th scope="row" className="h-8 text-left font-normal text-(--color-text-secondary)">{label}</th>
      <td className="text-right font-semibold whitespace-nowrap">
        {value}
        {unit && <span className="font-normal text-(--color-text-muted)"> {unit}</span>}
      </td>
      <td className="type-caption pl-4 text-right whitespace-nowrap text-(--color-text-muted)">{note}</td>
    </tr>
  )
}

function TimeSection({ s }: { s: Detail }) {
  const noTrials = 'No trials recorded'
  const away = s.head_away_count === null ? 'Head-away was not recorded in this session' : null
  return (
    <section
      aria-label="Where the time went"
      className="col-span-16 flex flex-col gap-6 rounded-(--radius-panel) border bg-(--color-surface) p-6 min-[1056px]:col-span-10"
    >
      <h2 className="type-title m-0">Where the time went</h2>
      {s.states.length > 0 ? <StateStrip states={s.states} /> : <p className="type-body m-0 text-(--color-text-muted)">No Game Flow states recorded.</p>}
      <div className="grid gap-8 border-t pt-4 min-[720px]:grid-cols-[4fr_6fr]">
        <div className="flex flex-col gap-1">
          <span className="type-caption text-(--color-text-muted)">Accuracy, S5 to S8, tutorial excluded</span>
          <span className="type-figure">
            {s.accuracy !== null ? formatPercent(s.accuracy) : <Missing reason="No answered trials in S5 to S8" />}
          </span>
          {longestState(s.states) && <p className="type-body m-0 text-(--color-text-secondary)">{longestState(s.states)}</p>}
        </div>
        <table className="type-body w-full border-collapse">
          <caption className="type-caption pb-2 text-left text-(--color-text-muted)">Behavior over answered trials</caption>
          <tbody>
            <Figure
              label="Mean response time"
              value={s.mean_rt_ms !== null ? Math.round(s.mean_rt_ms) : <Missing reason="No answered trials" />}
              unit={s.mean_rt_ms !== null ? 'ms' : undefined}
              note="All answered trials"
            />
            <Figure
              label="Response time variability"
              value={s.rt_cv_mean !== null ? s.rt_cv_mean.toFixed(2) : <Missing reason="Not enough answered trials for a window" />}
              unit={s.rt_cv_mean !== null ? 'CV' : undefined}
              note="Window of 3 trials"
            />
            <Figure
              label="Head-away"
              value={s.head_away_count ?? <Missing reason={away!} />}
              unit={s.head_away_count !== null ? 'episodes' : undefined}
              note={s.head_away_ms !== null ? `${(s.head_away_ms / 1000).toFixed(1)} s in total` : <Missing reason={away!} />}
            />
            <Figure
              label="Hints"
              value={s.hint_requests ?? <Missing reason={noTrials} />}
              unit={s.hint_requests !== null ? 'requests' : undefined}
              note={s.proactive_hints !== null ? `${s.proactive_hints} proactive` : <Missing reason={noTrials} />}
            />
          </tbody>
        </table>
      </div>
    </section>
  )
}

function ActionBar({ label, n, of, fill }: { label: string; n: number; of: number; fill: string }) {
  return (
    <div className="grid grid-cols-[160px_minmax(0,1fr)_40px] items-center gap-4">
      <span>{label}</span>
      <div className="h-2 rounded-[1px] bg-(--color-border-subtle)">
        <div className={`h-2 rounded-[1px] ${fill}`} style={{ width: `${of ? (n / of) * 100 : 0}%` }} />
      </div>
      <span className="text-right text-(--color-text-muted)">{n}</span>
    </div>
  )
}

function Outcomes({ a }: { a: Adaptations }) {
  const parts: [string, number, string, React.CSSProperties?][] = [
    ['positive', a.outcome_positive, 'bg-(--color-outcome-positive)'],
    ['neutral', a.outcome_neutral, 'bg-(--color-outcome-neutral)'],
    ['negative', a.outcome_negative, 'bg-(--color-outcome-negative)'],
    ['uncertain', a.outcome_uncertain, 'border border-(--color-border-strong)', { background: 'var(--hatch-outcome-uncertain)' }],
    ['not recorded', a.outcome_not_recorded, 'border border-dashed border-(--color-border-strong)'],
  ]
  return (
    <div className="flex flex-col gap-2">
      <span className="type-caption text-(--color-text-muted)">Outcome of the changes</span>
      <div role="img" aria-label={`Outcomes: ${parts.map(([l, n]) => `${n} ${l}`).join(', ')}`} className="flex h-4 gap-0.5">
        {parts.map(([l, n, cls, style]) => n > 0 && <div key={l} style={{ flex: n, ...style }} className={cls} />)}
      </div>
      <div className="type-caption flex flex-wrap gap-4 text-(--color-text-muted)">
        {parts.map(([l, n]) => (l !== 'not recorded' || n > 0) && <span key={l}>{l[0]!.toUpperCase() + l.slice(1)} {n}</span>)}
      </div>
    </div>
  )
}

function AdaptationsSection({ s }: { s: Detail }) {
  const a = s.adaptations
  const changes = a ? a.environment_changes + a.assistance_changes : 0
  return (
    <section
      aria-label="Adaptations"
      className="col-span-16 flex flex-col gap-4 border-t-2 border-(--color-text) pt-6 min-[1056px]:col-span-6"
    >
      <h2 className="type-title m-0">Adaptations</h2>
      {!a ? (
        <p className="type-body m-0 text-(--color-text-secondary)">
          {s.condition === 'STATIC' ? 'No adaptations in a static session.' : 'No decisions recorded in this session.'}
        </p>
      ) : (
        <>
          <p className="type-body m-0 text-(--color-text-secondary)">
            {a.decisions} decisions in S7. {changes} changed something.
          </p>
          <div className="type-body flex flex-col gap-2">
            <ActionBar label="Change environment" n={a.environment_changes} of={changes} fill="bg-(--color-accent)" />
            <ActionBar label="Change assistance" n={a.assistance_changes} of={changes} fill="bg-(--color-lal-high)" />
            <ActionBar label="Skipped by Unity" n={a.skipped_by_unity} of={changes} fill="bg-(--color-condition-static)" />
          </div>
          {changes > 0 && <Outcomes a={a} />}
        </>
      )}
      <p className="type-caption m-0 text-(--color-text-muted)">S6 calibration profile: available in a later version.</p>
    </section>
  )
}

export function SessionView() {
  const { sessionId } = useParams()
  const { data, error, isPending, refetch } = useQuery({
    queryKey: ['research', 'sessions', sessionId],
    queryFn: () => getJson<Detail>(`/research/sessions/${sessionId}`),
  })
  // The selected trial, shared by the timeline, the Trials table and the inspector.
  const [selected, setSelected] = useState<string | null>(null)
  const notFound = error instanceof ApiError && (error.status === 404 || error.status === 422)

  return (
    <>
      <header className="col-span-16 flex flex-col gap-4 min-[1056px]:col-span-10">
        <Link to="/sessions" className="type-caption text-(--color-accent) no-underline hover:text-(--color-accent-hover)">Sessions</Link>
        <h1 className="type-display m-0">
          Session <span className="font-mono text-[30px] tracking-[-0.6px]">{sessionId?.slice(0, 8)}</span>
        </h1>
        {data && <p className="type-lead m-0 max-w-[640px] text-(--color-text-secondary)">{lead(data)}</p>}
      </header>
      {data && <Facts s={data} />}

      {isPending && <LoadingNotice title="Loading the session…" className="col-span-16" />}
      {notFound && (
        <Notice kind="error" title="Session not found" action={{ label: 'Back to sessions', to: '/sessions' }} className="col-span-16">
          No session has this id. It may have been deleted.
        </Notice>
      )}
      {error && !notFound && <OfflineNotice onRetry={() => void refetch()} className="col-span-16" />}

      {data && (
        <>
          <TimeSection s={data} />
          <AdaptationsSection s={data} />
          <Timeline sessionId={data.session_id} condition={data.condition} selected={selected} onSelect={setSelected} />
          <SessionTables sessionId={data.session_id} condition={data.condition} selected={selected} onSelect={setSelected} />
        </>
      )}
    </>
  )
}

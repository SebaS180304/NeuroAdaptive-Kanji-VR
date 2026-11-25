import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'
import { getJson, type Schemas } from '@/api/client'
import { CONDITION_LABEL, ConditionChip, type Condition } from '@/components/ConditionChip'
import { Missing } from '@/components/Missing'
import { SESSION_STATUS_LABEL, sessionStatusText } from '@/components/SessionStatus'
import { LoadingNotice, OfflineNotice } from '@/components/Notice'
import { formatDate, formatPercent } from '@/lib/format'

// V1.1 Session list, artboard *Session list* (light only; dark is built from the tokens).

type Session = Schemas['ResearchSession']
type Status = Session['status']

const NOT_PROJECTED = 'NOT_PROJECTED_ANY'

// NO_DATA and NOT_PROJECTED both lack projected rows: the counters and the status filter group them.
const projected = (s: Session) => s.projection_status === 'PROJECTED'

function Quality({ s }: { s: Session }) {
  const [dot, label] =
    s.open_error_count > 0
      ? ['bg-(--color-quality-error)', `${s.open_error_count} open ${s.open_error_count === 1 ? 'error' : 'errors'}`]
      : s.projection_status === 'NO_DATA'
        ? ['bg-(--color-outcome-neutral)', 'No data']
        : s.projection_status === 'NOT_PROJECTED'
          ? ['bg-(--color-outcome-neutral)', 'Not projected']
          : ['bg-(--color-quality-ok)', 'No open errors']
  return (
    <span className="inline-flex items-center gap-2 whitespace-nowrap">
      <span aria-hidden="true" className={`size-2 rounded-full ${dot}`} />
      {label}
    </span>
  )
}

function ConditionBar({ sessions }: { sessions: Session[] }) {
  const count = (c: Condition) => sessions.filter((s) => projected(s) && s.condition === c).length
  const [stat, behavior, multimodal] = [count('STATIC'), count('BEHAVIOR_ADAPTIVE'), count('MULTIMODAL_ADAPTIVE')]
  const none = sessions.filter((s) => !projected(s)).length
  return (
    <figure
      aria-label="Sessions by condition"
      className="col-span-16 m-0 flex flex-col gap-2 self-end border-t-2 border-(--color-text) pt-4 min-[1056px]:col-span-7"
    >
      <div
        role="img"
        aria-label={`Sessions: ${stat} static, ${behavior} behavior-adaptive, ${multimodal} multimodal-adaptive, ${none} not projected`}
        className="flex h-4 gap-0.5"
      >
        {stat > 0 && <div style={{ flex: stat }} className="bg-(--color-condition-static)" />}
        {behavior > 0 && <div style={{ flex: behavior }} className="bg-(--color-condition-behavior)" />}
        {multimodal > 0 && <div style={{ flex: multimodal }} className="bg-(--color-condition-multimodal)" />}
        {none > 0 && (
          <div
            style={{
              flex: none,
              background:
                'repeating-linear-gradient(45deg, var(--color-condition-static) 0 1px, var(--color-surface) 1px 5px)',
            }}
            className="border border-(--color-border-strong)"
          />
        )}
      </div>
      <figcaption className="type-caption flex flex-wrap gap-4 text-(--color-text-muted)">
        <span>Static {stat}</span>
        <span>Behavior-adaptive {behavior}</span>
        {multimodal > 0 && <span>Multimodal-adaptive {multimodal}</span>}
        <span>Not projected {none}</span>
        {multimodal === 0 && <span>Multimodal-adaptive starts with the pilot</span>}
      </figcaption>
    </figure>
  )
}

const field = 'type-caption flex flex-col gap-2 text-(--color-text-muted)'
const control =
  'type-body h-10 rounded-(--radius-input) border border-(--color-border-strong) bg-(--color-surface) text-(--color-text)'

const COLUMNS: [string, 'left' | 'right'][] = [
  ['Session', 'left'], ['Participant', 'left'], ['Condition', 'left'], ['Visit', 'right'], ['Recorded', 'left'],
  ['Status', 'left'], ['Trials', 'right'], ['Adaptations', 'right'], ['Accuracy', 'right'], ['Data quality', 'left'],
]

function adaptations(s: Session) {
  if (s.decision_count !== null) return s.decision_count
  if (s.condition === 'STATIC') return <Missing reason="No adaptations in a static session" />
  return <Missing reason={projected(s) ? 'No decisions recorded' : notProjectedReason(s)} />
}

const notProjectedReason = (s: Session) =>
  s.projection_status === 'NO_DATA' ? 'No data recorded' : 'Not projected'

export function SessionList() {
  const { data, error, isPending, refetch } = useQuery({
    queryKey: ['research', 'sessions'],
    queryFn: () => getJson<Session[]>('/research/sessions'),
  })
  const [code, setCode] = useState('')
  const [condition, setCondition] = useState<Condition | ''>('')
  const [status, setStatus] = useState<Status | typeof NOT_PROJECTED | ''>('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')

  // shortcut: filtered in the browser like V1.11 (tens of sessions); use the endpoint's filters if it grows.
  const rows = (data ?? []).filter((s) => {
    const day = formatDate(s.created_at)
    return (
      s.external_code.toLowerCase().includes(code.trim().toLowerCase()) &&
      (!condition || s.condition === condition) &&
      (!status || (status === NOT_PROJECTED ? !projected(s) : s.status === status)) &&
      (!from || day >= from) &&
      (!to || day <= to)
    )
  })
  const participants = new Set(data?.map((s) => s.participant_id)).size

  function clear() {
    setCode('')
    setCondition('')
    setStatus('')
    setFrom('')
    setTo('')
  }

  return (
    <>
      <header className="col-span-16 flex flex-col gap-2 min-[1056px]:col-span-9">
        <h1 className="type-display m-0">Sessions</h1>
        {data && (
          <p className="type-lead m-0 text-(--color-text-secondary)">
            {data.length} {data.length === 1 ? 'session' : 'sessions'} from {participants}{' '}
            {participants === 1 ? 'participant' : 'participants'}. Open one to rebuild what happened, trial by trial.
          </p>
        )}
      </header>
      {data && <ConditionBar sessions={data} />}

      {isPending && <LoadingNotice title="Loading sessions…" className="col-span-16" />}
      {error && <OfflineNotice onRetry={() => void refetch()} className="col-span-16" />}

      {data && (
        <>
          <form aria-label="Filters" className="col-span-16 flex flex-wrap items-end gap-4" onSubmit={(e) => e.preventDefault()}>
            <label className={`${field} flex-[1_1_220px]`}>
              Participant
              <input
                type="search"
                placeholder="External code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className={`${control} px-3`}
              />
            </label>
            <label className={`${field} flex-[1_1_200px]`}>
              Condition
              <select value={condition} onChange={(e) => setCondition(e.target.value as Condition | '')} className={`${control} px-2`}>
                <option value="">All conditions</option>
                {(Object.keys(CONDITION_LABEL) as Condition[]).map((c) => (
                  <option key={c} value={c}>{CONDITION_LABEL[c]}</option>
                ))}
              </select>
            </label>
            <label className={`${field} flex-[1_1_200px]`}>
              Status
              <select value={status} onChange={(e) => setStatus(e.target.value as typeof status)} className={`${control} px-2`}>
                <option value="">All statuses</option>
                {(['COMPLETED', 'IN_PROGRESS', 'ABORTED', 'CREATED'] as const).map((s) => (
                  <option key={s} value={s}>{SESSION_STATUS_LABEL[s]}</option>
                ))}
                <option value={NOT_PROJECTED}>Not projected</option>
              </select>
            </label>
            <fieldset className="m-0 flex flex-[1_1_300px] gap-2 border-0 p-0">
              <legend className="type-caption mb-2 p-0 text-(--color-text-muted)">Recorded between</legend>
              <input type="date" aria-label="Recorded from" value={from} onChange={(e) => setFrom(e.target.value)} className={`${control} min-w-0 flex-1 px-3`} />
              <input type="date" aria-label="Recorded to" value={to} onChange={(e) => setTo(e.target.value)} className={`${control} min-w-0 flex-1 px-3`} />
            </fieldset>
            <button
              type="button"
              onClick={clear}
              className="type-body h-10 rounded-(--radius-pill) border border-(--color-border-strong) bg-(--color-surface) px-5 font-medium text-(--color-text) hover:bg-(--color-border-subtle)"
            >
              Clear filters
            </button>
          </form>

          <section
            aria-label="Sessions table"
            className="col-span-16 overflow-x-auto rounded-(--radius-panel) border bg-(--color-surface)"
          >
            <table className="type-body w-full min-w-[980px] border-collapse">
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
                {rows.map((s) => (
                  <tr
                    key={s.session_id}
                    className={`border-b border-(--color-border-subtle) ${projected(s) ? '' : 'text-(--color-text-muted)'}`}
                  >
                    <th scope="row" className="type-mono h-12 px-4 text-left font-normal">
                      <Link to={`/sessions/${s.session_id}`} className="text-(--color-accent) hover:text-(--color-accent-hover)">
                        {s.session_id.slice(0, 8)}
                      </Link>
                    </th>
                    <td className="type-mono px-4">
                      <Link to={`/participants/${s.participant_id}`} className="text-(--color-accent) hover:text-(--color-accent-hover)">
                        {s.external_code}
                      </Link>
                    </td>
                    <td className="px-4"><ConditionChip c={s.condition} /></td>
                    <td className="px-4 text-right">{s.visit_number}</td>
                    <td className="px-4 whitespace-nowrap">{formatDate(s.created_at)}</td>
                    <td className="px-4 whitespace-nowrap">{sessionStatusText(s.status, s.last_state)}</td>
                    <td className="px-4 text-right">
                      {s.trial_count ?? <Missing reason={projected(s) ? 'No trials recorded' : notProjectedReason(s)} />}
                    </td>
                    <td className="px-4 text-right">{adaptations(s)}</td>
                    <td className="px-4 text-right whitespace-nowrap">
                      {s.accuracy !== null ? (
                        formatPercent(s.accuracy)
                      ) : (
                        <Missing reason={projected(s) ? 'No answered trials' : notProjectedReason(s)} />
                      )}
                    </td>
                    <td className="px-4"><Quality s={s} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {rows.length === 0 && (
              <p className="type-body m-0 px-4 py-6 text-(--color-text-muted)">
                {data.length === 0 ? 'No sessions recorded yet.' : 'No session matches these filters.'}
              </p>
            )}
          </section>
        </>
      )}
    </>
  )
}

import { useQuery } from '@tanstack/react-query'
import { getJson, type Schemas } from '@/api/client'
import { Missing } from '@/components/Missing'
import { LoadingNotice, OfflineNotice } from '@/components/Notice'
import { SESSION_STATUS_LABEL, type SessionStatus } from '@/components/SessionStatus'
import { clockMs, stateCode as code } from '@/lib/format'

// V1.6 Plan and execution tab, artboard *V1.6 Session View, Plan and execution tab*:
// table 1-11, the "Where the session stopped" note 12-16.

type Plan = Schemas['SessionPlan']
type Block = Plan['blocks'][number]
type Status = Block['trials'][number]['status']

const EXPECTED = ['S2', 'S5', 'S6', 'S7', 'S8']
const STATUS_LABEL: Record<Status, string> = { COMPLETED: 'completed', STARTED: 'started, not completed', NEVER_SHOWN: 'planned, never shown' }

// design-system.md V1.6: completed solid, started hatched, never shown outlined.
const SQUARE: Record<Status, { className: string; style?: object }> = {
  COMPLETED: { className: 'bg-(--color-trial-correct)' },
  STARTED: {
    className: 'border border-(--color-trial-correct)',
    style: { background: 'repeating-linear-gradient(45deg, var(--color-trial-correct) 0 2px, var(--color-surface) 2px 4px)' },
  },
  NEVER_SHOWN: { className: 'border border-(--color-distractor)' },
}

function blockNote(c: string, condition: string): string {
  return ({ S2: 'Tutorial', S5: 'Standardized learning', S6: 'Calibration', S8: 'Retrieval' } as Record<string, string>)[c]
    ?? (condition === 'STATIC' ? 'Experimental retrieval' : 'Adaptive')
}

const range = (ids: string[]) => (ids.length === 1 ? ids[0] : `${ids[0]} to ${ids.at(-1)}`)
const list = (codes: string[]) => (codes.length === 1 ? codes[0] : `${codes.slice(0, -1).join(', ')} and ${codes.at(-1)}`)

/** One sentence from the plan: the first cut block, then the blocks never generated. */
function whereItStopped(blocks: Block[]): string {
  if (blocks.length === 0) return 'No trial plan was generated in this session.'
  const cut = blocks.find((b) => b.completed < b.planned)
  const generated = blocks.map((b) => code(b.block_state))
  const after = EXPECTED.slice(EXPECTED.indexOf(generated.at(-1)!) + 1)
  const missing = after.length ? ` No plan was generated for ${list(after)}.` : ''
  if (!cut) return (missing ? 'Every generated block was completed.' : 'Every planned trial was completed, in every block.') + missing
  const ids = (s: Status) => cut.trials.filter((t) => t.status === s).map((t) => t.trial_id)
  const [done, started, never] = [ids('COMPLETED'), ids('STARTED'), ids('NEVER_SHOWN')]
  const c = code(cut.block_state)
  const parts = [done.length ? `${c} stopped after ${done.at(-1)}.` : `${c} stopped before its first completed trial.`]
  if (started.length && never.length)
    parts.push(`${range(started)} started but has no completion, and ${range(never)} were planned and never shown.`)
  else if (started.length) parts.push(`${range(started)} started but has no completion.`)
  else if (never.length) parts.push(`${range(never)} were planned and never shown.`)
  return parts.join(' ') + missing
}

function usePlan(sessionId: string) {
  return useQuery({
    queryKey: ['research', 'sessions', sessionId, 'plan'],
    queryFn: () => getJson<Plan>(`/research/sessions/${sessionId}/plan`),
  })
}

const COLUMNS: [string, 'left' | 'right'][] = [
  ['Block', 'left'], ['Planned trials, in order', 'left'], ['Planned', 'right'], ['Started', 'right'],
  ['Completed', 'right'], ['Seed', 'left'], ['Min lag', 'left'],
]

export function PlanTab({ sessionId, condition }: { sessionId: string; condition: string }) {
  const { data, error, isPending, refetch } = usePlan(sessionId)
  if (isPending) return <LoadingNotice title="Loading the plan…" className="m-6" />
  if (error) return <OfflineNotice onRetry={() => void refetch()} className="m-6" />
  return (
    <>
      <div className="overflow-x-auto">
        <table aria-label="Plan and execution" className="type-body w-full min-w-[900px] border-collapse">
          <thead>
            <tr>
              {COLUMNS.map(([label, align], i) => (
                <th
                  key={label}
                  scope="col"
                  className={`type-caption h-10 border-b px-4 font-medium whitespace-nowrap text-(--color-text-muted) ${align === 'right' ? 'text-right' : 'text-left'} ${i === 0 ? 'pl-6' : ''}`}
                >
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.blocks.map((b) => {
              const c = code(b.block_state)
              return (
                <tr key={b.block_state} className={`border-b border-(--color-border-subtle) ${b.completed < b.planned ? 'bg-(--color-warn-tint)' : ''}`}>
                  <th scope="row" className="h-14 pr-4 pl-6 text-left font-medium whitespace-nowrap">
                    {c}
                    <span className="type-caption block font-normal text-(--color-text-muted)">{blockNote(c, condition)}</span>
                  </th>
                  <td className="px-4">
                    <div role="img" aria-label={`${c}: ${b.completed} of ${b.planned} planned trials completed`} className="flex flex-wrap gap-1">
                      {b.trials.map((t) => (
                        <span
                          key={t.trial_id}
                          data-status={t.status}
                          title={`${t.trial_id}, ${STATUS_LABEL[t.status]}`}
                          className={`size-3.5 rounded-[1px] ${SQUARE[t.status].className}`}
                          style={SQUARE[t.status].style}
                        />
                      ))}
                    </div>
                  </td>
                  <td className="px-4 text-right">{b.planned}</td>
                  <td className="px-4 text-right">{b.started}</td>
                  <td className="px-4 text-right">{b.completed}</td>
                  <td className="type-mono px-4">{b.block_seed ?? <Missing reason="Not recorded" />}</td>
                  <td className="px-4 whitespace-nowrap">
                    {!b.kanji_repeats ? 'No kanji repeats'
                      : b.min_lag_achieved !== null && b.min_lag_requested !== null ? `${b.min_lag_achieved} of ${b.min_lag_requested} requested`
                        : <Missing reason="Not recorded" />}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {data.blocks.length === 0 && <p className="type-body m-0 px-6 py-6 text-(--color-text-muted)">No trial plan was generated in this session.</p>}
      </div>
      <div className="type-caption flex flex-wrap gap-6 px-6 pt-4 pb-6 text-(--color-text-muted)">
        {(['COMPLETED', 'STARTED', 'NEVER_SHOWN'] as const).map((s) => (
          <span key={s} className="flex items-center gap-2">
            <span aria-hidden="true" className={`size-3 rounded-[1px] ${SQUARE[s].className}`} style={SQUARE[s].style} />
            {STATUS_LABEL[s][0]!.toUpperCase() + STATUS_LABEL[s].slice(1)}
          </span>
        ))}
      </div>
    </>
  )
}

export function StopNote({ sessionId, status, kanjiSet }: { sessionId: string; status: SessionStatus; kanjiSet: string | null }) {
  const { data } = usePlan(sessionId)
  return (
    <aside
      aria-label="Where the session stopped"
      className="col-span-16 flex flex-col gap-4 self-start border-t-2 border-(--color-text) pt-6 min-[1056px]:col-span-5"
    >
      <h2 className="type-title m-0">Where the session stopped</h2>
      {data && (
        <>
          <p className="type-body m-0 text-(--color-text-secondary)">{whereItStopped(data.blocks)}</p>
          <dl className="type-body m-0 grid grid-cols-[max-content_minmax(0,1fr)] gap-x-4 gap-y-2">
            <dt className="text-(--color-text-muted)">Last state reached</dt>
            <dd className="m-0">
              {data.last_state ? `${code(data.last_state)}, at ${clockMs(data.last_state_ms!)}` : <Missing reason="No Game Flow state recorded" />}
            </dd>
            <dt className="text-(--color-text-muted)">Session status</dt>
            <dd className="m-0">{SESSION_STATUS_LABEL[status]}</dd>
            <dt className="text-(--color-text-muted)">Kanji set</dt>
            <dd className="m-0">{kanjiSet ?? <Missing reason="Not recorded" />}</dd>
          </dl>
        </>
      )}
      <p className="type-caption m-0 text-(--color-text-muted)">
        Plan and execution are stored apart on purpose: the gap between them is the record of where a session was cut.
      </p>
    </aside>
  )
}

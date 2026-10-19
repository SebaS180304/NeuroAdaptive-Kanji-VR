import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Fragment, useState } from 'react'
import { getJson, type Schemas } from '@/api/client'
import { Missing } from '@/components/Missing'
import { LoadingNotice, OfflineNotice } from '@/components/Notice'
import { EstimatedState } from './EstimatedState'
import { KeyValues } from './KeyValues'
import { OutcomeChip } from './OutcomeChip'

// V1.5 Adaptations tab, artboard *V1.5 Session View, Adaptations tab*: all 16 columns, no inspector.

type Adaptation = Schemas['ResearchAdaptation']

const title = (v: string) => v[0] + v.slice(1).toLowerCase().replace(/_/g, ' ')

function change(a: Adaptation): string {
  if (a.action === 'NO_CHANGE' || !a.dimension || !a.to_level) return 'No change'
  const what = a.dimension === 'ESL' ? 'Environment' : 'Assistance'
  return `${what} ${a.dimension} ${a.from_level ? `${title(a.from_level)} to ` : 'to '}${title(a.to_level)}${a.proactive_cues ? ', proactive cues' : ''}`
}

function inUnity(a: Adaptation) {
  if (a.action === 'NO_CHANGE') return <Missing reason="No change to apply" />
  if (a.unity_result === 'APPLIED') return <>Applied before <span className="whitespace-nowrap">{a.applied_before_trial_id}</span></>
  if (a.unity_result === 'SKIPPED') return `Skipped: ${(a.skip_reason ?? 'no reason recorded').toLowerCase()}`
  return 'No answer from Unity recorded'
}

function cooldown(a: Adaptation) {
  if (a.cooldown_until_trial_id) return a.cooldown_until_trial_id
  if (a.cooldown_until_trial !== null) return `trial ${a.cooldown_until_trial}, not run`
  return <Missing reason="No cooldown" />
}

const COLUMNS: [string, 'left' | 'right'][] = [
  ['After trial', 'left'], ['Estimated state', 'left'], ['Cause', 'left'], ['Confidence', 'right'],
  ['Change', 'left'], ['In Unity', 'left'], ['Cooldown until', 'left'], ['Outcome', 'left'],
]

export function AdaptationsTab({ sessionId, condition, showNoChange }: { sessionId: string; condition: string; showNoChange: boolean }) {
  const [open, setOpen] = useState<Set<string>>(new Set())
  const { data, error, isPending, refetch } = useQuery({
    queryKey: ['research', 'sessions', sessionId, 'adaptations', showNoChange],
    queryFn: () => getJson<Adaptation[]>(`/research/sessions/${sessionId}/adaptations?include_no_change=${showNoChange}`),
    placeholderData: keepPreviousData,
    enabled: condition !== 'STATIC',
  })

  if (condition === 'STATIC')
    return <p className="type-body m-0 px-6 py-6 text-(--color-text-secondary)">Static session: the system makes no decisions.</p>
  if (isPending) return <LoadingNotice title="Loading the decisions…" className="m-6" />
  if (error) return <OfflineNotice onRetry={() => void refetch()} className="m-6" />

  const changes = data.filter((a) => a.action !== 'NO_CHANGE').length
  const toggle = (id: string) => setOpen((o) => { const n = new Set(o); if (n.has(id)) n.delete(id); else n.add(id); return n })

  return (
    <>
      <p className="type-body m-0 px-6 pt-4 text-(--color-text-secondary)">
        {changes} {changes === 1 ? 'decision' : 'decisions'} changed something in S7. Each row is one decision, made right
        after the participant answered that trial.
      </p>
      {data.length === 0 ? (
        <p className="type-body m-0 px-6 py-6 text-(--color-text-muted)">No decisions recorded in this session.</p>
      ) : (
        <div className="overflow-x-auto">
          <table aria-label="Adaptations" className="type-body w-full min-w-[1080px] border-collapse">
            <thead>
              <tr>
                <th scope="col" className="h-10 border-b px-4"><span className="sr-only">Expand</span></th>
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
              {data.map((a) => {
                const isOpen = open.has(a.decision_id)
                return (
                  <Fragment key={a.decision_id}>
                    <tr className={`border-b border-(--color-border-subtle) ${isOpen ? 'bg-(--color-selected-row)' : ''}`}>
                      <td className="h-12 pr-2 pl-4">
                        <button
                          type="button"
                          aria-expanded={isOpen}
                          aria-controls={`decision-${a.decision_id}`}
                          aria-label={`Show indicators for ${a.trial_id}`}
                          onClick={() => toggle(a.decision_id)}
                          className="type-body size-8 rounded-(--radius-pill) border border-(--color-border-strong) bg-(--color-surface) leading-none text-(--color-text)"
                        >
                          {isOpen ? '−' : '+'}
                        </button>
                      </td>
                      <th scope="row" className={`type-mono px-4 text-left whitespace-nowrap ${isOpen ? 'font-medium' : 'font-normal'}`}>{a.trial_id}</th>
                      <td className="px-4"><EstimatedState state={a.learner_state} reason="Not recorded" /></td>
                      <td className="px-4">{a.cause ? title(a.cause) : <Missing reason="No cause recorded" />}</td>
                      <td className="px-4 text-right">{a.confidence.toFixed(2)}</td>
                      <td className="px-4">{change(a)}</td>
                      <td className="px-4">{inUnity(a)}</td>
                      <td className="type-mono px-4 whitespace-nowrap">{cooldown(a)}</td>
                      <td className="px-4">
                        {a.action === 'NO_CHANGE' ? <Missing reason="No change, so no outcome" /> : <OutcomeChip outcome={a.outcome} />}
                      </td>
                    </tr>
                    {isOpen && (
                      <tr className="border-b border-(--color-border) bg-(--color-explain-bg)">
                        <td />
                        <td colSpan={COLUMNS.length} className="px-4 pt-4 pb-6">
                          <section
                            id={`decision-${a.decision_id}`}
                            aria-label={`Decision after ${a.trial_id}`}
                            className="grid gap-8 min-[1056px]:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]"
                          >
                            <div className="flex flex-col gap-2">
                              <h3 className="type-subtitle m-0">
                                {a.action === 'NO_CHANGE' ? 'Why the system made no change' : 'Why the system changed'}
                              </h3>
                              <p className="type-body m-0 text-(--color-text-secondary)">{a.explanation}</p>
                              <span className="type-caption text-(--color-text-muted)">
                                Reason code <span className="font-mono">{a.reason_code}</span>, estimator{' '}
                                <span className="font-mono">{a.estimator_version ?? '—'}</span>, rules{' '}
                                <span className="font-mono">{a.rules_version ?? '—'}</span>
                              </span>
                            </div>
                            <div className="grid grid-cols-2 gap-6">
                              <KeyValues heading="Indicators" values={a.indicators} />
                              <KeyValues heading="Thresholds" values={a.thresholds} />
                            </div>
                          </section>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      <p className="type-caption m-0 px-6 pt-4 pb-6 text-(--color-text-muted)">
        Indicators and thresholds are shown as the backend stored them, key by key. An outcome is "Not recorded" until the
        three cooldown trials have been played.
      </p>
    </>
  )
}

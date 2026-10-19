import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import { getJson, type Schemas } from '@/api/client'
import { Missing } from '@/components/Missing'
import { LoadingNotice, OfflineNotice } from '@/components/Notice'
import { ReservedSlot } from '@/components/reserved/ReservedSlot'
import { formatPercent } from '@/lib/format'
import { clockMs } from '../timeline/lanes'
import { flatten } from './flatten'

// V1.4 Trials tab and inspector, artboard *Session View*: tables 1-11, inspector 12-16.

type Trial = Schemas['ResearchTrial']

const TYPE_LABEL: Record<string, string> = {
  T1_MEANING_TO_KANJI: 'Meaning to kanji',
  T2_KANJI_TO_MEANING: 'Kanji to meaning',
  T3_KANJI_TO_READING: 'Kanji to reading',
}
const ACTION_LABEL: Record<string, string> = {
  NO_CHANGE: 'No change', CHANGE_ENVIRONMENT: 'Change environment', CHANGE_ASSISTANCE: 'Change assistance',
}
const STATE_DOT: Record<string, string> = {
  STABLE: 'bg-(--color-state-stable)', DISENGAGED: 'bg-(--color-state-disengaged)', OVERLOADED: 'bg-(--color-state-overloaded)',
}
const title = (v: string) => v[0] + v.slice(1).toLowerCase().replace(/_/g, ' ')

function answer(t: Trial): ReactNode {
  if (t.completed_elapsed_ms === null) return 'Not completed (session ended)'
  if (t.timed_out) return <span title="Timed out">Not answered</span>
  if (t.is_correct === null) return 'Not answered'
  return t.is_correct ? 'Correct' : 'Incorrect'
}

function EstimatedState({ t, reason }: { t: Trial; reason: string }) {
  if (!t.learner_state) return <Missing reason={reason} />
  return (
    <span className="inline-flex items-center gap-2 whitespace-nowrap">
      <span aria-hidden="true" className={`size-2.5 rounded-full ${STATE_DOT[t.learner_state] ?? 'bg-(--color-text-muted)'}`} />
      {title(t.learner_state)}
    </span>
  )
}

const COLUMNS: [string, 'left' | 'right'][] = [
  ['Trial', 'left'], ['Type', 'left'], ['Kanji', 'left'], ['ESL', 'left'], ['LAL', 'left'], ['RT (ms)', 'right'],
  ['Answer', 'left'], ['Idle (ms)', 'right'], ['Away (ms)', 'right'], ['Hints', 'right'], ['Estimated state', 'left'], ['Action', 'left'],
]
const TABS = ['Trials', 'Adaptations', 'Plan and execution'] as const

type Props = { sessionId: string; condition: string; selected: string | null; onSelect: (trialId: string) => void }

export function SessionTables({ sessionId, condition, selected, onSelect }: Props) {
  const [tab, setTab] = useState<(typeof TABS)[number]>('Trials')
  const [hideTutorial, setHideTutorial] = useState(true)
  const [windowN, setWindowN] = useState(3)
  const tabs = useRef<(HTMLButtonElement | null)[]>([])
  const { data, error, isPending, refetch } = useQuery({
    queryKey: ['research', 'sessions', sessionId, 'trials', windowN],
    queryFn: () => getJson<Trial[]>(`/research/sessions/${sessionId}/trials?window_n=${windowN}`),
    placeholderData: keepPreviousData,
  })
  const noDecision = condition === 'STATIC' ? 'Static session: the system makes no decisions' : 'No decision recorded after this trial'
  const rows = (data ?? []).filter((t) => !hideTutorial || t.is_primary_analysis !== false)
  const current = data?.find((t) => t.trial_id === selected) ?? null

  // WAI-ARIA tabs: arrows move and select, focus follows.
  function onTabKey(e: KeyboardEvent, i: number) {
    const step = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0
    if (!step) return
    const next = (i + step + TABS.length) % TABS.length
    setTab(TABS[next]!)
    tabs.current[next]?.focus()
  }

  return (
    <>
      <section
        aria-label="Session tables"
        className="col-span-16 flex min-w-0 flex-col rounded-(--radius-panel) border bg-(--color-surface) min-[1056px]:col-span-11"
      >
        <div className="type-body flex flex-wrap items-center gap-2 border-b px-6">
          <div role="tablist" aria-label="Session tables" className="flex gap-2">
            {TABS.map((t, i) => (
              <button
                key={t}
                ref={(el) => { tabs.current[i] = el }}
                type="button"
                role="tab"
                id={`tab-${i}`}
                aria-selected={tab === t}
                aria-controls="session-tabpanel"
                tabIndex={tab === t ? 0 : -1}
                onClick={() => setTab(t)}
                onKeyDown={(e) => onTabKey(e, i)}
                className={`h-12 border-b-2 px-2 ${tab === t ? 'border-(--color-accent) font-semibold text-(--color-text)' : 'border-transparent text-(--color-text-muted)'}`}
              >
                {t}
              </button>
            ))}
          </div>
          <div className="flex-1" />
          {tab === 'Trials' && (
            <>
              <label className="flex items-center gap-2 text-(--color-text-secondary)">
                <input type="checkbox" checked={hideTutorial} onChange={(e) => setHideTutorial(e.target.checked)} className="accent-(--color-accent)" />
                Hide tutorial (S2)
              </label>
              <label className="flex items-center gap-2 text-(--color-text-secondary)">
                Window
                <select
                  value={windowN}
                  onChange={(e) => setWindowN(Number(e.target.value))}
                  className="h-8 rounded-(--radius-input) border border-(--color-border-strong) bg-(--color-surface) px-2 text-(--color-text)"
                >
                  {[3, 4, 5].map((n) => <option key={n} value={n}>{n} trials</option>)}
                </select>
              </label>
            </>
          )}
        </div>

        <div role="tabpanel" id="session-tabpanel" aria-labelledby={`tab-${TABS.indexOf(tab)}`} className="min-w-0">
          {tab !== 'Trials' ? (
            <ReservedSlot thing={`${tab} tab`} className="m-6" />
          ) : (
            <>
              {isPending && <LoadingNotice title="Loading the trials…" className="m-6" />}
              {error && <OfflineNotice onRetry={() => void refetch()} className="m-6" />}
              {data && (
                <div className="overflow-x-auto">
                  <table aria-label="Trials" className="type-body w-full min-w-[960px] border-collapse">
                    <thead>
                      <tr>
                        {COLUMNS.map(([label, align]) => (
                          <th
                            key={label}
                            scope="col"
                            className={`type-caption h-10 border-b px-4 font-medium whitespace-nowrap text-(--color-text-muted) ${align === 'right' ? 'text-right' : 'text-left'} ${label === 'Trial' ? 'sticky left-0 z-[1] bg-(--color-surface)' : ''}`}
                          >
                            {label}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((t) => {
                        const on = t.trial_id === selected
                        return (
                          <tr key={t.trial_id} className={`border-b border-(--color-border-subtle) ${on ? 'bg-(--color-selected-row)' : ''}`}>
                            <th
                              scope="row"
                              className={`sticky left-0 z-[1] h-10 px-4 text-left font-normal whitespace-nowrap ${on ? 'bg-(--color-selected-row)' : 'bg-(--color-surface)'}`}
                            >
                              <button
                                type="button"
                                aria-pressed={on}
                                onClick={() => onSelect(t.trial_id)}
                                className={`type-mono text-(--color-accent) hover:text-(--color-accent-hover) ${on ? 'font-medium' : ''}`}
                              >
                                {t.trial_id}
                              </button>
                              {t.is_primary_analysis === false && (
                                <span className="type-caption ml-2 rounded-(--radius-pill) bg-(--color-state-neutral) px-2 text-(--color-text-secondary)">
                                  Tutorial
                                </span>
                              )}
                            </th>
                            <td className="px-4 whitespace-nowrap">{t.trial_type ? TYPE_LABEL[t.trial_type] ?? t.trial_type : <Missing reason="Not recorded" />}</td>
                            <td className="px-4 font-(family-name:--font-kanji) text-xl font-medium">{t.kanji_char ?? <Missing reason="Not recorded" />}</td>
                            <td className="px-4">{t.esl ? title(t.esl) : <Missing reason="Not recorded" />}</td>
                            <td className="px-4">{t.lal ? title(t.lal) : <Missing reason="Not recorded" />}</td>
                            <td className="px-4 text-right">{t.response_time_ms ?? <Missing reason="Not answered" />}</td>
                            <td className="px-4">{answer(t)}</td>
                            <td className="px-4 text-right">{t.idle_ms ?? <Missing reason="Not recorded for this trial" />}</td>
                            <td className="px-4 text-right">{t.head_away_ms ?? <Missing reason="Head-away was not recorded in this session" />}</td>
                            <td className="px-4 text-right whitespace-nowrap">
                              {t.hint_count ?? <Missing reason="Not recorded" />}
                              {t.cue_trigger === 'PROACTIVE' && (
                                <>
                                  <span aria-hidden="true" className="ml-2 inline-block size-2 rounded-full border-2 border-(--color-lal-high) align-middle" />
                                  <span className="sr-only">proactive cue</span>
                                </>
                              )}
                            </td>
                            <td className="px-4"><EstimatedState t={t} reason={noDecision} /></td>
                            <td className="px-4 whitespace-nowrap">
                              {t.decision_action ? ACTION_LABEL[t.decision_action] ?? t.decision_action : <Missing reason={noDecision} />}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                  {rows.length === 0 && <p className="type-body m-0 px-6 py-6 text-(--color-text-muted)">No trials recorded in this session.</p>}
                </div>
              )}
            </>
          )}
        </div>
      </section>
      <Inspector t={current} windowN={windowN} noDecision={noDecision} />
    </>
  )
}

function Group({ title: heading, items }: { title: string; items: Record<string, ReactNode> }) {
  return (
    <div className="flex flex-col gap-2">
      <h3 className="type-subtitle m-0">{heading}</h3>
      <dl className="type-body m-0 grid grid-cols-[max-content_minmax(0,1fr)] gap-x-4 gap-y-1">
        {Object.entries(items).map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="text-(--color-text-muted)">{k}</dt>
            <dd className="m-0 text-right">{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

function KeyValues({ heading, values }: { heading: string; values: Record<string, unknown> | null }) {
  return (
    <div className="flex flex-col gap-2">
      <h4 className="type-caption m-0 font-medium text-(--color-text-secondary)">{heading}</h4>
      {values ? (
        <dl className="type-body m-0 grid grid-cols-[fit-content(60%)_minmax(0,1fr)] gap-x-4 gap-y-1">
          {flatten(values).map(([k, v, block]) => (
            <div key={k} className="contents">
              <dt className={`type-mono text-(--color-text-muted) ${block ? 'col-span-2' : ''}`}>
                {k.split('.').map((part, i) => <span key={i}>{i > 0 && <>.<wbr /></>}{part}</span>)}
              </dt>
              <dd className={`type-mono m-0 break-all ${block ? 'col-span-2 text-left' : 'text-right'}`}>{v}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <Missing reason="Not recorded for this decision" />
      )}
    </div>
  )
}

function Inspector({ t, windowN, noDecision }: { t: Trial | null; windowN: number; noDecision: string }) {
  const [details, setDetails] = useState(false)
  const notRecorded = <Missing reason="Not recorded for this trial" />
  return (
    <aside
      aria-label="Selected trial"
      className="col-span-16 flex min-w-0 flex-col gap-6 self-start rounded-(--radius-input) bg-(--color-surface-raised) p-6 shadow-(--shadow-raised) min-[1056px]:col-span-5"
    >
      {!t ? (
        <p className="type-body m-0 text-(--color-text-muted)">Select a trial in the table or the timeline to see its details.</p>
      ) : (
        <>
          <div className="flex flex-col gap-1">
            <h2 className="type-title m-0">Trial <span className="font-mono text-lg">{t.trial_id}</span></h2>
            <span className="type-mono text-(--color-text-muted)">
              {t.started_elapsed_ms !== null ? `started at ${clockMs(t.started_elapsed_ms)}` : 'start not recorded'}
            </span>
          </div>
          <Group title="Response" items={{
            'Kanji and type': <>{t.kanji_char ? <span className="font-(family-name:--font-kanji) font-medium">{t.kanji_char}</span> : notRecorded}{t.trial_type && `, ${TYPE_LABEL[t.trial_type] ?? t.trial_type}`}</>,
            'Answer': answer(t),
            'Response time': t.response_time_ms !== null ? `${t.response_time_ms} ms` : <Missing reason="Not answered" />,
          }} />
          <Group title="Environment" items={{
            'ESL profile': t.esl ? `${title(t.esl)}${t.env_profile ? `, ${t.env_profile}` : ''}` : notRecorded,
            'Props and movers': t.prop_count !== null && t.mover_count !== null ? `${t.prop_count} and ${t.mover_count}` : notRecorded,
            'Peripheral events': t.peripheral_event_count ?? <Missing reason="Peripheral events were not recorded in this session" />,
          }} />
          <Group title="Behavior" items={{
            'Idle': t.idle_ms !== null ? `${t.idle_ms} ms` : notRecorded,
            'Head-away': t.head_away_ms !== null ? `${t.head_away_ms} ms` : <Missing reason="Head-away was not recorded in this session" />,
            'Distractor dwell': t.distractor_dwell_ms !== null ? `${t.distractor_dwell_ms} ms` : <Missing reason="Distractors were not recorded in this session" />,
            [`Window accuracy (${windowN} trials)`]: t.window_accuracy !== null ? formatPercent(t.window_accuracy) : <Missing reason="No answered trials in the window" />,
          }} />
          {t.decision_action ? (
            <div
              className={`flex flex-col gap-2 rounded-(--radius-panel) p-4 ${t.decision_action === 'NO_CHANGE'
                ? 'border border-(--color-border) bg-(--color-surface-raised)' : 'bg-(--color-explain-bg)'}`}
            >
              <h3 className="type-subtitle m-0">{t.decision_action === 'NO_CHANGE' ? 'Why the system made no change' : 'Why the system changed'}</h3>
              <p className="type-body m-0 text-(--color-text-secondary)">{t.explanation}</p>
              <dl className="type-body m-0 grid grid-cols-[max-content_minmax(0,1fr)] gap-x-4 gap-y-1">
                <dt className="text-(--color-text-muted)">Estimated state</dt>
                <dd className="m-0 text-right">
                  {t.learner_state ? title(t.learner_state) : '—'}
                  {t.decision_confidence !== null && `, confidence ${t.decision_confidence.toFixed(2)}`}
                </dd>
                <dt className="text-(--color-text-muted)">Change</dt>
                <dd className="m-0 text-right">
                  {t.dimension && t.to_level ? `${t.dimension} ${t.from_level ? `${title(t.from_level)} to ` : 'to '}${title(t.to_level)}` : 'None'}
                </dd>
                {t.decision_action !== 'NO_CHANGE' && (
                  <>
                    <dt className="text-(--color-text-muted)">In Unity</dt>
                    <dd className="m-0 text-right">
                      {t.unity_result === 'APPLIED' ? <>Applied before <span className="whitespace-nowrap">{t.applied_before_trial_id}</span></>
                        : t.unity_result === 'SKIPPED' ? `Skipped: ${t.skip_reason}` : 'No answer from Unity recorded'}
                    </dd>
                    <dt className="text-(--color-text-muted)">Cooldown until</dt>
                    <dd className="type-mono m-0 text-right">
                      {t.cooldown_until_trial_id ?? (t.cooldown_until_trial !== null ? `trial ${t.cooldown_until_trial}, not run` : '—')}
                    </dd>
                    <dt className="text-(--color-text-muted)">Outcome</dt>
                    <dd className="m-0 text-right">{t.outcome ? title(t.outcome) : 'Not recorded'}</dd>
                  </>
                )}
              </dl>
            </div>
          ) : (
            <p className="type-body m-0 text-(--color-text-muted)">{noDecision}.</p>
          )}
          {t.decision_action && (
            <>
              <button
                type="button"
                aria-expanded={details}
                onClick={() => setDetails(!details)}
                className="type-body h-10 rounded-(--radius-pill) border border-(--color-border-strong) bg-(--color-surface) text-(--color-text)"
              >
                {details ? 'Hide indicators and thresholds' : 'Show indicators and thresholds'}
              </button>
              {details && (
                <div className="flex flex-col gap-4">
                  <p className="type-caption m-0 text-(--color-text-muted)">
                    {t.reason_code}, estimator {t.estimator_version ?? '—'}, rules {t.rules_version ?? '—'}
                  </p>
                  <KeyValues heading="Indicators" values={t.indicators as Record<string, unknown> | null} />
                  <KeyValues heading="Thresholds" values={t.thresholds as Record<string, unknown> | null} />
                </div>
              )}
            </>
          )}
        </>
      )}
    </aside>
  )
}

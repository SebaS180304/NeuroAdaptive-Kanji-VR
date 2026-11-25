import { useQuery } from '@tanstack/react-query'
import { Info } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { getJson, type Schemas } from '@/api/client'
import { CONDITION_LABEL, type Condition } from '@/components/ConditionChip'
import { LoadingNotice, OfflineNotice } from '@/components/Notice'
import { formatDate } from '@/lib/format'
import { OutcomeChip } from '@/features/sessions/trials/OutcomeChip'
import {
  acrossSentence, adaptationsOrigin, badges, calibrationOrigin, calibrationRows, EMPTY_SCOPE, groupSentence,
  noChanges, practiceSentence, scopeLine, staticOnly, tooFew, unrecorded, UNRECORDED_TIP,
} from './profileText'
import { formatMeasure, SHAPE, TrendChart, type Measure, type TrendPoint } from './TrendChart'

// F-PROFILE: the Learner Profile at the top of V1.8. Form from design-system.md "V1.8 Learner
// Profile (F-PROFILE)", including the canvas-only points of D-F6-11; copy from
// Contenido_UI_F-PROFILE.md (D-F6-6). Read only: the backend computes it when a session
// completes or aborts. Aborted sessions are never mentioned (D-F6-5).

type Detail = Schemas['ResearchParticipantDetail']
type Data = Schemas['LearnerProfileData']
type Group = Schemas['ProfileAdaptationGroup']
type Point = Schemas['ProfileTrendPoint']

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`
const decisions = (n: number) => plural(n, 'decision', 'decisions')
// shortcut: the session's Adaptations tab unfiltered; Task 11b adds ?group=<key>.
const adaptationsOf = (sessionId: string) => `/sessions/${sessionId}?tab=adaptations`

/** "Session [#]" uses the numbers of "Sessions in order", which still lists aborted sessions. */
function numbering(p: Detail) {
  return new Map(p.sessions.map((s, i) => [s.session_id, { n: i + 1, date: formatDate(s.created_at) }]))
}

const link = 'type-body whitespace-nowrap font-medium text-(--color-accent) underline hover:text-(--color-accent-hover)'
const rule = 'border-t border-(--color-border-subtle)'

/** One session: a plain link. Several: a disclosure whose list spans the row (below the badges). */
function useDecisionLinks(perSession: [string, number][], order: ReturnType<typeof numbering>) {
  const [open, setOpen] = useState(false)
  const total = perSession.reduce((n, [, k]) => n + k, 0)
  if (perSession.length === 1)
    return { trigger: <Link to={adaptationsOf(perSession[0]![0])} className={`${link} self-start`}>See {decisions(total)}</Link>, list: null }
  const lines = [...perSession].sort(([a], [b]) => (order.get(b)?.n ?? 0) - (order.get(a)?.n ?? 0))
  return {
    trigger: (
      <button type="button" aria-expanded={open} onClick={() => setOpen(!open)}
        className={`${link} inline-flex cursor-pointer items-center gap-1.5 self-start border-0 bg-transparent p-0`}>
        See {decisions(total)} in {perSession.length} sessions
        <svg aria-hidden="true" width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.6">
          <path d={open ? 'M3 7.5l3-3 3 3' : 'M3 4.5l3 3 3-3'} />
        </svg>
      </button>
    ),
    list: open && (
      <ul aria-label="Decisions by session"
        className="type-body col-span-2 m-0 flex list-none flex-col gap-1 rounded-(--radius-panel) bg-(--color-explain-bg) px-3 py-2">
        {lines.map(([sid, k]) => (
          <li key={sid} className="flex justify-between gap-4">
            <span>Session {order.get(sid)?.n} <span className="text-(--color-text-muted)">({order.get(sid)?.date})</span></span>
            <Link to={adaptationsOf(sid)} className={link}>{decisions(k)}</Link>
          </li>
        ))}
      </ul>
    ),
  }
}

function UsualPerformance({ code, data }: { code: string; data: Data }) {
  const rows = calibrationRows(data.calibrations)
  const many = data.calibrations.length > 1
  const head = 'type-caption h-8 border-b p-0 font-medium whitespace-nowrap text-(--color-text-muted)'
  const value = 'py-[5px] pl-4 text-right whitespace-nowrap'
  const rt = rows.filter((r) => r.rt)
  const row = (r: (typeof rows)[number], indent = false) => (
    <tr key={r.label} className="border-b border-(--color-border-subtle)">
      <th scope="row" className={`py-[5px] text-left font-normal ${indent ? 'pl-4' : ''}`}>{r.label}</th>
      <td className={value}>
        {r.latest}
        {r.fallback && (
          <span title={r.fallbackTip} aria-label={r.fallbackTip} className="ml-1 inline-flex align-[-2px] text-(--color-text-muted)">
            <Info aria-hidden="true" size={14} />
          </span>
        )}
      </td>
      <td className={`${value} text-(--color-text-secondary)`}>{r.range}</td>
    </tr>
  )
  return (
    <section aria-label="Usual performance" className="col-span-16 flex flex-col gap-3 min-[1056px]:col-span-6">
      <h3 className="type-subtitle m-0">Usual performance</h3>
      <p className="type-body m-0 text-(--color-text-secondary)">{practiceSentence(code, data.calibrations[data.calibrations.length - 1]!)}</p>
      <table className="type-body w-full border-collapse">
        <thead>
          <tr>
            <th scope="col" className={`${head} text-left`}><span className="sr-only">Measure</span></th>
            <th scope="col" className={`${head} pl-4 text-right`}>Latest session</th>
            <th scope="col" className={`${head} pl-4 text-right`}>{many ? `Across ${data.calibrations.length} sessions` : 'One session so far.'}</th>
          </tr>
        </thead>
        <tbody>
          {rt.length > 0 && (
            <tr><th scope="rowgroup" colSpan={3} className="type-body-strong pt-2 pb-0 text-left">Typical response time</th></tr>
          )}
          {rt.map((r) => row(r, true))}
          {rows.filter((r) => !r.rt).map((r) => row(r))}
        </tbody>
      </table>
      <p className="type-caption m-0 text-(--color-text-muted)">{calibrationOrigin(data.trend)}</p>
    </section>
  )
}

function GroupRow({ g, order }: { g: Group; order: ReturnType<typeof numbering> }) {
  const perSession = Object.entries(g.decisions).map(([sid, ids]) => [sid, ids.length] as [string, number])
  const { trigger, list } = useDecisionLinks(perSession, order)
  return (
    <li className={`grid grid-cols-[minmax(0,1fr)_auto] gap-x-6 gap-y-2 py-3 ${rule}`}>
      <p className="type-body m-0">{groupSentence(g)}</p>
      {trigger}
      <div className="col-span-2 flex flex-wrap items-center gap-2">
        {tooFew(g) && (
          <span className="type-caption inline-flex h-6 items-center rounded-(--radius-pill) bg-(--color-state-neutral) px-2.5 font-semibold text-(--color-text-secondary)">
            Too few to tell
          </span>
        )}
        {/* "Not recorded": OutcomeChip's dashed chip, the form validated by D-F6-96; always last (badges()). */}
        {badges(g).map((b) => (
          <OutcomeChip key={b.text} outcome={b.outcome === 'NOT_RECORDED' ? null : b.outcome} label={b.text} title={b.title} />
        ))}
      </div>
      {list}
    </li>
  )
}

function NoChanges({ recorded, order }: { recorded: Point[]; order: ReturnType<typeof numbering> }) {
  const checked = recorded.reduce((n, t) => n + (t.no_change ?? 0), 0)
  const { trigger, list } = useDecisionLinks(recorded.map((t) => [t.session_id, t.no_change ?? 0]), order)
  return (
    <div className={`flex flex-col gap-2 pt-3 ${rule}`}>
      <p className="type-body m-0">{noChanges(recorded.length, checked)}</p>
      {trigger}
      {list}
    </div>
  )
}

const SHOWN = 3

function Adaptations({ data, order }: { data: Data; order: ReturnType<typeof numbering> }) {
  const [all, setAll] = useState(false)
  const adaptive = data.trend.filter((t) => t.condition !== 'STATIC')
  const recorded = adaptive.filter((t) => t.decisions_recorded)
  const older = adaptive.length - recorded.length
  const groups = all ? data.adaptations : data.adaptations.slice(0, SHOWN)
  const more = data.adaptations.length - SHOWN
  let body
  if (adaptive.length === 0) body = <p className={`type-body m-0 pt-3 ${rule}`}>{staticOnly(data.trend.length)}</p>
  else if (data.adaptations.length === 0 && recorded.length > 0) body = <NoChanges recorded={recorded} order={order} />
  else
    body = (
      <>
        <ol className="m-0 list-none p-0">{groups.map((g) => <GroupRow key={g.key} g={g} order={order} />)}</ol>
        {more > 0 && !all && (
          <button type="button" onClick={() => setAll(true)}
            className="type-body h-8 cursor-pointer self-start rounded-(--radius-pill) border border-(--color-accent) bg-transparent px-4 font-medium text-(--color-on-accent-tint)">
            Show {plural(more, 'more group', 'more groups')}
          </button>
        )}
      </>
    )
  return (
    <section aria-label="What followed each adaptation"
      className="col-span-16 flex flex-col gap-3 self-start rounded-(--radius-panel) border bg-(--color-surface) px-6 py-5 min-[1056px]:col-span-10">
      <h3 className="type-subtitle m-0">What followed each adaptation</h3>
      {body}
      {recorded.length > 0 && <p className="type-caption m-0 text-(--color-text-muted)">{adaptationsOrigin(recorded.length, recorded.filter((t) => t.rules_version === 'rules-v2').length)}</p>}
      {older > 0 && <p title={UNRECORDED_TIP} className="type-caption m-0 text-(--color-text-muted)">{unrecorded(older)}</p>}
    </section>
  )
}

const MEASURES: [Measure, string, string][] = [
  ['correct', 'Correct in S7', 'Correct in S7 per completed session'],
  ['rt', 'Response time', 'Mean response time in S7 per completed session'],
]

// Legend marks drawn as small SVGs, in the chart's shapes.
function Mark({ c }: { c: Condition }) {
  const fill = `var(${SHAPE[c].token})`
  return (
    <svg aria-hidden="true" width="10" height="10" viewBox="0 0 12 12">
      {c === 'STATIC' && <rect x="1" y="1" width="10" height="10" fill={fill} />}
      {c === 'BEHAVIOR_ADAPTIVE' && <circle cx="6" cy="6" r="5" fill={fill} />}
      {c === 'MULTIMODAL_ADAPTIVE' && <polygon points="6,0.5 11.5,11 0.5,11" fill={fill} />}
    </svg>
  )
}

function Across({ trend, order, p }: { trend: Point[]; order: ReturnType<typeof numbering>; p: Detail }) {
  const [measure, setMeasure] = useState<Measure>('correct')
  const visit = new Map(p.sessions.map((s) => [s.session_id, s.visit_number]))
  const points: TrendPoint[] = trend.flatMap((t) => {
    const value = measure === 'correct' ? t.s7_correct : t.s7_mean_rt_ms
    const at = order.get(t.session_id)
    return value === null || !at ? [] : [{ n: at.n, condition: t.condition as Condition, value, date: at.date,
      visit: visit.get(t.session_id) ?? 1, of: t.s7_trials, set: t.kanji_set }]
  })
  const present = (Object.keys(SHAPE) as Condition[]).filter((c) => points.some((pt) => pt.condition === c))
  const name = MEASURES.find(([m]) => m === measure)![2]
  return (
    <section aria-label="Across sessions" className="col-span-16 flex flex-col gap-2 border-t pt-4">
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <div className="flex max-w-[760px] flex-col gap-1">
          <h3 className="type-subtitle m-0">Across sessions</h3>
          <p className="type-body m-0 text-(--color-text-secondary)">{acrossSentence(trend)}</p>
        </div>
        {trend.length > 1 && (
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
        )}
      </div>
      {trend.length > 1 && (
        <>
          <div role="img" aria-label={`${name}: ${points.map((pt) => `${pt.n} ${formatMeasure(measure, pt.value, pt.of)}`).join(', ')}`}>
            <TrendChart points={points} measure={measure} />
          </div>
          <div className="type-caption flex flex-wrap gap-6 text-(--color-text-muted)">
            {present.map((c) => (
              <span key={c} className="flex items-center gap-2"><Mark c={c} />{CONDITION_LABEL[c]}</span>
            ))}
            <span>Completed sessions only, numbered as in the table.</span>
          </div>
        </>
      )}
    </section>
  )
}

export function LearnerProfile({ p }: { p: Detail }) {
  const { data, error, isPending, refetch } = useQuery({
    queryKey: ['research', 'participants', p.id, 'profile'],
    queryFn: () => getJson<Schemas['LearnerProfile']>(`/research/participants/${p.id}/profile`),
  })
  const profile = data?.profile && data.profile.trend.length > 0 ? data.profile : null
  const order = numbering(p)
  return (
    <section aria-label="Learner Profile" className="col-span-16 grid grid-cols-16 gap-x-8 gap-y-6 border-t-2 border-(--color-text) pt-4">
      <div className="col-span-16 flex flex-col gap-1 min-[1056px]:col-span-13">
        <h2 className="type-title m-0">Learner Profile</h2>
        {data && <p className="type-body m-0 text-(--color-text-secondary)">{profile ? scopeLine(profile.trend.length) : EMPTY_SCOPE}</p>}
      </div>
      {data && (
        <p className="type-caption col-span-16 m-0 text-(--color-text-muted) min-[1056px]:col-span-3 min-[1056px]:text-right">
          {profile && data.computed_at ? `Updated ${formatDate(data.computed_at)}, profile ${data.profile_version}` : 'No profile computed'}
        </p>
      )}
      {isPending && <LoadingNotice title="Loading the profile…" className="col-span-16" />}
      {error && <OfflineNotice onRetry={() => void refetch()} className="col-span-16" />}
      {data && !profile && (
        <div className="col-span-16 flex flex-col gap-2 rounded-(--radius-panel) border bg-(--color-surface) p-6 min-[1056px]:col-span-10">
          <h3 className="type-subtitle m-0">No profile yet.</h3>
          <p className="type-body m-0 text-(--color-text-secondary)">
            {p.external_code} has no completed session yet. The profile appears after the first one.
            {p.pretest_completed_at && ` Pre-test done on ${formatDate(p.pretest_completed_at)}.`}
          </p>
        </div>
      )}
      {profile && (
        <>
          <UsualPerformance code={p.external_code} data={profile} />
          <Adaptations data={profile} order={order} />
          <Across trend={profile.trend} order={order} p={p} />
        </>
      )}
    </section>
  )
}

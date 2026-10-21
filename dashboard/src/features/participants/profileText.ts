import type { Schemas } from '@/api/client'

// F-PROFILE copy, Contenido_UI_F-PROFILE.md (UI/UX chat, 21 Oct). Every sentence here describes a
// window of trials, never the person; results say "after", never "helped"; counts, never percentages.
// Aborted sessions are never mentioned (Sebas, 21 Oct): the profile only holds completed ones.

type Cal = Schemas['ProfileCalibration']
type Group = Schemas['ProfileAdaptationGroup']
type Point = Schemas['ProfileTrendPoint']

const times = (n: number) => `${n} ${n === 1 ? 'time' : 'times'}`
const sessions = (n: number) => `${n} completed ${n === 1 ? 'session' : 'sessions'}`
// Rounded on whole tenths: (1950 / 1000).toFixed(1) would give 1.9.
const sec = (ms: number) => (Math.round(ms / 100) / 10).toFixed(1)

export const scopeLine = (n: number) =>
  `A summary of ${sessions(n)}. It describes what happened in windows of trials, not the person, and it doesn't change how the next session starts.`

export function practiceSentence(code: string, c: Cal): string {
  const rt = c.rt_ref_global !== null ? `, taking about ${sec(c.rt_ref_global)} s per answer` : ''
  const away = c.away_ref_ms === 0
    ? ', and stayed on the task area throughout.'
    : `, and spent about ${sec(c.away_ref_ms)} s per trial looking away from the task.`
  return `In practice (S6) of the latest session, ${code} answered ${c.correct} of ${c.n} correctly${rt}${away}`
}

// The short names V1.4 uses, with the type in brackets (design-system.md, F-PROFILE).
export const TYPES: [string, string][] = [
  ['T1_MEANING_TO_KANJI', 'Meaning to kanji (T1)'],
  ['T2_KANJI_TO_MEANING', 'Kanji to meaning (T2)'],
  ['T3_KANJI_TO_READING', 'Kanji to reading (T3)'],
]

export type CalRow = { label: string; latest: string; range: string | null; fallback?: boolean; type?: string; rt?: boolean }

const span = (values: number[], fmt: (v: number) => string, unit = '') => {
  const lo = Math.min(...values), hi = Math.max(...values)
  return `${fmt(lo) === fmt(hi) ? fmt(lo) : `${fmt(lo)}–${fmt(hi)}`}${unit}`
}

/** Latest session and the range over all; the range is null with one session ("One session so far."). */
export function calibrationRows(cals: Cal[]): CalRow[] {
  const last = cals[cals.length - 1]!
  const many = cals.length > 1
  const rows: CalRow[] = TYPES.filter(([t]) => last.rt_ref[t] !== undefined).map(([t, label]) => {
    const values = cals.map((c) => c.rt_ref[t]).filter((v): v is number => v !== undefined)
    return { label, type: t, rt: true, latest: `${sec(last.rt_ref[t]!)} s`, fallback: last.fallback_types.includes(t),
             range: many ? span(values, sec, ' s') : null }
  })
  const sameN = cals.every((c) => c.n === last.n)
  rows.push({ label: 'Correct in practice', latest: `${last.correct} of ${last.n}`,
              range: many ? span(cals.map((c) => c.correct), String, sameN ? ` of ${last.n}` : ' correct') : null })
  rows.push({ label: 'Looking away from the task', latest: `${sec(last.away_ref_ms)} s per trial`,
              range: many ? span(cals.map((c) => c.away_ref_ms), sec, ' s') : null })
  rows.push({ label: 'Time on room objects', latest: `${sec(last.env_dwell_ref_ms)} s per trial`,
              range: many ? span(cals.map((c) => c.env_dwell_ref_ms), sec, ' s') : null })
  return rows
}

export function calibrationOrigin(points: Point[]): string {
  const stat = points.filter((p) => p.condition === 'STATIC').length
  return `From practice (S6) of ${sessions(points.length)}: ${stat} STATIC, ${points.length - stat} adaptive.`
}

// The estimated state and cause of the window (§3.2). IMPULSIVE never appears on screen.
function clause(g: Group): string {
  if (g.learner_state === 'STABLE') return 'After two steady windows'
  if (g.learner_state === 'OVERLOADED') return 'When answers got slower and less accurate than in practice (estimated overload)'
  if (g.cause === 'ENVIRONMENT') return 'When attention went to the room, on objects or peripheral events (estimated disengagement, room)'
  if (g.cause === 'AWAY') return 'When the view left the task area (estimated disengagement, looking away)'
  if (g.cause === 'IMPULSIVE') return 'When answers came quickly and were wrong (estimated disengagement, quick errors)'
  return 'When the window looked different from practice (estimated disengagement)'
}

/** A return to MEDIUM after steady windows, as opposed to a rescue (§3.4). */
export const isReturn = (g: Group) => g.learner_state === 'STABLE'

function action(g: Group): string {
  const what = g.dimension === 'ESL' ? 'the environment level (ESL)' : 'assistance (LAL)'
  if (isReturn(g)) return `${what} was returned to MEDIUM`
  return `${what} was ${g.direction === 'UP' ? 'raised' : 'lowered'}`
}

const CLASSIFIED = ['POSITIVE', 'NEUTRAL', 'NEGATIVE'] as const
const LABEL: Record<(typeof CLASSIFIED)[number], [string, string]> = {   // [rescue, return to MEDIUM]
  POSITIVE: ['Recovered after', 'Held after'],
  NEUTRAL: ['No clear change after', 'Held, with a dip'],
  NEGATIVE: ['Worse after', 'Slipped after'],
}
const UNCERTAIN_LABEL: Record<string, string> = { NOT_APPLIED: "Can't tell: not applied", INCOMPLETE: "Can't tell: S7 ended first" }

const classified = (g: Group) => CLASSIFIED.reduce((n, o) => n + (g.outcomes[o] ?? 0), 0)

/** Fewer than 3 classified outcomes (UNCERTAIN and not recorded don't count). */
export const tooFew = (g: Group) => classified(g) < 3

export function groupSentence(g: Group): string {
  const base = `${clause(g)}, ${action(g)} ${times(g.count)}`
  if (tooFew(g)) return `${base}.`
  const top = [...CLASSIFIED].sort((a, b) => (g.outcomes[b] ?? 0) - (g.outcomes[a] ?? 0))[0]!
  const label = LABEL[top][isReturn(g) ? 1 : 0]
  return `${base}; ${label[0]!.toLowerCase()}${label.slice(1)} ${g.outcomes[top]} of ${classified(g)}.`
}

export type Badge = { outcome: string; text: string; title: string }

/** One badge per result, in a fixed order (never sorted by result, D-F6-1). */
export function badges(g: Group): Badge[] {
  const reasons = (o: string) => Object.entries(g.outcome_reasons[o] ?? {})
  const title = (o: string, rs: [string, number][]) => [o, ...rs.map(([r, n]) => `${r} ${n}`)].join(' · ')
  const out: Badge[] = []
  for (const o of CLASSIFIED) {
    const n = g.outcomes[o]
    if (n) out.push({ outcome: o, text: `${LABEL[o][isReturn(g) ? 1 : 0]}: ${n}`, title: title(o, reasons(o)) })
  }
  for (const [r, n] of reasons('UNCERTAIN').sort(([a], [b]) => (a === 'NOT_APPLIED' ? -1 : b === 'NOT_APPLIED' ? 1 : 0)))
    out.push({ outcome: 'UNCERTAIN', text: `${UNCERTAIN_LABEL[r] ?? "Can't tell"}: ${n}`, title: `UNCERTAIN · ${r} ${n}` })
  if (g.outcomes.NOT_RECORDED)
    out.push({ outcome: 'NOT_RECORDED', text: `Not recorded: ${g.outcomes.NOT_RECORDED}`, title: 'No outcome was recorded for these changes' })
  return out
}

const s = (n: number) => (n === 1 ? '' : 's')

export const adaptationsOrigin = (adaptive: number) =>
  `From ${adaptive} completed adaptive session${s(adaptive)}. STATIC sessions never adapt and aren't counted here.`

// One session is not in the copy; "the only session" keeps the sentence grammatical.
export const staticOnly = (n: number) => n === 1
  ? 'No adaptations: the only session so far was STATIC, and STATIC never adapts. Usual performance and the trend come from this session.'
  : `No adaptations: all ${n} sessions so far were STATIC, and STATIC never adapts. Usual performance and the trend come from these sessions.`

export const noChanges = (adaptive: number, checked: number) =>
  `No adaptations in ${adaptive} adaptive session${s(adaptive)}. The system checked ${checked} times and kept the levels each time.`

export const unrecorded = (m: number) => `${m} older session${s(m)} ${m === 1 ? 'has' : 'have'} no adaptation record.`
export const UNRECORDED_TIP = "Adaptations weren't recorded before 13 Oct. This session may have adapted; there's no way to tell."

const rt = (p: Point) => (p.s7_mean_rt_ms === null ? '—' : sec(p.s7_mean_rt_ms))

export function acrossSentence(points: Point[]): string {
  const first = points[0]!, last = points[points.length - 1]!
  const sets = new Set(points.map((p) => p.kanji_set)).size > 1 ? ' Kanji sets differ between sessions.' : ''
  if (points.length === 1) return 'One session so far. A trend needs at least 3.'
  if (points.length === 2)
    return `Two sessions so far: ${first.s7_correct} then ${last.s7_correct} correct in S7, ${rt(first)} then ${rt(last)} s per answer. Too few for a trend.${sets}`
  return `Over ${points.length} sessions, correct answers in S7 went from ${first.s7_correct} to ${last.s7_correct} of ${last.s7_trials}, and response time from ${rt(first)} to ${rt(last)} s.${sets}`
}

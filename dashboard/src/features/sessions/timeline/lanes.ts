import type { Schemas } from '@/api/client'

// The timeline as data: one lane per row, in the fixed order of visualization-rules.md.
// Fills are token names; the chart resolves them in the current theme. A new lane
// (EEG later) is one more entry in buildLanes().

type Timeline = Schemas['SessionTimeline']

export type Bar = {
  start: number
  end: number
  /** Shape as well as colour: a bar, the incorrect-trial hatch, or a line through the slot. */
  mark: 'bar' | 'hatch' | 'line'
  /** Token; null leaves the bar unfilled. */
  fill: string | null
  /** 1 px inside border (bar) or the line itself (line). */
  stroke?: string
  dashed?: boolean
  label?: string
  labelColor?: string
  tip: string
}

export type Lane = {
  key: string
  label: string
  hint: string
  height: 40 | 32
  barHeight: 24 | 16
  /** null: the lane's event type was never recorded in the session. */
  bars: Bar[] | null
  note: string | null
}

const pad = (n: number, w = 2) => String(n).padStart(w, '0')

/** Session time as mm:ss (minutes keep counting past 59). */
export const clock = (ms: number) => `${pad(Math.floor(ms / 60_000))}:${pad(Math.floor(ms / 1000) % 60)}`
/** Session time as mm:ss.SSS. */
export const clockMs = (ms: number) => `${clock(ms)}.${pad(Math.round(ms) % 1000, 3)}`

const code = (state: string) => state.slice(0, 2)
const title = (level: string) => level[0] + level.slice(1).toLowerCase()
const span = (start: number, end: number) => `${clockMs(start)} to ${clockMs(end)}`

// design-system.md "Timeline marks beyond the three levels" (Oct 19).
function levelMark(level: string, prefix: 'esl' | 'lal'): Pick<Bar, 'mark' | 'fill' | 'stroke' | 'labelColor'> {
  if (['LOW', 'MEDIUM', 'HIGH'].includes(level))
    return { mark: 'bar', fill: `--color-${prefix}-${level.toLowerCase()}`, labelColor: level === 'HIGH' ? '--color-on-accent' : '--color-text' }
  if (level === 'FOCUS') return { mark: 'bar', fill: '--color-surface', stroke: '--color-esl-high', labelColor: '--color-text' }
  if (level === 'OFF') return { mark: 'line', fill: null, stroke: '--color-border-strong', labelColor: '--color-text-muted' }
  return { mark: 'bar', fill: '--color-state-neutral', labelColor: '--color-text' }      // Minimal, Baseline
}

function levelBars(levels: Timeline['environment'], prefix: 'esl' | 'lal', name: string, end: number): Bar[] | null {
  if (!levels) return null
  return levels.map((l) => {
    const to = l.end_ms ?? end
    return {
      start: l.start_ms, end: to, label: title(l.level), ...levelMark(l.level, prefix),
      tip: `${name} ${title(l.level)}, ${span(l.start_ms, to)}`,
    }
  })
}

function lane(key: string, label: string, hint: string, bars: Bar[] | null, gameFlow = false): Lane {
  return {
    key, label, hint, bars,
    height: gameFlow ? 40 : 32,
    barHeight: gameFlow ? 24 : 16,
    note: bars === null ? 'Not recorded in this session' : bars.length === 0 ? 'Nothing in this session' : null,
  }
}

export function buildLanes(t: Timeline): Lane[] {
  const end = t.session_end_ms ?? 0
  const states = t.states?.map((s): Bar => {
    const to = s.end_ms ?? end
    const key = code(s.state) === 'S7'
    return {
      start: s.start_ms, end: to, mark: 'bar', label: code(s.state),
      fill: key ? '--color-text' : '--color-state-neutral',
      labelColor: key ? '--color-surface' : '--color-text-secondary',
      tip: `${s.state}, ${span(s.start_ms, to)}${s.end_ms === null ? ', no exit recorded' : ''}`,
    }
  }) ?? null
  const trials = t.trials?.map((tr): Bar => {
    const to = tr.end_ms ?? end
    const [mark, word] =
      tr.end_ms === null ? (['bar', 'not completed (session ended)'] as const)
        : tr.is_correct === null ? (['bar', 'not answered'] as const)
          : tr.is_correct ? (['bar', 'correct'] as const) : (['hatch', 'incorrect'] as const)
    const unfinished = tr.end_ms === null || tr.is_correct === null
    return {
      start: tr.start_ms, end: to, mark,
      fill: unfinished ? null : mark === 'hatch' ? '--color-alert' : '--color-trial-correct',
      ...(unfinished ? { stroke: '--color-border-strong' } : {}),
      ...(tr.end_ms === null ? { dashed: true } : {}),
      tip: `${tr.trial_id}, ${word}, ${span(tr.start_ms, to)}`,
    }
  }) ?? null
  return [
    lane('states', 'Game Flow', 'States S0 to S9', states, true),
    lane('environment', 'Environment', 'ESL level', levelBars(t.environment, 'esl', 'ESL', end)),
    lane('assistance', 'Assistance', 'LAL level', levelBars(t.assistance, 'lal', 'LAL', end)),
    lane('trials', 'Trials', 'Start to completion', trials),
  ]
}

/** From the first S7 entry to its exit (or the last event); null if the session never reached S7. */
export function s7Window(t: Timeline): [number, number] | null {
  const s7 = t.states?.filter((s) => code(s.state) === 'S7') ?? []
  if (s7.length === 0) return null
  return [s7[0]!.start_ms, Math.max(...s7.map((s) => s.end_ms ?? t.session_end_ms ?? s.start_ms))]
}

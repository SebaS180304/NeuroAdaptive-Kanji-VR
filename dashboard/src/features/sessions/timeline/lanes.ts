import type { Schemas } from '@/api/client'
import { clockMs, stateCode as code } from '@/lib/format'

// The timeline as data: one lane per row, in the fixed order of visualization-rules.md.
// Fills are token names; the chart resolves them in the current theme. A new lane
// (EEG later) is one more entry in buildLanes().

type Timeline = Schemas['SessionTimeline']

export type Mark = {
  start: number
  /** Equal to start for a point mark (dot, tick, diamond, badge). */
  end: number
  /**
   * Shape as well as colour. Spans: bar, hatch (incorrect trial), line (through the slot),
   * band (cooldown), link (decision to Unity's answer). Points: dot, tick, diamond, badge.
   */
  mark: 'bar' | 'hatch' | 'line' | 'band' | 'link' | 'dot' | 'tick' | 'diamond' | 'badge'
  /** Token; null leaves the mark unfilled. */
  fill: string | null
  /** 1 px inside border, a 2 px diamond outline, or the line itself. */
  stroke?: string
  dashed?: boolean
  /** Offset and height inside the lane's bar slot, in px; the whole slot by default. */
  y?: number
  h?: number
  /** Badge shape (outcome chips of design-system.md: circle for positive and neutral, square otherwise). */
  shape?: 'circle' | 'square'
  label?: string
  labelColor?: string
  tip: string
  /** The trial a click on this mark selects. */
  ref?: string
}

export type Lane = {
  key: string
  label: string
  hint: string
  height: 40 | 32
  barHeight: 24 | 16
  /** null: the lane's event type was never recorded in the session. */
  marks: Mark[] | null
  note: string | null
}


const title = (level: string) => level[0] + level.slice(1).toLowerCase()
const span = (start: number, end: number) => `${clockMs(start)} to ${clockMs(end)}`

// design-system.md "Timeline marks beyond the three levels" (Oct 19).
function levelMark(level: string, prefix: 'esl' | 'lal'): Pick<Mark, 'mark' | 'fill' | 'stroke' | 'labelColor'> {
  if (['LOW', 'MEDIUM', 'HIGH'].includes(level))
    return { mark: 'bar', fill: `--color-${prefix}-${level.toLowerCase()}`, labelColor: level === 'HIGH' ? '--color-on-accent' : '--color-text' }
  if (level === 'FOCUS') return { mark: 'bar', fill: '--color-surface', stroke: '--color-esl-high', labelColor: '--color-text' }
  if (level === 'OFF') return { mark: 'line', fill: null, stroke: '--color-border-strong', labelColor: '--color-text-muted' }
  return { mark: 'bar', fill: '--color-state-neutral', labelColor: '--color-text' }      // Minimal, Baseline
}

function levelBars(levels: Timeline['environment'], prefix: 'esl' | 'lal', name: string, end: number): Mark[] | null {
  if (!levels) return null
  return levels.map((l) => {
    const to = l.end_ms ?? end
    return {
      start: l.start_ms, end: to, label: title(l.level), ...levelMark(l.level, prefix),
      tip: `${name} ${title(l.level)}, ${span(l.start_ms, to)}`,
    }
  })
}

function lane(key: string, label: string, hint: string, marks: Mark[] | null, gameFlow = false, missing = 'Not recorded in this session'): Lane {
  return {
    key, label, hint, marks,
    height: gameFlow ? 40 : 32,
    barHeight: gameFlow ? 24 : 16,
    note: marks === null ? missing : marks.length === 0 ? 'Nothing in this session' : null,
  }
}

const point = (ms: number) => ({ start: ms, end: ms })

// Lanes 5-8: design-system.md "Lanes 5-8 marks" (Oct 19).
function hintMarks(t: Timeline): Mark[] | null {
  return t.hints?.map((h): Mark => ({
    ...point(h.ms), mark: 'dot', y: 4, h: 8,
    ...(h.proactive ? { fill: null, stroke: '--color-lal-high' } : { fill: '--color-lal-high' }),
    tip: `${h.trial_id}, ${h.proactive ? 'proactive cue' : 'hint requested'} at ${clockMs(h.ms)}`,
  })) ?? null
}

function peripheralMarks(t: Timeline): Mark[] | null {
  if (!t.peripherals && !t.distractors) return null
  const events = (t.peripherals ?? []).map((p): Mark => ({
    ...point(p.ms), mark: 'tick', y: 0, h: 8, fill: '--color-peripheral',
    tip: `Peripheral event ${p.event_index}, ${p.object_name}, at ${clockMs(p.ms)}`,
  }))
  const distractors = (t.distractors ?? []).map((d): Mark =>
    d.kind === 'DWELL'
      ? { start: d.start_ms, end: d.start_ms + d.duration_ms, mark: 'bar', y: 12, h: 4, fill: '--color-distractor',
          tip: `Dwell on ${d.object_name}, ${span(d.start_ms, d.start_ms + d.duration_ms)}` }
      : { ...point(d.start_ms), mark: 'tick', y: 8, h: 8, fill: '--color-distractor',
          tip: `Orienting to ${d.object_name} at ${clockMs(d.start_ms)}, ${d.duration_ms} ms` })
  return [...events, ...distractors].sort((a, b) => a.start - b.start)
}

function headAwayMarks(t: Timeline, end: number): Mark[] | null {
  return t.head_away?.map((a): Mark => ({
    start: a.start_ms, end: a.end_ms ?? end, mark: 'bar',
    ...(a.end_ms === null ? { fill: null, stroke: '--color-headaway', dashed: true } : { fill: '--color-headaway' }),
    tip: a.end_ms === null
      ? `Head-away (${title(a.limit_crossed).replace('_', ' ')}) from ${clockMs(a.start_ms)}. No return recorded before the session ended`
      : `Head-away (${title(a.limit_crossed).replace('_', ' ')}), ${span(a.start_ms, a.end_ms)}`,
  })) ?? null
}

const OUTCOME_BADGE: Record<string, Pick<Mark, 'fill' | 'stroke' | 'shape'>> = {
  POSITIVE: { fill: '--color-outcome-positive', shape: 'circle' },
  NEUTRAL: { fill: null, stroke: '--color-text-muted', shape: 'circle' },
  NEGATIVE: { fill: '--color-outcome-negative', shape: 'square' },
  UNCERTAIN: { fill: null, stroke: '--color-text-muted', shape: 'square' },
}

function adaptationMarks(t: Timeline): Mark[] | null {
  if (!t.adaptations) return null
  const bands: Mark[] = [], links: Mark[] = [], diamonds: Mark[] = [], badges: Mark[] = []
  for (const a of t.adaptations) {
    const change = `${a.dimension === 'ESL' ? 'environment' : 'assistance'} ${a.from_level ? `${title(a.from_level)} to ` : 'to '}${title(a.to_level)}`
    const unity = a.unity_result === 'APPLIED' ? `Applied at ${clockMs(a.result_ms!)}`
      : a.unity_result === 'SKIPPED' ? `Skipped by Unity (${a.skip_reason}) at ${clockMs(a.result_ms!)}`
        : 'No answer from Unity recorded'
    const tip = `${a.trial_id}, estimated state ${title(a.learner_state)}: ${change}. ${unity}. ` +
      `Outcome: ${a.outcome ? a.outcome.toLowerCase() : 'not recorded'}`
    if (a.cooldown_until_ms !== null)
      bands.push({ start: a.decided_ms, end: a.cooldown_until_ms, mark: 'band', y: 2, h: 12, fill: '--color-accent-tint',
        tip: `Cooldown after ${a.trial_id}, until ${clockMs(a.cooldown_until_ms)}` })
    if (a.unity_result !== null && a.result_ms !== null)
      links.push({ start: a.decided_ms, end: a.result_ms, mark: 'link', fill: null, stroke: '--color-accent', tip })
    diamonds.push({
      ...point(a.decided_ms), mark: 'diamond', tip, ref: a.trial_id,
      ...(a.unity_result === 'APPLIED' ? { fill: '--color-accent' }
        : { fill: null, stroke: '--color-accent', ...(a.unity_result === null ? { dashed: true } : {}) }),
    })
    if (a.outcome && OUTCOME_BADGE[a.outcome])
      badges.push({ ...point(a.decided_ms), mark: 'badge', ...OUTCOME_BADGE[a.outcome]!, tip: `${a.trial_id}, outcome ${a.outcome.toLowerCase()}` })
  }
  return [...bands, ...links, ...diamonds, ...badges]
}

export function buildLanes(t: Timeline, condition?: string): Lane[] {
  const end = t.session_end_ms ?? 0
  const states = t.states?.map((s): Mark => {
    const to = s.end_ms ?? end
    const key = code(s.state) === 'S7'
    return {
      start: s.start_ms, end: to, mark: 'bar', label: code(s.state),
      fill: key ? '--color-text' : '--color-state-neutral',
      labelColor: key ? '--color-surface' : '--color-text-secondary',
      tip: `${s.state}, ${span(s.start_ms, to)}${s.end_ms === null ? ', no exit recorded' : ''}`,
    }
  }) ?? null
  const trials = t.trials?.map((tr): Mark => {
    const to = tr.end_ms ?? end
    const [mark, word] =
      tr.end_ms === null ? (['bar', 'not completed (session ended)'] as const)
        : tr.is_correct === null ? (['bar', 'not answered'] as const)
          : tr.is_correct ? (['bar', 'correct'] as const) : (['hatch', 'incorrect'] as const)
    const unfinished = tr.end_ms === null || tr.is_correct === null
    return {
      start: tr.start_ms, end: to, mark, ref: tr.trial_id,
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
    lane('hints', 'Hints', 'On request or proactive', hintMarks(t)),
    lane('peripherals', 'Peripherals',
      t.distractors === null && t.peripherals !== null ? 'Events; dwell not recorded' : 'Events, dwell, orienting',
      peripheralMarks(t)),
    lane('head_away', 'Head-away', 'Episodes', headAwayMarks(t, end)),
    lane('adaptations', 'Adaptations', 'Decisions and cooldown', adaptationMarks(t), false,
      condition === 'STATIC' ? 'No adaptations in a static session' : 'Not recorded in this session'),
  ]
}

/** From the first S7 entry to its exit (or the last event); null if the session never reached S7. */
export function s7Window(t: Timeline): [number, number] | null {
  const s7 = t.states?.filter((s) => code(s.state) === 'S7') ?? []
  if (s7.length === 0) return null
  return [s7[0]!.start_ms, Math.max(...s7.map((s) => s.end_ms ?? t.session_end_ms ?? s.start_ms))]
}

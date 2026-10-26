import { describe, expect, it } from 'vitest'
import type { Schemas } from '@/api/client'
import { clock, clockMs } from '@/lib/format'
import { buildLanes, s7Window } from './lanes'

type Timeline = Schemas['SessionTimeline']

const DATA: Timeline = {
  session_end_ms: 400_000,
  states: [
    { state: 'S5_STANDARDIZED_LEARNING', start_ms: 0, end_ms: 100_000 },
    { state: 'S7_EXPERIMENTAL_RETRIEVAL', start_ms: 100_000, end_ms: 300_000 },
    { state: 'S9_SESSION_END', start_ms: 300_000, end_ms: null },
  ],
  environment: [
    { level: 'LOW', start_ms: 0, end_ms: 100_000 },
    { level: 'FOCUS', start_ms: 100_000, end_ms: 200_000 },
    { level: 'BASELINE', start_ms: 200_000, end_ms: null },
  ],
  assistance: [
    { level: 'OFF', start_ms: 0, end_ms: 100_000 },
    { level: 'MEDIUM', start_ms: 100_000, end_ms: null },
  ],
  trials: [
    { trial_id: 'S7-001', block_state: 'S7_EXPERIMENTAL_RETRIEVAL', start_ms: 110_000, end_ms: 115_000, is_correct: true },
    { trial_id: 'S7-002', block_state: 'S7_EXPERIMENTAL_RETRIEVAL', start_ms: 120_000, end_ms: 125_000, is_correct: false },
    { trial_id: 'S7-003', block_state: 'S7_EXPERIMENTAL_RETRIEVAL', start_ms: 130_000, end_ms: 135_000, is_correct: null },
    { trial_id: 'S7-004', block_state: 'S7_EXPERIMENTAL_RETRIEVAL', start_ms: 140_000, end_ms: null, is_correct: null },
  ],
  hints: [
    { ms: 111_000, trial_id: 'S7-001', proactive: false },
    { ms: 130_000, trial_id: 'S7-003', proactive: true },
  ],
  peripherals: [{ ms: 112_000, event_index: 1, object_name: 'WallClock_T3' }],
  distractors: [
    { kind: 'DWELL', start_ms: 113_000, duration_ms: 1200, object_name: 'WallClock_T3' },
    { kind: 'ORIENTING', start_ms: 114_000, duration_ms: 600, object_name: 'WallClock_T3' },
  ],
  head_away: [
    { start_ms: 150_000, end_ms: 152_500, limit_crossed: 'YAW' },
    { start_ms: 390_000, end_ms: null, limit_crossed: 'PITCH_DOWN' },
  ],
  adaptations: [
    { decision_id: 'd1', trial_id: 'S7-006', decided_ms: 200_000, action: 'CHANGE_ENVIRONMENT', dimension: 'ESL',
      from_level: 'MEDIUM', to_level: 'LOW', learner_state: 'DISENGAGED', unity_result: 'APPLIED', skip_reason: null,
      result_ms: 201_500, cooldown_until_ms: 215_000, outcome: 'NEGATIVE' },
    { decision_id: 'd2', trial_id: 'S7-011', decided_ms: 250_000, action: 'CHANGE_ASSISTANCE', dimension: 'LAL',
      from_level: 'MEDIUM', to_level: 'HIGH', learner_state: 'OVERLOADED', unity_result: 'SKIPPED', skip_reason: 'TIMEOUT',
      result_ms: 250_300, cooldown_until_ms: null, outcome: null },
    { decision_id: 'd3', trial_id: 'S7-015', decided_ms: 300_000, action: 'CHANGE_ASSISTANCE', dimension: 'LAL',
      from_level: 'HIGH', to_level: 'MEDIUM', learner_state: 'STABLE', unity_result: null, skip_reason: null,
      result_ms: null, cooldown_until_ms: null, outcome: null },
  ],
}

describe('timeline lanes', () => {
  it('keeps the fixed lane order, with the lane sizes of design-system.md', () => {
    const lanes = buildLanes(DATA)
    expect(lanes.map((l) => [l.label, l.height, l.barHeight])).toEqual([
      ['Game Flow', 40, 24], ['Environment', 32, 16], ['Assistance', 32, 16], ['Trials', 32, 16],
      ['Hints', 32, 16], ['Peripherals', 32, 16], ['Head-away', 32, 16], ['Adaptations', 32, 16],
    ])
  })

  it('draws an open interval up to the last event', () => {
    const [states, env] = buildLanes(DATA)
    expect(states!.marks!.at(-1)).toMatchObject({ start: 300_000, end: 400_000, label: 'S9' })
    expect(env!.marks!.at(-1)).toMatchObject({ start: 200_000, end: 400_000, label: 'Baseline' })
  })

  it('S7 stands out; levels use their tokens, Minimal and Baseline the neutral fill', () => {
    const [states, env] = buildLanes(DATA)
    expect(states!.marks!.map((b) => b.fill)).toEqual(['--color-state-neutral', '--color-text', '--color-state-neutral'])
    expect(env!.marks!.map((b) => b.fill)).toEqual(['--color-esl-low', '--color-surface', '--color-state-neutral'])
  })

  it('ESL Focus is the surface with an esl-high inside border (design-system.md, Oct 19)', () => {
    const focus = buildLanes(DATA)[1]!.marks![1]!
    expect(focus).toMatchObject({ mark: 'bar', fill: '--color-surface', stroke: '--color-esl-high', label: 'Focus' })
  })

  it('LAL Off is a line through the slot, not a bar (design-system.md, Oct 19)', () => {
    const [off, medium] = buildLanes(DATA)[2]!.marks!
    expect(off).toMatchObject({ mark: 'line', stroke: '--color-border-strong', label: 'Off', labelColor: '--color-text-muted' })
    expect(medium).toMatchObject({ mark: 'bar', fill: '--color-lal-medium' })
  })

  it('tells correct, incorrect, not answered and not completed trials apart by more than colour', () => {
    const trials = buildLanes(DATA)[3]!.marks!
    expect(trials.map((b) => [b.mark, b.fill, b.stroke, b.dashed ?? false])).toEqual([
      ['bar', '--color-trial-correct', undefined, false],
      ['hatch', '--color-alert', undefined, false],
      ['bar', null, '--color-border-strong', false],                // not answered
      ['bar', null, '--color-border-strong', true],                 // not completed: the session ended
    ])
    expect(trials[3]).toMatchObject({ end: 400_000 })
    expect(trials[1]!.tip).toBe('S7-002, incorrect, 02:00.000 to 02:05.000')
  })

  it('hints are point marks: filled when requested, outlined when proactive', () => {
    const hints = buildLanes(DATA)[4]!.marks!
    expect(hints.map((m) => [m.mark, m.start, m.fill, m.stroke])).toEqual([
      ['dot', 111_000, '--color-lal-high', undefined],
      ['dot', 130_000, null, '--color-lal-high'],
    ])
  })

  it('peripheral ticks, dwell bars and orienting ticks share a lane, each in its own row', () => {
    const lane = buildLanes(DATA)[5]!
    expect(lane.marks!.map((m) => [m.mark, m.start, m.end, m.y, m.h, m.fill])).toEqual([
      ['tick', 112_000, 112_000, 0, 8, '--color-peripheral'],
      ['bar', 113_000, 114_200, 12, 4, '--color-distractor'],
      ['tick', 114_000, 114_000, 8, 8, '--color-distractor'],
    ])
    expect(lane.hint).toBe('Events, dwell, orienting')
    expect(buildLanes({ ...DATA, distractors: null })[5]!.hint).toBe('Events; dwell not recorded')
  })

  it('head-away episodes are bars; one with no return is outlined and dashed up to the end', () => {
    const away = buildLanes(DATA)[6]!.marks!
    expect(away[0]).toMatchObject({ mark: 'bar', fill: '--color-headaway', start: 150_000, end: 152_500 })
    expect(away[1]).toMatchObject({ fill: null, stroke: '--color-headaway', dashed: true, end: 400_000 })
    expect(away[1]!.tip).toBe('Head-away (Pitch down) from 06:30.000. No return recorded before the session ended')
  })

  it('a decision is a diamond joined to its application, with its cooldown and outcome', () => {
    const marks = buildLanes(DATA)[7]!.marks!
    // Drawn back to front: bands, links, diamonds, badges.
    expect(marks.map((m) => [m.mark, m.start, m.end])).toEqual([
      ['band', 200_000, 215_000],
      ['link', 200_000, 201_500], ['link', 250_000, 250_300],              // none for d3: Unity never answered
      ['diamond', 200_000, 200_000], ['diamond', 250_000, 250_000], ['diamond', 300_000, 300_000],
      ['badge', 200_000, 200_000],
    ])
    const [applied, skipped, pending] = marks.filter((m) => m.mark === 'diamond')
    expect(applied).toMatchObject({ fill: '--color-accent' })
    expect(applied!.tip).toBe('S7-006, estimated state Disengaged: environment Medium to Low. Applied at 03:21.500. Outcome: negative')
    expect(skipped).toMatchObject({ fill: null, stroke: '--color-accent' })
    expect(skipped!.dashed).toBeUndefined()
    expect(skipped!.tip).toBe('S7-011, estimated state Overloaded: assistance Medium to High. Skipped by Unity (TIMEOUT) at 04:10.300. Outcome: not recorded')
    expect(pending).toMatchObject({ fill: null, stroke: '--color-accent', dashed: true })
    expect(pending!.tip).toBe('S7-015, estimated state Stable: assistance High to Medium. No answer from Unity recorded. Outcome: not recorded')
    expect(marks.find((m) => m.mark === 'badge')).toMatchObject({ fill: '--color-outcome-negative', shape: 'square' })
  })

  it('names UNDERCHALLENGED by its short name in the decision tooltip', () => {
    const data = { ...DATA, adaptations: DATA.adaptations!.map((a, i) => (i === 0 ? { ...a, learner_state: 'UNDERCHALLENGED' } : a)) }
    const diamond = buildLanes(data)[7]!.marks!.find((m) => m.mark === 'diamond')!
    expect(diamond.tip).toMatch(/^S7-006, estimated state Low challenge \(estimated\): /)
  })

  it('trial bars and decision diamonds name their trial, so a click can select it', () => {
    const lanes = buildLanes(DATA)
    expect(lanes[3]!.marks!.map((m) => m.ref)).toEqual(['S7-001', 'S7-002', 'S7-003', 'S7-004'])
    expect(lanes[7]!.marks!.filter((m) => m.mark === 'diamond').map((m) => m.ref)).toEqual(['S7-006', 'S7-011', 'S7-015'])
    expect(lanes[7]!.marks!.filter((m) => m.mark !== 'diamond').every((m) => m.ref === undefined)).toBe(true)
  })

  it('a static session has no adaptations lane data, and says why', () => {
    const lane = buildLanes({ ...DATA, adaptations: null }, 'STATIC')[7]!
    expect(lane.marks).toBeNull()
    expect(lane.note).toBe('No adaptations in a static session')
  })

  it('says whether an empty lane was recorded or not', () => {
    const lanes = buildLanes({ ...DATA, environment: null, assistance: [] })
    expect(lanes[1]!.marks).toBeNull()
    expect(lanes[1]!.note).toBe('Not recorded in this session')
    expect(lanes[2]!.marks).toEqual([])
    expect(lanes[2]!.note).toBe('Nothing in this session')
  })

  it('formats session time as mm:ss and mm:ss.SSS', () => {
    expect(clock(83_456)).toBe('01:23')
    expect(clockMs(83_456)).toBe('01:23.456')
    expect(clockMs(3_723_004)).toBe('62:03.004')
  })

  it('finds the S7 window, if the session reached it', () => {
    expect(s7Window(DATA)).toEqual([100_000, 300_000])
    expect(s7Window({ ...DATA, states: DATA.states!.slice(0, 1) })).toBeNull()
  })
})

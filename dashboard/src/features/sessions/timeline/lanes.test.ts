import { describe, expect, it } from 'vitest'
import type { Schemas } from '@/api/client'
import { buildLanes, clock, clockMs, s7Window } from './lanes'

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
    { level: 'BASELINE', start_ms: 100_000, end_ms: null },
  ],
  assistance: [],
  trials: [
    { trial_id: 'S7-001', block_state: 'S7_EXPERIMENTAL_RETRIEVAL', start_ms: 110_000, end_ms: 115_000, is_correct: true },
    { trial_id: 'S7-002', block_state: 'S7_EXPERIMENTAL_RETRIEVAL', start_ms: 120_000, end_ms: 125_000, is_correct: false },
    { trial_id: 'S7-003', block_state: 'S7_EXPERIMENTAL_RETRIEVAL', start_ms: 130_000, end_ms: null, is_correct: null },
  ],
}

describe('timeline lanes', () => {
  it('keeps the fixed lane order, with the lane sizes of design-system.md', () => {
    const lanes = buildLanes(DATA)
    expect(lanes.map((l) => [l.label, l.height, l.barHeight])).toEqual([
      ['Game Flow', 40, 24], ['Environment', 32, 16], ['Assistance', 32, 16], ['Trials', 32, 16],
    ])
  })

  it('draws an open interval up to the last event', () => {
    const [states, env] = buildLanes(DATA)
    expect(states!.bars!.at(-1)).toMatchObject({ start: 300_000, end: 400_000, label: 'S9' })
    expect(env!.bars!.at(-1)).toMatchObject({ start: 100_000, end: 400_000, label: 'Baseline' })
  })

  it('S7 stands out; levels use their tokens, and levels with no token the neutral fill', () => {
    const [states, env] = buildLanes(DATA)
    expect(states!.bars!.map((b) => b.fill)).toEqual(['--color-state-neutral', '--color-text', '--color-state-neutral'])
    expect(env!.bars!.map((b) => b.fill)).toEqual(['--color-esl-low', '--color-state-neutral'])
  })

  it('tells correct, incorrect and unfinished trials apart by more than colour', () => {
    const trials = buildLanes(DATA)[3]!.bars!
    expect(trials.map((b) => b.pattern)).toEqual(['solid', 'hatch', 'outline'])
    expect(trials[2]).toMatchObject({ end: 400_000 })
    expect(trials[1]!.tip).toBe('S7-002, incorrect, 02:00.000 to 02:05.000')
  })

  it('says whether an empty lane was recorded or not', () => {
    const lanes = buildLanes({ ...DATA, environment: null })
    expect(lanes[1]!.bars).toBeNull()
    expect(lanes[1]!.note).toBe('Not recorded in this session')
    expect(lanes[2]!.bars).toEqual([])
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

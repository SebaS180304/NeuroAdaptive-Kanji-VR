import { describe, expect, it } from 'vitest'
import type { Schemas } from '@/api/client'
import {
  acrossSentence, badges, calibrationRows, groupSentence, practiceSentence, scopeLine, staticOnly, tooFew,
} from './profileText'

type Cal = Schemas['ProfileCalibration']
type Group = Schemas['ProfileAdaptationGroup']
type Point = Schemas['ProfileTrendPoint']

const cal = (over: Partial<Cal> = {}): Cal => ({
  session_id: 's1', rt_ref: { T1_MEANING_TO_KANJI: 2300, T2_KANJI_TO_MEANING: 1500, T3_KANJI_TO_READING: 2100 },
  rt_ref_global: 2049, rt_spread: 0.2, acc_ref: 0.875, idle_eff_ref: null, away_ref_ms: 412, env_dwell_ref_ms: 180,
  orienting_rate_ref: null, n_trials: 8, n_valid_rt: 8, reliability: 1, correct: 7, n: 8, fallback_types: [], ...over,
})
const group = (over: Partial<Group> = {}): Group => ({
  key: 'OVERLOADED.NONE.LAL.UP', learner_state: 'OVERLOADED', cause: null, dimension: 'LAL', direction: 'UP', count: 1,
  outcomes: { POSITIVE: 1 }, outcome_reasons: { POSITIVE: { RESOLVED: 1 } }, decisions: { s1: ['d1'] },
  last_decided_at: '2026-10-20T07:00:00+00:00', ...over,
})
const point = (over: Partial<Point> = {}): Point => ({
  session_id: 's1', condition: 'STATIC', kanji_set: 'A', created_at: '2026-10-01T00:00:00+00:00', s7_trials: 20,
  s7_correct: 15, s7_mean_rt_ms: 2412.3, no_change: null, decisions_recorded: null, ...over,
})

describe('Learner Profile copy (Contenido_UI_F-PROFILE.md)', () => {
  it('says how many completed sessions it covers, and never mentions aborted ones', () => {
    expect(scopeLine(1)).toBe(
      "A summary of 1 completed session. It describes what happened in windows of trials, not the person, and it doesn't change how the next session starts.")
    expect(scopeLine(11)).toMatch(/^A summary of 11 completed sessions\./)
    expect(scopeLine(11)).not.toMatch(/abort/i)
  })

  it('opens Usual performance with the latest practice', () => {
    expect(practiceSentence('P01', cal())).toBe(
      'In practice (S6) of the latest session, P01 answered 7 of 8 correctly, taking about 2.0 s per answer, and spent about 0.4 s per trial looking away from the task.')
    expect(practiceSentence('P01', cal({ away_ref_ms: 0 }))).toMatch(/, and stayed on the task area throughout\.$/)
  })

  it('gives the latest value, the range across sessions and the global-median fallback', () => {
    const rows = calibrationRows([cal({ correct: 6, rt_ref: { T1_MEANING_TO_KANJI: 2900 } }), cal({ fallback_types: ['T2_KANJI_TO_MEANING'] })])
    expect(rows.find((r) => r.label === 'Kanji to meaning (T2)')).toMatchObject({ latest: '1.5 s', fallback: true })
    expect(rows.find((r) => r.label === 'Meaning to kanji (T1)')).toMatchObject({ latest: '2.3 s', range: '2.3–2.9 s' })
    expect(rows.find((r) => r.label === 'Correct in practice')).toMatchObject({ latest: '7 of 8', range: '6–7 of 8' })
    expect(rows.find((r) => r.label === 'Looking away from the task')).toMatchObject({ latest: '0.4 s per trial', range: '0.4 s' })
  })

  it('describes the window, never the person, and says "after", never "helped"', () => {
    expect(groupSentence(group())).toBe(
      'When answers got slower and less accurate than in practice (estimated overload), assistance (LAL) was raised 1 time.')
    expect(groupSentence(group({ learner_state: 'DISENGAGED', cause: 'IMPULSIVE', dimension: 'ESL', direction: 'DOWN', count: 2 })))
      .toBe('When answers came quickly and were wrong (estimated disengagement, quick errors), the environment level (ESL) was lowered 2 times.')
    expect(groupSentence(group({ learner_state: 'STABLE', direction: 'DOWN', count: 2, outcomes: { POSITIVE: 1, NOT_RECORDED: 1 } })))
      .toBe('After two steady windows, assistance (LAL) was returned to MEDIUM 2 times.')
  })

  it('closes with the most frequent result only from 3 classified outcomes', () => {
    const g = group({ count: 4, outcomes: { POSITIVE: 2, NEUTRAL: 1, UNCERTAIN: 1 } })
    expect(groupSentence(g)).toMatch(/was raised 4 times; recovered after 2 of 3\.$/)
    expect(tooFew(g)).toBe(false)
    expect(tooFew(group({ count: 3, outcomes: { POSITIVE: 2, UNCERTAIN: 1 } }))).toBe(true)
  })

  it('labels outcomes by direction, with the reason always visible for UNCERTAIN', () => {
    const rescue = badges(group({ outcomes: { POSITIVE: 1, UNCERTAIN: 2, NOT_RECORDED: 1 },
      outcome_reasons: { POSITIVE: { RESOLVED: 1 }, UNCERTAIN: { INCOMPLETE: 1, NOT_APPLIED: 1 }, NOT_RECORDED: { NOT_RECORDED: 1 } } }))
    expect(rescue.map((b) => b.text)).toEqual([
      'Recovered after: 1', "Can't tell: not applied: 1", "Can't tell: S7 ended first: 1", 'Not recorded: 1'])
    expect(rescue[0]!.title).toBe('POSITIVE · RESOLVED 1')
    const back = badges(group({ learner_state: 'STABLE', direction: 'DOWN', outcomes: { POSITIVE: 1, NEUTRAL: 1, NEGATIVE: 1 },
      outcome_reasons: { POSITIVE: { HELD: 1 }, NEUTRAL: { HELD_WITH_DROP: 1 }, NEGATIVE: { RELAPSED: 1 } } }))
    expect(back.map((b) => b.text)).toEqual(['Held after: 1', 'Held, with a dip: 1', 'Slipped after: 1'])
  })

  it('says STATIC never adapts, also with a single session', () => {
    expect(staticOnly(2)).toMatch(/^No adaptations: all 2 sessions so far were STATIC/)
    expect(staticOnly(1)).toMatch(/^No adaptations: the only session so far was STATIC, .* come from this session\.$/)
  })

  it('describes first and last session only, with no projection', () => {
    expect(acrossSentence([point()])).toBe('One session so far. A trend needs at least 3.')
    expect(acrossSentence([point(), point({ s7_correct: 17, s7_mean_rt_ms: 2100 })])).toBe(
      'Two sessions so far: 15 then 17 correct in S7, 2.4 then 2.1 s per answer. Too few for a trend.')
    expect(acrossSentence([point(), point(), point({ s7_correct: 18, s7_mean_rt_ms: 1950, kanji_set: 'C' })])).toBe(
      'Over 3 sessions, correct answers in S7 went from 15 to 18 of 20, and response time from 2.4 to 2.0 s. Kanji sets differ between sessions.')
  })
})

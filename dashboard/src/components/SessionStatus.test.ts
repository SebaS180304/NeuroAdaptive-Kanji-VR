import { describe, expect, it } from 'vitest'
import { sessionStatusText } from './SessionStatus'

describe('session status words (design-system.md, V1.8)', () => {
  it('names the last state of an aborted session, when recorded', () => {
    expect(sessionStatusText('ABORTED', 'S7_EXPERIMENTAL_RETRIEVAL')).toBe('Aborted in S7')
    expect(sessionStatusText('ABORTED', null)).toBe('Aborted')
  })

  it('uses the shared words for the other statuses', () => {
    expect(sessionStatusText('COMPLETED', 'S9_SESSION_SUMMARY')).toBe('Completed')
    expect(sessionStatusText('IN_PROGRESS', 'S5_STANDARDIZED_LEARNING')).toBe('In progress')
    expect(sessionStatusText('CREATED', null)).toBe('Not started')
  })
})

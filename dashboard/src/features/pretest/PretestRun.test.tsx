import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { json, mockApi } from '@/test/api'
import { renderApp } from '@/test/render'

const PID = 'p1'
const participant = { id: PID, external_code: 'P07' }
const state = (answered: number, next: string | null, extra = {}) => ({
  completed: next === null, completed_at: next === null ? '2026-10-18T05:07:00Z' : null, answered,
  next: next && { kanji_id: `ID_${next}`, kanji: next },
  // The page receives these but must never render them (the participant is looking).
  substitutions: [{ set: 'A', original: '月', substitute: '火' }], flagged: [{ set: 'B', original: '車' }],
  ...extra,
})

afterEach(() => vi.unstubAllGlobals())

const routes = (s: object, more = {}) => ({
  [`GET /api/participants/${PID}`]: () => json(participant),
  [`GET /api/participants/${PID}/pretest`]: () => json(s),
  ...more,
})

describe('pre-test, one kanji (V1.10)', () => {
  it('shows the kanji, the code and the count, and nothing the participant must not see', async () => {
    mockApi(routes(state(0, '月')))
    renderApp(`/pretest/${PID}`)
    expect(await screen.findByRole('img', { name: 'Kanji to answer' })).toHaveTextContent('月')
    expect(screen.getByText('P07')).toBeInTheDocument()
    expect(screen.getByText(/answered/).closest('[aria-live]')).toHaveTextContent('0 answered')
    expect(screen.queryByRole('navigation', { name: 'Main' })).toBeNull()       // focus mode: no rail
    expect(document.body.textContent).not.toMatch(/substitute|火|車|Set [ABC]/i)
  })

  it('"No" on key 1 needs no typing, and Save moves to the next kanji', async () => {
    let s = state(0, '月')
    const calls = mockApi(routes(s, {
      [`POST /api/participants/${PID}/pretest/responses`]: () => { s = state(1, '車'); return json(s) },
    }))
    const user = userEvent.setup()
    renderApp(`/pretest/${PID}`)
    await screen.findByRole('img', { name: 'Kanji to answer' })
    await user.keyboard('1')
    expect(screen.getByRole('button', { name: /^No\s*Key 1/ })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.queryByLabelText('Reading, in kana or romaji')).toBeNull()
    await user.click(screen.getByRole('button', { name: 'Save and next' }))
    expect(await screen.findByRole('img', { name: 'Kanji to answer' })).toHaveTextContent('車')
    expect(calls.at(-1)).toEqual({ key: `POST /api/participants/${PID}/pretest/responses`, body: { kanji_id: 'ID_月', self_report: 'NO' } })
    expect(screen.getByRole('button', { name: /^No\s*Key 1/ })).toHaveAttribute('aria-pressed', 'false')   // reset
  })

  it('"Yes" asks for the reading and meaning, checks them, lets the researcher flip, then saves the verdict', async () => {
    const calls = mockApi(routes(state(0, '月'), {
      [`POST /api/participants/${PID}/pretest/check`]: () => json({ reading_correct: true, meaning_correct: false }),
      [`POST /api/participants/${PID}/pretest/responses`]: () => json(state(1, '車')),
    }))
    const user = userEvent.setup()
    renderApp(`/pretest/${PID}`)
    await screen.findByRole('img', { name: 'Kanji to answer' })
    await user.keyboard('3')
    const save = screen.getByRole('button', { name: 'Save and next' })
    expect(save).toBeDisabled()                                                  // no result yet
    await user.type(screen.getByLabelText('Reading, in kana or romaji'), 'tsuki')
    await user.type(screen.getByLabelText('Meaning, in English'), 'sun')
    await user.keyboard('1')                                     // typed into the meaning, not an answer
    expect(screen.getByRole('button', { name: /^Yes\s*Key 3/ })).toHaveAttribute('aria-pressed', 'true')
    await user.click(screen.getByRole('button', { name: 'Check' }))
    expect(await screen.findByText('Correct')).toBeInTheDocument()
    expect(screen.getByText('Incorrect')).toBeInTheDocument()

    const strip = screen.getByRole('region', { name: 'Researcher controls' })
    await user.click(within(strip).getByRole('button', { name: 'Mark meaning correct' }))
    expect(screen.queryByText('Incorrect')).toBeNull()
    expect(within(strip).getByRole('button', { name: 'Mark meaning incorrect' })).toBeInTheDocument()

    await user.click(save)
    expect(calls.at(-1)?.body).toEqual({
      kanji_id: 'ID_月', self_report: 'YES', typed_reading: 'tsuki', typed_meaning: 'sun1',
      reading_correct: true, meaning_correct: true,
    })
  })

  it('a changed answer needs a new check before saving', async () => {
    mockApi(routes(state(0, '月'), {
      [`POST /api/participants/${PID}/pretest/check`]: () => json({ reading_correct: true, meaning_correct: true }),
    }))
    const user = userEvent.setup()
    renderApp(`/pretest/${PID}`)
    await screen.findByRole('img', { name: 'Kanji to answer' })
    await user.keyboard('2')
    await user.type(screen.getByLabelText('Reading, in kana or romaji'), 'tsuki')
    await user.click(screen.getByRole('button', { name: 'Check' }))
    expect(screen.getByRole('button', { name: 'Save and next' })).toBeEnabled()
    await user.type(screen.getByLabelText('Meaning, in English'), 'moon')
    expect(screen.getByRole('button', { name: 'Save and next' })).toBeDisabled()
    expect(screen.queryByText('Correct')).toBeNull()
  })

  it('a 409 reloads the state and says so', async () => {
    let s = state(0, '月')
    mockApi(routes(state(0, '月'), {
      [`GET /api/participants/${PID}/pretest`]: () => json(s),
      [`POST /api/participants/${PID}/pretest/responses`]: () => { s = state(1, '車'); return json({ detail: 'expected kanji 車' }, 409) },
    }))
    const user = userEvent.setup()
    renderApp(`/pretest/${PID}`)
    await screen.findByRole('img', { name: 'Kanji to answer' })
    await user.keyboard('1')
    await user.click(screen.getByRole('button', { name: 'Save and next' }))
    expect(await screen.findByRole('status', { name: 'This kanji was already saved' })).toBeInTheDocument()
    expect(await screen.findByRole('img', { name: 'Kanji to answer' })).toHaveTextContent('車')
    expect(document.body.textContent).not.toContain('expected kanji')
  })

  it('a 422 shows its notice next to Save', async () => {
    mockApi(routes(state(0, '月'), {
      [`POST /api/participants/${PID}/pretest/responses`]: () => json({ detail: [] }, 422),
    }))
    const user = userEvent.setup()
    renderApp(`/pretest/${PID}`)
    await screen.findByRole('img', { name: 'Kanji to answer' })
    await user.keyboard('1')
    await user.click(screen.getByRole('button', { name: 'Save and next' }))
    expect(await screen.findByRole('alert', { name: 'Check both answers before saving' })).toBeInTheDocument()
  })

  it('resuming says where it picks up', async () => {
    mockApi(routes(state(4, '車')))
    renderApp(`/pretest/${PID}`)
    const notice = await screen.findByRole('status', { name: 'Picking up where you left off' })
    expect(notice).toHaveTextContent('4 kanji answered so far. This is the next one.')
  })

  it('Pause goes back to the list with where it stopped', async () => {
    mockApi(routes(state(3, '車'), { 'GET /api/research/participants': () => json([]) }))
    const user = userEvent.setup()
    renderApp(`/pretest/${PID}`)
    await screen.findByRole('img', { name: 'Kanji to answer' })
    await user.click(screen.getByRole('link', { name: 'Pause' }))
    expect(await screen.findByRole('status', { name: 'Paused at 3 answered' })).toBeInTheDocument()
  })
})

describe('pre-test, complete (V1.10)', () => {
  it('thanks the participant and shows the researcher only the time, the count and the link', async () => {
    mockApi(routes(state(18, null)))
    renderApp(`/pretest/${PID}`)
    expect(await screen.findByRole('heading', { level: 1, name: "That's all. Thank you." })).toBeInTheDocument()
    const researcher = screen.getByRole('region', { name: 'For the researcher' })
    expect(researcher).toHaveTextContent(/Completed\s*2026-10-18, \d{2}:\d{2}/)
    expect(researcher).toHaveTextContent('Answered18 kanji')
    expect(within(researcher).getByRole('link', { name: 'Open participant page' })).toHaveAttribute('href', `/participants/${PID}`)
    expect(screen.queryByRole('link', { name: 'Pause' })).toBeNull()
    expect(document.body.textContent).not.toMatch(/substitute|月|火|車|Set [ABC]/i)
  })
})

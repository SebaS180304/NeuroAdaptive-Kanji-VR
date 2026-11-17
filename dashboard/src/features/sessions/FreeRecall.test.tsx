import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { json, mockApi } from '@/test/api'
import { renderApp } from '@/test/render'

const SID = 's2'
const PATH = `/api/sessions/${SID}/block-r/recall`
const kanji = [
  { kanji_id: 'KANJI_TSUKI', kanji: '月', meaning: 'moon', reading: 'つき' },
  { kanji_id: 'KANJI_KURUMA', kanji: '車', meaning: 'car', reading: 'くるま' },
  { kanji_id: 'KANJI_HI', kanji: '火', meaning: 'fire', reading: 'ひ' },
  { kanji_id: 'KANJI_TAKE', kanji: '竹', meaning: 'bamboo', reading: 'たけ' },
  { kanji_id: 'KANJI_ISHI', kanji: '石', meaning: 'stone', reading: 'いし' },
]
const form = (saved: object | null = null) => ({
  session_id: SID, participant_code: 'P01', visit_number: 2,
  evaluated_session_id: '65af2fe4-b620-4cb2-98ff-d48a89b70f8a', evaluated_kanji_set: 'A',
  learned_at: '2026-11-16T09:18:34Z', kanji, saved,
  board_text: ['Last time you learned some kanji. Tell the researcher everything you remember about them.', 'Say it out loud.'],
})
const savedAt = '2026-11-19T03:05:00Z'

afterEach(() => vi.unstubAllGlobals())

const row = (name: string) => screen.getByRole('row', { name: new RegExp(name) })

describe('block R free recall (V1.12, D-F6-226)', () => {
  it('shows the evaluated session, its five kanji as taught and the What counts rule, in focus mode', async () => {
    mockApi({ [`GET ${PATH}`]: () => json(form()) })
    renderApp(`/sessions/${SID}/recall`)
    expect(await screen.findByRole('heading', { name: 'Free recall' })).toBeInTheDocument()
    expect(screen.getByText('P01')).toBeInTheDocument()
    expect(screen.getByText('Visit 2, block R part 1 of 3')).toBeInTheDocument()
    expect(screen.getByText('65af2fe4')).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Main' })).toBeNull()          // focus mode: no rail
    expect(screen.getByText(/Meaning: the meaning or a clear synonym, in any language\. Reading: the Japanese reading, said close enough to recognise\. Anything you're unsure about goes in "What they said", without a mark\. There is no mark for a partial answer\./)).toBeInTheDocument()
    expect(screen.getByText(/Last time you learned some kanji/)).toBeInTheDocument()
    expect(within(row('月')).getByText('moon')).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Nothing marked. Not saved yet.')
    expect(screen.getByRole('button', { name: 'Save: nothing recalled' })).toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/\d{1,2}:\d\d/)                 // no clock (D-F6-212)
  })

  it('orders the kanji by their first mark, keeps that order when a mark goes off and on, and saves it', async () => {
    const calls = mockApi({
      [`GET ${PATH}`]: () => json(form()),
      [`POST ${PATH}`]: (body) => json(form({ saved_at: savedAt, recalled: 2, items: (body as { items: unknown[] }).items, anything_else: null })),
    })
    const user = userEvent.setup()
    renderApp(`/sessions/${SID}/recall`)
    await screen.findByRole('heading', { name: 'Free recall' })
    await user.click(within(row('車')).getByRole('button', { name: /Meaning/ }))
    await user.click(within(row('月')).getByRole('button', { name: /Reading/ }))
    expect(within(row('車')).getByRole('button', { name: /Meaning/ })).toHaveAttribute('aria-pressed', 'true')
    expect(within(row('車')).getByText('1st')).toBeInTheDocument()
    expect(within(row('月')).getByText('2nd')).toBeInTheDocument()
    await user.click(within(row('車')).getByRole('button', { name: /Meaning/ }))      // off: no order shown
    expect(within(row('車')).getByText('—')).toBeInTheDocument()
    expect(within(row('月')).getByText('1st')).toBeInTheDocument()
    await user.click(within(row('車')).getByRole('button', { name: /Meaning/ }))      // on again: its first place
    expect(within(row('車')).getByText('1st')).toBeInTheDocument()
    await user.type(within(row('竹')).getByRole('textbox'), 'tree?')
    expect(screen.getByRole('status')).toHaveTextContent('2 of 5 kanji recalled. Not saved yet.')
    await user.click(screen.getByRole('button', { name: 'Save free recall' }))
    expect(await screen.findByRole('button', { name: 'Save changes' })).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent(/^Saved at \d\d:\d\d\. 2 of 5 kanji recalled\./)
    const body = calls.at(-1)!.body as { items: { kanji_id: string; meaning: boolean; reading: boolean; order: number | null; said: string | null }[] }
    expect(body.items.find((i) => i.kanji_id === 'KANJI_KURUMA')).toMatchObject({ meaning: true, reading: false, order: 1 })
    expect(body.items.find((i) => i.kanji_id === 'KANJI_TSUKI')).toMatchObject({ meaning: false, reading: true, order: 2 })
    expect(body.items.find((i) => i.kanji_id === 'KANJI_TAKE')).toMatchObject({ meaning: false, reading: false, order: null, said: 'tree?' })
  })

  it('saving with no marks records nothing recalled', async () => {
    const calls = mockApi({
      [`GET ${PATH}`]: () => json(form()),
      [`POST ${PATH}`]: () => json(form({ saved_at: savedAt, recalled: 0, items: kanji.map((k) => ({ kanji_id: k.kanji_id, meaning: false, reading: false, order: null, said: null })), anything_else: null })),
    })
    const user = userEvent.setup()
    renderApp(`/sessions/${SID}/recall`)
    await user.click(await screen.findByRole('button', { name: 'Save: nothing recalled' }))
    expect(await screen.findByRole('status')).toHaveTextContent(/Saved at \d\d:\d\d\. 0 of 5 kanji recalled\./)
    expect(calls.at(-1)!.key).toBe(`POST ${PATH}`)
  })

  it('a failed save keeps the marks and says so', async () => {
    mockApi({ [`GET ${PATH}`]: () => json(form()), [`POST ${PATH}`]: () => json({ detail: 'boom' }, 500) })
    const user = userEvent.setup()
    renderApp(`/sessions/${SID}/recall`)
    await screen.findByRole('heading', { name: 'Free recall' })
    await user.click(within(row('火')).getByRole('button', { name: /Meaning/ }))
    await user.click(screen.getByRole('button', { name: 'Save free recall' }))
    expect(await screen.findByRole('alert')).toHaveTextContent("Couldn't save. Your marks are still here.")
    expect(screen.getByRole('alert')).toHaveTextContent('500')
    expect(within(row('火')).getByRole('button', { name: /Meaning/ })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('status')).toHaveTextContent('1 of 5 kanji recalled. Not saved.')
  })

  it('opens with the last save', async () => {
    const items = kanji.map((k, i) => ({ kanji_id: k.kanji_id, meaning: i === 4, reading: false, order: i === 4 ? 1 : null, said: null }))
    mockApi({ [`GET ${PATH}`]: () => json(form({ saved_at: savedAt, recalled: 1, items, anything_else: 'said 山' })) })
    renderApp(`/sessions/${SID}/recall`)
    expect(await screen.findByRole('button', { name: 'Save changes' })).toBeInTheDocument()
    expect(within(row('石')).getByRole('button', { name: /Meaning/ })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByDisplayValue('said 山')).toBeInTheDocument()
  })
})

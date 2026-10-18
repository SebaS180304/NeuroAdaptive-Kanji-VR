import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { json, mockApi, offline } from '@/test/api'
import { renderApp } from '@/test/render'

const created = (body: unknown) => json({ ...(body as object), id: 'new-id' }, 201)

afterEach(() => vi.unstubAllGlobals())

async function fill(user: ReturnType<typeof userEvent.setup>, japanese: string) {
  await user.type(screen.getByLabelText('Participant code'), 'P07')
  await user.click(screen.getByLabelText(/Consent was obtained/))
  const q = (name: RegExp) => screen.getByRole('group', { name })
  await user.click(within(q(/How old are you/)).getByLabelText('25–34'))
  await user.click(within(q(/studied Japanese/)).getByLabelText(japanese))
  await user.click(within(q(/studied kanji/)).getByLabelText('No'))
  await user.click(within(q(/VR headset/)).getByLabelText('Prefer not to answer'))
  await user.click(within(q(/keep your attention/)).getByLabelText('Very often'))
}

describe('pre-test, register a participant (V1.10)', () => {
  it('keeps Save disabled until consent is confirmed', async () => {
    mockApi({})
    const user = userEvent.setup()
    renderApp('/pretest/register')
    await user.type(screen.getByLabelText('Participant code'), 'P07')
    const save = screen.getByRole('button', { name: 'Save registration' })
    expect(save).toBeDisabled()
    expect(screen.getByRole('status', { name: 'Confirm consent to continue' })).toBeInTheDocument()
    await user.click(screen.getByLabelText(/Consent was obtained/))
    expect(save).toBeEnabled()
    expect(screen.queryByRole('status', { name: 'Confirm consent to continue' })).toBeNull()
  })

  it('sends both parts in one POST, "Prefer not to answer" as null', async () => {
    const calls = mockApi({
      'POST /api/participants': created,
      'GET /api/participants/new-id': () => json({ id: 'new-id', external_code: 'P07' }),
      'GET /api/participants/new-id/pretest': () => json({ completed: false, completed_at: null, answered: 0,
        next: { kanji_id: 'K', kanji: '月' }, substitutions: [], flagged: [] }),
    })
    const user = userEvent.setup()
    renderApp('/pretest/register')
    await fill(user, 'No')
    await user.click(screen.getByRole('button', { name: 'Save registration' }))
    expect(calls[0]).toEqual({ key: 'POST /api/participants', body: {
      external_code: 'P07', consent_obtained: true, age_range: '25-34',
      previous_japanese_experience: false, previous_kanji_experience: false,
      previous_vr_experience: null, self_rated_attention_difficulty: 'VERY_OFTEN',
    } })
    // No notice applies: straight to the pre-test.
    expect(await screen.findByRole('img', { name: 'Kanji to answer' })).toBeInTheDocument()
  })

  it.each([
    ['Yes', 'For the researcher: previous Japanese study reported'],
    ['Prefer not to answer', 'For the researcher: previous Japanese study not reported'],
  ])('Japanese study "%s" shows the inclusion notice', async (answer, title) => {
    mockApi({ 'POST /api/participants': created })
    const user = userEvent.setup()
    renderApp('/pretest/register')
    await fill(user, answer)
    await user.click(screen.getByRole('button', { name: 'Save registration' }))
    const notice = await screen.findByRole('status', { name: title })
    expect(notice).toHaveTextContent('accepted by MIRAI on Oct 9')
    expect(within(notice).getByRole('link', { name: 'Continue to the pre-test' })).toHaveAttribute('href', '/pretest/new-id')
    expect(within(notice).getByRole('link', { name: 'Stop here' })).toHaveAttribute('href', '/pretest')
    expect(screen.getByRole('button', { name: 'Save registration' })).toBeDisabled()   // no edit after saving
  })

  it('says under the code when it is already registered', async () => {
    mockApi({ 'POST /api/participants': () => json({ detail: 'external_code already exists' }, 409) })
    const user = userEvent.setup()
    renderApp('/pretest/register')
    await fill(user, 'No')
    await user.click(screen.getByRole('button', { name: 'Save registration' }))
    const code = screen.getByLabelText('Participant code')
    expect(await screen.findByText('This code is already registered. Open it from the participant list instead.')).toBeInTheDocument()
    expect(code).toHaveAttribute('aria-invalid', 'true')
  })

  it('says when the backend cannot be reached, and nothing was saved', async () => {
    mockApi({ 'POST /api/participants': offline })
    const user = userEvent.setup()
    renderApp('/pretest/register')
    await fill(user, 'No')
    await user.click(screen.getByRole('button', { name: 'Save registration' }))
    const alert = await screen.findByRole('alert', { name: "Can't reach the backend" })
    expect(alert).toHaveTextContent('Nothing was saved.')
  })

  it('asks only for a code, never for who the participant is', () => {
    mockApi({})
    renderApp('/pretest/register')
    const fields = screen.getAllByRole('textbox').map((f) => f.getAttribute('aria-label') ?? (f as HTMLInputElement).labels?.[0]?.textContent)
    expect(fields).toEqual([expect.stringContaining('Participant code')])
    expect(screen.getByText(/Who the code belongs to stays outside this system/)).toBeInTheDocument()
  })
})

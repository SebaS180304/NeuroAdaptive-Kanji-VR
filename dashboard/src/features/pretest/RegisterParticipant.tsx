import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useId, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { ApiError, postJson, type Schemas } from '@/api/client'
import { Notice, OfflineNotice } from '@/components/Notice'

// V1.10 Register, artboard *V1.10 Register*: a centered form with no rail. Part 1 is
// the researcher's, Part 2 the participant's; one POST saves both, with no edit after.
// Options approved by Sebas on Oct 17 (tasks/plan.md); "Prefer not to answer" is null.

type Create = Schemas['ParticipantCreate']
type Created = Schemas['ParticipantRead']
type Value = string | boolean | null

const YES_NO: [string, Value][] = [['No', false], ['Yes', true], ['Prefer not to answer', null]]

const QUESTIONS: { field: keyof Create; text: string; optional?: true; options: [string, Value][] }[] = [
  {
    field: 'age_range',
    text: 'How old are you?',
    options: [['18–24', '18-24'], ['25–34', '25-34'], ['35–44', '35-44'], ['45 or older', '45+'], ['Prefer not to answer', null]],
  },
  { field: 'previous_japanese_experience', text: 'Have you studied Japanese before (classes, courses or self-study)?', options: YES_NO },
  { field: 'previous_kanji_experience', text: 'Have you studied kanji before?', options: YES_NO },
  { field: 'previous_vr_experience', text: 'Have you used a VR headset before?', options: YES_NO },
  {
    field: 'self_rated_attention_difficulty',
    text: 'How often is it hard for you to keep your attention on study tasks?',
    optional: true,
    options: [['Never', 'NEVER'], ['Rarely', 'RARELY'], ['Sometimes', 'SOMETIMES'], ['Often', 'OFTEN'],
      ['Very often', 'VERY_OFTEN'], ['Prefer not to answer', null]],
  },
]

const panel = 'col-span-16 m-0 rounded-(--radius-panel) border bg-(--color-surface) min-[1056px]:col-span-11'
const cta = 'type-body inline-flex h-10 items-center rounded-(--radius-pill) bg-(--color-cta) font-semibold text-(--color-on-cta) no-underline'

function PartHeading({ part, title, children }: { part: number; title: string; children: string }) {
  return (
    <div className="col-span-16 flex flex-col gap-2 min-[1056px]:col-span-5">
      <span className="type-caption text-(--color-text-muted)">Part {part} of 2</span>
      <h2 className="type-title m-0">{title}</h2>
      <p className="m-0 text-(--color-text-secondary)">{children}</p>
    </div>
  )
}

function Question({ q, picked, onPick }: { q: (typeof QUESTIONS)[number]; picked: number | undefined; onPick: (i: number) => void }) {
  const name = useId()
  return (
    <fieldset className="m-0 flex flex-col gap-3 border-0 border-b border-(--color-border-subtle) px-6 py-5 last:border-b-0">
      <legend className="type-lead float-left p-0 text-(--color-text)">
        {q.text}
        {q.optional && <span className="type-caption ml-2 text-(--color-text-muted)">Optional</span>}
      </legend>
      <div className="clear-both flex flex-wrap gap-2">
        {q.options.map(([label], i) => (
          <label
            key={label}
            className={`type-body relative inline-flex h-10 cursor-pointer items-center gap-2 rounded-(--radius-pill) px-5 has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-(--color-accent) ${
              picked === i
                ? 'border-2 border-(--color-accent) bg-(--color-accent-tint) font-semibold text-(--color-on-accent-tint)'
                : 'border border-(--color-border-strong) bg-(--color-surface) text-(--color-text)'
            }`}
          >
            <input type="radio" name={name} checked={picked === i} onChange={() => onPick(i)} className="sr-only" />
            {picked === i && <span aria-hidden="true">✓</span>}
            {label}
          </label>
        ))}
      </div>
    </fieldset>
  )
}

export function RegisterParticipant() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [code, setCode] = useState('')
  const [consent, setConsent] = useState(false)
  const [picked, setPicked] = useState<Partial<Record<keyof Create, number>>>({})

  const save = useMutation({
    mutationFn: (body: Create) => postJson<Created>('/participants', body),
    onSuccess: (p) => {
      void queryClient.invalidateQueries({ queryKey: ['research', 'participants'] })
      if (p.previous_japanese_experience === false) navigate(`/pretest/${p.id}`)
    },
  })
  const taken = save.error instanceof ApiError && save.error.status === 409
  const saved = save.data
  const locked = saved !== undefined || save.isPending

  function submit(e: React.FormEvent) {
    e.preventDefault()
    const answers = Object.fromEntries(
      QUESTIONS.map((q) => [q.field, picked[q.field] === undefined ? null : q.options[picked[q.field]!]![1]]),
    )
    save.mutate({ external_code: code.trim(), consent_obtained: consent, ...answers } as Create)
  }

  return (
    <div className="flex min-h-screen flex-col bg-(--color-bg)">
      <header className="flex flex-wrap items-center justify-between gap-4 bg-(--color-sidebar) px-8 py-4 text-(--color-sidebar-text)">
        <h1 className="type-title m-0">Register a participant</h1>
        <Link
          to="/pretest"
          className="type-body inline-flex h-8 items-center rounded-(--radius-pill) border border-(--color-on-dark-border) px-4 text-(--color-sidebar-text) no-underline"
        >
          Cancel
        </Link>
      </header>

      <form
        aria-label="Participant registration"
        onSubmit={submit}
        className="mx-auto grid w-full max-w-[1120px] grid-cols-16 gap-x-8 gap-y-12 px-8 pt-12 pb-16"
      >
        {save.error && !taken && <OfflineNotice className="col-span-16" />}

        <PartHeading part={1} title="Researcher">
          Use the code from your own list. Who the code belongs to stays outside this system.
        </PartHeading>
        <fieldset disabled={locked} className={`${panel} flex flex-col gap-6 p-6`}>
          <legend className="sr-only">Researcher details</legend>
          <div className="type-caption flex max-w-[360px] flex-col gap-2 text-(--color-text-muted)">
            <label htmlFor="register-code">Participant code</label>
            <input
              id="register-code"
              type="text"
              value={code}
              onChange={(e) => { setCode(e.target.value); save.reset() }}
              aria-invalid={taken}
              aria-describedby={taken ? 'register-code-error' : undefined}
              autoComplete="off"
              style={{ fontFamily: 'var(--font-mono)' }}
              className={`type-body h-10 rounded-(--radius-input) bg-(--color-surface) px-3 text-(--color-text) ${
                taken ? 'border-2 border-(--color-alert)' : 'border border-(--color-border-strong)'
              }`}
            />
            {taken && (
              <span id="register-code-error" className="flex items-center gap-2 text-(--color-alert)">
                <svg aria-hidden="true" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6">
                  <circle cx="8" cy="8" r="6.5" />
                  <path d="M8 4.5v4.5M8 11.2v.3" />
                </svg>
                This code is already registered. Open it from the participant list instead.
              </span>
            )}
          </div>
          <label className="flex items-start gap-3 text-(--color-text)">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              className="mt-px size-[18px] accent-(--color-accent)"
            />
            <span className="flex flex-col gap-1">
              <span className="font-medium">Consent was obtained</span>
              <span className="type-caption text-(--color-text-muted)">
                Required. Without it the participant can't be registered or take the pre-test. How consent is
                recorded: to be confirmed with MIRAI.
              </span>
            </span>
          </label>
        </fieldset>

        <PartHeading part={2} title="About you">
          The participant answers these at the keyboard. There are no right or wrong answers.
        </PartHeading>
        <fieldset disabled={locked} className={`${panel} p-0`}>
          <legend className="sr-only">About you</legend>
          {QUESTIONS.map((q) => (
            <Question key={q.field} q={q} picked={picked[q.field]} onPick={(i) => setPicked({ ...picked, [q.field]: i })} />
          ))}
        </fieldset>

        <div className="col-span-16 flex flex-col gap-4 min-[1056px]:col-span-11 min-[1056px]:col-start-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <p className="m-0 text-(--color-text-secondary)">Both parts are saved together and can't be edited later.</p>
            <button type="submit" disabled={!consent || !code.trim() || locked} className={`${cta} cursor-pointer border-0 px-6 disabled:cursor-not-allowed disabled:opacity-50`}>
              Save registration
            </button>
          </div>
          {!consent && (
            <Notice kind="warning" title="Confirm consent to continue">
              Save stays disabled, and the pre-test can't start, until consent is confirmed.
            </Notice>
          )}
        </div>

        {saved && saved.previous_japanese_experience !== false && <InclusionNotice participantId={saved.id} reported={saved.previous_japanese_experience === true} />}
      </form>
    </div>
  )
}

function InclusionNotice({ participantId, reported }: { participantId: string; reported: boolean }) {
  const titleId = useId()
  return (
    <section
      role="status"
      aria-labelledby={titleId}
      className="col-span-16 flex flex-col gap-4 rounded-(--radius-panel) bg-(--color-warn-tint) p-6 min-[1056px]:col-span-11 min-[1056px]:col-start-6"
    >
      <div className="flex items-start gap-3">
        <svg aria-hidden="true" width="20" height="20" viewBox="0 0 16 16" fill="none" stroke="var(--color-lal-high)" strokeWidth="1.6" className="mt-0.5 shrink-0">
          <path d="M8 1.8L15 14H1z" />
          <path d="M8 6.2v3.8M8 11.6v.3" />
        </svg>
        <div className="flex flex-col gap-1">
          <h2 id={titleId} className="type-subtitle m-0">
            For the researcher: previous Japanese study {reported ? 'reported' : 'not reported'}
          </h2>
          <p className="m-0 text-(--color-text-secondary)">
            {reported ? '' : 'The participant chose Prefer not to answer. '}The inclusion criterion "no previous study of
            Japanese" was accepted by MIRAI on Oct 9. The registration is saved either way. Decide whether to go on to the
            pre-test.
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-2 pl-8">
        <Link to={`/pretest/${participantId}`} className={`${cta} px-5`}>Continue to the pre-test</Link>
        <Link
          to="/pretest"
          className="type-body inline-flex h-10 items-center rounded-(--radius-pill) border border-(--color-lal-high) bg-transparent px-5 text-(--color-text) no-underline"
        >
          Stop here
        </Link>
      </div>
    </section>
  )
}

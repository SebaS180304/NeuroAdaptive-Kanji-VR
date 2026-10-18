import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { ApiError, getJson, postJson, type Schemas } from '@/api/client'
import { LoadingNotice, Notice, OfflineNotice } from '@/components/Notice'
import { formatDate } from '@/lib/format'

// V1.10 One kanji and Complete, artboards *V1.10 One kanji* and *Complete*: focus mode,
// no rail. The participant looks at this screen, so nothing here may show a correct
// reading or meaning, a set name or a substitute (design-rules.md §8). The API state
// carries substitutions and flagged kanji; they are never rendered.

type State = Schemas['PretestState']
type Answer = Schemas['PretestAnswer']
type Grade = Schemas['PretestGrade']
type SelfReport = Answer['self_report']

const ANSWERS: [SelfReport, string, string][] = [['NO', 'No', '1'], ['UNSURE', 'Not sure', '2'], ['YES', 'Yes', '3']]
const outlinePill = 'type-body inline-flex h-8 items-center rounded-(--radius-pill) border px-4 no-underline'
const cta = 'type-body inline-flex h-10 items-center rounded-(--radius-pill) border-0 bg-(--color-cta) px-6 font-semibold text-(--color-on-cta) no-underline'

function Header({ code, answered, paused, done }: { code?: string; answered?: number; paused?: boolean; done?: boolean }) {
  const Title = done ? 'span' : 'h1'
  return (
    <header className="flex flex-wrap items-center justify-between gap-4 border-b px-8 py-4">
      <div className="flex items-baseline gap-4">
        <Title className="type-title m-0">Kanji pre-test</Title>
        {code && <span className="type-mono text-(--color-text-muted)">{code}</span>}
      </div>
      <div className="flex items-center gap-4">
        {answered !== undefined && (
          <span aria-live="polite" className="text-(--color-text-secondary)">
            <span className="font-semibold">{answered}</span> answered
          </span>
        )}
        {paused !== undefined && (
          <Link to="/pretest" state={{ pausedAt: answered }} className={`${outlinePill} border-(--color-border-strong) text-(--color-text)`}>
            Pause
          </Link>
        )}
      </div>
    </header>
  )
}

function ResultPill({ correct }: { correct: boolean }) {
  return (
    <span
      className={`inline-flex h-7 items-center gap-2 self-start rounded-(--radius-pill) px-3 font-semibold ${
        correct ? 'bg-(--color-accent-tint) text-(--color-on-accent-tint)' : 'bg-(--color-alert-tint) text-(--color-on-alert-tint)'
      }`}
    >
      <svg aria-hidden="true" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d={correct ? 'M3 8.5l3.2 3.2L13 5' : 'M4 4l8 8M12 4l-8 8'} />
      </svg>
      {correct ? 'Correct' : 'Incorrect'}
    </span>
  )
}

function KanjiItem({ participantId, item, onSaved, onConflict }: {
  participantId: string
  item: NonNullable<State['next']>
  onSaved: (s: State) => void
  onConflict: () => void
}) {
  const [report, setReport] = useState<SelfReport | null>(null)
  const [typed, setTyped] = useState({ reading: '', meaning: '' })
  const [verdict, setVerdict] = useState<Grade | null>(null)   // auto-grade, then the researcher's flips

  // Keys 1-3 answer, except while typing a reading or meaning.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey || (e.target as HTMLElement).closest('input, textarea')) return
      const hit = ANSWERS.find(([, , key]) => key === e.key)
      if (hit) setReport(hit[0])
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const base = `/participants/${participantId}/pretest`
  const check = useMutation({
    mutationFn: () => postJson<Grade>(`${base}/check`, { kanji_id: item.kanji_id, typed_reading: typed.reading, typed_meaning: typed.meaning }),
    onSuccess: setVerdict,
  })
  const save = useMutation({
    mutationFn: (body: Answer) => postJson<State>(`${base}/responses`, body),
    onSuccess: onSaved,
    onError: (e) => { if (e instanceof ApiError && e.status === 409) onConflict() },
  })

  const needsTyping = report === 'UNSURE' || report === 'YES'
  const canSave = report === 'NO' || (needsTyping && verdict !== null)
  const type = (field: 'reading' | 'meaning', value: string) => {
    setTyped({ ...typed, [field]: value })
    setVerdict(null)
    check.reset()
  }
  function submit() {
    if (!report) return
    save.mutate(report === 'NO'
      ? ({ kanji_id: item.kanji_id, self_report: 'NO' } as Answer)   // the typed fields default to '' in the API
      : { kanji_id: item.kanji_id, self_report: report, typed_reading: typed.reading, typed_meaning: typed.meaning, ...verdict! })
  }
  const saveError = save.error && !(save.error instanceof ApiError && save.error.status === 409) ? save.error : null

  return (
    <>
      <main className="mx-auto flex w-full max-w-[880px] flex-1 flex-col items-center gap-8 px-8 py-12">
        <div role="img" aria-label="Kanji to answer" lang="ja" className="type-kanji-display text-(--color-text)">
          {item.kanji}
        </div>

        <fieldset className="m-0 flex flex-col items-center gap-4 border-0 p-0">
          <legend className="type-title mx-auto pb-4 text-center">Do you know this kanji?</legend>
          <div className="flex flex-wrap justify-center gap-3">
            {ANSWERS.map(([value, label, key]) => (
              <button
                key={value}
                type="button"
                aria-pressed={report === value}
                aria-keyshortcuts={key}
                onClick={() => setReport(value)}
                className={`inline-flex h-16 min-w-[168px] cursor-pointer flex-col items-center justify-center gap-0.5 rounded-(--radius-pill) px-6 text-[16px] leading-6 ${
                  report === value
                    ? 'border-2 border-(--color-accent) bg-(--color-accent-tint) font-semibold text-(--color-on-accent-tint)'
                    : 'border border-(--color-border-strong) bg-(--color-surface) font-medium text-(--color-text)'
                }`}
              >
                {label}
                <span className={`type-caption ${report === value ? 'text-(--color-on-accent-tint)' : 'text-(--color-text-muted)'}`}>Key {key}</span>
              </button>
            ))}
          </div>
        </fieldset>

        {needsTyping && (
          <>
            <div className="grid w-full grid-cols-2 gap-6">
              {(['reading', 'meaning'] as const).map((field) => (
                <div key={field} className="flex flex-col gap-2">
                  <label htmlFor={`pretest-${field}`} className="type-caption text-(--color-text-muted)">
                    {field === 'reading' ? 'Reading, in kana or romaji' : 'Meaning, in English'}
                  </label>
                  <input
                    id={`pretest-${field}`}
                    type="text"
                    autoComplete="off"
                    value={typed[field]}
                    onChange={(e) => type(field, e.target.value)}
                    style={{ fontSize: 18 }}
                    className="h-12 rounded-(--radius-input) border border-(--color-border-strong) bg-(--color-surface) px-4 text-(--color-text)"
                  />
                  {verdict && <ResultPill correct={field === 'reading' ? verdict.reading_correct : verdict.meaning_correct} />}
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={() => check.mutate()}
              className="type-body h-10 cursor-pointer rounded-(--radius-pill) border border-(--color-accent) bg-(--color-surface) px-6 font-medium text-(--color-on-accent-tint)"
            >
              {verdict ? 'Check again' : 'Check'}
            </button>
            {check.isError && <OfflineNotice onRetry={() => check.mutate()} className="w-full" />}
          </>
        )}
      </main>

      <section aria-label="Researcher controls" className="bg-(--color-sidebar) px-8 py-5 text-(--color-sidebar-text)">
        <div className="mx-auto flex max-w-[1376px] flex-wrap items-center gap-6">
          <span className="type-subtitle">Researcher</span>
          <span className="text-(--color-sidebar-muted)">Flip a result if the automatic check got it wrong.</span>
          {verdict && (
            <div className="flex flex-wrap gap-2">
              {(['reading', 'meaning'] as const).map((field) => {
                const key = field === 'reading' ? 'reading_correct' : 'meaning_correct'
                return (
                  <button
                    key={field}
                    type="button"
                    onClick={() => setVerdict({ ...verdict, [key]: !verdict[key] })}
                    className={`${outlinePill} cursor-pointer border-(--color-on-dark-border) bg-transparent text-(--color-sidebar-text)`}
                  >
                    Mark {field} {verdict[key] ? 'incorrect' : 'correct'}
                  </button>
                )
              })}
            </div>
          )}
          <div className="flex-1" />
          <button type="button" disabled={!canSave || save.isPending} onClick={submit} className={`${cta} cursor-pointer disabled:cursor-not-allowed disabled:opacity-50`}>
            Save and next
          </button>
        </div>
        {saveError && (
          <div className="mx-auto mt-4 max-w-[1376px]">
            {saveError instanceof ApiError && saveError.status === 422 ? (
              <Notice kind="error" title="Check both answers before saving">
                With Not sure or Yes, the reading and the meaning each need a result. Press Check, then save.
              </Notice>
            ) : (
              <OfflineNotice onRetry={submit} />
            )}
          </div>
        )}
      </section>
    </>
  )
}

function Done({ participantId, state }: { participantId: string; state: State }) {
  const at = new Date(state.completed_at!)
  const time = at.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
  return (
    <>
      <section aria-label="Finished" className="flex flex-col items-center gap-4 px-8 pt-16 pb-12 text-center">
        <h1 className="type-display m-0">That's all. Thank you.</h1>
        <p className="type-lead m-0 max-w-[480px] text-(--color-text-secondary)">
          You've answered every kanji. Please let the researcher know you're done.
        </p>
      </section>
      <div className="mx-auto flex w-full max-w-[1120px] flex-col gap-6 px-8 pb-16">
        <section aria-label="For the researcher" className="grid grid-cols-16 gap-x-8 gap-y-4 border-t-2 border-(--color-text) pt-6">
          <h2 className="type-subtitle col-span-16 m-0 min-[1056px]:col-span-5">For the researcher</h2>
          <dl className="col-span-16 m-0 grid grid-cols-[136px_minmax(0,1fr)] gap-x-4 gap-y-2 min-[1056px]:col-span-6">
            <dt className="text-(--color-text-muted)">Completed</dt>
            <dd className="m-0">{formatDate(state.completed_at!)}, {time}</dd>
            <dt className="text-(--color-text-muted)">Answered</dt>
            <dd className="m-0">{state.answered} kanji</dd>
          </dl>
          <div className="col-span-16 flex flex-col items-start gap-2 min-[1056px]:col-span-5">
            <p className="m-0 text-(--color-text-secondary)">
              Substitutions and flagged kanji are on the participant's page, away from this screen.
            </p>
            <Link
              to={`/participants/${participantId}`}
              className={`${outlinePill} border-(--color-accent) font-medium text-(--color-on-accent-tint)`}
            >
              Open participant page
            </Link>
          </div>
        </section>
        <div className="flex justify-end">
          <Link to="/pretest" className={cta}>Back to participants</Link>
        </div>
      </div>
    </>
  )
}

export function PretestRun() {
  const participantId = useParams().participantId!
  const queryClient = useQueryClient()
  const participant = useQuery({
    queryKey: ['participant', participantId],
    queryFn: () => getJson<Schemas['ParticipantRead']>(`/participants/${participantId}`),
  })
  const pretestKey = ['pretest', participantId]
  const pretest = useQuery({
    queryKey: pretestKey,
    queryFn: () => getJson<State>(`/participants/${participantId}/pretest`),
  })
  const [savedHere, setSavedHere] = useState(false)
  const [conflict, setConflict] = useState(false)
  const state = pretest.data
  // Opened with answers already saved, and nothing saved since: a resume.
  const notice = conflict ? 'conflict' : !savedHere && (state?.answered ?? 0) > 0 ? 'resumed' : null
  const notFound = participant.error instanceof ApiError && participant.error.status === 404

  return (
    <div className="flex min-h-screen flex-col bg-(--color-bg)">
      <Header
        code={participant.data?.external_code}
        answered={state?.answered}
        paused={state && !state.completed ? false : undefined}
        done={state?.completed}
      />

      {notFound ? (
        <Notice kind="warning" title="Participant not found" action={{ label: 'Back to participants', to: '/pretest' }} className="m-8">
          Check the link, or pick the participant from the list.
        </Notice>
      ) : pretest.isPending ? (
        <LoadingNotice title="Loading the pre-test…" className="m-8" />
      ) : pretest.error ? (
        <OfflineNotice onRetry={() => void pretest.refetch()} className="m-8" />
      ) : state!.completed ? (
        <Done participantId={participantId} state={state!} />
      ) : (
        <>
          {notice && (
            <div className="mx-auto w-full max-w-[880px] px-8 pt-8">
              {notice === 'conflict' ? (
                <Notice kind="info" title="This kanji was already saved">
                  It was answered from another tab or saved twice. The pre-test reloaded and continues from the next kanji.
                </Notice>
              ) : (
                <Notice kind="info" title="Picking up where you left off">
                  {state!.answered} kanji answered so far. This is the next one.
                </Notice>
              )}
            </div>
          )}
          <KanjiItem
            key={state!.next!.kanji_id}
            participantId={participantId}
            item={state!.next!}
            onSaved={(s) => {
              queryClient.setQueryData(pretestKey, s)
              void queryClient.invalidateQueries({ queryKey: ['research', 'participants'] })
              setSavedHere(true)
              setConflict(false)
            }}
            onConflict={() => {
              void pretest.refetch()
              setConflict(true)
            }}
          />
        </>
      )}
    </div>
  )
}

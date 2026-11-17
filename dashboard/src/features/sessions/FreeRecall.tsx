import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { ApiError, getJson, postJson, type Schemas } from '@/api/client'
import { LoadingNotice, Notice, OfflineNotice } from '@/components/Notice'
import { formatTime } from '@/lib/format'

// V1.12 Block R · Free recall (design-system.md, validated D-F6-226): focus mode, researcher-only.
// The participant speaks in the headset; the researcher marks here. No clock and nothing that paces it
// (D-F6-212): the researcher ends part 1 with the R key in Unity, never from this form. The portal's second
// and last write, under /sessions (D-F6-230 (1)).

type Form = Schemas['RecallForm']
type Item = Schemas['RecallItem']

// D-F6-225, word for word as V1.12 has it.
const WHAT_COUNTS =
  'Meaning: the meaning or a clear synonym, in any language. Reading: the Japanese reading, said close enough to ' +
  'recognise. Anything you\'re unsure about goes in "What they said", without a mark. There is no mark for a partial answer.'

const ORDINAL = ['1st', '2nd', '3rd', '4th', '5th']
const pill = 'type-body inline-flex h-8 items-center gap-2 rounded-(--radius-pill) border px-4'
const DAY = new Intl.DateTimeFormat('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })

function learned(iso: string | null | undefined): string {
  if (!iso) return '—'
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000)
  return `${DAY.format(new Date(iso))}, ${days === 0 ? 'today' : days === 1 ? '1 day ago' : `${days} days ago`}`
}

type Mark = { meaning: boolean; reading: boolean; first: number | null; said: string }

/** The order shown and sent: each marked kanji's rank by its first mark, 1..k without gaps. */
function orders(marks: Record<string, Mark>): Record<string, number> {
  const marked = Object.entries(marks).filter(([, m]) => m.meaning || m.reading).sort(([, a], [, b]) => a.first! - b.first!)
  return Object.fromEntries(marked.map(([id], i) => [id, i + 1]))
}

function fromSaved(form: Form): { marks: Record<string, Mark>; other: string } {
  const byId = Object.fromEntries((form.saved?.items ?? []).map((i) => [i.kanji_id, i]))
  const marks = Object.fromEntries(form.kanji.map((k) => {
    const i = byId[k.kanji_id]
    return [k.kanji_id, { meaning: !!i?.meaning, reading: !!i?.reading, first: i?.order ?? null, said: i?.said ?? '' }]
  }))
  return { marks, other: form.saved?.anything_else ?? '' }
}

function Toggle({ label, on, onClick }: { label: string; on: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={`${pill} cursor-pointer ${on
        ? 'border-(--color-accent) bg-(--color-accent-tint) font-semibold text-(--color-on-accent-tint)'
        : 'border-(--color-border-strong) bg-(--color-surface) text-(--color-text)'}`}
    >
      {on && (
        <svg aria-hidden="true" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M3 8.5l3.2 3.2L13 5" />
        </svg>
      )}
      {label}
    </button>
  )
}

function Recall({ form }: { form: Form }) {
  const queryClient = useQueryClient()
  const initial = fromSaved(form)
  const [marks, setMarks] = useState(initial.marks)
  const [other, setOther] = useState(initial.other)
  const [dirty, setDirty] = useState(false)
  const [next, setNext] = useState(1 + Math.max(0, ...Object.values(initial.marks).map((m) => m.first ?? 0)))
  const order = orders(marks)
  const recalled = Object.keys(order).length

  const save = useMutation({
    mutationFn: (body: Schemas['RecallSave']) => postJson<Form>(`/sessions/${form.session_id}/block-r/recall`, body),
    onSuccess: (data) => { queryClient.setQueryData(['recall', form.session_id], data); setDirty(false) },
  })

  const toggle = (id: string, field: 'meaning' | 'reading') => {
    const cur = marks[id]!
    const updated = { ...cur, [field]: !cur[field] }
    // A kanji takes its place with its first mark and keeps it while either mark is on; with no mark left it
    // loses it, and marked again it goes last (Sebas, 17 Nov; V1.12 said "kept if switched off and on").
    if (!updated.meaning && !updated.reading) updated.first = null
    else if (updated.first === null) { updated.first = next; setNext(next + 1) }
    setMarks({ ...marks, [id]: updated })
    setDirty(true)
  }

  const submit = () => {
    const items: Item[] = form.kanji.map((k) => {
      const m = marks[k.kanji_id]!
      return { kanji_id: k.kanji_id, meaning: m.meaning, reading: m.reading, order: order[k.kanji_id] ?? null, said: m.said.trim() || null }
    })
    save.mutate({ items, anything_else: other.trim() || null })
  }

  const saved = form.saved
  const failed = save.isError
  const status = failed
    ? `${recalled} of 5 kanji recalled. Not saved.`
    : saved && !dirty
      ? `Saved at ${formatTime(saved.saved_at)}. ${saved.recalled} of 5 kanji recalled. Changes are saved again with their time.`
      : recalled === 0 ? 'Nothing marked. Not saved yet.' : `${recalled} of 5 kanji recalled. Not saved yet.`
  const dot = failed ? 'bg-(--color-alert)' : saved && !dirty ? 'bg-(--color-accent)' : 'border border-(--color-border-strong)'
  const label = saved ? 'Save changes' : recalled === 0 ? 'Save: nothing recalled' : 'Save free recall'
  const code = save.error instanceof ApiError ? `HTTP ${save.error.status}` : save.error ? 'NETWORK' : ''

  return (
    <div className="flex min-h-screen flex-col bg-(--color-bg) text-(--color-text)">
      <header className="flex flex-wrap items-center justify-between gap-4 bg-(--color-sidebar) px-8 py-4 text-(--color-sidebar-text)">
        <div className="flex flex-wrap items-baseline gap-4">
          <h1 className="type-title m-0">Free recall</h1>
          <span className="type-mono">{form.participant_code}</span>
          <span className="type-caption text-(--color-sidebar-muted)">Visit {form.visit_number}, block R part 1 of 3</span>
        </div>
        <Link to={`/sessions/${form.session_id}`} className={`${pill} border-(--color-on-dark-border) text-(--color-sidebar-text) no-underline`}>
          Back to the session
        </Link>
      </header>

      <main className="mx-auto grid w-full max-w-[1120px] flex-1 grid-cols-16 gap-x-8 gap-y-8 px-8 pt-12 pb-16">
        <section className="col-span-16 flex flex-col gap-6 min-[1056px]:col-span-5">
          <h2 className="type-title m-0">What they remember</h2>
          <p className="m-0 text-(--color-text-secondary)">
            The participant answers out loud, in the headset. Mark each thing as they say it. Don't repeat, correct or
            hint, and don't ask about a kanji they haven't mentioned.
          </p>
          <dl className="m-0 grid grid-cols-[96px_1fr] gap-x-4 gap-y-2">
            <dt className="type-caption text-(--color-text-muted)">Evaluates</dt>
            <dd className="m-0"><Link to={`/sessions/${form.evaluated_session_id}`} className="type-mono text-(--color-accent) hover:text-(--color-accent-hover)">{form.evaluated_session_id.slice(0, 8)}</Link></dd>
            <dt className="type-caption text-(--color-text-muted)">Set</dt>
            <dd className="m-0">{form.evaluated_kanji_set ?? '—'}</dd>
            <dt className="type-caption text-(--color-text-muted)">Learned</dt>
            <dd className="m-0">{learned(form.learned_at)}</dd>
          </dl>
          <div className="flex flex-col gap-2 rounded-[2px] bg-(--color-explain-bg) p-4">
            <span className="type-caption text-(--color-text-muted)">On the board in VR</span>
            {form.board_text.map((t) => <p key={t} className="m-0">{t}</p>)}
          </div>
          <div className="flex flex-col gap-1">
            <span className="type-caption text-(--color-text-muted)">What counts</span>
            <p className="m-0">{WHAT_COUNTS}</p>
          </div>
        </section>

        <section className="col-span-16 flex flex-col gap-6 min-[1056px]:col-span-11">
          <table className="w-full border-collapse rounded-[2px] border border-(--color-border) bg-(--color-surface)">
            <caption className="sr-only">Kanji of set {form.evaluated_kanji_set}</caption>
            <thead>
              <tr className="type-caption text-(--color-text-muted)">
                <th scope="col" className="px-6 py-4 text-left font-normal">Kanji</th>
                <th scope="col" className="py-4 text-left font-normal">Taught as</th>
                <th scope="col" className="py-4 text-left font-normal">Recalled</th>
                <th scope="col" className="px-6 py-4 text-right font-normal">Order</th>
              </tr>
            </thead>
            <tbody>
              {form.kanji.map((k) => {
                const m = marks[k.kanji_id]!
                return (
                  <tr key={k.kanji_id} className="border-t border-(--color-border-subtle) align-top">
                    <td className="w-[56px] px-6 py-4"><span lang="ja" className="font-(family-name:--font-kanji) text-[32px] leading-10 font-medium">{k.kanji}</span></td>
                    <td className="w-[128px] py-4">
                      <div className="type-body">{k.meaning}</div>
                      <div lang="ja" className="type-caption text-(--color-text-secondary)">{k.reading}</div>
                    </td>
                    <td className="py-4">
                      <div className="flex flex-wrap gap-2">
                        <Toggle label="Meaning" on={m.meaning} onClick={() => toggle(k.kanji_id, 'meaning')} />
                        <Toggle label="Reading" on={m.reading} onClick={() => toggle(k.kanji_id, 'reading')} />
                      </div>
                      <label className="mt-3 flex flex-col gap-1">
                        <span className="type-caption text-(--color-text-muted)">What they said <span className="sr-only">for {k.meaning}</span></span>
                        <input
                          type="text"
                          placeholder="Optional"
                          value={m.said}
                          onChange={(e) => { const said = e.target.value; setMarks((all) => ({ ...all, [k.kanji_id]: { ...all[k.kanji_id]!, said } })); setDirty(true) }}
                          className="h-8 rounded-[4px] border border-(--color-border-strong) bg-(--color-surface) px-2 placeholder:text-(--color-text-muted)"
                        />
                      </label>
                    </td>
                    <td className="w-[48px] px-6 py-4 text-right">
                      <span className="type-mono type-caption text-(--color-text-muted)">{order[k.kanji_id] ? ORDINAL[order[k.kanji_id]! - 1] : '—'}</span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>

          <label className="flex flex-col gap-1">
            <span className="type-caption text-(--color-text-muted)">
              Anything else they said: other kanji, words or guesses that don't match one of these five
            </span>
            <textarea
              rows={3}
              value={other}
              onChange={(e) => { setOther(e.target.value); setDirty(true) }}
              className="rounded-[4px] border border-(--color-border-strong) bg-(--color-surface) p-2"
            />
          </label>

          {failed && (
            <Notice kind="error" title="Couldn't save. Your marks are still here.">
              Check that the backend is running, then save again. <span className="type-mono">{code}</span>
            </Notice>
          )}

          <footer className="flex flex-wrap items-start justify-between gap-4 border-t border-(--color-border) pt-6">
            <p role="status" className="m-0 flex items-center gap-2">
              <span aria-hidden="true" className={`inline-block size-2 rounded-full ${dot}`} />
              {status}
            </p>
            <div className="flex flex-col items-end gap-2">
              <button
                type="button"
                onClick={submit}
                disabled={save.isPending}
                className="type-body inline-flex h-10 cursor-pointer items-center rounded-(--radius-pill) border-0 bg-(--color-cta) px-6 font-semibold text-(--color-on-cta)"
              >
                {label}
              </button>
              <span className="type-caption text-(--color-text-muted)">
                Saving with no marks records that nothing was recalled. Leaving without saving records nothing for this part.
              </span>
            </div>
          </footer>
        </section>
      </main>
    </div>
  )
}

export function FreeRecall() {
  const { sessionId = '' } = useParams()
  const { data, error, isPending, refetch } = useQuery({
    queryKey: ['recall', sessionId],
    queryFn: () => getJson<Form>(`/sessions/${sessionId}/block-r/recall`),
    retry: false,
  })
  if (isPending) return <LoadingNotice title="Loading the free recall" className="m-8" />
  if (error instanceof ApiError && error.status === 409)
    return <Notice kind="neutral" title="This session has no block R" className="m-8" action={{ label: 'Back to the session', to: `/sessions/${sessionId}` }} />
  if (error || !data) return <OfflineNotice onRetry={() => refetch()} className="m-8" />
  // Keyed by the save time, so a new save from elsewhere resets the marks to what is stored.
  return <Recall key={data.saved?.saved_at ?? 'new'} form={data} />
}

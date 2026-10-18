import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useLocation } from 'react-router'
import { getJson, type Schemas } from '@/api/client'
import { LoadingNotice, Notice, OfflineNotice } from '@/components/Notice'
import { PretestChip } from '@/components/PretestChip'
import { formatDate } from '@/lib/format'

// V1.10 Pick a participant, artboard *V1.10 Pick*. Same data as the participant list.

type Participant = Schemas['ResearchParticipant']

const pill = 'type-body inline-flex h-8 items-center rounded-(--radius-pill) px-4 font-medium no-underline'
const ACTION: Record<Participant['pretest_status'], [string, string]> = {
  NOT_STARTED: ['Start', `${pill} bg-(--color-cta) text-(--color-on-cta)`],
  IN_PROGRESS: ['Resume', `${pill} border border-(--color-accent) bg-(--color-surface) text-(--color-on-accent-tint)`],
  COMPLETED: ['View result', `${pill} border border-(--color-border-strong) bg-(--color-surface) text-(--color-text)`],
}

const th = 'type-caption h-10 border-b font-medium text-(--color-text-muted)'

export function PretestPick() {
  const { data, error, isPending, refetch } = useQuery({
    queryKey: ['research', 'participants'],
    queryFn: () => getJson<Participant[]>('/research/participants'),
  })
  const pausedAt = (useLocation().state as { pausedAt?: number } | null)?.pausedAt
  const [code, setCode] = useState('')
  const query = code.trim()
  const rows = (data ?? []).filter((p) => p.external_code.toLowerCase().includes(query.toLowerCase()))

  return (
    <>
      <header className="col-span-16 flex flex-col gap-2 min-[1056px]:col-span-11">
        <h1 className="type-display m-0">Kanji pre-test</h1>
        <p className="type-lead m-0 max-w-[640px] text-(--color-text-secondary)">
          Run it with the participant before their first visit. Unity can't start a session for anyone whose pre-test
          isn't complete.
        </p>
      </header>
      <div className="col-span-16 flex items-end justify-end min-[1056px]:col-span-5">
        <Link
          to="/pretest/register"
          className="type-body inline-flex h-10 items-center rounded-(--radius-pill) bg-(--color-cta) px-6 font-semibold text-(--color-on-cta) no-underline"
        >
          Register a participant
        </Link>
      </div>

      <form aria-label="Find a participant" className="col-span-16 flex items-end gap-4 min-[1056px]:col-span-7" onSubmit={(e) => e.preventDefault()}>
        <label className="type-caption flex flex-1 flex-col gap-2 text-(--color-text-muted)">
          Participant code
          <input
            type="search"
            placeholder="External code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="type-body h-10 rounded-(--radius-input) border border-(--color-border-strong) bg-(--color-surface) px-3 text-(--color-text)"
          />
        </label>
      </form>
      <p className="type-caption col-span-16 m-0 self-end text-(--color-text-muted) min-[1056px]:col-span-9">
        A completed pre-test opens read-only. It can't be redone or edited.
      </p>

      {pausedAt !== undefined && <Notice kind="info" title={`Paused at ${pausedAt} answered`} className="col-span-16" />}
      {isPending && <LoadingNotice title="Loading the pre-test…" className="col-span-16" />}
      {error && <OfflineNotice onRetry={() => void refetch()} className="col-span-16" />}
      {data && query && rows.length === 0 && (
        <Notice kind="warning" title={`No participant with code ${query}`} action={{ label: 'Register', to: '/pretest/register' }} className="col-span-16">
          Check the code against your list, or register them as a new participant.
        </Notice>
      )}

      {data && rows.length > 0 && (
        <section
          aria-label="Participants and pre-test status"
          className="col-span-16 overflow-x-auto rounded-(--radius-panel) border bg-(--color-surface)"
        >
          <table className="type-body w-full min-w-[880px] border-collapse">
            <thead>
              <tr>
                <th scope="col" className={`${th} px-6 text-left`}>Participant</th>
                <th scope="col" className={`${th} px-4 text-left`}>Registered</th>
                <th scope="col" className={`${th} px-4 text-left`}>Pre-test</th>
                <th scope="col" className={`${th} px-6 text-right`}><span className="sr-only">Action</span></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((p) => {
                const [label, cls] = ACTION[p.pretest_status]
                return (
                  <tr key={p.id} className="border-b border-(--color-border-subtle)">
                    <th scope="row" className="type-mono h-14 px-6 text-left font-normal">{p.external_code}</th>
                    <td className="px-4 whitespace-nowrap">{formatDate(p.created_at)}</td>
                    <td className="px-4"><PretestChip p={p} /></td>
                    <td className="px-6 text-right">
                      <Link to={`/pretest/${p.id}`} className={cls}>{label}</Link>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </section>
      )}
    </>
  )
}

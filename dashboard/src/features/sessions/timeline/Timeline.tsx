import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { getJson, type Schemas } from '@/api/client'
import { LoadingNotice, OfflineNotice } from '@/components/Notice'
import { buildLanes, clock, s7Window } from './lanes'
import { AXIS_HEIGHT, PLOT_INSET, TimelineChart } from './TimelineChart'

// V1.3 Timeline, artboard *Session View*: lanes 1-4 (Game Flow, environment,
// assistance, trials) over session_elapsed_ms, with zoom and pan.

type Timeline = Schemas['SessionTimeline']

const pillBase = 'type-body inline-flex h-8 items-center justify-center rounded-(--radius-pill) border disabled:opacity-40'
const pill = (on = false) =>
  `${pillBase} ${on
    ? 'border-(--color-accent) bg-(--color-accent-tint) font-medium text-(--color-on-accent-tint)'
    : 'border-(--color-border-strong) bg-(--color-surface) text-(--color-text)'}`

export function Timeline({ sessionId, condition }: { sessionId: string; condition: string }) {
  const { data, error, isPending, refetch } = useQuery({
    queryKey: ['research', 'sessions', sessionId, 'timeline'],
    queryFn: () => getJson<Timeline>(`/research/sessions/${sessionId}/timeline`),
  })
  return (
    <section
      aria-label="Session timeline"
      className="col-span-16 flex flex-col gap-4 rounded-(--radius-panel) border bg-(--color-surface) p-6"
    >
      {isPending && <LoadingNotice title="Loading the timeline…" />}
      {error && <OfflineNotice onRetry={() => void refetch()} />}
      {data && <Lanes data={data} condition={condition} />}
    </section>
  )
}

function Lanes({ data, condition }: { data: Timeline; condition: string }) {
  const lanes = useMemo(() => buildLanes(data, condition), [data, condition])
  const end = data.session_end_ms ?? 0
  const s7 = s7Window(data)
  const [w, setW] = useState<[number, number]>([0, end])
  const same = (a: [number, number], b: [number, number] | null) => !!b && Math.abs(a[0] - b[0]) < 1 && Math.abs(a[1] - b[1]) < 1

  // Halve or double the shown span around its middle, within the session.
  function zoom(factor: number) {
    const mid = (w[0] + w[1]) / 2
    const half = Math.min(Math.max(((w[1] - w[0]) * factor) / 2, 2500), end / 2)
    const from = Math.min(Math.max(mid - half, 0), end - 2 * half)
    setW([from, from + 2 * half])
  }

  const height = lanes.reduce((h, l) => h + l.height, 0)
  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="type-title m-0">Timeline</h2>
        <div className="flex items-center gap-2">
          <button type="button" aria-label="Zoom out" onClick={() => zoom(2)} disabled={same(w, [0, end])} className={`${pill()} w-8`}>−</button>
          <button type="button" aria-label="Zoom in" onClick={() => zoom(0.5)} disabled={end === 0} className={`${pill()} w-8`}>+</button>
          <button type="button" aria-pressed={same(w, [0, end])} onClick={() => setW([0, end])} className={`${pill(same(w, [0, end]))} px-4`}>
            Whole session
          </button>
          <button
            type="button"
            aria-pressed={same(w, s7)}
            onClick={() => s7 && setW(s7)}
            disabled={!s7}
            title={s7 ? undefined : 'This session did not reach S7'}
            className={`${pill(same(w, s7))} px-4`}
          >
            Only S7
          </button>
        </div>
      </div>

      <p className="sr-only" aria-live="polite">Showing {clock(w[0])} to {clock(w[1])} of the session.</p>

      <div className="grid grid-cols-[184px_minmax(0,1fr)]">
        <div>
          {lanes.map((l) => (
            <div key={l.key} style={{ height: l.height }} className="flex flex-col justify-center border-t border-(--color-border-subtle) pr-4">
              {/* 16 px leading: label and hint fit a 32 px lane. */}
              <span className="type-body leading-4 font-medium">{l.label}</span>
              <span className="type-caption text-(--color-text-muted)">{l.hint}</span>
            </div>
          ))}
        </div>
        <div className="relative" style={{ height: height + AXIS_HEIGHT }}>
          {lanes.map((l) => (
            <div key={l.key} style={{ height: l.height, paddingLeft: PLOT_INSET }} className="type-caption flex items-center border-t border-(--color-border-subtle) text-(--color-text-muted)">
              {l.note}
            </div>
          ))}
          {end > 0 && <TimelineChart lanes={lanes} end={end} window={w} onWindow={setW} />}
        </div>
      </div>

      <div className="type-caption flex flex-wrap gap-6 text-(--color-text-muted)">
        <span className="flex items-center gap-2"><span aria-hidden="true" className="h-2 w-4 bg-(--color-trial-correct)" />Correct</span>
        <span className="flex items-center gap-2"><span aria-hidden="true" className="h-2 w-4" style={{ background: 'var(--hatch-trial-incorrect)' }} />Incorrect</span>
        <span className="flex items-center gap-2"><span aria-hidden="true" className="h-2 w-4 border border-(--color-border-strong)" />Not answered</span>
        <span className="flex items-center gap-2"><span aria-hidden="true" className="h-2 w-4 border border-dashed border-(--color-border-strong)" />Not completed (session ended)</span>
        <span className="flex items-center gap-2"><span aria-hidden="true" className="size-2.5 rotate-45 bg-(--color-accent)" />Change applied</span>
        <span className="flex items-center gap-2"><span aria-hidden="true" className="size-2.5 rotate-45 border-2 border-(--color-accent)" />Change skipped by Unity</span>
        <span className="flex items-center gap-2"><span aria-hidden="true" className="h-2 w-6 bg-(--color-accent-tint)" />Cooldown</span>
      </div>
    </>
  )
}

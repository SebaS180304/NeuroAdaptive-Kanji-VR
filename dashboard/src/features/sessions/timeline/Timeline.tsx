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

      <Legend />
    </>
  )
}

// design-system.md "Lanes 5-8 marks": every mark, grouped by lane in lane order. Swatches
// are CSS copies of the canvas marks.
const HATCH = { background: 'var(--hatch-trial-incorrect)' }
const LEGEND: [string, [string, string, object?][]][] = [
  ['Game Flow', [['S7', 'h-2 w-4 bg-(--color-text)'], ['Other states', 'h-2 w-4 bg-(--color-state-neutral)']]],
  ['Environment', [
    ['Low', 'h-2 w-4 bg-(--color-esl-low)'], ['Medium', 'h-2 w-4 bg-(--color-esl-medium)'], ['High', 'h-2 w-4 bg-(--color-esl-high)'],
    ['Focus', 'h-2 w-4 border border-(--color-esl-high) bg-(--color-surface)'], ['Minimal or Baseline', 'h-2 w-4 bg-(--color-state-neutral)'],
  ]],
  ['Assistance', [
    ['Low', 'h-2 w-4 bg-(--color-lal-low)'], ['Medium', 'h-2 w-4 bg-(--color-lal-medium)'], ['High', 'h-2 w-4 bg-(--color-lal-high)'],
    ['Off', 'h-px w-4 bg-(--color-border-strong)'],
  ]],
  ['Trials', [
    ['Correct', 'h-2 w-4 bg-(--color-trial-correct)'], ['Incorrect', 'h-2 w-4', HATCH],
    ['Not answered', 'h-2 w-4 border border-(--color-border-strong)'],
    ['Not completed (session ended)', 'h-2 w-4 border border-dashed border-(--color-border-strong)'],
  ]],
  ['Hints', [['Hint requested', 'size-2 rounded-full bg-(--color-lal-high)'], ['Proactive cue', 'size-2 rounded-full border-2 border-(--color-lal-high)']]],
  ['Peripherals', [
    ['Peripheral event', 'h-2 w-0.5 bg-(--color-peripheral)'], ['Dwell', 'h-1 w-4 bg-(--color-distractor)'],
    ['Orienting', 'h-2 w-0.5 bg-(--color-distractor)'],
  ]],
  ['Head-away', [
    ['Episode', 'h-2 w-4 bg-(--color-headaway)'],
    ['No return (session ended)', 'h-2 w-4 border border-dashed border-(--color-headaway)'],
  ]],
  ['Adaptations', [
    ['Change applied', 'size-2.5 rotate-45 bg-(--color-accent)'],
    ['Change skipped by Unity', 'size-2.5 rotate-45 border-2 border-(--color-accent)'],
    ['No answer from Unity', 'size-2.5 rotate-45 border-2 border-dashed border-(--color-accent)'],
    ['Cooldown', 'h-2 w-6 bg-(--color-accent-tint)'],
    ['Outcome positive', 'size-1.5 rounded-full bg-(--color-outcome-positive)'],
    ['Outcome neutral', 'size-1.5 rounded-full border border-(--color-text-muted)'],
    ['Outcome negative', 'size-1.5 bg-(--color-outcome-negative)'],
    ['Outcome uncertain', 'size-1.5 border border-(--color-text-muted)'],
  ]],
]

function Legend() {
  return (
    <ul aria-label="Legend" className="type-caption m-0 flex list-none flex-wrap gap-x-8 gap-y-3 p-0 text-(--color-text-muted)">
      {LEGEND.map(([lane, items]) => (
        <li key={lane} className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <h3 className="type-caption m-0 font-medium text-(--color-text-secondary)">{lane}</h3>
          <ul className="m-0 flex list-none flex-wrap gap-x-4 gap-y-1 p-0">
            {items.map(([label, swatch, style]) => (
              <li key={label} className="flex items-center gap-2">
                <span aria-hidden="true" className={`shrink-0 ${swatch}`} style={style} />
                {label}
              </li>
            ))}
          </ul>
        </li>
      ))}
    </ul>
  )
}

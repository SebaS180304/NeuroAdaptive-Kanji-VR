import { useQuery } from '@tanstack/react-query'
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { getJson, type Schemas } from '@/api/client'
import { clippedLastSecond, columns, nowLabel, WINDOW_MS } from './traceMath'

// V1.13 "Channel traces" (design-system.md, Validated D-F6-301 (5); option A, between Sync and Events). Display only:
// live.py's min/max per 40 ms bin of the causally filtered signal (1–40 Hz, 60 Hz notch), 20 s, a fixed common scale,
// «Now» = µV RMS of the last second (D-F6-297 (2)). Its own query every 250 ms with ?since=, a 20 s ring on the client.

type Traces = Schemas['LiveTraces']
type Bin = Schemas['LiveTraceBin']
export type ChannelStatus = 'OK' | 'Watch' | 'Bad' | 'No data'

const POLL_MS = 250
const SCALES = [50, 100, 200, 500] as const
const LANE_H = 28
const GAP = 2
const GUTTER = 32
const VALUE_W = 54
const STALE_S = 5
const MAX_PEAK_LABELS = 4

const css = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#888'
const STATUS_TOKEN: Record<ChannelStatus, string> = {
  OK: '--color-accent', Watch: '--color-quality-warn', Bad: '--color-quality-error', 'No data': '--color-border-strong',
}

function useRing(sessionId: string) {
  const [bins, setBins] = useState<Bin[]>([])
  const since = useRef(-1)   // one query key: the cursor lives here, not in the key (4 fetches a second)
  const q = useQuery({
    queryKey: ['live-traces', sessionId],
    queryFn: () => getJson<Traces>(`/research/sessions/${sessionId}/live/traces?since=${since.current}`),
    refetchInterval: POLL_MS,
  })
  useEffect(() => {
    const got = q.data?.bins.filter((b) => b.t_ms > since.current)
    if (!got?.length) return
    since.current = got[got.length - 1]!.t_ms
    setBins((old) => {
      const all = [...old, ...got]
      const keep = all[all.length - 1]!.t_ms - WINDOW_MS - 1000
      return all.filter((b) => b.t_ms >= keep)
    })
  }, [q.data])
  return { data: q.data, bins }
}

export function ChannelTraces({ sessionId, status, ended }:
  { sessionId: string; status: Record<string, ChannelStatus>; ended: boolean }) {
  const { data, bins } = useRing(sessionId)
  const [scale, setScale] = useState<number>(100)
  const box = useRef<HTMLDivElement>(null)
  const canvas = useRef<HTMLCanvasElement>(null)
  const [width, setWidth] = useState(378)
  useLayoutEffect(() => {
    const el = box.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(([e]) => setWidth(Math.max(200, Math.floor(e!.contentRect.width))))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const labels = useMemo(() => data?.labels ?? ['Fp1', 'F3', 'Fz', 'F4', 'Cz', 'P3', 'Pz', 'P4'], [data?.labels])
  const nowMs = bins.length ? bins[bins.length - 1]!.t_ms : 0
  const plotW = Math.max(100, width - GUTTER - VALUE_W)
  const height = labels.length * (LANE_H + GAP)
  const age = data?.now?.age_s as number | undefined

  useEffect(() => {
    const c = canvas.current
    const g = c?.getContext?.('2d')
    if (!c || !g || !data?.on) return
    const dpr = window.devicePixelRatio || 1
    c.width = plotW * dpr
    c.height = height * dpr
    g.setTransform(dpr, 0, 0, dpr, 0, 0)
    g.clearRect(0, 0, plotW, height)
    g.lineWidth = 1
    g.strokeStyle = css('--color-border-subtle')
    for (let s = 0; s <= 20; s++) {   // 1 s grid
      const x = Math.round((s / 20) * plotW) + 0.5
      g.beginPath(); g.moveTo(x, 0); g.lineTo(x, height); g.stroke()
    }
    const t0 = nowMs - WINDOW_MS
    const xOf = (ms: number) => ((ms - t0) / WINDOW_MS) * plotW
    g.font = `600 10px ${css('--font-sans') || 'sans-serif'}`
    for (const st of data.stages) {   // stage changes: solid secondary line with the code
      const ms = (st as { ms: number }).ms
      if (ms < t0 || ms > nowMs) continue
      g.strokeStyle = css('--color-text-secondary'); g.setLineDash([])
      g.beginPath(); g.moveTo(xOf(ms) + 0.5, 0); g.lineTo(xOf(ms) + 0.5, height); g.stroke()
      g.fillStyle = css('--color-text-secondary'); g.fillText(String((st as { state: string }).state).slice(0, 2), xOf(ms) + 3, 10)
    }
    const taps = ((data.now?.taps as number[] | undefined) ?? [])
    taps.forEach((ms, i) => {   // Unity tap markers: dashed text line, «Tap n»
      if (ms < t0 || ms > nowMs) return
      g.strokeStyle = css('--color-text'); g.setLineDash([3, 3])
      g.beginPath(); g.moveTo(xOf(ms) + 0.5, 0); g.lineTo(xOf(ms) + 0.5, height); g.stroke()
      g.setLineDash([]); g.fillStyle = css('--color-text'); g.fillText(`Tap ${i + 1}`, xOf(ms) + 3, 20)
    })
    let peaks = 0
    labels.forEach((label, ch) => {
      const top = ch * (LANE_H + GAP)
      const mid = top + LANE_H / 2
      const yOf = (v: number) => mid - (v / scale) * (LANE_H / 2)
      g.strokeStyle = css('--color-border-subtle'); g.setLineDash([])
      g.beginPath(); g.moveTo(0, mid + 0.5); g.lineTo(plotW, mid + 0.5); g.stroke()
      const excluded = data.excluded === label
      g.strokeStyle = ended || excluded ? css('--color-border-strong') : css(STATUS_TOKEN[status[label] ?? 'OK'])
      g.beginPath()
      columns(bins, ch, plotW, nowMs).forEach((c, x) => {
        if (!c) return
        const hi = Math.max(top, yOf(c.hi)), lo = Math.min(top + LANE_H, yOf(c.lo))
        g.moveTo(x + 0.5, hi); g.lineTo(x + 0.5, Math.max(lo, hi + 1))
        if ((c.hi > scale || c.lo < -scale) && !excluded) {   // clipped: a 2 px warn tick, at most 4 peak labels
          g.save(); g.fillStyle = css('--color-quality-warn'); g.fillRect(x, c.hi > scale ? top : top + LANE_H - 2, 1, 2); g.restore()
          if (peaks < MAX_PEAK_LABELS && x > plotW - 60) {
            peaks++
            const v = c.hi > scale ? c.hi : c.lo
            g.save(); g.fillStyle = css('--color-quality-warn'); g.font = '600 10px monospace'
            g.fillText(Math.abs(v) >= 1000 ? `${(v / 1000).toFixed(1)} mV` : `${Math.round(v)} µV`, Math.min(x, plotW - 48), top + 10)
            g.restore()
          }
        }
      })
      g.stroke()
    })
    g.strokeStyle = css('--color-text'); g.setLineDash([])   // «Now» at the right edge
    g.beginPath(); g.moveTo(plotW - 0.5, 0); g.lineTo(plotW - 0.5, height); g.stroke()
  }, [bins, data, scale, plotW, height, labels, nowMs, status, ended])

  if (data && !data.on) {
    return (
      <section aria-label="Channel traces" className="flex shrink-0 flex-col rounded-(--radius-panel) border border-(--color-border) bg-(--color-surface) px-5 py-4">
        <h2 className="type-subtitle font-heading">Channel traces</h2>
        <p className="type-body mt-2">Channel traces are off for this session.</p>
        <p className="type-caption text-(--color-text-muted)">The raw signal is in the AURA software.</p>
      </section>
    )
  }
  const cut = age != null && age > STALE_S
  const caption = ended ? (age != null ? 'Last data' : 'Waiting') : !data || !bins.length ? 'Waiting'
    : cut ? `No data for ${Math.round(age!)} s` : 'Live, every 0.25 s'
  const rms = (data?.now?.rms_uv as (number | null)[] | undefined) ?? []
  return (
    <section aria-label="Channel traces, 8 channels, last 20 seconds"
      className={`flex shrink-0 flex-col rounded-(--radius-panel) border px-5 py-4 ${ended ? 'border-dashed border-(--color-border-strong) bg-(--color-bg)' : 'border-(--color-border) bg-(--color-surface)'}`}>
      <div className="mb-1 flex items-baseline justify-between gap-4">
        <h2 className="type-subtitle font-heading">Channel traces</h2>
        <span className={`type-caption ${cut && !ended ? 'text-(--color-alert)' : 'text-(--color-text-muted)'}`}>{caption}</span>
      </div>
      <p className="type-caption text-(--color-text-secondary)">
        Filtered 1–40 Hz with 60 Hz notch, last 20 s. For checking contact. The engine does not read this panel.
      </p>
      <div className="mt-2 flex items-center gap-1.5">
        <span className="type-caption text-(--color-text-muted)">Scale</span>
        {SCALES.map((s) => (
          <button key={s} type="button" aria-pressed={scale === s} onClick={() => setScale(s)}
            className={`h-5 rounded-full border px-2 font-mono text-[10px] ${scale === s ? 'border-(--color-accent) font-semibold' : 'border-(--color-border)'}`}>
            ±{s} µV
          </button>
        ))}
        <span className="type-caption ml-auto text-(--color-text-secondary)">µV rms, 1 s</span>
      </div>
      <div ref={box} className="mt-2 grid" style={{ gridTemplateColumns: `${GUTTER}px minmax(0,1fr) ${VALUE_W}px` }}>
        <ol className="m-0 list-none p-0" aria-hidden>
          {labels.map((l) => <li key={l} className="font-mono text-[11px] text-(--color-text-secondary)" style={{ height: LANE_H, marginBottom: GAP, lineHeight: `${LANE_H}px` }}>{l}</li>)}
        </ol>
        <canvas ref={canvas} role="img" aria-label="Eight channel traces" style={{ width: plotW, height }} />
        <ol className="m-0 list-none p-0" aria-label="µV rms, 1 s">
          {labels.map((l, ch) => {
            const text = nowLabel(rms[ch], clippedLastSecond(bins, ch, nowMs, scale), data?.excluded === l)
            const muted = text === '—' || text === 'excluded' || ended
            return (
              <li key={l} className={`text-right font-mono text-[10px] ${muted ? 'text-(--color-text-muted)' : 'text-(--color-text)'}`}
                style={{ height: LANE_H, marginBottom: GAP, lineHeight: `${LANE_H}px` }}>{text}</li>
            )
          })}
        </ol>
      </div>
      <div className="mt-1 flex justify-between font-mono text-[10px] text-(--color-text-muted)" style={{ paddingLeft: GUTTER, paddingRight: VALUE_W }}>
        <span>−20 s</span><span>−16</span><span>−12</span><span>−8</span><span>−4</span>
        <span className="font-sans font-semibold text-(--color-text)">Now</span>
      </div>
      <div className="mt-1 flex items-center gap-1.5 font-mono text-[9px]" aria-label="Scale bar, 100 µV">
        <span className="inline-block w-0.5 bg-(--color-text)" style={{ height: Math.max(2, (100 / scale) * (LANE_H / 2)) }} />100 µV
      </div>
      {!data?.labels && !bins.length && (
        <p className="type-caption mt-1 text-(--color-text-muted)">No session. Traces start with the AURA stream.</p>
      )}
    </section>
  )
}

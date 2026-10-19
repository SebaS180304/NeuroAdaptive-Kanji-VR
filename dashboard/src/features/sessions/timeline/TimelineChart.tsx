import { CustomChart } from 'echarts/charts'
import { DataZoomComponent, GridComponent, TooltipComponent } from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { useEffect, useRef } from 'react'
import { tokenReader } from '@/lib/tokens'
import { clock, type Lane } from './lanes'

echarts.use([CustomChart, GridComponent, TooltipComponent, DataZoomComponent, CanvasRenderer])

export const AXIS_HEIGHT = 28
/** Room at each side of the plot for the first and last tick label. */
export const PLOT_INSET = 24

type Props = {
  lanes: Lane[]
  end: number
  window: [number, number]
  onWindow: (w: [number, number]) => void
  /** Start of the selected trial: the 2 px cursor across every lane. */
  cursor: number | null
  onPick: (trialId: string) => void
}

// --color-trial-incorrect: 45°, 2 px alert on alert-tint (design-system.md).
function hatch(color: (n: string) => string): { image: HTMLCanvasElement; repeat: 'repeat' } | string {
  const c = document.createElement('canvas')
  c.width = c.height = 4
  const g = c.getContext('2d')
  if (!g) return color('--color-alert')
  g.fillStyle = color('--color-alert-tint')
  g.fillRect(0, 0, 4, 4)
  g.strokeStyle = color('--color-alert')
  g.lineWidth = 1.4
  g.beginPath()
  g.moveTo(-1, 5); g.lineTo(5, -1)
  g.moveTo(-1, 1); g.lineTo(1, -1)
  g.moveTo(3, 5); g.lineTo(5, 3)
  g.stroke()
  return { image: c, repeat: 'repeat' }
}

function option(lanes: Lane[], end: number, w: [number, number], cursor: number | null, color: (n: string) => string): echarts.EChartsCoreOption {
  // Each lane's top edge, in px from the top of the plot.
  const tops = lanes.map((_, i) => lanes.slice(0, i).reduce((h, l) => h + l.height, 0))
  const height = tops.at(-1)! + lanes.at(-1)!.height
  const pattern = hatch(color)
  const data = lanes.flatMap((l, li) => (l.marks ?? []).map((m, mi) => [li, mi, m.start, m.end]))
  return {
    animation: false,
    grid: { left: PLOT_INSET, right: PLOT_INSET, top: 0, height, outerBoundsMode: 'none' },
    tooltip: {
      trigger: 'item',
      backgroundColor: color('--color-surface-raised'),
      borderColor: color('--color-border'),
      textStyle: { color: color('--color-text'), fontFamily: 'Public Sans', fontSize: 12 },
      formatter: (p: { value: number[] }) => echarts.format.encodeHTML(lanes[p.value[0]!]!.marks![p.value[1]!]!.tip),
    },
    xAxis: {
      type: 'value', min: 0, max: end,
      axisLine: { lineStyle: { color: color('--color-border-strong') } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { formatter: clock, color: color('--color-text-muted'), fontFamily: 'JetBrains Mono', fontSize: 12, hideOverlap: true },
    },
    yAxis: { type: 'value', min: 0, max: 1, show: false },
    dataZoom: [{ type: 'inside', xAxisIndex: 0, filterMode: 'weakFilter', startValue: w[0], endValue: w[1], minValueSpan: 5000 }],
    series: [{
      type: 'custom',
      cursor: 'pointer',
      data,
      encode: { x: [2, 3] },
      clip: true,
      renderItem: (params: { coordSys: { x: number; y: number; width: number } }, api: { value: (i: number) => number; coord: (v: number[]) => number[] }) => {
        const lane = lanes[api.value(0)]!
        const m = lane.marks![api.value(1)]!
        const cs = params.coordSys
        const x0 = api.coord([api.value(2), 0])[0]!
        const x1 = api.coord([api.value(3), 0])[0]!
        const slot = cs.y + tops[api.value(0)]! + 8          // bars sit 8 px from the lane top
        const y = slot + (m.y ?? 0)
        const h = m.h ?? lane.barHeight
        const mid = y + h / 2
        const stroke = m.stroke ? color(m.stroke) : undefined
        const fill = m.mark === 'hatch' ? pattern : m.fill ? color(m.fill) : 'transparent'
        const dash = m.dashed ? [3, 2] : undefined
        const visible = (x: number) => x >= cs.x - 8 && x <= cs.x + cs.width + 8

        // Point marks: drawn at their time, kept whole near the edges.
        if (m.start === m.end && m.mark !== 'bar') {
          if (!visible(x0)) return null
          if (m.mark === 'tick') return { type: 'rect', shape: { x: x0 - 1, y, width: 2, height: h }, style: { fill } }
          if (m.mark === 'dot')
            // A requested hint is filled; a proactive cue is a 2 px ring of the same size.
            return { type: 'circle', shape: { cx: x0, cy: mid, r: h / 2 - (stroke ? 1 : 0) }, style: { fill, stroke, lineWidth: 2 } }
          if (m.mark === 'diamond') {
            // design-system.md: a 12 px square rotated 45°, filled = applied, 2 px outline = skipped.
            const r = stroke ? 7.5 : 8.5
            return {
              type: 'polygon',
              shape: { points: [[x0, slot + 8 - r], [x0 + r, slot + 8], [x0, slot + 8 + r], [x0 - r, slot + 8]] },
              style: { fill: stroke ? color('--color-surface') : fill, stroke, lineWidth: 2, lineDash: dash },
            }
          }
          // badge: the outcome, 6 px, at the diamond's upper right, inside a 1 px surface ring.
          const ring = { fill: color('--color-surface') }
          const style = { fill, stroke, lineWidth: 1 }
          const inner = stroke ? 0.5 : 0
          return {
            type: 'group',
            children: m.shape === 'circle'
              ? [{ type: 'circle', shape: { cx: x0 + 8, cy: slot - 2, r: 4 }, style: ring },
                 { type: 'circle', shape: { cx: x0 + 8, cy: slot - 2, r: 3 - inner }, style }]
              : [{ type: 'rect', shape: { x: x0 + 4, y: slot - 6, width: 8, height: 8 }, style: ring },
                 { type: 'rect', shape: { x: x0 + 5 + inner, y: slot - 5 + inner, width: 6 - 2 * inner, height: 6 - 2 * inner }, style }],
          }
        }

        const rect = echarts.graphic.clipRectByRect(
          { x: x0, y, width: Math.max(x1 - x0 - (m.mark === 'link' ? 0 : 1), 1), height: h },
          { x: cs.x, y: cs.y, width: cs.width, height },
        )
        if (!rect) return null
        if (m.mark === 'link')
          // Decision to Unity's answer: a line ending in a 2 px tick at the answer.
          return {
            type: 'group',
            children: [
              { type: 'line', shape: { x1: rect.x, y1: slot + 8, x2: rect.x + rect.width, y2: slot + 8 }, style: { stroke, lineWidth: 1 } },
              ...(visible(x1) ? [{ type: 'rect', shape: { x: x1 - 1, y: slot + 2, width: 2, height: 12 }, style: { fill: stroke } }] : []),
            ],
          }
        const text = (label: string, x: number, style: object) => ({
          type: 'text',
          style: { text: label, x, y: mid, verticalAlign: 'middle', fill: color(m.labelColor ?? '--color-text'), ...style },
        })
        const children: object[] = []
        if (m.mark === 'line') {
          // LAL Off: a line through the slot, its name at the start of a run of 48 px or more.
          children.push({ type: 'line', shape: { x1: rect.x, y1: mid, x2: rect.x + rect.width, y2: mid }, style: { stroke, lineWidth: 1 } })
          if (m.label && rect.width >= 48)
            children.push(text(m.label, rect.x, {
              align: 'left', font: '12px "Public Sans"', backgroundColor: color('--color-surface'), padding: [0, 4, 0, 0],
            }))
        } else {
          const inset = stroke ? 0.5 : 0      // a 1 px border drawn inside the bar
          children.push({
            type: 'rect',
            shape: { x: rect.x + inset, y: rect.y + inset, width: Math.max(rect.width - 2 * inset, 1), height: rect.height - 2 * inset, r: 1 },
            style: { fill, stroke, lineWidth: 1, lineDash: dash },
          })
          if (m.label && rect.width > 8 * m.label.length + 12)
            children.push(text(m.label, rect.x + (lane.key === 'states' ? rect.width / 2 : 8), {
              align: lane.key === 'states' ? 'center' : 'left', font: `${lane.key === 'states' ? 12 : 11}px "JetBrains Mono"`,
            }))
        }
        return { type: 'group', children }
      },
    }, {
      // design-system.md "Timeline": the selected trial, a 2 px --color-text cursor.
      type: 'custom',
      silent: true,
      data: cursor === null ? [] : [[cursor]],
      encode: { x: 0 },
      renderItem: (params: { coordSys: { y: number } }, api: { value: (i: number) => number; coord: (v: number[]) => number[] }) => ({
        type: 'rect',
        shape: { x: api.coord([api.value(0), 0])[0]! - 1, y: params.coordSys.y, width: 2, height },
        style: { fill: color('--color-text') },
      }),
    }],
  }
}

export function TimelineChart({ lanes, end, window: w, onWindow, cursor, onPick }: Props) {
  const el = useRef<HTMLDivElement>(null)
  const chart = useRef<echarts.ECharts | null>(null)
  const lanesRef = useRef(lanes)
  useEffect(() => { lanesRef.current = lanes }, [lanes])
  const report = useRef(onWindow)
  const pick = useRef(onPick)
  useEffect(() => { report.current = onWindow; pick.current = onPick }, [onWindow, onPick])

  useEffect(() => {
    const c = echarts.init(el.current!)
    chart.current = c
    c.on('datazoom', () => {
      const dz = (c.getOption().dataZoom as { startValue: number; endValue: number }[])[0]!
      report.current([dz.startValue, dz.endValue])
    })
    // A click on a trial bar or a decision diamond selects its trial.
    c.on('click', (p) => {
      const [li, mi] = p.value as number[]
      const ref = lanesRef.current[li!]?.marks?.[mi!]?.ref
      if (p.seriesIndex === 0 && ref) pick.current(ref)
    })
    const resize = new ResizeObserver(() => c.resize())
    resize.observe(el.current!)
    return () => { resize.disconnect(); c.dispose() }
  }, [])

  // Redrawn on a theme change, so the canvas follows the tokens.
  useEffect(() => {
    const draw = () => chart.current!.setOption(option(lanes, end, w, cursor, tokenReader(el.current!)), { replaceMerge: ['series'] })
    draw()
    const media = matchMedia('(prefers-color-scheme: dark)')
    media.addEventListener('change', draw)
    return () => media.removeEventListener('change', draw)
  }, [lanes, end, w, cursor])

  return <div ref={el} aria-hidden="true" className="absolute inset-0" />
}

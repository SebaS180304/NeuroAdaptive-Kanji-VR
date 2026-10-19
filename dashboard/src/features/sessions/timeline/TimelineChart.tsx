import { CustomChart } from 'echarts/charts'
import { DataZoomComponent, GridComponent, TooltipComponent } from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { useEffect, useRef } from 'react'
import { clock, type Lane } from './lanes'

echarts.use([CustomChart, GridComponent, TooltipComponent, DataZoomComponent, CanvasRenderer])

export const AXIS_HEIGHT = 28

type Props = {
  lanes: Lane[]
  end: number
  window: [number, number]
  onWindow: (w: [number, number]) => void
}

/** A token's value in the current theme (the canvas cannot read CSS variables). */
function tokenReader(el: HTMLElement) {
  const style = getComputedStyle(el)
  return (name: string) => style.getPropertyValue(name).trim()
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

function option(lanes: Lane[], end: number, w: [number, number], color: (n: string) => string): echarts.EChartsCoreOption {
  // Each lane's top edge, in px from the top of the plot.
  const tops = lanes.map((_, i) => lanes.slice(0, i).reduce((h, l) => h + l.height, 0))
  const height = tops.at(-1)! + lanes.at(-1)!.height
  const pattern = hatch(color)
  const data = lanes.flatMap((l, li) => (l.bars ?? []).map((b, bi) => [li, bi, b.start, b.end]))
  return {
    animation: false,
    grid: { left: 0, right: 0, top: 0, height },
    tooltip: {
      trigger: 'item',
      backgroundColor: color('--color-surface-raised'),
      borderColor: color('--color-border'),
      textStyle: { color: color('--color-text'), fontFamily: 'Public Sans', fontSize: 12 },
      formatter: (p: { value: number[] }) => echarts.format.encodeHTML(lanes[p.value[0]!]!.bars![p.value[1]!]!.tip),
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
      data,
      encode: { x: [2, 3] },
      clip: true,
      renderItem: (params: { coordSys: { x: number; y: number; width: number } }, api: { value: (i: number) => number; coord: (v: number[]) => number[] }) => {
        const lane = lanes[api.value(0)]!
        const bar = lane.bars![api.value(1)]!
        const x0 = api.coord([api.value(2), 0])[0]!
        const x1 = api.coord([api.value(3), 0])[0]!
        const cs = params.coordSys
        const rect = echarts.graphic.clipRectByRect(
          { x: x0, y: cs.y + tops[api.value(0)]! + 8, width: Math.max(x1 - x0 - 1, 1), height: lane.barHeight },
          { x: cs.x, y: cs.y, width: cs.width, height },
        )
        if (!rect) return null
        const fill = bar.pattern === 'hatch' ? pattern : bar.pattern === 'outline' ? 'transparent' : color(bar.fill)
        const stroke = bar.pattern === 'outline' ? color(bar.fill) : undefined
        const children: object[] = [{ type: 'rect', shape: { ...rect, r: 1 }, style: { fill, stroke, lineWidth: 1 } }]
        if (bar.label && rect.width > 8 * bar.label.length + 12)
          children.push({
            type: 'text',
            style: {
              text: bar.label, x: rect.x + (lane.key === 'states' ? rect.width / 2 : 8), y: rect.y + rect.height / 2,
              align: lane.key === 'states' ? 'center' : 'left', verticalAlign: 'middle',
              fill: color(bar.labelColor ?? '--color-text'), font: `${lane.key === 'states' ? 12 : 11}px "JetBrains Mono"`,
            },
          })
        return { type: 'group', children }
      },
    }],
  }
}

export function TimelineChart({ lanes, end, window: w, onWindow }: Props) {
  const el = useRef<HTMLDivElement>(null)
  const chart = useRef<echarts.ECharts | null>(null)
  const report = useRef(onWindow)
  useEffect(() => { report.current = onWindow }, [onWindow])

  useEffect(() => {
    const c = echarts.init(el.current!)
    chart.current = c
    c.on('datazoom', () => {
      const dz = (c.getOption().dataZoom as { startValue: number; endValue: number }[])[0]!
      report.current([dz.startValue, dz.endValue])
    })
    const resize = new ResizeObserver(() => c.resize())
    resize.observe(el.current!)
    return () => { resize.disconnect(); c.dispose() }
  }, [])

  // Redrawn on a theme change, so the canvas follows the tokens.
  useEffect(() => {
    const draw = () => chart.current!.setOption(option(lanes, end, w, tokenReader(el.current!)), { replaceMerge: ['series'] })
    draw()
    const media = matchMedia('(prefers-color-scheme: dark)')
    media.addEventListener('change', draw)
    return () => media.removeEventListener('change', draw)
  }, [lanes, end, w])

  return <div ref={el} aria-hidden="true" className="absolute inset-0" />
}

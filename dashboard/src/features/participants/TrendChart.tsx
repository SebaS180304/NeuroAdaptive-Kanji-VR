import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { useEffect, useRef } from 'react'
import type { Condition } from '@/components/ConditionChip'
import { tokenReader } from '@/lib/tokens'

echarts.use([LineChart, GridComponent, TooltipComponent, CanvasRenderer])

// "Across sessions" of the Learner Profile (design-system.md, V1.8 rules and F-PROFILE): correct in
// S7 as answers of 20, never a percentage, or the mean response time.

export type Measure = 'correct' | 'rt'
/** One completed session; n is its # in "Sessions in order"; of is its S7 trial count. */
export type TrendPoint = { n: number; condition: Condition; value: number; date: string; visit: number; of: number; set: string | null }

// Shape and color, never color alone. No diamond: it belongs to timeline decisions.
export const SHAPE: Record<Condition, { symbol: string; token: string }> = {
  STATIC: { symbol: 'rect', token: '--color-condition-static' },
  BEHAVIOR_ADAPTIVE: { symbol: 'circle', token: '--color-condition-behavior' },
  MULTIMODAL_ADAPTIVE: { symbol: 'triangle', token: '--color-condition-multimodal' },
}

/** From 0 to the next 500 ms step above the largest mean, in 4 or 5 gridlines at most. */
export function rtAxis(largest: number): { max: number; interval: number } {
  const interval = 500 * Math.ceil(Math.ceil(largest / 500) / 5)
  return { max: interval * Math.max(1, Math.ceil(largest / interval)), interval }
}

export const formatMeasure = (m: Measure, v: number, of = 20) => (m === 'correct' ? `${v} of ${of}` : `${Math.round(v)} ms`)

export function trendOption(points: TrendPoint[], measure: Measure, color: (n: string) => string) {
  const many = points.length > 12
  const text = { fontFamily: 'Public Sans', fontSize: 12, color: color('--color-text-muted') }
  const of = Math.max(...points.map((p) => p.of))
  const y = measure === 'correct' ? { min: 0, max: of, interval: 5 } : { min: 0, ...rtAxis(Math.max(...points.map((p) => p.value))) }
  return {
    animation: false,
    textStyle: { fontFamily: 'Public Sans' },
    grid: { left: 56, right: 56, top: 16, bottom: 48 },
    tooltip: {
      trigger: 'item',
      formatter: (p: { dataIndex: number }) => {
        const t = points[p.dataIndex]!
        return echarts.format.encodeHTML(
          `Session ${t.n}, ${t.date}${t.visit > 1 ? `, visit ${t.visit}` : ''}${t.set ? `, set ${t.set}` : ''}: ${formatMeasure(measure, t.value, t.of)}`)
      },
    },
    xAxis: {
      type: 'category',
      data: points.map((p) => String(p.n)),
      name: 'Completed sessions, numbered as in the table',
      nameLocation: 'middle',
      nameGap: 32,
      nameTextStyle: text,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: color('--color-border-strong') } },
      axisLabel: { ...text, interval: many ? (_: number, label: string) => Number(label) % 5 === 0 : 0 },
    },
    yAxis: {
      type: 'value',
      ...y,
      axisLabel: { ...text, formatter: (v: number) => (measure === 'correct' ? (v === of ? `${v} of ${of}` : String(v)) : `${v} ms`) },
      splitLine: { lineStyle: { color: color('--color-border-subtle') } },
    },
    series: [{
      type: 'line',
      lineStyle: { width: 1, color: color('--color-border-strong') },
      data: points.map((p, i) => ({
        value: p.value,
        symbol: SHAPE[p.condition].symbol,
        symbolSize: many ? 6 : 10,
        itemStyle: { color: color(SHAPE[p.condition].token) },
        label: { show: !many && i === points.length - 1, formatter: 'Latest', position: 'right',
          fontSize: 12, fontWeight: 500, color: color('--color-text') },
      })),
    }],
  }
}

export function TrendChart({ points, measure }: { points: TrendPoint[]; measure: Measure }) {
  const el = useRef<HTMLDivElement>(null)
  const chart = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    const c = echarts.init(el.current!)
    chart.current = c
    const resize = new ResizeObserver(() => c.resize())
    resize.observe(el.current!)
    return () => { resize.disconnect(); c.dispose() }
  }, [])

  // Redrawn on a theme change, so the canvas follows the tokens.
  useEffect(() => {
    const draw = () => chart.current!.setOption(trendOption(points, measure, tokenReader(el.current!)), { notMerge: true })
    draw()
    const media = matchMedia('(prefers-color-scheme: dark)')
    media.addEventListener('change', draw)
    return () => media.removeEventListener('change', draw)
  }, [points, measure])

  return <div ref={el} aria-hidden="true" className="h-[248px] w-full" />
}

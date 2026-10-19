import { describe, expect, it } from 'vitest'
import { rtAxis, trendOption, type TrendPoint } from './TrendChart'

const color = (n: string) => n
const point = (n: number, condition: TrendPoint['condition'], value: number): TrendPoint =>
  ({ n, condition, value, date: '2026-10-14', visit: 1 })

type Item = { value: number; symbol: string; symbolSize: number; itemStyle: { color: string }; label?: { show: boolean } }
const series = (o: ReturnType<typeof trendOption>) => (o.series as { data: Item[] }[])[0]!.data
const ticks = (o: ReturnType<typeof trendOption>) => (o.xAxis as { data: string[] }).data

describe('trend chart (design-system.md, V1.8)', () => {
  it('ticks the table numbers and shapes points by condition, the latest labeled', () => {
    const o = trendOption([point(1, 'STATIC', 0.5), point(2, 'BEHAVIOR_ADAPTIVE', 0.6), point(4, 'MULTIMODAL_ADAPTIVE', 0.7)], 'accuracy', color)
    expect(ticks(o)).toEqual(['1', '2', '4'])
    expect(series(o).map((d) => [d.symbol, d.itemStyle.color])).toEqual([
      ['rect', '--color-condition-static'], ['circle', '--color-condition-behavior'], ['triangle', '--color-condition-multimodal'],
    ])
    expect(series(o).map((d) => !!d.label?.show)).toEqual([false, false, true])
    expect(o.yAxis).toMatchObject({ min: 0, max: 1, interval: 0.25 })
  })

  it('with more than 12 points: 6 px points and no point labels', () => {
    const many = Array.from({ length: 13 }, (_, i) => point(i + 1, 'STATIC', 0.5))
    const d = series(trendOption(many, 'accuracy', color))
    expect(d.every((p) => p.symbolSize === 6 && !p.label?.show)).toBe(true)
  })

  it('scales response time from 0 to the next 500 ms step, 4 or 5 gridlines', () => {
    expect(rtAxis(1834)).toEqual({ max: 2000, interval: 500 })
    expect(rtAxis(2600)).toEqual({ max: 3000, interval: 1000 })
    expect(rtAxis(4600)).toEqual({ max: 5000, interval: 1000 })
  })
})

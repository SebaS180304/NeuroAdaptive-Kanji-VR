import { useEffect, useRef, useState, type ReactNode } from 'react'
import type { Schemas } from '@/api/client'
import { Chip, Legend, Readout, STROKE, WIDTH, referenceChip, slotOf, trialNo, type Epoch, type Key, type SessionTrace } from './SessionIndices'

// MI outside S7 (design-handoff/design-system.md «Live indices: S7 only in S7, 20 s window outside», validated
// D-F6-312 (3); D-F6-308 (3), D-F6-309 (4)); texts from Contenido_UI_Monitor_Indices.md §2, §3, §4.2 and §7.6
// (PM's extract of 27 Nov, D-F6-320). Drawn when the backend sends view "window" (MONITOR_INDICES_WINDOW).

type Snapshot = Schemas['LiveSnapshot']
type Decision = Schemas['LiveDecision']
export type WindowEpoch = Epoch & { end_ms: number; ln_ei: number | null; ln_theta: number | null }
export type WindowTrace = Omit<SessionTrace, 'epochs' | 'ica'> & {
  view: 'window'; epochs: WindowEpoch[]
  ica: (NonNullable<SessionTrace['ica']> & { at_ms: number | null; switch_ms: number | null; switch_channel: string | null }) | null
}

const S7 = 'S7_EXPERIMENTAL_RETRIEVAL', S6 = 'S6_GUIDED_PRACTICE_CALIBRATION'
const WINDOW_MS = 20_000, GUTTER = 36
const SCALE: Record<Key, [number, number]> = { ei: [-3.0, 0.0], theta: [-3.5, -0.5] }   // EEG's fixed ln scale, D-F6-309 (4) (b)
const HEIGHT: Record<Key, number> = { ei: 76, theta: 64 }
const NAME: Record<Key, string> = { ei: 'Engagement Index', theta: 'Theta (Fz)' }
const REF: Record<string, string> = {   // §2: every stage outside S7 is raw, in ln
  s13: 'Raw, no reference yet', S4: 'Raw, S4 baseline', S5: 'Raw, no decisions yet', S6: 'Building reference (S6)',
  s89: 'Raw, no decisions after S7',
}
const minus = (v: number, digits = 1) => (v < 0 ? `−${Math.abs(v).toFixed(digits)}` : v.toFixed(digits))
const pad = (n: number) => String(n).padStart(2, '0')
const hms = (ms: number) => `${pad(Math.floor(ms / 3_600_000))}:${pad(Math.floor(ms / 60_000) % 60)}:${pad(Math.floor(ms / 1000) % 60)}`
const short = (state: string) => state.slice(0, 2)
const mid = (e: WindowEpoch) => (e.start_ms + e.end_ms) / 2

function useWidth(fallback: number) {
  const ref = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(fallback)
  useEffect(() => {
    const el = ref.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(([e]) => setWidth(Math.max(200, Math.floor(e!.contentRect.width))))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return [ref, width] as const
}

type Kind = keyof typeof STROKE
const FILL: Record<Kind, string> = { valid: 'fill-(--color-accent)', invalid: 'fill-(--color-quality-error)', grey: 'fill-(--color-border-strong)' }

/** A POOR epoch has no value: it sits between its valid neighbours of the same stage, in red (as the S7 view). */
function values(list: WindowEpoch[], col: 'ln_ei' | 'ln_theta' | 'ei' | 'theta', middle: number): number[] {
  return list.map((e, j) => {
    if (e[col] != null) return e[col]!
    const same = (x: WindowEpoch) => x.state === e.state && x[col] != null
    const prev = list.slice(0, j).reverse().find(same)?.[col], next = list.slice(j + 1).find(same)?.[col]
    return prev != null && next != null ? (prev + next) / 2 : prev ?? next ?? middle
  })
}

function WindowStrip({ k, epochs, stages, now, width, kind }: {
  k: Key; epochs: WindowEpoch[]; stages: SessionTrace['stages']; now: number; width: number; kind: (e: WindowEpoch) => Kind
}) {
  const height = HEIGHT[k], top = 12, H = height - top - 4
  const [lo, hi] = SCALE[k]
  const from = now - WINDOW_MS
  const x = (t: number) => GUTTER + ((t - from) / WINDOW_MS) * (width - GUTTER)
  const y = (v: number) => top + H - ((Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo)) * H
  const list = epochs.filter((e) => mid(e) >= from && mid(e) <= now)
  const vs = values(list, k === 'ei' ? 'ln_ei' : 'ln_theta', (lo + hi) / 2)
  const lines = stages.filter((s) => s.ms > from && s.ms <= now)
  return (
    <svg width={width} height={height} className="block" role="img" aria-label={`${NAME[k]}, last 20 seconds, log values`}>
      <text x={GUTTER + 2} y={9} className="fill-(--color-text-muted) font-mono text-[9px]">ln</text>
      {[lo, (lo + hi) / 2, hi].map((v) => (
        <g key={v}>
          <line data-tick={v.toFixed(1)} x1={GUTTER} x2={width} y1={y(v)} y2={y(v)} strokeWidth={1} className="stroke-(--color-border)" />
          <text x={GUTTER - 4} y={y(v) + 3} textAnchor="end" className="fill-(--color-text-muted) font-mono text-[9px]">{minus(v)}</text>
        </g>
      ))}
      {[16, 12, 8, 4].map((s) => <line key={s} x1={x(now - s * 1000)} x2={x(now - s * 1000)} y1={top} y2={height}
        className="stroke-(--color-border-subtle)" />)}
      <line x1={width - 0.5} x2={width - 0.5} y1={0} y2={height} strokeWidth={1} className="stroke-(--color-text)" />
      {lines.map((s) => (
        <g key={`${s.state}${s.ms}`}>
          <line x1={x(s.ms)} x2={x(s.ms)} y1={0} y2={height} strokeWidth={1} className="stroke-(--color-text-secondary)" />
          {k === 'ei' && <>
            <rect x={x(s.ms) + 1} y={0} width={16} height={11} className="fill-(--color-surface)" />
            <text x={x(s.ms) + 3} y={9} className="fill-(--color-text-secondary) text-[10px] font-semibold">{short(s.state)}</text>
          </>}
        </g>
      ))}
      {list.map((e, j) => j > 0 && list[j - 1]!.state === e.state && (   // never joined across a stage line
        <line key={`j${e.i}`} data-join x1={x(mid(list[j - 1]!))} x2={x(mid(e))} y1={y(vs[j - 1]!)} y2={y(vs[j]!)}
          strokeWidth={WIDTH[kind(e)]} className={STROKE[kind(e)]} />
      ))}
      {list.map((e, j) => <circle key={`d${e.i}`} data-dot={e.i} cx={x(mid(e))} cy={y(vs[j]!)} r={2.2} className={FILL[kind(e)]} />)}
    </svg>
  )
}

function S7Strip({ k, epochs, s7, now, width, kind, decisions, switchLine, readout }: {
  k: Key; epochs: WindowEpoch[]; s7: number; now: number; width: number; kind: (e: WindowEpoch) => Kind
  decisions: Decision[]; switchLine: { ms: number; text: string } | null; readout: ReactNode
}) {
  const height = HEIGHT[k], top = k === 'ei' ? 12 : 0, H = height - top
  const span = Math.max(1, now - s7)
  const x = (t: number) => ((t - s7) / span) * width
  const y = (v: number) => top + H - ((Math.max(-2.5, Math.min(2.5, v)) + 2.5) / 5) * H
  const vs = values(epochs, k, 0)
  const zOf = (d: Decision) => (k === 'ei' ? d.eeg_ei_z : d.eeg_theta_z)
  return (
    <div>
      <div data-strip-head className="flex h-7 items-baseline justify-between">
        <h3 className="type-body-strong">{NAME[k]}</h3>
        {readout}
      </div>
      <svg width={width} height={height} className="block" role="img" aria-label={`${NAME[k]}, stage S7, z against S6`}>
        <text x={1} y={top + 8} className="fill-(--color-text-muted) font-mono text-[9px]">z</text>
        <rect x={0} y={y(1)} width={width} height={y(-1) - y(1)} className="fill-(--color-explain-bg)" />
        {[-1, 1].map((g) => <line key={g} x1={0} x2={width} y1={y(g)} y2={y(g)} strokeWidth={1} className="stroke-(--color-border)" />)}
        {k === 'ei' && <>
          <line x1={0} x2={width} y1={y(-1.5)} y2={y(-1.5)} strokeDasharray="4 3" className="stroke-(--color-quality-error)" />
        </>}
        {epochs.map((e, j) => (
          <line key={e.i} data-epoch={kind(e)} x1={j ? x(mid(epochs[j - 1]!)) : x(mid(e)) - 1} x2={x(mid(e))}
            y1={y(vs[j ? j - 1 : j]!)} y2={y(vs[j]!)} strokeWidth={WIDTH[kind(e)]} className={STROKE[kind(e)]} />
        ))}
        {switchLine && <>
          <line x1={x(switchLine.ms)} x2={x(switchLine.ms)} y1={0} y2={height} strokeWidth={1.5} className="stroke-(--color-quality-warn)" />
          {k === 'ei' && <text x={x(switchLine.ms) - 3} y={10} textAnchor="end"
            className="fill-(--color-quality-warn) text-[10px] font-semibold">{switchLine.text}</text>}
        </>}
        {decisions.filter((d) => d.trial_sequence != null && d.trial_sequence >= 3 && zOf(d) != null && d.decided_elapsed_ms != null)
          .map((d) => {
            const z = zOf(d)!, cx = x(d.decided_elapsed_ms!), cy = y(z)
            const mark = d.eeg_counted === false ? 'ring' : z <= -1 ? 'low' : z >= 1 ? 'high' : 'normal'
            return (
              <g key={`p${d.trial_id}`} data-point={mark}>
                <title>{`Decision at trial ${d.trial_sequence}. ${NAME[k]} z ${z.toFixed(1)}.`}</title>
                {mark === 'ring' ? <circle cx={cx} cy={cy} r={3.5} fill="none" strokeWidth={1.25} className="stroke-(--color-text)" />
                  : mark === 'normal' ? <circle cx={cx} cy={cy} r={3} className="fill-(--color-text) stroke-(--color-surface)" />
                  : <path d={mark === 'low' ? `M${cx - 4},${cy - 3}h8l-4,6z` : `M${cx - 4},${cy + 3}h8l-4,-6z`}
                    className="fill-(--color-text) stroke-(--color-surface)" />}
              </g>
            )
          })}
        {k === 'ei' && (   // left end, where no decision falls (they start at trial 3), on a halo and above them (12:15, 2)
          <text x={2} y={y(-1.5) - 2} strokeWidth={3}
            className="fill-(--color-text-muted) stroke-(--color-surface) text-[9px] [paint-order:stroke]">Lead line (−1.5)</text>
        )}
      </svg>
    </div>
  )
}

/** The ICA status line (§3, §4.2): outside the strips, beside the rule chip, written to the end of the session. */
function icaLine(ica: WindowTrace['ica']): { text: string; mark: 'ring' | 'dot' | 'warn' } {
  if (ica == null) return { text: 'Fitting ICA', mark: 'ring' }
  const at = ica.at_ms == null ? '—' : hms(ica.at_ms)
  if (ica.switched_to_nosound_at != null) {   // as referenceChip; provisional "Rule (2) from" (D-F6-320 (3) (b))
    const when = ica.switch_ms == null ? '—' : hms(ica.switch_ms)
    return { text: ica.switch_channel ? `${ica.switch_channel} excluded at ${when}, rule (2) from here`
      : `Rule (2) from ${when}`, mark: 'warn' }
  }
  return ica.identified ? { text: `ICA applied at ${at}, r ${(ica.corr ?? 0).toFixed(2)}`, mark: 'dot' }
    : { text: `ICA not found at ${at}, rule (2) from here`, mark: 'warn' }
}

const AXIS_S = [20, 16, 12, 8, 4]

export function IndicesWindow({ i, s, stage, decisions, ended, now }: {
  i: Snapshot['indices']; s: WindowTrace; stage: string | null | undefined; decisions: Decision[]; ended: boolean
  now: number | null
}) {
  const [ref, width] = useWidth(452)
  const slot = slotOf(stage ?? 'S1')
  const order = ['s13', 'S4', 'S5', 'S6', 'S7', 's89']
  const reached = (id: string) => order.indexOf(slot) >= order.indexOf(id)
  const t = now ?? Math.max(0, ...s.epochs.map((e) => e.end_ms))
  const inS7 = slot === 'S7'
  const s7 = s.stages.find((x) => x.state === S7)?.ms ?? t
  const fallback = !!s.ica && (!s.ica.identified || s.ica.switched_to_nosound_at != null)
  const kind = (e: WindowEpoch): Kind => {
    const k: Kind = e.grey || (e.state === S6 && s.ica == null) ? 'grey' : !e.valid ? 'invalid' : 'valid'
    return ended && k === 'valid' ? 'grey' : k
  }
  const [refName, solid] = inS7 ? [referenceChip('S7', i.reference, s.ica)[0], true] : [REF[slot]!, false]
  const line = reached('S6') ? icaLine(s.ica) : null
  const s7epochs = s.epochs.filter((e) => e.state === S7)
  const switchLine = s.ica?.switch_ms != null && s.ica.switch_ms >= s7 && line ? { ms: s.ica.switch_ms, text: line.text } : null
  // «Trial n» at the end of trial n, where its decision point is (D-F6-328 (2) (b)): the decision's time, or before
  // trial 3 (no decision) its last epoch's end. The newest label stays clear of «Now»; older ones give way.
  const ends = new Map<number, number>()
  for (const e of s7epochs) { const n = trialNo(e.trial_id); if (n) ends.set(n, Math.max(ends.get(n) ?? 0, e.end_ms)) }
  const decided = new Set<number>()
  for (const d of decisions) if (d.trial_sequence != null && d.decided_elapsed_ms != null) {
    ends.set(d.trial_sequence, d.decided_elapsed_ms); decided.add(d.trial_sequence)
  }
  const current = Math.max(0, ...ends.keys())
  for (const n of [...ends.keys()]) if (!decided.has(n) && n === current) ends.delete(n)   // the trial in course has no end yet
  const sx = (ms: number) => ((ms - s7) / Math.max(1, t - s7)) * width
  const trialLabels: [number, number][] = []
  for (const [n, ms] of [...ends].filter(([n]) => n % 2 === 1).sort((a, b) => b[0] - a[0])) {
    const x = Math.min(sx(ms), width - 30 - 18)
    if (x >= 18 && trialLabels.every(([, x2]) => Math.abs(x2 - x) >= 44)) trialLabels.push([n, x])
  }
  return (
    <div ref={ref}>
      <p className="type-caption text-(--color-text-secondary)">For viewing only. Decisions use 3-trial windows from S7.</p>
      <div className="mb-2 flex items-baseline justify-between">
        <span className="type-caption text-(--color-text-secondary)" title="Outside S7 the strips show the last 20 seconds in log values, about 8 epochs, with no reference. S7 shows the whole stage against S6, with its decision points.">
          Updates with each epoch, every 2.5 s.</span>
        {inS7 && <span className="type-caption">EEG counted in {i.windows.counted} of {i.windows.with_eeg}</span>}
      </div>
      <div data-testid="chip-row" className="mb-2 flex flex-nowrap items-center gap-1.5">
        {reached('S6') && s.ica != null && (fallback
          ? <Chip title="ICA is not active in this session. Epochs follow rule (2): the blink rule applies and task sounds are not cut. Expect more red epochs if blinks are frequent.">
              <span aria-hidden className="text-(--color-quality-warn)">▲</span>Rule: (2) fallback</Chip>
          : <Chip title="The eye component found by ICA is removed from every epoch from S6 on. The trace and the engine use the same correction.">
              <span aria-hidden className="inline-block size-2 rounded-full bg-(--color-accent)" />Rule: ICA</Chip>)}
        <Chip dashed={!solid}>{refName}</Chip>
        {line && (
          <span title={line.text} aria-label={line.text}   // may be cut with «…» at 1440 (D-F6-328 (2) (a))
            className="type-caption inline-flex min-w-0 items-center gap-1.5 text-(--color-text-secondary)">
            {line.mark === 'ring' ? <span aria-hidden className="inline-block size-2 shrink-0 rounded-full border border-(--color-text-secondary)" />
              : line.mark === 'dot' ? <span aria-hidden className="inline-block size-2 shrink-0 rounded-full bg-(--color-accent)" />
              : <svg aria-hidden width={9} height={8} className="shrink-0"><path d="M4.5,0L9,8H0z" className="fill-(--color-quality-warn)" /></svg>}
            <span data-testid="ica-line" aria-hidden className="min-w-0 truncate">{line.text}</span>
          </span>
        )}
      </div>
      {!reached('S4') ? (
        <div className="type-body flex items-center justify-center text-(--color-text-muted)" style={{ height: HEIGHT.ei + HEIGHT.theta + 2 * 28 + 14 }}>
          Indices from the end of S3</div>
      ) : inS7 ? (<>
        {(['ei', 'theta'] as Key[]).map((k) => <S7Strip key={k} k={k} epochs={s7epochs} s7={s7} now={t} width={width} kind={kind}
          decisions={decisions} switchLine={switchLine} readout={<Readout last={i.last} k={k} />} />)}
        <svg width={width} height={14} className="block" aria-label="Trials">
          {trialLabels.map(([n, x]) => <text key={n} data-trial={n} x={x} y={11} textAnchor="middle"
            className="fill-(--color-text-muted) text-[10px]">Trial {n}</text>)}
          <text x={width} y={11} textAnchor="end" className="fill-(--color-text) text-[10px] font-semibold">Now</text>
        </svg>
      </>) : (<>
        {(['ei', 'theta'] as Key[]).map((k) => (
          <div key={k}>
            <div data-strip-head className="flex h-7 items-baseline">   {/* as S7's, so the panel keeps its height (12:15, 1) */}
              <h3 className="type-body-strong">{NAME[k]}</h3>
            </div>
            <WindowStrip k={k} epochs={s.epochs} stages={s.stages} now={t} width={width} kind={kind} />
          </div>
        ))}
        <svg width={width} height={14} className="block" aria-label="Last 20 seconds">
          {AXIS_S.map((sec) => <text key={sec} x={GUTTER + ((WINDOW_MS - sec * 1000) / WINDOW_MS) * (width - GUTTER)} y={11}
            textAnchor="middle" className="fill-(--color-text-muted) text-[10px]">{sec === 20 ? '−20 s' : `−${sec}`}</text>)}
          <text x={width} y={11} textAnchor="end" className="fill-(--color-text) text-[10px] font-semibold">Now</text>
        </svg>
      </>)}
      <Legend />
    </div>
  )
}

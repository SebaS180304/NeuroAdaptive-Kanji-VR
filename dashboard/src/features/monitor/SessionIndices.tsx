import type { ReactNode } from 'react'
import type { Schemas } from '@/api/client'

// MI: «Live indices for the whole session» (design-handoff/design-system.md, validated D-F6-280; D-F6-277, D-F6-293 (4),
// D-F6-297 (4)); texts from Contenido_UI_Monitor_Indices.md. One point per live epoch as the backend sends it
// (indices.session), no smoothing; Low / Normal / High only at S7's decision points. Behind MONITOR_LIVE_INDICES.

type Snapshot = Schemas['LiveSnapshot']
type Decision = Schemas['LiveDecision']
export type Epoch = {
  i: number; start_ms: number; state: string; trial_id: string | null; valid: boolean; grey: boolean
  excluded: string | null; unit: 'ln' | 'z'; ei: number | null; theta: number | null
}
export type SessionTrace = {
  stages: { state: string; ms: number }[]; eyes_closed_ms: [number, number] | null
  ica: { identified: boolean; corr: number | null; reason: string | null; switched_to_nosound_at: number | null
    switch_reason: string | null } | null
  epochs: Epoch[]
}
type Key = 'ei' | 'theta'

// Fixed slots per stage (452 px), a 5 px gap where the unit changes: S4|S5, S5|S6, S6|S7 (design-system.md).
const SLOTS = [
  { id: 's13', w: 28, expect: 88, block: 0 }, { id: 'S4', w: 30, expect: 48, block: 0 },
  { id: 'S5', w: 30, expect: 84, block: 1 }, { id: 'S6', w: 34, expect: 40, block: 2 },
  { id: 'S7', w: 287, expect: 20, block: 3 }, { id: 's89', w: 28, expect: 28, block: 3 },
] as const
const GAP = 5, W = 452, TRIALS = 20
const slotOf = (state: string) => {
  const n = Number(state.slice(1, 2))
  return n <= 3 ? 's13' : n === 4 ? 'S4' : n === 5 ? 'S5' : n === 6 ? 'S6' : n === 7 ? 'S7' : 's89'
}
const X0: Record<string, number> = {}
SLOTS.reduce((x, s, k) => { X0[s.id] = x; return x + s.w + (k < SLOTS.length - 1 && SLOTS[k + 1]!.block !== s.block ? GAP : 0) }, 0)
const W_OF: Record<string, number> = Object.fromEntries(SLOTS.map((s) => [s.id, s.w]))
const BLOCK: Record<string, number> = Object.fromEntries(SLOTS.map((s) => [s.id, s.block]))
const UNIT = ['ln', 'z', 'ln', 'z']
const trialNo = (id: string | null) => (id ? Number(id.split('-')[1]) || null : null)

/** x of each epoch: S7 by trial (1–20), the others spread by the stage's expected epochs, squeezed if it runs long. */
function epochX(epochs: Epoch[]): Map<number, number> {
  const out = new Map<number, number>()
  const bySlot = new Map<string, Epoch[]>()
  for (const e of epochs) bySlot.set(slotOf(e.state), [...(bySlot.get(slotOf(e.state)) ?? []), e])
  for (const s of SLOTS) {
    const list = bySlot.get(s.id) ?? []
    if (s.id === 'S7') {
      const cell = s.w / TRIALS
      let last = 1
      const byTrial = new Map<number, Epoch[]>()
      for (const e of list) { last = trialNo(e.trial_id) ?? last; byTrial.set(last, [...(byTrial.get(last) ?? []), e]) }
      for (const [n, es] of byTrial) es.forEach((e, j) => out.set(e.i, X0.S7! + cell * (n - 1) + (cell * (j + 0.5)) / es.length))
    } else {
      const n = Math.max(s.expect, list.length)
      list.forEach((e, k) => out.set(e.i, X0[s.id]! + (s.w * (k + 0.5)) / n))
    }
  }
  return out
}

const REF_CHIP: Record<string, [string, string | null, boolean]> = {   // [chip, second line, solid]
  s13: ['Raw, no reference yet', null, false], S4: ['Raw, S4 baseline', null, false],
  S5: ['z vs S4 eyes open (provisional)', 'No decisions yet', false], S6: ['Building reference (S6)', null, false],
}
function referenceChip(slot: string, ref: Snapshot['indices']['reference'], ica: SessionTrace['ica']): [string, string | null, boolean] {
  if (REF_CHIP[slot]) return REF_CHIP[slot]!
  const name = !ref?.source ? 'Building reference (S6)' : ref.source === 'S6' ? (ica?.identified && ica.switched_to_nosound_at == null
    ? 'z vs S6 (ICA)' : 'z vs S6 (rule 2)') : 'z vs S4 eyes open (fallback)'
  return [name, slot === 's89' ? 'No decisions after S7' : null, true]
}

function Chip({ children, dashed = false, title }: { children: ReactNode; dashed?: boolean; title?: string }) {
  return (
    <span title={title} className={`type-caption inline-flex h-[22px] items-center gap-1.5 rounded-full border px-2.5 font-medium border-(--color-border-strong) ${dashed ? 'border-dashed' : ''}`}>
      {children}
    </span>
  )
}

const STROKE = { valid: 'stroke-(--color-accent)', invalid: 'stroke-(--color-quality-error)', grey: 'stroke-(--color-border-strong)' }
const WIDTH = { valid: 1.25, invalid: 1.75, grey: 1.5 }

function Strip({ name, k, epochs, xs, decisions, height, line, ended, readout }: {
  name: string; k: Key; epochs: Epoch[]; xs: Map<number, number>; decisions: Decision[]; height: number
  line: { x: number; text: string; warn: boolean } | null; ended: boolean; readout: ReactNode
}) {
  const top = k === 'ei' ? 12 : 0, H = height - top
  // each block its own y: z blocks −2.5..+2.5, ln blocks fit their own data
  const range = [0, 1, 2, 3].map((b) => {
    if (UNIT[b] === 'z') return [-2.5, 2.5] as const
    const v = epochs.filter((e) => BLOCK[slotOf(e.state)] === b && e[k] != null).map((e) => e[k]!)
    if (!v.length) return [-1, 1] as const
    const lo = Math.min(...v), hi = Math.max(...v), pad = Math.max(0.1, (hi - lo) * 0.1)
    return [lo - pad, hi + pad] as const
  })
  const y = (b: number, v: number) => {
    const [lo, hi] = range[b]!
    return top + H - ((Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo)) * H
  }
  const kind = (e: Epoch): keyof typeof STROKE => (e.grey ? 'grey' : !e.valid || e[k] == null ? 'invalid' : 'valid')
  // a POOR epoch has no value: it sits between its valid neighbours in the same block, in red
  const segs: ReactNode[] = []
  const blocks = [0, 1, 2, 3].map((b) => epochs.filter((e) => BLOCK[slotOf(e.state)] === b))
  blocks.forEach((list, b) => {
    const known = list.map((e) => e[k])
    const at = (j: number) => {
      if (known[j] != null) return known[j]!
      const prev = known.slice(0, j).reverse().find((v) => v != null), next = known.slice(j + 1).find((v) => v != null)
      return prev != null && next != null ? (prev + next) / 2 : prev ?? next ?? (range[b]![0] + range[b]![1]) / 2
    }
    list.forEach((e, j) => {
      const x1 = xs.get(e.i)!, x0 = j ? xs.get(list[j - 1]!.i)! : x1 - 1
      const c = ended && kind(e) === 'valid' ? 'grey' : kind(e)
      segs.push(<line key={`${b}-${e.i}`} data-epoch={kind(e)} x1={x0} x2={x1} y1={y(b, at(j ? j - 1 : j))} y2={y(b, at(j))}
        strokeWidth={WIDTH[c]} className={STROKE[c]} />)
    })
  })
  const zBlocks = [1, 3].map((b) => ({ b, x: X0[SLOTS.find((s) => s.block === b)!.id]!,
    w: SLOTS.filter((s) => s.block === b).reduce((a, s) => a + s.w, 0) }))
  const s7w = W_OF.S7! + W_OF.s89!
  const zOf = (d: Decision) => (k === 'ei' ? d.eeg_ei_z : d.eeg_theta_z)
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <h3 className="type-body-strong">{name}</h3>
        {readout}
      </div>
      <svg viewBox={`0 0 ${W} ${height}`} className="block h-auto w-full" role="img" aria-label={`${name} per epoch, for viewing only`}>
        {zBlocks.map(({ b, x, w }) => [-1, 1].map((g) => (
          <line key={`g${b}${g}`} x1={x} x2={x + w} y1={y(b, g)} y2={y(b, g)} strokeWidth={1} className="stroke-(--color-border)" />)))}
        <rect x={X0.S7} y={y(3, 1)} width={s7w} height={y(3, -1) - y(3, 1)} className="fill-(--color-explain-bg)" />
        {k === 'ei' && <>
          <line x1={X0.S7} x2={X0.S7! + s7w} y1={y(3, -1.5)} y2={y(3, -1.5)} strokeDasharray="4 3" className="stroke-(--color-quality-error)" />
          <text x={W} y={y(3, -1.5) - 2} textAnchor="end" className="fill-(--color-text-muted) text-[9px]">Lead line (−1.5)</text>
        </>}
        {[0, 1, 2, 3].map((b) => {
          const x = X0[SLOTS.find((s) => s.block === b)!.id]!
          return <text key={`u${b}`} x={x + 1} y={top + 8} className="fill-(--color-text-muted) font-mono text-[9px]">{UNIT[b]}</text>
        })}
        {SLOTS.map((s) => <line key={`t${s.id}`} x1={X0[s.id]} x2={X0[s.id]} y1={top} y2={height} className="stroke-(--color-border-subtle)" />)}
        {segs}
        {line && <line x1={line.x} x2={line.x} y1={0} y2={height} strokeWidth={1.5}
          className={line.warn ? 'stroke-(--color-quality-warn)' : 'stroke-(--color-accent)'} />}
        {k === 'ei' && line && <text x={line.x + 3} y={10} className={`text-[10px] font-semibold ${line.warn ? 'fill-(--color-quality-warn)' : 'fill-(--color-accent)'}`}>{line.text}</text>}
        {decisions.filter((d) => d.trial_sequence != null && d.trial_sequence >= 3 && zOf(d) != null).map((d) => {
          const z = zOf(d)!, cx = X0.S7! + (W_OF.S7! / TRIALS) * d.trial_sequence!, cy = y(3, z)
          const mark = d.eeg_counted === false ? 'ring' : z <= -1 ? 'low' : z >= 1 ? 'high' : 'normal'
          return (
            <g key={`p${d.trial_id}`} data-point={mark}>
              <title>{`Decision at trial ${d.trial_sequence}. ${name} z ${z.toFixed(1)}.`}</title>
              {mark === 'ring' ? <circle cx={cx} cy={cy} r={3.5} fill="none" strokeWidth={1.25} className="stroke-(--color-text)" />
                : mark === 'normal' ? <circle cx={cx} cy={cy} r={3} className="fill-(--color-text) stroke-(--color-surface)" />
                : <path d={mark === 'low' ? `M${cx - 4},${cy - 3}h8l-4,6z` : `M${cx - 4},${cy + 3}h8l-4,-6z`}
                  className="fill-(--color-text) stroke-(--color-surface)" />}
            </g>
          )
        })}
      </svg>
    </div>
  )
}

const AXIS: [string, string][] = [['s13', 'S1–3'], ['S4', 'S4'], ['S5', 'S5'], ['S6', 'S6'], ['S7', 'S7'], ['s89', 'S8–9']]
const ORDER = AXIS.map(([id]) => id)

function Legend() {
  const item = (swatch: ReactNode, text: string) => (
    <span className="type-caption inline-flex items-center gap-2">
      <svg width={16} height={10} aria-hidden>{swatch}</svg>{text}</span>)
  return (
    <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1">
      {item(<line x1={0} x2={16} y1={5} y2={5} strokeWidth={1.25} className="stroke-(--color-accent)" />, 'Epoch trace, for viewing only')}
      {item(<><path d="M1,2h7l-3.5,6z" className="fill-(--color-text)" /><circle cx={12.5} cy={5} r={3} className="fill-(--color-text)" /></>, 'Decision point, what the engine used')}
      {item(<line x1={0} x2={16} y1={5} y2={5} strokeWidth={1.75} className="stroke-(--color-quality-error)" />, 'Not valid under the active rule')}
      {item(<line x1={0} x2={16} y1={5} y2={5} strokeWidth={1.5} className="stroke-(--color-border-strong)" />, 'Not used: eyes closed or fitting ICA')}
    </div>
  )
}

export function SessionIndices({ i, s, stage, decisions, ended }: {
  i: Snapshot['indices']; s: SessionTrace; stage: string | null | undefined; decisions: Decision[]; ended: boolean
}) {
  const slot = slotOf(stage ?? 'S1')
  const reached = (id: string) => ORDER.indexOf(slot) >= ORDER.indexOf(id)
  const xs = epochX(s.epochs)
  const fitting = reached('S6') && s.ica == null
  const ruleKnown = reached('S6') && s.ica != null
  const fallback = !!s.ica && (!s.ica.identified || s.ica.switched_to_nosound_at != null)
  const line = !reached('S6') ? null : fitting ? { x: X0.S6!, text: 'Fitting ICA', warn: false }
    : s.ica!.identified ? { x: X0.S6!, text: `ICA applied, r ${(s.ica!.corr ?? 0).toFixed(2)}`, warn: false }
    : { x: X0.S6!, text: 'ICA not found, rule (2) from here', warn: true }
  const [refName, refLine, solid] = referenceChip(slot, i.reference, s.ica)
  const readout = (k: Key) => {
    if (!reached('S7') || !i.last) return null
    const counted = i.last.counted !== false
    const z = k === 'ei' ? i.last.ei_z : i.last.theta_z, band = k === 'ei' ? i.last.ei_band : i.last.theta_band
    return (
      <span className={`flex items-baseline gap-2 ${counted ? '' : 'text-(--color-text-muted)'}`}>
        <span className="type-caption">After trial {i.last.trial_id.split('-')[1]?.replace(/^0+/, '')}</span>
        {counted ? <span className="type-body font-semibold">{band === 'Low' ? '▼ ' : band === 'High' ? '▲ ' : '● '}{band}</span>
          : <span className="type-body">Not counted</span>}
        <span className="text-[24px] leading-7 font-medium">{z == null ? '—' : (z < 0 ? `−${Math.abs(z).toFixed(1)}` : `+${z.toFixed(1)}`)}</span>
      </span>
    )
  }
  return (
    <>
      <p className="type-caption mb-2 text-(--color-text-secondary)">For viewing only. Decisions use 3-trial windows from S7.</p>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        {ruleKnown && (fallback
          ? <Chip title="ICA is not active in this session. Epochs follow rule (2): the blink rule applies and task sounds are not cut. Expect more red epochs if blinks are frequent.">
              <span aria-hidden className="text-(--color-quality-warn)">▲</span>Rule: (2) fallback</Chip>
          : <Chip title="The eye component found by ICA is removed from every epoch from S6 on. The trace and the engine use the same correction.">
              <span aria-hidden className="inline-block size-2 rounded-full bg-(--color-accent)" />Rule: ICA</Chip>)}
        <Chip dashed={!solid}>{refName}{refLine && <span className="font-normal text-(--color-text-muted)">{refLine}</span>}</Chip>
        <span className="type-caption ml-auto">EEG counted in {i.windows.counted} of {i.windows.with_eeg}</span>
      </div>
      <Strip name="Engagement Index" k="ei" epochs={s.epochs} xs={xs} decisions={decisions} height={76} line={line} ended={ended} readout={readout('ei')} />
      <Strip name="Theta (Fz)" k="theta" epochs={s.epochs} xs={xs} decisions={decisions} height={64} line={line} ended={ended} readout={readout('theta')} />
      <svg viewBox={`0 0 ${W} 14`} className="block h-auto w-full" aria-label="Stages">
        {AXIS.map(([id, label]) => (
          <text key={id} x={X0[id]! + W_OF[id]! / 2} y={11} textAnchor="middle"
            className={`text-[10px] ${id === slot ? 'fill-(--color-text) font-semibold' : reached(id) ? 'fill-(--color-text-muted)' : 'fill-(--color-border-strong)'}`}>{label}</text>
        ))}
      </svg>
      <Legend />
    </>
  )
}

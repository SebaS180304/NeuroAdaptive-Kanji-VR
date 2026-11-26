import type { Schemas } from '@/api/client'

// Pure parts of the Channel traces panel (TR4), tested without a canvas.

type Bin = Schemas['LiveTraceBin']

export const WINDOW_MS = 20_000

/** min/max per pixel column over [now − 20 s, now]; null where no bin falls (a gap stays a gap). */
export function columns(bins: Bin[], ch: number, width: number, nowMs: number): ({ lo: number; hi: number } | null)[] {
  const out: ({ lo: number; hi: number } | null)[] = Array.from({ length: width }, () => null)
  const t0 = nowMs - WINDOW_MS
  for (const b of bins) {
    if (b.t_ms < t0 || b.t_ms > nowMs) continue
    const x = Math.min(width - 1, Math.floor(((b.t_ms - t0) / WINDOW_MS) * width))
    const lo = b.mins[ch]!, hi = b.maxs[ch]!
    const c = out[x]
    out[x] = c ? { lo: Math.min(c.lo, lo), hi: Math.max(c.hi, hi) } : { lo, hi }
  }
  return out
}

/** A sample out of the lane in the last second, at the chosen scale: «▲» beside the value (D-F6-297 (2)). */
export function clippedLastSecond(bins: Bin[], ch: number, nowMs: number, scale: number): boolean {
  return bins.some((b) => b.t_ms > nowMs - 1000 && (b.maxs[ch]! > scale || b.mins[ch]! < -scale))
}

const uv = (v: number) => (Math.abs(v) >= 1000 ? `${(v / 1000).toFixed(1)} mV` : `${Math.round(v)}`)

/** The «µV rms, 1 s» column: "15", "2.4 mV", "35 ▲", "—", "excluded". */
export function nowLabel(rms: number | null | undefined, clipped: boolean, excluded: boolean): string {
  if (excluded) return 'excluded'
  if (rms == null) return '—'
  return `${uv(rms)}${clipped ? ' ▲' : ''}`
}

import { useQuery } from '@tanstack/react-query'
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router'
import { getJson, type Schemas } from '@/api/client'
import { useCurrentSession } from '@/components/LiveMonitorAccess'
import { CONDITION_LABEL, type Condition } from '@/components/ConditionChip'
import { clock } from '@/lib/format'

// V1.13 Live session monitor (design-handoff/monitor, validated D-F6-233; D-F6-231, D-F6-234, D-F6-254, D-F6-265).
// Second screen, 1440 x 900, no scroll, read-only: nothing here writes or sends a command (M2 is another feature).
// One snapshot from GET /research/sessions/{id}/live every second; each section says when it last changed and
// "No data for [n] s" when its source stops. The words and z come from the engine (D-F6-234); nothing is recomputed.

type Snapshot = Schemas['LiveSnapshot']
type Decision = Schemas['LiveDecision']

/** M1b's per-channel figures (live.py, eeg_sessions.monitor; the EEG chat's table of 19 Nov 12:45, D-F6-254). */
type Channel = {
  label: string; l60_uv: number | null; rms_uv: number | null; over_pct: number | null
  status: 'OK' | 'Watch' | 'Bad' | 'No data'; flat: boolean; sync_tap: boolean; mark_60: boolean
}
type Quality = { age_s: number | null; session_60_uv: number | null; session_60_status: 'OK' | 'Watch'; channels: Channel[] }

const POLL_MS = 1000
/** V1.13 sessionEnded (D-F6-270 (4)): the panels keep their last data in the stale style. */
const Ended = createContext(false)
const STALE_S = 5   // a source silent this long reads "No data for [n] s" (D-F6-231 (4))

// TODO(design): V1.13 names only S7; the others show their code and the state's own words until UI/UX names them.
const STAGE_NAME: Record<string, string> = { S7: 'Adaptive practice', SR: 'Block R' }
function stageTitle(stage: string | null | undefined): string {
  if (!stage) return '—'
  const [code, ...rest] = stage.split('_')
  const words = rest.join(' ').toLowerCase()
  return `${code} ${STAGE_NAME[code!] ?? words.charAt(0).toUpperCase() + words.slice(1)}`
}

const minus = (n: number) => (n < 0 ? `−${Math.abs(n).toFixed(1)}` : `+${n.toFixed(1)}`)

const panel = 'flex min-h-0 flex-col rounded-(--radius-panel) border px-5 py-4'
const fresh = 'border-(--color-border) bg-(--color-surface)'
const stale = 'border-dashed border-(--color-border-strong) bg-(--color-bg) text-(--color-text-muted)'

function Section({ title, updated, children, className = '' }:
  { title: string; updated?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section aria-label={title} className={`${panel} ${useContext(Ended) ? stale : fresh} ${className}`}>
      <div className="mb-3 flex items-baseline justify-between gap-4">
        <h2 className="type-subtitle font-heading">{title}</h2>
        {updated && <span className="type-caption text-(--color-text-muted)">{updated}</span>}
      </div>
      {children}
    </section>
  )
}

function Dot({ kind }: { kind: 'ok' | 'warn' | 'error' | 'none' }) {
  // Never color alone: every dot sits next to its word (design-system.md, D-F6-231 (4)).
  const color = { ok: 'bg-(--color-quality-ok)', warn: 'bg-(--color-quality-warn)',
    error: 'bg-(--color-quality-error)', none: 'border border-(--color-text-muted)' }[kind]
  const shape = kind === 'warn' ? 'rotate-45 rounded-[1px]' : 'rounded-full'
  return <span aria-hidden className={`inline-block size-2.5 shrink-0 ${shape} ${color}`} />
}

function Row({ k, children }: { k: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[160px_1fr] gap-x-4 py-1">
      <dt className="type-body text-(--color-text-muted)">{k}</dt>
      <dd className="type-body m-0">{children}</dd>
    </div>
  )
}

const ago = (s: number | null | undefined) => (s == null ? '—' : s < 2 ? '1 s ago' : `${Math.round(s)} s ago`)
const noData = (s: number | null | undefined) => (s != null && s > STALE_S ? `No data for ${Math.round(s)} s` : null)

function TopBar({ s, elapsed }: { s: Snapshot['session']; elapsed: number | null }) {
  const meta: [string, ReactNode, boolean][] = [
    ['Session', s.session_id.slice(0, 8), true], ['Participant', s.external_code, true],
    ['Condition', CONDITION_LABEL[s.condition as Condition] ?? s.condition, false],
    ['Set', s.set ?? '—', false], ['Visit', s.visit ?? '—', false],
  ]
  return (
    <header className="grid h-[88px] shrink-0 grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-6 bg-(--color-sidebar) px-6 text-(--color-sidebar-text)">
      <div className="flex min-w-0 flex-col gap-0.5">
        <span className="type-caption text-(--color-sidebar-muted)">Live session monitor</span>
        <span className="font-heading text-[36px] leading-10 font-medium tracking-[-0.36px] whitespace-nowrap">
          {stageTitle(s.stage)}
        </span>
      </div>
      <div className="flex flex-col items-center gap-0.5">
        <span className="font-mono text-[30px] leading-9 font-medium">{elapsed == null ? '—' : clock(elapsed)}</span>
        <span className="type-caption text-(--color-sidebar-muted)">since the session started</span>
      </div>
      <dl className="m-0 flex items-baseline justify-end gap-5">
        {meta.map(([k, v, mono]) => (
          <span key={k} className="flex flex-col">
            <dt className="type-caption text-(--color-sidebar-muted)">{k}</dt>
            <dd className={`m-0 ${mono ? 'font-mono' : ''}`}>{v}</dd>
          </span>
        ))}
      </dl>
    </header>
  )
}

function SignalQuality({ q, heartbeat }: { q: Quality | null; heartbeat: number | null | undefined }) {
  if (!q) {
    return (
      <Section title="Signal quality" updated="Off">
        <p className="type-body text-(--color-text-muted)">
          Waiting for live.py. The per-channel figures are switched off until they are turned on for a session.
        </p>
      </Section>
    )
  }
  const word = { OK: 'ok', Watch: 'warn', Bad: 'error', 'No data': 'none' } as const
  return (
    <Section title="Signal quality" updated={noData(q.age_s) ?? `Updated ${ago(q.age_s)}`}>
      <table className="type-body w-full border-collapse tabular-nums" aria-label="Channels">
        <thead>
          <tr className="type-caption text-left text-(--color-text-muted)">
            <th className="py-1 font-normal">Channel</th><th className="font-normal">Last 5 s</th>
            <th className="text-right font-normal">60 Hz (µV)</th><th className="text-right font-normal">RMS (µV)</th>
            <th className="text-right font-normal">% &gt; 100 µV</th>
          </tr>
        </thead>
        <tbody>
          {q.channels.map((c) => (
            <tr key={c.label} className="border-t border-(--color-border-subtle)">
              <td className="py-1.5 font-mono">{c.label}</td>
              <td><span className="inline-flex items-center gap-2"><Dot kind={word[c.status]} />{c.status}
                {c.flat && ' · flat'}
                {c.sync_tap && <span className="type-caption text-(--color-text-muted)">Sync tap</span>}</span></td>
              <td className="text-right">{c.l60_uv == null ? '—' : Math.round(c.l60_uv)}{c.mark_60 && ' ◇'}</td>
              <td className="text-right">{c.rms_uv == null ? '—' : Math.round(c.rms_uv)}</td>
              <td className="text-right">{c.over_pct == null ? '—' : c.over_pct.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="type-body mt-3 flex items-center gap-2">
        <Dot kind={q.session_60_status === 'OK' ? 'ok' : 'warn'} />{q.session_60_status} · 60 Hz, median of 8:{' '}
        <strong>{q.session_60_uv == null ? '—' : `${Math.round(q.session_60_uv)} µV`}</strong>
        <span className="type-caption text-(--color-text-muted)">warning from 800 µV</span>
      </p>
      <p className="type-caption mt-2 text-(--color-text-muted)">
        Share of samples over 100 µV in the last 5 s, leaving out ±1 s around each sync tap. OK under 5 %. Watch 5–20 %,
        or the last 30 s over 20 %. Bad over 20 %, or flat. ◇ on 60 Hz: under 0.3× or over 3× the others.
        Sync tap: the taps cover the last 5 s, so the earlier colour stays.
        {heartbeat != null && heartbeat > STALE_S && ` live.py: no data for ${Math.round(heartbeat)} s.`}
      </p>
    </Section>
  )
}

function Trace({ points, pick }: { points: Snapshot['indices']['trace']; pick: 'ei_z' | 'theta_z' }) {
  // z from -3 to +3; the band -1..+1 and the dashed -1.5 line of V1.13 (D-F6-234). No label on the trace.
  const W = 420, H = 44, y = (z: number) => H / 2 - (Math.max(-3, Math.min(3, z)) / 3) * (H / 2)
  const pts = points.filter((p) => p[pick] != null).slice(-60)
  const x = (i: number) => (pts.length < 2 ? W / 2 : (i / (pts.length - 1)) * W)
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-11 w-full" role="img" aria-label={`${pick === 'ei_z' ? 'Engagement Index' : 'Frontal theta'} per epoch`}>
      <rect x="0" y={y(1)} width={W} height={y(-1) - y(1)} className="fill-(--color-accent-tint)" />
      {pick === 'ei_z' && <line x1="0" x2={W} y1={y(-1.5)} y2={y(-1.5)} strokeDasharray="4 3" className="stroke-(--color-alert)" />}
      <polyline fill="none" strokeWidth="1.5" className="stroke-(--color-accent)"
        points={pts.map((p, i) => `${x(i)},${y(p[pick]!)}`).join(' ')} />
    </svg>
  )
}

function Index({ name, z, band, points, pick, beforeRef }:
  { name: string; z: number | null | undefined; band: string | null | undefined; points: Snapshot['indices']['trace']
    pick: 'ei_z' | 'theta_z'; beforeRef: boolean }) {
  const counted = band && band !== 'Not counted'
  return (
    <div className="mb-3">
      <div className="flex items-baseline justify-between">
        <h3 className="type-body-strong">{name}</h3>
        {beforeRef ? <span className="type-body text-(--color-text-muted)">Reference after S6</span>
          : band === 'Not counted' ? <span className="type-body text-(--color-text-muted)">Not counted</span>
          : (
            <span className="flex items-baseline gap-2">
              {band === 'Low' && <span aria-hidden>▼</span>}{band === 'High' && <span aria-hidden>▲</span>}
              <span className="type-body">{band ?? '—'}</span>
              <span className={`text-[24px] font-medium ${counted ? '' : 'text-(--color-text-muted)'}`}>
                {z == null ? '—' : minus(z)}</span>
            </span>
          )}
      </div>
      <Trace points={points} pick={pick} />
    </div>
  )
}

function LiveIndices({ i, heartbeat }: { i: Snapshot['indices']; heartbeat: number | null | undefined }) {
  const beforeRef = !i.last
  const pct = i.windows.with_eeg ? Math.round((100 * i.windows.counted) / i.windows.with_eeg) : null
  const ref = i.reference
  return (
    <Section title="Live indices" updated={noData(heartbeat) ?? (i.last ? `z per decision window, last after ${i.last.trial_id}` : 'Waiting for S7')}>
      <Index name="Engagement Index" z={i.last?.ei_z} band={i.last?.ei_band} points={i.trace} pick="ei_z" beforeRef={beforeRef} />
      <Index name="Frontal theta (Fz)" z={i.last?.theta_z} band={i.last?.theta_band} points={i.trace} pick="theta_z" beforeRef={beforeRef} />
      <dl className="m-0">
        <Row k="EEG counted">{i.windows.with_eeg ? `${i.windows.counted} of ${i.windows.with_eeg} windows (${pct} %)` : '—'}</Row>
        <Row k="Reference">{!ref?.source ? (beforeRef ? 'Reference after S6' : 'None')
          : ref.source === 'S6' ? `S6 (${ref.n_epochs} epochs not POOR)` : `S4 eyes open (fallback, ${ref.n_epochs} epochs)`}</Row>
      </dl>
      <p className="type-caption mt-2 text-(--color-text-muted)">
        Zones use the engine's reference: Low z ≤ −1, High z ≥ +1. The word is the decision window's, for reading only.
        Dashed: −1.5, the EEG leads.
      </p>
    </Section>
  )
}

const STATE_DOT: Record<string, string> = {
  STABLE: 'bg-(--color-state-stable)', DISENGAGED: 'bg-(--color-state-disengaged)',
  OVERLOADED: 'bg-(--color-state-overloaded)', UNDERCHALLENGED: 'bg-(--color-state-underchallenged)',
}
const title = (w: string | null | undefined) => (w ? w.charAt(0) + w.slice(1).toLowerCase() : '—')

function decisionLine(d: Decision): string {
  if (d.action === 'NO_CHANGE') return 'No change'
  return `${d.dimension ?? ''} ${d.from_level ?? ''} → ${d.to_level ?? ''}`.trim()
}

function Decisions({ list }: { list: Decision[] }) {
  return (
    <Section title="Adaptation decisions" className="min-h-0 flex-1"
      updated={(n => `${n} ${n === 1 ? 'change' : 'changes'}`)(list.filter((d) => d.action !== 'NO_CHANGE').length)}>
      {list[0] && (
        <dl className="m-0 mb-2 grid grid-cols-[48px_1fr] gap-x-3">
          <dt className="type-body text-(--color-text-muted)">ESL</dt><dd className="type-body m-0">{title(list[0].esl)}</dd>
          <dt className="type-body text-(--color-text-muted)">LAL</dt><dd className="type-body m-0">{title(list[0].lal)}</dd>
        </dl>
      )}
      <ol className="m-0 min-h-0 flex-1 list-none overflow-hidden p-0">
        {list.slice(0, 6).map((d) => (
          <li key={`${d.trial_id}-${d.decided_elapsed_ms}`} className="grid grid-cols-[88px_1fr_auto] gap-x-3 border-t border-(--color-border-subtle) py-2">
            <span className="type-body whitespace-nowrap text-(--color-text-muted)">
              <span aria-hidden>{d.action === 'NO_CHANGE' ? '◇' : '◆'} </span>After {d.trial_sequence ?? '—'}
            </span>
            <span className="type-body inline-flex flex-wrap items-center gap-x-2">
              <span aria-hidden className={`inline-block size-2.5 rounded-full ${STATE_DOT[d.learner_state ?? ''] ?? 'border border-(--color-text-muted)'}`} />
              {title(d.learner_state)}
              {d.eeg_effect && <span className="font-mono">EEG_{d.eeg_effect}</span>}
            </span>
            <span className={`type-body text-right ${d.action === 'NO_CHANGE' ? '' : 'font-medium'}`}>{decisionLine(d)}</span>
          </li>
        ))}
        {list.length === 0 && <li className="type-body text-(--color-text-muted)">No decision yet.</li>}
      </ol>
    </Section>
  )
}

function Events({ list }: { list: Snapshot['events'] }) {
  return (
    <Section title="Events" updated="Live" className="min-h-0 flex-1">
      <p className="type-caption mb-2 text-(--color-text-muted)">Newest first. Grey is routine; a triangle marks one to look at.</p>
      <ol className="m-0 min-h-0 flex-1 list-none overflow-hidden p-0">
        {list.map((e, n) => (
          <li key={n} className="type-body flex gap-3 border-t border-(--color-border-subtle) py-1">
            <span className="font-mono text-(--color-text-muted)">{e.elapsed_ms == null ? '—' : clock(e.elapsed_ms)}</span>
            {e.flag === 'look' && <span aria-label="look at this" className="text-(--color-lal-high)">▲</span>}
            <span className={`font-mono ${e.flag === 'decision' ? 'text-(--color-accent)' : e.flag ? 'font-medium' : 'text-(--color-text-secondary)'}`}>
              {e.event_type}</span>
            {e.trial_id && <span className="text-(--color-text-muted)">{e.trial_id}</span>}
          </li>
        ))}
      </ol>
    </Section>
  )
}

function Sync({ s }: { s: Snapshot['sync'] }) {
  const within = s?.robust_spread_ms != null && s.robust_spread_ms <= 50
  return (
    <Section title="Sync" updated="Measured after S3">
      <dl className="m-0">
        <Row k="S3 taps">{s?.taps ? `${s.clear_taps} of ${s.taps} clear` : '—'}</Row>
        <Row k="Offset">{s?.offset_ms == null ? '—' : `${s.offset_ms.toFixed(1)} ms`}</Row>
        <Row k="Dispersion (robust)">
          {s?.robust_spread_ms == null ? '—' : (
            <span className="inline-flex items-center gap-2">{s.robust_spread_ms.toFixed(1)} ms
              <Dot kind={within ? 'ok' : 'warn'} />{within ? 'Within 50 ms' : 'Over 50 ms'}</span>)}
        </Row>
      </dl>
    </Section>
  )
}

function System({ s }: { s: Snapshot['system'] }) {
  const alpha = s?.alpha_ratio as Record<string, number> | null | undefined
  return (
    <Section title="System" updated={s ? `Updated ${ago(0)}` : undefined}>
      <dl className="m-0">
        <Row k="LabRecorder">—</Row>
        <Row k="autorun">—</Row>
        <Row k="live.py">{s?.heartbeat_age_s == null ? '—' : (
          <span className="inline-flex items-center gap-2"><Dot kind={s.heartbeat_age_s > STALE_S ? 'warn' : 'ok'} />
            Heartbeat {ago(s.heartbeat_age_s)}</span>)}</Row>
        <Row k="Excluded channel">{s?.bad_channel ?? (s ? 'None' : '—')}</Row>
        <Row k="S4 alpha ratio">{alpha ? `${Object.entries(alpha).map(([k, v]) => `${k} ${v.toFixed(1)}`).join(', ')}. `
          + (s?.alpha_passed ? 'Passes (≥ 1.2)' : 'Does not pass (≥ 1.2)') : '—'}</Row>
      </dl>
    </Section>
  )
}

function useClock(snap: Snapshot | undefined, fetchedAt: number): number | null {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 250); return () => clearInterval(t) }, [])
  const base = snap?.session.elapsed_ms
  if (base == null) return null
  return snap!.session.status === 'IN_PROGRESS' ? base + Math.max(0, now - fetchedAt) : base
}

const HMS = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })

/** V1.13 sessionEnded (Contenido_UI_Monitor_Accesos.md §3.1, D-F6-270 (4)): only on /monitor/<id>. */
function EndedBanner({ s }: { s: Snapshot['session'] }) {
  return (
    <div role="status" className="type-body flex shrink-0 items-center gap-3 border-b border-(--color-border) bg-(--color-surface) px-6 py-2.5">
      <span aria-hidden className="inline-block size-2.5 rounded-full border border-(--color-text-muted)" />
      <strong>This session has ended</strong>
      <span className="text-(--color-text-muted)">
        Session {s.session_id.slice(0, 8)} closed at {s.completed_at ? HMS.format(new Date(s.completed_at)) : '—'}. Its data is in
        the session view.
      </span>
      <Link to={`/sessions/${s.session_id}`} className="font-semibold text-(--color-accent) underline">Open session view</Link>
    </div>
  )
}

function Monitor({ sessionId, pinned }: { sessionId: string; pinned: boolean }) {
  const { data, error, dataUpdatedAt } = useQuery({
    queryKey: ['live', sessionId],
    queryFn: () => getJson<Snapshot>(`/research/sessions/${sessionId}/live`),
    refetchInterval: POLL_MS,
  })
  const elapsed = useClock(data, dataUpdatedAt)
  if (!data) {
    return <Frame><p className="type-body p-6">{error ? 'The backend does not answer. Nothing is shown until it does.' : 'Loading the session…'}</p></Frame>
  }
  const heartbeat = data.system?.heartbeat_age_s
  // /monitor/<id> keeps a session that ended, marked; /monitor (the rail) never gets here with one (it waits instead)
  const ended = pinned && data.session.status !== 'IN_PROGRESS'
  return (
    <Frame>
      <Ended.Provider value={ended}>
      <TopBar s={data.session} elapsed={elapsed} />
      {ended ? <EndedBanner s={data.session} /> : (
        <p className="type-body shrink-0 border-b border-(--color-border) px-6 py-2.5 text-(--color-text-secondary)">
          Read only. Nothing on this screen changes the session.
        </p>
      )}
      <main className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,0.9fr)] gap-6 p-6">
        <div className="flex min-h-0 flex-col gap-6">
          <SignalQuality q={data.signal_quality as Quality | null} heartbeat={heartbeat} />
          <System s={data.system} />
        </div>
        <div className="flex min-h-0 flex-col gap-6">
          <LiveIndices i={data.indices} heartbeat={heartbeat} />
          <Decisions list={data.decisions} />
        </div>
        <div className="flex min-h-0 flex-col gap-6">
          <Sync s={data.sync} />
          <Events list={data.events} />
        </div>
      </main>
      </Ended.Provider>
    </Frame>
  )
}

function Frame({ children }: { children: ReactNode }) {
  return <div className="flex h-[900px] w-[1440px] flex-col overflow-hidden bg-(--color-bg) text-(--color-text) tabular-nums">{children}</div>
}

/** /monitor follows the newest session in progress; /monitor/:sessionId pins one. */
export function LiveMonitor() {
  const { sessionId } = useParams()
  // D-F6-270 (3): the IN_PROGRESS session with the latest event, the same rule as the rail's "Live monitor"
  const current = useCurrentSession()
  const id = sessionId ?? current?.session_id
  if (!id) {
    return (
      <Frame>
        <div className="p-6">
          <p className="type-subtitle font-heading">Waiting for a new session</p>
          <p className="type-body text-(--color-text-muted)">The monitor will show the next session when it starts. Nothing to do here.</p>
        </div>
      </Frame>
    )
  }
  return <Monitor key={id} sessionId={id} pinned={!!sessionId} />
}

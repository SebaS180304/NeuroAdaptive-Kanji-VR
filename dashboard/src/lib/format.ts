// Display helpers shared by the screens.

const DATE = new Intl.DateTimeFormat('en-CA', { year: 'numeric', month: '2-digit', day: '2-digit' })

/** Local calendar date, YYYY-MM-DD. */
export function formatDate(iso: string): string {
  return DATE.format(new Date(iso))
}

/** A 0-1 ratio as "81.6 %". */
export function formatPercent(ratio: number): string {
  return `${(ratio * 100).toFixed(1)} %`
}

const TIME = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit' })

/** Local time of day, HH:MM. */
export function formatTime(iso: string): string {
  return TIME.format(new Date(iso))
}

/** A duration in ms as "m:ss". */
export function formatDuration(ms: number): string {
  const s = Math.round(ms / 1000)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

/** A Game Flow state's code: "S7_EXPERIMENTAL_RETRIEVAL" → "S7", "S10_HCI_SELF_REPORT" → "S10". */
export function stateCode(state: string): string {
  return state.split('_')[0]!
}

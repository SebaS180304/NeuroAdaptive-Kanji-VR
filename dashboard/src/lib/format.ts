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

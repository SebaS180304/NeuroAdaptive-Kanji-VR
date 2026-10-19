/** Nested objects as dotted keys, one value per line; values exactly as stored. */
export function flatten(values: Record<string, unknown>, prefix = ''): [string, string][] {
  return Object.entries(values).flatMap(([k, v]): [string, string][] =>
    v !== null && typeof v === 'object' && !Array.isArray(v)
      ? flatten(v as Record<string, unknown>, `${prefix}${k}.`)
      : [[`${prefix}${k}`, typeof v === 'string' ? v : JSON.stringify(v)]])
}

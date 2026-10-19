/**
 * Nested objects as dotted keys, values exactly as stored. The flag marks a value that
 * goes as JSON on its own line under its key: an array, or an object with nothing inside.
 */
export function flatten(values: Record<string, unknown>, prefix = ''): [string, string, boolean][] {
  return Object.entries(values).flatMap(([k, v]): [string, string, boolean][] => {
    const key = `${prefix}${k}`
    if (v !== null && typeof v === 'object' && !Array.isArray(v) && Object.keys(v).length > 0)
      return flatten(v as Record<string, unknown>, `${key}.`)
    if (v !== null && typeof v === 'object') return [[key, JSON.stringify(v), true]]
    return [[key, typeof v === 'string' ? v : JSON.stringify(v), false]]
  })
}

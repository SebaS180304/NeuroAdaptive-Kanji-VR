import type { components } from './schema'

export type Schemas = components['schemas']

/** The backend answered with an error status (a network failure is a TypeError instead). */
export class ApiError extends Error {
  readonly status: number
  readonly detail: unknown
  constructor(status: number, detail: unknown) {
    super(`API answered ${status}`)
    this.status = status
    this.detail = detail
  }
}

// Same origin: Vite proxies /api to the backend (vite.config.ts), so nothing leaves 127.0.0.1.
async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const resp = await fetch(`/api${path}`, {
    method,
    ...(body === undefined ? {} : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  })
  const data = await resp.json().catch(() => null)
  if (!resp.ok) throw new ApiError(resp.status, (data as { detail?: unknown } | null)?.detail)
  return data as T
}

export const getJson = <T,>(path: string) => request<T>('GET', path)
export const postJson = <T,>(path: string, body: unknown) => request<T>('POST', path, body)

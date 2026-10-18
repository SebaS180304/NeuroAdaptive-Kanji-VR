import type { components } from './schema'

export type Schemas = components['schemas']

// Same origin: Vite proxies /api to the backend (vite.config.ts), so nothing leaves 127.0.0.1.
export async function getJson<T>(path: string): Promise<T> {
  const resp = await fetch(`/api${path}`)
  if (!resp.ok) throw new Error(`GET ${path} answered ${resp.status}`)
  return (await resp.json()) as T
}

import { vi } from 'vitest'

type Handler = (body: unknown) => Response | Promise<Response>

/**
 * Stubs fetch with one handler per "METHOD /api/path". An unexpected call fails
 * the test; `calls` keeps every request body for assertions.
 */
export function mockApi(handlers: Record<string, Handler>) {
  const calls: { key: string; body: unknown }[] = []
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    const key = `${init?.method ?? 'GET'} ${url}`
    const body = init?.body ? JSON.parse(String(init.body)) : undefined
    calls.push({ key, body })
    const handler = handlers[key]
    if (!handler) throw new Error(`unexpected request ${key}`)
    return handler(body)
  }))
  return calls
}

export const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status })
export const offline = () => Promise.reject(new TypeError('Failed to fetch'))

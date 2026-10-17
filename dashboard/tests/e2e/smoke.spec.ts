import { connect } from 'node:net'
import { networkInterfaces } from 'node:os'
import { expect, test } from '@playwright/test'

const SCREENS = ['/sessions', '/sessions/6eb2bd5c', '/participants', '/participants/abc', '/pretest', '/quality', '/tokens']

// Skill rule 7: no outbound request, fonts included.
test('every screen loads with no request outside 127.0.0.1:5300', async ({ page }) => {
  const outside: string[] = []
  page.on('request', (req) => {
    const url = new URL(req.url())
    if (url.protocol !== 'data:' && url.host !== '127.0.0.1:5300') outside.push(req.url())
  })
  for (const path of SCREENS) {
    await page.goto(path)
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('heading', { level: 1 })).toBeAttached()
  }
  expect(outside).toEqual([])
})

test('the bundled fonts are the ones in use', async ({ page }) => {
  await page.goto('/tokens')
  await page.evaluate(() => document.fonts.ready)
  const loaded = await page.evaluate(() =>
    ['500 36px "Newsreader Variable"', '400 14px "Public Sans"', '400 12px "JetBrains Mono"', '500 176px "Noto Serif JP"']
      .map((f) => [f, document.fonts.check(f, f.includes('Noto') ? '月' : 'a')]))
  for (const [font, ok] of loaded) expect(ok, font as string).toBe(true)
})

// The dev server must not answer on the machine's network addresses.
test('the dev server is not reachable from the LAN address', async () => {
  const lan = Object.values(networkInterfaces()).flat()
    .filter((i) => i && i.family === 'IPv4' && !i.internal).map((i) => i!.address)
  test.skip(lan.length === 0, 'no network interface')
  for (const host of lan) {
    const reachable = await new Promise<boolean>((resolve) => {
      const socket = connect({ host, port: 5300, timeout: 1000 })
      socket.once('connect', () => { socket.destroy(); resolve(true) })
      socket.once('error', () => resolve(false))
      socket.once('timeout', () => { socket.destroy(); resolve(false) })
    })
    expect(reachable, host).toBe(false)
  }
})

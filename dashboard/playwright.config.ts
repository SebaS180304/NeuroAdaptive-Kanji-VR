import { defineConfig, devices } from '@playwright/test'

// Smoke and screenshot checks against the Vite dev server (127.0.0.1 only).
export default defineConfig({
  testDir: './tests/e2e',
  outputDir: './test-results',
  reporter: 'list',
  use: { baseURL: 'http://127.0.0.1:5300', viewport: { width: 1440, height: 900 } },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } }],
  webServer: { command: 'npm run dev', url: 'http://127.0.0.1:5300', reuseExistingServer: true },
})

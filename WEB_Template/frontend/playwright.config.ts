import { defineConfig, devices } from '@playwright/test';

/**
 * Smoke testy v prohlížeči (T-378) proti běžící aplikaci: backend `./dev.sh local` (FHIR v paměti, mock AI)
 * a frontend (`next start` v CI, `next dev` lokálně). Servery nespouští Playwright, jen se na ně připojí:
 *   E2E_BASE_URL (výchozí http://localhost:3000), E2E_API_URL (výchozí http://localhost:8000).
 * Spuštění: `npx playwright test --trace off` (trasování jen při ladění: `--trace on`).
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:3000',
    locale: 'cs-CZ',
    timezoneId: 'Europe/Prague',
    screenshot: 'only-on-failure',
    trace: 'off',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});

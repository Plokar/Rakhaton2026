import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';

// T-383: jednotkové testy čisté logiky frontendu (normalita údajů, slidy, hlasové příkazy). Prohlížeč testuje Playwright (e2e/).
export default defineConfig({
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  test: { include: ['src/**/*.test.ts'], environment: 'node' },
});

import { defineConfig } from 'playwright';

export default defineConfig({
  use: {
    baseURL: process.env.OPENROUNDS_BASE_URL ?? 'https://pro.innovator.org',
    headless: process.env.HEADLESS === '1',
    trace: 'on-first-retry'
  },
  timeout: 120_000
});

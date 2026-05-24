import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';
import { storageStatePath } from './_paths.js';

async function main() {
  const baseURL = process.env.OPENROUNDS_BASE_URL ?? 'https://pro.innovator.org';
  const startUrl = process.env.OPENROUNDS_AUTH_URL ?? `${baseURL}/open-rounds`;

  await fs.mkdir(path.dirname(storageStatePath()), { recursive: true });

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log(`Opening ${startUrl}`);
  console.log('Log in manually, then navigate to Open Rounds.');
  console.log('When you see the Open Rounds page, come back here and press Enter in the terminal.');

  await page.goto(startUrl, { waitUntil: 'domcontentloaded' });

  await new Promise<void>((resolve) => {
    process.stdin.resume();
    process.stdin.setEncoding('utf8');
    process.stdin.once('data', () => resolve());
  });

  await context.storageState({ path: storageStatePath() });
  console.log(`Saved storage state to ${storageStatePath()}`);

  await browser.close();
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});

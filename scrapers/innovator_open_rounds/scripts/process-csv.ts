import fs from 'node:fs/promises';
import path from 'node:path';
import { parse } from 'csv-parse/sync';
import sanitize from 'sanitize-filename';
import { chromium } from 'playwright';
import { downloadsOpenRoundsRoot, runOutputDir } from './_paths.js';
import type { CompanyRow } from './scrape-open-rounds.js';

type Link = { label: string; url: string };

function safeCompanyDirName(row: CompanyRow) {
  const base = row.companyName?.trim() ? row.companyName.trim() : `company-${row.companyId || 'unknown'}`;
  const cleaned = sanitize(base).replace(/\s+/g, ' ').trim();
  return row.companyId ? `${cleaned} (${row.companyId})` : cleaned;
}

function parseJson<T>(s?: string): T | undefined {
  if (!s) return undefined;
  try {
    return JSON.parse(s) as T;
  } catch {
    return undefined;
  }
}

async function downloadToFile(url: string, outPath: string) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Fetch failed ${res.status} ${res.statusText} for ${url}`);
  const buf = Buffer.from(await res.arrayBuffer());
  await fs.writeFile(outPath, buf);
}

function isPitchDeckLink(url: string) {
  // Most pitch decks are PDFs from media.innovator.org; we intentionally skip these.
  return /media\.innovator\.org\/.+\.pdf(\?|$)/i.test(url);
}

async function writeCompanyPdf(outDir: string, row: CompanyRow) {
  const html = `<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>${row.companyName || row.companyId || 'Company'}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; padding: 24px; }
    h1 { margin: 0 0 6px; }
    .muted { color: #555; font-size: 12px; }
    h2 { margin-top: 18px; }
    table { border-collapse: collapse; width: 100%; }
    td, th { border: 1px solid #ddd; padding: 6px 8px; vertical-align: top; }
    th { background: #f7f7f7; text-align: left; }
    code { white-space: pre-wrap; }
  </style>
</head>
<body>
  <h1>${row.companyName || '(missing name)'}</h1>
  <div class="muted">Company ID: ${row.companyId || ''}</div>
  <div class="muted">Portal URL: ${row.companyUrl || ''}</div>
  <div class="muted">Website: ${row.websiteUrl || ''}</div>

  <h2>Open Deal</h2>
  <code>${row.openDeal ?? ''}</code>

  <h2>General Information</h2>
  <code>${row.generalInformation ?? ''}</code>

  <h2>All Deals</h2>
  <code>${row.allDeals ?? ''}</code>

  <h2>Product & Regulatory</h2>
  <code>${row.productRegulatoryInformation ?? ''}</code>

  <h2>Team Members</h2>
  <code>${row.teamMembers ?? ''}</code>

  <h2>Links</h2>
  <code>${JSON.stringify({
    productImages: parseJson<Link[]>(row.productImages) ?? [],
    productVideos: parseJson<Link[]>(row.productVideos) ?? [],
    pitchDecks: parseJson<Link[]>(row.pitchDecks) ?? []
  }, null, 2)}</code>
</body>
</html>`;

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.setContent(html, { waitUntil: 'domcontentloaded' });
  await page.pdf({ path: path.join(outDir, 'company.pdf'), format: 'Letter', printBackground: true });
  await browser.close();
}

async function main() {
  const csvPath = process.env.OPENROUNDS_CSV_IN ?? path.join(process.cwd(), 'open-rounds.csv');
  const runId = process.env.RUN_ID ?? new Date().toISOString().replace(/[:.]/g, '-');
  const outRoot = runOutputDir(runId);

  await fs.mkdir(downloadsOpenRoundsRoot(), { recursive: true });
  await fs.mkdir(outRoot, { recursive: true });

  const csv = await fs.readFile(csvPath, 'utf8');
  const records = parse(csv, { columns: true, skip_empty_lines: true }) as CompanyRow[];

  // Save the input CSV alongside the run
  await fs.writeFile(path.join(outRoot, 'open-rounds.csv'), csv);

  console.log(`Processing ${records.length} companies into ${outRoot}`);

  for (let i = 0; i < records.length; i++) {
    const row = records[i]!;
    const companyDir = path.join(outRoot, safeCompanyDirName(row));
    await fs.mkdir(companyDir, { recursive: true });

    // Write a per-company CSV (single row)
    const headers = Object.keys(row) as (keyof CompanyRow)[];
    const line = headers.map((h) => JSON.stringify((row as any)[h] ?? '')).join(',');
    await fs.writeFile(path.join(companyDir, 'company.csv'), `${headers.join(',')}\n${line}\n`);

    // Download non-deck media (images only for now)
    const images = parseJson<Link[]>(row.productImages) ?? [];
    if (images.length) {
      const mediaDir = path.join(companyDir, 'media');
      await fs.mkdir(mediaDir, { recursive: true });

      for (const img of images) {
        const u = img.url;
        if (!u || isPitchDeckLink(u)) continue;
        const ext = path.extname(new URL(u).pathname) || '.bin';
        const fileBase = sanitize(img.label || 'image').slice(0, 120) || 'image';
        const outPath = path.join(mediaDir, `${fileBase}${ext}`);
        try {
          await downloadToFile(u, outPath);
        } catch (e) {
          // Keep going; network or auth issues can happen
          console.warn(`Failed to download ${u}:`, e);
        }
      }
    }

    // Generate PDF summary from scraped info
    try {
      await writeCompanyPdf(companyDir, row);
    } catch (e) {
      console.warn(`Failed to generate PDF for ${row.companyName || row.companyId}:`, e);
    }

    if ((i + 1) % 10 === 0) console.log(`... ${i + 1}/${records.length}`);
  }

  console.log('Done.');
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});

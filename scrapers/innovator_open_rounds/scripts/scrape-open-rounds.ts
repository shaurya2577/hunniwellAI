import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium, type Page } from 'playwright';
import { stringify } from 'csv-stringify/sync';
import { ensurePosixUrl, storageStatePath } from './_paths.js';

type KV = { label: string; value: string };
type Link = { label: string; url: string };
type TeamMember = { name: string; title: string; bio: string; imageUrl?: string };

export type CompanyRow = {
  companyId: string;
  companyName: string;
  companyUrl: string;
  websiteUrl?: string;

  // Summary card
  summaryHeadline?: string; // e.g. "15M Series A - target closing ..."
  summaryTagline?: string;
  summaryLocation?: string;
  summaryYearFounded?: string;
  summaryCurrentRunway?: string;
  summaryTeam?: string;
  summaryUrgency?: string;
  summaryDevelopmentStage?: string;
  summaryRegulatoryPathway?: string;
  summaryCategory?: string;

  // Sections (as key/value pairs)
  openDeal?: string; // JSON
  generalInformation?: string; // JSON
  allDeals?: string; // JSON
  productRegulatoryInformation?: string; // JSON

  // Media/links
  pitchDecks?: string; // JSON Link[] (download links)
  productImages?: string; // JSON Link[] (src)
  productVideos?: string; // JSON Link[] (youtube/external)
  teamMembers?: string; // JSON TeamMember[]
};

function textOrEmpty(s: string | null | undefined) {
  return (s ?? '').replace(/\s+/g, ' ').trim();
}

async function extractDl(page: Page, containerSelector: string): Promise<KV[]> {
  const exists = await page.locator(containerSelector).count();
  if (!exists) return [];

  return await page.locator(`${containerSelector} dl > div`).evaluateAll((nodes) =>
    nodes
      .map((n) => {
        const dt = n.querySelector('dt');
        const dd = n.querySelector('dd');
        const label = (dt?.textContent ?? '').trim();
        const value = (dd?.textContent ?? '').trim();
        return { label, value };
      })
      .filter((x) => x.label || x.value)
  );
}

async function extractPitchDeckLinks(page: Page, baseURL: string): Promise<Link[]> {
  const section = page.locator('#section-pitch-deck');
  if ((await section.count()) === 0) return [];

  const links = await section.locator('a[href]').evaluateAll((as) =>
    as
      .map((a) => ({ label: (a.textContent ?? '').trim(), url: a.getAttribute('href') ?? '' }))
      .filter((x) => x.url)
  );

  // Prefer explicit "Download" anchors, but keep all links in case UI changes
  const normalized = links.map((l) => ({ ...l, url: l.url.startsWith('http') ? l.url : l.url }));
  const dedup = new Map<string, Link>();
  for (const l of normalized) {
    const abs = ensurePosixUrl(baseURL, l.url);
    dedup.set(abs, { label: l.label || 'link', url: abs });
  }

  // Filter out obviously irrelevant anchors
  return [...dedup.values()].filter((l) => !l.url.endsWith('#'));
}

async function extractImages(page: Page, baseURL: string): Promise<Link[]> {
  const section = page.locator('#section-product-images');
  if ((await section.count()) === 0) return [];

  const imgs = await section.locator('img[src]').evaluateAll((nodes) =>
    nodes
      .map((img) => ({
        label: (img.getAttribute('alt') ?? '').trim() || 'image',
        url: img.getAttribute('src') ?? ''
      }))
      .filter((x) => x.url)
  );

  const dedup = new Map<string, Link>();
  for (const i of imgs) {
    const abs = ensurePosixUrl(baseURL, i.url);
    dedup.set(abs, { label: i.label, url: abs });
  }
  return [...dedup.values()];
}

async function extractVideos(page: Page): Promise<Link[]> {
  const section = page.locator('#section-product-videos');
  if ((await section.count()) === 0) return [];

  const links = await section.locator('a[href]').evaluateAll((as) =>
    as
      .map((a) => ({ label: (a.textContent ?? '').trim() || 'video', url: a.getAttribute('href') ?? '' }))
      .filter((x) => x.url)
  );

  const dedup = new Map<string, Link>();
  for (const l of links) dedup.set(l.url, l);
  return [...dedup.values()];
}

async function extractTeam(page: Page, baseURL: string): Promise<TeamMember[]> {
  const section = page.locator('#section-team');
  if ((await section.count()) === 0) return [];

  return await section.locator('h3').evaluateAll((hs) => {
    const members: TeamMember[] = [];
    for (const h of hs) {
      const card = h.closest('div');
      const name = (h.textContent ?? '').trim();
      const title = (card?.querySelector('p')?.textContent ?? '').trim();
      const ps = card ? Array.from(card.querySelectorAll('p')) : [];
      const bio = (ps[1]?.textContent ?? '').trim();
      const img = card?.parentElement?.querySelector('img[src]') as HTMLImageElement | null;
      const imageUrl = img?.getAttribute('src') ?? undefined;
      members.push({ name, title, bio, imageUrl });
    }
    return members;
  }).then((ms) =>
    ms.map((m) => ({
      ...m,
      imageUrl: m.imageUrl ? (m.imageUrl.startsWith('http') ? m.imageUrl : `${baseURL}${m.imageUrl.startsWith('/') ? '' : '/'}${m.imageUrl}`) : undefined
    }))
  );
}

async function extractSummaryCard(page: Page) {
  const name = textOrEmpty(await page.locator('nav[aria-label="Progress"] .text-2xl').first().textContent().catch(() => ''));

  // Some fields exist on the card table blocks
  const getRow = async (label: string) => {
    const row = page.locator('div').filter({ hasText: label }).first();
    return textOrEmpty(await row.textContent().catch(() => ''));
  };

  return { name };
}

async function getCompanyIdFromUrl(url: string) {
  const m = url.match(/\/open-rounds\/company\/(\d+)/);
  return m?.[1] ?? '';
}

async function collectCompanyUrls(page: Page, baseURL: string): Promise<string[]> {
  await page.goto(`${baseURL}/open-rounds`, { waitUntil: 'domcontentloaded' });

  // Ensure we're actually on the list page (if auth is required, you'll likely see a login form).
  const hasCompanyLink = page.locator('a[href^="/open-rounds/company/"]').first();
  const hasPasswordInput = page.locator('input[type="password"]').first();

  await Promise.race([
    hasCompanyLink.waitFor({ state: 'attached', timeout: 15_000 }).catch(() => undefined),
    hasPasswordInput.waitFor({ state: 'attached', timeout: 15_000 }).catch(() => undefined)
  ]);

  if (await hasPasswordInput.count()) {
    throw new Error('Not authenticated. Run "npm run auth" to save a session, then re-run the scrape.');
  }

  // Scroll to bottom until URLs stop increasing (handles infinite-scroll lists)
  const seen = new Set<string>();
  let stableIterations = 0;

  while (stableIterations < 6) {
    const before = seen.size;

    try {
      const hrefs = await page.locator('a[href^="/open-rounds/company/"]').evaluateAll((as) =>
        as.map((a) => a.getAttribute('href') ?? '').filter(Boolean)
      );
      for (const h of hrefs) seen.add(ensurePosixUrl(baseURL, h));

      if (seen.size === before) stableIterations += 1;
      else stableIterations = 0;

      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(800);
    } catch {
      // If a navigation happened mid-loop (redirects, SPA transitions), stabilize and continue.
      await page.waitForLoadState('domcontentloaded').catch(() => undefined);
      stableIterations += 1;
    }
  }

  return [...seen.values()].sort();
}

async function scrapeCompany(page: Page, baseURL: string, companyUrl: string): Promise<CompanyRow> {
  await page.goto(companyUrl, { waitUntil: 'domcontentloaded' });

  const companyId = await getCompanyIdFromUrl(companyUrl);

  // Company name + website from General Information section
  const companyName = textOrEmpty(await page.locator('#section-general-information dd').first().textContent().catch(() => '')) ||
    textOrEmpty(await page.locator('nav[aria-label="Progress"] .text-2xl').first().textContent().catch(() => ''));

  const websiteUrl = await page.locator('#section-general-information a[href^="http"]').first().getAttribute('href').catch(() => null) ?? undefined;

  // Open Deal: use the section container and dl rows
  const openDealKVs = await extractDl(page, '#section-open-deal');
  const generalInfoKVs = await extractDl(page, '#section-general-information');
  const allDealsKVs = await extractDl(page, '#section-deals');
  const productRegKVs = await extractDl(page, '#section-product-information');

  // Summary bits that are easy to read from the card
  const summaryHeadline = textOrEmpty(await page.locator('#section-card .font-bold').first().textContent().catch(() => ''));
  const summaryTagline = textOrEmpty(await page.locator('#section-card .font-bold').first().locator('xpath=following-sibling::div').first().textContent().catch(() => ''));

  // On the left of the card there is a table-like block with alternating rows
  const summaryBlockText = textOrEmpty(await page.locator('#section-card .w-1/3 .border').first().textContent().catch(() => ''));

  const pitchDecks = await extractPitchDeckLinks(page, baseURL);
  const productImages = await extractImages(page, baseURL);
  const productVideos = await extractVideos(page);
  const teamMembers = await extractTeam(page, baseURL);

  // Attempt to pick out common summary rows if present
  const pick = (label: string) => {
    const re = new RegExp(`${label}\\s*([^\\n]+)`, 'i');
    const m = summaryBlockText.match(re);
    return m ? textOrEmpty(m[1]) : undefined;
  };

  return {
    companyId,
    companyName,
    companyUrl,
    websiteUrl,

    summaryHeadline: summaryHeadline || undefined,
    summaryTagline: summaryTagline || undefined,
    summaryLocation: pick('Year Founded') ? undefined : undefined, // location is unlabeled in snapshot; keep in KVs below when we improve selectors

    openDeal: openDealKVs.length ? JSON.stringify(openDealKVs) : undefined,
    generalInformation: generalInfoKVs.length ? JSON.stringify(generalInfoKVs) : undefined,
    allDeals: allDealsKVs.length ? JSON.stringify(allDealsKVs) : undefined,
    productRegulatoryInformation: productRegKVs.length ? JSON.stringify(productRegKVs) : undefined,

    pitchDecks: pitchDecks.length ? JSON.stringify(pitchDecks) : undefined,
    productImages: productImages.length ? JSON.stringify(productImages) : undefined,
    productVideos: productVideos.length ? JSON.stringify(productVideos) : undefined,
    teamMembers: teamMembers.length ? JSON.stringify(teamMembers) : undefined
  };
}

async function main() {
  const baseURL = process.env.OPENROUNDS_BASE_URL ?? 'https://pro.innovator.org';
  const outPath = process.env.OPENROUNDS_CSV_OUT ?? path.join(process.cwd(), 'open-rounds.csv');
  const maxCompanies = process.env.MAX_COMPANIES ? Number(process.env.MAX_COMPANIES) : undefined;

  const browser = await chromium.launch({ headless: process.env.HEADLESS === '1' });

  // If storageState doesn't exist yet, run unauthenticated (useful for first-time setup / debugging).
  let context;
  try {
    await fs.access(storageStatePath());
    context = await browser.newContext({ storageState: storageStatePath() });
  } catch {
    console.warn(`No storage state found at ${storageStatePath()}. Run \"npm run auth\" first if the site requires login.`);
    context = await browser.newContext();
  }
  const page = await context.newPage();

  const companyUrls = await collectCompanyUrls(page, baseURL);
  const urls = maxCompanies ? companyUrls.slice(0, maxCompanies) : companyUrls;

  console.log(`Discovered ${companyUrls.length} companies; scraping ${urls.length}.`);

  const rows: CompanyRow[] = [];
  for (let i = 0; i < urls.length; i++) {
    const url = urls[i]!;
    console.log(`[${i + 1}/${urls.length}] ${url}`);
    try {
      rows.push(await scrapeCompany(page, baseURL, url));
    } catch (e) {
      console.warn(`Failed scraping ${url}:`, e);
      rows.push({ companyId: await getCompanyIdFromUrl(url), companyName: '', companyUrl: url });
    }
  }

  const header: (keyof CompanyRow)[] = [
    'companyId',
    'companyName',
    'companyUrl',
    'websiteUrl',
    'summaryHeadline',
    'summaryTagline',
    'summaryLocation',
    'summaryYearFounded',
    'summaryCurrentRunway',
    'summaryTeam',
    'summaryUrgency',
    'summaryDevelopmentStage',
    'summaryRegulatoryPathway',
    'summaryCategory',
    'openDeal',
    'generalInformation',
    'allDeals',
    'productRegulatoryInformation',
    'pitchDecks',
    'productImages',
    'productVideos',
    'teamMembers'
  ];

  const csv = stringify(rows, { header: true, columns: header });
  await fs.writeFile(outPath, csv);
  console.log(`Wrote CSV: ${outPath}`);

  await browser.close();
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});

# scrapers/innovator_open_rounds

Scraper for **pro.innovator.org/open-rounds** — MedTech Innovator's public Open Rounds listings.

TypeScript + Playwright. (The previous Python stub under this folder imported a `recordings.macro` module that was never written; this TS implementation is what actually works and what powers MTI Open Rounds runs.)

## Used for

- MTI 2026 — Open Rounds

## Setup (one-time, from this folder)

```bash
cd scrapers/innovator_open_rounds
npm install
npx playwright install
```

## Run

```bash
# 1) Save an authenticated session (opens a browser; log in, then press Enter in the terminal)
npm run auth                # writes ./.auth/storageState.json

# 2) Scrape every Open Rounds company into a single CSV
npm run scrape              # writes ./open-rounds.csv

# 3) Post-process the CSV into per-company folders + media + PDF summary
npm run process

# Or end-to-end:
npm run run:all             # scrape + process
```

### Env knobs

`scrape`:
- `OPENROUNDS_BASE_URL` — default `https://pro.innovator.org`
- `OPENROUNDS_CSV_OUT` — default `./open-rounds.csv`
- `MAX_COMPANIES=25` — for quick test runs
- `HEADLESS=1` — run headless

`process`:
- `OPENROUNDS_CSV_IN` — default `./open-rounds.csv`
- `RUN_ID` — default ISO timestamp

## Output layout

```
~/Downloads/openRounds/<RUN_ID>/
  open-rounds.csv
  <Company Name (id)>/
    company.csv
    company.pdf
    media/*           # non-deck downloads (product images, etc.)
```

## Quirks

- Pitch decks are **not downloaded**; only their direct download URLs are captured in the CSV. (Decks live on `media.innovator.org`; you can fetch them by hand or wire a separate step.)
- If you see auth failures while downloading media, re-run `npm run auth` — the storage state expired.
- `samples/company ex 5 files.html` is a saved snapshot of one company page kept for selector debugging; not used at runtime.
- `node_modules/`, `.auth/`, and `samples/` are gitignored.

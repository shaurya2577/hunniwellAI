# scrapers/hellopartnering

Scraper for **hellopartnering.com** (the RESI partnering platform run by Life Science Nation).

## Used for

- JPM 2026
- Other RESI events

## Entry points

```bash
# One-time auth recording (open a browser, log in, save storage state)
python -m scrapers.hellopartnering.run --save-storage

# Full auto: scrape all sectors, write index CSV(s)
python -m scrapers.hellopartnering.run --auto --all-sectors

# Investor mode: scrape investor firms and their delegates
python -m scrapers.hellopartnering.run --investor --auto

# Then download files from the index CSV
python -m scrapers.common.download <path-to-index.csv> --output-dir ~/Downloads/RESI
```

See `python -m scrapers.hellopartnering.run --help` for all flags.

## Output

- Index CSV under `~/Downloads/RESI/` (or `--output-dir`)
- Files downloaded into sector-named subfolders
- Playwright session in `scrapers/hellopartnering/recordings/auth.json` and `*_browser_profile/`

## Quirks

- The site requires login; auth state must be recorded once via `--save-storage`.
- Categorical "sector" folders are part of RESI's UI — preserved in the index CSV as the `Sector` column.

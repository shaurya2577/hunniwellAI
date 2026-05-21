# scrapers/innovator_open_rounds

Scraper for **pro.innovator.org/open-rounds** — MedTech Innovator's public Open Rounds listings.

## Used for

- MTI 2026 - Open Rounds

## Entry points

```bash
# Full auto: scrape every Open Rounds company, write index CSV
python -m scrapers.innovator_open_rounds.run --auto

# Test mode: first company only
python -m scrapers.innovator_open_rounds.run --auto --test-one

# Download files from the index CSV
python -m scrapers.common.download ~/Downloads/Innovator/index_*.csv \
    --output-dir ~/Downloads/Innovator \
    --base-url https://pro.innovator.org
```

See `python -m scrapers.innovator_open_rounds.run --help` for all flags.

## Output

- Per-company index CSV (`OPEN_ROUNDS_INDEX_HEADERS` schema in `scrapers.common.index_csv`)
- Direct PDF/video downloads available — no Google Drive indirection
- Playwright session in `scrapers/innovator_open_rounds/recordings/auth.json`

## Quirks

- The Open Rounds page exposes direct deck URLs (unlike Pro Innovator applications, which often hide decks behind Google Drive viewers). The downloader works straightforwardly.

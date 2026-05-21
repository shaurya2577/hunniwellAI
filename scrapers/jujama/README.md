# scrapers/jujama

Scraper for **connect-v3.jujama.com** — the Jujama event-partnering platform.

## Used for

- LSI 2026 - USA
- LSI 2026 - Asia
- Any other event hosted on Jujama

## Setup

Uses the root venv. From the repo root:

```bash
source .venv/bin/activate
playwright install chromium
```

## Entry points

```bash
# Export company profiles to CSV
python -m scrapers.jujama.run_companies                     # full run
python -m scrapers.jujama.run_companies --test-one          # first company only
python -m scrapers.jujama.run_companies --headless          # no visible browser

# Export attendee profiles to CSV
python -m scrapers.jujama.run_attendees                     # full run
python -m scrapers.jujama.run_attendees --test-one
```

See `--help` on each for all flags.

## Output

- `~/Downloads/Jujama/jujama_companies/jujama_companies.csv`
- `~/Downloads/Jujama/jujama_attendees/jujama_attendees.csv`

## Flow

1. The script launches a persistent Chromium profile (`jujama_browser_profile/`).
2. You log in manually the first time, then navigate to the Jujama list page (Companies or Attendees) for the event.
3. The script paginates through the live list, opening each detail page in a fresh tab and collecting fields.
4. CSV is written incrementally.

## Quirks

- No headless first-run: you must log in interactively. After that, `--headless` works because the session is cached in the persistent profile.
- Pagination logic in `common.py` is keyed to Jujama's specific Bootstrap pagination markup.
- `organize.py` (was `organize_jujama_companies.py`) post-processes the CSV into per-company folders matching the CompanyFiles convention.

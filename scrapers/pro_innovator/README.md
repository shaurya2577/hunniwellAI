# scrapers/pro_innovator

Scraper for **pro.innovator.org** Applications / cohorts (e.g. APAC 2026) and the **Radar Forum** views. Distinct from `scrapers/innovator_open_rounds/` because the data lives behind login and pitch decks are usually Google-Drive viewer pages, not direct downloads.

## Used for

- MTI 2026 Virtual Pitch # 1, Virtual Pitch # 2
- MTI 2026 APAC Virtual Pitch # 2
- MTI 2026 Asia Medtech Spotlight
- MTI 2026 LA Radar Forum
- MTI 2026 Prelim Reviews

## Entry points

```bash
# Live AG Grid scrape (Playwright) — full CSV + deck capture
python -m scrapers.pro_innovator.run --live

# CSV only (no deck rebuild)
python -m scrapers.pro_innovator.run --live --csv-only

# One company only
python -m scrapers.pro_innovator.run --live --test-one

# Offline fallback: extract from a saved Applications HTML
python -m scrapers.pro_innovator.run --extract /path/to/saved.html ./pro_innovator_companies.csv

# Radar Forum extract (saved HTML, supports multiple files)
python -m scrapers.pro_innovator.run --radar ~/Scratch/radar/*.html --radar-output ./radar_companies.csv
```

See `python -m scrapers.pro_innovator.run --help`.

## How the deck capture works

Pro Innovator pitch decks live on Google Drive. The Google Drive viewer does NOT expose a direct download. Strategy in `deck_capture.py` + `pdf_build.py`:

1. Visit the deck viewer page in Playwright.
2. Screenshot each viewable page.
3. Stitch screenshots back into a PDF via `pdf_build.build_pdf_from_images`.

See `SLIDEDECK_DOWNLOAD.md` for the full rationale and known limitations.

## Output

- Per-cohort CSV with full grid fields (`grid_extract.py`)
- Rebuilt PDFs per company under the configured output dir
- Companion `company_docs.py` / `company_pdfs.py` post-processors generate Word docs and bundled PDFs from the CSV

## Quirks

- Authenticated; uses a persistent browser profile (`*_browser_profile/`) — log in once manually.
- Grid scrape is fragile to UI changes; the HTML fallback (`innovator_portal_reader.py`) is the recovery path when selectors break.

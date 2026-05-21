# Hunniwell – MTI & Partner Platform Tools

Internship tooling for MedTech Innovator (MTI) and related platforms: index-based pitch deck downloads, CSV extraction, and document generation.

## Nomenclature

| Term | Platform | What it is |
|------|----------|-------------|
| **Open Rounds** | pro.innovator.org | Publicly listed companies seeking funding. Each has a deal page at `/open-rounds/company/ID` with direct PDF/video links. |
| **Pro Innovator** | pro.innovator.org | Applications/cohort companies (e.g. APAC 2026). Data in Applications → APAC → Cohort grid. Slide decks often hosted on Google Drive—no direct download links. |

## Project layout

```
.
├── resi/                          # Main MTI & index-downloader tooling
│   ├── index_helper.py            # Shared CSV schema and helpers
│   ├── download_from_index.py     # Generic: download PDFs/videos from index CSV
│   ├── generate_company_docs.py   # Word docs from Open Rounds CSV
│   ├── cleanup_duplicates.py      # Remove duplicate downloaded files
│   ├── run_resi.py                # RESI (HelloPartnering) automation
│   ├── run_innovator.py           # Open Rounds automation
│   ├── run_pro_innovator.py       # Pro Innovator (Applications) extraction
│   └── platforms/
│       ├── resi/                  # RESI-specific Playwright automation
│       └── innovator/
│           ├── config.py          # Open Rounds config
│           ├── run_downloader.py # Open Rounds: scrape company pages, index
│           ├── recordings/       # Macro, auth
│           └── pro_innovator/    # Pro Innovator: live AG Grid scrape, HTML fallback, deck capture
├── pitchbook_converter/           # PitchBook HTML → Word (separate data source)
└── requirements.txt
```

## Quick start

```bash
pip install -r requirements.txt
playwright install chromium
```

- **Open Rounds** (company list + pitch decks):
  ```bash
  cd resi
  python run_innovator.py --auto
  python download_from_index.py --output-dir ~/Downloads/Innovator --base-url https://pro.innovator.org
  ```

- **Pro Innovator** (live Applications page -> CSV -> rebuilt PDFs):
  ```bash
  cd resi
  python run_pro_innovator.py --live --csv-only
  python run_pro_innovator.py --live --test-one
  ```

- **Pro Innovator fallback** (extract from saved Applications HTML):
  ```bash
  cd resi
  python run_pro_innovator.py --extract /path/to/saved.html ~/Downloads/Innovator/pro_innovator_companies.csv
  ```

- **RESI** (HelloPartnering): `cd resi && python run_resi.py --auto`

See [resi/README.md](resi/README.md) for full details.

## Open Rounds vs Pro Innovator

| Feature | Open Rounds | Pro Innovator |
|---------|-------------|---------------|
| Source | `/open-rounds` | Applications → APAC → Cohort (live AG Grid, plus saved HTML fallback) |
| Data extraction | Playwright macro on company pages | Playwright grid scrape or HTML parser |
| Pitch deck URLs | Direct (media.innovator.org) | Often Google Drive (no direct download) |
| Download flow | `download_from_index.py` works | Rebuild from captured viewer pages |

## Requirements

- Python 3.10+
- playwright, python-docx, pillow, flask

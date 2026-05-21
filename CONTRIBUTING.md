# Contributing

## Setup

```bash
git clone https://github.com/shaurya2577/hunniwellAI.git Hunniwell
cd Hunniwell
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
playwright install chromium
cp ai/airtable_ingest/.env.example ai/airtable_ingest/.env   # fill in keys
```

Single root venv. Single `pyproject.toml`. No per-subproject `venv`.

## Conventions

- **One subdir under `scrapers/` per website.** Never per event. An event (JPM 2026, MTI Spotlight, etc.) is a use of a website. Multiple events route through the same scraper.
- **Truly generic helpers live in `scrapers/common/`.** Anything that knows about specific selectors / login flows stays in the platform subdir.
- **`ai/airtable_ingest/events.py` is the source of truth** for the canonical event taxonomy. To add an event, add an entry there AND create the matching folder under `$HUNNIWELL_COMPANYFILES_ROOT`.
- **Never commit secrets.** `.env` is gitignored. So are `*_browser_profile/`, `recordings/auth.json`, `CompanyFiles/`, and all data files (`*.csv`, `*.xlsx`, `*.pdf`, `*.docx`, `*.pptx`).
- **Match imports to module paths.** Use `from scrapers.common.index_csv import ...`, not relative path-hackery. The package is installed editable via `pip install -e .`.

## Adding a new scraper (new website)

1. Pick a name (the website's short name, lowercase). Examples: `hellopartnering`, `jujama`, `pro_innovator`.
2. Copy an existing scraper as a template:
   ```bash
   cp -r scrapers/jujama scrapers/yoursite
   ```
3. Edit `scrapers/yoursite/config.py` — base URL, output paths, timeouts.
4. Rewrite `scrapers/yoursite/run*.py` to drive the new site.
5. If the site has an authenticated session, plan for a one-time auth recording — see how `scrapers/hellopartnering/downloader.py` handles `--save-storage`.
6. Add a `README.md` documenting the entry-point command and login flow.
7. Verify by running `python -m scrapers.yoursite.run --help`.

## Adding a new event

1. Confirm the canonical OneDrive name (e.g. `MTI 2027 - Virtual Pitch # 1 (270315)`).
2. Add an entry to `ai/airtable_ingest/events.py`:
   ```python
   "MTI 2027 - Virtual Pitch # 1 (270315)": {"layout": "flat"},
   ```
   For nested events, also pass `"categories": [...]`.
3. Create the matching folder under `$HUNNIWELL_COMPANYFILES_ROOT/`.
4. Drop scraped company subfolders inside.
5. Run `python -m ai.airtable_ingest.ingest --dry-run --event "..."` to verify before a real ingest.

## Commit hygiene

- One change per commit; describe the *why* not the *what*.
- Don't run secrets through commit messages.
- Before pushing, re-check: `git ls-files | grep -Ei "\.(env|pdf|pptx|docx|xlsx|csv)$"` should be empty.

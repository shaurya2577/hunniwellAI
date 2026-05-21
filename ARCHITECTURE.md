# Architecture

## Data flow

```
   ┌───────────────────────┐
   │   Conference websites │
   │                       │
   │ hellopartnering.com   │──────┐
   │ pro.innovator.org     │──────┤
   │ connect-v3.jujama.com │──────┤
   └───────────────────────┘      │
                                  ▼
   ┌────────────────────────────────────────────┐
   │ scrapers/<platform>/                       │
   │   - Playwright sessions                    │
   │   - Index CSV writers (scrapers/common/)   │
   │   - Generic file downloader                │
   └─────────────────────┬──────────────────────┘
                         │
                         ▼ writes per-company folders
   ┌────────────────────────────────────────────┐
   │ $HUNNIWELL_COMPANYFILES_ROOT/<event>/...   │
   │   - One subdir per OneDrive canonical event│
   │   - Companies at depth 1 (flat)            │
   │   - or depth 2 (nested: JPM, Prelim)       │
   └─────────────────────┬──────────────────────┘
                         │
                         ▼  read by AI ingest
   ┌────────────────────────────────────────────┐
   │ ai/airtable_ingest/ingest.py               │
   │   - Walks events from events.py whitelist  │
   │   - Extracts text from PDF/DOCX/PPTX/TXT/MD│
   │   - One Claude call per company            │
   │   - Strict JSON schema → Airtable POST     │
   └─────────────────────┬──────────────────────┘
                         │
                         ▼
                  Airtable: HLV Companies DB
```

## Module boundaries

- **`scrapers/<platform>/`** owns the relationship with one website. Login flow, page selectors, deck-download tactics — all live here. New platform = new subdir (copy an existing one as a template).
- **`scrapers/common/`** owns reusable mechanics: CSV-index schemas, generic file downloader, sanitizers, post-processors. Pure utility, no playwright-session state.
- **`ai/airtable_ingest/`** owns the *interpretation* step: turning a folder of files into a structured record. Knows nothing about how the files got there. Talks to Claude + Airtable.
- **`ai/airtable_ingest/events.py`** owns the canonical event taxonomy and per-event folder layout (flat vs nested). This is the single source of truth for the OneDrive-aligned naming convention.
- **`tools/`** holds non-scraper, non-AI utilities (currently just `pitchbook_converter`).
- **`scripts/`** holds repo-level operational scripts (migration runners, audits).

## Why one venv

Previously every subdir had its own `.venv` and `requirements.txt`. New contributors had to spin up four venvs. Now there's one root `.venv` + `pyproject.toml`. All deps coexist (playwright, anthropic, flask, etc.). Install with `pip install -e .`.

## Why "scrapers/" by website, not by event

A website is a stable API surface (selectors, login flow, pagination logic) that you maintain. An event (JPM 2026, MTI Spotlight) is a use of that API. Multiple events can flow through the same website's scraper — e.g. JPM 2026 + RESI Boston both use `scrapers/hellopartnering/`. Organizing by website keeps related selector code together and makes it obvious where to add support for a new website.

## State / output locations

| Thing | Location | Tracked? |
|---|---|---|
| Scraper index CSVs | wherever `--output-dir` points | no (gitignored, often `~/Downloads/...`) |
| Scraper downloaded files | same | no |
| CompanyFiles tree | `$HUNNIWELL_COMPANYFILES_ROOT` (default `~/Documents/Hunniwell/`) | no — lives outside this repo |
| Airtable ingest state | `ai/airtable_ingest/.processed.json` | no (gitignored) |
| Airtable ingest run log | `ai/airtable_ingest/run_log.csv` | no |
| Playwright auth cookies | `scrapers/<platform>/recordings/auth.json` and `*_browser_profile/` | no |

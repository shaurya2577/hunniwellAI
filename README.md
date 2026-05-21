# Hunniwell — Medtech Event Tooling

Internal tools for Hunniwell Lake Ventures: scrapers that pull company info from medtech conference platforms (RESI, MTI Innovator, Jujama), an AI extractor that converts those files into structured Airtable records, and a couple of offline utilities.

## What this exists for

Hunniwell sees hundreds of medtech companies across conferences (JPM, LSI, MedTech Innovator events) every quarter. Each event drops a different export format on a different platform. Doing this by hand:

- Costs hours per event of analyst time
- Misses companies because the conference UIs paginate badly
- Produces inconsistent Airtable rows (different fields filled per analyst)

This repo automates the boring half:

1. **Scrapers** pull a full per-company export from each conference platform — login flow, pagination, deck download — into a per-company folder structure.
2. **AI ingest** reads each company folder, calls Claude with strict JSON schema, and writes one Airtable row per company. Inference is allowed for IATA / class / regulatory pathway (calibrated against the OneDrive layout used by the rest of the team).

Net result: the analyst's job becomes "review the rows" instead of "transcribe each deck."


## Status

| Piece | State |
|---|---|
| `scrapers/hellopartnering/` — RESI / HelloPartnering | Works. Last used for JPM 2026. |
| `scrapers/innovator_open_rounds/` — MTI Innovator Open Rounds | Works. Powers MTI 2026 Open Rounds. |
| `scrapers/pro_innovator/` — MTI applications + Radar Forum | Works live; reliable in `--extract`/`--radar` offline mode. Used for MTI 2026 Virtual Pitches, APAC, Asia Spotlight, LA Radar Forum. |
| `scrapers/jujama/` — Jujama platform | Works. Used for LSI 2026 events. |
| `tools/pitchbook_converter/` — PitchBook HTML → Word | Works; simple Flask UI. |
| `ai/airtable_ingest/` — Claude → Airtable | Working as of last run; 2,128 records ingested across 11 events. Defaults to Haiku 4.5 for cost. |

## Layout

```
.
├── scrapers/                 # One subdir per WEBSITE (not per event)
│   ├── common/                  # Shared utilities (CSV index, downloader, sanitizers, postprocess)
│   ├── hellopartnering/         # hellopartnering.com   (RESI; used for JPM 2026)
│   ├── innovator_open_rounds/   # pro.innovator.org/open-rounds   (used for MTI Open Rounds)
│   ├── pro_innovator/           # pro.innovator.org applications + Radar (used for MTI Virtual / APAC / Spotlight / Prelim Reviews)
│   └── jujama/                  # connect-v3.jujama.com   (used for LSI 2026 events)
│
├── ai/                       # LLM / extraction code
│   └── airtable_ingest/         # Reads CompanyFiles/<event>/<company>/, calls Claude, writes Airtable
│
├── tools/                    # Offline / one-off utilities
│   └── pitchbook_converter/     # PitchBook HTML → Word doc (Flask UI)
│
├── scripts/                  # Repo-level operational scripts
│   └── migrate_companyfiles.py  # Rename messy local folders to canonical OneDrive names
│
├── pyproject.toml            # Single project; all deps consolidated
├── README.md                 # this file
├── ARCHITECTURE.md           # Data flow diagram and design notes
├── CONTRIBUTING.md           # Setup, conventions, how to add a new scraper or event
└── EVENT_LAYOUT.md           # Canonical OneDrive event names + flat/nested rules
```

**Convention:** one subdir under `scrapers/` per website. Real-world events are mapped to a platform via the AI ingest's [events.py](ai/airtable_ingest/events.py).

## Setup (one-time)

```bash
git clone https://github.com/shaurya2577/hunniwellAI.git Hunniwell
cd Hunniwell
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
playwright install chromium
cp ai/airtable_ingest/.env.example ai/airtable_ingest/.env   # fill in keys
```

`CompanyFiles/` (the source data for the AI ingest) lives **outside** this repo, defaulting to `~/Documents/Hunniwell`. Override via `HUNNIWELL_COMPANYFILES_ROOT` env var. See [EVENT_LAYOUT.md](EVENT_LAYOUT.md) for the canonical folder taxonomy.

## Quick start, by tool

**Scrape companies from a platform** — one entry point per platform:

```bash
python -m scrapers.hellopartnering.run --auto                # RESI
python -m scrapers.innovator_open_rounds.run --auto          # MTI Open Rounds
python -m scrapers.pro_innovator.run --live                  # MTI Pro Innovator (applications/Radar)
python -m scrapers.jujama.run_companies                      # Jujama companies
python -m scrapers.jujama.run_attendees                      # Jujama attendees
```

Each entry point has `--help`. See each platform's own README under `scrapers/<platform>/`.

**Ingest scraped folders into Airtable:**

```bash
python -m ai.airtable_ingest.ingest --dry-run                # preview
python -m ai.airtable_ingest.ingest                          # do it
python -m ai.airtable_ingest.ingest --event "JPM 2026 (260115)"
```

**Convert a PitchBook HTML export to Word:**

```bash
python tools/pitchbook_converter/pitchbook_converter_ui.py   # opens a local Flask UI
```

**Rename messy local CompanyFiles folders to canonical OneDrive names** (dry-run by default):

```bash
python scripts/migrate_companyfiles.py            # preview
python scripts/migrate_companyfiles.py --apply    # do it
```

## Adding a new scraper or event

See [CONTRIBUTING.md](CONTRIBUTING.md).

## How the pieces fit together

See [ARCHITECTURE.md](ARCHITECTURE.md).

## Security / data handling

See [SECURITY.md](SECURITY.md). Short version: confidential company decks NEVER touch the repo. Keys NEVER touch the repo. CompanyFiles/ lives at `~/Documents/Hunniwell/` outside the repo, and `.gitignore` blocks every common data-file extension by default.

## Index of docs

| Doc | When to read |
|---|---|
| [README.md](README.md) | You're here — start. |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Understanding how scrapers + AI + Airtable fit together. |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Setting up locally; adding a new scraper or event. |
| [EVENT_LAYOUT.md](EVENT_LAYOUT.md) | Adding a new event to the AI ingest taxonomy. |
| [SECURITY.md](SECURITY.md) | Before pushing anything; understanding what's confidential. |
| `scrapers/<platform>/README.md` | Working on a specific scraper. |
| `ai/airtable_ingest/README.md` | Running or changing the AI ingest. |

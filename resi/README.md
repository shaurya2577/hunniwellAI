# Index-based pitch deck downloader

Bulk download pitch decks and media from partnering/conference platforms.

**Nomenclature:** **Open Rounds** = public deal listings at `/open-rounds` (direct PDF links). **Pro Innovator** = Applications/cohort (e.g. APAC 2026) – often Google Drive–hosted, no direct download.

- **Generic index downloader** – works with any index CSV that has `Company Name`, `Sector`, `Link Label`, and `PDF URL`.
- **RESI (HelloPartnering)** – Playwright automation that builds the index, then uses the generic downloader.
- **Open Rounds** – Playwright visits each company page, extracts data and pitch deck URLs (direct links), writes index CSV.
- **Pro Innovator** – Live Playwright runner from the Applications page: scrape AG Grid -> CSV -> open `View` -> capture viewer pages -> rebuild PDFs. Saved-HTML extraction remains as a fallback.

---

## Layout

```
.
├── download_from_index.py     # Generic: download from any index CSV (sector/company folders)
├── generate_company_docs.py   # Generate Word docs from open rounds CSV into company folders
├── cleanup_duplicates.py     # Remove duplicate files (e.g. Company_Deck_2.pdf when base exists)
├── index_helper.py            # Generic: index CSV schema and helpers
├── run_resi.py                # Entrypoint for RESI
├── run_innovator.py           # Entrypoint for Open Rounds
├── run_pro_innovator.py       # Entrypoint for Pro Innovator (live / extract)
├── platforms/
│   ├── resi/                 # RESI-specific automation
│   │   ├── config.py         # RESI URLs, output dir, timeouts, sectors
│   │   ├── run_downloader.py # Playwright: login, search, macro loop, index writing
│   │   └── recordings/       # Recorded macro (run_macro) and auth (gitignored)
│   └── innovator/
│       ├── config.py         # Open Rounds config
│       ├── run_downloader.py # Open Rounds: list → company pages, macro, index
│       ├── recordings/
│       │   └── macro.py      # run_macro: extract name + pitch deck links from company page
│       └── pro_innovator/    # Pro Innovator (Applications/cohort)
│           ├── innovator_portal_reader.py  # Saved HTML -> CSV fallback
│           ├── run_downloader.py           # Live Applications page runner
│           ├── grid_extract.py             # AG Grid row extraction
│           ├── deck_capture.py             # Viewer capture helpers
│           ├── pdf_build.py                # Rebuild captured page images into PDFs
│           └── SLIDEDECK_DOWNLOAD.md       # Flow notes and limitations
├── tests/
│   └── test_download.py      # RESI output dir + Playwright download check
└── requirements.txt
```

**Run from `resi/`** (or from repo root: `python resi/run_innovator.py`).

---

## Index downloader (generic)

**Use for any source** that can produce an index CSV with at least:

- `Company Name`
- `Sector`
- `Link Label`
- `PDF URL`

Extra columns (e.g. Subsectors, Website, Year founded) are preserved in sector index CSVs.

**Output layout:**

- `OUTPUT_DIR/[Sector]/!!![Sector]_index.csv` – one CSV per sector (same columns as input).
- `OUTPUT_DIR/[Sector]/[Company]/` – one folder per company; files named `CompanyName_LinkLabel.pdf` (or `.mp4` for movie links).

**Usage:**

```bash
# Default output: ~/Downloads/IndexDownloads; relative URLs need --base-url
python download_from_index.py path/to/index.csv

# Custom output and base URL (e.g. for RESI index)
python download_from_index.py index_2025-02-03_14-30-00.csv --output-dir ~/Downloads/RESI --base-url https://www.hellopartnering.com

# Env (optional): INDEX_OUTPUT_DIR, INDEX_BASE_URL
export INDEX_OUTPUT_DIR=~/Downloads/RESI
export INDEX_BASE_URL=https://www.hellopartnering.com
python download_from_index.py   # uses newest index_*.csv in INDEX_OUTPUT_DIR
```

Options: `--no-skip-existing` to re-download; `--fix-names` to sanitize existing filenames in the output dir.

---

## RESI (HelloPartnering) run_downloader

**RESI-only**: Playwright automation that logs in, applies search filters, opens each company modal, runs a recorded macro to collect links and metadata, and writes an index CSV. Downloads themselves are then done with the generic **index downloader** (same index format).

**Setup:**

1. Install: `pip install -r requirements.txt` and `playwright install chromium`.
2. One-time auth:  
   `python run_resi.py --save-storage`  
   Log in in the browser, then press Enter to save auth to `platforms/resi/recordings/auth.json`.
3. Record macro (if not already):  
   `playwright codegen --load-storage=platforms/resi/recordings/auth.json https://www.hellopartnering.com`  
   Do one per-company flow, then put the generated logic into `platforms/resi/recordings/macro.py` inside a `run_macro(page, context, company_name)` that returns `(company_name, [(link_label, url), ...], categorization_dict, general_info_dict)`.

**Run:**

```bash
# From repo root
python run_resi.py
# Browser opens; go to company list, then for each company press Enter to run macro; type 'done' when finished.

# Full automation (login + all sectors)
python run_resi.py --auto --all-sectors

# Test one company
python run_resi.py --test-one

# Investor mode: index delegates (name, position, LinkedIn, email) from investor firms
python run_resi.py --investor
# Manual: log in, go to Search for Investors, press Enter; script clicks each Delegates button and extracts info.

# Investor mode with full automation
python run_resi.py --investor --auto

# Test one investor
python run_resi.py --investor --test-one
```

Output: `~/Downloads/RESI` (or `RESI_OUTPUT_DIR`) with `index_YYYY-MM-DD_HH-MM-SS.csv`. Investor mode writes `investor_index_YYYY-MM-DD_HH-MM-SS.csv` with columns: Firm Name, Delegate Name, Position, Email, LinkedIn, Firm Sectors, Mandate Summary, etc. Then:

```bash
python download_from_index.py --output-dir ~/Downloads/RESI --base-url https://www.hellopartnering.com
```

---

## Innovator Portal (pro.innovator.org) Open Rounds

**Innovator-only**: Playwright automation that goes to the Open Rounds list, visits each company page (`/open-rounds/company/ID`), runs a macro to extract company name, pitch deck links, video URLs, and other metadata, and writes an index CSV. Downloads are then done with the generic **index downloader** (same format).

**Macro** (in `platforms/innovator/recordings/macro.py`): on a company page, reads company name from the sidebar nav, and from `#section-pitch-deck` each list item’s filename (link label) and Download link href (PDF URL). Extracts Video URL from `#section-product-videos` when present. Optionally reads website from General Information.

**Run:**

```bash
# From repo root
python run_innovator.py
# Browser opens at Open Rounds; navigate to a company page, press Enter to run macro; type 'done' when finished.

# Full automation: visit all company pages from the list (with pagination)
python run_innovator.py --auto

# Test: process only the first company
python run_innovator.py --auto --test-one

# One-time: save auth for codegen (if you need to re-record the macro)
python run_innovator.py --save-storage
```

Output: `~/Downloads/Innovator` (or `INNOVATOR_OUTPUT_DIR`) with `open_rounds_YYYY-MM-DD_HH-MM-SS.csv` (columns: Company Name, Company ID, Website, One-liner, Pitch Deck Download URL, Video URL, Product Summary, Team Members, etc.). Then:

```bash
python download_from_index.py --output-dir ~/Downloads/Innovator --base-url https://pro.innovator.org
```

Pitch deck URLs from the portal are typically absolute (e.g. `https://media.innovator.org/...`), so `--base-url` is often unnecessary but does no harm.

**Post-download utilities:**

```bash
# Remove duplicate files (e.g. Company_Deck_2.pdf when Company_Deck.pdf exists and same size)
python cleanup_duplicates.py --dry-run   # preview
python cleanup_duplicates.py ~/Downloads/Innovator

# Generate a Word doc per company from the open rounds CSV (Overview, Deal, Product, Team, etc.)
python generate_company_docs.py --dry-run   # preview
python generate_company_docs.py --output-dir ~/Downloads/Innovator
```

---

## Pro Innovator (Applications/cohort)

**Pro Innovator** = Applications → APAC → Cohort companies. The main flow is now live Playwright automation against the AG Grid page you open manually before capture. Decks are often hosted on Google Drive, so the runner captures rendered viewer pages and rebuilds a PDF locally.

**Live Applications page -> CSV only**:

```bash
# Script opens a persistent browser profile.
# Log in if needed, navigate to the Applications page, then press Enter.
python run_pro_innovator.py --live --csv-only
```

**Live Applications page -> CSV + rebuilt PDFs**:

```bash
# Capture all rows and then rebuild PDFs from the deck viewer pages
python run_pro_innovator.py --live

# Test just the first company
python run_pro_innovator.py --live --test-one
```

**Extract from saved HTML → CSV** (no Playwright; stdlib only):

```bash
# Save the Applications page (e.g. APAC 2026) as HTML, then:
python run_pro_innovator.py --extract /path/to/saved.html ~/Downloads/Innovator/pro_innovator_companies.csv
```

See `platforms/innovator/pro_innovator/SLIDEDECK_DOWNLOAD.md` for the capture strategy and remaining limitations.

---

## Adding another platform

1. **Index only (no browser)**  
   - Produce an index CSV with `Company Name`, `Sector`, `Link Label`, `PDF URL` (and any extra columns).  
   - Run:  
     `python download_from_index.py your_index.csv --output-dir /path/to/output --base-url https://your-site.com`

2. **New platform with its own automation**  
   - Add e.g. `platforms/your_platform/`:  
     - `config.py` – base URL, output dir, auth/timeouts.  
     - `run_downloader.py` – Playwright (or other) flow that builds an index CSV (reuse `index_helper.append_to_index` and the same headers from `index_helper.INDEX_HEADERS`).  
     - Optional `recordings/` for macros/auth.  
   - Add a root entrypoint (e.g. `run_your_platform.py`) that calls your run_downloader’s `main()`.  
   - After the run, use the same `download_from_index.py` with your platform’s output dir and base URL.

The index downloader stays generic; new platforms only need to emit the same CSV shape and then use `download_from_index.py` with the right `--output-dir` and `--base-url`.

---

## Requirements

- Python 3.10+
- `playwright>=1.40.0` (for RESI and Innovator run_downloaders and tests)
- `python-docx>=1.1.0` (for `generate_company_docs.py`)
- `pillow>=11.0.0` (for Pro Innovator PDF rebuild)

```bash
pip install -r requirements.txt
playwright install chromium
```

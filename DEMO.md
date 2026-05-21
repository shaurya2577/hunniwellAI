# Demo Walkthrough

A 30-second, no-login demo that shows the offline scraper extracting real medtech companies from a saved conference portal HTML page into a structured CSV.

## Why this demo

- **No login mid-demo.** Uses saved HTML, so nothing can break because of an expired session.
- **Fast.** Runs in under 5 seconds.
- **Visible result.** Produces a CSV with 144 companies and 27 columns.
- **Talkable.** You can explain the architecture (per-website scraper, offline fallback, shared CSV schema) while the audience reads the output.

## Pre-reqs (do once before the demo)

```bash
# Clone (if you don't already have it)
git clone https://github.com/shaurya2577/hunniwellAI.git Hunniwell
cd Hunniwell

# Set up the venv and install everything
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
playwright install chromium
```

If you already have it cloned, just make sure `source .venv/bin/activate` works.

## The demo

**1.** Open a terminal in the repo root:

```bash
cd ~/Dev/Hunniwell                # wherever you cloned it
source .venv/bin/activate
```

**2.** Pick a saved HTML file. We ship a known-good one in the user's CompanyFiles tree:

```bash
HTML="$HOME/Documents/Hunniwell/MTI 2026 - LA Radar Forum (260407)/Innovator Portal.html"
ls -lh "$HTML"                    # confirm it exists
```

If you're demoing on a different machine, replace `$HTML` with any path to a saved MedTech Innovator Radar Forum HTML file.

**3.** Run the extractor:

```bash
mkdir -p demo_output
python -m scrapers.pro_innovator.run \
    --radar "$HTML" \
    --radar-output demo_output/radar_companies.csv
```

Expected output (under 5 seconds):

```
  Innovator Portal.html: 144 companies, 1 with detail
Wrote 144 companies to demo_output/radar_companies.csv
```

**4.** Show the result:

```bash
wc -l demo_output/radar_companies.csv
head -1 demo_output/radar_companies.csv | tr ',' '\n' | head -10
open demo_output/radar_companies.csv          # opens in Excel/Numbers on macOS
```

That's 144 medtech companies with columns like Company Name, Country, Clinical Areas, Round, Year Founded, Pitch Deck URL, etc.

## What to talk about while it runs

- **Per-website organization.** `scrapers/pro_innovator/` is one of five scraper subdirs — each corresponds to one website (`pro.innovator.org`, `hellopartnering.com`, `connect-v3.jujama.com`, etc.). New website → new subdir.
- **Two modes per scraper.** Live (Playwright drives a real browser) for fresh data, offline (`--radar` / `--extract`) for re-parsing saved HTML. The offline mode is what makes this demo bulletproof.
- **One CSV schema.** All scrapers feed into a shared schema (`scrapers/common/index_csv.py`) so downstream tooling — including the AI ingest — doesn't care which platform the data came from.
- **Next stage of the pipeline.** That CSV gets paired with downloaded decks under `~/Documents/Hunniwell/<event>/<company>/`, and `ai/airtable_ingest/` turns each folder into an Airtable row via Claude.

## Extending the demo (optional)

Process ALL four LA Radar Forum HTML files at once (they're paginated):

```bash
python -m scrapers.pro_innovator.run \
    --radar "$HOME/Documents/Hunniwell/MTI 2026 - LA Radar Forum (260407)"/Innovator\ Portal*.html \
    --radar-output demo_output/radar_companies_full.csv
```

Or do the AI extraction step on one company (requires Anthropic key in `ai/airtable_ingest/.env`):

```bash
python -m ai.airtable_ingest.ingest \
    --dry-run \
    --event "LSI 2026 - USA (260320)" \
    --company "Aliph Medical"
```

Shows the JSON record Claude would write to Airtable, with ~12 fields populated from the source files.

## Where the output goes

- The CSV is written to whatever path you passed `--radar-output`. In this walkthrough that's `demo_output/radar_companies.csv` relative to the repo root.
- The `demo_output/` directory is in `.gitignore` (along with all `*.csv` files) so the data never gets committed.

## If something goes wrong

| Symptom | Fix |
|---|---|
| `command not found: python` | `source .venv/bin/activate` first |
| `ModuleNotFoundError: scrapers` | Run from repo root, not from inside a subdir |
| `Could not find HTML file` | Check the `$HTML` path; spaces and the `#` in folder names need quoting |
| Output is empty | The HTML may be from a different portal layout; try the `--extract` flag instead of `--radar` |

# ai/airtable_ingest

Walks `$HUNNIWELL_COMPANYFILES_ROOT/<event>/<company>/`, extracts text from PDF/DOCX/PPTX/TXT/MD files, asks Claude to produce a strict-schema JSON record, and POSTs it to the Hunniwell Airtable base. Re-runs skip companies already in `.processed.json`.

## Setup

Uses the root venv. From the repo root:

```bash
source .venv/bin/activate
cp ai/airtable_ingest/.env.example ai/airtable_ingest/.env   # fill in keys
```

Required env vars (loaded from `ai/airtable_ingest/.env`):

| Var | What |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key |
| `AIRTABLE_API_KEY` | Airtable personal access token (PAT, `pat...`) |
| `AIRTABLE_BASE_ID` | e.g. `appqYNxEg8JJkY4h5` |
| `AIRTABLE_TABLE_NAME` | table name OR table ID (`tbl...`) |
| `HUNNIWELL_COMPANYFILES_ROOT` | path to CompanyFiles tree (default `~/Documents/Hunniwell`) |

## Run

```bash
python -m ai.airtable_ingest.ingest                          # full run
python -m ai.airtable_ingest.ingest --dry-run                # no Airtable writes
python -m ai.airtable_ingest.ingest --event "JPM 2026 (260115)"
python -m ai.airtable_ingest.ingest --company "Aliph Medical"
python -m ai.airtable_ingest.ingest --root /custom/path
python -m ai.airtable_ingest.ingest --reset-state            # clear .processed.json
```

## Events

`events.py` holds the canonical OneDrive event names and their layout (flat vs nested). Edit there to register a new event. See `EVENT_LAYOUT.md` at repo root for the full table and conventions.

## Outputs

- New Airtable record per company.
- `run_log.csv` (next to `ingest.py`) — append-only audit log.
- `.processed.json` — state file; re-runs skip entries here.
- `errors/<company>.txt` — raw Claude response if JSON parse failed.

# Event Layout

The AI ingest (`ai/airtable_ingest/ingest.py`) walks `$HUNNIWELL_COMPANYFILES_ROOT` and processes each event folder whose name appears in `ai/airtable_ingest/events.py`. This is the canonical taxonomy.

## Canonical OneDrive event names

These mirror the OneDrive layout in the `HLV Companies DB / HLV 2026 Companies/` shared folder.

| Folder name (under `$HUNNIWELL_COMPANYFILES_ROOT`) | Layout | Platform |
|---|---|---|
| `JPM 2026 (260115)` | nested by RESI sector | RESI / hellopartnering |
| `MTI 2026 - Virtual Pitch # 1 (260326)` | flat | MTI Innovator |
| `MTI 2026 - APAC Virtual Pitch # 2 (260402)` | flat | MTI Innovator |
| `MTI 2026 - Virtual Pitch # 2 (260416)` | flat | MTI Innovator |
| `MTI 2026 - Asia Medtech Spotlight (260418)` | flat | MTI Innovator (TODO confirm date) |
| `MTI 2026 - LA Radar Forum (260407)` | flat | MTI Pro Innovator (Radar) |
| `MTI 2026 - Open Rounds` | flat | MTI Innovator Open Rounds |
| `MTI 2026 - Prelim Reviews` | nested by region (`apac/`, `mti/`) | MTI |
| `LSI 2026 - USA (260320)` | flat | Jujama |
| `LSI 2026 - ASia (260703)` | flat | Jujama |

## Layout rules

- **Flat:** `<event>/<company>/<files>` — most events.
- **Nested:** `<event>/<category>/<company>/<files>` — when companies are pre-grouped (by RESI sector for JPM; by region for Prelim Reviews).

For nested events, the Airtable `Event` column is `"<event-folder-name> - <category>"`. Example: `"JPM 2026 (260115) - HealthTech"`.

## Adding a new event

1. Create the folder under `$HUNNIWELL_COMPANYFILES_ROOT/` with the canonical name.
2. Drop company subfolders inside (depth 1 for flat, depth 2 for nested).
3. Add an entry to `ai/airtable_ingest/events.py`:
   ```python
   "Your Event Name (YYMMDD)": {"layout": "flat"},
   # or for nested:
   "Your Event Name (YYMMDD)": {"layout": "nested", "categories": ["a", "b"]},
   ```
4. Dry-run: `python -m ai.airtable_ingest.ingest --dry-run --event "Your Event Name (YYMMDD)"`.

## Migrating from legacy folder names

Use the migration script:

```bash
python scripts/migrate_companyfiles.py            # dry-run
python scripts/migrate_companyfiles.py --apply    # rename for real
```

The mapping table in `scripts/migrate_companyfiles.py` is the source of truth for legacy → canonical renames. Edit there if you spot a name you want migrated.

## CompanyFiles location

`CompanyFiles/` does **not** live in this repo. It defaults to `~/Documents/Hunniwell/` and is overridable via `HUNNIWELL_COMPANYFILES_ROOT`. The reason: it's 18 GB of confidential decks and would be a liability inside a public repo even with gitignore.

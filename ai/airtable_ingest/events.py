"""
EVENT_LAYOUTS — canonical OneDrive event folder names that ingest.py walks.

To add a new event, append a new entry below. Keys MUST match the on-disk folder
name under $HUNNIWELL_COMPANYFILES_ROOT exactly. Schema per entry:

    "Event Name (260326)": {
        "layout": "flat",                       # company subdirs at depth 1
    }
    "Event Name (260115)": {
        "layout": "nested",                     # category subdirs at depth 1, companies at depth 2
        "categories": ["apac", "mti"],          # optional: validated if present, warns on extras
    }

The Airtable "Event" column uses the folder name verbatim (date suffix included).
For nested events, Airtable's "Event" value is "<folder name> - <category>"
(e.g. "JPM 2026 (260115) - HealthTech").
"""

EVENT_LAYOUTS: dict[str, dict] = {
    # JPM 2026: companies are scraped through RESI and end up in 10 RESI sector subdirs
    "JPM 2026 (260115)": {"layout": "nested"},

    # MTI 2026 events (Innovator portal): companies at depth 1
    "MTI 2026 - Virtual Pitch # 1 (260326)":      {"layout": "flat"},
    "MTI 2026 - APAC Virtual Pitch # 2 (260402)": {"layout": "flat"},
    "MTI 2026 - Virtual Pitch # 2 (260416)":      {"layout": "flat"},
    "MTI 2026 - Asia Medtech Spotlight (260418)": {"layout": "flat"},  # TODO confirm date
    "MTI 2026 - LA Radar Forum (260407)":         {"layout": "flat"},
    "MTI 2026 - Open Rounds":                     {"layout": "flat"},

    # MTI 2026 Prelim Reviews: nested by region
    "MTI 2026 - Prelim Reviews": {"layout": "nested", "categories": ["apac", "mti"]},

    # LSI 2026 events (Jujama platform): companies at depth 1
    "LSI 2026 - USA (260320)":  {"layout": "flat"},
    "LSI 2026 - ASia (260703)": {"layout": "flat"},
}

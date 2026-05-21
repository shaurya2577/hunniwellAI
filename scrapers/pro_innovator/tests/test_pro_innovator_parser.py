#!/usr/bin/env python3
import csv
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scrapers.pro_innovator.innovator_portal_reader import (
    parse_innovator_portal_html,
    parse_saved_pro_innovator_html,
    write_companies_to_csv,
)


SAMPLE_HTML = """
<html><body>
<div class="grid py-1 lg:grid-cols-4">
  <div class="col-span-1">Company Name</div>
  <div class="col-span-3">MediVault</div>
</div>
<div class="grid py-1 lg:grid-cols-4">
  <div class="col-span-1">Product Name</div>
  <div class="col-span-3">Records App</div>
</div>
<div class="grid py-1 lg:grid-cols-4">
  <div class="col-span-1">Product Name</div>
  <div class="col-span-3">Companion Portal</div>
</div>
<div class="grid py-1 lg:grid-cols-4">
  <div class="col-span-1">Company Name</div>
  <div class="col-span-3">Philia Labs</div>
</div>
<div class="grid py-1 lg:grid-cols-4">
  <div class="col-span-1">Pitch deck</div>
  <div class="col-span-3">Philia Deck.pdf</div>
</div>
</body></html>
"""

SAMPLE_GRID_HTML = """
<html><body>
<div class="ag-pinned-left-cols-container" role="rowgroup">
  <div role="row" row-id="18945" aria-rowindex="3">
    <div role="gridcell" col-id="company.name"><span class="ag-group-value">MediVault</span></div>
  </div>
  <div role="row" row-id="19072" aria-rowindex="4">
    <div role="gridcell" col-id="company.name"><span class="ag-group-value">Philia Labs</span></div>
  </div>
</div>
<div class="ag-center-cols-container" role="rowgroup">
  <div role="row" row-id="18945" aria-rowindex="3">
    <div role="gridcell" col-id="submissionData.oneLineDescription">Family health records</div>
    <div role="gridcell" col-id="submissionData.developmentStage">Commercial</div>
  </div>
  <div role="row" row-id="19072" aria-rowindex="4">
    <div role="gridcell" col-id="submissionData.oneLineDescription">Diagnostics platform</div>
  </div>
</div>
</body></html>
"""


class InnovatorPortalReaderTests(unittest.TestCase):
    def test_parse_saved_html_into_company_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = Path(tmpdir) / "portal.html"
            html_path.write_text(SAMPLE_HTML, encoding="utf-8")

            companies = parse_innovator_portal_html(str(html_path))

        self.assertEqual(2, len(companies))
        self.assertEqual("MediVault", companies[0]["Company Name"])
        self.assertEqual(
            "Records App | Companion Portal", companies[0]["Product Name"]
        )
        self.assertEqual("Philia Deck.pdf", companies[1]["Pitch deck"])

    def test_write_companies_to_csv_preserves_discovered_headers(self):
        companies = [
            {"Company Name": "MediVault", "Pitch deck": "Deck.pdf"},
            {"Company Name": "Philia Labs", "Website": "https://example.com"},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "companies.csv"
            write_companies_to_csv(companies, str(csv_path))

            with csv_path.open(newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))

        self.assertEqual(2, len(rows))
        self.assertEqual("MediVault", rows[0]["Company Name"])
        self.assertIn("Pitch deck", rows[0])
        self.assertIn("Website", rows[0])

    def test_parse_saved_grid_html_falls_back_to_grid_schema(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = Path(tmpdir) / "grid.html"
            html_path.write_text(SAMPLE_GRID_HTML, encoding="utf-8")

            companies = parse_saved_pro_innovator_html(str(html_path))

        self.assertEqual(2, len(companies))
        self.assertEqual("MediVault", companies[0]["Company Name"])
        self.assertEqual("Family health records", companies[0]["One-liner"])


if __name__ == "__main__":
    unittest.main()

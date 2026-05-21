#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from platforms.innovator.pro_innovator.grid_extract import (
    build_company_records,
    extract_grid_rows_from_html,
)


SAMPLE_GRID_HTML = """
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
    <div role="gridcell" col-id="submissionData.totalEquityFunding">$3M</div>
    <div role="gridcell" col-id="submissionData.openNextRound">Seed+</div>
    <div role="gridcell" col-id="submissionData.preferredPitchLocation">Swiss</div>
  </div>
  <div role="row" row-id="19072" aria-rowindex="4">
    <div role="gridcell" col-id="submissionData.oneLineDescription">Diagnostics platform</div>
    <div role="gridcell" col-id="submissionData.developmentStage">Clinical</div>
  </div>
</div>
"""


class ProInnovatorGridExtractTests(unittest.TestCase):
    def test_extract_grid_rows_from_html_merges_pinned_and_center_cells(self):
        rows = extract_grid_rows_from_html(SAMPLE_GRID_HTML)

        self.assertEqual(2, len(rows))
        self.assertEqual("18945", rows[0]["row_id"])
        self.assertEqual("MediVault", rows[0]["company.name"])
        self.assertEqual(
            "Family health records", rows[0]["submissionData.oneLineDescription"]
        )

    def test_build_company_records_maps_first_version_csv_schema(self):
        records = build_company_records(extract_grid_rows_from_html(SAMPLE_GRID_HTML))

        self.assertEqual(2, len(records))
        self.assertEqual("MediVault", records[0]["Company Name"])
        self.assertEqual("Family health records", records[0]["One-liner"])
        self.assertEqual("Commercial", records[0]["Development Stage"])
        self.assertEqual("Swiss", records[0]["Preferred Pitch Location"])
        self.assertEqual("Philia Labs", records[1]["Company Name"])


if __name__ == "__main__":
    unittest.main()

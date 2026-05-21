#!/usr/bin/env python3
"""AG Grid extraction helpers for the live Pro Innovator Applications page."""

import csv
import re
from html import unescape

from scrapers.pro_innovator import config


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return " ".join(unescape(text).split()).strip()


def _normalize_company_cell(cell_html: str) -> str:
    match = re.search(r'<[^>]*class="[^"]*ag-group-value[^"]*"[^>]*>([\s\S]*?)</', cell_html)
    if match:
        value = _strip_html(match.group(1))
    else:
        value = _strip_html(cell_html)

    repeated = re.match(r"^(.+?)\s+\1(?:$|[\s:.-])", value)
    if repeated:
        return repeated.group(1).strip()
    return value


def extract_grid_rows_from_html(html: str) -> list:
    """
    Parse a saved AG Grid DOM snapshot into row dicts.

    This is used in tests and for offline debugging. The live runner uses the
    same row shape, but collects it via page.evaluate from the actual page.
    """
    row_map = {}
    row_starts = list(
        re.finditer(r'<div[^>]*role="row"[^>]*row-id="([^"]+)"[^>]*>', html, re.DOTALL)
    )

    for index, row_match in enumerate(row_starts):
        row_id = row_match.group(1)
        start = row_match.end()
        end = row_starts[index + 1].start() if index + 1 < len(row_starts) else len(html)
        row_html = html[start:end]
        row = row_map.setdefault(row_id, {"row_id": row_id})
        for cell_match in re.finditer(
            r'<div[^>]*role="gridcell"[^>]*col-id="([^"]+)"[^>]*>([\s\S]*?)</div>',
            row_html,
            re.DOTALL,
        ):
            col_id, cell_html = cell_match.groups()
            if col_id == "company.name":
                value = _normalize_company_cell(cell_html)
            else:
                value = _strip_html(cell_html)
            if value:
                row[col_id] = value

    return sorted(row_map.values(), key=lambda item: item.get("row_id", ""))


def build_company_records(rows: list) -> list:
    """Map raw AG Grid rows into the first-version Pro Innovator CSV schema."""
    records = []
    for row in rows:
        company_name = (row.get("company.name") or "").strip()
        if not company_name:
            continue
        records.append(
            {
                "Company Name": company_name,
                "Row ID": (row.get("row_id") or "").strip(),
                "One-liner": (row.get("submissionData.oneLineDescription") or "").strip(),
                "Development Stage": (row.get("submissionData.developmentStage") or "").strip(),
                "Total Equity Funding": (row.get("submissionData.totalEquityFunding") or "").strip(),
                "Next Round": (row.get("submissionData.openNextRound") or "").strip(),
                "Preferred Pitch Location": (
                    row.get("submissionData.preferredPitchLocation") or ""
                ).strip(),
                "Deck Status": "",
                "Deck Source URL": "",
                "Rebuilt PDF Path": "",
            }
        )
    return records


def write_company_records_csv(records: list, csv_path) -> None:
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=config.CSV_HEADERS)
        writer.writeheader()
        for record in records:
            writer.writerow({header: record.get(header, "") for header in config.CSV_HEADERS})


def extract_live_grid_rows(page) -> list:
    """
    Collect AG Grid rows from the live page by scrolling the grid viewport.

    Rows are keyed by `row-id` and merged across the pinned-left and center
    containers so the first version works even when only some columns are in the
    main viewport.
    """
    script = """
() => {
  const rows = {};
  const addCells = (selector) => {
    document.querySelectorAll(selector).forEach((row) => {
      const rowId = row.getAttribute('row-id');
      if (!rowId) return;
      rows[rowId] = rows[rowId] || { row_id: rowId };
      row.querySelectorAll('[role="gridcell"][col-id]').forEach((cell) => {
        const colId = cell.getAttribute('col-id');
          let text = '';
          if (colId === 'company.name') {
            const primary = cell.querySelector('.ag-group-value');
            text = ((primary && (primary.innerText || primary.textContent)) || cell.innerText || cell.textContent || '')
              .replace(/\\s+/g, ' ')
              .trim();
          } else {
            text = (cell.innerText || cell.textContent || '').replace(/\\s+/g, ' ').trim();
          }
        if (colId && text) rows[rowId][colId] = text;
      });
    });
  };
  addCells('.ag-pinned-left-cols-container [role="row"][row-id]');
  addCells('.ag-center-cols-container [role="row"][row-id]');
  return Object.values(rows);
}
"""

    merged = {}
    viewport_selectors = [
        ".ag-body-viewport",
        ".ag-center-cols-viewport",
        ".ag-body-horizontal-scroll-viewport",
    ]

    def merge_rows(items):
        if not isinstance(items, list):
            return
        for item in items:
            if not isinstance(item, dict):
                continue
            row_id = item.get("row_id")
            if not row_id:
                continue
            merged.setdefault(row_id, {"row_id": row_id}).update(item)

    merge_rows(page.evaluate(script))

    viewport = None
    active_selector = None
    for selector in viewport_selectors:
        locator = page.locator(selector).first
        if locator.count() > 0:
            viewport = locator
            active_selector = selector
            break

    if viewport is None:
        return list(merged.values())

    previous_top = -1
    for _ in range(config.MAX_GRID_SCROLLS):
        next_top = page.evaluate(
            """(selector) => {
                const viewport = document.querySelector(selector);
                if (!viewport) return -1;
                viewport.scrollTop = viewport.scrollTop + viewport.clientHeight;
                return viewport.scrollTop;
            }""",
            active_selector,
        )
        page.wait_for_timeout(config.GRID_SCROLL_PAUSE_MS)
        merge_rows(page.evaluate(script))
        if next_top == previous_top:
            break
        previous_top = next_top

    page.evaluate(
        """(selector) => {
            const viewport = document.querySelector(selector);
            if (viewport) viewport.scrollTop = 0;
        }""",
        active_selector,
    )
    return list(merged.values())

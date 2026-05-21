#!/usr/bin/env python3
"""
Offline parser for saved MedTech Innovator Radar Forum / Pitch Report HTML pages.

Extracts company data from the AG Grid DOM snapshot and any expanded detail panels,
merges across multiple saved HTML files, and writes a single CSV.

Usage:
    python -m scrapers.pro_innovator.radar_portal_reader \
        file1.html [file2.html ...] [-o output.csv]

Each HTML file should be a "Save As → Webpage, Complete" snapshot of the
pro.innovator.org Radar Forum pitch-report page.
"""

import argparse
import csv
import html
import re
import sys
from pathlib import Path
from urllib.parse import unquote

# ---------------------------------------------------------------------------
# Column mapping from AG Grid col-id to CSV header
# ---------------------------------------------------------------------------
GRID_COL_MAP = {
    "submissionData.oneLineDescription": "Short Description",
    "company.country": "Country",
    "0": "Clinical Areas",
    "1": "Round",
}

DETAIL_FIELDS = [
    "Year Founded",
    "Website",
    "Website URL",
    "Detail Country",
    "State",
    "City",
    "Pitch Deck",
    "Pitch Deck URL",
    "5 Minute Pitch Recording",
    "Pitch Recording URL",
    "Pitch Event Video",
    "Pitch Event Video URL",
    "Product Name",
    "One-Line Description",
    "Product Abstract",
    "Product Description",
    "Product Development Stage",
    "On Market",
    "Product Video URL",
    "Product Video Password",
]

CSV_HEADERS = [
    "Row ID",
    "Company Name",
    "Product Name (Grid)",
    "Logo File",
    "Short Description",
    "Country",
    "Clinical Areas",
    "Round",
] + DETAIL_FIELDS

LABEL_TO_FIELD = {
    "What year was your organization founded?": "Year Founded",
    "Website": "Website",
    "Country": "Detail Country",
    "State": "State",
    "City": "City",
    "Pitch Deck": "Pitch Deck",
    "5 Minute Pitch Recording": "5 Minute Pitch Recording",
    "Pitch Event Video": "Pitch Event Video",
    "Product Name": "Product Name",
    "One-Line Description": "One-Line Description",
    "Product abstract": "Product Abstract",
    "Product Description": "Product Description",
    "Product development stage": "Product Development Stage",
    "Is this product currently on the market?": "On Market",
    "Product Video URL": "Product Video URL",
    "Product Video Password": "Product Video Password",
}

LINK_FIELDS = {
    "Website": "Website URL",
    "Pitch Deck": "Pitch Deck URL",
    "5 Minute Pitch Recording": "Pitch Recording URL",
    "Pitch Event Video": "Pitch Event Video URL",
}


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return " ".join(html.unescape(text).split()).strip()


def _decode_url(url: str) -> str:
    """Decode HTML entities only; preserve percent-encoding so signed URLs stay intact."""
    return html.unescape(url)


# ---------------------------------------------------------------------------
# Grid row extraction (pinned-left + center containers)
# ---------------------------------------------------------------------------

def _container_chunk(content: str, class_name: str) -> str:
    """Return the HTML slice from the given container up to the next sibling container."""
    start = content.find(f'class="{class_name}"')
    if start == -1:
        return ""
    candidates = [
        content.find('class="ag-center-cols-container"', start + 1),
        content.find('class="ag-full-width-container"', start + 1),
    ]
    end = min((c for c in candidates if c > start), default=len(content))
    return content[start:end]


def _extract_pinned_rows(content: str) -> dict:
    """Return {row_id: {Company Name, Product Name (Grid), Logo File}}."""
    rows = {}
    chunk = _container_chunk(content, "ag-pinned-left-cols-container")
    if not chunk:
        return rows

    row_starts = list(
        re.finditer(r'<div[^>]*role="row"[^>]*row-id="(\d+)"[^>]*>', chunk)
    )
    for i, m in enumerate(row_starts):
        row_id = m.group(1)
        start = m.end()
        end = row_starts[i + 1].start() if i + 1 < len(row_starts) else len(chunk)
        cell_html = chunk[start:end]

        name_m = re.search(
            r'<div class="font-semibold truncate">([^<]+)</div>', cell_html
        )
        prod_m = re.search(
            r'<div class="text-xs text-gray-500 italic truncate">([^<]*)</div>',
            cell_html,
        )
        logo_m = re.search(r'src="([^"]+)"', cell_html)

        rows[row_id] = {
            "Row ID": row_id,
            "Company Name": _strip_html(name_m.group(1)) if name_m else "",
            "Product Name (Grid)": _strip_html(prod_m.group(1)) if prod_m else "",
            "Logo File": logo_m.group(1) if logo_m else "",
        }
    return rows


def _extract_center_rows(content: str) -> dict:
    """Return {row_id: {Short Description, Country, Clinical Areas, Round}}."""
    rows = {}
    chunk = _container_chunk(content, "ag-center-cols-container")
    if not chunk:
        return rows

    row_starts = list(
        re.finditer(r'<div[^>]*role="row"[^>]*row-id="(\d+)"[^>]*>', chunk)
    )
    for i, m in enumerate(row_starts):
        row_id = m.group(1)
        start = m.end()
        end = row_starts[i + 1].start() if i + 1 < len(row_starts) else len(chunk)
        row_html = chunk[start:end]

        row_data = {}
        for cell_m in re.finditer(
            r'<div[^>]*role="gridcell"[^>]*col-id="([^"]+)"[^>]*>([\s\S]*?)(?=<div[^>]*role="gridcell"|<div[^>]*role="row"|$)',
            row_html,
        ):
            col_id = cell_m.group(1)
            cell_text = _strip_html(cell_m.group(2))
            csv_col = GRID_COL_MAP.get(col_id)
            if csv_col and cell_text:
                row_data[csv_col] = cell_text

        if row_data:
            rows[row_id] = row_data
    return rows


# ---------------------------------------------------------------------------
# Expanded detail extraction
# ---------------------------------------------------------------------------

def _extract_expanded_details(content: str) -> dict:
    """Return {row_id: {field: value, ...}} for each expanded detail panel."""
    details = {}
    detail_starts = list(re.finditer(r'row-id="detail_(\d+)"', content))

    for i, m in enumerate(detail_starts):
        row_id = m.group(1)
        start = m.start()
        end = detail_starts[i + 1].start() if i + 1 < len(detail_starts) else len(content)
        detail_html = content[start:end]

        record = {}
        pairs = re.findall(
            r'col-span-1[^>]*>\s*(?:<p[^>]*>)?\s*([^<]+?)\s*(?:</p>)?\s*</div>'
            r'\s*<div[^>]*col-span-3[^>]*>(.*?)</div>\s*</div>',
            detail_html,
            re.DOTALL,
        )
        for raw_label, raw_value in pairs:
            label = raw_label.strip()
            field = LABEL_TO_FIELD.get(label)
            if not field:
                continue

            text_value = _strip_html(raw_value)
            record[field] = text_value

            link_field = LINK_FIELDS.get(label)
            if link_field:
                links = re.findall(r'href="([^"]*)"', raw_value)
                if links:
                    record[link_field] = _decode_url(links[0])

        if record:
            details[row_id] = record
    return details


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_radar_html(html_path: str) -> dict:
    """
    Parse one saved Radar Forum HTML and return {row_id: record_dict}.
    """
    with open(html_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    pinned = _extract_pinned_rows(content)
    center = _extract_center_rows(content)
    details = _extract_expanded_details(content)

    merged = {}
    all_ids = set(pinned) | set(center)
    for rid in all_ids:
        rec = {}
        rec.update(pinned.get(rid, {}))
        rec.update(center.get(rid, {}))
        rec.update(details.get(rid, {}))
        if rec.get("Company Name"):
            merged[rid] = rec

    return merged


def merge_records(all_records: list[dict]) -> list[dict]:
    """Merge record dicts from multiple HTML files, keyed by Row ID."""
    combined = {}
    for file_records in all_records:
        for rid, rec in file_records.items():
            if rid not in combined:
                combined[rid] = dict(rec)
            else:
                for k, v in rec.items():
                    if v and not combined[rid].get(k):
                        combined[rid][k] = v

    return sorted(combined.values(), key=lambda r: r.get("Company Name", ""))


def write_csv(records: list[dict], output_path: str) -> None:
    if not records:
        print("No companies found.")
        return

    all_keys = list(CSV_HEADERS)
    for rec in records:
        for k in rec:
            if k not in all_keys:
                all_keys.append(k)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        for rec in records:
            row = {
                k: (rec.get(k) or "").replace("\n", " ").replace("\r", "")
                for k in all_keys
            }
            writer.writerow(row)

    print("Wrote %d companies to %s" % (len(records), output_path))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse saved Radar Forum HTML pages into a CSV."
    )
    parser.add_argument(
        "html_files",
        nargs="*",
        help="Path(s) to saved HTML files. Defaults to ~/Scratch/radar/Innovator Portal*.html",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output CSV path (default: radar_companies.csv next to this script)",
    )
    args = parser.parse_args()

    html_files = args.html_files
    if not html_files:
        radar_dir = Path.home() / "Scratch" / "radar"
        html_files = sorted(str(p) for p in radar_dir.glob("Innovator Portal*.html"))
        if not html_files:
            print("No HTML files found in %s" % radar_dir)
            sys.exit(1)

    output_path = args.output or str(
        Path(__file__).parent / "radar_companies.csv"
    )

    print("Parsing %d HTML file(s)..." % len(html_files))
    all_records = []
    for path in html_files:
        if not Path(path).exists():
            print("  WARNING: %s not found, skipping." % path)
            continue
        records = parse_radar_html(path)
        print("  %s: %d companies, %d with detail" % (
            Path(path).name,
            len(records),
            sum(1 for r in records.values() if r.get("Year Founded")),
        ))
        all_records.append(records)

    merged = merge_records(all_records)
    write_csv(merged, output_path)


if __name__ == "__main__":
    main()

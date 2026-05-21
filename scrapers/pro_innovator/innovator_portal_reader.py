#!/usr/bin/env python3
"""
Offline fallback parser for saved MedTech Innovator Pro Innovator HTML.

This remains useful for debugging selector changes or generating a CSV when the
live Playwright run is not needed.
"""

import csv
import html
import re
import sys
from pathlib import Path
from urllib.parse import unquote

from scrapers.pro_innovator.grid_extract import (
    build_company_records,
    extract_grid_rows_from_html,
)


def strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = " ".join(text.split())
    return text.strip()


def parse_innovator_portal_html(html_path: str) -> list:
    """
    Parse the saved portal HTML and return a list of company records.
    Each record is a dict mapping field labels to values.
    """
    with open(html_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    grid_pattern = re.compile(
        r'<div class="[^"]*grid[^"]*lg:grid-cols-4[^"]*"[^>]*>\s*'
        r'<div class="[^"]*col-span-1[^"]*"[^>]*>([\s\S]*?)</div>\s*'
        r'<div class="[^"]*col-span-3[^"]*"[^>]*>([\s\S]*?)</div>\s*'
        r"</div>",
        re.DOTALL,
    )

    all_pairs = []
    for match in grid_pattern.finditer(content):
        label = strip_html(match.group(1))
        raw_value = match.group(2) or ""
        value = strip_html(raw_value)
        hrefs = re.findall(r'href="([^"]+)"', raw_value)
        hrefs = [_decode_url(h).strip() for h in hrefs if (h or "").strip()]
        if label and not label.startswith("["):
            all_pairs.append((label, value, hrefs))

    companies = []
    current_company = {}
    seen_company_name = False

    for label, value, hrefs in all_pairs:
        if label == "Company Name":
            if current_company:
                companies.append(current_company)
            current_company = {"Company Name": value}
            seen_company_name = True
        elif seen_company_name:
            if label in current_company and current_company[label]:
                existing = current_company[label]
                if value and value != existing:
                    current_company[label] = "%s | %s" % (existing, value)
            else:
                current_company[label] = value
            if hrefs:
                url_key = f"{label} URL"
                current_company[url_key] = _merge_value(
                    current_company.get(url_key, ""), " | ".join(hrefs)
                )

    if current_company:
        companies.append(current_company)

    return companies


def parse_saved_pro_innovator_html(html_path: str) -> list:
    """
    Parse either:
    - the legacy detailed application HTML, or
    - the newer saved AG Grid Applications page.
    """
    with open(html_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # 1) Legacy detailed application HTML (older snapshots).
    detailed_records = parse_innovator_portal_html(html_path)
    if detailed_records:
        return detailed_records

    # 2) Newer Applications page: AG Grid + expandable detail panels.
    if "ag-root" in content or "ag-center-cols-container" in content:
        return _parse_saved_applications_ag_grid_html(content)

    # 3) Fallback: basic grid-only extraction (first version schema).
    return build_company_records(extract_grid_rows_from_html(content))


def _decode_url(url: str) -> str:
    """Decode HTML entities only; preserve percent-encoding (signed URLs)."""
    return html.unescape(url or "")


def _merge_value(existing: str, new: str) -> str:
    existing = (existing or "").strip()
    new = (new or "").strip()
    if not new:
        return existing
    if not existing:
        return new
    if new == existing:
        return existing
    # Avoid exploding duplicates when the same token repeats.
    existing_parts = [p.strip() for p in existing.split(" | ") if p.strip()]
    if new in existing_parts:
        return existing
    return existing + " | " + new


def _parse_saved_applications_ag_grid_html(content: str) -> list[dict]:
    """
    Parse a saved Applications (Pro Innovator) HTML snapshot:
    - Extract AG Grid row data (company + visible columns)
    - Extract expanded detail panels (all label/value pairs + link URLs)

    Returns: list of company dicts with a superset of fields.
    """
    rows = extract_grid_rows_from_html(content)
    by_row_id: dict[str, dict] = {}
    for row in rows:
        row_id = (row.get("row_id") or "").strip()
        name = (row.get("company.name") or "").strip()
        if not row_id or not name:
            continue
        rec = by_row_id.setdefault(row_id, {"Row ID": row_id, "Company Name": name})
        # Keep all grid columns (col-id) for debugging/completeness.
        for k, v in row.items():
            if k in ("row_id",):
                continue
            if not v:
                continue
            if k == "company.name":
                continue
            rec[f"Grid: {k}"] = _merge_value(rec.get(f"Grid: {k}", ""), str(v).strip())

    # Expanded detail panels follow the pattern: row-id="detail_<row_id>"
    detail_starts = list(re.finditer(r'row-id="detail_([^"]+)"', content))
    for i, m in enumerate(detail_starts):
        row_id = (m.group(1) or "").strip()
        start = m.start()
        end = detail_starts[i + 1].start() if i + 1 < len(detail_starts) else len(content)
        detail_html = content[start:end]

        rec = by_row_id.setdefault(row_id, {"Row ID": row_id, "Company Name": ""})

        # The detail UI uses a 4-col grid with label/value split as col-span-1 / col-span-3
        pairs = re.findall(
            r'col-span-1[^>]*>\s*(?:<p[^>]*>)?\s*([^<]+?)\s*(?:</p>)?\s*</div>'
            r'\s*<div[^>]*col-span-3[^>]*>(.*?)</div>\s*</div>',
            detail_html,
            re.DOTALL,
        )
        for raw_label, raw_value in pairs:
            label = strip_html(raw_label)
            if not label:
                continue
            value_text = strip_html(raw_value)
            if value_text:
                rec[label] = _merge_value(rec.get(label, ""), value_text)

            hrefs = re.findall(r'href="([^"]*)"', raw_value)
            hrefs = [_decode_url(h).strip() for h in hrefs if (h or "").strip()]
            if hrefs:
                # Preserve full viewer URLs; downstream tooling can unwrap if needed.
                rec[f"{label} URL"] = _merge_value(rec.get(f"{label} URL", ""), " | ".join(hrefs))

        # Also capture any attachment links rendered outside the label/value grid,
        # e.g. in "Application Files" sections.
        attachment_urls: list[str] = []
        attachment_items: list[str] = []
        for anchor_match in re.finditer(
            r'<a[^>]+href="([^"]+)"[^>]*>([\s\S]*?)</a>',
            detail_html,
            re.DOTALL,
        ):
            href = _decode_url(anchor_match.group(1)).strip()
            text = strip_html(anchor_match.group(2))
            if not href:
                continue
            if "file-viewer?url=" in href or "media.innovator.org/" in href or "mti-innovator.s3" in href or "officeapps.live.com" in href:
                attachment_urls.append(href)
                if text:
                    attachment_items.append(text)

        if attachment_urls:
            rec["Attachments"] = _merge_value(rec.get("Attachments", ""), " | ".join(attachment_items) if attachment_items else "")
            rec["Attachments URL"] = _merge_value(rec.get("Attachments URL", ""), " | ".join(attachment_urls))

    # Post-process: fill missing Company Name from any field that looks like it.
    for rec in by_row_id.values():
        if rec.get("Company Name"):
            continue
        # Some snapshots embed company name in Grid cells only.
        for k in ("Grid: company.name", "Company", "Name"):
            if (rec.get(k) or "").strip():
                rec["Company Name"] = (rec.get(k) or "").strip()
                break

    # Stable sort by name for deterministic CSV output.
    return sorted(by_row_id.values(), key=lambda r: (r.get("Company Name") or "", r.get("Row ID") or ""))


def write_companies_to_csv(companies: list, output_path: str) -> None:
    """Write company records to CSV with a merged header set."""
    if not companies:
        print("No companies found.")
        return

    all_keys = ["Company Name"]
    for company in companies:
        for key in company:
            if key not in all_keys:
                all_keys.append(key)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        for company in companies:
            row = {
                key: (company.get(key) or "").replace("\n", " ").replace("\r", "")
                for key in all_keys
            }
            writer.writerow(row)

    print("Wrote %d companies to %s" % (len(companies), output_path))


def main() -> None:
    default_html = Path.home() / "Scratch" / "pro innovator" / "Innovator Portal.html"
    default_output = Path(__file__).parent / "innovator_companies.csv"

    html_path = sys.argv[1] if len(sys.argv) > 1 else str(default_html)
    output_path = sys.argv[2] if len(sys.argv) > 2 else str(default_output)

    if not Path(html_path).exists():
        print("Error: HTML file not found: %s" % html_path)
        print("Usage: python innovator_portal_reader.py [html_path] [output_csv_path]")
        sys.exit(1)

    companies = parse_innovator_portal_html(html_path)
    write_companies_to_csv(companies, output_path)


if __name__ == "__main__":
    main()

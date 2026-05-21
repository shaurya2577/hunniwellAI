#!/usr/bin/env python3
"""
Innovator Portal HTML Reader

Parses a saved MedTech Innovator Portal HTML file and extracts company application
data into a CSV file. Each company's data (Company Name, Product Name, Product
Description, funding, milestones, etc.) becomes one row in the output CSV.

Uses only Python standard library (no external dependencies).
"""

import csv
import html
import re
import sys
from pathlib import Path


def strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = " ".join(text.split())
    return text.strip()


def parse_innovator_portal_html(html_path: str) -> list[dict]:
    """
    Parse the Innovator Portal HTML and return a list of company records.
    Each record is a dict mapping field labels to values.
    """
    with open(html_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Pattern: grid with col-span-1 (label) followed by col-span-3 (value)
    # <div class="grid py-1 lg:grid-cols-4..."><div class="col-span-1...">LABEL</div><div class="col-span-3...">VALUE</div>
    # Use regex to find label-value pairs - handle nested content
    pattern = re.compile(
        r'<div class="[^"]*col-span-1[^"]*"[^>]*>([^<]*(?:<[^>]+>[^<]*)*)</div>\s*'
        r'<div class="[^"]*col-span-3[^"]*"[^>]*>([\s\S]*?)</div>\s*</div>',
        re.DOTALL,
    )

    # Simpler alternative: find grid divs and extract first two child div contents
    # Match: <div class="grid py-1 lg:grid-cols-4..."><div...>LABEL</div><div...>VALUE</div>
    # The structure is: grid > div (label) > div (value)
    grid_pattern = re.compile(
        r'<div class="grid py-1 lg:grid-cols-4[^"]*"[^>]*>'
        r'<div class="[^"]*col-span-1[^"]*"[^>]*>([\s\S]*?)</div>\s*'
        r'<div class="[^"]*col-span-3[^"]*"[^>]*>([\s\S]*?)</div>\s*'
        r'</div>',
        re.DOTALL,
    )

    all_pairs: list[tuple[str, str]] = []
    for m in grid_pattern.finditer(content):
        label = strip_html(m.group(1))
        value = strip_html(m.group(2))
        if label and not label.startswith("["):  # Skip aria/script labels
            all_pairs.append((label, value))

    # Split into company blocks by "Company Name" - each occurrence starts a new company
    companies: list[dict] = []
    current_company: dict = {}
    seen_company_name = False

    for label, value in all_pairs:
        if label == "Company Name":
            if current_company:
                companies.append(current_company)
            current_company = {"Company Name": value}
            seen_company_name = True
        elif seen_company_name:
            key = label
            if key in current_company and current_company[key]:
                existing = current_company[key]
                if value and value != existing:
                    current_company[key] = f"{existing} | {value}"
            else:
                current_company[key] = value

    if current_company:
        companies.append(current_company)

    return companies


def write_companies_to_csv(companies: list[dict], output_path: str) -> None:
    """Write company records to CSV with proper escaping."""
    if not companies:
        print("No companies found.")
        return

    # Collect all unique keys across companies, with Company Name first
    all_keys = ["Company Name"]
    for c in companies:
        for k in c:
            if k not in all_keys:
                all_keys.append(k)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        for c in companies:
            row = {k: (c.get(k) or "").replace("\n", " ").replace("\r", "") for k in all_keys}
            writer.writerow(row)

    print(f"Wrote {len(companies)} companies to {output_path}")


def main():
    # Default paths - can be overridden by command line
    default_html = Path.home() / "Scratch" / "pro innovator" / "Innovator Portal.html"
    default_output = Path(__file__).parent / "innovator_companies.csv"

    html_path = sys.argv[1] if len(sys.argv) > 1 else str(default_html)
    output_path = sys.argv[2] if len(sys.argv) > 2 else str(default_output)

    if not Path(html_path).exists():
        print(f"Error: HTML file not found: {html_path}")
        print("Usage: python innovator_portal_reader.py [html_path] [output_csv_path]")
        sys.exit(1)

    companies = parse_innovator_portal_html(html_path)
    write_companies_to_csv(companies, output_path)


if __name__ == "__main__":
    main()

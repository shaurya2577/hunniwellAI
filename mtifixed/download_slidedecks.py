#!/usr/bin/env python3
"""
Download pitch decks and application files from MedTech Innovator Portal.

Requires: pip install playwright
          playwright install chromium

Usage:
  1. Run: python download_slidedecks.py
  2. When the browser opens, log in manually at pro.innovator.org
  3. Press Enter in the terminal when logged in
  4. Script will navigate to applications and attempt to download files

Output: Files saved to ./downloads/<CompanyName>/<filename>
"""

import csv
import re
import sys
import time
from pathlib import Path

# Check for playwright
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Installing playwright...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    from playwright.sync_api import sync_playwright


def sanitize_filename(name: str) -> str:
    """Make string safe for use as filename."""
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip()[:80]


def get_companies_from_csv(csv_path: str) -> list[dict]:
    """Load company names and file info from CSV."""
    companies = []
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            name = row.get("Company Name", "").strip()
            if name:
                companies.append({
                    "name": name,
                    "pitch_deck": row.get("Pitch deck", "").strip(),
                    "product_photo": row.get("Product Photo", "").strip(),
                    "other_docs": row.get("Other Supporting Documents", "").strip(),
                })
    return companies


def main():
    script_dir = Path(__file__).parent
    csv_path = script_dir / "innovator_companies.csv"
    downloads_dir = script_dir / "downloads"

    if not csv_path.exists():
        print(f"Error: {csv_path} not found. Run innovator_portal_reader.py first.")
        sys.exit(1)

    companies = get_companies_from_csv(str(csv_path))
    print(f"Found {len(companies)} companies in CSV")

    portal_url = "https://pro.innovator.org/applications/apac/cohort-year/2026?assignedTo=Daniel%20Teo"

    print("\nOpening browser. Please log in manually.")
    input("Press Enter when you are logged in and on the applications page...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        try:
            page.goto(portal_url, wait_until="networkidle", timeout=60000)
            time.sleep(2)

            # Find and expand each company row, then look for download links
            for i, company in enumerate(companies):
                name = company["name"]
                safe_name = sanitize_filename(name)
                company_dir = downloads_dir / safe_name
                company_dir.mkdir(parents=True, exist_ok=True)

                print(f"\n[{i+1}/{len(companies)}] {name}")

                # Try to find expand button / row for this company
                # AG Grid uses company names in cells - look for expand icon
                try:
                    # Click expand button (ag-group-contracted or similar)
                    expand_btn = page.locator(f'text="{name}"').first
                    if expand_btn.count() > 0:
                        # Click the row to expand
                        expand_btn.click()
                        time.sleep(2)

                    # Look for download links in Application Files section
                    links = page.locator('a[href*="download"], a[href*="file"], a[download]')
                    for j in range(links.count()):
                        link = links.nth(j)
                        href = link.get_attribute("href")
                        text = link.inner_text().strip()

                        if href and (".pdf" in href.lower() or ".pdf" in text.lower() or "deck" in text.lower()):
                            with page.expect_download() as download_info:
                                link.click()
                            download = download_info.value
                            save_path = company_dir / sanitize_filename(download.suggested_filename or f"file_{j}.pdf")
                            download.save_as(str(save_path))
                            print(f"  Saved: {save_path.name}")

                except Exception as e:
                    print(f"  Skipped: {e}")

                time.sleep(1)

        finally:
            browser.close()

    print(f"\nDone. Files saved to {downloads_dir}")


if __name__ == "__main__":
    main()

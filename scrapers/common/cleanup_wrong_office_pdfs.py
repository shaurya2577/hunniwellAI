#!/usr/bin/env python3
"""
Remove "wrong" PDFs that were downloaded for Office sources (ppt/pptx).

We delete a <stem>.pdf only when:
- the media URL in radar_media_index.csv ends with .pptx or .ppt
- and a matching <stem>.pptx or <stem>.ppt exists in the same company folder

This preserves real PDFs for entries whose URLs are PDFs.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path


def _is_office_url(url: str) -> str | None:
    u = (url or "").lower().strip()
    if u.endswith(".pptx"):
        return ".pptx"
    if u.endswith(".ppt"):
        return ".ppt"
    # Sometimes the URL may contain query params; check contained suffix too.
    if ".pptx" in u:
        return ".pptx"
    if ".ppt" in u:
        return ".ppt"
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description="Delete wrong Office-typed PDFs for ppt/pptx URLs.")
    ap.add_argument(
        "--output-dir",
        "-o",
        action="append",
        required=True,
        help="An output directory containing radar_media_index.csv and company folders.",
    )
    args = ap.parse_args()

    # Import downloader helpers (filename/stem logic)
    resi_root = Path(__file__).resolve().parent
    sys.path.insert(0, str(resi_root))
    from scrapers.common.download import sanitize_filename

    deleted = 0
    checked = 0

    for out_root_str in args.output_dir:
        out_root = Path(out_root_str).expanduser().resolve()
        index_path = out_root / "radar_media_index.csv"
        if not index_path.exists():
            print(f"[skip] No radar_media_index.csv in {out_root}")
            continue

        with index_path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                company = (row.get("Company Name") or "").strip()
                label = (row.get("Link Label") or "").strip()
                url = (row.get("PDF URL") or "").strip()
                if not (company and label and url):
                    continue

                office_ext = _is_office_url(url)
                if not office_ext:
                    continue

                checked += 1

                company_dir = out_root / sanitize_filename(company)
                if not company_dir.is_dir():
                    # Flat output should have the company folder; if missing, skip.
                    continue

                base = sanitize_filename(company)
                raw = sanitize_filename(label, max_length=60)
                # Match downloader: strip common media extensions from label
                for e in (".pdf", ".mp4", ".png", ".pptx", ".ppt"):
                    if raw.lower().endswith(e):
                        raw = raw[: -len(e)]
                        break
                stem = base + "_" + raw

                correct_office = company_dir / (stem + office_ext)
                wrong_pdf = company_dir / (stem + ".pdf")

                if correct_office.exists() and wrong_pdf.exists():
                    wrong_pdf.unlink(missing_ok=True)
                    deleted += 1

    print(f"Cleanup complete: checked {checked}, deleted {deleted}.")


if __name__ == "__main__":
    main()


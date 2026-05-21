#!/usr/bin/env python3
"""
Generate one PDF "company brief" per company from a Pro Innovator companies CSV.

This complements the existing downloader (`resi/download_from_index.py`) which creates:
  OUTPUT_DIR/<Sector>/<Company>/

We write:
  OUTPUT_DIR/<Sector>/<Company>/<Company>.pdf

Designed for the offline Pro Innovator extractor outputs:
  - apac_companies.csv
  - mti_companies.csv

If fpdf2 isn't installed, the script will attempt to install it.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import textwrap
from pathlib import Path


def _ensure_fpdf():
    try:
        from fpdf import FPDF  # type: ignore

        return FPDF
    except Exception:
        import subprocess

        print("Installing fpdf2...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "fpdf2"])
        from fpdf import FPDF  # type: ignore

        return FPDF


def _safe(s: str) -> str:
    # Normalize whitespace aggressively; fpdf can choke on very long unbroken tokens.
    s = (s or "").replace("\r", " ").replace("\n", " ").strip()
    s = " ".join(s.split())
    return s


def _pdf_safe(s: str) -> str:
    """
    Ensure text is renderable with core PDF fonts (Latin-1-ish).
    Replace unsupported unicode with '?' to avoid FPDF line breaking exceptions.
    """
    s = _safe(s)
    try:
        return s.encode("latin-1", "replace").decode("latin-1")
    except Exception:
        return "".join((ch if ord(ch) < 256 else "?") for ch in s)


def _is_internal_grid_key(key: str) -> bool:
    return key.startswith("Grid: ")


def _pick_sector(row: dict, fallback: str) -> str:
    v = (row.get("Sector") or row.get("sector") or "").strip()
    return v or fallback


def _company_folder(output_dir: Path, sector: str, company_name: str) -> Path:
    # Use the same sanitization logic as download_from_index so paths match.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from download_from_index import sanitize_filename, sanitize_foldername  # noqa

    sector_dir = output_dir / sanitize_foldername(sector)
    return sector_dir / sanitize_filename(company_name)


def _company_brief_pdf_path(folder: Path, company_name: str) -> Path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from download_from_index import sanitize_filename  # noqa

    # Use a suffix so we don't collide with downloaded media PDFs.
    safe = sanitize_filename(company_name, max_length=140)
    return folder / f"{safe}_brief.pdf"


def _write_company_pdf(out_path: Path, company_name: str, items: list[tuple[str, str]]) -> None:
    FPDF = _ensure_fpdf()
    pdf = FPDF(unit="pt", format="letter")
    pdf.set_auto_page_break(auto=True, margin=36)
    pdf.add_page()
    width = pdf.w - pdf.l_margin - pdf.r_margin

    pdf.set_font("Helvetica", "B", 18)
    pdf.multi_cell(width, 22, _pdf_safe(company_name))
    pdf.ln(6)

    pdf.set_font("Helvetica", "", 11)
    for k, v in items:
        if not v:
            continue
        # fpdf can fail when a single "word" can't be broken; hard-wrap at character count.
        v = _pdf_safe(v)
        v = "\n".join(
            textwrap.wrap(
                v,
                width=95,
                break_long_words=True,
                break_on_hyphens=False,
                replace_whitespace=False,
                drop_whitespace=False,
            )
        )
        # Key
        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(width, 14, _pdf_safe(f"{k}:"))
        # Value (wrap)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(width, 14, v)
        pdf.ln(6)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_path))


def run(companies_csv: Path, output_dir: Path, sector: str, include_grid: bool = True) -> int:
    with companies_csv.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    count = 0
    for row in rows:
        company = _safe(row.get("Company Name") or "")
        if not company:
            continue

        company_sector = _pick_sector(row, sector)
        folder = _company_folder(output_dir, company_sector, company)
        folder.mkdir(parents=True, exist_ok=True)

        # Build ordered items: prefer human labels, then URLs, then remaining fields.
        keys = list(row.keys())

        preferred = [
            "Company Name",
            "One-liner",
            "One-Line Description",
            "Short Description",
            "Product Name",
            "Product Description",
            "Product abstract",
            "Product Abstract",
            "Development Stage",
            "Product development stage",
            "Product Development Stage",
            "Website",
            "Website URL",
            "Country",
            "Detail Country",
            "State",
            "City",
            "Year Founded",
            "What year was your organization founded?",
        ]

        seen = set()
        ordered: list[str] = []
        for k in preferred:
            if k in row and k not in seen:
                ordered.append(k)
                seen.add(k)

        # Add all "* URL" fields (media links) next.
        for k in keys:
            if k.endswith(" URL") and k not in seen:
                ordered.append(k)
                seen.add(k)

        # Add everything else.
        for k in keys:
            if k in seen:
                continue
            if not include_grid and _is_internal_grid_key(k):
                continue
            ordered.append(k)
            seen.add(k)

        items: list[tuple[str, str]] = []
        for k in ordered:
            if k == "Company Name":
                continue
            v = _safe(row.get(k) or "")
            if v:
                items.append((k, v))

        pdf_path = _company_brief_pdf_path(folder, company)
        _write_company_pdf(pdf_path, company, items)
        count += 1

    return count


def main() -> None:
    ap = argparse.ArgumentParser(description="Write per-company PDF briefs from a Pro Innovator companies CSV.")
    ap.add_argument("--companies-csv", required=True, type=Path, help="Path to *_companies.csv")
    ap.add_argument("--output-dir", "-o", required=True, type=Path, help="Output dir used by downloader")
    ap.add_argument("--sector", required=True, help="Sector label used for folder grouping (e.g. APAC, MTI)")
    ap.add_argument(
        "--no-grid",
        action="store_true",
        help="Exclude internal 'Grid: <col-id>' fields from PDFs",
    )
    args = ap.parse_args()

    n = run(
        companies_csv=args.companies_csv.expanduser().resolve(),
        output_dir=args.output_dir.expanduser().resolve(),
        sector=args.sector,
        include_grid=not args.no_grid,
    )
    print(f"Wrote {n} PDF(s).")


if __name__ == "__main__":
    main()


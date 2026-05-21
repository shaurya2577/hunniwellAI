#!/usr/bin/env python3
"""
Offline pipeline for saved Pro Innovator Applications HTML snapshots (AG Grid pages).

Given one or more saved "Innovator Portal.html" snapshots (Save As → Webpage, HTML Only or Complete),
this will:
- Extract ALL label/value pairs from the expanded detail panels ("company dropdown"/detail view)
  plus any grid-visible columns.
- Write a full-fidelity companies CSV.
- Write a media index CSV compatible with resi/download_from_index.py (one row per link).
- Emit a macOS-friendly download script to fetch media into per-company folders.

This is designed to keep APAC and MTI outputs distinct.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
from pathlib import Path
from typing import Iterable

from scrapers.pro_innovator.innovator_portal_reader import (
    parse_saved_pro_innovator_html,
    write_companies_to_csv,
)


MEDIA_LABEL_RE = re.compile(
    r"(deck|slide|presentation|pitch|recording|video|youtube|photo|document|supporting|file)",
    re.IGNORECASE,
)

DOWNLOADABLE_URL_RE = re.compile(
    r"(file-viewer\?url=|media\.innovator\.org/|mti-innovator\.s3|officeapps\.live\.com/|youtu\.be/|youtube\.com/|wistia\.com/medias/|vimeo\.com/|dropbox\.com/.*\.mp4)",
    re.IGNORECASE,
)


def _program_from_path(path: Path) -> str:
    s = str(path).lower()
    if "/apac/" in s:
        return "apac"
    if "/mti/" in s:
        return "mti"
    # fallback: parent folder name
    return (path.parent.name or "output").lower()


def _iter_media_links(company: dict) -> Iterable[tuple[str, str]]:
    """
    Yield (label, url) pairs from:
    - fields ending in ' URL' that look like media, and
    - any detected Innovator file-viewer/media links embedded in values.

    Only yields URLs that look downloadable (to avoid saving HTML pages as .pdf).
    """
    # 1) Structured "* URL" fields extracted from anchors in the detail panels.
    for k, v in company.items():
        if not k.endswith(" URL"):
            continue
        label = k[: -len(" URL")].strip() or "Link"
        raw = (v or "").strip()
        if not raw:
            continue
        # Values can be "url1 | url2" when multiple anchors were present.
        for part in raw.split(" | "):
            url = part.strip()
            if not url:
                continue
            if url == "-":
                continue
            if not (url.startswith("http://") or url.startswith("https://")):
                continue
            if not DOWNLOADABLE_URL_RE.search(url):
                continue
            if url:
                yield (label, url)

    # 2) Unstructured: some saved pages include file-viewer links in plain text blobs.
    # Scan all values for file-viewer links and emit them as "Slide Deck" items.
    for k, v in company.items():
        raw = (v or "")
        if not raw:
            continue
        for m in re.finditer(r"https?://[^\\s\"<>]+", raw):
            url = m.group(0).strip()
            if not url:
                continue
            if not DOWNLOADABLE_URL_RE.search(url):
                continue
            if url.endswith("file-viewer?url=http"):
                continue
            label = "Slide Deck" if "file-viewer" in url or "media.innovator.org" in url else "Media"
            yield (label, url)


def write_media_index(companies: list[dict], output_path: Path, sector: str) -> int:
    """
    Create an index CSV compatible with download_from_index.py.
    """
    rows: list[dict] = []
    for company in companies:
        name = (company.get("Company Name") or "").strip()
        if not name:
            continue
        for label, url in _iter_media_links(company):
            rows.append(
                {
                    "Company Name": name,
                    "Sector": sector,
                    "Link Label": label,
                    "PDF URL": url,
                }
            )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["Company Name", "Sector", "Link Label", "PDF URL"],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def write_download_command(output_dir: Path, index_csv: Path) -> Path:
    """
    Emit a double-clickable .command file (macOS) that runs download_from_index.py.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    command_path = output_dir / "download_media.command"
    repo_root = Path(__file__).resolve().parents[1]
    command_path.write_text(
        "\n".join(
            [
                "#!/bin/zsh",
                "set -euo pipefail",
                "",
                "# Run from repo root so imports work",
                f"cd {repo_root.as_posix()}",
                "",
                f"python resi/download_from_index.py {index_csv.as_posix()} --output-dir {output_dir.as_posix()}",
                "",
                "echo \"\"",
                "echo \"Done. Output is organized by Sector/Company under:\"",
                f"echo \"  {output_dir.as_posix()}\"",
                "read -r \"?Press Enter to close...\"",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    os.chmod(command_path, 0o755)
    return command_path


def run_one(html_path: Path, base_output_dir: Path, program: str | None = None) -> dict:
    program = (program or _program_from_path(html_path)).lower()
    program_dir = base_output_dir / program
    program_dir.mkdir(parents=True, exist_ok=True)

    companies = parse_saved_pro_innovator_html(str(html_path))
    companies_csv = program_dir / f"{program}_companies.csv"
    write_companies_to_csv(companies, str(companies_csv))

    media_index = program_dir / f"{program}_media_index.csv"
    n_links = write_media_index(companies, media_index, sector=program.upper())

    command_path = write_download_command(program_dir, media_index)
    return {
        "program": program,
        "companies_csv": str(companies_csv),
        "media_index_csv": str(media_index),
        "download_command": str(command_path),
        "companies": len(companies),
        "links": n_links,
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Offline extractor for saved Pro Innovator Applications HTML -> full companies CSV + media index.",
    )
    ap.add_argument(
        "--html",
        nargs="+",
        required=True,
        help="Path(s) to saved Applications HTML snapshots (e.g. .../APAC/Innovator Portal.html).",
    )
    ap.add_argument(
        "--output-dir",
        "-o",
        required=True,
        type=Path,
        help="Base output directory (will create ./apac and ./mti subfolders).",
    )
    ap.add_argument(
        "--program",
        choices=["apac", "mti"],
        default=None,
        help="Override program bucket for ALL inputs (otherwise inferred from path).",
    )
    args = ap.parse_args()

    out = args.output_dir.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    for p in args.html:
        html_path = Path(p).expanduser().resolve()
        if not html_path.exists():
            raise SystemExit(f"HTML file not found: {html_path}")
        result = run_one(html_path, out, program=args.program)
        print(
            f"{result['program']}: {result['companies']} companies, {result['links']} media link(s)\n"
            f"  companies CSV: {result['companies_csv']}\n"
            f"  media index:   {result['media_index_csv']}\n"
            f"  download cmd:  {result['download_command']}"
        )


if __name__ == "__main__":
    main()


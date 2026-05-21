#!/usr/bin/env python3
"""Organize Jujama companies into per-company folders with profile docs and media."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DEFAULT_INPUT = Path.home() / "Downloads" / "Jujama" / "jujama_companies" / "jujama_companies.csv"
DEFAULT_OUTPUT = Path.home() / "Downloads" / "LSI4082026"
MEDIA_EXTENSIONS = (
    ".pdf",
    ".ppt",
    ".pptx",
    ".mp4",
    ".mov",
    ".m4v",
    ".avi",
    ".wmv",
    ".webm",
)
URL_RE = re.compile(r"https?://[^\s<>()\"']+")
INVALID_NAME_CHARS = re.compile(r'[#%&*:<>?"/\\|]')
DOWNLOAD_TIMEOUT_S = 20
MAX_WORKERS = 12


def sanitize_name(value: str, fallback: str = "Unknown", max_length: int = 140) -> str:
    text = (value or "").strip()
    text = INVALID_NAME_CHARS.sub("_", text)
    text = re.sub(r"\s+", " ", text).strip().strip(".")
    if not text:
        text = fallback
    return text[:max_length]


def normalize_url(url: str) -> str:
    value = (url or "").strip()
    return value.replace(" ", "%20")


def filename_from_url(url: str, fallback_stem: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name
    if not name:
        return f"{fallback_stem}.bin"
    return sanitize_name(name, fallback=f"{fallback_stem}.bin")


def is_probable_media_url(url: str) -> bool:
    lower = (url or "").lower()
    return any(ext in lower for ext in MEDIA_EXTENSIONS)


def download_file(url: str, out_path: Path) -> bool:
    req = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) jujama-organizer/1.0"},
    )
    try:
        with urlopen(req, timeout=DOWNLOAD_TIMEOUT_S) as resp:
            if resp.status != 200:
                return False
            data = resp.read()
    except Exception:
        return False
    if not data:
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    return True


def parse_json_field(raw: str):
    try:
        return json.loads(raw)
    except Exception:
        return raw


def extract_candidate_urls(row: dict) -> list[str]:
    urls: list[str] = []
    direct_columns = [
        "Detail URL",
        "Website URL",
        "LinkedIn URL",
        "Twitter/X URL",
        "Facebook URL",
    ]
    for col in direct_columns:
        val = (row.get(col) or "").strip()
        if val:
            urls.append(val)

    other_socials = parse_json_field(row.get("Other Social URLs JSON") or "[]")
    if isinstance(other_socials, list):
        urls.extend(str(v).strip() for v in other_socials if str(v).strip())

    attendees = parse_json_field(row.get("Attendees JSON") or "[]")
    if isinstance(attendees, list):
        for attendee in attendees:
            if not isinstance(attendee, dict):
                continue
            for key in ("attendee_url",):
                val = str(attendee.get(key) or "").strip()
                if val:
                    urls.append(val)

    about = row.get("About") or ""
    urls.extend(match.rstrip(".,);]") for match in URL_RE.findall(about))

    deduped: list[str] = []
    seen = set()
    for item in urls:
        value = normalize_url(item)
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def write_company_doc(company_dir: Path, row: dict) -> None:
    company_name = row.get("Company Name") or "Unknown Company"
    lines = [
        f"# {company_name}",
        "",
        "## Core Profile",
    ]
    ordered_fields = [
        "Company ID",
        "Detail URL",
        "Profile Image URL",
        "Location",
        "Website URL",
        "LinkedIn URL",
        "Twitter/X URL",
        "Facebook URL",
        "Exported At",
    ]
    for field in ordered_fields:
        value = (row.get(field) or "").strip()
        lines.append(f"- **{field}:** {value}")

    lines.extend(["", "## About", row.get("About") or "", "", "## Other Social URLs JSON"])
    other_socials = parse_json_field(row.get("Other Social URLs JSON") or "[]")
    lines.append("```json")
    lines.append(json.dumps(other_socials, ensure_ascii=True, indent=2))
    lines.append("```")

    lines.extend(["", "## Attendees JSON"])
    attendees = parse_json_field(row.get("Attendees JSON") or "[]")
    lines.append("```json")
    lines.append(json.dumps(attendees, ensure_ascii=True, indent=2))
    lines.append("```")
    (company_dir / "company_info.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(input_csv: Path, output_dir: Path, no_download: bool = False) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    root_csv = output_dir / "jujama_companies.csv"
    shutil.copy2(input_csv, root_csv)
    logging.info("Copied CSV to %s", root_csv)

    with input_csv.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    downloaded = 0
    failed = 0
    skipped = 0
    download_jobs: list[tuple[str, Path]] = []
    folder_name_counts: dict[str, int] = {}
    for row in rows:
        company = sanitize_name(row.get("Company Name") or "", fallback="Unknown Company")
        key = company.lower()
        folder_name_counts[key] = folder_name_counts.get(key, 0) + 1
        if folder_name_counts[key] == 1:
            company_folder = company
        else:
            company_id = sanitize_name(row.get("Company ID") or "", fallback=str(folder_name_counts[key]), max_length=40)
            company_folder = f"{company}__{company_id}"
        company_dir = output_dir / company_folder
        company_dir.mkdir(parents=True, exist_ok=True)
        write_company_doc(company_dir, row)

        if no_download:
            continue

        media_dir = company_dir / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        urls = extract_candidate_urls(row)
        for idx, url in enumerate(urls, start=1):
            if not is_probable_media_url(url):
                skipped += 1
                continue
            name = filename_from_url(url, fallback_stem=f"asset_{idx}")
            target = media_dir / name
            if target.exists() and target.stat().st_size > 0:
                continue
            download_jobs.append((url, target))

    if not no_download and download_jobs:
        logging.info("Starting downloads: %d candidate media files", len(download_jobs))
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(download_file, url, target): (url, target) for url, target in download_jobs}
            for future in as_completed(futures):
                if future.result():
                    downloaded += 1
                else:
                    failed += 1

    logging.info(
        "Done. Companies=%d, downloaded=%d, failed=%d, non-media-skipped=%d",
        len(rows),
        downloaded,
        failed,
        skipped,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create per-company folders from Jujama CSV with company doc + downloadable media."
    )
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT, help="Path to jujama_companies.csv")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT, help="Root output folder")
    parser.add_argument("--no-download", action="store_true", help="Only write docs/folders and copy CSV")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    run(args.input_csv.expanduser().resolve(), args.output_dir.expanduser().resolve(), no_download=args.no_download)


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Download PDFs, videos, and other media listed in an index CSV into local storage, organized by sector and company.

Works with any CSV based on column titles:
  - RESI/index format: Company Name, Sector, Link Label, PDF URL (one row per link)
  - Open Rounds format: Company Name, Pitch Deck Download URL, Video URL (one row per company)

Structure:
  OUTPUT_DIR/
    [Sector1]/                          # e.g. Biotechnology - Therapeutics and Diagnostics
      !!![Sector1]_index.csv             # sector index at top (same columns as original CSV)
      [CompanyA]/                        # one subfolder per company
        CompanyA_SLIDEDECK.pdf
        CompanyA_LinkLabel.pdf
      [CompanyB]/
        ...
    [Sector2]/
      ...

Sectors are taken from the CSV (no hardcoding). Rows with no Sector go into "Other".
If PDF URL is empty, the company folder is still created but no file is downloaded.
Set INDEX_OUTPUT_DIR and INDEX_BASE_URL (or use --output-dir and --base-url) for generic use.
For RESI, use the same output dir as the RESI run (e.g. ~/Downloads/RESI).

Usage:
  python download_from_index.py [index.csv] [--output-dir DIR] [--base-url URL]
  python download_from_index.py   # uses newest index_*.csv in OUTPUT_DIR
"""
import argparse
import csv
import logging
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import unquote, urljoin, urlparse, parse_qs
from urllib.request import Request, urlopen

# Generic config: env or defaults (no platform-specific import)
def _default_output_dir():
    if os.environ.get("INDEX_OUTPUT_DIR"):
        return os.environ["INDEX_OUTPUT_DIR"]
    return os.path.join(os.path.expanduser("~"), "Downloads", "IndexDownloads")


def _default_base_url():
    return os.environ.get("INDEX_BASE_URL", "").strip()

# Sector index filename prefix so it sorts first in directory listings
SECTOR_INDEX_PREFIX = "!!!"
SECTOR_INDEX_SUFFIX = "_index.csv"

# Download timeout (seconds); large PDFs/movies may need longer
DOWNLOAD_TIMEOUT = 120

SLIDEDECK_SUFFIX = "_SLIDEDECK.pdf"


# Characters invalid in file/folder names on Windows and common filesystems
_INVALID_NAME_CHARS = r'[#%&*:<>?"/\\|]'


def sanitize_filename(name: str, max_length: int = 200) -> str:
    """Sanitize company name or label for use in filenames. Removes invalid chars and trailing period/space."""
    s = (name or "").strip()
    s = re.sub(_INVALID_NAME_CHARS, "_", s)
    s = re.sub(r"\s+", " ", s).strip().strip(".")
    return s[:max_length] if len(s) > max_length else s or "Unknown"


def sanitize_foldername(sector: str, max_length: int = 80) -> str:
    """Sanitize sector (or similar) for use as a folder name. Removes invalid chars and trailing period/space."""
    s = (sector or "").strip()
    if not s:
        return "Other"
    s = re.sub(_INVALID_NAME_CHARS, "_", s)
    s = re.sub(r"\s+", " ", s).strip().strip(".")
    return s[:max_length] if len(s) > max_length else s or "Other"


def extension_for_media(link_label: str, url: str) -> str:
    """Infer file extension for this media."""
    label = (link_label or "").strip().lower()
    u = (url or "").lower()
    # Images: pitch decks sometimes arrive as JPG/PNG
    if re.search(r"\.png($|\?)", u):
        return ".png"
    if re.search(r"\.jpe?g($|\?)", u):
        return ".jpg"
    if ".webp" in u:
        return ".webp"
    # Office files
    if ".pptx" in u:
        return ".pptx"
    if re.search(r"(^|[?&])format=pptx($|&)", u):
        return ".pptx"
    if re.search(r"\.ppt($|[?#])", u):
        return ".ppt"
    if ".pdf" in u:
        return ".pdf"

    if "youtube.com" in u or "youtu.be" in u:
        return ".mp4"
    if "vimeo.com" in u or "loom.com" in u:
        return ".mp4"
    if "movie file" in label or "movie" in label:
        return ".mp4"
    if "recording" in label:
        return ".mp4"
    if ".mp4" in u or ".mov" in u or "video" in u:
        return ".mp4"

    # If the label says it's a video, prefer mp4 even when the URL isn't explicit.
    if "video" in label or "recording" in label:
        return ".mp4"
    return ".pdf"


def get_media_path(
    company_name: str,
    parent_dir: str,
    link_label: Optional[str] = None,
    extension: str = ".pdf",
) -> str:
    """Path for CompanyName_LinkLabel.ext under parent_dir (company folder).
    If file exists, use _2, _3, etc. extension is e.g. .pdf or .mp4."""
    base = sanitize_filename(company_name)
    ext = extension if extension.startswith(".") else "." + extension
    if link_label and link_label.strip():
        raw = sanitize_filename(link_label.strip(), max_length=60)
        # Strip extension from label to avoid "deck.pdf.pdf"
        for e in (".pdf", ".mp4", ".png", ".pptx", ".ppt"):
            if raw.lower().endswith(e):
                raw = raw[: -len(e)]
                break
        stem = base + "_" + raw
    else:
        stem = base + SLIDEDECK_SUFFIX.replace(".pdf", "")
    path = os.path.join(parent_dir, stem + ext)
    if not os.path.isfile(path):
        return path
    i = 2
    while True:
        path = os.path.join(parent_dir, f"{stem}_{i}{ext}")
        if not os.path.isfile(path):
            return path
        i += 1


def resolve_url(url: str, base_url: str) -> str:
    """If URL is relative and base_url is set, prepend base_url."""
    u = (url or "").strip()
    if not u:
        return u
    # Some exports include bare domains/paths like "example.com/foo" (no scheme)
    if re.match(r"^[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/|$)", u) and not u.startswith(("http://", "https://")):
        return "https://" + u
    if u.startswith(("http://", "https://")):
        # Innovator file viewer wrapper: unwrap to the real signed media URL.
        try:
            parsed = urlparse(u)
            if "file-viewer" in parsed.path:
                url_param = parse_qs(parsed.query).get("url", [""])[0]
                if url_param:
                    real = unquote(url_param).strip()
                    return real.replace(" ", "%20")
        except Exception:
            pass
        # Office viewer wrapper: prefer downloading the underlying src URL directly.
        # This avoids 404s on view.officeapps.live.com and preserves the signed S3 URL.
        try:
            parsed = urlparse(u)
            if parsed.netloc.endswith("view.officeapps.live.com") and parsed.path.endswith("/op/view.aspx"):
                # NOTE: do NOT percent-decode the src value (it may contain signed URLs).
                # We want the raw, percent-encoded URL so it remains fetchable.
                m = re.search(r"(?:^|[?&])src=([^&]+)", parsed.query)
                if m:
                    src_raw = m.group(1).strip()
                    if src_raw:
                        # src is already percent-encoded; just decode HTML entities if any.
                        src_raw = src_raw.replace("&amp;", "&")
                        # But if we extracted src from the viewer wrapper, it is a *percent-encoded URL*.
                        # Decode it once so urllib can fetch it (spaces must remain percent-encoded).
                        return unquote(src_raw)
        except Exception:
            pass
        return u
    # Common in exports: "www.example.com/..." without a scheme
    if u.startswith("www."):
        return "https://" + u
    if not base_url:
        return u
    return urljoin(base_url.rstrip("/") + "/", u.lstrip("/"))


def download_youtube(url: str, save_path: str, timeout: int = DOWNLOAD_TIMEOUT) -> bool:
    """
    Download YouTube/video URL using yt-dlp. Returns True on success.
    Requires yt-dlp: pip install yt-dlp or brew install yt-dlp
    """
    # Prefer running yt-dlp in the current interpreter environment (works well inside venv),
    # to avoid global python/ssl mismatches.
    ytdlp_cmd = [sys.executable, "-m", "yt_dlp"]
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    # yt-dlp -o "path.%(ext)s" lets it pick extension (mp4, webm, etc.)
    stem = save_path.rsplit(".", 1)[0] if "." in save_path and not save_path.endswith(".") else save_path
    out_tmpl = stem + ".%(ext)s"
    try:
        base_args = [
            *ytdlp_cmd,
            "-o",
            out_tmpl,
            "--no-playlist",
            "--quiet",
            "--no-warnings",
            "-f",
            "bv*+ba/b",
            url,
        ]
        result = subprocess.run(
            base_args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            msg = (result.stderr or result.stdout or "")
            # Retry with cookies from Brave for YouTube bot/sign-in prompts.
            if (
                ("sign in to confirm" in msg.lower())
                or ("not a bot" in msg.lower())
                or ("use --cookies" in msg.lower())
                or ("this helps protect our community" in msg.lower())
            ):
                retry_args = [
                    *ytdlp_cmd,
                    "--cookies-from-browser",
                    "brave",
                    "-o",
                    out_tmpl,
                    "--no-playlist",
                    "--quiet",
                    "--no-warnings",
                    "-f",
                    "bv*+ba/b",
                    url,
                ]
                retry = subprocess.run(
                    retry_args,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                if retry.returncode == 0:
                    result = retry
                else:
                    msg = (retry.stderr or retry.stdout or msg)
                    logging.warning("yt-dlp failed for %s: %s", url[:60], msg[:200])
                    return False
            else:
                logging.warning("yt-dlp failed for %s: %s", url[:60], msg[:200])
                return False
        # Find the file yt-dlp created (stem.mp4, stem.webm, etc.)
        for ext in (".mp4", ".webm", ".mkv", ".m4a"):
            candidate = stem + ext
            if os.path.isfile(candidate) and os.path.getsize(candidate) > 0:
                if candidate != save_path:
                    try:
                        os.rename(candidate, save_path)
                    except OSError:
                        pass  # keep as candidate
                return True
        return os.path.isfile(save_path) and os.path.getsize(save_path) > 0
    except subprocess.TimeoutExpired:
        logging.warning("yt-dlp timeout for %s", url[:60])
        return False
    except Exception as e:
        logging.warning("yt-dlp error for %s: %s", url[:60], e)
        return False


def download_media(media_url: str, save_path: str, timeout: int = DOWNLOAD_TIMEOUT) -> bool:
    """
    Fetch file from media_url (PDF or movie) and write to save_path.
    Uses timeout to avoid hanging on errors. Returns True on success, False on failure (logs reason).
    """
    req = Request(
        media_url,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) RESI-download/1.0"},
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                logging.warning("GET %s -> %s", media_url[:80], resp.status)
                return False
            content_type = (resp.headers.get("Content-Type") or "").lower()
            body = resp.read()
    except TimeoutError as e:
        logging.warning("Timeout fetching %s: %s", media_url[:80], e)
        return False
    except OSError as e:
        logging.warning("Failed to fetch %s: %s", media_url[:80], e)
        return False
    except Exception as e:
        logging.warning("Failed to fetch %s: %s", media_url[:80], e)
        return False

    # Guard: don't write HTML error pages / disguised responses.
    sniff = body[:256].lstrip()
    ext = Path(save_path).suffix.lower()
    if (
        "text/html" in (content_type or "")
        or sniff.lower().startswith(b"<!doctype html")
        or sniff.lower().startswith(b"<html")
    ):
        logging.warning("Skipping HTML response for %s", media_url[:80])
        return False

    # Guard: don't save non-PDF as .pdf.
    if ext == ".pdf":
        if not body.startswith(b"%PDF"):
            logging.warning("Skipping non-PDF content for %s (got head %r)", media_url[:80], body[:16])
            return False

    # Guard: don't save non-MP4 as .mp4.
    if ext == ".mp4":
        # MP4 boxes: 'ftyp' should appear near the beginning (offset 4)
        head = body[:16]
        if not (len(head) >= 8 and head[4:8] == b"ftyp"):
            if head.startswith(b"<"):
                logging.warning("Skipping HTML response for %s", media_url[:80])
            else:
                logging.warning("Skipping non-MP4 content for %s (got head %r)", media_url[:80], head)
            return False

    try:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(body)
    except OSError as e:
        logging.warning("Failed to write %s: %s", save_path, e)
        return False

    if os.path.getsize(save_path) == 0:
        logging.warning("Wrote empty file for %s", save_path)
        return False
    return True


def _convert_office_to_pdf(input_path: str) -> bool:
    """
    Convert an Office file (ppt/pptx/docx) to PDF using LibreOffice, writing PDF next to input.
    Returns True if a PDF was produced.
    """
    # Import locally to avoid rare NameError in some execution contexts
    from pathlib import Path as _Path

    in_path = _Path(input_path)
    if not in_path.exists():
        return False
    out_dir = in_path.parent
    pdf_path = out_dir / (in_path.stem + ".pdf")
    # Prefer PATH
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        # Common macOS app bundle
        mac = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
        if mac.exists():
            soffice = str(mac)
    if not soffice:
        return False
    try:
        subprocess.run(
            [
                soffice,
                "--headless",
                "--nologo",
                "--nodefault",
                "--nolockcheck",
                "--norestore",
                "--convert-to",
                "pdf",
                "--outdir",
                str(out_dir),
                str(in_path),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception:
        return False
    return pdf_path.exists() and pdf_path.stat().st_size > 0


def _convert_image_to_pdf(image_path: str, pdf_path: str) -> bool:
    """
    Convert an image to PDF using Pillow.
    Returns True if pdf_path was created.
    """
    try:
        from PIL import Image
    except ImportError:
        return False

    in_path = Path(image_path)
    out_path = Path(pdf_path)
    if not in_path.exists():
        return False

    try:
        img = Image.open(in_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Single-page PDF conversion
        img.save(str(out_path), "PDF")
        return out_path.exists() and out_path.stat().st_size > 0
    except Exception:
        return False


def sanitize_file_basename(basename: str) -> str:
    """Sanitize a file basename (stem + extension). Preserves extension; sanitizes stem."""
    if not basename or basename.endswith("."):
        return basename
    idx = basename.rfind(".")
    if idx <= 0:
        return sanitize_filename(basename)
    stem, ext = basename[:idx], basename[idx:]
    safe_stem = sanitize_filename(stem)
    return safe_stem + ext


def fix_existing_output_names(output_dir: str) -> tuple[int, int]:
    """
    Walk output_dir bottom-up and rename any file or folder whose name contains
    invalid characters (or trailing period/space) to a sanitized name.
    Returns (files_renamed, dirs_renamed).
    """
    out_dir = os.path.abspath(output_dir)
    if not os.path.isdir(out_dir):
        logging.warning("Output directory does not exist: %s", out_dir)
        return 0, 0
    files_renamed = 0
    dirs_renamed = 0
    for dirpath, dirnames, filenames in os.walk(out_dir, topdown=False):
        for name in filenames:
            if name.startswith("."):
                continue  # skip hidden files (e.g. .DS_Store)
            safe = sanitize_file_basename(name)
            if safe != name:
                old_path = os.path.join(dirpath, name)
                new_path = os.path.join(dirpath, safe)
                try:
                    os.rename(old_path, new_path)
                    logging.info("Renamed file: %s -> %s", name, safe)
                    files_renamed += 1
                except OSError as e:
                    logging.warning("Could not rename %s to %s: %s", old_path, new_path, e)
        for name in dirnames:
            safe = sanitize_foldername(name)
            if safe != name:
                old_path = os.path.join(dirpath, name)
                new_path = os.path.join(dirpath, safe)
                try:
                    os.rename(old_path, new_path)
                    logging.info("Renamed folder: %s -> %s", name, safe)
                    dirs_renamed += 1
                except OSError as e:
                    logging.warning("Could not rename %s to %s: %s", old_path, new_path, e)
    return files_renamed, dirs_renamed


def newest_index_path(output_dir: str) -> Optional[str]:
    """Return path to newest index_*.csv or open_rounds_*.csv in output_dir, or None."""
    if not os.path.isdir(output_dir):
        return None
    candidates = [
        os.path.join(output_dir, f)
        for f in os.listdir(output_dir)
        if f.endswith(".csv") and (f.startswith("index_") or f.startswith("open_rounds_"))
    ]
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)


def _sector_index_filename(sector: str) -> str:
    """Filename for sector index CSV (!!! at start so it sorts first)."""
    safe = sanitize_foldername(sector)
    return f"{SECTOR_INDEX_PREFIX}{safe}{SECTOR_INDEX_SUFFIX}"


def _collect_download_items(row: dict, fieldnames: List[str]) -> List[Tuple[str, str, str]]:
    """
    Collect (link_label, url, extension) from a row based on available columns.
    Supports: PDF URL, Link Label (index format); Pitch Deck Download URL, Video URL (open_rounds format).
    """
    items: List[Tuple[str, str, str]] = []
    fn = {h.strip(): h for h in fieldnames}

    # Index format: PDF URL + Link Label
    pdf_col = fn.get("PDF URL") or fn.get("Pitch Deck Download URL")
    if pdf_col:
        url = (row.get(pdf_col) or "").strip()
        if url:
            label_col = fn.get("Link Label") or fn.get("Pitch Deck Filename")
            label = (row.get(label_col) or "Pitch Deck").strip() if label_col else "Pitch Deck"
            ext = extension_for_media(label, url)
            items.append((label, url, ext))

    # Open Rounds: Pitch Deck Download URL already handled above. Video URL is separate.
    video_col = fn.get("Video URL")
    if video_col:
        video_val = (row.get(video_col) or "").strip()
        for part in video_val.split(";"):
            part = part.strip()
            if not part:
                continue
            if "youtube.com" in part or "youtu.be" in part:
                items.append(("Product Video", part, ".mp4"))  # yt-dlp can fetch as mp4
            else:
                items.append(("Video", part, ".mp4"))

    return items


def run(
    index_path: str,
    output_dir: str,
    base_url: str = "",
    skip_existing: bool = True,
    flat: bool = False,
) -> None:
    """
    Read CSV, group by sector (or use "Other" if no Sector column), then by company.
    Detect columns: Company Name, Sector, PDF URL / Pitch Deck Download URL, Link Label,
    Video URL. Download each media URL into company folders.
    """
    if not os.path.isfile(index_path):
        logging.error("Index file not found: %s", index_path)
        return

    out_dir = os.path.abspath(output_dir)
    os.makedirs(out_dir, exist_ok=True)
    logging.info("Output directory: %s", out_dir)

    with open(index_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        raw_headers = list(reader.fieldnames or [])
        raw_rows = list(reader)

    if not raw_headers:
        logging.error("Index CSV has no headers.")
        return

    # Normalize headers (strip BOM/stray chars); fix "xCompany Name" etc.
    def _norm(h: str) -> str:
        s = str(h or "").strip().lstrip("\ufeff")
        if "Company Name" in s and s != "Company Name":
            return "Company Name"  # e.g. "xCompany Name" from corruption
        return s

    fieldnames = [_norm(h) for h in raw_headers]
    rows = []
    for r in raw_rows:
        rows.append({fieldnames[i]: r.get(raw_headers[i], "") for i in range(len(raw_headers)) if i < len(fieldnames)})
    is_open_rounds = "Pitch Deck Download URL" in fieldnames or "Company ID" in fieldnames

    def _sector(row: dict) -> str:
        for k in ("Sector", "sector"):
            if k in row and (row.get(k) or "").strip():
                return (row.get(k) or "").strip()
        if is_open_rounds:
            # Derive sector from Product Development Stage > Regulatory Pathway > Round
            for col in ("Product Development Stage", "Regulatory Pathway", "Round"):
                if col in row:
                    v = (row.get(col) or "").strip()
                    if v:
                        return v
        return "Open Rounds" if is_open_rounds else "Other"

    def _subsector(row: dict) -> str:
        for k in ("Subsectors", "Subsector", "subsectors", "subsector"):
            if k in row and (row.get(k) or "").strip():
                return (row.get(k) or "").strip()
        if is_open_rounds:
            # Use Regulatory Pathway or Round as subsector when different from sector
            sector = _sector(row)
            for col in ("Regulatory Pathway", "Round"):
                if col in row:
                    v = (row.get(col) or "").strip()
                    if v and v != sector:
                        return v
        return ""

    # Ensure Sector and Subsectors columns exist for index (RESI-style)
    if "Sector" not in fieldnames:
        fieldnames = ["Sector"] + list(fieldnames)
    if "Subsectors" not in fieldnames and "Subsector" not in fieldnames:
        idx = fieldnames.index("Sector") + 1
        fieldnames = fieldnames[:idx] + ["Subsectors"] + fieldnames[idx:]

    # Populate Sector and Subsectors in each row for index CSV (RESI-style)
    for row in rows:
        row["Sector"] = _sector(row) or "Other"
        row["Subsectors"] = _subsector(row)

    by_sector: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        company = (row.get("Company Name") or "").strip()
        if not company:
            continue
        sector_key = row.get("Sector") or "Other"
        by_sector[sector_key].append(row)

    done = 0
    skipped_no_url = 0
    skipped_exists = 0
    failed = 0

    for sector in sorted(by_sector.keys()):
        sector_rows = by_sector[sector]

        if flat:
            sector_path = out_dir
        else:
            sector_folder_name = sanitize_foldername(sector)
            sector_path = os.path.join(out_dir, sector_folder_name)
            os.makedirs(sector_path, exist_ok=True)

            sector_index_path = os.path.join(sector_path, _sector_index_filename(sector))
            with open(sector_index_path, "w", newline="", encoding="utf-8") as sf:
                writer = csv.DictWriter(sf, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(sector_rows)
            logging.info(
                "Sector %s: wrote %s (%d rows)",
                sector_folder_name,
                os.path.basename(sector_index_path),
                len(sector_rows),
            )

        by_company: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in sector_rows:
            company = (row.get("Company Name") or "").strip()
            by_company[company].append(row)

        for company in sorted(by_company.keys()):
            company_path = os.path.join(sector_path, sanitize_filename(company))
            os.makedirs(company_path, exist_ok=True)

            for row in by_company[company]:
                items = _collect_download_items(row, fieldnames)
                if not items:
                    skipped_no_url += 1
                    continue

                for link_label, media_url, ext in items:
                    if not media_url:
                        skipped_no_url += 1
                        continue

                    # Deterministic path (no suffix) so reruns don't create _2/_3 duplicates.
                    base = sanitize_filename(company)
                    ext2 = ext if ext.startswith(".") else "." + ext
                    if link_label and link_label.strip():
                        raw = sanitize_filename(link_label.strip(), max_length=60)
                        # Strip extension from label to avoid "deck.pdf.pdf"
                        for e in (".pdf", ".mp4", ".png", ".pptx", ".ppt"):
                            if raw.lower().endswith(e):
                                raw = raw[: -len(e)]
                                break
                        stem = base + "_" + raw
                    else:
                        stem = base + SLIDEDECK_SUFFIX.replace(".pdf", "")
                    save_path = os.path.join(company_path, stem + ext2)

                    if skip_existing and os.path.isfile(save_path):
                        # If the media file exists but the derived PDF is missing/invalid,
                        # attempt conversion (useful when we changed extension inference).
                        lower = save_path.lower()
                        if lower.endswith((".ppt", ".pptx")):
                            pdf_path = os.path.join(company_path, Path(save_path).stem + ".pdf")
                            if not os.path.isfile(pdf_path):
                                _convert_office_to_pdf(save_path)
                        elif lower.endswith((".jpg", ".jpeg", ".png")):
                            pdf_path = os.path.join(company_path, Path(save_path).stem + ".pdf")
                            if not os.path.isfile(pdf_path):
                                _convert_image_to_pdf(save_path, pdf_path)

                        skipped_exists += 1
                        continue

                    url = resolve_url(media_url, base_url)
                    lower_save = save_path.lower()
                    # For expected .mp4 files, prefer yt-dlp: it handles
                    # both direct MP4 URLs and embedded video pages.
                    if lower_save.endswith(".mp4"):
                        logging.info(
                            "Downloading video (yt-dlp) for %s -> %s",
                            company,
                            os.path.basename(save_path),
                        )
                        if download_youtube(url, save_path, timeout=DOWNLOAD_TIMEOUT):
                            done += 1
                        else:
                            failed += 1
                        continue
                    logging.info("Downloading %s -> %s", company, os.path.basename(save_path))
                    if download_media(url, save_path):
                        # If this is a PPT/PPTX deck, try to also produce a PDF alongside it.
                        lower = save_path.lower()
                        if lower.endswith((".ppt", ".pptx")):
                            _convert_office_to_pdf(save_path)
                        # If this is an image deck, convert to PDF.
                        if lower.endswith((".jpg", ".jpeg", ".png")):
                            pdf_path = os.path.join(company_path, Path(save_path).stem + ".pdf")
                            _convert_image_to_pdf(save_path, pdf_path)
                        done += 1
                    else:
                        failed += 1

    logging.info(
        "Done: %d downloaded, %d skipped (no URL), %d skipped (already exists), %d failed.",
        done, skipped_no_url, skipped_exists, failed,
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    parser = argparse.ArgumentParser(
        description="Download from index CSV into sector/company folders (generic; works with any index with Company Name, Sector, Link Label, PDF URL).",
    )
    parser.add_argument(
        "index",
        nargs="?",
        default=None,
        help="Path to index CSV (default: newest index_*.csv in output dir).",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=None,
        help="Output directory (default: INDEX_OUTPUT_DIR env or ~/Downloads/IndexDownloads).",
    )
    parser.add_argument(
        "--base-url",
        "-b",
        default=None,
        help="Base URL for relative links (default: INDEX_BASE_URL env or empty).",
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Re-download even if file already exists.",
    )
    parser.add_argument(
        "--flat",
        action="store_true",
        help="Flat output structure: write directly to OUTPUT_DIR/<Company>/ (no sector folders).",
    )
    parser.add_argument(
        "--fix-names",
        action="store_true",
        help="Fix existing file and folder names in output dir (remove invalid chars), then exit.",
    )
    args = parser.parse_args()

    output_dir = args.output_dir or _default_output_dir()
    base_url = (args.base_url or _default_base_url()).strip()

    if args.fix_names:
        out_dir = os.path.abspath(output_dir)
        logging.info("Fixing file and folder names in: %s", out_dir)
        files_renamed, dirs_renamed = fix_existing_output_names(out_dir)
        logging.info("Done: %d file(s) and %d folder(s) renamed.", files_renamed, dirs_renamed)
        sys.exit(0)

    index_path = args.index
    if not index_path:
        index_path = newest_index_path(output_dir)
        if not index_path:
            logging.error("No index file given and no index_*.csv or open_rounds_*.csv found in %s", output_dir)
            sys.exit(1)
        logging.info("Using newest index: %s", index_path)

    run(
        index_path,
        output_dir=output_dir,
        base_url=base_url,
        skip_existing=not args.no_skip_existing,
        flat=args.flat,
    )


if __name__ == "__main__":
    main()

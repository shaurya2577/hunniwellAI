#!/usr/bin/env python3
"""
Delete invalid media files that were saved with the wrong extension.

Rules:
- *.pdf must start with magic bytes "%PDF"
- *.mp4 must not start with "<" (HTML) and must contain an MP4 box marker ("ftyp")

This helps when wrappers return HTML error pages but we previously saved them as
PDF/MP4 due to older downloader behavior.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def _read_head(path: Path, n: int = 64) -> bytes:
    try:
        return path.read_bytes()[:n]
    except OSError:
        return b""


def cleanup(root: Path, dry_run: bool) -> tuple[int, int]:
    root = root.expanduser().resolve()
    deleted = 0
    checked = 0

    for p in root.rglob("*"):
        if p.is_dir():
            continue
        name = p.name.lower()

        if name.endswith(".pdf"):
            checked += 1
            head = _read_head(p)
            if not head.startswith(b"%PDF"):
                if not dry_run:
                    p.unlink(missing_ok=True)
                deleted += 1

        elif name.endswith(".mp4"):
            checked += 1
            head = _read_head(p)
            if head.startswith(b"<") or b"ftyp" not in head:
                if not dry_run:
                    p.unlink(missing_ok=True)
                deleted += 1

    return checked, deleted


def main() -> None:
    ap = argparse.ArgumentParser(description="Delete invalid .pdf/.mp4 files in output trees.")
    ap.add_argument(
        "-o",
        "--output-dir",
        action="append",
        required=True,
        help="Output directory containing radar_media_index.csv and company folders.",
    )
    ap.add_argument("--dry-run", action="store_true", help="Only print what would be deleted.")
    args = ap.parse_args()

    total_checked = 0
    total_deleted = 0
    for out in args.output_dir:
        root = Path(out)
        checked, deleted = cleanup(root, dry_run=args.dry_run)
        total_checked += checked
        total_deleted += deleted
        print(f"{root}: checked {checked}, deleted {deleted}")

    print(f"Total: checked {total_checked}, deleted {total_deleted}")


if __name__ == "__main__":
    main()


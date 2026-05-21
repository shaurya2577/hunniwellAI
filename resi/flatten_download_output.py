#!/usr/bin/env python3
"""
Flatten an existing download output folder from:
  OUTPUT_DIR/<Sector>/<Company>/...
to:
  OUTPUT_DIR/<Company>/...

This is a one-time migration helper for previously generated outputs.
"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


def flatten(output_dir: Path) -> tuple[int, int]:
    output_dir = output_dir.expanduser().resolve()
    moved_files = 0
    removed_dirs = 0

    for sector_dir in sorted(p for p in output_dir.iterdir() if p.is_dir()):
        # skip known non-sector dirs
        if sector_dir.name.startswith("."):
            continue
        if sector_dir.name in {"company_docs"}:
            continue
        # heuristic: sector dirs tend to contain !!!*_index.csv or company subdirs
        children = list(sector_dir.iterdir())
        if not children:
            continue

        # Move each company directory up
        for child in children:
            if child.is_file() and child.name.startswith("!!!") and child.name.endswith("_index.csv"):
                # sector index file: drop it
                continue
            if not child.is_dir():
                continue
            company_dir = child
            target = output_dir / company_dir.name
            target.mkdir(parents=True, exist_ok=True)
            for item in company_dir.iterdir():
                dest = target / item.name
                if dest.exists():
                    # If collision, keep both by suffixing
                    stem = dest.stem
                    suffix = dest.suffix
                    i = 2
                    while True:
                        alt = target / f"{stem}_{i}{suffix}"
                        if not alt.exists():
                            dest = alt
                            break
                        i += 1
                shutil.move(str(item), str(dest))
                moved_files += 1
            # remove now-empty company dir
            try:
                company_dir.rmdir()
            except OSError:
                pass

        # remove now-empty sector dir
        try:
            for leftover in sector_dir.iterdir():
                if leftover.is_file() and leftover.name.startswith("!!!") and leftover.name.endswith("_index.csv"):
                    leftover.unlink(missing_ok=True)
            sector_dir.rmdir()
            removed_dirs += 1
        except OSError:
            pass

    # Remove legacy company_docs (docs are now per-company)
    legacy_docs = output_dir / "company_docs"
    if legacy_docs.is_dir():
        shutil.rmtree(legacy_docs, ignore_errors=True)

    return moved_files, removed_dirs


def main() -> None:
    ap = argparse.ArgumentParser(description="Flatten OUTPUT_DIR sector/company structure into OUTPUT_DIR/company only.")
    ap.add_argument("--output-dir", "-o", type=Path, required=True)
    args = ap.parse_args()

    moved, removed = flatten(args.output_dir)
    print(f"Flatten done: {moved} items moved, {removed} sector dir(s) removed.")


if __name__ == "__main__":
    main()


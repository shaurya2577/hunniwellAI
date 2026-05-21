#!/usr/bin/env python3
"""
Remove leftover "*_Website.pdf" files from an output directory.

These came from older index generations that included Website URLs; the current
Radar pipeline excludes Website links, but previously-downloaded files remain.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def remove(root: Path) -> int:
    root = root.expanduser().resolve()
    deleted = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if not name.endswith("_Website.pdf"):
                continue
            p = Path(dirpath) / name
            try:
                p.unlink()
                deleted += 1
            except OSError:
                pass
    return deleted


def main() -> None:
    ap = argparse.ArgumentParser(description="Remove *_Website.pdf files under output dir.")
    ap.add_argument("--output-dir", "-o", type=Path, required=True)
    args = ap.parse_args()
    n = remove(args.output_dir)
    print(f"Removed {n} website PDF(s).")


if __name__ == "__main__":
    main()


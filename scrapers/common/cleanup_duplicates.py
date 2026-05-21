#!/usr/bin/env python3
"""
Remove duplicate files in Innovator (or similar) download folders.

When the downloader runs multiple times, it creates Company_Deck_2.pdf, Company_Deck_3.pdf
etc. to avoid overwriting. These are duplicates of Company_Deck.pdf. This script finds
such files, verifies they match the base file (same size), and removes the duplicates.

Videos with _2, _3 etc. that have DIFFERENT sizes from the base are kept (they're
different videos, not duplicates).

Usage:
  python cleanup_duplicates.py [directory]
  python cleanup_duplicates.py ~/Downloads/Innovator
  python cleanup_duplicates.py --dry-run ~/Downloads/Innovator  # show what would be deleted
"""
import argparse
import os
import re
import sys


def find_duplicate_candidates(root_dir: str) -> list[tuple[str, str]]:
    """
    Find files matching *_2.ext, *_3.ext, etc. Return list of (duplicate_path, base_path).
    """
    candidates = []
    # Match _2, _3, _4, ... before the extension
    pattern = re.compile(r"^(.+)_(\d+)(\.[a-zA-Z0-9]+)$")

    for dirpath, _dirnames, filenames in os.walk(root_dir):
        for name in filenames:
            if name.startswith("."):
                continue
            m = pattern.match(name)
            if not m:
                continue
            stem, num, ext = m.groups()
            base_name = stem + ext
            dup_path = os.path.join(dirpath, name)
            base_path = os.path.join(dirpath, base_name)
            if os.path.isfile(base_path):
                candidates.append((dup_path, base_path))
    return candidates


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove duplicate files (e.g. Company_Deck_2.pdf) when base exists and has same content."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=os.path.join(os.path.expanduser("~"), "Downloads", "Innovator"),
        help="Directory to scan (default: ~/Downloads/Innovator)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be deleted, don't delete",
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=1,
        help="Only consider files at least this many bytes (default: 1)",
    )
    args = parser.parse_args()

    root = os.path.abspath(args.directory)
    if not os.path.isdir(root):
        print(f"Error: not a directory: {root}", file=sys.stderr)
        sys.exit(1)

    candidates = find_duplicate_candidates(root)
    to_delete = []
    for dup_path, base_path in candidates:
        try:
            dup_size = os.path.getsize(dup_path)
            base_size = os.path.getsize(base_path)
        except OSError:
            continue
        if dup_size < args.min_size:
            continue
        if dup_size == base_size:
            to_delete.append(dup_path)

    if not to_delete:
        print("No duplicate files found.")
        return

    print(f"Found {len(to_delete)} duplicate(s) (same size as base file):")
    for p in sorted(to_delete):
        print(f"  {p}")

    if args.dry_run:
        print("\nDry run: no files deleted. Run without --dry-run to remove.")
        return

    print("\nDeleting...")
    deleted = 0
    for p in to_delete:
        try:
            os.remove(p)
            print(f"  Deleted: {p}")
            deleted += 1
        except OSError as e:
            print(f"  Failed to delete {p}: {e}", file=sys.stderr)
    print(f"Done: {deleted} file(s) removed.")


if __name__ == "__main__":
    main()

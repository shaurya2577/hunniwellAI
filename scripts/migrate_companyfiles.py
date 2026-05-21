#!/usr/bin/env python3
"""
Rename the messy local CompanyFiles/ folders to match the canonical OneDrive
event names. Runs in --dry-run mode by default. Per-user direction: does ONLY
renames, NEVER deletions.

Usage:
    python scripts/migrate_companyfiles.py                # dry-run (default)
    python scripts/migrate_companyfiles.py --apply        # actually rename
    python scripts/migrate_companyfiles.py --root /custom/path

Default ROOT comes from $HUNNIWELL_COMPANYFILES_ROOT or ~/Documents/Hunniwell.

The mapping table below is the source of truth. Edit it if you discover the
local folder names are different from what we observed.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Mapping: current local folder name -> canonical OneDrive folder name.
# Entries whose source folder doesn't exist are silently skipped (idempotent).
RENAMES: dict[str, str] = {
    "RESI":              "JPM 2026 (260115)",
    "Virtual0326":       "MTI 2026 - Virtual Pitch # 1 (260326)",
    "virtual0416":       "MTI 2026 - Virtual Pitch # 2 (260416)",
    "apacVirtual2(2)":   "MTI 2026 - APAC Virtual Pitch # 2 (260402)",
    "apacspotlight2":    "MTI 2026 - Asia Medtech Spotlight (260418)",  # TODO confirm date
    "LSI_USA26":         "LSI 2026 - USA (260320)",
    "LSI4082026":        "LSI 2026 - USA (260320)",
    "OpenRounds2":       "MTI 2026 - Open Rounds",
    "radar3":            "MTI 2026 - LA Radar Forum (260407)",
    # Intentionally NOT renamed (per user):
    #   Innovator           -> keep as-is; standalone, outside canonical taxonomy
    #   apacspotlight       -> noise (pre-v2 dup)
    #   apacVirtual2        -> noise (pre-patch dup)
    #   OpenRounds          -> noise (pre-v2 dup)
    #   open rounds         -> noise (HTML dumps)
    #   radar2              -> noise (empty folders)
    #   mti                 -> noise (metadata only)
    #   mti passthrough... -> ambiguous
    #   jujama / Jujama2 / jujamaaa -> Jujama scrape artifacts
    #   *_files             -> saved-HTML asset dumps
    #   2                   -> single-digit junk
    #   hunniwellDiagnosticCompanyReview, medtechbiobook -> reference docs
    #   Loose top-level files (xlsx, pptx, md, etc.) -> work product
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="Actually rename. Default is dry-run.")
    ap.add_argument(
        "--root",
        help="Override CompanyFiles root (default: $HUNNIWELL_COMPANYFILES_ROOT or ~/Documents/Hunniwell).",
    )
    args = ap.parse_args()

    root = Path(
        args.root or os.environ.get("HUNNIWELL_COMPANYFILES_ROOT") or "~/Documents/Hunniwell"
    ).expanduser().resolve()

    if not root.exists() or not root.is_dir():
        print(f"ERROR: root does not exist or is not a directory: {root}")
        return 1

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"Mode: {mode}")
    print(f"Root: {root}\n")

    plan = []
    warnings = []
    for src_name, dst_name in RENAMES.items():
        src = root / src_name
        dst = root / dst_name
        if not src.exists():
            continue
        if dst.exists():
            # Idempotent: target already exists. Only warn if source ALSO has content.
            try:
                has_src_content = any(src.iterdir())
            except OSError:
                has_src_content = False
            if has_src_content:
                warnings.append(
                    f"BOTH exist: '{src_name}' -> '{dst_name}'. Target non-empty AND source non-empty. "
                    "Manual review required. Will NOT overwrite."
                )
            else:
                plan.append((src_name, dst_name, "noop (source empty, target exists)"))
            continue
        plan.append((src_name, dst_name, "rename"))

    if not plan and not warnings:
        print("Nothing to do. Either already migrated or no source folders match.")
        return 0

    for src_name, dst_name, status in plan:
        print(f'  mv "{src_name}/" -> "{dst_name}/"   [{status}]')

    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  {w}")

    if not args.apply:
        print("\n(dry-run; pass --apply to perform renames)")
        return 0

    for src_name, dst_name, status in plan:
        if status != "rename":
            continue
        src = root / src_name
        dst = root / dst_name
        try:
            src.rename(dst)
            print(f"renamed: {src_name} -> {dst_name}")
        except OSError as e:
            print(f"FAILED:  {src_name} -> {dst_name}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

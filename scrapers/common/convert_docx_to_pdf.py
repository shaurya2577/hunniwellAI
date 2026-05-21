#!/usr/bin/env python3
"""
Batch convert DOCX -> PDF for generated company docs.

Primary converter: LibreOffice (soffice) in headless mode.

This script is intentionally dependency-light; it shells out to LibreOffice.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def _find_soffice() -> str | None:
    # PATH-installed
    for name in ("soffice", "libreoffice"):
        p = shutil.which(name)
        if p:
            return p
    # Common macOS app-bundle installs
    candidates = [
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice.bin",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return None


def convert_folder(docx_dir: Path, out_dir: Path, overwrite: bool) -> tuple[int, int]:
    """
    Convert all .docx in docx_dir into PDFs in out_dir.
    Returns (converted, skipped_existing).
    """
    docx_dir = docx_dir.expanduser().resolve()
    out_dir = out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    soffice = _find_soffice()
    if not soffice:
        raise SystemExit(
            "LibreOffice was not found.\n"
            "Install it (or ensure `soffice` is on PATH), then rerun.\n"
            "Expected locations include:\n"
            "  /Applications/LibreOffice.app/Contents/MacOS/soffice"
        )

    converted = 0
    skipped = 0

    for docx in sorted(docx_dir.glob("*.docx")):
        pdf = out_dir / (docx.stem + ".pdf")
        if pdf.exists() and not overwrite:
            skipped += 1
            continue

        # LibreOffice writes into out_dir; it chooses output filename based on input.
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
                str(docx),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if pdf.exists():
            converted += 1

    return converted, skipped


def convert_tree(root: Path, overwrite: bool) -> tuple[int, int]:
    """
    Convert all .docx under root (recursive) into PDFs alongside each docx.
    Returns (converted, skipped_existing).
    """
    root = root.expanduser().resolve()
    soffice = _find_soffice()
    if not soffice:
        raise SystemExit(
            "LibreOffice was not found.\n"
            "Install it (or ensure `soffice` is on PATH), then rerun.\n"
            "Expected locations include:\n"
            "  /Applications/LibreOffice.app/Contents/MacOS/soffice"
        )

    converted = 0
    skipped = 0
    for docx in sorted(root.rglob("*.docx")):
        out_dir = docx.parent
        pdf = out_dir / (docx.stem + ".pdf")
        if pdf.exists() and not overwrite:
            skipped += 1
            continue
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
                str(docx),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if pdf.exists():
            converted += 1
    return converted, skipped


def main() -> None:
    ap = argparse.ArgumentParser(description="Convert company_docs/*.docx to PDFs.")
    ap.add_argument(
        "--docx-dir",
        type=Path,
        required=True,
        help="Directory containing .docx files (e.g. ~/Downloads/apacspotlight/company_docs).",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Directory to write PDFs to (often same as docx-dir).",
    )
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing PDFs.")
    ap.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively convert all .docx under --docx-dir into PDFs alongside each .docx.",
    )
    args = ap.parse_args()

    if args.recursive:
        converted, skipped = convert_tree(args.docx_dir, overwrite=args.overwrite)
    else:
        converted, skipped = convert_folder(args.docx_dir, args.out_dir, overwrite=args.overwrite)
    print(f"PDF conversion done: {converted} converted, {skipped} skipped (existing).")


if __name__ == "__main__":
    main()


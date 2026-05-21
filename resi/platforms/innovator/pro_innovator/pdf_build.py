#!/usr/bin/env python3
"""PDF rebuild and manifest helpers for Pro Innovator deck capture."""

import json
from pathlib import Path


def init_run_manifest(manifest_path, run_label: str) -> None:
    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if manifest_path.exists():
        return
    manifest = {"run_label": run_label, "companies": []}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def load_run_manifest(manifest_path):
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        return {"run_label": "", "companies": []}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def append_company_result(manifest_path, result: dict) -> None:
    manifest_path = Path(manifest_path)
    manifest = load_run_manifest(manifest_path)
    companies = manifest.setdefault("companies", [])
    key_company = result.get("company_name", "")
    key_row = result.get("row_id", "")
    updated = False
    for index, existing in enumerate(companies):
        if existing.get("company_name") == key_company or (
            key_row and existing.get("row_id") == key_row
        ):
            companies[index] = result
            updated = True
            break
    if not updated:
        companies.append(result)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def build_pdf_from_images(image_paths: list, pdf_path) -> None:
    """
    Convert captured page images into a PDF.

    Requires Pillow at runtime. The import stays local so non-capture workflows
    can still run without it.
    """
    if not image_paths:
        raise ValueError("No images were provided for PDF rebuild.")

    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required for PDF rebuild. Install it with `pip install Pillow`."
        ) from exc

    converted = []
    for image_path in image_paths:
        image = Image.open(image_path)
        if image.mode != "RGB":
            image = image.convert("RGB")
        converted.append(image)

    first, rest = converted[0], converted[1:]
    Path(pdf_path).parent.mkdir(parents=True, exist_ok=True)
    first.save(pdf_path, save_all=True, append_images=rest)

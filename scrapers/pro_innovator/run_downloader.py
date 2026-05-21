#!/usr/bin/env python3
"""Live Pro Innovator runner: current Applications page -> CSV -> optional deck capture."""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from scrapers.pro_innovator import config
from scrapers.pro_innovator.deck_capture import capture_company_deck
from scrapers.pro_innovator.grid_extract import (
    build_company_records,
    extract_live_grid_rows,
    write_company_records_csv,
)
from scrapers.pro_innovator.pdf_build import (
    append_company_result,
    init_run_manifest,
    load_run_manifest,
)


def setup_logging(log_file: str = None) -> None:
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
        force=True,
    )


def launch_browser(headless: bool = False):
    pw = sync_playwright().start()
    context = pw.chromium.launch_persistent_context(
        user_data_dir=config.BROWSER_USER_DATA_DIR,
        headless=headless,
        accept_downloads=True,
    )
    context.set_default_timeout(config.DEFAULT_TIMEOUT_MS)
    context.set_default_navigation_timeout(config.NAVIGATION_TIMEOUT_MS)
    page = context.pages[-1] if context.pages else context.new_page()
    return pw, context, page


def wait_for_applications_page(page) -> None:
    page.locator(".ag-root[role='grid'], .ag-root-wrapper").first.wait_for(
        state="visible",
        timeout=config.NAVIGATION_TIMEOUT_MS,
    )
    page.locator('[role="gridcell"][col-id="company.name"], [role="columnheader"][col-id="company.name"]').first.wait_for(
        state="visible",
        timeout=config.NAVIGATION_TIMEOUT_MS,
    )


def _run_paths(output_dir: Path, resume_manifest: Path = None) -> dict:
    if resume_manifest:
        resume_manifest = Path(resume_manifest)
        stem = resume_manifest.name.replace("_manifest.json", "")
        return {
            "csv": resume_manifest.parent / ("%s.csv" % stem),
            "manifest": resume_manifest,
            "log": resume_manifest.parent / "pro_innovator.log",
            "label": stem.replace("pro_innovator_", ""),
        }
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    return {
        "csv": output_dir / ("pro_innovator_%s.csv" % stamp),
        "manifest": output_dir / ("pro_innovator_%s_manifest.json" % stamp),
        "log": output_dir / "pro_innovator.log",
        "label": stamp,
    }


def _manifest_lookup(manifest: dict) -> dict:
    lookup = {}
    for item in manifest.get("companies", []):
        if item.get("row_id"):
            lookup["row:%s" % item["row_id"]] = item
        if item.get("company_name"):
            lookup["company:%s" % item["company_name"]] = item
    return lookup


def run_live_capture(page, output_dir, paths: dict = None, csv_only: bool = False, test_one: bool = False) -> dict:
    paths = paths or _run_paths(Path(output_dir))
    raw_rows = extract_live_grid_rows(page)
    records = build_company_records(raw_rows)
    init_run_manifest(paths["manifest"], paths["label"])
    manifest = load_run_manifest(paths["manifest"])
    previous_results = _manifest_lookup(manifest)

    for record in records:
        previous = previous_results.get("row:%s" % record["Row ID"]) or previous_results.get(
            "company:%s" % record["Company Name"]
        )
        if previous:
            record["Deck Status"] = previous.get("status", "")
            record["Deck Source URL"] = previous.get("source_url", "")
            record["Rebuilt PDF Path"] = previous.get("pdf_path", "")

    write_company_records_csv(records, paths["csv"])

    logging.info("Captured %d company row(s) into %s", len(records), paths["csv"])
    if csv_only:
        return paths

    targets = records[:1] if test_one else records
    grid_url = page.url
    for record in targets:
        if (
            record.get("Deck Status") == "captured"
            and record.get("Rebuilt PDF Path")
            and Path(record["Rebuilt PDF Path"]).exists()
        ):
            logging.info("Skipping %s; already captured in manifest.", record["Company Name"])
            continue
        logging.info("Capturing deck for %s", record["Company Name"])
        result = capture_company_deck(page, record, output_dir)
        record["Deck Status"] = result.get("status", "")
        record["Deck Source URL"] = result.get("source_url", "")
        record["Rebuilt PDF Path"] = result.get("pdf_path", "")
        append_company_result(paths["manifest"], result)
        write_company_records_csv(records, paths["csv"])
        if page.url != grid_url:
            page.goto(grid_url, wait_until="domcontentloaded", timeout=config.NAVIGATION_TIMEOUT_MS)
            wait_for_applications_page(page)

    write_company_records_csv(records, paths["csv"])
    return paths


def run_manual_session(output_dir, paths: dict = None, headless: bool = False, csv_only: bool = False, test_one: bool = False) -> dict:
    pw, context, page = launch_browser(headless=headless)
    try:
        print("Browser ready. Log in if needed, navigate to the Pro Innovator Applications page, then press Enter.")
        input()
        wait_for_applications_page(page)
        return run_live_capture(page, output_dir, paths=paths, csv_only=csv_only, test_one=test_one)
    finally:
        context.close()
        pw.stop()


def main(output_dir=None, headless: bool = False, csv_only: bool = False, test_one: bool = False, resume_manifest=None):
    output_dir = Path(output_dir or config.DEFAULT_OUTPUT_DIR)
    paths = _run_paths(output_dir, resume_manifest=resume_manifest)
    setup_logging(str(paths["log"]))
    return run_manual_session(output_dir, paths=paths, headless=headless, csv_only=csv_only, test_one=test_one)

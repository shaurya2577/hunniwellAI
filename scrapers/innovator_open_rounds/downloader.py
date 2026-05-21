#!/usr/bin/env python3
"""
Innovator Portal (pro.innovator.org) Open Rounds pitch deck index builder.

Like the RESI scraper: automatically collects all company URLs from the Open Rounds list,
then visits each company page, runs the macro to extract full data, and writes both
index CSV (for download_from_index.py) and open_rounds CSV. MTI displays all companies
in one list, so no pagination groups.

Usage (from repo root):
  python -m scrapers.innovator_open_rounds.downloader           # full auto: grab all companies
  python -m scrapers.innovator_open_rounds.downloader --test-one # process only first company
  python -m scrapers.innovator_open_rounds.downloader --manual  # manual: navigate, press Enter per company
  python -m scrapers.innovator_open_rounds.downloader --save-storage   # one-time: save auth
"""
import logging
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

# Ensure project root is on path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from playwright.sync_api import sync_playwright

from scrapers.innovator_open_rounds import config
from scrapers.common.index_csv import (
    append_to_open_rounds_index,
    get_open_rounds_index_path_for_run,
    init_open_rounds_index,
)

os.makedirs(config.OUTPUT_DIR, exist_ok=True)


def setup_logging(log_file: str | None = None) -> None:
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
    """Launch Chromium, navigate to Innovator Open Rounds. Returns (pw, context)."""
    pw = sync_playwright().start()
    context = pw.chromium.launch_persistent_context(
        user_data_dir=config.BROWSER_USER_DATA_DIR,
        headless=headless,
        downloads_path=config.OUTPUT_DIR,
    )
    context.set_default_timeout(config.DEFAULT_TIMEOUT)
    context.set_default_navigation_timeout(config.NAVIGATION_TIMEOUT)
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(
        config.OPEN_ROUNDS_URL,
        wait_until="domcontentloaded",
        timeout=config.NAVIGATION_TIMEOUT,
    )
    return pw, context


def wait_for_company_list(page) -> None:
    """
    Wait for the Open Rounds company list to be visible and fully loaded.
    Scrolls down to trigger lazy-loading if the list is long.
    """
    try:
        # Wait for at least one company link to appear
        page.locator("a[href*='/open-rounds/company/']").first.wait_for(
            state="visible", timeout=config.NAVIGATION_TIMEOUT
        )
        # Scroll until no new links load (handles lazy/infinite scroll)
        prev_count = 0
        for _ in range(15):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(600)
            count = page.locator("a[href*='/open-rounds/company/']").count()
            if count == prev_count and count > 0:
                break
            prev_count = count
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(400)
    except Exception:
        pass


def get_company_urls_on_page(page) -> list[str]:
    """
    Return list of absolute company page URLs on the current Open Rounds list page.
    Links match href containing /open-rounds/company/ (and are deduped).
    """
    seen = set()
    out = []
    try:
        links = page.locator("a[href*='/open-rounds/company/']")
        n = links.count()
        for i in range(n):
            try:
                href = links.nth(i).get_attribute("href", timeout=2000) or ""
                href = href.strip()
                if not href or "open-rounds/company/" not in href:
                    continue
                if href.startswith("/"):
                    full = urljoin(config.BASE_URL, href)
                else:
                    full = href
                # Normalize: strip fragment and query if present
                base = full.split("?")[0].split("#")[0]
                if base not in seen:
                    seen.add(base)
                    out.append(base)
            except Exception:
                continue
    except Exception:
        pass
    return out


def go_to_next_page(page) -> bool:
    """Click next page on Open Rounds list. Return True if navigated."""
    timeout = config.MACRO_STEP_TIMEOUT
    next_link = page.get_by_role("link", name=re.compile(r"next|»|last", re.I)).first
    if next_link.count() > 0 and next_link.is_visible():
        try:
            next_link.click(timeout=timeout)
            page.wait_for_load_state("networkidle", timeout=config.NAVIGATION_TIMEOUT)
            return True
        except Exception:
            pass
    page2 = page.get_by_role("link", name="2").first
    if page2.count() > 0 and page2.is_visible():
        try:
            page2.click(timeout=timeout)
            page.wait_for_load_state("networkidle", timeout=config.NAVIGATION_TIMEOUT)
            return True
        except Exception:
            pass
    return False


def _categorization_kwargs(cat: dict, fallback_sector: str = "") -> dict:
    if not isinstance(cat, dict):
        cat = {}
    return {
        "sector": (cat.get("sector") or fallback_sector or "").strip(),
        "subsectors": (cat.get("subsectors") or "").strip(),
        "business_model": (cat.get("business_model") or "").strip(),
        "main_therapeutic_sector": (cat.get("main_therapeutic_sector") or "").strip(),
        "customer_segments": (cat.get("customer_segments") or "").strip(),
    }


def _general_info_kwargs(info: dict) -> dict:
    if not isinstance(info, dict):
        info = {}
    return {
        "address": (info.get("address") or "").strip(),
        "year_founded": (info.get("year_founded") or "").strip(),
        "company_email": (info.get("company_email") or "").strip(),
        "website": (info.get("website") or "").strip(),
        "company_description": (info.get("company_description") or "").strip(),
        "state_of_ownership": (info.get("state_of_ownership") or "").strip(),
        "function_of_location": (info.get("function_of_location") or "").strip(),
        "headquarters": (info.get("headquarters") or "").strip(),
        "source_of_foundation": (info.get("source_of_foundation") or "").strip(),
    }


def run_macro_on_page(page, context, run_macro_fn, company_name_hint: str = ""):
    """Run the Innovator macro on the current page; return (company_name, links, cat, info, open_rounds_data)."""
    try:
        result = run_macro_fn(page, context, company_name_hint)
    except TypeError:
        result = run_macro_fn(page, context)
    open_rounds_data = {}
    if isinstance(result, tuple) and len(result) >= 2:
        name = (result[0] or company_name_hint or "Unknown").strip()
        links = result[1] if isinstance(result[1], list) else []
        cat = result[2] if len(result) >= 3 and isinstance(result[2], dict) else {}
        info = result[3] if len(result) >= 4 and isinstance(result[3], dict) else {}
        open_rounds_data = result[4] if len(result) >= 5 and isinstance(result[4], dict) else {}
    else:
        name = (result or company_name_hint or "Unknown").strip() if result else "Unknown"
        links = []
        cat = {}
        info = {}
    if not isinstance(links, list):
        links = [( "", str(links).strip() )] if links else []
    return name, links, cat, info, open_rounds_data


def run_auto_loop(page, context, test_one: bool = False) -> None:
    """
    Full automation: from Open Rounds list, collect all company URLs, then for each
    URL navigate, run macro, append to open_rounds CSV (single consolidated output).
    """
    from scrapers.innovator_open_rounds.recordings import macro as macro_module

    run_macro_fn = getattr(macro_module, "run_macro", None)
    if run_macro_fn is None:
        logging.error("platforms/innovator/recordings/macro.py has no run_macro function.")
        return

    open_rounds_path = get_open_rounds_index_path_for_run(config.OUTPUT_DIR)
    init_open_rounds_index(open_rounds_path)

    # Wait for company list to load, then collect all URLs (MTI shows all in one list)
    wait_for_company_list(page)
    urls = get_company_urls_on_page(page)
    logging.info("Found %d company link(s) on Open Rounds list.", len(urls))
    if not urls:
        logging.warning("No company links found. Ensure you are logged in and on the Open Rounds page.")
        return

    for idx, url in enumerate(urls, 1):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=config.NAVIGATION_TIMEOUT)
            # Wait for main content to render (SPA needs JS to hydrate; networkidle hangs on video)
            page.locator("#section-card, #navContainerRef, #section-general-information").first.wait_for(
                state="visible", timeout=config.NAVIGATION_TIMEOUT
            )
            name, links, cat, info, open_rounds_data = run_macro_on_page(page, context, run_macro_fn)
            if open_rounds_data and open_rounds_data.get("company_name"):
                append_to_open_rounds_index(open_rounds_path, **open_rounds_data)
            n_links = len(links) or 1
            logging.info("[%d/%d] Done: %s (%d link(s)).", idx, len(urls), name, n_links)
        except Exception as e:
            logging.warning("Failed for %s: %s", url, e)

        if test_one:
            logging.info("Test-one: stopping after first company.")
            break

    logging.info("Run complete. Open Rounds: %s", open_rounds_path)


def run_playback_loop(page, context) -> None:
    """
    Manual mode: user navigates to a company page, presses Enter; we run macro and append.
    Type 'done' to exit.
    """
    from scrapers.innovator_open_rounds.recordings import macro as macro_module

    run_macro_fn = getattr(macro_module, "run_macro", None)
    if run_macro_fn is None:
        logging.error("platforms/innovator/recordings/macro.py has no run_macro function.")
        return

    open_rounds_path = get_open_rounds_index_path_for_run(config.OUTPUT_DIR)
    init_open_rounds_index(open_rounds_path)

    while True:
        try:
            line = input(
                "Navigate to a company page (open-rounds/company/...), then press Enter to run macro (or type 'done' to exit). "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        if line == "done":
            break

        try:
            name, links, cat, info, open_rounds_data = run_macro_on_page(page, context, run_macro_fn)
            if open_rounds_data and open_rounds_data.get("company_name"):
                append_to_open_rounds_index(open_rounds_path, **open_rounds_data)
            logging.info("Done: %s (%d link(s)).", name, len(links) or 1)
        except Exception as e:
            logging.warning("Macro failed: %s", e)

    logging.info("Open Rounds: %s", open_rounds_path)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Innovator Portal Open Rounds: build index CSV from company pages (then use download_from_index.py)."
    )
    parser.add_argument(
        "--save-storage",
        action="store_true",
        help="One-time: launch browser, log in if needed, press Enter; save auth to recordings/auth.json.",
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Manual mode: navigate to each company page, press Enter to run macro (type 'done' to exit).",
    )
    parser.add_argument(
        "--test-one",
        action="store_true",
        help="Process only the first company (auto mode).",
    )
    parser.add_argument("--headless", action="store_true", help="Run browser headless.")
    parser.add_argument("--log-file", type=str, default=None, help="Also write logs to this file.")
    args = parser.parse_args()

    log_path = args.log_file or os.path.join(config.OUTPUT_DIR, "innovator_download.log")
    setup_logging(log_path)

    if args.save_storage:
        os.makedirs(config.RECORDINGS_DIR, exist_ok=True)
        logging.info("Save-storage: browser will open. Log in if needed, then press Enter to save auth to %s", config.STORAGE_STATE_PATH)
        pw, context = launch_browser(headless=args.headless)
        try:
            if sys.stdin is not None and sys.stdin.isatty():
                input()
            else:
                logging.warning(
                    "stdin is not interactive; cannot wait for Enter. Leaving browser open for 60s to allow login."
                )
                time.sleep(60)
            context.storage_state(path=config.STORAGE_STATE_PATH)
            logging.info("Saved to %s", config.STORAGE_STATE_PATH)
        finally:
            context.close()
            pw.stop()
        return

    logging.info("Output: %s", config.OUTPUT_DIR)
    pw, context = launch_browser(headless=args.headless)
    try:
        page = context.pages[0] if context.pages else context.new_page()
        if args.manual:
            logging.info("Manual mode: navigate to each company page, press Enter to run macro (type 'done' to exit).")
            run_playback_loop(page, context)
        else:
            run_auto_loop(page, context, test_one=args.test_one)
        if sys.stdin is not None and sys.stdin.isatty():
            logging.info("Close browser when ready.")
            input("Press Enter to close browser and exit.")
        else:
            logging.info("Run complete (non-interactive); closing browser.")
    finally:
        context.close()
        pw.stop()


if __name__ == "__main__":
    main()

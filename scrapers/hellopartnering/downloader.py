#!/usr/bin/env python3
"""
RESI (HelloPartnering) Pitch Deck Bulk Downloader (record-and-replay).

You record one per-company flow with Playwright codegen, then run this script:
navigate to each company in the browser and press Enter to run the macro.
Downloads go to the configured folder (default: ~/Downloads/RESI on macOS) and are
renamed to CompanyName_RESI.pdf and CompanyName_SLIDEDECK.pdf; a per-run CSV index
(index_YYYY-MM-DD_HH-MM-SS.csv) is created in that folder.

Usage (from repo root):
  python run_resi.py --save-storage   # one-time: save auth for codegen
  python run_resi.py                  # browser opens; go to each company, press Enter; type 'done' when finished
  python run_resi.py --auto           # full automation (login, all sectors)
  python run_resi.py --auto --all-sectors

Or: python -m scrapers.hellopartnering.downloader [options]
"""
import argparse
import getpass
import logging
import os
import re
import sys
from pathlib import Path

# Ensure project root is on path so index_helper and this package resolve
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from playwright.sync_api import sync_playwright

from scrapers.hellopartnering import config
from scrapers.common.index_csv import (
    append_to_index,
    append_to_investor_index,
    get_index_path_for_run,
    get_investor_index_path_for_run,
    init_index,
    init_investor_index,
)

# Ensure output directory exists
os.makedirs(config.OUTPUT_DIR, exist_ok=True)


def setup_logging(log_file: str | None = None) -> None:
    """Configure logging to console and optionally to file."""
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
        force=True,
    )


# Characters invalid in file/folder names on Windows and common filesystems
_INVALID_NAME_CHARS = r'[#%&*:<>?"/\\|]'


def sanitize_filename(name: str, max_length: int = 200) -> str:
    """Sanitize company name for use in filenames. Removes invalid chars and trailing period/space."""
    s = (name or "").strip()
    s = re.sub(_INVALID_NAME_CHARS, "_", s)
    s = re.sub(r"\s+", " ", s).strip().strip(".")
    return s[:max_length] if len(s) > max_length else s or "Unknown"


def get_credentials() -> tuple[str, str]:
    """Return (username, password) from env or prompt. Never write to disk."""
    username = config.RESI_USERNAME
    password = config.RESI_PASSWORD
    if not username:
        username = input("RESI username (or set RESI_USERNAME): ").strip()
    if not password:
        password = getpass.getpass("RESI password (or set RESI_PASSWORD): ")
    return username, password


def launch_browser_and_login(headless: bool = False, skip_manual_login: bool = False):
    """
    Launch Chromium with persistent context, navigate to RESI.
    If skip_manual_login is False, wait for user to log in and press Enter.
    Returns (playwright, browser_context). Caller must close context and stop playwright when done.
    """
    pw = sync_playwright().start()
    context = pw.chromium.launch_persistent_context(
        user_data_dir=config.BROWSER_USER_DATA_DIR,
        headless=headless,
        downloads_path=config.OUTPUT_DIR,
    )
    context.set_default_timeout(config.DEFAULT_TIMEOUT)
    context.set_default_navigation_timeout(config.NAVIGATION_TIMEOUT)
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(config.BASE_URL, wait_until="domcontentloaded", timeout=config.NAVIGATION_TIMEOUT)
    if not skip_manual_login:
        logging.info(
            "Browser opened. Log in, then navigate to the search results (company list or investor list). "
            "Press Enter here when you are on the list. Sector and categorization are read from each profile."
        )
        input()
    return pw, context


def _scroll_into_view_and_click(page, locator, timeout: int = config.MACRO_STEP_TIMEOUT) -> None:
    """Scroll element into view and click."""
    locator.wait_for(state="visible", timeout=timeout)
    locator.scroll_into_view_if_needed(timeout=timeout)
    locator.click()


def _is_logged_in(page) -> bool:
    """True if we're on a post-login page (home or search visible)."""
    url = page.url.lower()
    if "/home" in url or "/search" in url:
        return True
    try:
        return page.get_by_role("link", name=re.compile(r"search|q search", re.I)).first.is_visible(timeout=2000)
    except Exception:
        return False


def login(page, username: str, password: str) -> None:
    """
    HelloPartnering login: go to RESI JPM login (or use existing session).
    If already logged in (redirect to /home or Search visible), skip form.
    Otherwise: click login -> Previous conferences -> RESI JPM -> fill form -> submit.
    """
    timeout = config.MACRO_STEP_TIMEOUT

    # If we're already on a logged-in page (e.g. persistent session), skip
    if _is_logged_in(page):
        logging.info("Already logged in (session valid). Skipping login form.")
        return

    # Click login / partnering login in top-right
    login_link = page.get_by_role("link", name=re.compile(r"login|partnering", re.I))
    if login_link.count() == 0:
        login_link = page.locator("a").filter(has_text=re.compile(r"login|partnering", re.I)).first
    _scroll_into_view_and_click(page, login_link.first, timeout)

    # Previous conferences
    prev_conf = page.get_by_text("Previous conferences", exact=False).first
    prev_conf.wait_for(state="visible", timeout=timeout)
    prev_conf.scroll_into_view_if_needed(timeout=timeout)
    prev_conf.click()

    # RESI JPM
    resi_jpm = page.get_by_text("RESI JPM", exact=False).first
    resi_jpm.wait_for(state="visible", timeout=timeout)
    resi_jpm.click()

    # Let navigation settle (might redirect to /home if already logged in)
    page.wait_for_load_state("domcontentloaded", timeout=timeout)
    if _is_logged_in(page):
        logging.info("Already logged in after RESI JPM. Skipping login form.")
        return

    # Wait for login form and fill
    email_input = page.get_by_label(re.compile(r"email|username|user", re.I)).or_(page.locator('input[type="email"]')).first
    pass_input = page.get_by_label(re.compile(r"password", re.I)).or_(page.locator('input[type="password"]')).first
    email_input.wait_for(state="visible", timeout=timeout)
    email_input.fill(username)
    pass_input.fill(password)

    # Submit (button Login / Sign in)
    submit_btn = page.get_by_role("button", name=re.compile(r"login|sign in|submit", re.I)).first
    if submit_btn.count() == 0:
        submit_btn = page.locator('button[type="submit"]').first
    submit_btn.click()

    # Wait for logged-in: e.g. Search tab or user menu visible
    page.get_by_role("link", name=re.compile(r"search|q search", re.I)).first.wait_for(
        state="visible", timeout=config.NAVIGATION_TIMEOUT
    )
    logging.info("Logged in successfully.")


def apply_search_filters(page, sector: str) -> None:
    """
    Go to Search, set Sector to the given sector, expand Company presentations,
    check three checkboxes, click Search.
    """
    timeout = config.MACRO_STEP_TIMEOUT
    # Search tab (top nav)
    search_tab = page.get_by_role("link", name=re.compile(r"search|q search", re.I)).first
    _scroll_into_view_and_click(page, search_tab, timeout)

    # Search for Companies (left sidebar)
    search_companies = page.get_by_text("SEARCH FOR COMPANIES", exact=False).first
    search_companies.wait_for(state="visible", timeout=timeout)
    search_companies.scroll_into_view_if_needed(timeout=timeout)
    search_companies.click()

    # Sector: select the given sector (e.g. "Biotechnology - Therapeutics and Diagnostics")
    sector_label = page.get_by_text("Sector", exact=False).or_(page.get_by_text("Main sector", exact=False)).first
    sector_label.wait_for(state="visible", timeout=timeout)
    sector_label.scroll_into_view_if_needed(timeout=timeout)
    sector_dropdown = page.locator("select, [role='combobox'], [aria-haspopup='listbox']").filter(has=sector_label).first
    if sector_dropdown.count() == 0:
        sector_dropdown = page.get_by_text("Sector", exact=False).first.locator("..").locator("select, [role='combobox']").first
    if sector_dropdown.count() > 0:
        sector_dropdown.click()
        page.get_by_text(sector, exact=True).first.click()
    else:
        page.get_by_text(sector, exact=True).first.scroll_into_view_if_needed(timeout=timeout)
        page.get_by_text(sector, exact=True).first.click()

    # Company presentations section: expand if collapsed, then Media type dropdown and checkboxes
    company_pres = page.get_by_text("Company presentations", exact=False).first
    company_pres.wait_for(state="visible", timeout=timeout)
    company_pres.scroll_into_view_if_needed(timeout=timeout)
    # If it's expandable (chevron), click to expand
    try:
        company_pres.click(timeout=2000)
    except Exception:
        pass

    # Checkbox 1: Profiles incl. any kind of presentations
    cb1 = page.get_by_role("checkbox").filter(has_text=re.compile(r"Profiles incl\. any kind of presentations", re.I)).first
    if cb1.count() > 0 and not cb1.is_checked():
        cb1.check()

    # Media type dropdown: open and check "Recorded company presentation (movie)" and "Company slides (pdf)"
    media_type = page.get_by_text("Media type", exact=False).first
    media_type.wait_for(state="visible", timeout=timeout)
    media_type.scroll_into_view_if_needed(timeout=timeout)
    # Open dropdown (-- select -- or the dropdown trigger)
    dropdown_trigger = page.get_by_text("-- select --", exact=False).first
    if dropdown_trigger.count() > 0:
        dropdown_trigger.click()
    cb2 = page.get_by_role("checkbox").filter(has_text=re.compile(r"Recorded company presentation \(movie\)", re.I)).first
    if cb2.count() > 0 and not cb2.is_checked():
        cb2.check()
    cb3 = page.get_by_role("checkbox").filter(has_text=re.compile(r"Company slides \(pdf\)", re.I)).first
    if cb3.count() > 0 and not cb3.is_checked():
        cb3.check()

    # Search button
    search_btn = page.get_by_role("button", name=re.compile(r"search", re.I)).first
    if search_btn.count() == 0:
        search_btn = page.get_by_text("Search", exact=True).first
    search_btn.wait_for(state="visible", timeout=timeout)
    search_btn.click()

    # Wait for results (e.g. "Results 1 - 20" or company list)
    page.wait_for_load_state("networkidle", timeout=config.NAVIGATION_TIMEOUT)
    logging.info("Search filters applied; results loaded.")


def apply_search_filters_investor(page) -> None:
    """
    Navigate to Search for Investors, apply default filters, click Search.
    Investor search page has similar structure; Main sector "Investor" or subsector filters.
    """
    timeout = config.MACRO_STEP_TIMEOUT
    # Navigate to investor search
    page.goto(config.INVESTOR_SEARCH_URL, wait_until="domcontentloaded", timeout=config.NAVIGATION_TIMEOUT)
    page.wait_for_load_state("networkidle", timeout=config.NAVIGATION_TIMEOUT)
    # Search tab if not already there
    search_tab = page.get_by_role("link", name=re.compile(r"search|q search", re.I)).first
    if search_tab.count() > 0 and search_tab.is_visible():
        try:
            search_tab.click(timeout=timeout)
            page.wait_for_load_state("domcontentloaded", timeout=timeout)
        except Exception:
            pass
    # Search for Investors (left sidebar)
    search_investors = page.get_by_text("search for investors", exact=False).first
    if search_investors.count() > 0:
        search_investors.wait_for(state="visible", timeout=timeout)
        search_investors.scroll_into_view_if_needed(timeout=timeout)
        search_investors.click()
    # Main sector: Investor (if dropdown exists)
    sector_label = page.get_by_text("Main sector", exact=False).or_(page.get_by_text("Sector", exact=False)).first
    if sector_label.count() > 0 and sector_label.is_visible(timeout=2000):
        try:
            sector_label.scroll_into_view_if_needed(timeout=timeout)
            page.get_by_text("Investor", exact=True).first.click(timeout=timeout)
        except Exception:
            pass
    # Search button
    search_btn = page.get_by_role("button", name=re.compile(r"search", re.I)).first
    if search_btn.count() == 0:
        search_btn = page.get_by_text("Search", exact=True).first
    if search_btn.count() > 0:
        search_btn.wait_for(state="visible", timeout=timeout)
        search_btn.click()
    page.wait_for_load_state("networkidle", timeout=config.NAVIGATION_TIMEOUT)
    logging.info("Investor search filters applied; results loaded.")


def _parse_firm_name_from_data_target(data_target: str) -> str:
    """Extract firm name from data-target like '#1004-Venture-Partners698d1f6f3c420' -> '1004 Venture Partners'."""
    if not data_target:
        return "Unknown"
    s = data_target.strip().lstrip("#")
    # Remove trailing hex-like hash (typically 10+ alphanumeric)
    s = re.sub(r"[0-9a-f]{10,}$", "", s, flags=re.I).strip("-_")
    return s.replace("-", " ").strip() or "Unknown"


def get_investor_links_on_page(page) -> list[tuple[str, str]]:
    """
    Return list of (firm_name, data_target) for investors on the current search results page.
    Uses open-delegate buttons: data-target contains modal id; firm name parsed from it.
    """
    buttons = page.locator("input.open-delegate[data-target], .open-delegate[data-target]")
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    n = buttons.count()
    for i in range(n):
        loc = buttons.nth(i)
        try:
            if not loc.is_visible(timeout=1000):
                continue
            data_target = (loc.get_attribute("data-target") or "").strip()
            if not data_target:
                continue
            firm_name = _parse_firm_name_from_data_target(data_target)
            if firm_name not in seen:
                seen.add(firm_name)
                out.append((firm_name, data_target))
        except Exception:
            continue
    return out


def get_company_links_on_page(page) -> list[tuple[str, str]]:
    """
    Return list of (company_name, company_name) for companies on the current search results page.
    HelloPartnering uses buttons (not links): .search-result-title input[data-toggle=modal] with value=company name.
    Caller clicks the button by name to open the company profile modal.
    """
    # Company name is an input button in .search-result-title that opens the modal (not the "View" button)
    buttons = page.locator(".search-result-title input[type='button'][data-toggle='modal']")
    out = []
    seen = set()
    n = buttons.count()
    for i in range(n):
        loc = buttons.nth(i)
        try:
            if not loc.is_visible(timeout=1000):
                continue
            # value is the company name (e.g. "7 Hills Pharma Inc.")
            name = (loc.get_attribute("value") or "").strip()
            if not name or len(name) > 200:
                continue
            if name.lower() in ("view", "company", "media", "search"):
                continue
            if name not in seen:
                seen.add(name)
                out.append((name, name))
        except Exception:
            continue
    return out


def go_to_next_page(page) -> bool:
    """Click next page (e.g. '2', 'Next', 'Last >'). Return True if we navigated, False if no next page."""
    timeout = config.MACRO_STEP_TIMEOUT
    # Pagination: current page is often highlighted; next is a link to page 2, or "»", or "Last >"
    next_link = page.get_by_role("link", name=re.compile(r"next|»|last", re.I)).first
    if next_link.count() > 0 and next_link.is_visible():
        try:
            next_link.click(timeout=timeout)
            page.wait_for_load_state("networkidle", timeout=config.NAVIGATION_TIMEOUT)
            return True
        except Exception:
            pass
    # Try clicking page number 2 if we're on 1
    page2 = page.get_by_role("link", name="2").first
    if page2.count() > 0 and page2.is_visible():
        try:
            page2.click(timeout=timeout)
            page.wait_for_load_state("networkidle", timeout=config.NAVIGATION_TIMEOUT)
            return True
        except Exception:
            pass
    return False


def _base_name(company_name: str) -> str:
    """Sanitized base name for file naming (single underscore suffixes)."""
    return sanitize_filename(company_name)


def company_files_exist(company_name: str) -> tuple[bool, bool]:
    """
    Return (resi_exists, slidedeck_exists) for this company.
    RESI profile: CompanyName_RESI.pdf; slide deck: CompanyName_SLIDEDECK.pdf.
    """
    base = _base_name(company_name)
    resi_prefix = base + config.RESI_PROFILE_SUFFIX.replace(".pdf", "")
    slidedeck_prefix = base + config.SLIDEDECK_SUFFIX.replace(".pdf", "")
    resi_exists = False
    slidedeck_exists = False
    try:
        for f in os.listdir(config.OUTPUT_DIR):
            fn = f.lower()
            if fn.startswith(resi_prefix.lower()) and fn.endswith(".pdf"):
                resi_exists = True
            if fn.startswith(slidedeck_prefix.lower()) and fn.endswith(".pdf"):
                slidedeck_exists = True
            if resi_exists and slidedeck_exists:
                break
    except OSError:
        pass
    return (resi_exists, slidedeck_exists)


def get_resi_profile_path(company_name: str) -> str:
    """Return path for CompanyName_RESI.pdf; if exists use _2, _3, etc."""
    base = _base_name(company_name)
    path = os.path.join(config.OUTPUT_DIR, base + config.RESI_PROFILE_SUFFIX)
    if not os.path.isfile(path):
        return path
    i = 2
    while True:
        path = os.path.join(config.OUTPUT_DIR, f"{base}_RESI_{i}.pdf")
        if not os.path.isfile(path):
            return path
        i += 1


def get_slidedeck_path(company_name: str) -> str:
    """Return path for CompanyName_SLIDEDECK.pdf; if exists use _2, _3, etc."""
    base = _base_name(company_name)
    path = os.path.join(config.OUTPUT_DIR, base + config.SLIDEDECK_SUFFIX)
    if not os.path.isfile(path):
        return path
    i = 2
    while True:
        path = os.path.join(config.OUTPUT_DIR, f"{base}_SLIDEDECK_{i}.pdf")
        if not os.path.isfile(path):
            return path
        i += 1


def get_company_name_from_profile(page) -> str:
    """Extract company name from profile page (h1 or main heading). RESI: company name at top of profile."""
    for selector in ("h1", "[data-testid='company-name']", ".company-name", ".profile-title"):
        try:
            el = page.locator(selector).first
            if el.count() > 0:
                text = el.inner_text().strip()
                if text and len(text) < 300:
                    return text
        except Exception:
            continue
    return "Unknown"


def get_newest_files_since(output_dir: str, since_mtime: float, max_count: int = 2) -> list[str]:
    """Return paths of up to max_count newest files in output_dir with mtime > since_mtime, oldest first (first = RESI, second = SLIDEDECK)."""
    paths_with_mtime: list[tuple[str, float]] = []
    try:
        for name in os.listdir(output_dir):
            path = os.path.join(output_dir, name)
            if not os.path.isfile(path):
                continue
            m = os.path.getmtime(path)
            if m > since_mtime:
                paths_with_mtime.append((path, m))
    except OSError:
        return []
    paths_with_mtime.sort(key=lambda x: x[1])  # oldest first
    return [p for p, _ in paths_with_mtime[:max_count]]


def rename_newest_downloads_to_company(company_name: str, newest_paths: list[str]) -> None:
    """
    Rename newest download(s) to CompanyName_RESI.pdf and CompanyName_SLIDEDECK.pdf (collision-safe).
    First path -> _RESI, second -> _SLIDEDECK. If only one path, name it _RESI.
    """
    if not newest_paths:
        return
    resi_dest = get_resi_profile_path(company_name)
    if len(newest_paths) >= 2:
        slidedeck_dest = get_slidedeck_path(company_name)
        try:
            os.rename(newest_paths[1], slidedeck_dest)
            logging.info("  Renamed -> %s", os.path.basename(slidedeck_dest))
        except OSError as e:
            logging.warning("  Could not rename to slidedeck: %s", e)
    try:
        os.rename(newest_paths[0], resi_dest)
        logging.info("  Renamed -> %s", os.path.basename(resi_dest))
    except OSError as e:
        logging.warning("  Could not rename to profile: %s", e)


def dismiss_company_modal(page, timeout: int = 3000) -> None:
    """
    Close any open company profile modal so the next company button can be clicked.
    Call after each company (success or failure) to avoid "intercepts pointer events".
    """
    try:
        close_btn = page.locator(".modal.show .modal-content button.close, .modal.in .modal-content button.close").first
        if close_btn.count() > 0:
            close_btn.click(timeout=timeout)
        else:
            page.keyboard.press("Escape")
        # Allow Bootstrap modal to finish closing before next click
        page.wait_for_timeout(250)
    except Exception:
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)
        except Exception:
            pass


def _categorization_kwargs(cat: dict, fallback_sector: str = "") -> dict:
    """Build kwargs for append_to_index from macro categorization dict (or fallback sector)."""
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
    """Build kwargs for append_to_index from macro general_info dict."""
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


def _run_company_loop(
    page,
    context,
    sector: str,
    run_macro_fn,
    max_companies: int | None = None,
    index_path: str | None = None,
) -> None:
    """
    For each result page: get company buttons, click each -> run_macro -> next; then next page.
    Macro returns (company_name, links, categorization); categorization is written to the index.
    Always dismisses the company modal after each iteration so the next button is clickable.
    If max_companies is set (e.g. 1 for --test-one), stop after that many companies on the first page.
    If index_path is given, append to that file (do not init). Otherwise create a new index for this run.
    """
    if index_path is None:
        index_path = get_index_path_for_run(config.OUTPUT_DIR)
        init_index(index_path)

    page_num = 1
    total_done = 0
    while True:
        company_links = get_company_links_on_page(page)
        logging.info("Page %d: %d companies.", page_num, len(company_links))

        for _href, company_name in company_links:
            if max_companies is not None and total_done >= max_companies:
                logging.info("Reached limit (%d company). Stopping.", max_companies)
                return

            company_name = (company_name or "Unknown").strip()

            try:
                btn = page.get_by_role("button", name=company_name).first
                btn.wait_for(state="visible", timeout=config.MACRO_STEP_TIMEOUT)
                btn.click()
                page.wait_for_timeout(500)  # let modal finish opening
                result = run_macro_fn(page, context, company_name)
                # Macro returns (company_name, [(link_label, url), ...], categorization, general_info)
                if isinstance(result, tuple) and len(result) >= 2:
                    company_name = (result[0] or company_name or "Unknown").strip()
                    links = result[1] if isinstance(result[1], list) else []
                    cat = result[2] if len(result) >= 3 and isinstance(result[2], dict) else {}
                    general_info = result[3] if len(result) >= 4 and isinstance(result[3], dict) else {}
                else:
                    company_name = (result or company_name or "Unknown").strip()
                    links = []
                    cat = {}
                    general_info = {}
                if not isinstance(links, list):
                    links = [( "", str(links).strip() )] if links else []
                c = {**_categorization_kwargs(cat, sector), **_general_info_kwargs(general_info)}
                if not links:
                    append_to_index(
                        index_path, company_name, pdf_url="", link_label="", **c
                    )
                    total_done += 1
                else:
                    for label, pdf_url in links:
                        append_to_index(
                            index_path, company_name,
                            pdf_url=(pdf_url or "").strip(),
                            link_label=(label or "").strip(),
                            **c,
                        )
                    total_done += 1
                logging.info("Done for %s (%d link(s)).", company_name, len(links) or 1)
            except Exception as e:
                logging.warning("Failed for %s: %s. Continuing.", company_name, e)
                c = {**_categorization_kwargs({}, sector), **_general_info_kwargs({})}
                append_to_index(
                    index_path, company_name, pdf_url="", link_label="", **c
                )
            finally:
                dismiss_company_modal(page)

        if max_companies is not None or not go_to_next_page(page):
            break
        page_num += 1

    logging.info("Run complete. Processed %d page(s).", page_num)


def _run_investor_loop(
    page,
    context,
    run_investor_macro_fn,
    max_investors: int | None = None,
    index_path: str | None = None,
) -> None:
    """
    For each result page: get investor (Delegate) buttons, click each -> run investor macro -> append to index.
    If max_investors is set (e.g. 1 for --test-one), stop after that many.
    """
    if index_path is None:
        index_path = get_investor_index_path_for_run(config.OUTPUT_DIR)
        init_investor_index(index_path)

    page_num = 1
    total_done = 0
    while True:
        investor_links = get_investor_links_on_page(page)
        logging.info("Page %d: %d investors.", page_num, len(investor_links))

        for firm_name_hint, data_target in investor_links:
            if max_investors is not None and total_done >= max_investors:
                logging.info("Reached limit (%d investor). Stopping.", max_investors)
                return

            try:
                # Click Delegates button to open modal (same modal for Company/Investor/Delegates tabs)
                btn = page.locator(f'[data-target="{data_target}"]').first
                btn.wait_for(state="visible", timeout=5000)
                btn.click()
                page.wait_for_timeout(500)  # Match company flow: let modal open
                result = run_investor_macro_fn(page, context, firm_name_hint)
                if isinstance(result, tuple) and len(result) >= 2:
                    firm_name, delegates, firm_info = result[0], result[1], result[2] if len(result) >= 3 else {}
                else:
                    firm_name = firm_name_hint
                    delegates = []
                    firm_info = {}
                if not isinstance(delegates, list):
                    delegates = []
                if not isinstance(firm_info, dict):
                    firm_info = {}
                fi = {k: (v or "").strip() for k, v in firm_info.items()}

                def _fi(key: str) -> str:
                    return fi.get(key, "")

                if not delegates:
                    append_to_investor_index(
                        index_path,
                        firm_name=firm_name,
                        delegate_name="",
                        position="",
                        email="",
                        linkedin="",
                        sector=_fi("sector"),
                        subsector=_fi("subsector"),
                        main_therapeutic_sector=_fi("main_therapeutic_sector"),
                        investor_type=_fi("investor_type"),
                        sector_subsector=_fi("sector_subsector"),
                        indication_interest=_fi("indication_interest"),
                        geographical_interest=_fi("geographical_interest"),
                        therapeutic_dev_phase=_fi("therapeutic_dev_phase"),
                        medical_device_dev_phase=_fi("medical_device_dev_phase"),
                        capital_structure=_fi("capital_structure"),
                        investment_stage=_fi("investment_stage"),
                        mandate_summary=_fi("mandate_summary"),
                        location=_fi("location"),
                    )
                    total_done += 1
                else:
                    for d in delegates:
                        append_to_investor_index(
                            index_path,
                            firm_name=firm_name,
                            delegate_name=(d.get("name") or "").strip(),
                            position=(d.get("position") or "").strip(),
                            email=(d.get("email") or "").strip(),
                            linkedin=(d.get("linkedin") or "").strip(),
                            sector=_fi("sector"),
                            subsector=_fi("subsector"),
                            main_therapeutic_sector=_fi("main_therapeutic_sector"),
                            investor_type=_fi("investor_type"),
                            sector_subsector=_fi("sector_subsector"),
                            indication_interest=_fi("indication_interest"),
                            geographical_interest=_fi("geographical_interest"),
                            therapeutic_dev_phase=_fi("therapeutic_dev_phase"),
                            medical_device_dev_phase=_fi("medical_device_dev_phase"),
                            capital_structure=_fi("capital_structure"),
                            investment_stage=_fi("investment_stage"),
                            mandate_summary=_fi("mandate_summary"),
                            location=_fi("location"),
                        )
                    total_done += 1
                logging.info("Done for %s (%d delegate(s)).", firm_name, len(delegates) or 1)
            except Exception as e:
                logging.warning("Failed for %s: %s. Continuing.", firm_name_hint, e)
                try:
                    append_to_investor_index(index_path, firm_name=firm_name_hint, delegate_name="")
                except Exception:
                    pass
            finally:
                dismiss_company_modal(page)

        if max_investors is not None or not go_to_next_page(page):
            break
        page_num += 1

    logging.info("Investor run complete. Processed %d page(s).", page_num)


def run_auto_loop(
    page, context, sector: str | None = None, all_sectors: bool = False
) -> None:
    """
    Full automation: login, then for each sector apply search filters and run company loop.
    If all_sectors is True, run for every sector in config.TARGET_SECTORS (one shared index).
    Otherwise run for the given sector (or first TARGET_SECTORS if sector is None).
    """
    from scrapers.hellopartnering.recordings import macro as macro_module

    run_macro_fn = getattr(macro_module, "run_macro", None)
    if run_macro_fn is None:
        logging.error("platforms/resi/recordings/macro.py has no run_macro function.")
        return

    username, password = get_credentials()
    login(page, username, password)

    if all_sectors:
        sectors = config.TARGET_SECTORS
        index_path = get_index_path_for_run(config.OUTPUT_DIR)
        init_index(index_path)
        logging.info("Running for all %d sectors; index: %s", len(sectors), index_path)
        for i, s in enumerate(sectors):
            logging.info("Sector %d/%d: %s", i + 1, len(sectors), s)
            apply_search_filters(page, s)
            _run_company_loop(
                page, context, s, run_macro_fn, index_path=index_path
            )
            # Back to search for next sector (avoid stale results)
            if i < len(sectors) - 1:
                search_tab = page.get_by_role("link", name=re.compile(r"search|q search", re.I)).first
                if search_tab.count() > 0:
                    search_tab.first.click()
                    page.wait_for_load_state("domcontentloaded", timeout=config.NAVIGATION_TIMEOUT)
    else:
        s = (sector if sector in config.TARGET_SECTORS else None) or config.TARGET_SECTORS[0]
        apply_search_filters(page, s)
        _run_company_loop(page, context, s, run_macro_fn)


def run_company_loop_only(
    page, context, sector: str | None = None, test_one: bool = False
) -> None:
    """
    Run the company loop only: no login, no search filters.
    You manually choose categories in the browser; Sector, Subsectors, Business model, etc.
    are read from each company's Company categorization section in the modal and written to the index.
    Call when user has already logged in and navigated to the company list (search results).
    If test_one is True, process only the first company (for verifying the full flow).
    """
    fallback_sector = (sector or "").strip() or ""

    try:
        from scrapers.hellopartnering.recordings import macro as macro_module
    except Exception as e:
        logging.error("Could not import scrapers.hellopartnering.recordings.macro: %s", e)
        return

    run_macro_fn = getattr(macro_module, "run_macro", None)
    if run_macro_fn is None:
        logging.error("platforms/resi/recordings/macro.py has no run_macro function.")
        return

    if test_one:
        logging.info(
            "Test-one mode: will process only the first company. "
            "Verify after: 1) PDF in %s, 2) index CSV has one row.",
            config.OUTPUT_DIR,
        )
    _run_company_loop(
        page, context, fallback_sector, run_macro_fn,
        max_companies=1 if test_one else None,
    )
    if test_one:
        logging.info(
            "Test-one complete. Check %s for the PDF and the latest index_*.csv for the row.",
            config.OUTPUT_DIR,
        )


def run_investor_auto_loop(page, context, test_one: bool = False) -> None:
    """
    Investor mode: navigate to Search for Investors, apply filters, run investor loop.
    Collects delegate info (name, position, email, LinkedIn) for each investor firm.
    """
    from scrapers.hellopartnering.recordings import investor_macro as inv_macro

    run_fn = getattr(inv_macro, "run_investor_macro", None)
    if run_fn is None:
        logging.error("platforms/resi/recordings/investor_macro.py has no run_investor_macro.")
        return

    username, password = get_credentials()
    login(page, username, password)
    apply_search_filters_investor(page)
    _run_investor_loop(
        page, context, run_fn,
        max_investors=1 if test_one else None,
    )


def run_investor_loop_only(page, context, test_one: bool = False) -> None:
    """
    Investor loop only: no login, no filters. You navigate to the investor list.
    For each firm, click Delegates to open modal; script extracts delegate info.
    """
    try:
        from scrapers.hellopartnering.recordings import investor_macro as inv_macro
    except Exception as e:
        logging.error("Could not import investor_macro: %s", e)
        return

    run_fn = getattr(inv_macro, "run_investor_macro", None)
    if run_fn is None:
        logging.error("platforms/resi/recordings/investor_macro.py has no run_investor_macro.")
        return

    if test_one:
        logging.info(
            "Test-one mode: will process only the first investor. "
            "Check %s for investor_index_*.csv.",
            config.OUTPUT_DIR,
        )
    _run_investor_loop(
        page, context, run_fn,
        max_investors=1 if test_one else None,
    )
    if test_one:
        logging.info(
            "Test-one complete. Check %s for investor_index_*.csv.",
            config.OUTPUT_DIR,
        )


def run_playback_loop(page, context, sector: str) -> None:
    """
    Loop: prompt user to navigate to a company and press Enter; run macro (saves slide deck directly), append to run's CSV index.
    Exit when user types 'done' or empty line.
    """
    _auth_path = os.path.join(config.RECORDINGS_DIR, "auth.json")
    macro_instructions = (
        "Run: playwright codegen --load-storage=" + _auth_path + " " + config.BASE_URL + "\n"
        "Perform your per-company flow once, then paste the generated code into platforms/resi/recordings/macro.py "
        "(inside run_macro). Remove any page.goto(...); use the page and context passed in."
    )
    try:
        from scrapers.hellopartnering.recordings import macro as macro_module
        run_macro = getattr(macro_module, "run_macro", None)
        if run_macro is None:
            logging.error("platforms/resi/recordings/macro.py has no run_macro function. %s", macro_instructions)
            return
    except Exception as e:
        logging.error("Could not import scrapers.hellopartnering.recordings.macro: %s. %s", e, macro_instructions)
        return

    index_path = get_index_path_for_run(config.OUTPUT_DIR)
    init_index(index_path)

    while True:
        prompt = "Navigate to a company profile, then press Enter to run the macro (or type 'done' to exit). "
        try:
            line = input(prompt).strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        if line in ("done", ""):
            break

        company_name = get_company_name_from_profile(page)
        if not company_name or company_name == "Unknown":
            company_name = "Unknown"

        _, slidedeck_exists = company_files_exist(company_name)
        if slidedeck_exists:
            logging.info("Already have slide deck for %s; skipping.", company_name)
            append_to_index(index_path, company_name, pdf_url="", link_label="", **_categorization_kwargs({}, sector), **_general_info_kwargs({}))
            continue

        links = []
        cat = {}
        general_info = {}
        try:
            try:
                result = run_macro(page, context, company_name)
            except TypeError:
                result = run_macro(page, context)
            if isinstance(result, tuple) and len(result) >= 2:
                company_name = (result[0] or company_name or "Unknown").strip()
                links = result[1] if isinstance(result[1], list) else [("", (result[1] or "").strip())]
                cat = result[2] if len(result) >= 3 and isinstance(result[2], dict) else {}
                general_info = result[3] if len(result) >= 4 and isinstance(result[3], dict) else {}
            elif result is not None:
                company_name = (result.strip() if hasattr(result, "strip") else str(result)).strip()
        except Exception as e:
            logging.warning("Macro failed: %s. Correct the page and try again.", e)
            append_to_index(index_path, company_name, pdf_url="", link_label="", **_categorization_kwargs({}, sector), **_general_info_kwargs({}))
            continue

        c = {**_categorization_kwargs(cat, sector), **_general_info_kwargs(general_info)}
        if not links:
            append_to_index(index_path, company_name, pdf_url="", link_label="", **c)
        else:
            for label, pdf_url in links:
                append_to_index(
                    index_path, company_name,
                    pdf_url=(pdf_url or "").strip(),
                    link_label=(label or "").strip(),
                    **c,
                )
        logging.info("Done for %s (%d link(s)).", company_name, len(links) or 1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RESI Pitch Deck Bulk Downloader (record-and-replay). Navigate to each company and press Enter to run the macro."
    )
    parser.add_argument(
        "--save-storage",
        action="store_true",
        help="One-time: launch browser, log in, press Enter; save auth to platforms/resi/recordings/auth.json for playwright codegen --load-storage.",
    )
    parser.add_argument(
        "--sector",
        type=str,
        default="Recorded",
        help="Subsector name for index (default: Recorded).",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Full automation: login (RESI_USERNAME/RESI_PASSWORD or prompt), apply search filters, collect links for all companies on all pages.",
    )
    parser.add_argument(
        "--all-sectors",
        action="store_true",
        help="With --auto: run for every sector in config.TARGET_SECTORS (one index CSV). Default: run for --sector or first TARGET_SECTORS.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (default: visible).",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Also write logs to this file (e.g. resi_download.log).",
    )
    parser.add_argument(
        "--test-one",
        action="store_true",
        help="Process only the first company (manual login, then one click → macro → verify PDF and index).",
    )
    parser.add_argument(
        "--investor",
        action="store_true",
        help="Investor mode: index delegates from investor firms (name, position, email, LinkedIn). Use Search for Investors.",
    )
    args = parser.parse_args()

    log_path = args.log_file or os.path.join(config.OUTPUT_DIR, "resi_download.log")
    setup_logging(log_path)

    if args.save_storage:
        os.makedirs(config.RECORDINGS_DIR, exist_ok=True)
        logging.info("Save-storage mode: browser will open. Log in, then press Enter to save auth to %s", config.STORAGE_STATE_PATH)
        pw, context = launch_browser_and_login(headless=args.headless)
        try:
            context.storage_state(path=config.STORAGE_STATE_PATH)
            logging.info("Saved storage state to %s. Run: playwright codegen --load-storage=%s %s", config.STORAGE_STATE_PATH, config.STORAGE_STATE_PATH, config.BASE_URL)
        finally:
            context.close()
            pw.stop()
        return

    logging.info("Starting RESI downloader. Output: %s", config.OUTPUT_DIR)
    pw, context = launch_browser_and_login(
        headless=args.headless,
        skip_manual_login=args.auto,
    )
    try:
        page = context.pages[0] if context.pages else context.new_page()
        if args.investor:
            if args.auto:
                run_investor_auto_loop(page, context, test_one=args.test_one)
            else:
                run_investor_loop_only(page, context, test_one=args.test_one)
        elif args.auto:
            run_auto_loop(
                page, context,
                sector=args.sector,
                all_sectors=args.all_sectors,
            )
        else:
            # You choose categories in the browser; script prompts for category name for the index
            run_company_loop_only(
                page, context, sector=None, test_one=args.test_one
            )
        logging.info("Run complete. Close browser when ready.")
        input("Press Enter to close browser and exit.")
    finally:
        context.close()
        pw.stop()


if __name__ == "__main__":
    main()

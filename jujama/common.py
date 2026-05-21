#!/usr/bin/env python3
"""Shared helpers for Jujama Playwright runners."""

from __future__ import annotations

import csv
import json
import logging
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urlparse

from . import config


def setup_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )


def launch_browser(headless: bool = False):
    from playwright.sync_api import sync_playwright

    config.BROWSER_USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    pw = sync_playwright().start()
    context = pw.chromium.launch_persistent_context(
        str(config.BROWSER_USER_DATA_DIR),
        headless=headless,
        accept_downloads=False,
        viewport={"width": 1440, "height": 900},
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.set_default_timeout(config.DEFAULT_TIMEOUT_MS)
    return pw, context, page


def get_manual_page(context, fallback_page):
    pages = [page for page in context.pages if not page.is_closed()]
    return pages[-1] if pages else fallback_page


def normalize_whitespace(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def get_query_param(url: str, key: str) -> str:
    return parse_qs(urlparse(url).query).get(key, [""])[0]


def wait_for_links(page, selector: str) -> None:
    page.wait_for_selector(selector)
    page.wait_for_timeout(config.PAGE_LOAD_PAUSE_MS)


def current_active_page(page) -> int:
    locator = page.locator("ul.pagination li.page-item.active a.page-link").first
    if locator.count() == 0:
        return 1
    text = normalize_whitespace(locator.inner_text())
    return int(text) if text.isdigit() else 1


def get_total_pages(page) -> int:
    last_link = page.locator("ul.pagination a.page-link", has_text="Last").first
    if last_link.count() > 0:
        href = last_link.get_attribute("href") or ""
        match = re.search(r"LoadPaging\((\d+)\)", href)
        if match:
            return int(match.group(1))

    texts = page.locator("ul.pagination a.page-link").all_inner_texts()
    numbers = [int(text.strip()) for text in texts if text.strip().isdigit()]
    return max(numbers) if numbers else 1


def click_next_page(page, expected_page: int | None = None) -> bool:
    previous_marker = page.locator("#divContent").inner_text() if page.locator("#divContent").count() else ""
    current_page = current_active_page(page)
    next_link = page.locator("ul.pagination li.page-item a.page-link", has_text="Next").first
    if next_link.count() == 0:
        return False

    parent_class = next_link.locator("xpath=..").get_attribute("class") or ""
    href = next_link.get_attribute("href") or ""
    if "disabled" in parent_class or not href or "LoadPaging(" not in href:
        return False

    next_link.click()

    page.wait_for_timeout(config.PAGE_LOAD_PAUSE_MS)
    try:
        page.wait_for_function(
            """(payload) => {
                const [pageNumber, previous] = payload;
                const active = document.querySelector('ul.pagination li.page-item.active a.page-link');
                const content = document.querySelector('#divContent');
                const activeOk = !!active && (active.textContent || '').trim() === String(pageNumber);
                const contentOk = !!content && (!previous || content.innerText !== previous);
                return activeOk && contentOk;
            }""",
            [expected_page or (current_page + 1), previous_marker],
            timeout=config.NAVIGATION_TIMEOUT_MS,
        )
    except Exception:
        pass
    page.wait_for_timeout(config.PAGE_LOAD_PAUSE_MS)
    return True


def unique_visible_hrefs(page, selector: str) -> list[str]:
    values = page.locator(selector).evaluate_all(
        """(els) => els
            .filter((el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length))
            .map((el) => el.href || el.getAttribute('href') || '')
        """
    )
    seen = set()
    urls = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            urls.append(value)
    return urls


def open_detail_page(context, url: str):
    detail_page = context.new_page()
    detail_page.set_default_timeout(config.DEFAULT_TIMEOUT_MS)
    detail_page.goto(url, wait_until="domcontentloaded", timeout=config.NAVIGATION_TIMEOUT_MS)
    detail_page.wait_for_timeout(config.PAGE_LOAD_PAUSE_MS)
    return detail_page


def write_csv(rows: Iterable[dict], fieldnames: list[str], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            normalized = {}
            for key in fieldnames:
                value = row.get(key, "")
                if isinstance(value, (dict, list)):
                    normalized[key] = json.dumps(value, ensure_ascii=True, sort_keys=True)
                else:
                    normalized[key] = value
            writer.writerow(normalized)

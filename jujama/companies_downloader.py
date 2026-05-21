#!/usr/bin/env python3
"""Live Playwright exporter for Jujama companies."""

from __future__ import annotations

import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .common import (
    click_next_page,
    get_query_param,
    get_manual_page,
    get_total_pages,
    launch_browser,
    setup_logging,
    unique_visible_hrefs,
    wait_for_links,
    write_csv,
)

DETAIL_LINK_SELECTOR = "#divContent .card-list__profile-name a[href*='/Exhibitors/Details?id=']"
EXPECTED_URL_FRAGMENTS = ("/Organization/List", "/Exhibitors/List")
READY_WAIT_TIMEOUT_S = 600
HEADLESS_DEFAULT_LIST_PATH = "/Exhibitors/List"
CSV_FLUSH_EVERY = 25
CSV_HEADERS = [
    "Company Name",
    "Company ID",
    "Detail URL",
    "Profile Image URL",
    "Location",
    "About",
    "Website URL",
    "LinkedIn URL",
    "Twitter/X URL",
    "Facebook URL",
    "Other Social URLs JSON",
    "Attendee Names",
    "Attendees JSON",
    "Exported At",
]


def wait_for_company_list(page) -> None:
    if not any(fragment in page.url for fragment in EXPECTED_URL_FRAGMENTS):
        logging.warning(
            "Current page is %s; expected a Jujama companies list page, but continuing because selectors may still match.",
            page.url,
        )
    wait_for_links(page, DETAIL_LINK_SELECTOR)


def extract_company_list_urls(page) -> list[str]:
    return unique_visible_hrefs(page, DETAIL_LINK_SELECTOR)


def _load_company_tab(detail_page, tab_name: str, expected_selector: str) -> None:
    previous_marker = (
        detail_page.locator("#divDetailsContent").inner_text()
        if detail_page.locator("#divDetailsContent").count()
        else ""
    )
    detail_page.evaluate(
        """(tabName) => {
            if (typeof LoadContent === 'function') {
                LoadContent(tabName);
                return;
            }
            const link = document.querySelector(`#lnk${tabName}`);
            if (link) link.click();
        }""",
        tab_name,
    )
    detail_page.wait_for_timeout(150)
    try:
        detail_page.wait_for_function(
            """(payload) => {
                const [selector, previous] = payload;
                const target = document.querySelector(selector);
                const content = document.querySelector('#divDetailsContent');
                return !!target && !!content && (!previous || (content.innerText || '').trim() !== previous.trim());
            }""",
            [expected_selector, previous_marker],
            timeout=config.NAVIGATION_TIMEOUT_MS,
        )
    except Exception:
        detail_page.wait_for_selector(expected_selector, timeout=config.DEFAULT_TIMEOUT_MS)
    detail_page.wait_for_timeout(150)


def scrape_company_detail(context, url: str, detail_page=None) -> dict:
    owns_page = detail_page is None
    detail_page = detail_page or context.new_page()
    detail_page.set_default_timeout(config.DEFAULT_TIMEOUT_MS)
    try:
        detail_page.goto(url, wait_until="domcontentloaded", timeout=config.NAVIGATION_TIMEOUT_MS)
        detail_page.wait_for_timeout(200)
        detail_page.wait_for_selector(".card-list__profile-name")
        _load_company_tab(detail_page, "About", "#divDetailsContent")
        payload = detail_page.evaluate(
            r"""() => {
                const clean = (value) => (value || '').replace(/\s+/g, ' ').trim();
                const decodeHtml = (html) => {
                    const node = document.createElement('div');
                    node.innerHTML = html || '';
                    return clean(node.textContent || '');
                };
                const profile = document.querySelector('.card-list__profile.inline-items');
                const name = clean(profile?.querySelector('.card-list__profile-name')?.textContent || '');
                const paragraph = profile?.querySelector('p');
                let location = '';
                if (paragraph) {
                    const parts = paragraph.innerHTML
                        .split(/<br\s*\/?>/i)
                        .map((part) => decodeHtml(part))
                        .filter(Boolean)
                        .filter((part) => part !== name);
                    location = parts.join(', ');
                }

                const socials = {
                    linkedin_url: '',
                    twitter_url: '',
                    facebook_url: '',
                    other_social_urls: [],
                };
                document.querySelectorAll('#divDetailsContent ul.socials a[href]').forEach((anchor) => {
                    const href = anchor.href || anchor.getAttribute('href') || '';
                    const lower = href.toLowerCase();
                    if (!href) return;
                    if (lower.includes('linkedin.com') && !socials.linkedin_url) {
                        socials.linkedin_url = href;
                    } else if ((lower.includes('twitter.com') || lower.includes('x.com')) && !socials.twitter_url) {
                        socials.twitter_url = href;
                    } else if (lower.includes('facebook.com') && !socials.facebook_url) {
                        socials.facebook_url = href;
                    } else if (!socials.other_social_urls.includes(href)) {
                        socials.other_social_urls.push(href);
                    }
                });

                return {
                    company_name: name,
                    image_url: document.querySelector('.company__profile img, .card-list__profile-image img')?.src || '',
                    location,
                    about: clean(document.querySelector('#divDetailsContent .profile-info')?.textContent || ''),
                    website_url: document.querySelector('#divDetailsContent a.btn.btn-primary.btn-100[href]')?.href || '',
                    linkedin_url: socials.linkedin_url,
                    twitter_url: socials.twitter_url,
                    facebook_url: socials.facebook_url,
                    other_social_urls: socials.other_social_urls,
                };
            }"""
        )
        attendees = []
        if detail_page.locator("#lnkAttendees").count() > 0:
            try:
                _load_company_tab(detail_page, "Attendees", "#divDetailsContent .notification-list, #divDetailsContent p")
                attendees = detail_page.evaluate(
                    r"""() => {
                        const clean = (value) => (value || '').replace(/\s+/g, ' ').trim();
                        return Array.from(document.querySelectorAll('#divDetailsContent ul.notification-list li')).map((item) => {
                            const nameAnchor = item.querySelector('.notification-friend[href]');
                            const roleText = clean(item.querySelector('.chat-message-item')?.textContent || '');
                            return {
                                name: clean(nameAnchor?.textContent || ''),
                                role: roleText,
                                attendee_url: nameAnchor?.href || '',
                                person_id: (() => {
                                    const href = nameAnchor?.href || '';
                                    const match = href.match(/[?&]personId=(\d+)/i);
                                    return match ? match[1] : '';
                                })(),
                                image_url: item.querySelector('.author-thumb img')?.src || '',
                            };
                        }).filter((item) => item.name);
                    }"""
                )
            except Exception:
                attendees = []
        exported_at = datetime.now(timezone.utc).isoformat()
        return {
            "Company Name": payload.get("company_name", ""),
            "Company ID": get_query_param(url, "id"),
            "Detail URL": url,
            "Profile Image URL": payload.get("image_url", ""),
            "Location": payload.get("location", ""),
            "About": payload.get("about", ""),
            "Website URL": payload.get("website_url", ""),
            "LinkedIn URL": payload.get("linkedin_url", ""),
            "Twitter/X URL": payload.get("twitter_url", ""),
            "Facebook URL": payload.get("facebook_url", ""),
            "Other Social URLs JSON": payload.get("other_social_urls", []),
            "Attendee Names": ", ".join(item.get("name", "") for item in attendees if item.get("name")),
            "Attendees JSON": attendees,
            "Exported At": exported_at,
        }
    finally:
        if owns_page:
            detail_page.close()


def run_live_capture(page, output_dir: Path, test_one: bool = False) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "jujama_companies.csv"
    records = []
    seen = set()

    wait_for_company_list(page)
    total_pages = get_total_pages(page)
    logging.info("Companies page detected. Scraping up to %d page(s).", total_pages)

    detail_page = page.context.new_page()
    detail_page.set_default_timeout(config.DEFAULT_TIMEOUT_MS)
    try:
        page_number = 1
        while True:
            urls = extract_company_list_urls(page)
            logging.info("Found %d company detail link(s) on page %d/%d.", len(urls), page_number, total_pages)
            for url in urls:
                key = get_query_param(url, "id") or url
                if key in seen:
                    continue
                seen.add(key)
                record = scrape_company_detail(page.context, url, detail_page=detail_page)
                records.append(record)
                if len(records) % CSV_FLUSH_EVERY == 0:
                    write_csv(records, CSV_HEADERS, output_path)
                logging.info("Captured company %s", record.get("Company Name", url))
                if test_one:
                    write_csv(records, CSV_HEADERS, output_path)
                    return output_path

            if page_number >= total_pages:
                break
            if not click_next_page(page, expected_page=page_number + 1):
                logging.warning("Unable to click Next from companies page %d; stopping early.", page_number)
                break
            wait_for_links(page, DETAIL_LINK_SELECTOR)
            page_number += 1
    finally:
        detail_page.close()

    write_csv(records, CSV_HEADERS, output_path)
    return output_path


def run_manual_session(output_dir: Path, headless: bool = False, test_one: bool = False) -> Path:
    pw, context, page = launch_browser(headless=headless)
    try:
        print("Browser ready. Log in if needed, navigate to the Jujama Companies page, then press Enter.")
        if sys.stdin.isatty():
            input()
        else:
            # In non-interactive launchers, stdin is not available; wait for the
            # user to move the browser to the Companies page instead.
            logging.info("stdin not interactive; waiting for Companies page to become ready.")
            if headless and not any(fragment in page.url for fragment in EXPECTED_URL_FRAGMENTS):
                target_url = f"{config.BASE_URL.rstrip('/')}{HEADLESS_DEFAULT_LIST_PATH}"
                logging.info("Headless mode: navigating to %s", target_url)
                page.goto(target_url, wait_until="domcontentloaded", timeout=config.NAVIGATION_TIMEOUT_MS)
            deadline = time.monotonic() + READY_WAIT_TIMEOUT_S
            while time.monotonic() < deadline:
                candidate = get_manual_page(context, page)
                if any(fragment in candidate.url for fragment in EXPECTED_URL_FRAGMENTS):
                    if candidate.locator(DETAIL_LINK_SELECTOR).count() > 0:
                        break
                candidate.wait_for_timeout(1000)
            else:
                raise TimeoutError(
                    "Timed out waiting for the Companies list page. "
                    "Open Jujama Companies list in the launched browser and rerun."
                )
        page = get_manual_page(context, page)
        return run_live_capture(page, output_dir=output_dir, test_one=test_one)
    finally:
        context.close()
        pw.stop()


def main(output_dir=None, headless: bool = False, test_one: bool = False):
    output_dir = Path(output_dir or config.COMPANIES_OUTPUT_DIR)
    log_path = output_dir / "jujama_companies.log"
    setup_logging(log_path)
    result = run_manual_session(output_dir=output_dir, headless=headless, test_one=test_one)
    logging.info("Companies export written to %s", result)
    return result

#!/usr/bin/env python3
"""Live Playwright exporter for Jujama attendees."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .common import (
    click_next_page,
    get_query_param,
    get_manual_page,
    get_total_pages,
    launch_browser,
    open_detail_page,
    setup_logging,
    unique_visible_hrefs,
    wait_for_links,
    write_csv,
)

DETAIL_LINK_SELECTOR = "#divContent .card-list__profile-name a[href*='/Attendee/Details?PersonId=']"
EXPECTED_URL_FRAGMENTS = ("/Attendee/List",)
CSV_HEADERS = [
    "Attendee Name",
    "Person ID",
    "Company ID",
    "Title",
    "Company Name",
    "Company Profile URL",
    "Detail URL",
    "Profile Image URL",
    "Attendance Type",
    "Location",
    "LinkedIn URL",
    "About",
    "Profile Attributes JSON",
    "Exported At",
]


def wait_for_attendee_list(page) -> None:
    if not any(fragment in page.url for fragment in EXPECTED_URL_FRAGMENTS):
        logging.warning(
            "Current page is %s; expected a Jujama attendee list page, but continuing because selectors may still match.",
            page.url,
        )
    wait_for_links(page, DETAIL_LINK_SELECTOR)


def extract_attendee_list_urls(page) -> list[str]:
    return unique_visible_hrefs(page, DETAIL_LINK_SELECTOR)


def scrape_attendee_detail(context, url: str) -> dict:
    detail_page = open_detail_page(context, url)
    try:
        detail_page.wait_for_selector(".card-list__profile-name")
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
                const container = profile?.querySelector('.pl-2') || profile;
                const title = clean(container?.querySelector('em')?.textContent || '');
                const companyAnchor = container?.querySelector('a[href*="/Organization/CompanyProfile"]');
                const companyName = clean(companyAnchor?.textContent || '');
                const companyProfileUrl = companyAnchor?.href || '';
                const attendanceType = clean(profile?.querySelector('.icon-overlay title')?.textContent || '');

                let location = '';
                if (container) {
                    const parts = container.innerHTML
                        .split(/<br\s*\/?>/i)
                        .map((part) => decodeHtml(part))
                        .filter(Boolean);
                    const filtered = parts.filter((part) => {
                        if (part === name || part === title || part === companyName) return false;
                        if (companyName && part === `at ${companyName}`) return false;
                        if (part.includes('linkedin.com')) return false;
                        return true;
                    });
                    location = filtered.join(', ');
                }

                const attributes = {};
                document.querySelectorAll('#divAbout ul li').forEach((item) => {
                    const label = clean((item.querySelector('.title')?.textContent || '').replace(/:+$/g, ''));
                    const value = clean(item.querySelector('.text')?.textContent || '');
                    if (label && value) {
                        attributes[label] = value;
                    }
                });

                return {
                    attendee_name: name,
                    title,
                    company_name: companyName,
                    company_profile_url: companyProfileUrl,
                    image_url: document.querySelector('.card-list__profile-image img')?.src || '',
                    attendance_type: attendanceType,
                    location,
                    linkedin_url: document.querySelector('a[href*="linkedin.com"]')?.href || '',
                    about: clean(document.querySelector('#divAbout p')?.textContent || ''),
                    attributes,
                };
            }"""
        )
        exported_at = datetime.now(timezone.utc).isoformat()
        return {
            "Attendee Name": payload.get("attendee_name", ""),
            "Person ID": get_query_param(url, "PersonId"),
            "Company ID": get_query_param(url, "CompanyId"),
            "Title": payload.get("title", ""),
            "Company Name": payload.get("company_name", ""),
            "Company Profile URL": payload.get("company_profile_url", ""),
            "Detail URL": url,
            "Profile Image URL": payload.get("image_url", ""),
            "Attendance Type": payload.get("attendance_type", ""),
            "Location": payload.get("location", ""),
            "LinkedIn URL": payload.get("linkedin_url", ""),
            "About": payload.get("about", ""),
            "Profile Attributes JSON": payload.get("attributes", {}),
            "Exported At": exported_at,
        }
    finally:
        detail_page.close()


def run_live_capture(page, output_dir: Path, test_one: bool = False) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "jujama_attendees.csv"
    records = []
    seen = set()

    wait_for_attendee_list(page)
    total_pages = get_total_pages(page)
    logging.info("Attendee page detected. Scraping up to %d page(s).", total_pages)

    page_number = 1
    while True:
        urls = extract_attendee_list_urls(page)
        logging.info("Found %d attendee detail link(s) on page %d/%d.", len(urls), page_number, total_pages)
        for url in urls:
            key = get_query_param(url, "PersonId") or url
            if key in seen:
                continue
            seen.add(key)
            record = scrape_attendee_detail(page.context, url)
            records.append(record)
            write_csv(records, CSV_HEADERS, output_path)
            logging.info("Captured attendee %s", record.get("Attendee Name", url))
            if test_one:
                return output_path

        if page_number >= total_pages:
            break
        if not click_next_page(page, expected_page=page_number + 1):
            logging.warning("Unable to click Next from attendee page %d; stopping early.", page_number)
            break
        wait_for_links(page, DETAIL_LINK_SELECTOR)
        page_number += 1

    write_csv(records, CSV_HEADERS, output_path)
    return output_path


def run_manual_session(output_dir: Path, headless: bool = False, test_one: bool = False) -> Path:
    pw, context, page = launch_browser(headless=headless)
    try:
        print("Browser ready. Log in if needed, navigate to the Jujama Attendees page, then press Enter.")
        input()
        page = get_manual_page(context, page)
        return run_live_capture(page, output_dir=output_dir, test_one=test_one)
    finally:
        context.close()
        pw.stop()


def main(output_dir=None, headless: bool = False, test_one: bool = False):
    output_dir = Path(output_dir or config.ATTENDEES_OUTPUT_DIR)
    log_path = output_dir / "jujama_attendees.log"
    setup_logging(log_path)
    result = run_manual_session(output_dir=output_dir, headless=headless, test_one=test_one)
    logging.info("Attendee export written to %s", result)
    return result

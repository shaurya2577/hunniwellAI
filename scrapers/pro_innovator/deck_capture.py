#!/usr/bin/env python3
"""Live deck viewer opening and screenshot capture helpers."""

import re
from pathlib import Path

from scrapers.pro_innovator import config
from scrapers.pro_innovator.pdf_build import build_pdf_from_images


def sanitize_filename(name: str, max_length: int = 120) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]+', "_", (name or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip(".")
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip()
    return cleaned or "Unknown"


def _company_cell_for_row(page, row_id: str):
    return page.locator(
        '.ag-pinned-left-cols-container [role="row"][row-id="%s"] [role="gridcell"][col-id="company.name"]'
        % row_id
    ).first


def ensure_row_visible(page, row_id: str):
    company_cell = _company_cell_for_row(page, row_id)
    if company_cell.count() > 0:
        return company_cell

    active_selector = None
    for selector in (".ag-body-viewport", ".ag-center-cols-viewport"):
        if page.locator(selector).count() > 0:
            active_selector = selector
            break
    if not active_selector:
        return company_cell

    page.evaluate(
        """(selector) => {
            const viewport = document.querySelector(selector);
            if (viewport) viewport.scrollTop = 0;
        }""",
        active_selector,
    )
    page.wait_for_timeout(config.GRID_SCROLL_PAUSE_MS)

    previous_top = -1
    for _ in range(config.MAX_GRID_SCROLLS):
        company_cell = _company_cell_for_row(page, row_id)
        if company_cell.count() > 0:
            return company_cell
        next_top = page.evaluate(
            """({ selector, rowId }) => {
                const viewport = document.querySelector(selector);
                if (!viewport) return -1;
                const row = document.querySelector('[role="row"][row-id="' + rowId + '"]');
                if (row) {
                    row.scrollIntoView({ block: 'center' });
                    return viewport.scrollTop;
                }
                viewport.scrollTop = viewport.scrollTop + viewport.clientHeight;
                return viewport.scrollTop;
            }""",
            {"selector": active_selector, "rowId": row_id},
        )
        page.wait_for_timeout(config.GRID_SCROLL_PAUSE_MS)
        if next_top == previous_top:
            break
        previous_top = next_top
    return _company_cell_for_row(page, row_id)


def _nearest_view_trigger(page, row_id: str):
    locator = page.locator("button, a").filter(has_text=re.compile(r"^View$", re.I))
    count = locator.count()
    if count == 0:
        return None
    nearest_index = page.evaluate(
        """(rowId) => {
            const row = document.querySelector('[role="row"][row-id="' + rowId + '"]');
            if (!row) return -1;
            const rowRect = row.getBoundingClientRect();
            const rowCenter = rowRect.top + rowRect.height / 2;
            const items = [...document.querySelectorAll('button, a')]
              .filter((el) => (el.innerText || el.textContent || '').trim().toLowerCase() === 'view')
              .filter((el) => {
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
              });
            if (!items.length) return -1;
            let bestIndex = 0;
            let bestDistance = Infinity;
            items.forEach((el, index) => {
              const rect = el.getBoundingClientRect();
              const center = rect.top + rect.height / 2;
              const distance = Math.abs(center - rowCenter);
              if (distance < bestDistance) {
                bestDistance = distance;
                bestIndex = index;
              }
            });
            return bestIndex;
        }""",
        row_id,
    )
    if nearest_index < 0 or nearest_index >= count:
        return None
    return locator.nth(nearest_index)


def open_deck_viewer(page, row_id: str):
    """Open the deck viewer for a company and return the viewer page."""
    company_cell = ensure_row_visible(page, row_id)
    if company_cell.count() == 0:
        raise RuntimeError("Could not find row %s in the current grid." % row_id)

    company_cell.click(timeout=5_000)
    page.wait_for_timeout(500)
    trigger = _nearest_view_trigger(page, row_id)
    if trigger is None:
        raise RuntimeError("Could not find a View trigger near row %s" % row_id)

    original_url = page.url
    existing_pages = set(page.context.pages)
    try:
        with page.context.expect_page(timeout=10_000) as popup_info:
            trigger.click(timeout=10_000)
        viewer_page = popup_info.value
        viewer_page.wait_for_load_state("domcontentloaded", timeout=20_000)
        return viewer_page, original_url
    except Exception:
        trigger.click(timeout=10_000)
        page.wait_for_timeout(1_000)
        new_pages = [candidate for candidate in page.context.pages if candidate not in existing_pages]
        if new_pages:
            viewer_page = new_pages[-1]
            viewer_page.wait_for_load_state("domcontentloaded", timeout=20_000)
            return viewer_page, original_url
        page.wait_for_load_state("domcontentloaded", timeout=20_000)
        return page, original_url


def _wait_for_rendered_element(viewer_page, page_el) -> bool:
    for _ in range(20):
        try:
            if page_el.evaluate(
                """(el) => {
                    const rect = el.getBoundingClientRect();
                    const child = el.querySelector('img, canvas, svg');
                    if (!child) return rect.width > 0 && rect.height > 0;
                    const childRect = child.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0 && childRect.width > 0 && childRect.height > 0;
                }"""
            ):
                return True
        except Exception:
            pass
        viewer_page.wait_for_timeout(250)
    return False


def _capture_google_drive_pages(viewer_page, artifact_dir: Path) -> list:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    container_selectors = [
        ".ndfHFb-c4YZDc-cYSp0e-DARUcf",
        '[aria-label^="Page "]',
        "canvas",
        "img",
    ]

    for selector in container_selectors:
        locator = viewer_page.locator(selector)
        if locator.count() == 0:
            continue

        images = []
        stable_count = 0
        prev_count = 0
        for _ in range(80):
            count = locator.count()
            if count == prev_count and count > 0:
                stable_count += 1
            else:
                stable_count = 0
            prev_count = count
            viewer_page.mouse.wheel(0, 2_000)
            viewer_page.wait_for_timeout(500)
            if stable_count >= 3:
                break

        viewer_page.evaluate("window.scrollTo(0, 0)")
        viewer_page.wait_for_timeout(500)
        total = locator.count()
        for idx in range(total):
            page_el = locator.nth(idx)
            try:
                page_el.scroll_into_view_if_needed(timeout=5_000)
                viewer_page.wait_for_timeout(250)
                if not _wait_for_rendered_element(viewer_page, page_el):
                    continue
                image_path = artifact_dir / ("page_%03d.png" % (idx + 1))
                page_el.screenshot(path=str(image_path))
                images.append(str(image_path))
            except Exception:
                continue
        if images:
            return images
    fallback = artifact_dir / "viewer_full.png"
    viewer_page.screenshot(path=str(fallback), full_page=True)
    return [str(fallback)] if fallback.exists() else []
    return []


def capture_company_deck(page, record: dict, output_dir) -> dict:
    """
    Open the deck viewer, capture rendered pages, and rebuild a PDF.

    The first version optimizes for robust full-page capture. Cropping can be
    added later inside this module without changing the runner contract.
    """
    company_name = record["Company Name"]
    safe_name = sanitize_filename(company_name)
    company_dir = Path(output_dir) / safe_name
    artifact_dir = company_dir / "pages"
    company_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "company_name": company_name,
        "row_id": record.get("Row ID", ""),
        "status": "failed",
        "page_count": 0,
        "pdf_path": "",
        "source_url": "",
        "error": "",
    }

    viewer_page = None
    original_url = page.url
    try:
        viewer_page, original_url = open_deck_viewer(page, record.get("Row ID", ""))
        result["source_url"] = viewer_page.url
        image_paths = _capture_google_drive_pages(viewer_page, artifact_dir)
        if not image_paths:
            raise RuntimeError("Viewer opened but no page images were captured.")

        pdf_path = company_dir / ("%s.pdf" % safe_name)
        build_pdf_from_images(image_paths, pdf_path)

        result["status"] = "captured"
        result["page_count"] = len(image_paths)
        result["pdf_path"] = str(pdf_path)
        return result
    except Exception as exc:
        result["error"] = str(exc)
        return result
    finally:
        if viewer_page is not None and viewer_page is not page:
            try:
                viewer_page.close()
            except Exception:
                pass
        elif page.url != original_url:
            try:
                page.goto(original_url, wait_until="domcontentloaded", timeout=20_000)
            except Exception:
                pass

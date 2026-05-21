#!/usr/bin/env python3
"""
Verify that the RESI output directory is writable and that Playwright
can save downloads there. Run from project root: python tests/test_download.py
"""
import os
import sys
from pathlib import Path

# Add project root so we can import platforms.resi.config
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from platforms.resi import config

# Small PDF (W3C dummy PDF) - we fetch and write to OUTPUT_DIR
TEST_PDF_URL = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
TEST_FILENAME = "test_download_playwright.pdf"


def test_output_dir_writable():
    """Check OUTPUT_DIR exists and we can write a file into it."""
    out = os.path.abspath(config.OUTPUT_DIR)
    os.makedirs(out, exist_ok=True)
    test_path = os.path.join(out, "test_write.txt")
    with open(test_path, "w") as f:
        f.write("ok")
    os.remove(test_path)
    print(f"OK: OUTPUT_DIR is writable: {out}")
    return out


def test_playwright_download():
    """Fetch a PDF via Playwright and write to OUTPUT_DIR; verify path and write work."""
    from playwright.sync_api import sync_playwright

    out = os.path.abspath(config.OUTPUT_DIR)
    os.makedirs(out, exist_ok=True)
    save_path = os.path.join(out, TEST_FILENAME)

    if os.path.isfile(save_path):
        os.remove(save_path)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context()
        context.set_default_timeout(15_000)
        page = context.new_page()

        # Fetch PDF via request (same as browser would get) and write to OUTPUT_DIR
        response = page.request.get(TEST_PDF_URL, timeout=15_000)
        if response.status != 200:
            print(f"FAIL: GET {TEST_PDF_URL} returned {response.status}")
            return False
        body = response.body()
        with open(save_path, "wb") as f:
            f.write(body)

        context.close()
        browser.close()

    if os.path.isfile(save_path) and os.path.getsize(save_path) > 0:
        print(f"OK: Wrote PDF to {save_path} ({os.path.getsize(save_path)} bytes)")
        return True
    print(f"FAIL: File missing or empty: {save_path}")
    return False


def main():
    print("Testing RESI download output...")
    print(f"OUTPUT_DIR = {os.path.abspath(config.OUTPUT_DIR)}")
    test_output_dir_writable()
    ok = test_playwright_download()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

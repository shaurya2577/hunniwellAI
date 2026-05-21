#!/usr/bin/env python3
"""Configuration for live Pro Innovator scraping and deck capture."""

import os

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

BASE_URL = os.environ.get("PRO_INNOVATOR_BASE_URL", "https://pro.innovator.org")
DEFAULT_OUTPUT_DIR = os.environ.get(
    "PRO_INNOVATOR_OUTPUT_DIR",
    os.path.join(os.path.expanduser("~"), "Downloads", "Innovator", "pro_innovator"),
)

BROWSER_USER_DATA_DIR = os.path.join(_THIS_DIR, "pro_innovator_browser_profile")
DEFAULT_TIMEOUT_MS = 15_000
NAVIGATION_TIMEOUT_MS = 30_000
VIEWER_RENDER_TIMEOUT_MS = 45_000
GRID_SCROLL_PAUSE_MS = 500
MAX_GRID_SCROLLS = 50
MAX_VIEWER_SCROLLS = 80

CSV_HEADERS = (
    "Company Name",
    "Row ID",
    "One-liner",
    "Development Stage",
    "Total Equity Funding",
    "Next Round",
    "Preferred Pitch Location",
    "Deck Status",
    "Deck Source URL",
    "Rebuilt PDF Path",
)

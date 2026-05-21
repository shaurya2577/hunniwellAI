#!/usr/bin/env python3
"""Configuration for Jujama live profile exporters."""

from __future__ import annotations

import os
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent

BASE_URL = os.environ.get("JUJAMA_BASE_URL", "https://connect-v3.jujama.com")
DEFAULT_OUTPUT_ROOT = Path(
    os.environ.get(
        "JUJAMA_OUTPUT_DIR",
        str(Path.home() / "Downloads" / "Jujama"),
    )
)
COMPANIES_OUTPUT_DIR = DEFAULT_OUTPUT_ROOT / "jujama_companies"
ATTENDEES_OUTPUT_DIR = DEFAULT_OUTPUT_ROOT / "jujama_attendees"

BROWSER_USER_DATA_DIR = _THIS_DIR / "jujama_browser_profile"
DEFAULT_TIMEOUT_MS = 15_000
NAVIGATION_TIMEOUT_MS = 30_000
PAGE_LOAD_PAUSE_MS = 1_000
MAX_EMPTY_PAGES = 2

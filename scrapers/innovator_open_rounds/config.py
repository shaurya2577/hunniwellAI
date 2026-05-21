"""
Configuration for Innovator Portal (pro.innovator.org) Open Rounds pitch deck downloader.
"""
import os
import platform

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# Innovator Portal base URL
BASE_URL = os.environ.get("INNOVATOR_BASE_URL", "https://pro.innovator.org")
OPEN_ROUNDS_PATH = "/open-rounds"
OPEN_ROUNDS_URL = BASE_URL.rstrip("/") + OPEN_ROUNDS_PATH

# Output: default ~/Downloads/Innovator or INNOVATOR_OUTPUT_DIR
if os.environ.get("INNOVATOR_OUTPUT_DIR"):
    OUTPUT_DIR = os.environ["INNOVATOR_OUTPUT_DIR"]
else:
    OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "Innovator")

# Browser profile for persistent login (optional)
BROWSER_USER_DATA_DIR = os.path.join(_THIS_DIR, "innovator_browser_profile")

# Storage state for Playwright (one-time save after login)
RECORDINGS_DIR = os.path.join(_THIS_DIR, "recordings")
STORAGE_STATE_PATH = os.path.join(RECORDINGS_DIR, "auth.json")

# Timeouts (ms)
NAVIGATION_TIMEOUT = 30_000
DEFAULT_TIMEOUT = 15_000
MACRO_STEP_TIMEOUT = 25_000

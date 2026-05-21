"""
Configuration for RESI (HelloPartnering) Pitch Deck Bulk Downloader.
"""
import os
import platform

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# RESI / HelloPartnering base URL (adjust if different)
BASE_URL = os.environ.get("RESI_BASE_URL", "https://www.hellopartnering.com")
# Investor search (--investor mode)
INVESTOR_SEARCH_URL = os.environ.get(
    "RESI_INVESTOR_SEARCH_URL",
    "https://www.hellopartnering.com/search/search_investor",
)

# Login (--auto mode). Do not commit credentials. Set RESI_USERNAME / RESI_PASSWORD or enter when prompted.
RESI_USERNAME = os.environ.get("RESI_USERNAME")
RESI_PASSWORD = os.environ.get("RESI_PASSWORD")
# Direct RESI JPM login URL (avoids dropdown; use if click-through fails)
RESI_JPM_LOGIN_URL = os.environ.get("RESI_JPM_LOGIN_URL", "https://www.hellopartnering.com/login/index/RSIJ26")

# Output: single folder for all decks. Default: macOS ~/Downloads/RESI or Windows Downloads\RESI
if os.environ.get("RESI_OUTPUT_DIR"):
    OUTPUT_DIR = os.environ["RESI_OUTPUT_DIR"]
else:
    if platform.system() == "Darwin":
        OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "RESI")
    else:
        OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "RESI")

# Browser profile for persistent login (under this package)
BROWSER_USER_DATA_DIR = os.path.join(_THIS_DIR, "resi_browser_profile")

# Storage state for Playwright codegen (one-time: save after login so codegen can --load-storage)
RECORDINGS_DIR = os.path.join(_THIS_DIR, "recordings")
STORAGE_STATE_PATH = os.path.join(RECORDINGS_DIR, "auth.json")

# Timeouts (ms for Playwright)
NAVIGATION_TIMEOUT = 30_000
DOWNLOAD_TIMEOUT = 60_000
DEFAULT_TIMEOUT = 15_000
MACRO_STEP_TIMEOUT = 25_000  # modal/popup steps (MEDIA tab, PDF link, Download)

# Supported pitch deck file extensions
SUPPORTED_EXTENSIONS = (".pdf", ".ppt", ".pptx")

# File name suffixes (single underscore per plan)
RESI_PROFILE_SUFFIX = "_RESI.pdf"
SLIDEDECK_SUFFIX = "_SLIDEDECK.pdf"

# Target sectors (user manually selects these in RESI; script does not change filter)
TARGET_SECTORS = [
    "Biotechnology - Therapeutics and Diagnostics",
    "Biotechnology - R&D Services",
    "Biotechnology - Other",
    "Pharma (fully integrated)",
    "Medical Technology",
    "HealthTech",
]

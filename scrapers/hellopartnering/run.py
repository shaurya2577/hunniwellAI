#!/usr/bin/env python3
"""
Entrypoint for RESI (HelloPartnering) pitch deck bulk downloader.

Run from repo root:
  python run_resi.py [--save-storage | --auto | --auto --all-sectors | --test-one] [options]
"""
import sys
from pathlib import Path

# Ensure project root is on path
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scrapers.hellopartnering.downloader import main

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Entrypoint for Innovator Portal (pro.innovator.org) Open Rounds pitch deck index builder.

Run from repo root:
  python run_innovator.py [--save-storage | --manual | --test-one] [options]
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scrapers.innovator_open_rounds.downloader import main

if __name__ == "__main__":
    main()

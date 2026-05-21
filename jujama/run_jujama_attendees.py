#!/usr/bin/env python3
"""Entrypoint for the Jujama attendees exporter."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from jujama.attendees_downloader import main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Jujama: export attendee profiles from the live Attendees page into CSV."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for jujama_attendees.csv and logs",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Launch the browser headless",
    )
    parser.add_argument(
        "--test-one",
        action="store_true",
        help="Capture only the first attendee",
    )
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    main(output_dir=args.output_dir, headless=args.headless, test_one=args.test_one)

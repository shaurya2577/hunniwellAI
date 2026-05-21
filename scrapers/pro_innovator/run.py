#!/usr/bin/env python3
"""
Entrypoint for Pro Innovator (Applications/cohort) extraction and live capture.

Pro Innovator = Applications -> APAC -> Cohort companies (vs Open Rounds).
"""
import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def build_parser():
    parser = argparse.ArgumentParser(
        description="Pro Innovator: extract saved HTML or run the live Applications-page capture flow."
    )
    parser.add_argument(
        "--extract",
        nargs=2,
        metavar=("HTML_PATH", "CSV_PATH"),
        help="Extract companies from saved Applications HTML into CSV",
    )
    parser.add_argument(
        "--radar",
        nargs="*",
        metavar="HTML_PATH",
        help="Extract companies from saved Radar Forum HTML(s) into CSV. "
        "Defaults to ~/Scratch/radar/Innovator Portal*.html",
    )
    parser.add_argument(
        "--radar-output",
        type=Path,
        help="Output CSV for --radar (default: radar_companies.csv next to the module)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run the live Playwright flow from the currently opened Applications page",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Backward-compatible alias for --live",
    )
    parser.add_argument(
        "--csv-only",
        action="store_true",
        help="Only scrape the Applications grid into CSV; skip deck capture",
    )
    parser.add_argument(
        "--test-one",
        action="store_true",
        help="Process only the first company during deck capture",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Launch the browser headless",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for CSV, manifests, and rebuilt PDFs",
    )
    parser.add_argument(
        "--resume-manifest",
        type=Path,
        help="Resume a prior live run from this manifest JSON",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.extract:
        from scrapers.pro_innovator.innovator_portal_reader import (
            parse_saved_pro_innovator_html,
            write_companies_to_csv,
        )
        html_path, csv_path = args.extract
        if not Path(html_path).exists():
            print(f"Error: HTML file not found: {html_path}")
            sys.exit(1)
        companies = parse_saved_pro_innovator_html(html_path)
        write_companies_to_csv(companies, str(csv_path))
        return

    if args.radar is not None:
        from scrapers.pro_innovator.radar_portal_reader import (
            merge_records,
            parse_radar_html,
            write_csv,
        )
        html_files = args.radar or None
        if not html_files:
            radar_dir = Path.home() / "Scratch" / "radar"
            html_files = sorted(str(p) for p in radar_dir.glob("Innovator Portal*.html"))
        if not html_files:
            print("No Radar HTML files found.")
            sys.exit(1)
        output = str(args.radar_output) if args.radar_output else str(
            Path(__file__).resolve().parent
            / "platforms" / "innovator" / "pro_innovator" / "radar_companies.csv"
        )
        all_records = []
        for path in html_files:
            if not Path(path).exists():
                print(f"  WARNING: {path} not found, skipping.")
                continue
            records = parse_radar_html(path)
            print(f"  {Path(path).name}: {len(records)} companies, "
                  f"{sum(1 for r in records.values() if r.get('Year Founded'))} with detail")
            all_records.append(records)
        write_csv(merge_records(all_records), output)
        return

    if args.live or args.download:
        from scrapers.pro_innovator.run_downloader import main as live_main

        live_main(
            output_dir=args.output_dir,
            headless=args.headless,
            csv_only=args.csv_only,
            test_one=args.test_one,
            resume_manifest=args.resume_manifest,
        )
        return

    parser.print_help()
    print("\nExample:")
    print("  python run_pro_innovator.py --extract saved.html pro_innovator_companies.csv")
    print("  python run_pro_innovator.py --radar                          # auto-find Radar HTMLs")
    print("  python run_pro_innovator.py --radar page1.html page2.html -o radar.csv")
    print("  python run_pro_innovator.py --live --csv-only")
    print("  python run_pro_innovator.py --live --test-one")


if __name__ == "__main__":
    main()

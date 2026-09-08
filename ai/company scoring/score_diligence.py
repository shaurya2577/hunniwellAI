#!/usr/bin/env python3
"""
score_diligence.py — Project Atlas due-diligence scoring pipeline

For each company data room (a folder of documents) under
$HUNNIWELL_COMPANYFILES_ROOT, this script:
  1. Reads all internal docs (PDF / DOCX / PPTX / XLSX / TXT / MD) in the
     company's folder, recursively.
  2. Sends them to Claude along with the Project Atlas scoring rubric
     (scoring_rubric.md).
  3. Claude scores each of the 26 lettered rubric sections (High/Mid/Low
     confidence -> +3/0/-3 points, base 50), with reasoning per section.
  4. Writes a plain-text scorecard into each company folder (or a shared
     --output-dir).

This mirrors the folder-walking / doc-extraction pattern in web_ingest.py,
but does a single scoring call per company instead of a two-step
web-search + report call, and writes NO data to Airtable.

Setup (same venv as ingest.py / web_ingest.py):
    pip install anthropic python-dotenv pypdf python-docx python-pptx openpyxl

Required env vars (same .env as ingest.py):
    ANTHROPIC_API_KEY
    HUNNIWELL_COMPANYFILES_ROOT

Rubric file:
    By default the script looks for scoring_rubric.md in the same directory
    as this script. Override with --rubric /path/to/other_rubric.md.

Run:
    python score_diligence.py                          # score all companies
    python score_diligence.py --event "JPM 2026 (260115)"
    python score_diligence.py --company "Medical 21"
    python score_diligence.py --dry-run                 # print, don't write
    python score_diligence.py --reset-state              # clear skip cache
    python score_diligence.py --output-dir ./scorecards  # collect in one folder
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from pypdf import PdfReader
from docx import Document
from pptx import Presentation

try:
    from openpyxl import load_workbook
    HAVE_XLSX = True
except ImportError:
    HAVE_XLSX = False

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR / ".env")

DEFAULT_ROOT = Path(os.environ.get("HUNNIWELL_COMPANYFILES_ROOT", "~/Documents/Hunniwell")).expanduser()
DEFAULT_RUBRIC = SCRIPT_DIR / "scoring_rubric.md"
STATE_FILE = SCRIPT_DIR / ".score_processed.json"

# Data-room review benefits from a stronger model than the fast enrichment
# pass in web_ingest.py — override with --model if you want to trade off
# cost/speed differently.
CLAUDE_MODEL = "claude-sonnet-4-6"

PER_FILE_CHAR_LIMIT = 120_000    
TOTAL_INTERNAL_CHAR_LIMIT = 1_500_000
MAX_FOLDER_DEPTH = 6  # data rooms are often nested (Financials/, Legal/, Cap Table/, ...)

READABLE_EXTS = {".pdf", ".docx", ".pptx", ".txt", ".md"}
if HAVE_XLSX:
    READABLE_EXTS.add(".xlsx")

RUBRIC_SECTIONS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

# Weighted category structure from the objectified Project Atlas rubric.
# Weights must sum to 1.0; every section A-Z must appear in exactly one
# category (26 sections total). The composite score is computed here in
# Python — not left to the model's arithmetic — for reliability.
CATEGORIES = [
    ("Clinical Need", 0.20, ["C", "D"]),
    ("Technology Differentiation", 0.10, ["I", "T"]),
    ("Regulatory/Development Maturity", 0.15, ["E", "P", "Q", "R"]),
    ("Market/Commercial Strength", 0.15, ["K", "M", "N", "S"]),
    ("Capital Efficiency", 0.10, ["B", "F", "U", "V"]),
    ("Strategic Exit Relevance", 0.20, ["J", "X", "Z"]),
    ("Hygiene (gating/dealbreaker)", 0.10, ["A", "G", "H", "L", "O", "W", "Y"]),
]

assert abs(sum(w for _, w, _ in CATEGORIES) - 1.0) < 1e-9, "Category weights must sum to 1.0"
assert sorted(s for _, _, secs in CATEGORIES for s in secs) == RUBRIC_SECTIONS, \
    "Every section A-Z must be mapped to exactly one category"

# ---------------------------------------------------------------------------
# File extractors
# ---------------------------------------------------------------------------

def extract_pdf(path: Path) -> str:
    try:
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        print(f"  [warn] PDF extract failed for {path.name}: {e}")
        return ""


def extract_docx(path: Path) -> str:
    try:
        doc = Document(str(path))
        parts = [p.text for p in doc.paragraphs if p.text]
        for tbl in doc.tables:
            for row in tbl.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))
        return "\n".join(parts)
    except Exception as e:
        print(f"  [warn] DOCX extract failed for {path.name}: {e}")
        return ""


def extract_pptx(path: Path) -> str:
    try:
        prs = Presentation(str(path))
        parts = []
        for i, slide in enumerate(prs.slides, 1):
            parts.append(f"--- Slide {i} ---")
            for shape in slide.shapes:
                try:
                    if shape.has_text_frame and shape.text_frame.text:
                        parts.append(shape.text_frame.text)
                except Exception:
                    continue
        return "\n".join(parts)
    except Exception as e:
        print(f"  [warn] PPTX extract failed for {path.name}: {e}")
        return ""


def extract_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"  [warn] text read failed for {path.name}: {e}")
        return ""


def extract_xlsx(path: Path) -> str:
    if not HAVE_XLSX:
        return ""
    try:
        wb = load_workbook(str(path), data_only=True, read_only=True)
        parts = []
        for ws in wb.worksheets:
            parts.append(f"--- Sheet: {ws.title} ---")
            row_count = 0
            for row in ws.iter_rows(values_only=True):
                if row_count >= 200:  # cap huge sheets (e.g. cap tables, models)
                    parts.append("... (truncated)")
                    break
                cells = [str(c) for c in row if c is not None]
                if cells:
                    parts.append(" | ".join(cells))
                    row_count += 1
        return "\n".join(parts)
    except Exception as e:
        print(f"  [warn] XLSX extract failed for {path.name}: {e}")
        return ""


EXTRACTORS = {
    ".pdf": extract_pdf,
    ".docx": extract_docx,
    ".pptx": extract_pptx,
    ".txt": extract_text_file,
    ".md": extract_text_file,
    ".xlsx": extract_xlsx,
}


def collect_internal_docs(company_dir: Path) -> list[dict]:
    """Returns list of {filename, text} for all readable files anywhere under
    the company's data-room folder (recursive, depth-capped)."""
    docs = []
    total = 0
    for path in sorted(company_dir.rglob("*")):
        if not path.is_file():
            continue
        if len(path.relative_to(company_dir).parts) > MAX_FOLDER_DEPTH:
            continue
        if path.suffix.lower() not in READABLE_EXTS:
            continue
        text = EXTRACTORS[path.suffix.lower()](path)
        if not text.strip():
            continue
        text = text[:PER_FILE_CHAR_LIMIT]
        docs.append({"filename": path.relative_to(company_dir).as_posix(), "text": text})
        total += len(text)
        if total >= TOTAL_INTERNAL_CHAR_LIMIT:
            print(f"  [warn] hit {TOTAL_INTERNAL_CHAR_LIMIT}-char internal doc cap, some files skipped")
            break
    return docs

# ---------------------------------------------------------------------------
# Claude scoring call
# ---------------------------------------------------------------------------

def build_system_prompt(rubric_text: str) -> str:
    return f"""You are a medtech venture capital due-diligence analyst. Score a
company's data room against the Project Atlas Objective Due Diligence
Scoring Rubric below, using ONLY the internal documents provided to you in
the user message. Do not invent facts or use outside/prior knowledge of
the company. Where a document doesn't state a number the rubric asks for
(e.g. DSO, turnover %, customer concentration %), say so explicitly rather
than estimating or guessing a figure.
RUBRIC:
{rubric_text}

SCORING METHOD (follow exactly):

- Each lettered section (A-Z) contains several named criteria. Score EACH
  criterion Low / Mid / High against the specific thresholds in the
  rubric — not a subjective impression.
- Section-level roll-up: a section is High if a majority of its criteria
  are High and none are Low; Low if a majority of its criteria are Low,
  OR if any criterion marked HARD STOP in the rubric is triggered
  (regardless of the other criteria in that section); otherwise Mid.

- Points per section: score an integer from -3 to +3, based on the
  proportion of criteria that are High vs Mid vs Low within that section.
  High counts as +3, Mid as 0, Low as -3 per criterion; average those
  values across all criteria in the section and round to the nearest
  integer. For example, if a section has 3 criteria scored High, High,
  Mid, the average is (3+3+0)/3 = +2, so the section score is +2. A HARD
  STOP always forces the section to -3, overriding the averaged value.
- Absence of all evidence for a criterion does not automatically count as
  Low for that criterion. Objectively reason about the available
  documents for that criterion.


MISSING DOCUMENTS:
- For every section (A-Z), state whether any document or data point
  needed to score that section's criteria is absent from the data room.
  If nothing is missing for a section, say so explicitly rather than
  omitting it. Use the exact format shown in the OUTPUT FORMAT below
  (one line per section, e.g. "Section B: Business Model Document
  Missing" or "Section A: No documents missing").




OUTPUT FORMAT — follow this exactly, for every section, in order A to Z:
COMPANY: <company name>
FILES REVIEWED: <count>


MISSING DOCCUMENTS: 
	- Example: 
	- Section A : No documents missing 
	- Section B: Business Model Document Missing 



SECTION-BY-SECTION SCORING
A - Intro & Overview
Criteria:
  - <Criterion name>: High | Mid | Low — Evidence: <1 sentence citing specific facts/files, or "No relevant documents found in data room.">
  - <next criterion>: ...
  (list every criterion in this section from the rubric)
HARD STOP triggered: <"None" or the specific criterion + why>
Section roll-up: High | Mid | Low
Section points: +3 | 0 | -3
B - Business Model / Financial Forecast
Criteria:
  ...
HARD STOP triggered: ...
Section roll-up: ...
Section points: ...
...(continue through Z in the same format, covering all 26 sections)...
SECTION ADJUSTMENTS SUMMARY
<All 26 letters with their point values on one line, exact format, e.g.:
A:+3 B:0 C:-3 D:+3 E:0 F:-3 G:+3 H:0 I:-3 J:+3 K:0 L:-3 M:+3 N:0 O:-3 P:+3 Q:0 R:-3 S:+3 T:0 U:-3 V:+3 W:0 X:-3 Y:+3 Z:0
(fill in your actual computed section points per letter — this line is parsed programmatically, so it must include all 26 letters, each followed by a colon and a signed point value of -3, 0, or +3, space-separated, nothing else on this line)>
HARD STOP / DEALBREAKER FLAGS
- <list every triggered HARD STOP with section letter, criterion, and the specific evidence, or "None identified">
TOP INFORMATION GAPS
- <the 3-6 most important missing documents/data points that, if provided, would most change the score>
Rules:
- Do not skip any section or criterion. If you find zero information for a criterion, still score it (Low, per the absence-of-evidence rule) and say so.
- Be specific — reference actual filenames or document contents where possible, not generic language.


- Keep each criterion's evidence concise (roughly one sentence).
- The SECTION ADJUSTMENTS SUMMARY line is required and must be machine-parseable exactly as specified — this is how the final weighted score gets calculated, so double-check it has all 26 letters before finishing.

INVESTMENT RECOMMENDATION
- After completing all section scores, step back and give an objective
  investment recommendation: Invest / Pass / Watch (revisit later).
- This recommendation is not a restatement of the composite score. Weigh
  qualitative factors that the weighted score may not fully capture —
  e.g., founder bandwidth and focus (is leadership running multiple
  companies or otherwise divided?), competitive differentiation on the
  specific dimension investors care about (not just "competitors exist"
  but whether this company's core metric/spec is actually better than
  the field), early revenue or commercial traction as a signal even if
  early-stage, and any other pattern you'd flag to a partner as a reason
  to invest or pass even if the numeric score alone wouldn't fully
  explain it.
- You may draw on general market/industry knowledge (e.g., typical
  competitive benchmarks in this space, what "good" looks like for a
  company at this stage) to contextualize the data room's findings. Do
  NOT invent specific facts about this company that aren't in the data
  room — outside knowledge is for framing and comparison only, not for
  filling gaps in what the company itself has or hasn't disclosed.
- Structure as 3-6 bullet points, each a specific, standalone reason
  (positive or negative), written the way an analyst would explain a
  recommendation to a partner — not generic ("good market opportunity")
  but specific to what's in this data room (e.g., "Founder/CEO is
  actively running 4 other ventures per the bios in the deck — bandwidth
  risk for a company still pre-revenue" or "Resolution/accuracy spec in
  the tech docs trails the two closest disclosed competitors by a
  meaningful margin, and no roadmap item addresses closing that gap").
- End with one line: RECOMMENDATION: Invest | Pass | Watch — followed by
  a one-sentence summary reason.
"""


def score_company(client, model: str, rubric_text: str, company_name: str, internal_docs: list) -> str:
    system_prompt = build_system_prompt(rubric_text)

    parts = [f"Company: {company_name}\n"]
    parts.append("=== DATA ROOM DOCUMENTS ===")
    if not internal_docs:
        parts.append("(No readable documents were found in this company's data room folder.)")
    for doc in internal_docs:
        parts.append(f"\n--- File: {doc['filename']} ---\n{doc['text']}")

    parts.append(
        "\n=== TASK ===\nScore this company's data room against the Project Atlas "
        "rubric, following the exact output format specified in the system prompt."
    )

    resp = client.messages.create(
        model=model,
        max_tokens=16000,
        system=system_prompt,
        messages=[{"role": "user", "content": "\n".join(parts)}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def parse_section_adjustments(report_text: str) -> dict:
    """Pulls the 'SECTION ADJUSTMENTS SUMMARY' line (e.g. 'A:+3 B:0 C:-3 ...')
    out of Claude's response and returns {letter: point_value}. Raises
    ValueError if any of the 26 letters is missing or malformed."""
    matches = re.findall(r"\b([A-Z]):([+-]?\d+)\b", report_text)
    scores = {}
    for letter, val in matches:
        if letter in RUBRIC_SECTIONS:
            scores[letter] = int(val)  # last occurrence wins, in case a letter is mentioned earlier too

    missing = [s for s in RUBRIC_SECTIONS if s not in scores]
    if missing:
        raise ValueError(f"missing section scores for: {', '.join(missing)}")
    bad = [f"{k}={v}" for k, v in scores.items() if not (-3 <= v <= 3)]
    if bad:
        raise ValueError(f"section scores must be integers from -3 to +3; got: {', '.join(bad)}")
    return scores


def compute_composite_score(section_scores: dict) -> tuple:
    lines = []
    total_contribution = 0.0
    for name, weight, sections in CATEGORIES:
        vals = [section_scores[s] for s in sections]
        avg_delta = sum(vals) / len(vals)
        weight_points = weight * 100          # 0.20 -> 20
        contribution = weight_points * avg_delta / 6   # bounds final score to 0-100
        total_contribution += contribution
        sec_str = " ".join(f"{s}:{section_scores[s]:+d}" for s in sections)
        lines.append(
            f"  {name} ({weight:.0%}) — sections [{sec_str}] — avg delta {avg_delta:+.2f} "
            f"— contribution {contribution:+.3f}"
        )
    final_score = 50 + total_contribution
    return lines, final_score


def build_computed_score_block(report_text: str) -> str:
    """Parses Claude's SECTION ADJUSTMENTS SUMMARY line and computes the
    weighted composite score deterministically in Python. Returns a text
    block to append to the report, or an error block if parsing failed."""
    try:
        section_scores = parse_section_adjustments(report_text)
    except ValueError as e:
        return (
            "\nCOMPUTED SCORE (verified programmatically)\n"
            f"  [ERROR] Could not parse section scores from model output: {e}\n"
            "  Re-run this company, or check the raw output above for a malformed "
            "SECTION ADJUSTMENTS SUMMARY line.\n"
            "TOTAL SCORE: ?\n"
        )
    breakdown, final_score = compute_composite_score(section_scores)
    block = (
        "\nCOMPUTED SCORE (verified programmatically, not model arithmetic)\n"
        "Category contributions:\n" + "\n".join(breakdown) + "\n"
        f"Final Score = 50 + sum(contributions) = {final_score:.2f}\n"
        f"TOTAL SCORE: {final_score:.2f}\n"
    )
    return block


def load_state(path: Path) -> set:
    if path.exists():
        try:
            return set(json.loads(path.read_text()))
        except Exception:
            return set()
    return set()


def save_state(state: set, path: Path) -> None:
    path.write_text(json.dumps(sorted(state), indent=2))


def extract_total_score(report_text: str) -> str:
    m = re.search(r"TOTAL SCORE:\s*([\-\d.]+)", report_text)
    return m.group(1) if m else "?"

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Score company data rooms against the Project Atlas rubric.")
    ap.add_argument("--company", help="Restrict to one company/dataroom folder (exact folder name).")
    ap.add_argument("--dry-run", action="store_true", help="Print scorecards to stdout, don't write files.")
    ap.add_argument("--reset-state", action="store_true", help="Clear the skip cache and exit.")
    ap.add_argument("--output-dir", help="Write all .txt files here instead of inside each company folder.")
    ap.add_argument("--root", help="Folder containing one subfolder per company data room "
                                    "(default: HUNNIWELL_COMPANYFILES_ROOT env var, e.g. .../SVC).")
    ap.add_argument("--rubric", help=f"Path to rubric markdown file (default: {DEFAULT_RUBRIC}).")
    ap.add_argument("--model", default=CLAUDE_MODEL, help=f"Claude model to use (default: {CLAUDE_MODEL}).")
    ap.add_argument("--nested", action="store_true",
                     help="Use event/company two-level layout (root/EventFolder/CompanyFolder/...) "
                          "instead of the default flat layout (root/CompanyFolder/...).")
    ap.add_argument("--event", help="With --nested: restrict to one event folder (exact folder name).")
    args = ap.parse_args()

    root = Path(args.root or os.environ.get("HUNNIWELL_COMPANYFILES_ROOT") or DEFAULT_ROOT).expanduser()
    rubric_path = Path(args.rubric).expanduser() if args.rubric else DEFAULT_RUBRIC

    if args.reset_state:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
            print(f"Removed {STATE_FILE}")
        else:
            print("No state file found.")
        return

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_key:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        sys.exit(1)
    if not root.exists():
        print(f"ERROR: Root directory not found: {root}")
        sys.exit(1)
    if not rubric_path.exists():
        print(f"ERROR: Rubric file not found: {rubric_path}")
        sys.exit(1)

    rubric_text = rubric_path.read_text(encoding="utf-8")

    output_dir = Path(args.output_dir).resolve() if args.output_dir else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    if not HAVE_XLSX:
        print("[note] openpyxl not installed — .xlsx files (cap tables, financial models) will be skipped. "
              "Run: pip install openpyxl")

    client = anthropic.Anthropic(api_key=anthropic_key)
    state = load_state(STATE_FILE)

    # Build a flat list of (label, company_dir) pairs to score.
    # label is used for the state-cache key and printed progress; it includes
    # the event name only in --nested mode.
    jobs = []
    if args.nested:
        all_events = sorted(p for p in root.iterdir() if p.is_dir())
        if args.event:
            event_folders = [p for p in all_events if p.name == args.event]
            if not event_folders:
                print(f"No event folder matching '{args.event}'.")
                sys.exit(1)
        else:
            event_folders = all_events

        for event_folder in event_folders:
            for company_dir in sorted(p for p in event_folder.iterdir() if p.is_dir()):
                jobs.append((f"{event_folder.name}/{company_dir.name.strip()}", company_dir))
    else:
        for company_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            jobs.append((company_dir.name.strip(), company_dir))

    total_ok = total_skip = total_fail = 0
    summary_rows = []  # (company, total_score)

    if args.company:
        needle = args.company.strip().lower()
        matched = [(k, d) for k, d in jobs if needle in d.name.strip().lower()]
        if not matched:
            print(f"No company folder matching '{args.company}'. Folders found under root:")
            for _, d in jobs:
                print(f"  - {d.name!r}")
            sys.exit(1)
        if len(matched) > 1:
            print(f"'{args.company}' matched multiple folders — be more specific:")
            for _, d in matched:
                print(f"  - {d.name!r}")
            sys.exit(1)
        jobs = matched

    for state_key, company_dir in jobs:
        company = company_dir.name.strip()

        print(f"\n{state_key}")

        if state_key in state:
            print("  skip (already scored — use --reset-state to rerun)")
            total_skip += 1
            continue

        print("  reading data room...")
        internal_docs = collect_internal_docs(company_dir)
        print(f"  found {len(internal_docs)} readable file(s)")

        print(f"  scoring against rubric ({args.model})...")
        try:
            report = score_company(client, args.model, rubric_text, company, internal_docs)
        except Exception as e:
            print(f"  ERROR: {e}")
            total_fail += 1
            continue

        header = (
            f"PROJECT ATLAS — DUE DILIGENCE SCORECARD\n"
            f"Company: {company}\n"
            f"Generated: {time.strftime('%Y-%m-%d %H:%M')}\n"
            f"Data room files reviewed: {len(internal_docs)}\n"
            + "=" * 80 + "\n\n"
        )
        computed_block = build_computed_score_block(report)
        full_report = header + report + "\n" + computed_block

        total_score = extract_total_score(computed_block)
        summary_rows.append((company, total_score))
        print(f"  -> TOTAL SCORE: {total_score}")

        if args.dry_run:
            print("\n" + full_report)
        else:
            safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", company)[:80]
            if output_dir:
                out_path = output_dir / f"{safe_name}_atlas_score.txt"
            else:
                out_path = company_dir / f"{safe_name}_atlas_score.txt"

            out_path.write_text(full_report, encoding="utf-8")
            print(f"  -> wrote {out_path}")

        state.add(state_key)
        save_state(state, STATE_FILE)
        total_ok += 1

    print(f"\nDone. ok={total_ok}  skipped={total_skip}  failed={total_fail}")
    if summary_rows:
        print("\nScore summary:")
        for company, score in summary_rows:
            print(f"  {score:>4}  {company}")


if __name__ == "__main__":
    main()


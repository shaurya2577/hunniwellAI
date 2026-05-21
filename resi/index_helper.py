"""
Index CSV helpers (generic for any platform).

Creates one CSV per run: index_YYYY-MM-DD_HH-MM-SS.csv with columns: Company Name, Sector, optional
categorization fields, Link Label, PDF URL. One row per link. Use download_from_index.py to fetch files.
"""
import csv
import logging
import os
from datetime import datetime


INDEX_HEADERS = (
    "Company Name",
    "Sector",
    "Subsectors",
    "Business model",
    "Main therapeutic sector",
    "Customer segments",
    "Address",
    "Year founded",
    "Company email",
    "Website",
    "Company description",
    "State of ownership",
    "Function of location",
    "Headquarters",
    "Source of foundation",
    "Link Label",
    "PDF URL",
)

# Open Rounds index: one row per company with full extracted data
# Categories: Identity, Summary, Open Deal, Pitch Deck, All Deals, Product & Regulatory, Milestones, Team
OPEN_ROUNDS_INDEX_HEADERS = (
    "Company Name",
    "Company ID",
    "Website",
    "Company URL",
    "One-liner",
    "Location",
    "Year Founded",
    "Current Runway",
    "Team Size",
    "Deal Summary",
    "Urgency",
    "Have Terms",
    "Deal Type",
    "Round",
    "Target Total",
    "Open Amount",
    "Pitch Deck Filename",
    "Pitch Deck Download URL",
    "Total Equity To-date",
    "Total Debt To-date",
    "Total Non-Dilutive To-date",
    "Primary Product Name",
    "Product Summary",
    "Product Development Stage",
    "Regulatory Pathway",
    "US Regulatory Status",
    "EU Regulatory Status",
    "Asia Regulatory Status",
    "Milestones Completed",
    "Milestones Funded",
    "Milestones Open Round",
    "Team Members",
    "Video URL",
)

# Investor/delegate index: one row per delegate, with firm-level context
# Fields from Company tab, Investor details tab, and Seeking tab
INVESTOR_INDEX_HEADERS = (
    "Firm Name",
    "Delegate Name",
    "Position",
    "Email",
    "LinkedIn",
    "Sector",
    "Subsector",
    "Main therapeutic sector",
    "Investor type",
    "Sector & subsector",
    "Indication interest",
    "Geographical interest",
    "Therapeutic development phase",
    "Medical device development phase",
    "Capital structure preference",
    "Investment stage preference",
    "Mandate summary",
    "Location",
)


def get_index_path_for_run(output_dir: str) -> str:
    """Return path for this run's index CSV: index_YYYY-MM-DD_HH-MM-SS.csv in output_dir."""
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"index_{stamp}.csv"
    return os.path.join(output_dir, filename)


def get_investor_index_path_for_run(output_dir: str) -> str:
    """Return path for this run's investor index CSV: investor_index_YYYY-MM-DD_HH-MM-SS.csv."""
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"investor_index_{stamp}.csv"
    return os.path.join(output_dir, filename)


def get_open_rounds_index_path_for_run(output_dir: str) -> str:
    """Return path for this run's Open Rounds CSV: open_rounds_YYYY-MM-DD_HH-MM-SS.csv."""
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"open_rounds_{stamp}.csv"
    return os.path.join(output_dir, filename)


def init_open_rounds_index(index_path: str) -> None:
    """Create Open Rounds CSV with headers. Overwrites if exists (fresh run)."""
    os.makedirs(os.path.dirname(index_path) or ".", exist_ok=True)
    with open(index_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(OPEN_ROUNDS_INDEX_HEADERS)
    logging.info("Created Open Rounds index at %s", index_path)


def append_to_open_rounds_index(
    index_path: str,
    company_name: str = "",
    company_id: str = "",
    website: str = "",
    company_url: str = "",
    one_liner: str = "",
    location: str = "",
    year_founded: str = "",
    current_runway: str = "",
    team_size: str = "",
    deal_summary: str = "",
    urgency: str = "",
    have_terms: str = "",
    deal_type: str = "",
    round_: str = "",
    target_total: str = "",
    open_amount: str = "",
    pitch_deck_filename: str = "",
    pitch_deck_download_url: str = "",
    total_equity_to_date: str = "",
    total_debt_to_date: str = "",
    total_non_dilutive_to_date: str = "",
    primary_product_name: str = "",
    product_summary: str = "",
    product_development_stage: str = "",
    regulatory_pathway: str = "",
    us_regulatory_status: str = "",
    eu_regulatory_status: str = "",
    asia_regulatory_status: str = "",
    milestones_completed: str = "",
    milestones_funded: str = "",
    milestones_open_round: str = "",
    team_members: str = "",
    video_url: str = "",
) -> None:
    """Append one row to the Open Rounds CSV (one row per company with full data)."""
    name = (company_name or "").strip()
    if not name:
        return
    row = [
        name,
        (company_id or "").strip(),
        (website or "").strip(),
        (company_url or "").strip(),
        (one_liner or "").strip(),
        (location or "").strip(),
        (year_founded or "").strip(),
        (current_runway or "").strip(),
        (team_size or "").strip(),
        (deal_summary or "").strip(),
        (urgency or "").strip(),
        (have_terms or "").strip(),
        (deal_type or "").strip(),
        (round_ or "").strip(),
        (target_total or "").strip(),
        (open_amount or "").strip(),
        (pitch_deck_filename or "").strip(),
        (pitch_deck_download_url or "").strip(),
        (total_equity_to_date or "").strip(),
        (total_debt_to_date or "").strip(),
        (total_non_dilutive_to_date or "").strip(),
        (primary_product_name or "").strip(),
        (product_summary or "").strip(),
        (product_development_stage or "").strip(),
        (regulatory_pathway or "").strip(),
        (us_regulatory_status or "").strip(),
        (eu_regulatory_status or "").strip(),
        (asia_regulatory_status or "").strip(),
        (milestones_completed or "").strip(),
        (milestones_funded or "").strip(),
        (milestones_open_round or "").strip(),
        (team_members or "").strip(),
        (video_url or "").strip(),
    ]
    with open(index_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)


def init_index(index_path: str) -> None:
    """Create CSV with headers. Overwrites if exists (fresh run)."""
    os.makedirs(os.path.dirname(index_path) or ".", exist_ok=True)
    with open(index_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(INDEX_HEADERS)
    logging.info("Created index at %s", index_path)


def append_to_index(
    index_path: str,
    company_name: str,
    pdf_url: str = "",
    link_label: str = "",
    sector: str = "",
    subsectors: str = "",
    business_model: str = "",
    main_therapeutic_sector: str = "",
    customer_segments: str = "",
    address: str = "",
    year_founded: str = "",
    company_email: str = "",
    website: str = "",
    company_description: str = "",
    state_of_ownership: str = "",
    function_of_location: str = "",
    headquarters: str = "",
    source_of_foundation: str = "",
) -> None:
    """Append one row to the run's index CSV (company + categorization + general info + link label, PDF URL)."""
    name = company_name.strip()
    if not name:
        return
    row = [
        name,
        (sector or "").strip(),
        (subsectors or "").strip(),
        (business_model or "").strip(),
        (main_therapeutic_sector or "").strip(),
        (customer_segments or "").strip(),
        (address or "").strip(),
        (year_founded or "").strip(),
        (company_email or "").strip(),
        (website or "").strip(),
        (company_description or "").strip(),
        (state_of_ownership or "").strip(),
        (function_of_location or "").strip(),
        (headquarters or "").strip(),
        (source_of_foundation or "").strip(),
        (link_label or "").strip(),
        (pdf_url or "").strip(),
    ]
    with open(index_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)


def init_investor_index(index_path: str) -> None:
    """Create investor CSV with headers. Overwrites if exists (fresh run)."""
    os.makedirs(os.path.dirname(index_path) or ".", exist_ok=True)
    with open(index_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(INVESTOR_INDEX_HEADERS)
    logging.info("Created investor index at %s", index_path)


def append_to_investor_index(
    index_path: str,
    firm_name: str,
    delegate_name: str = "",
    position: str = "",
    email: str = "",
    linkedin: str = "",
    sector: str = "",
    subsector: str = "",
    main_therapeutic_sector: str = "",
    investor_type: str = "",
    sector_subsector: str = "",
    indication_interest: str = "",
    geographical_interest: str = "",
    therapeutic_dev_phase: str = "",
    medical_device_dev_phase: str = "",
    capital_structure: str = "",
    investment_stage: str = "",
    mandate_summary: str = "",
    location: str = "",
) -> None:
    """Append one row to the investor index CSV (one row per delegate)."""
    firm = (firm_name or "").strip()
    if not firm:
        return
    row = [
        firm,
        (delegate_name or "").strip(),
        (position or "").strip(),
        (email or "").strip(),
        (linkedin or "").strip(),
        (sector or "").strip(),
        (subsector or "").strip(),
        (main_therapeutic_sector or "").strip(),
        (investor_type or "").strip(),
        (sector_subsector or "").strip(),
        (indication_interest or "").strip(),
        (geographical_interest or "").strip(),
        (therapeutic_dev_phase or "").strip(),
        (medical_device_dev_phase or "").strip(),
        (capital_structure or "").strip(),
        (investment_stage or "").strip(),
        (mandate_summary or "").strip(),
        (location or "").strip(),
    ]
    with open(index_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)
        f.flush()
        os.fsync(f.fileno())

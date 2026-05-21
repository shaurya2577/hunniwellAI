# Slidedeck Download Guide

## Summary: CSV Data Completeness

**The CSV contains all text data from the saved HTML.**

| Source | Count |
|--------|-------|
| HTML grid label-value pairs | 1,032 |
| Unique field labels | 83 |
| Companies | 15 |
| CSV columns | 83 ✓ |

All application form fields (Company Name, Product Description, funding, milestones, Pitch deck filename, etc.) are captured. The only data **not** in the saved files:

- **Actual PDF/video files** (pitch decks, product photos, other documents) — these live on the MTI server at `pro.innovator.org`
- **Pitch recordings** — if any were uploaded

## Slidedeck Files (from CSV)

| Company | Pitch Deck | Other Files |
|---------|------------|-------------|
| Adsys | deck_15slides_adsys.pdf | adsys march testing report_compressed.pdf |
| Spinvention | (in Other) | Spinvention.pdf, Spinvention-One Pager.pdf |
| Aignosis | Aignosis Pitch Deck (1).pdf | Aignosis Executive Summary.pdf |
| Reviv | GetReviv Pitch_Deck.pdf | — |
| NEMA AI | NEMA AI US PITCH 2025.pdf | MD12APPROVED.pdf |
| Walking Doctors | WD.Deck.11.30.25.pdf | WD.short.1.MP4 |
| Theia Health | MedClarity_Intro Slides_nonconfidential_... | — |
| BrainCapture | BrainCapture Pitch Deck.pdf | — |
| Physiologas | PhysiologasTechnologies_Deck.pdf | — |
| LioMed | URL_Pitch Deck PPT_2025-11-17_nc.pdf | — |
| Serenic.ai | Serenic.ai - Pitch Deck Jan26-2.pdf | — |
| Apex Cura | ApexCura-PitchDeck-Oct25.pdf | — |
| MicroHeal | MicroHeal Deck_MedTech_Investopitch (1)_... | — |
| Wumi Health | Pitch deck Pak and MENA 2M.pdf | — |
| Immunyfit | Immunyfit Pitchdeck 2025 V9.pdf | Immunyfit_Platform_Demo Basic... |

## How to Download Slidedecks

The files are stored on the **MedTech Innovator portal** (`https://pro.innovator.org`). They are **not** in the saved HTML or `Innovator Portal_files` folder.

### Option 1: Manual Download (Recommended)

1. Log in at https://pro.innovator.org
2. Go to Applications → APAC → 2026
3. Expand each company row
4. Scroll to **Application Files**
5. Click each file link to download

### Option 2: Browser Automation (Playwright)

Use the provided `download_slidedecks.py` script. It requires:

- Playwright: `pip install playwright && playwright install chromium`
- You must log in manually on first run (script will pause)
- Script then automates clicking through each company and downloading files

### Option 3: Request from MTI

Contact MedTech Innovator admin to request a bulk export of application files for the 2026 APAC cohort.

## Source URL

The saved page was from:
`https://pro.innovator.org/applications/apac/cohort-year/2026?assignedTo=Daniel%20Teo`

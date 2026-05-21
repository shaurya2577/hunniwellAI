# Pro Innovator Slidedeck Download Guide

## Summary: CSV Data Completeness

**The CSV contains all text data from the saved HTML.**

All application form fields (Company Name, Product Description, funding, milestones, Pitch deck filename, etc.) are captured. The only data **not** in the saved files:

- **Actual PDF/video files** (pitch decks, product photos, other documents) — these live on the MTI server at `pro.innovator.org`
- **Pitch recordings** — if any were uploaded

## Current Automation Strategy

Pro Innovator application files are often hosted on Google Drive. Links open a Google Drive viewer page that **does not offer direct download**.

The live runner now uses this strategy:

1. Scrape the Applications AG Grid into a CSV.
2. Click each company's `View` action.
3. Detect the viewer tab/page.
4. Capture rendered page containers as images.
5. Rebuild those images into a PDF locally.

This first version prioritizes reliable full rendered-page capture. Tighter slide cropping can be added later.

## How to Download Slidedecks

### Option 1: Manual Download

1. Log in at https://pro.innovator.org
2. Go to Applications → APAC → [Cohort Year]
3. Expand each company row
4. Scroll to **Application Files**
5. Click each file link to download (where supported)

### Option 2: Browser Automation (Playwright)

```bash
cd resi
python run_pro_innovator.py --live
```

Or, to validate the setup against one company first:

```bash
cd resi
python run_pro_innovator.py --live --test-one
```

The script opens a persistent Chromium profile. Log in if needed, navigate to the Applications page, then press Enter in the terminal.

### Option 3: Request from MTI

Contact MedTech Innovator admin to request a bulk export of application files.

## Source URL

Applications page (example):
`https://pro.innovator.org/applications/apac/cohort-year/2026?assignedTo=Daniel%20Teo`

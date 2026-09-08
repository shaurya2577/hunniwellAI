# Project Atlas: Due Diligence Scoring Rubric

Each company starts at a baseline score of 50. Every section (A–Z) is scored Low (-3), Mid (0), or High (+3) based on where the majority of its bullet points fall. A Low score can also be triggered by a single bullet reflecting a serious dealbreaker issue — this override applies across all sections, including Hygiene.

## Weighted Category Structure

| Category | Weight | Sections Mapped |
|---|---|---|
| Clinical Need | 20% | C, D |
| Technology Differentiation | 10% | I, T |
| Regulatory/Development Maturity | 15% | E, P, Q, R |
| Market/Commercial Strength | 15% | K, M, N, S |
| Capital Efficiency | 10% | B, F, U, V |
| Strategic Exit Relevance | 20% | J, X, Z |
| Hygiene (gating/dealbreaker) | 10% | A, G, H, L, O, W, Y |
| **Total** | **100%** | **26 sections (A–Z)** |

## Composite Scoring Formula

```
Final Score = 50 + Σ [ Category Weight(points) × (Category Average Delta ÷ 6) ]
```

Category Average Delta = the mean of the ±3 scores of all sections mapped to that category (range: -3 to +3). R (Regulatory & Reimbursements) is scored once as a whole section under Regulatory/Development Maturity.

Category Weight is expressed in points out of 100 (e.g. Clinical Need = 20, not 0.20). The average delta is normalized by dividing by 6 before multiplying by weight — this bounds the composite naturally to the 0–100 range with no clamping needed, since weights sum to 100 and delta/6 tops out at ±0.5.

**Example:** if every section in Clinical Need (weight 20) scores the max +3, avg delta = +3, contribution = 20 × (3/6) = +10. If every category across the whole rubric hit +3, total contribution = +50, final score = 100. If every category hit -3, total contribution = -50, final score = 0.

**Dealbreaker mechanism:** Hygiene sections (A, G, H, L, O, W, Y) retain full override authority. A Low score on a dealbreaker bullet (e.g., catastrophic/uncapped legal exposure, active undisclosed litigation) can flag or kill a deal regardless of the weighted composite score — the 10% Hygiene weight governs only its contribution to the numeric total, not its veto power.

---

# Project Atlas — Objective Due Diligence Scoring Rubric

## 1. Scoring Framework

**Section-level roll-up rule:** A section scores High (+3) if a majority of its listed criteria meet the High threshold and none meet Low. A section scores Low (–3) if a majority of its criteria meet the Low threshold, or if any criterion marked HARD STOP is triggered (these mirror the explicit dealbreakers already present in the original draft — e.g., >50% revenue concentration in 3 customers, or any litigation exceeding the USD 25,000 threshold set by HLV item L1). Otherwise, a section scores Mid (0).

**Note on threshold calibration:** The specific cutoffs below (percentages, day-counts, dollar figures) are illustrative defaults grounded in common growth-stage venture/PE diligence conventions and in the few numeric anchors already present in the source documents (the USD 25,000 materiality threshold in HLV item L1; the >50% customer-concentration dealbreaker and CAC/LTV multiples already drafted in Atlas Sections M, S, and T).

## 2. Objectified Rubric, A–Z

### A — Intro & Overview
*HLV Section Title: Intro and Overview*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Motivation & Mission/Vision Clarity (Ref: A1, A2) | No documented mission/vision statement, or the investor deck does not name a specific target market or problem. | Mission/vision statement provided and a target market is named, but no measurable 3–5 year objective is stated. | Mission/vision statement names a specific target market, a quantified problem size, and a measurable 3–5 year objective. |
| Corporate/Subsidiary Structure Complexity (Ref: A3) | Structure chart missing, or >5 legal entities exist with <80% of ownership stakes documented. | Structure chart provided; 2–5 entities with ≥80% of ownership stakes documented. | Structure chart provided; ≤2 entities (or 100% of ownership across all entities fully documented). |
| History of Challenges & Resolution (Ref: A1) | ≥2 unresolved pivots/restarts with no documented resolution plan. | 1 pivot/restart with a documented resolution plan of unconfirmed status. | 0 unresolved pivots, or all past challenges show a documented resolution completed within 12 months of onset. |
| Data Room / Deck Organization (Ref: A2) | Investor deck missing ≥2 of the 5 standard sections (problem, solution, market, team, financials), or >30% of A-section requested items outstanding at first ask. | Deck complete; 10–30% of A-section requested items outstanding at first ask. | Deck complete; ≥95% of A-section requested items fulfilled at first ask. |

### B — Business Model / Financial Forecast
*HLV Section Title: Business Model*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Model Completeness for Valuation (Ref: B1, B2) | 5-year model missing ≥2 of (unit volumes, ASP, COGS, opex), or not provided. | Model includes all four core drivers but supports fewer than 2 valuation methodologies. | Model includes all four core drivers and valuation is cross-checked via ≥2 methods (e.g., DCF and comparables). |
| Forecast Horizon (Ref: B2) | Forecast covers <2 years, or is built on <12 months of trailing actuals. | Forecast covers 3 years. | Forecast covers the full 5 years, with quarterly granularity for years 1–2. |
| Scenario & Sensitivity Testing (Ref: B2, B3) | No sensitivity table or alternative scenario beyond the base case. | 1 alternative scenario provided (e.g., downside only). | ≥3 scenarios (best/base/worst) with sensitivity testing on ≥3 identified key value drivers. |
| Funding Adequacy (Ref: B1, B3) | <6 months of cash runway at current burn with no financing plan on file. | 6–12 months of cash runway. | >12 months of runway post-raise, or a break-even date is specified and supported within the model. |
| Risk Quantification (Ref: B3) | Risks discussed narratively only, with no quantified dollar impact for any risk category. | Risks quantified (dollar impact) for <50% of identified risk categories. | ≥80% of identified risk categories are quantified with dollar impact and an owning department. |

### C — Commercial
*HLV Section Title: Commercial*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| TAM / SAM / SOM Definition (Ref: C1, C2) | TAM/SAM/SOM undefined, or based solely on a company estimate with no stated methodology. | TAM/SAM/SOM defined via a top-down OR bottom-up methodology, without third-party validation. | TAM/SAM/SOM defined via both top-down and bottom-up methods and cross-validated by ≥1 third-party market study (C2). |
| Conversion / Adoption Rate (Ref: C1) | No conversion/adoption data on file, or documented pilot-to-paid conversion <10%. | Conversion rate 10–25%, based on <12 months of data. | Conversion rate >25% sustained over ≥12 months, or above a disclosed, sourced industry benchmark. |
| Market/Pipeline Management System (Ref: C1) | No CRM or pipeline-tracking system in use. | System in place; data lag between a sales event and system update exceeds 30 days. | System in place with documented pipeline stages; data lag ≤7 days. |
| Customer Buying Dynamics (Ref: C1, C2) | No documented buyer persona or average sales-cycle length. | Buyer persona and average sales-cycle length documented, not segmented by customer type. | Buyer persona, decision-maker map, and average sales-cycle length documented and segmented by customer type. |

### D — Direct & Indirect Competition
*HLV Section Title: Direct and Indirect Competition*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Competitive Landscape Mapping (Ref: D2, D3) | <3 competitors identified, or no landscape/feature comparison exists. | 3–5 competitors identified with a feature comparison. | ≥5 competitors identified with a feature/pricing comparison table plus an adjacent/emerging-technology scan. |
| Dependency on External Parties (Ref: D1) | A critical input or channel has a single-source dependency with no identified alternative. | Single-source dependency exists; ≥2 alternatives identified but not yet qualified. | No critical single-source dependency, or ≥2 qualified alternatives are already in place. |
| Convergence Risk from Adjacent Technologies (Ref: D3) | No documented assessment of adjacent-technology threats. | Adjacent-technology risks are named but carry no mitigation plan. | Adjacent-technology risks are named with a documented mitigation/monitoring plan reviewed at least annually. |
| Pricing & Feature Differentiation (Ref: D1, D3) | Pricing within 5% of the nearest competitor with no stated differentiation, or no competitor pricing data on file. | Differentiation documented on 1 dimension (feature or price). | Differentiation documented across ≥2 dimensions (feature, price, go-to-market) supported by win-rate data. |
| Regulatory Timing Strategy (Ref: D3) | No regulatory timing plan on file. | Regulatory milestones listed without target dates. | Regulatory milestones are dated and tracked against actuals within ±90 days. |

### E — Engineering Design
*HLV Section Title: Engineering Design*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Design History File (DHF) Completeness (Ref: E1) | DHF is <50% complete or absent. | DHF is 50–90% complete. | DHF is ≥90% complete and was last updated within 6 months. |
| Design Review Currency (Ref: E2) | No design review on record in the past 12 months. | Most recent design review on record is 6–12 months old. | Most recent design review is <6 months old, indexed and cross-referenced to the DHF. |
| Frequency of Design Changes / Restarts (Ref: E2, E3) | ≥2 full redesigns/restarts in the past 24 months with no supporting test data. | 1 restart in the past 24 months, partially supported by test data. | 0 restarts in the past 24 months, or all design changes are documented as data-driven (review + test data attached). |
| On-Time Delivery Track Record (Ref: E2, E3) | >50% of design milestones missed by >90 days. | 20–50% of design milestones missed by >90 days. | <20% of design milestones missed by >90 days. |

### F — Finance (Historical)
*HLV Section Title: Financial Statements*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Historic Trend Examination (Ref: F1, F2) | Fewer than 3 years of audited financials provided, or statements are unaudited. | 3 years of audited financials provided; YoY variances >10% are not explained. | 3 years of audited financials plus monthly management reports (F2), with all YoY variances >10% explained in writing. |
| Audit Variance (Ref: F1) | Unexplained audit adjustment exceeds 5% of reported net income. | Audit adjustment is 1–5% of net income and is explained. | Audit adjustment is <1% of net income, or none. |
| Crisis Anticipation / Liquidity Planning (Ref: F2) | No cash-flow forecast or runway analysis on file. | Runway is calculated but not stress-tested against a downside case. | Runway is calculated and stress-tested against ≥1 downside scenario, with a documented contingency plan. |
| Working Capital & Collections (Ref: F6, F8) | Days Sales Outstanding (DSO) >90 days, or DSO has worsened >20% over the trailing 3 years. | DSO 45–90 days, flat trend over 3 years. | DSO <45 days, or an improving trend over the trailing 3 years. |
| Off-Balance-Sheet Items (Ref: F5) | Off-balance-sheet items exist and are undisclosed or unexplained. | Off-balance-sheet items are disclosed with a partially documented rationale. | Off-balance-sheet items are fully disclosed and documented, totaling <1% of total assets, or none exist. |

### G — Governance
*HLV Section Title: Governance*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Corporate Action Authority (Minutes/AGM) (Ref: G1) | Board minutes/AGM records missing for ≥1 of the last 3 fiscal years. | Minutes available for all 3 years but incomplete signature/quorum records. | Complete, signed board minutes and AGM records for all 3 fiscal years. |
| Incorporation & Constitutive Documents (Ref: G4) | ≥1 of (Certificate of Incorporation, Bylaws, board resolutions) is missing. | All documents present; ≥1 amendment is undocumented. | All documents present, fully executed, and version-controlled with a complete amendment history. |
| Shareholder Structure / Cap Table (Ref: G3) | Cap table does not reconcile to the share ledger, or ≥1 undocumented issuance exists. | Cap table reconciles; ≥1 pending grant or unclear vesting item remains open. | Cap table fully reconciles; 100% of grants documented with vesting schedules. |
| Certificate of Good Standing (Ref: G6) | Certificate is not current, or has lapsed, in ≥1 jurisdiction. | Current in the home jurisdiction only. | Current across all jurisdictions where the company is qualified to do business. |
| Tax Payments & Liabilities (Ref: G3) | ≥1 delinquent tax filing in the past 3 years. | Filings current; ≥1 disclosed ambiguity in liability treatment remains. | All filings current with zero ambiguity, fully disclosed. |
| Loan & Shareholder Agreements (Ref: G5) | >1 required agreement is missing or undocumented. | All agreements present; ≥1 non-standard term flagged by counsel. | All agreements present, standard-form, and vetted by counsel. |

### H — Human Resources
*HLV Section Title: Human Resources*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Employment Agreement Coverage (Ref: H1, H5, H7) | <80% of employees have a signed agreement on file. | 80–99% of employees have a signed agreement on file. | 100% of employees have a signed, standard-form agreement on file. |
| Compensation & Incentive Benchmarking (Ref: H1) | No compensation benchmarking data exists for any role. | Benchmarking exists for key roles only (<50% of headcount). | ≥50% of headcount benchmarked against market data sourced within the past 12 months. |
| Union / Labor Relations (Ref: H4, H9) | ≥1 active labor dispute or grievance filed in the past 12 months. | Union relationship exists; 0 disputes in the past 12 months. | No union exposure, or a union relationship with 0 disputes in the past 24 months. |
| Termination History (Ref: H4) | ≥1 termination-related litigation or agency claim in the past 3 years. | Terminations occurred with no litigation, but ≥1 informal dispute is on record. | No termination disputes of any kind in the past 3 years. |
| Employee Turnover (Ref: H8) | Annual voluntary turnover >30%. | Annual voluntary turnover 15–30%. | Annual voluntary turnover <15%, or below a disclosed, sourced industry benchmark. |
| Leadership Stability & Engagement (Ref: H6) | ≥2 leadership-team departures in the past 12 months, or no engagement survey ever conducted. | 1 leadership departure in the past 12 months, or no engagement survey in the past 12 months. | 0 leadership departures in the past 12 months and an engagement survey completed within the past 12 months with a documented score. |

### I — Intellectual Property
*HLV Section Title: Intellectual Property*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Patent Portfolio Breadth & Remaining Life (Ref: I6) | 0 issued/pending patents core to the product, or all core patents expire before the projected end of product life. | ≥1 patent filed/pending; remaining coverage exceeds product life by <5 years. | ≥1 granted patent with remaining life exceeding projected product life by ≥5 years, or documented trade-secret protection substitutes for patent coverage. |
| Freedom-to-Operate (FTO) (Ref: I1, I6) | No FTO analysis has been performed. | FTO analysis performed; ≥1 unresolved risk flagged. | FTO analysis performed by outside counsel within the past 24 months with zero unresolved risks. |
| Ownership / Chain of Title (Ref: I2–I5) | <90% of company-relevant inventions have a signed assignment agreement on file. | 90–99% of inventions are assigned. | 100% of inventions/IP assigned, with a fully documented chain of title. |
| Trade Secret / Know-How Protection (Ref: I2, I4) | No NDA or access-control policy governing trade secrets. | NDA policy exists but covers <90% of personnel with trade-secret access. | NDA and access controls cover 100% of personnel with trade-secret access. |
| Litigation / Infringement Exposure (Ref: I1, I6) | Active or credibly threatened IP litigation exists. | No active litigation, but ≥1 unaddressed third-party infringement notice is on file. | Zero litigation history and zero open infringement claims. |

### J — Joint Ventures
*HLV Section Title: Joint Ventures*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Dependency on JV/Partner (Ref: J1, J2) | >25% of revenue, or a critical function (manufacturing, distribution, or tech), depends on a single JV/partner with no alternative. | 10–25% dependency; ≥1 alternative identified but not yet qualified. | <10% dependency, or ≥1 qualified alternative is already in place. |
| Governance / Control Rights (Ref: J1) | Partner holds >50% control or an unmitigated veto over key decisions. | Control rights are balanced overall, but ≥1 provision is ambiguous. | Governance rights are favorable or balanced and documented without ambiguity. |
| Exit / Termination Provisions (Ref: J1) | No exit/termination clause exists, or termination requires unanimous partner consent. | Exit provisions exist but conditions are ambiguous. | Clear exit, termination, and change-of-control provisions, reviewed by counsel. |
| JV Terms Documentation (Ref: J1) | JV agreement is undocumented or in active dispute. | Agreement is documented but has not been independently reviewed/vetted. | Fully documented, vetted by counsel, with zero disputes on record. |

### K — Key Performance Indicators (KPIs)
*HLV Section Title: Key Performance Indicators*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Definition & Relevance of Tracked KPIs (Ref: K1) | <3 KPIs formally tracked, or tracked KPIs are not tied to unit economics. | 3–5 KPIs tracked and reported at least monthly. | ≥5 KPIs tracked, reported at least monthly, directly tied to unit economics/board reporting. |
| Historical Trend (Ref: K1) | Primary KPI trend is flat or declining over the trailing 12 months. | Primary KPI improving <10% over the trailing 12 months. | Primary KPI improving ≥10% over the trailing 12 months, or in the top quartile vs. a sourced benchmark. |
| Data Reliability & Systems (Ref: K1, K2) | KPIs tracked manually (spreadsheet) with no reconciliation to source systems. | KPIs tracked in a system of record but reconciled on an ad hoc basis. | KPIs tracked in a system of record and reconciled to source data on a monthly basis. |
| Benchmarking vs. Industry/Comparables (Ref: K2) | No benchmarking against industry or comparable companies has been performed. | Benchmarking performed against <3 comparable companies. | Benchmarking performed against ≥3 comparable companies with documented sourcing, at or above the median. |

### L — Legal
*HLV Section Title: Legal*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Litigation History (Ref: L1) | **HARD STOP** — ≥1 claim (pending, threatened, or resolved) in the past 3 years exceeding USD 25,000 — the materiality threshold defined in HLV item L1. | Claims exist but all are below the USD 25,000 threshold, or 1 resolved claim above the threshold with no ongoing exposure. | Zero claims of any size in the past 3 years. |
| Regulatory Compliance History (Ref: L2) | ≥1 unresolved regulatory finding, warning letter, or recall. | Findings exist but are fully remediated, with no open items. | Zero regulatory findings in company history. |
| Corporate / Legal Entity Structure Risk (Ref: G4) | Structure exposes owners/investors to uncapped personal liability. | Structure is sound with minor documentation gaps. | Structure is fully documented, liability capped and ring-fenced. |
| Insurance Coverage (Ref: L3, L4, L5) | No insurance policy in force for ≥1 identified key risk category. | Coverage in force but <100% of identified key risk categories are covered. | Coverage in force for 100% of identified key risk categories, with no lapses in the past 3 years. |
| General Contract Review (Ref: L6) | ≥1 material undisclosed legal exposure identified during contract review. | Zero undisclosed exposures found, but ≥1 clause is flagged for renegotiation. | Zero issues identified across the full contract review. |

### M — Material Contracts / Agreements
*HLV Section Title: Material Contracts/Agreements*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Customer / Supplier Concentration (Ref: M6) | **HARD STOP** — Top 3 customers account for >50% of aggregate revenue, indicating going-concern risk. | Top 3 customers account for 25–50% of revenue. | No single customer accounts for >10% of revenue (top 3 <30%). |
| Contract Terms & Durations (Ref: M1, M2, M3) | ≥1 key contract carries an unfavorable change-of-control clause or a termination-for-convenience notice period <30 days. | Standard terms overall, with 1–2 clauses flagged for review. | All key contracts are standard-form, vetted, with no unfavorable clauses. |
| Contract Renewal Risk (Ref: M1, M2, M5) | ≥1 key contract (>10% of revenue) expires within 6 months with no renewal in progress. | A key contract expires within 6–12 months; renewal discussions are underway. | No key contracts expire within 12 months, or renewal is already executed. |
| Exclusivity Constraints (Ref: M2, M3, M4) | Exclusivity terms block entry into ≥1 identified growth market. | Exclusivity present but limited to non-core markets. | No exclusivity constraints, or constraints reviewed and deemed immaterial by counsel. |

### N — New Business Development
*HLV Section Title: New Strategic Business Development (sic)*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Pipeline of New Products / Markets (Ref: N1) | No documented pipeline exists beyond the current product/indication. | A pipeline exists with ≥1 project, but timelines are undefined. | A pipeline of ≥2 projects exists with dated milestones. |
| R&D Roadmap & Resourcing (Ref: N1) | R&D budget is undefined or <5% of revenue, with no roadmap. | A roadmap exists; R&D budget is 5–10% of revenue. | A roadmap exists with R&D budget ≥10% of revenue (or sector-appropriate benchmark) and dedicated headcount. |
| Partnership / Licensing Strategy (Ref: N1) | No active partnership or licensing discussions on file. | ≥1 discussion underway; no signed letter of intent (LOI). | ≥1 signed LOI, term sheet, or executed partnership agreement. |
| Market Expansion Strategy (Ref: N1) | No documented geographic/indication expansion plan. | A plan exists but is untested (0 new markets entered). | A plan exists and is validated by ≥1 successful new-market entry. |

### O — Organizational Structure, Culture, and Process
*HLV Section Title: Organizational Structure, Culture, and Processes (sic)*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Org Chart Clarity (Ref: O1) | Org chart missing, or >20% of roles are unassigned/overlapping. | Org chart present with 5–20% gaps. | Org chart complete with <5% gaps, updated within the past 6 months. |
| Key-Person Dependency (Ref: O1) | ≥1 individual's departure would halt >30% of critical functions, with no succession plan. | Key-person risk is identified, with informal cross-training in place. | A documented succession plan exists for all key roles, with formal cross-training. |
| Turnover & Culture (Ref: O2, H8) | Annual turnover >30%, or no engagement data exists. | Annual turnover 15–30%. | Annual turnover <15%, or top-quartile vs. a sourced industry benchmark. |
| Process Documentation (SOPs) (Ref: O2) | <50% of core processes have a written SOP. | 50–90% of core processes are documented. | ≥90% of core processes documented as SOPs, reviewed within the past 12 months. |

### P — Production and Manufacturing
*HLV Section Title: Production and Manufacturing*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Manufacturing Scalability (Ref: P1, P5) | Current capacity utilization >90% with no expansion plan, or the process is unproven at any commercial volume. | Capacity utilization 70–90%; an expansion plan exists but is unfunded. | Capacity utilization <70% of current demand, with a funded expansion plan supporting ≥2x growth. |
| Supplier Reliability (Ref: P3) | ≥1 single-source supplier for a critical component with no qualified backup. | Single-source dependency exists; a backup supplier is identified but not yet qualified. | ≥2 qualified suppliers for all critical components, or a documented dual-source strategy. |
| Quality Control During Production (Ref: P1) | Defect/yield rate is >10 percentage points below a sourced industry benchmark, or not tracked. | Yield is tracked and within 5–10 points of benchmark. | Yield is at or above a sourced industry benchmark, tracked with monthly reporting. |
| Capacity vs. Projected Demand (Ref: P4) | Capacity is below 100% of projected 12-month demand. | Capacity is 100–120% of projected 12-month demand. | Capacity is ≥120% of projected 12-month demand, or scalable within a 90-day lead time. |

### Q — Quality
*HLV Section Title: Quality*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| QMS Maturity (Ref: Q1) | No certified QMS (e.g., ISO 13485 / 21 CFR 820) where applicable, or certification has lapsed. | Certified, with ≥1 open finding from the most recent audit. | Certified, with zero open findings from the most recent audit. |
| CAPA Effectiveness (Ref: Q1) | >20% of CAPAs are open beyond their target closure date. | 5–20% of CAPAs are overdue. | <5% of CAPAs overdue, or all closed on time. |
| Audit History (Ref: Q2) | ≥1 unresolved finding (e.g., FDA 483, warning letter) in the past 3 years. | Findings were issued but resolved within the applicable regulatory deadline. | Zero adverse findings in the past 3 years. |
| Complaint Handling & Post-Market Surveillance (Ref: Q2) | Average complaint response time >30 days, or no post-market surveillance process exists. | Average response time 10–30 days. | Average response time <10 days, with a documented post-market surveillance process. |

### R — Regulatory and Reimbursements
*HLV Section Title: Regulatory and Reimbursements*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Regulatory Pathway & Approvals (Ref: R1, R2, R6) | No regulatory strategy document exists, or the key clearance/approval application has not been filed and no filing date is set. | Pathway is mapped and the application is filed, with a clear decision timeline pending. | Key clearances/approvals are secured for the current product, with a documented pathway for pipeline products. |
| Reimbursement Infrastructure & Coding (Ref: R3, R4) | No CPT/HCPCS code identified or applied for; no reimbursement/billing pathway exists. | Code(s) identified/applied for; payor coverage is not yet confirmed. | Code(s) secured, with ≥1 payor coverage decision confirmed. |
| Clinical Validation / Data Gaps (Ref: R5) | No control arm exists, or the pre-specified clinical endpoint was not achieved. | Data exists but relies on surrogate endpoints or a sample of <100 subjects. | Peer-reviewed data with clearly achieved statistical power (defined endpoint, sample at or above the pre-specified size). |

### S — Sales and Marketing
*HLV Section Title: Sales and Marketing*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Unit Economics — CAC & LTV (Ref: S3, S4) | LTV/CAC ratio <1.0x, or payback period >24 months, or metrics are not tracked. | LTV/CAC ratio ≈2x; payback period 12–24 months. | LTV/CAC ratio >3x with predictable, short payback (<12 months). |
| Customer Concentration Risk (Ref: M6, S3) | **HARD STOP** — Top 3 customers account for >50% of aggregate revenue. | A single customer's loss would reduce profitability but not breach going-concern status (single customer 10–50% of revenue). | No single customer accounts for >10% of revenue. |
| Sales Pipeline & Conversion Scaling (Ref: S4) | Conversion rate is declining quarter-over-quarter with no documented cause. | Conversion rate is flat quarter-over-quarter. | Conversion rate is stable or improving as pipeline volume scales, with no signs of diminishing returns. |

### T — Technology (R&D)
*HLV Section Title: Technology (R&D)*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| IP Portfolio & Freedom-to-Operate (Ref: T2) | Active infringement claim exists, or 0 owned/core IP protects the technology. | Provisional patents filed; FTO analysis completed but covers <50% of claimed core features. | Issued patents/trade secrets cover ≥80% of core claimed features, with a clean FTO. |
| Architecture Scalability & Technical Debt (Ref: T1, T3) | Architecture cannot scale beyond 2x current volume without a full core rebuild. | Architecture scales to 2–5x current volume using existing/legacy components. | Architecture is demonstrated (via load test or production data) to scale ≥10x current volume with <10% incremental infrastructure cost per unit. |
| Development Methodology & Versioning (Ref: T3) | No documented development methodology, or no version-control/approval process exists. | A methodology and versioning process exist but are inconsistently followed. | A documented methodology (e.g., Agile/Scrum) and version-control/approval process are consistently followed and auditable. |

### U — Details of Assets
*HLV Section Title: Details of Assets*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Tangible / Intangible Title (Ref: U1, U2, U3, U4, U5) | ≥1 material asset has undocumented ownership, or is encumbered by an undisclosed lien. | All assets are documented; ≤10% carry minor tracking gaps. | 100% of assets documented and unencumbered (or encumbrances fully disclosed), with title verified within the past 12 months. |
| Data Capital Governance (Ref: U2) | Proprietary data is collected without a documented consent mechanism, or a known HIPAA/GDPR compliance gap exists. | A governance framework exists but enforcement is <100% (e.g., inconsistent cataloging). | A governance framework is fully enforced with zero known compliance gaps; data is cataloged and access-controlled. |

### V — Details of Liabilities
*HLV Section Title: Details of Liabilities*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Undisclosed / Contingent Liabilities (Ref: V1, V3) | **HARD STOP** — Any liability is found in diligence that was not disclosed by management. | All liabilities are disclosed, but contingent liabilities are not independently quantified or audited. | Zero undisclosed liabilities; all contingent liabilities are quantified and, where material, insured. |
| Debt Maturity & Covenant Compliance (Ref: V1, V2) | Active covenant breach exists, or >50% of debt matures within 12 months with no refinancing plan. | Covenants are currently in compliance but headroom is <10%. | Full covenant compliance with ≥25% headroom; no maturities within 12 months, or refinancing is already arranged. |

### W — Misc Documents
*HLV Section Title: Misc Documents (sic)*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Data Room Internal Consistency (Ref: W1, W2) | ≥3 discrepancies found between data-room files and audited financials/pitch deck. | 1–2 non-material discrepancies found, explained by management. | Zero discrepancies found across all cross-checked documents. |

### X — Exits
*HLV Section Title: Exits*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Strategic M&A Viability (Ref: X1, X2) | 0 identifiable strategic acquirers, or comparable transaction multiples have declined >20% over the trailing 3 years. | ≥1 acquirer identified; comparable multiples are flat to declining <20%. | ≥3 identifiable strategic acquirers, with comparable transaction multiples flat or increasing over the trailing 3 years. |
| Founder / Capital Alignment (Ref: X1) | Founders have explicitly stated an intent to decline a qualifying exit offer (documented lifestyle-business intent). | Alignment is assumed but exit timeline and return expectations are undocumented. | Exit timeline and return expectations are documented and agreed in writing (e.g., term sheet, side letter). |

### Y — Due Diligence Report
*HLV Section Title: Due Diligence Report*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Data Room Completeness (Ref: A–X, aggregate) | <70% of items requested across sections A–X are fulfilled at first request, or core templates (e.g., B1 model, F1 audited financials) are missing. | 70–95% of requested items fulfilled at first request. | ≥95% of requested items fulfilled at first request. |
| Management Responsiveness (Ref: A–X, aggregate) | Average response time to follow-up requests >10 business days. | Average response time 5–10 business days. | Average response time <5 business days. |

### Z — Definitive Legal Agreement
*HLV Section Title: Definitive Legal Agreements (execution and signed)*

| Criterion | Low Confidence (–3 pts) | Mid Confidence (0 pts) | High Confidence (+3 pts) |
|---|---|---|---|
| Voting Control & Shareholder Protections (Ref: Closing docs) | Founders retain unilateral veto/control that eliminates standard investor protective provisions (e.g., no board seat, no protective provisions on major decisions). | Standard protective provisions are present, but ≥1 voting threshold sits above the typical market range (e.g., supermajority >75% required for routine matters). | Full standard protective provisions in place: investor board seat, standard veto rights, and a supermajority threshold ≤67% for major decisions. |
| Conditions Precedent & Structural Guardrails (Ref: Closing docs) | ≥1 mandatory condition precedent has been rejected by management/founders. | Conditions precedent are agreed in principle; ≥1 item has been pending implementation for >30 days. | 100% of conditions precedent satisfied and documented prior to closing. |

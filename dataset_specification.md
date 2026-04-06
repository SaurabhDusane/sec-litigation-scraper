# Securities Litigation Classification Dataset
## Dataset Specification Document

**Project:** Legal AI Case Outcome Prediction  
**Version:** 1.0  
**Date:** February 22, 2026  
**Author:** CIPS Lab

---

## 1. Overview

### 1.1 Research Objective

Build a labeled dataset of securities class action cases to train machine learning models for:
- **Case outcome prediction** (plaintiff win vs defendant win)
- **Category classification** (cryptocurrency vs pharmaceutical/biotech)
- **Text-based legal analysis** (NLP on complaint documents)

### 1.2 Dataset Summary

| Attribute | Value |
|-----------|-------|
| **Total Cases** | 40-50 |
| **Categories** | 2 (Cryptocurrency, Pharmaceutical/Biotech) |
| **Cases per Category** | 20-25 |
| **Outcome Labels** | Binary (win/lose) |
| **Time Period** | 2016-2025 |

---

## 2. Data Sources

### 2.1 Primary Source: Stanford SCAC

**URL:** https://securities.stanford.edu/

**What it provides:**
- Private securities class action lawsuits (shareholder suits)
- Case outcomes (SETTLED, DISMISSED, ONGOING)
- Settlement amounts
- Company/defendant information
- Complaint documents (PDFs)
- Trend category tags (cryptocurrency, COVID-19, AI, etc.)

**Why primary:**
- Contains outcome data (win/lose determination)
- Tracks settlement amounts
- Has trend category filtering
- Provides complaint PDFs for NLP

**Access:** Free registration required for full case details

### 2.2 Secondary Source: SEC Litigation Releases

**URL:** https://www.sec.gov/enforcement-litigation/litigation-releases

**What it provides:**
- SEC enforcement actions (government vs individuals/companies)
- Complaint documents
- Final judgments
- Charges and penalties

**Why secondary (supplementary use):**
- Different plaintiff (SEC vs private shareholders)
- Different outcome metrics (penalties vs settlements)
- Can cross-reference to identify companies facing both actions

**How we'll use SEC data:**
- Cross-reference to enrich Stanford cases
- Identify if a company faced SEC action (additional feature)
- Source complaint text if Stanford version unavailable

### 2.3 Source Selection Rationale

```
┌─────────────────────────────────────────────────────────────┐
│                     DATA SOURCE FLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────────┐         ┌─────────────────┐          │
│   │  Stanford SCAC  │         │  SEC Releases   │          │
│   │   (PRIMARY)     │         │  (SECONDARY)    │          │
│   └────────┬────────┘         └────────┬────────┘          │
│            │                           │                    │
│            ▼                           ▼                    │
│   ┌─────────────────┐         ┌─────────────────┐          │
│   │ • Case outcomes │         │ • Cross-reference│          │
│   │ • Settlements   │         │ • SEC action flag│          │
│   │ • Categories    │         │ • Additional docs│          │
│   │ • Complaints    │         │                  │          │
│   └────────┬────────┘         └────────┬────────┘          │
│            │                           │                    │
│            └───────────┬───────────────┘                    │
│                        ▼                                    │
│               ┌─────────────────┐                          │
│               │  UNIFIED DATASET │                          │
│               │   (40-50 cases)  │                          │
│               └─────────────────┘                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Category Definitions

### 3.1 Category 1: Cryptocurrency / Digital Assets

**Stanford SCAC Trend:** "Cryptocurrency Litigation"

**Inclusion Criteria:**
- Cases tagged under "Cryptocurrency" trend in Stanford SCAC
- Defendants include cryptocurrency exchanges, token issuers, NFT platforms, crypto mining companies, DeFi protocols
- Allegations related to digital asset sales, ICOs, token offerings, crypto-related securities

**Typical Allegations:**
- Unregistered securities offerings (tokens/ICOs)
- Misleading statements about token value or utility
- Exchange liability for listing unregistered securities
- NFT classification as securities
- Cryptocurrency mining fraud

**Example Companies:**
- Coinbase Global, Inc.
- Ripple Labs Inc.
- Block.one
- Binance Holdings
- Yuga Labs (NFTs)

**Available Cases:** 103 total filings (2016-2025)

### 3.2 Category 2: Pharmaceutical / Biotech

**Stanford SCAC Sector/Industry:** "Healthcare" → "Biotechnology & Drugs" / "Pharmaceuticals"

**Inclusion Criteria:**
- Companies in pharmaceutical or biotechnology sectors
- Drug development, clinical trials, FDA-related allegations
- Healthcare services with drug/treatment components

**Typical Allegations:**
- Misleading clinical trial results
- Overstated drug efficacy or safety
- FDA approval misrepresentations
- Failure to disclose adverse events
- Manufacturing/quality control issues

**Example Companies:**
- Emergent BioSolutions Inc.
- Veru Inc.
- Novavax, Inc.
- BioNTech SE
- bluebird bio, Inc.

**Available Cases:** 50+ filings (Healthcare sector, Biotech/Pharma industry)

---

## 4. Outcome Definitions

### 4.1 Binary Outcome Labels

| Label | Value | Definition |
|-------|-------|------------|
| **Win** | 1 | Plaintiff prevailed (settlement reached) |
| **Lose** | 0 | Defendant prevailed (case dismissed) |

### 4.2 Outcome Mapping from Stanford SCAC

| Stanford Status | Outcome Label | Reasoning |
|-----------------|---------------|-----------|
| `SETTLED` | **Win (1)** | Plaintiffs recovered money |
| `DISMISSED` | **Lose (0)** | Case thrown out, no recovery |
| `ONGOING` | **Exclude** | No outcome yet |
| `TRIAL VERDICT - Plaintiff` | **Win (1)** | Rare, plaintiff won at trial |
| `TRIAL VERDICT - Defendant` | **Lose (0)** | Rare, defendant won at trial |

### 4.3 Nuances and Edge Cases

**Partial Dismissals:**
- If case partially dismissed but proceeds → treat as **Ongoing** until final resolution
- If case fully dismissed → **Lose**

**Settlement Amount:**
- Any settlement > $0 → **Win**
- $0 settlement (rare) → Review case details

**Voluntary Dismissal:**
- Plaintiff voluntarily dismisses → **Lose** (typically indicates weak case)

---

## 5. Dataset Schema

### 5.1 Core Fields (Required)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `case_id` | string | Stanford SCAC case identifier | "107456" |
| `category` | string | Case category | "crypto" or "pharma" |
| `filing_name` | string | Company/defendant name | "Coinbase Global, Inc." |
| `filing_date` | date | Date complaint filed | "2022-08-04" |
| `outcome` | integer | Binary label (1=win, 0=lose) | 1 |
| `outcome_status` | string | Raw status from source | "SETTLED" |

### 5.2 Case Details (Recommended)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `district_court` | string | Federal court | "S.D. New York" |
| `exchange` | string | Stock exchange | "NASDAQ" |
| `ticker` | string | Stock symbol | "COIN" |
| `class_period_start` | date | Start of alleged fraud | "2021-04-14" |
| `class_period_end` | date | End of alleged fraud | "2022-07-26" |
| `resolution_date` | date | Date of settlement/dismissal | "2024-03-15" |

### 5.3 Financial Metrics (If Available)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `settlement_amount` | float | Settlement in USD (0 if dismissed) | 27500000.00 |
| `ddl_amount` | float | Disclosure Dollar Loss | 150000000.00 |
| `mdl_amount` | float | Maximum Dollar Loss | 500000000.00 |
| `market_cap` | float | Company market cap at filing | 10000000000.00 |

### 5.4 Enrichment Fields (Optional)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `sec_action` | boolean | Related SEC enforcement exists | true |
| `sec_release_number` | string | SEC release if applicable | "LR-25123" |
| `num_defendants` | integer | Number of named defendants | 5 |
| `lead_plaintiff_firm` | string | Lead plaintiff law firm | "Pomerantz LLP" |
| `allegations_summary` | text | Brief description of claims | "Misleading ICO statements" |

### 5.5 NLP Fields (For Text Analysis)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `complaint_url` | string | URL to complaint PDF | "https://..." |
| `complaint_text` | text | Extracted complaint text | "[Full text]" |
| `complaint_pages` | integer | Number of pages | 85 |

---

## 6. Sample Data Records

### 6.1 Cryptocurrency Cases

```json
{
  "case_id": "105234",
  "category": "crypto",
  "filing_name": "Block.one : Cryptocurrency",
  "filing_date": "2020-04-03",
  "outcome": 1,
  "outcome_status": "SETTLED",
  "district_court": "S.D. New York",
  "exchange": "N/A",
  "ticker": "N/A",
  "settlement_amount": 27500000.00,
  "allegations_summary": "Alleged unregistered ICO raising $4 billion for EOS tokens",
  "sec_action": true,
  "sec_release_number": "LR-24636"
}
```

```json
{
  "case_id": "106891",
  "category": "crypto",
  "filing_name": "Riot Blockchain, Inc.",
  "filing_date": "2018-02-17",
  "outcome": 0,
  "outcome_status": "DISMISSED",
  "district_court": "D. New Jersey",
  "exchange": "NASDAQ",
  "ticker": "RIOT",
  "settlement_amount": 0,
  "allegations_summary": "Alleged pump-and-dump scheme related to crypto pivot",
  "sec_action": false
}
```

### 6.2 Pharmaceutical/Biotech Cases

```json
{
  "case_id": "104567",
  "category": "pharma",
  "filing_name": "Emergent BioSolutions Inc.",
  "filing_date": "2021-04-19",
  "outcome": 1,
  "outcome_status": "SETTLED",
  "district_court": "D. Maryland",
  "exchange": "NYSE",
  "ticker": "EBS",
  "settlement_amount": 40000000.00,
  "allegations_summary": "Alleged misleading statements about COVID vaccine manufacturing",
  "sec_action": false
}
```

```json
{
  "case_id": "106432",
  "category": "pharma",
  "filing_name": "Veru Inc.",
  "filing_date": "2022-12-05",
  "outcome": 0,
  "outcome_status": "DISMISSED",
  "district_court": "S.D. Florida",
  "exchange": "NASDAQ",
  "ticker": "VERU",
  "settlement_amount": 0,
  "allegations_summary": "Alleged misleading statements about COVID treatment drug",
  "sec_action": false
}
```

---

## 7. Data Collection Process

### 7.1 Step-by-Step Workflow

```
Step 1: Access Stanford SCAC
├── Register for free account
├── Navigate to Advanced Search
└── Export case lists

Step 2: Filter Cryptocurrency Cases
├── Go to Current Trends → Cryptocurrency
├── Filter by Status: SETTLED or DISMISSED
├── Export 25-30 cases (buffer for quality)
└── Record case IDs

Step 3: Filter Pharmaceutical Cases
├── Go to Filings Database
├── Filter by Sector: Healthcare
├── Filter by Industry: Biotechnology & Drugs
├── Filter by Status: SETTLED or DISMISSED
├── Export 25-30 cases
└── Record case IDs

Step 4: Collect Case Details
├── For each case ID, visit case page
├── Extract all schema fields
├── Download complaint PDF
└── Record in structured format

Step 5: Cross-Reference SEC (Optional)
├── Search SEC releases for company names
├── Flag cases with parallel SEC action
├── Add SEC release numbers
└── Note any additional information

Step 6: Quality Control
├── Verify outcome labels
├── Check for missing data
├── Balance win/lose distribution
└── Final review: 20-25 per category
```

### 7.2 Expected Time Investment

| Task | Estimated Time |
|------|----------------|
| Stanford account setup | 10 minutes |
| Cryptocurrency case collection | 2-3 hours |
| Pharmaceutical case collection | 2-3 hours |
| SEC cross-reference | 1-2 hours |
| Quality control & validation | 1 hour |
| **Total** | **6-9 hours** |

---

## 8. Quality Criteria

### 8.1 Inclusion Criteria

- [ ] Case has clear resolution (SETTLED or DISMISSED)
- [ ] Resolution occurred (not appealed/ongoing)
- [ ] Case fits category definition
- [ ] Basic metadata available (filing date, court, company)
- [ ] Complaint document accessible

### 8.2 Exclusion Criteria

- [ ] Case still ongoing
- [ ] Outcome unclear or partial
- [ ] Case transferred/consolidated (use lead case only)
- [ ] Duplicate filing (same company, same allegations)
- [ ] Non-federal case (state court only)

### 8.3 Balance Targets

| Category | Target Total | Target Wins | Target Losses |
|----------|-------------|-------------|---------------|
| Cryptocurrency | 20-25 | 10-12 | 10-13 |
| Pharmaceutical | 20-25 | 10-12 | 10-13 |

**Note:** Natural distribution may not be 50/50. Document actual distribution and consider stratified sampling if needed.

---

## 9. File Formats

### 9.1 Primary Dataset File

**Filename:** `securities_litigation_dataset.csv`

```csv
case_id,category,filing_name,filing_date,outcome,outcome_status,district_court,exchange,ticker,settlement_amount,allegations_summary
107456,crypto,Block.one,2020-04-03,1,SETTLED,S.D. New York,N/A,N/A,27500000.00,Alleged unregistered ICO
106891,crypto,Riot Blockchain,2018-02-17,0,DISMISSED,D. New Jersey,NASDAQ,RIOT,0,Pump-and-dump allegations
104567,pharma,Emergent BioSolutions,2021-04-19,1,SETTLED,D. Maryland,NYSE,EBS,40000000.00,COVID vaccine manufacturing
```

### 9.2 JSON Format (Alternative)

**Filename:** `securities_litigation_dataset.json`

```json
{
  "metadata": {
    "created_date": "2026-02-22",
    "version": "1.0",
    "total_cases": 45,
    "categories": ["crypto", "pharma"],
    "sources": ["Stanford SCAC", "SEC Litigation Releases"]
  },
  "cases": [
    {
      "case_id": "107456",
      "category": "crypto",
      ...
    }
  ]
}
```

### 9.3 Document Storage

```
/data/
├── securities_litigation_dataset.csv
├── securities_litigation_dataset.json
├── complaints/
│   ├── crypto/
│   │   ├── 107456_block_one_complaint.pdf
│   │   ├── 106891_riot_blockchain_complaint.pdf
│   │   └── ...
│   └── pharma/
│       ├── 104567_emergent_complaint.pdf
│       └── ...
└── extracted_text/
    ├── 107456_complaint.txt
    └── ...
```

---

## 10. Usage Guidelines

### 10.1 For Classification Tasks

```python
import pandas as pd
from sklearn.model_selection import train_test_split

# Load dataset
df = pd.read_csv('securities_litigation_dataset.csv')

# Split by category for category classification
X = df['complaint_text']  # or other features
y_category = df['category']  # 'crypto' vs 'pharma'

# Split by outcome for outcome prediction
y_outcome = df['outcome']  # 1 (win) vs 0 (lose)

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y_outcome, test_size=0.2, stratify=y_outcome
)
```

### 10.2 For NLP Analysis

```python
# Load complaint texts
complaints = []
for _, row in df.iterrows():
    with open(f"complaints/{row['category']}/{row['case_id']}_complaint.txt") as f:
        complaints.append(f.read())

df['complaint_text'] = complaints

# Feature extraction examples:
# - TF-IDF vectors
# - Named entity recognition (companies, people, laws)
# - Legal citation extraction
# - Sentiment analysis on allegations
```

---

## 11. Limitations and Considerations

### 11.1 Known Limitations

1. **Selection Bias:** Resolved cases may differ from ongoing cases
2. **Settlement ≠ Merit:** Some settlements occur to avoid litigation costs, not due to strong claims
3. **Dismissal Reasons Vary:** Some dismissals are procedural, not merit-based
4. **Time Period Effects:** Market conditions and legal standards evolve
5. **Category Overlap:** Some crypto companies are also biotech (rare)

### 11.2 Ethical Considerations

- Data is from public court filings
- No personally identifiable information beyond public record
- Academic/research use only
- Cite sources appropriately

### 11.3 Future Enhancements

- [ ] Add more categories (AI, SPAC, Data Breach)
- [ ] Include appeal outcomes
- [ ] Add judge-level features
- [ ] Incorporate SEC enforcement outcomes
- [ ] Extract structured allegations from complaint text

---

## 12. References

### Data Sources

1. Stanford Law School Securities Class Action Clearinghouse  
   https://securities.stanford.edu/

2. SEC Litigation Releases  
   https://www.sec.gov/enforcement-litigation/litigation-releases

### Research Reports

3. "Securities Class Action Filings: 2025 Midyear Assessment"  
   Cornerstone Research & Stanford Law School

4. "Securities Class Action Settlements: 2024 Review and Analysis"  
   Cornerstone Research & Stanford Law School

### Legal Background

5. Securities Act of 1933, Section 11  
6. Securities Exchange Act of 1934, Section 10(b) and Rule 10b-5

---

*Document version 1.0 | Last updated: February 22, 2026*

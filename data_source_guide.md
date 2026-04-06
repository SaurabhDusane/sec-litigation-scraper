# Data Source Quick Reference Guide

## Which Source for What?

### Short Answer

| Data Need | Primary Source | Secondary Source |
|-----------|---------------|------------------|
| **Case outcomes (win/lose)** | Stanford SCAC | - |
| **Settlement amounts** | Stanford SCAC | - |
| **Category filtering** | Stanford SCAC | - |
| **Complaint documents** | Stanford SCAC | SEC (backup) |
| **SEC enforcement flag** | SEC Releases | - |
| **Charges/penalties detail** | SEC Releases | - |

---

## Stanford SCAC (PRIMARY - 90% of your data)

**Use for:**
- ✅ Finding cases in cryptocurrency and pharma categories
- ✅ Getting case outcomes (SETTLED vs DISMISSED)
- ✅ Settlement amounts
- ✅ Case metadata (court, dates, company info)
- ✅ Downloading complaint PDFs
- ✅ Trend category tags

**URL:** https://securities.stanford.edu/

**Access:** Free registration required

---

## SEC Litigation Releases (SECONDARY - Enrichment only)

**Use for:**
- ✅ Cross-referencing: "Did this company also face SEC action?"
- ✅ Adding `sec_action` boolean field to your dataset
- ✅ Backup source for complaint documents
- ✅ Additional context on serious fraud cases

**NOT used for:**
- ❌ Primary case selection
- ❌ Win/lose determination (different legal standard)
- ❌ Settlement amounts (SEC uses penalties/disgorgement)

**URL:** https://www.sec.gov/enforcement-litigation/litigation-releases

**Access:** Fully public, no registration

---

## Why This Approach?

### Stanford SCAC = Private Class Actions
```
Plaintiff: Shareholders (private investors)
Defendant: Companies and executives  
Outcome: Settlement (win) or Dismissal (lose)
Goal: Monetary damages for investor losses
```

### SEC = Government Enforcement
```
Plaintiff: SEC (federal government)
Defendant: Companies and individuals
Outcome: Penalties, bars, disgorgement
Goal: Regulatory enforcement and deterrence
```

**Key insight:** These are *different types of litigation*. A company can face:
- Only a private class action (Stanford)
- Only an SEC action
- Both (cross-reference opportunity!)

For your **outcome prediction task**, Stanford SCAC provides consistent win/lose labels based on settlement vs dismissal—exactly what you need.

---

## Workflow Summary

```
1. START with Stanford SCAC
   ├── Filter: Cryptocurrency trend → get 25-30 resolved cases
   ├── Filter: Healthcare/Biotech sector → get 25-30 resolved cases
   └── Extract: outcome, settlement amount, metadata

2. ENRICH with SEC (optional)
   ├── For each company, search SEC releases
   ├── If found: set sec_action = true, add release number
   └── If not found: set sec_action = false

3. RESULT: Unified dataset
   └── 40-50 cases, primarily from Stanford, enriched with SEC flags
```

---

## Data Field Sources

| Field | Source |
|-------|--------|
| `case_id` | Stanford SCAC |
| `category` | Stanford SCAC (trend tag / sector) |
| `filing_name` | Stanford SCAC |
| `filing_date` | Stanford SCAC |
| `outcome` | Stanford SCAC (SETTLED=1, DISMISSED=0) |
| `outcome_status` | Stanford SCAC |
| `district_court` | Stanford SCAC |
| `exchange` | Stanford SCAC |
| `ticker` | Stanford SCAC |
| `settlement_amount` | Stanford SCAC |
| `ddl_amount` | Stanford SCAC |
| `mdl_amount` | Stanford SCAC |
| `complaint_url` | Stanford SCAC |
| `complaint_text` | Stanford SCAC (PDF extraction) |
| `sec_action` | SEC Releases (cross-reference) |
| `sec_release_number` | SEC Releases |

---

## Example: How the Sources Connect

**Case: Block.one (Cryptocurrency ICO)**

**From Stanford SCAC:**
```
Case ID: 105234
Filing Name: Block.one : Cryptocurrency  
Filing Date: 2020-04-03
Status: SETTLED
Settlement: $27,500,000
Court: S.D. New York
→ outcome = 1 (win)
```

**From SEC Releases:**
```
Release: LR-24636 (September 2019)
Defendant: Block.one
Charges: Unregistered ICO
Penalty: $24,000,000 civil penalty
→ sec_action = true
```

**Combined Record:**
```json
{
  "case_id": "105234",
  "category": "crypto",
  "filing_name": "Block.one",
  "outcome": 1,
  "settlement_amount": 27500000,
  "sec_action": true,
  "sec_release_number": "LR-24636"
}
```

---

## Getting Started Checklist

- [ ] Register for Stanford SCAC account (free)
- [ ] Access Advanced Search or Filings List
- [ ] Filter by Cryptocurrency trend → note resolved cases
- [ ] Filter by Healthcare sector → note resolved cases
- [ ] For each case, record outcome and metadata
- [ ] (Optional) Cross-reference with SEC for enrichment
- [ ] Compile into CSV/JSON dataset

---

*Ready to collect data? Start at: https://securities.stanford.edu/sign-up.html*

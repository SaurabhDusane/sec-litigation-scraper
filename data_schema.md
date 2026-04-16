# SEC Litigation Data Schema

## Overview

Two schemas:

1. **Source Schema** — the raw 39-column CSV as scraped from SEC.gov
2. **Target Schema** — a lean 15-column dataset built from the raw data through cleaning, selection, and feature engineering

---

## Source Schema (Raw CSV)

`sec_litigation_releases_20260403_234416.csv` — 10,914 rows × 39 columns

All fields are strings. Multi-valued fields use semicolons (`;`) as delimiters.

| # | Column | Coverage | Multi-valued? | Description |
|---|--------|----------|---------------|-------------|
| 1 | `case_title` | 100% | No | Full case caption |
| 2 | `citation` | 100% | No | Release number and civil action number |
| 3 | `court` | 89.1% | No | Federal district court abbreviation |
| 4 | `date` | 100% | No | Release date (text, e.g. "March 18, 2026") |
| 5 | `petitioner` | 100% | No | Always "SEC" — zero information |
| 6 | `respondent` | 100% | Rarely | Defendant name(s) |
| 7 | `defendant_roles` | 80.0% | Yes | Professional titles ("CEO; Director") |
| 8 | `defendant_employer` | 21.6% | Rarely | Employer or affiliated firm |
| 9 | `employer_crd_cik` | 0.3% | Rarely | FINRA CRD or SEC CIK |
| 10 | `co_defendants` | 0.0% | — | **Empty column** |
| 11 | `relief_defendants` | 4.8% | Yes | Parties receiving misappropriated funds |
| 12 | `sec_attorneys` | 24.8% | Yes | Investigating attorneys |
| 13 | `sec_regional_office` | 24.3% | No | Handling SEC office |
| 14 | `judges` | 25.9% | Rarely | Presiding judge(s) |
| 15 | `judgment_type` | 94.6% | Sometimes | Complaint / Consent / Default / Final / Summary |
| 16 | `summary` | 100% | — | Full case narrative (avg 3,367 chars) |
| 17 | `outcome` | 94.5% | Yes | Legal outcomes ("Disgorgement; Permanent Injunction") |
| 18 | `legal_topic` | 98.5% | Yes | Violation categories ("Insider Trading; Securities Fraud") |
| 19 | `charges_and_sections` | 87.9% | Yes | Statutory citations ("Exchange Act § 10(b); Rule 10b-5") |
| 20 | `company_domain` | 83.3% | Sometimes | Industry sector |
| 21 | `total_fine_amount` | 32.8% | Yes | Penalty breakdown in text |
| 22 | `total_victim_losses` | 5.6% | No | Aggregate investor losses |
| 23 | `scheme_duration` | 30.6% | No | Time span of the fraud (text) |
| 24 | `scheme_method` | 84.2% | No | How the fraud was conducted |
| 25 | `victim_count` | 21.5% | No | Number of affected parties (text) |
| 26 | `admission_status` | 60.5% | No | "Consented" / "Without admitting or denying" |
| 27 | `parallel_actions` | 88.7% | No | Related criminal/admin proceedings |
| 28 | `related_releases` | 95.7% | Sometimes | Linked release numbers |
| 29 | `case_status` | 93.7% | Sometimes | Procedural status |
| 30 | `scheme_start_date` | 30.6% | No | When fraud began |
| 31 | `scheme_end_date` | 30.6% | No | When fraud ended |
| 32 | `complaint_filed_date` | 11.0% | No | When SEC filed complaint |
| 33 | `judgment_date` | 8.2% | No | When court entered judgment |
| 34 | `regulatory_registrations` | 4.7% | Yes | FINRA series registrations |
| 35 | `defendant_sentence` | 7.6% | No | Criminal sentence |
| 36 | `final_judgment_details` | 31.4% | Sometimes | Court orders and injunctions |
| 37 | `source_url` | 100% | No | URL to original release |
| 38 | `pdf_insights` | 45.9% | No | Extracted amounts and entities from PDFs |
| 39 | `associated_documents` | 47.2% | Sometimes | PDF document names |

### Known Issues in Source

- All values are untyped strings
- Multi-valued delimiter (`;`) is inconsistent (spaces vary)
- Monetary amounts embedded in text ("Disgorgement: $2,860,000")
- Dates in multiple text formats ("March 18, 2026" vs "January 2016")
- 1 entirely empty column (`co_defendants`)
- OCR page-break markers in `summary`
- ~2.4% near-duplicate summaries

---

## Target Schema (15 Columns)

### Column Map

| # | Target Column | Type | Source Column(s) | How It's Built |
|---|---------------|------|------------------|----------------|
| 1 | `case_id` | string | `citation` | Extract release number (e.g. "LR-26503") |
| 2 | `case_title` | string | `case_title` | Trim whitespace |
| 3 | `release_date` | date | `date` | Parse to ISO-8601 (`2026-03-18`) |
| 4 | `year` | int | `date` | **Engineered** — extract year from parsed date |
| 5 | `court` | string | `court` | Normalize abbreviations to standard form |
| 6 | `primary_topic` | string | `legal_topic` | First value before `;` — **Classification Target 1** |
| 7 | `primary_status` | string | `case_status` | First value before `;` — **Classification Target 2** |
| 8 | `primary_domain` | string | `company_domain` | First value before `;` — **Classification Target 3** |
| 9 | `summary_clean` | string | `summary` | Remove OCR markers, collapse whitespace, cap 6000 chars |
| 10 | `judgment_type` | string | `judgment_type` | First value before `;` (Complaint/Consent/Final/Default/Summary) |
| 11 | `admission_status` | string | `admission_status` | As-is categorical |
| 12 | `num_charges` | int | `charges_and_sections` | **Engineered** — count of statutes cited (split on `;`) |
| 13 | `has_criminal_parallel` | bool | `parallel_actions` | **Engineered** — `true` if text contains "Criminal" |
| 14 | `total_fine_usd` | float | `total_fine_amount` | **Engineered** — extract largest dollar amount from text |
| 15 | `summary_length` | int | `summary` | **Engineered** — word count of cleaned summary |

### Why These 15?

**Identifiers (2):** `case_id`, `case_title` — needed to trace rows back to source

**Temporal (2):** `release_date`, `year` — when the case happened; `year` is a direct ML feature for trend-aware models

**Categorical features (4):** `court`, `judgment_type`, `admission_status`, `has_criminal_parallel` — structured signals that influence case outcomes. Courts have different dismissal rates; consent judgments behave differently from default judgments; criminal parallel actions correlate with harsher civil outcomes

**Classification targets (3):** `primary_topic`, `primary_status`, `primary_domain` — the three prediction tasks

**Text feature (1):** `summary_clean` — the primary text source for TF-IDF / embeddings

**Engineered numeric (3):** `num_charges`, `total_fine_usd`, `summary_length` — continuous features derived from messy source fields:

- `num_charges`: Cases citing more statutes tend to be more complex and more likely to settle
- `total_fine_usd`: Extracted from text like "Disgorgement: $2,860,000; Civil Penalty: $150,000" → `2860000.0` (takes the max)
- `summary_length`: Longer summaries correlate with more complex, multi-defendant cases

### What Got Dropped (and Why)

| Dropped Column | Reason |
|----------------|--------|
| `petitioner` | Constant ("SEC") — zero predictive value |
| `co_defendants` | Entirely empty |
| `employer_crd_cik` | 0.3% coverage |
| `relief_defendants` | 4.8% coverage |
| `regulatory_registrations` | 4.7% coverage |
| `total_victim_losses` | 5.6% coverage |
| `defendant_sentence` | 7.6% coverage |
| `judgment_date` | 8.2% coverage |
| `complaint_filed_date` | 11.0% coverage |
| `respondent` | Name of defendant — useful for lookup but not a feature |
| `defendant_roles` | 80% coverage, but high cardinality and noisy; information captured by `primary_domain` |
| `defendant_employer` | 21.6% coverage, free-text, noisy |
| `outcome` | 94.5% but heavily overlaps with `primary_status` and `judgment_type` |
| `legal_topic` (full) | Replaced by `primary_topic`; full array available via source |
| `charges_and_sections` (full) | Replaced by `num_charges`; raw text used for TF-IDF at modeling time |
| `scheme_method` | 84.2% but avg 1,150 chars — redundant with `summary_clean` |
| `scheme_duration`, `scheme_start/end_date` | 30.6% coverage; could be derived from summary if needed |
| `parallel_actions` (full text) | Replaced by boolean `has_criminal_parallel` |
| `related_releases` | Graph-only; not a feature |
| `source_url` | Reference only |
| `pdf_insights`, `final_judgment_details`, `associated_documents` | Enrichment text; redundant with summary |
| `sec_attorneys`, `sec_regional_office`, `judges` | <26% coverage; graph-enrichment only |

---

## Feature Engineering Details

### `case_id` — from `citation`

```
Source:  "Litigation Release No. 26503 / 21-civ-19387 (D.N.J.)"
Target: "LR-26503"
Logic:  regex extract first number after "No." or "No", prepend "LR-"
```

### `release_date` / `year` — from `date`

```
Source:  "March 18, 2026"
Target: release_date = 2026-03-18, year = 2026
Logic:  dateutil.parser.parse() with fallback
```

### `num_charges` — from `charges_and_sections`

```
Source:  "Exchange Act § 10(b); Rule 10b-5; Securities Act § 17(a)"
Target: 3
Logic:  split(";"), count non-empty elements
```

### `has_criminal_parallel` — from `parallel_actions`

```
Source:  "Criminal: U.S. Attorney's Office announced criminal charges"
Target: true
Logic:  case-insensitive search for "criminal" in text
```

### `total_fine_usd` — from `total_fine_amount`

```
Source:  "Disgorgement: $2,860,000; Prejudgment Interest: $340,523; Civil Penalty: $150,000"
Target: 2860000.0
Logic:  regex extract all dollar amounts → parse → take maximum
```

### `summary_length` — from `summary`

```
Source:  (3,367-character summary text)
Target: 502
Logic:  len(summary_clean.split())
```

### `summary_clean` — from `summary`

```
Source:  "--- BEGINNING OF PAGE #2 ---  The defendant   allegedly..."
Target: "The defendant allegedly..."
Logic:  strip OCR markers (regex), collapse whitespace, cap at 6000 chars
```

---

## Transformation Pipeline

```
Raw CSV (39 columns, all strings)
    │
    ├── SELECT 10 source columns
    │     case_title, citation, date, court, legal_topic,
    │     case_status, company_domain, judgment_type,
    │     admission_status, summary
    │
    ├── REFERENCE 3 more for feature engineering
    │     charges_and_sections, parallel_actions, total_fine_amount
    │
    ├── PARSE & CLEAN
    │     • dates → ISO-8601
    │     • multi-valued → take first value
    │     • summary → strip OCR, collapse whitespace
    │
    ├── ENGINEER 5 new columns
    │     case_id, year, num_charges,
    │     has_criminal_parallel, total_fine_usd, summary_length
    │
    └── OUTPUT (15 columns, typed)
          → Parquet (ML-ready, typed)
          → JSON    (graph-ready)
          → CSV     (inspection)
```

---

## ML Feature Matrix (at modeling time)

At training time, the 15-column dataset expands into the feature matrix:

| Feature Group | Derived From | Dimensions | Method |
|---------------|-------------|------------|--------|
| Text | `summary_clean` | ~10,000 | TF-IDF (1,2-grams) |
| Court | `court` | ~15 | One-hot encoding (top courts + Other) |
| Judgment Type | `judgment_type` | ~5 | One-hot encoding |
| Admission | `admission_status` | ~3 | One-hot encoding |
| Numeric | `num_charges`, `total_fine_usd`, `summary_length`, `year` | 4 | StandardScaler |
| Boolean | `has_criminal_parallel` | 1 | 0/1 |
| **Total** | | **~10,028** | |

### Targets

| Target | Column | Classes |
|--------|--------|---------|
| Task 1 | `primary_topic` | 16 (Insider Trading, Securities Fraud, …) |
| Task 2 | `primary_status` | 6 (Settled, Complaint filed, Final judgment, …) |
| Task 3 | `primary_domain` | 18 (Banking, Brokerage, Tech, …) |

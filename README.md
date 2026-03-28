# SEC Litigation Release Scraper

A scalable data extraction pipeline for SEC.gov enforcement litigation releases. The system scrapes case listing pages, navigates to individual case detail pages, downloads and analyzes associated PDF documents (Final Judgments, SEC Complaints, Consent Orders), and extracts 39 structured fields per case into a SQLite database. Designed for knowledge graph construction and legal NLP research.

---

## Table of Contents

- [Architecture](#architecture)
- [Technical Challenge: SEC.gov WAF Bypass](#technical-challenge-secgov-waf-bypass)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Output Schema (39 Fields)](#output-schema-39-fields)
- [Knowledge Graph Applications](#knowledge-graph-applications)
- [PDF Analysis Pipeline](#pdf-analysis-pipeline)
- [HPC Deployment (ASU Sol)](#hpc-deployment-asu-sol)
- [Project Structure](#project-structure)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Architecture

```
SEC.gov
  |
  |-- RSS Feed (/litigation-releases/rss)
  |-- HTML Listing Pages (paginated, ~20 entries per page)
  |
  v
+---------------------------------------------------------------+
|  Pipeline Orchestrator (async, 3-6 concurrent workers)        |
|                                                               |
|  For each entry:                                              |
|    1. Check SQLite -- skip if already scraped (dedup)         |
|    2. Fetch detail page via curl                              |
|    3. Run 24 regex extractors against page HTML               |
|    4. Discover PDF links (judgments, complaints, orders)      |
|    5. For each PDF:                                           |
|       a. Download via curl                                    |
|       b. Extract text with pdfplumber (up to 200 pages)       |
|       c. Run all 24 extractors against PDF text               |
|       d. Merge results into case record                       |
|       e. Extract narrative paragraphs for summary enrichment  |
|       f. Delete PDF from disk                                 |
|    6. Write case to SQLite (immediate commit)                 |
+---------------------------------------------------------------+
  |
  v
SQLite Database (sec_litigation.db)
  |
  |-- Export: CSV (flat tabular)
  |-- Export: JSON (with array fields for graph ingestion)
  |-- Export: SQLite (queryable, portable)
```

---

## Technical Challenge: SEC.gov WAF Bypass

SEC.gov employs Akamai's Web Application Firewall (WAF), which performs TLS ClientHello fingerprinting (JA3/JA4 hashing) on incoming connections. Requests originating from datacenter IP ranges -- including university HPC clusters -- are categorically blocked with HTTP 403, regardless of request headers.

Three HTTP client implementations were tested on ASU's Sol supercomputer before identifying a working approach:

| Implementation | TLS Stack | Result |
|----------------|-----------|--------|
| Playwright (headless Chromium) | BoringSSL | HTTP 403 |
| Python `requests` library | urllib3 / OpenSSL bindings | HTTP 403 |
| System `curl` (subprocess) | Native OpenSSL 3.0.13 | HTTP 200 |

The solution uses system `curl` via `asyncio.create_subprocess_exec()` for all HTTP operations. Curl's native OpenSSL TLS handshake produces a JA3 fingerprint that the WAF accepts, even from datacenter IPs. HTML parsing (BeautifulSoup) and PDF text extraction (pdfplumber) remain in Python.

---

## Requirements

**System requirements:**
- Python 3.9 or later
- curl (pre-installed on Linux, macOS, and most HPC environments)

**Python dependencies (3 packages):**
- `beautifulsoup4` -- HTML parsing
- `pdfplumber` -- PDF text extraction
- `lxml` -- fast XML/HTML parser backend for BeautifulSoup

All other imports (`asyncio`, `sqlite3`, `csv`, `json`, `re`, `subprocess`, `hashlib`, `argparse`, `dataclasses`, `xml.etree.ElementTree`) are Python standard library.

---

## Installation

```bash
git clone https://github.com/SaurabhDusane/sec-litigation-scraper.git
cd sec-litigation-scraper
pip install -r requirements.txt
```

Verify curl is available:

```bash
curl --version
```

No browser binaries, Chromium installations, or display servers are required.

---

## Usage

The scraper provides three subcommands: `scrape`, `export`, and `status`.

### Scraping

```bash
# Scrape the first page of listings (approximately 20 cases)
python sec_litigation_scraper_v8.py scrape

# Scrape 10 pages with 3 concurrent workers
python sec_litigation_scraper_v8.py scrape --pages 10 --workers 3

# Scrape the full archive (all available pages)
python sec_litigation_scraper_v8.py scrape --all --workers 5

# Incremental update: stop when reaching cases already in the database
python sec_litigation_scraper_v8.py scrape --incremental

# Filter by year and month
python sec_litigation_scraper_v8.py scrape --year 2026 --month 3 --pages 2

# Use RSS feed only (fastest, approximately 20 most recent releases)
python sec_litigation_scraper_v8.py scrape --rss-only
```

All scrape operations are **crash-safe**. If the process is interrupted (SLURM walltime, network failure, Ctrl+C), re-running the same command resumes from the last completed case. Cases already in the database are skipped automatically.

### Exporting

```bash
# Export to CSV
python sec_litigation_scraper_v8.py export --format csv -o sec_cases

# Export to JSON (array fields for Neo4j / knowledge graph ingestion)
python sec_litigation_scraper_v8.py export --format json -o sec_cases

# Export both formats
python sec_litigation_scraper_v8.py export --format both -o sec_cases
```

The JSON export converts semicolon-delimited fields into proper arrays. For example, `charges_and_sections` becomes `["Exchange Act Section 10(b)", "Rule 10b-5"]` instead of a flat string. This format is directly compatible with Neo4j's `apoc.load.json` and similar graph database import tools.

### Database Status

```bash
python sec_litigation_scraper_v8.py status
```

Displays total case count, latest scrape date, database size, success/error counts, and the top legal topics and courts by frequency.

### Scrape Command Options

| Flag | Default | Description |
|------|---------|-------------|
| `--pages N` | 1 | Number of listing pages to scrape |
| `--workers N` | 3 | Concurrent worker count (maximum: 6) |
| `--db FILE` | sec_litigation.db | SQLite database file path |
| `--year YYYY` | All | Filter by year |
| `--month M` | All | Filter by month (1-12) |
| `--rss-only` | Off | Scrape RSS feed only |
| `--incremental` | Off | Stop at first known case |
| `--all` | Off | Scrape all available pages |

---

## Output Schema (39 Fields)

### Core Identifiers

| Field | Description | Example |
|-------|-------------|---------|
| `case_title` | Full case caption | Securities and Exchange Commission v. Kenneth Welsh |
| `citation` | Release number and civil action number | Litigation Release No. 26503 / 21-civ-19387 (D.N.J.) |
| `court` | Federal district court abbreviation | D.N.J. |
| `date` | Release date | March 18, 2026 |

### Parties and Roles

| Field | Description | Example |
|-------|-------------|---------|
| `petitioner` | Plaintiff (always SEC) | Securities and Exchange Commission (SEC) |
| `respondent` | Defendant name(s) | Kenneth Welsh |
| `defendant_roles` | Professional titles and registrations | Registered Representative; Investment Adviser Representative |
| `defendant_employer` | Employer or affiliated firm | Wells Fargo Clearing Services, LLC |
| `employer_crd_cik` | FINRA CRD or SEC CIK identifier | CRD# 19616 |
| `co_defendants` | Additional named defendants | |
| `relief_defendants` | Parties who received misappropriated funds | |

### SEC Enforcement

| Field | Description | Example |
|-------|-------------|---------|
| `sec_attorneys` | Investigating and litigating attorneys | John Lehmann; Vanessa De Simone; Lara S. Mehraban |
| `sec_regional_office` | Handling SEC office | New York Regional Office |

### Judicial

| Field | Description | Example |
|-------|-------------|---------|
| `judges` | Presiding judge(s) | James V. Selna |
| `judgment_type` | Classification of judgment | Consent Judgment / Default Judgment / Final Judgment |

### Substantive

| Field | Description | Example |
|-------|-------------|---------|
| `summary` | Full case narrative including PDF-extracted details | (unlimited length) |
| `outcome` | Classified legal outcomes | Civil Penalty; Disgorgement; Final Judgment; Permanent Injunction |
| `legal_topic` | Fraud type and violation classification | Inv. Adviser Misconduct; Misappropriation; Securities Fraud |
| `charges_and_sections` | All statutory violations cited | Securities Act Section 17(a)(1); Exchange Act Section 10(b); Rule 10b-5; Advisers Act Section 206(1) |
| `company_domain` | Industry or sector of the prosecuted entity | Brokerage / Crypto/Digital Assets / Pharmaceuticals |

### Financial

| Field | Description | Example |
|-------|-------------|---------|
| `total_fine_amount` | Structured penalty breakdown | Disgorgement: $2,860,000; Prejudgment Interest: $340,523; Civil Penalty: $150,000 |
| `total_victim_losses` | Aggregate losses suffered by investors | $2.86 million |

### Scheme Details

| Field | Description | Example |
|-------|-------------|---------|
| `scheme_duration` | Time span of the fraudulent conduct | January 2016 to January 2021 |
| `scheme_method` | Description of how the fraud was conducted | transferring funds to credit card accounts held in the names of family members |
| `victim_count` | Number or description of affected parties | multiple clients and customers, some of whom were senior citizens |
| `admission_status` | Whether the defendant admitted or denied allegations | Without admitting or denying / Pleaded guilty |

### Cross-References

| Field | Description | Example |
|-------|-------------|---------|
| `parallel_actions` | Related criminal, administrative, or FINRA proceedings | Criminal: U.S. Attorney's Office for D.N.J. announced criminal charges |
| `related_releases` | Linked litigation release and AAER numbers | LR-25251; AAER-4583 |
| `case_status` | Current procedural status | Final judgment entered; Settled/Consented |

### Temporal Chain

| Field | Description | Example |
|-------|-------------|---------|
| `scheme_start_date` | When the fraudulent conduct began | January 2016 |
| `scheme_end_date` | When the fraudulent conduct ended | January 2021 |
| `complaint_filed_date` | When the SEC filed the complaint | October 28, 2021 |
| `judgment_date` | When the court entered judgment | March 16, 2026 |

### Regulatory and Criminal

| Field | Description | Example |
|-------|-------------|---------|
| `regulatory_registrations` | FINRA series registrations and licenses | Series 7; Series 31 |
| `defendant_sentence` | Criminal sentence from parallel prosecution | sentenced to, among other things, 44 months' imprisonment |

### Document Analysis

| Field | Description | Example |
|-------|-------------|---------|
| `final_judgment_details` | Full text of court orders, injunctions, and bars | Injunction: permanently enjoins Welsh from future violations... |
| `source_url` | URL of the litigation release detail page | https://www.sec.gov/enforcement-litigation/litigation-releases/lr-26503 |
| `pdf_insights` | Monetary amounts, key dates, transaction counts, entities | Amounts: $2.86 million; Transactions: at least 137 fraudulent transactions |
| `associated_documents` | Names of PDF documents analyzed for this case | Final Judgment; SEC Complaint |

---

## Knowledge Graph Applications

The 39 extracted fields support the following entity-relationship model for graph construction:

```
Person    --[employed_at]-->          Company
Person    --[held_role]-->            Role
Person    --[held_registration]-->    Registration (Series 7, Series 31)
Case      --[charged_under]-->        Statute (Securities Act Section 17(a), Rule 10b-5)
Case      --[filed_in]-->            Court (D.N.J., S.D.N.Y.)
Case      --[presided_by]-->         Judge
Case      --[investigated_by]-->     SEC Attorney
Case      --[handled_by]-->          SEC Regional Office
Case      --[parallel_to]-->         Criminal Case
Case      --[follows_from]-->        Related Litigation Release
Case      --[resulted_in]-->         Penalty (Disgorgement, Civil Penalty)
Case      --[involved_scheme]-->     Scheme (duration, method, victims)
Defendant --[admitted_or_denied]-->   Allegations
Defendant --[sentenced_to]-->        Criminal Sentence
Company   --[operates_in]-->         Industry Domain
```

The JSON export format produces arrays for multi-valued fields, enabling direct import into Neo4j via `apoc.load.json`, Amazon Neptune, or any graph database that accepts JSON documents.

---

## PDF Analysis Pipeline

Each associated PDF (Final Judgment, SEC Complaint, Consent Order, Stipulation) undergoes the following analysis:

1. **Download**: System curl fetches the PDF binary with a 60-second timeout, accepting files up to 50MB.

2. **Text extraction**: pdfplumber reads up to 200 pages per document, handling multi-column court document layouts.

3. **Deep extraction**: 24 specialized regex-based extractors run against the full text:
   - Statutory charges across five acts (Securities Act, Exchange Act, Advisers Act, Investment Company Act, Sarbanes-Oxley) plus SEC Rules and CFR references
   - Monetary penalties with structured breakdown (disgorgement, prejudgment interest, civil penalty)
   - Court orders, injunctions, bars (officer/director, penny stock, industry), and consent terms
   - Judge identification from multiple patterns (Hon./Judge titles, /s/ signatures, SO ORDERED footers)
   - Person-Role-Company relationships (defendant roles, employer entity, CRD/CIK numbers)
   - SEC enforcement staff (investigating attorneys, supervising attorneys, regional office)
   - Scheme details (duration, method, victim count, transaction count, admission status)
   - Cross-references (criminal case numbers, related litigation releases, FINRA actions)
   - Narrative paragraph extraction for summary enrichment

4. **Merge**: When a case has multiple PDFs (for example, both a Complaint and a Final Judgment), extraction results are merged. Charges, outcomes, and judges accumulate across documents; employer and court use first-found semantics.

5. **Delete**: Each PDF is removed from disk immediately after analysis to conserve storage.

---

## HPC Deployment (ASU Sol)

### Environment Setup

```bash
mamba create -n sec_scraper -c conda-forge python=3 beautifulsoup4 pdfplumber lxml
source activate sec_scraper
```

### SLURM Job Submission

A SLURM batch script (`sec_scraper_v8.sbatch`) is included. Example for a standard scrape:

```bash
sbatch sec_scraper_v8.sbatch
```

For full-archive scraping, submit with extended walltime. The pipeline is crash-safe: if a job reaches its walltime limit, re-submitting the same job resumes from the last completed case via the SQLite checkpoint.

```bash
# First run: scrapes as many cases as walltime allows
sbatch sec_scraper_v8.sbatch

# Subsequent runs: picks up where the previous run stopped
sbatch sec_scraper_v8.sbatch
```

### Estimated Runtimes

| Scope | Approximate Cases | Workers | Estimated Time |
|-------|-------------------|---------|----------------|
| 1 page | 20 | 3 | 2 minutes |
| 10 pages | 200 | 3 | 20 minutes |
| 50 pages | 1,000 | 5 | 2 hours |
| Full archive | 26,500 | 5 | 8-10 hours |

### Politeness and Rate Limiting

- 2-second delay between requests per worker
- 1-second delay before each PDF download
- User-Agent header identifies the scraper as academic research
- Exponential backoff on HTTP 429 (rate limit) responses
- Maximum 6 concurrent workers to avoid overwhelming SEC.gov

---

## Project Structure

```
sec-litigation-scraper/
    sec_litigation_scraper_v8.py     Main pipeline script
    sec_scraper_v8.sbatch            SLURM batch script for ASU Sol
    requirements.txt                 Python dependencies (3 packages)
    README.md                        This file
    LICENSE                          MIT License
    samples/                         Sample output files
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Acknowledgments

- CIPS Lab, School of Computing and Augmented Intelligence, Arizona State University
- Prof. Hasan Davulcu -- Research supervision
- U.S. Securities and Exchange Commission for public access to enforcement data via SEC.gov and EDGAR

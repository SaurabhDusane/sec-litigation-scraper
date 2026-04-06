# Securities Litigation Data Sources: Comprehensive Analysis

## Executive Summary

This document provides a detailed analysis of two primary securities litigation data sources for Legal AI research:

1. **Stanford Securities Class Action Clearinghouse (SCAC)** - Private class action lawsuits
2. **SEC Litigation Releases** - Government enforcement actions

Both sources offer complementary perspectives on securities fraud and enforcement, making them valuable for comprehensive legal AI applications.

---

## 1. Data Structure Analysis

### 1.1 Stanford SCAC Data Structure

**URL:** https://securities.stanford.edu/

**Database Overview:**
- **Total Filings:** 6,879 securities class action filings
- **Time Period:** 1996 to present
- **Total Settlements:** $119.35 billion across 3,004 settled cases
- **Total Defendants:** 53,195 (individuals and companies)
- **Cases Dismissed:** 3,306
- **Ongoing Cases:** 535

**Case Record Structure:**

| Field | Description | Example |
|-------|-------------|---------|
| `Filing Name` | Company/defendant name | Lockheed Martin Corporation |
| `Filing Date` | Date complaint filed | 07/28/2025 |
| `Case ID` | Unique identifier | 108640 |
| `District Court` | Federal court jurisdiction | S.D. New York |
| `Exchange` | Stock exchange listing | NASDAQ, NYSE, OTC-BB |
| `Ticker` | Stock symbol | LMT |
| `Sector` | Industry sector | Technology, Healthcare, Financial |
| `Case Status` | Current status | ONGOING, SETTLED, DISMISSED |
| `Case Summary` | Narrative description of allegations | Full text description |
| `Class Period` | Time range for affected investors | Start/end dates |
| `Presiding Judge` | Assigned judge | Name or N/A |

**Document Types Available:**
- First Identified Complaint (PDF)
- Reference Complaint
- Related District Court Filings
- Settlement Documents
- Court Orders

**Trend Categories Tracked:**

| Trend | Filing Count | First Filing | Latest Filing |
|-------|-------------|--------------|---------------|
| Cryptocurrency | 103 | 06/15/2016 | 07/25/2025 |
| SPACs | 117 | varies | ongoing |
| COVID-19 | 84 | 03/12/2020 | 06/30/2025 |
| Artificial Intelligence | 53+ | varies | ongoing |
| Cannabis | 40 | varies | ongoing |
| Data Breach | 35 | varies | ongoing |

**Analytics Available:**
- Disclosure Dollar Loss Index (DDL)
- Maximum Dollar Loss Index (MDL)
- Class Action Filings Index (CAF)
- Heat maps by year, circuit, sector, industry
- Settlement statistics

---

### 1.2 SEC Litigation Releases Data Structure

**URL:** https://www.sec.gov/enforcement-litigation/litigation-releases

**Database Overview:**
- **Release Numbers:** LR-1 through LR-26486+ (current)
- **Time Period:** 1995 to present
- **Update Frequency:** Daily/real-time
- **Format:** HTML pages with linked PDF documents

**Litigation Release Structure:**

| Field | Description | Example |
|-------|-------------|---------|
| `Release Number` | Sequential identifier | LR-26486 |
| `Release Date` | Publication date | February 20, 2026 |
| `Defendants` | Named parties | C-Hear, Inc.; Adena Harmon |
| `Case Citation` | Court docket number | No. 3:26-cv-00547-N (N.D. Tex.) |
| `Court` | Federal court | N.D. Texas |
| `Summary` | Case description | Detailed narrative |
| `Charges` | Securities violations | Section 17(a), Section 10(b), Rule 10b-5 |
| `Remedies Sought` | Relief requested | Injunctions, civil penalties, disgorgement |

**Linked Documents:**
- SEC Complaints (PDF)
- Final Judgments
- Default Judgments
- Consent Orders
- Stipulations to Dismiss
- Administrative Orders (AAER references)

**Sample Case Analysis (LR-26486):**

```
Release: LR-26486
Date: February 20, 2026
Defendant: C-Hear, Inc., Adena Harmon
Court: N.D. Texas (No. 3:26-cv-00547-N)

Allegations:
- Securities fraud in $4.2 million stock offering
- Misleading statements about technology capabilities
- Concealment of CEO's criminal convictions
- Misappropriation of ~$641,000 investor funds

Charges:
- Section 17(a) of Securities Act of 1933
- Section 10(b) of Exchange Act of 1934
- Rule 10b-5

Relief Sought:
- Permanent injunctions
- Civil penalties
- Disgorgement with prejudgment interest
- Conduct-based injunctions
```

---

## 2. API/Scraping Feasibility Assessment

### 2.1 Stanford SCAC Access

**robots.txt Analysis:**
```
User-agent: *
Disallow: [specific PDF documents only - 6 files blocked]
```

**Access Methods:**

| Method | Feasibility | Notes |
|--------|-------------|-------|
| Direct Web Scraping | ⚠️ Limited | Requires login for full case data |
| Free Account Registration | ✅ Available | Provides Advanced Search access |
| API | ❌ Not Available | No public API documented |
| RSS/Email Updates | ✅ Available | New Filings email service active |
| Research Reports | ✅ Public PDFs | Midyear/Annual assessments freely available |

**Data Access Limitations:**
- Full case pages require authentication
- Advanced Search requires login
- Some historical documents may be restricted
- Currently paused for restructuring (limited updates)

**Recommended Approach:**
1. Register for free account to access full database
2. Use Stanford Securities Litigation Analytics (sla.law.stanford.edu) during restructuring
3. Download publicly available research reports for aggregate statistics

---

### 2.2 SEC Litigation Releases Access

**robots.txt Analysis:**
- Timeout on fetch (large file)
- Generally permissive for programmatic access

**Official SEC Developer Resources:**

| Resource | URL | Description |
|----------|-----|-------------|
| Developer Page | sec.gov/developer | API documentation |
| Data APIs | data.sec.gov | RESTful JSON APIs |
| RSS Feeds | Available | Real-time updates |
| EDGAR Index Files | Archives available | Daily/quarterly indexes |
| Fair Access Policy | 10 req/sec limit | Rate limiting guidelines |

**Third-Party API Options:**

| Provider | Endpoint | Features |
|----------|----------|----------|
| SEC-API.io | api.sec-api.io/sec-litigation-releases | Full-text search, JSON responses |
| SEC-API.io | api.sec-api.io/sec-enforcement-actions | Complementary enforcement data |

**Data Access Methods:**

| Method | Feasibility | Notes |
|--------|-------------|-------|
| Direct Web Scraping | ✅ Feasible | Standard HTML, rate limit 10 req/sec |
| RSS Feed | ✅ Available | Real-time new releases |
| Third-Party API | ✅ Available | sec-api.io provides structured access |
| PDF Downloads | ⚠️ Requires Auth | Some documents return 403 |
| Index Files | ✅ Available | JSON/XML/HTML formats |

**Rate Limiting Requirements:**
- Maximum 10 requests per second
- Must identify bot/user-agent properly
- Unclassified bots may be blocked

**Recommended Approach:**
1. Use RSS feed for real-time monitoring
2. Implement polite scraping with proper headers and rate limiting
3. Consider sec-api.io for structured JSON access
4. Build PDF document pipeline separately

---

## 3. Data Collection Strategy

### 3.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Collection Pipeline                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Stanford   │    │     SEC      │    │   Unified    │  │
│  │    SCAC      │    │  Litigation  │    │   Database   │  │
│  │   Scraper    │    │   Scraper    │    │              │  │
│  └──────┬───────┘    └──────┬───────┘    └──────────────┘  │
│         │                   │                    ▲          │
│         ▼                   ▼                    │          │
│  ┌──────────────┐    ┌──────────────┐           │          │
│  │   Case       │    │   Release    │           │          │
│  │   Parser     │    │   Parser     │           │          │
│  └──────┬───────┘    └──────┬───────┘           │          │
│         │                   │                    │          │
│         ▼                   ▼                    │          │
│  ┌──────────────┐    ┌──────────────┐           │          │
│  │   PDF        │    │   PDF        │           │          │
│  │   Extractor  │    │   Extractor  │           │          │
│  └──────┬───────┘    └──────┬───────┘           │          │
│         │                   │                    │          │
│         └───────────────────┴────────────────────┘          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Stanford SCAC Collection Strategy

**Phase 1: Public Data Collection**

```python
# Pseudocode for Stanford SCAC scraper

class StanfordSCACCollector:
    BASE_URL = "https://securities.stanford.edu"
    
    def collect_filings_list(self):
        """Scrape publicly visible filings table"""
        # Fields available without login:
        # - Filing Name, Date, District Court, Exchange, Ticker
        pass
    
    def collect_trend_data(self):
        """Scrape trend category pages"""
        trends = [
            "cryptocurrency", "covid-19", "artificial-intelligence",
            "spac", "cannabis", "data-breach"
        ]
        # Full filing tables with sector info available
        pass
    
    def download_research_reports(self):
        """Download public PDF reports"""
        reports = [
            "Securities-Class-Action-Filings-2025-Midyear-Assessment.pdf",
            "Securities-Class-Action-Settlements-2024-Review-and-Analysis.pdf"
        ]
        pass
```

**Phase 2: Authenticated Collection**

```python
class StanfordAuthenticatedCollector:
    def login(self, email, password):
        """Authenticate to access restricted content"""
        pass
    
    def collect_full_case_page(self, case_id):
        """Collect complete case information"""
        # Fields requiring authentication:
        # - Full case summary
        # - All related filings
        # - Settlement details
        # - Document links
        pass
    
    def use_advanced_search(self, filters):
        """Query advanced search with filters"""
        # Available filters:
        # - Date range, Court, Sector, Industry
        # - Exchange, Ticker, Case status
        pass
```

**Data Schema:**

```sql
CREATE TABLE stanford_filings (
    id INTEGER PRIMARY KEY,
    case_id VARCHAR(20) UNIQUE,
    filing_name VARCHAR(255),
    filing_date DATE,
    district_court VARCHAR(100),
    exchange VARCHAR(50),
    ticker VARCHAR(10),
    sector VARCHAR(100),
    industry VARCHAR(100),
    case_status VARCHAR(50),
    case_summary TEXT,
    class_period_start DATE,
    class_period_end DATE,
    settlement_amount DECIMAL(15,2),
    ddl_amount DECIMAL(15,2),
    mdl_amount DECIMAL(15,2),
    trend_categories JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE stanford_documents (
    id INTEGER PRIMARY KEY,
    case_id VARCHAR(20) REFERENCES stanford_filings(case_id),
    document_type VARCHAR(100),
    document_url VARCHAR(500),
    document_date DATE,
    extracted_text TEXT,
    created_at TIMESTAMP
);
```

---

### 3.3 SEC Litigation Releases Collection Strategy

**Phase 1: Index Collection**

```python
class SECLitigationCollector:
    BASE_URL = "https://www.sec.gov/enforcement-litigation/litigation-releases"
    
    def collect_release_index(self, year=None, month=None):
        """Scrape release listing page with filters"""
        # Available: 1995-2026, all months
        pass
    
    def parse_release_page(self, release_number):
        """Extract structured data from release page"""
        # Fields: release_number, date, defendants, 
        # case_citation, court, summary, charges, remedies
        pass
    
    def extract_linked_documents(self, release_html):
        """Identify and download linked PDFs"""
        doc_types = [
            "SEC Complaint", "Final Judgment", 
            "Default Judgment", "Consent Order",
            "Stipulation to Dismiss"
        ]
        pass
```

**Phase 2: Document Processing**

```python
class SECDocumentProcessor:
    def download_pdf(self, url):
        """Download PDF with retry logic"""
        # Handle 403 errors, implement backoff
        pass
    
    def extract_text(self, pdf_path):
        """Extract text from complaint PDFs"""
        # Use PyPDF2, pdfplumber, or OCR for scanned docs
        pass
    
    def parse_complaint(self, text):
        """Extract structured information from complaint"""
        # - Parties (plaintiffs, defendants)
        # - Allegations
        # - Securities laws cited
        # - Time periods
        # - Dollar amounts
        pass
```

**Data Schema:**

```sql
CREATE TABLE sec_litigation_releases (
    id INTEGER PRIMARY KEY,
    release_number VARCHAR(20) UNIQUE,
    release_date DATE,
    title VARCHAR(500),
    case_citation VARCHAR(255),
    court VARCHAR(100),
    summary TEXT,
    charges JSON,
    remedies_sought JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE sec_defendants (
    id INTEGER PRIMARY KEY,
    release_number VARCHAR(20) REFERENCES sec_litigation_releases(release_number),
    defendant_name VARCHAR(255),
    defendant_type VARCHAR(50), -- individual, company
    ticker VARCHAR(10),
    cik VARCHAR(20)
);

CREATE TABLE sec_documents (
    id INTEGER PRIMARY KEY,
    release_number VARCHAR(20) REFERENCES sec_litigation_releases(release_number),
    document_type VARCHAR(100),
    document_url VARCHAR(500),
    document_date DATE,
    file_path VARCHAR(500),
    extracted_text TEXT,
    created_at TIMESTAMP
);
```

---

### 3.4 Entity Resolution & Cross-Referencing

**Matching Companies Across Sources:**

```python
class EntityResolver:
    def match_by_ticker(self, ticker):
        """Match using stock ticker symbol"""
        pass
    
    def match_by_company_name(self, name):
        """Fuzzy matching on company names"""
        # Handle variations: Inc., Corp., LLC, etc.
        pass
    
    def match_by_cik(self, cik):
        """Match using SEC CIK number"""
        pass
    
    def find_related_cases(self, company):
        """Find SCAC class actions related to SEC enforcement"""
        # Identify companies facing both private and public enforcement
        pass
```

**Cross-Reference Schema:**

```sql
CREATE TABLE company_master (
    id INTEGER PRIMARY KEY,
    company_name VARCHAR(255),
    ticker VARCHAR(10),
    cik VARCHAR(20),
    exchange VARCHAR(50),
    sector VARCHAR(100),
    industry VARCHAR(100)
);

CREATE TABLE case_linkage (
    id INTEGER PRIMARY KEY,
    company_id INTEGER REFERENCES company_master(id),
    stanford_case_id VARCHAR(20),
    sec_release_number VARCHAR(20),
    relationship_type VARCHAR(50), -- parallel, sequential, related
    notes TEXT
);
```

---

## 4. Trend Analysis

### 4.1 Artificial Intelligence-Related Filings

**Current Statistics (2025 H1):**
- **Total AI-related filings:** 53+ (and growing)
- **2025 H1 filings:** 12 (on pace to exceed 2024 total of 15)
- **Growth rate:** 60%+ year-over-year

**Filing Distribution:**

| Year | AI-Related Filings |
|------|-------------------|
| 2021 | 8 |
| 2022 | 17 |
| 2023 | 11 |
| 2024 | 15 |
| 2025 H1 | 12 (24 annualized) |

**Key Plaintiff Law Firms (2025 H1):**
- Pomerantz LLP: 5 of 12 first identified complaints
- Levi & Korsinsky LLP: 2 filings
- Edelsberg Law: 2 filings

**Common AI-Related Allegations:**
1. Overstated AI capabilities in products/services
2. Misleading statements about AI implementation progress
3. Failure to disclose AI-related risks
4. False claims about AI revenue generation
5. Misrepresentation of AI technology partnerships

---

### 4.2 Cryptocurrency Litigation

**Current Statistics:**
- **Total filings:** 103 (since 06/15/2016)
- **2025 H1 filings:** 6 (nearly matching 2024 full-year total of 7)
- **First case:** GAW Miners, LLC (06/15/2016)

**Filing Categories:**

| Category | Count | Examples |
|----------|-------|----------|
| Initial Coin Offerings (ICO) | 25+ | Ripple Labs, BitConnect, Paragon Coin |
| Cryptocurrency Exchanges | 15+ | Binance, Coinbase, KuCoin |
| NFT/Digital Assets | 12+ | Yuga Labs, DraftKings, Dolce & Gabbana |
| Crypto Mining | 10+ | Marathon Digital, Riot Blockchain |
| DeFi/DAO | 5+ | Compound DAO, Lido DAO |
| Memecoins | Growing | $JENNER, $HAWK, $PNUT |

**Geographic Distribution (District Courts):**

| Court | Filing % |
|-------|----------|
| S.D. New York | ~40% |
| N.D. California | ~20% |
| S.D. Florida | ~10% |
| Other | ~30% |

**Key Legal Issues:**
1. Whether tokens constitute "securities" under Howey test
2. Exchange liability for listing unregistered securities
3. DAO liability and entity status
4. NFT classification as securities
5. Celebrity endorsement liability

**Notable Settlements:**
- Block.one: $27.5M (ICO)
- DraftKings NFTs: $10M
- Shaq/Astrals NFTs: $11M
- Voyager: $6.5M

---

### 4.3 COVID-19 Related Filings

**Current Statistics:**
- **Total filings:** 84 (since 03/12/2020)
- **2025 H1 filings:** 2 (lowest since trend emerged)
- **Trajectory:** Sharply declining

**Filing Trend:**

| Period | COVID-19 Filings |
|--------|-----------------|
| 2020 | 33 |
| 2021 | 28 |
| 2022 | 11 |
| 2023 | 7 |
| 2024 | 4 |
| 2025 H1 | 2 |

**Industry Distribution:**

| Sector | % of COVID Filings |
|--------|-------------------|
| Healthcare/Pharma | 45% |
| Services | 20% |
| Technology | 15% |
| Consumer | 12% |
| Financial | 8% |

**Common Allegation Types:**
1. Vaccine/treatment efficacy misrepresentations
2. Supply chain disruption disclosures
3. Business resilience overstatements
4. Remote work/technology capability claims
5. Pandemic-related demand projections

**Notable Outcomes:**
- AstraZeneca: Dismissed (9/2022)
- Peloton: Dismissed (4/2023)
- Emergent BioSolutions: $40M settlement
- Chegg: $55M settlement
- Honest Company: $28M settlement

---

### 4.4 SPAC-Related Filings

**Current Statistics:**
- **Total SPAC filings:** 117+
- **2025 H1 filings:** 5
- **Peak year:** 2022 (23 filings)

**SPAC Filing Trend:**

| Year | SPAC Filings |
|------|-------------|
| 2021 | 33 |
| 2022 | 27 |
| 2023 | 15 |
| 2024 | 11 |
| 2025 H1 | 5 |

**Common SPAC Allegations:**
1. Misleading projections in de-SPAC transactions
2. Failure to disclose target company risks
3. Sponsor conflicts of interest
4. Inadequate due diligence
5. Post-merger performance misrepresentations

---

### 4.5 Comparative Analysis: Private vs. Public Enforcement

**Enforcement Patterns:**

| Dimension | Stanford SCAC (Private) | SEC (Public) |
|-----------|------------------------|--------------|
| Initiator | Shareholder plaintiffs | SEC Enforcement Division |
| Remedy | Damages for class members | Disgorgement, penalties, bars |
| Burden of Proof | Preponderance (civil) | Preponderance (civil) |
| Typical Timeline | 3-5 years | 1-3 years |
| Settlement Rates | ~45% | ~90%+ |
| Average Recovery | $42.4M median (2024) | Varies widely |

**Overlap Analysis:**
- Many companies face both private class actions AND SEC enforcement
- SEC actions often precede or follow private suits
- Criminal DOJ referrals represent most serious cases

---

## 5. Research Applications

### 5.1 Legal AI Use Cases

1. **Outcome Prediction**
   - Predict settlement amounts based on case features
   - Estimate dismissal probability
   - Forecast litigation duration

2. **Document Analysis**
   - Extract allegations from complaints
   - Identify similar cases
   - Track legal argument evolution

3. **Entity Recognition**
   - Extract defendant/plaintiff names
   - Link to company databases (CIK, ticker)
   - Map legal counsel networks

4. **Trend Detection**
   - Identify emerging violation categories
   - Track sector-specific risk patterns
   - Monitor enforcement policy shifts

5. **Risk Assessment**
   - Company litigation risk scoring
   - Industry benchmarking
   - Early warning indicators

### 5.2 Recommended Dataset Structure

**Training Data for NLP:**
- Complaint full text (PDF extraction)
- Case summaries
- Settlement documents
- Court orders/opinions

**Structured Features:**
- Filing date, resolution date, duration
- Court, judge, jurisdiction
- Company sector, industry, exchange
- Dollar losses (DDL, MDL)
- Settlement amount
- Outcome (dismissed, settled, ongoing)

**Labels for Classification:**
- Violation types (10b-5, Section 11, etc.)
- Allegation categories (accounting fraud, omissions, etc.)
- Outcome categories
- Trend categories (AI, crypto, COVID, SPAC)

---

## 6. Implementation Recommendations

### 6.1 Immediate Actions

1. **Register for Stanford SCAC account** (free)
2. **Set up SEC RSS feed monitoring**
3. **Implement base scrapers** with rate limiting
4. **Download available research reports** for baseline statistics

### 6.2 Technical Stack Suggestions

| Component | Recommended Tools |
|-----------|------------------|
| Web Scraping | Scrapy, BeautifulSoup, Selenium |
| PDF Processing | pdfplumber, PyPDF2, Tesseract OCR |
| Database | PostgreSQL with full-text search |
| NLP Pipeline | spaCy, Hugging Face Transformers |
| Entity Resolution | dedupe, recordlinkage |
| API Integration | requests, aiohttp |

### 6.3 Ethical Considerations

- Respect robots.txt directives
- Implement polite scraping (rate limits, delays)
- Properly identify scrapers in User-Agent
- Consider data licensing for commercial use
- Handle PII appropriately in extracted documents

---

## Appendix A: Key URLs

| Resource | URL |
|----------|-----|
| Stanford SCAC Home | https://securities.stanford.edu/ |
| Stanford Filings List | https://securities.stanford.edu/filings.html |
| Stanford Current Trends | https://securities.stanford.edu/current-trends.html |
| Stanford Research Reports | https://securities.stanford.edu/clearinghouse-research.html |
| Stanford Sign-Up | https://securities.stanford.edu/sign-up.html |
| SEC Litigation Releases | https://www.sec.gov/enforcement-litigation/litigation-releases |
| SEC Developer Resources | https://www.sec.gov/developer |
| SEC EDGAR APIs | https://data.sec.gov/ |
| Third-Party API | https://sec-api.io/docs/sec-litigation-releases-database-api |

## Appendix B: Sample Data Records

### Stanford SCAC Sample

```json
{
  "case_id": "108640",
  "filing_name": "Lockheed Martin Corporation",
  "filing_date": "2025-07-28",
  "district_court": "S.D. New York",
  "exchange": "New York SE",
  "ticker": "LMT",
  "sector": "Capital Goods",
  "case_status": "ONGOING",
  "allegations": [
    "Lacked effective internal controls",
    "Overstated ability to deliver on contracts",
    "Failed to disclose material adverse facts"
  ],
  "class_period": {
    "start": "TBD",
    "end": "TBD"
  }
}
```

### SEC Litigation Release Sample

```json
{
  "release_number": "LR-26486",
  "release_date": "2026-02-20",
  "defendants": [
    {"name": "C-Hear, Inc.", "type": "company"},
    {"name": "Adena Harmon", "type": "individual"}
  ],
  "case_citation": "No. 3:26-cv-00547-N (N.D. Tex.)",
  "court": "N.D. Texas",
  "charges": [
    "Section 17(a) of Securities Act of 1933",
    "Section 10(b) of Exchange Act of 1934",
    "Rule 10b-5"
  ],
  "amount_at_issue": 4200000,
  "misappropriated": 641000,
  "documents": [
    {
      "type": "SEC Complaint",
      "url": "https://www.sec.gov/files/litigation/complaints/2026/comp26486.pdf"
    }
  ]
}
```

---

*Document generated: February 22, 2026*
*For CIPS Lab - Legal AI Research*

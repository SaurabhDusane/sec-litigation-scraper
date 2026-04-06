"""
SEC Litigation Releases Data Collector

This module provides tools for collecting and parsing SEC litigation releases
from https://www.sec.gov/enforcement-litigation/litigation-releases

Usage:
    collector = SECLitigationCollector()
    releases = collector.collect_releases(year=2025, limit=100)
"""

import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime
import time
import json
import re
from pathlib import Path


@dataclass
class LinkedDocument:
    """Represents a document linked from a litigation release"""
    doc_type: str
    url: str
    filename: Optional[str] = None


@dataclass
class Defendant:
    """Represents a defendant in a litigation release"""
    name: str
    defendant_type: str = "unknown"  # individual, company, other


@dataclass
class LitigationRelease:
    """Represents a single SEC litigation release"""
    release_number: str
    release_date: Optional[datetime] = None
    title: str = ""
    case_citation: str = ""
    court: str = ""
    summary: str = ""
    defendants: List[Defendant] = field(default_factory=list)
    charges: List[str] = field(default_factory=list)
    documents: List[LinkedDocument] = field(default_factory=list)
    url: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "release_number": self.release_number,
            "release_date": self.release_date.isoformat() if self.release_date else None,
            "title": self.title,
            "case_citation": self.case_citation,
            "court": self.court,
            "summary": self.summary,
            "defendants": [{"name": d.name, "type": d.defendant_type} for d in self.defendants],
            "charges": self.charges,
            "documents": [{"type": d.doc_type, "url": d.url} for d in self.documents],
            "url": self.url
        }


class SECLitigationCollector:
    """Collector for SEC Litigation Releases"""
    
    BASE_URL = "https://www.sec.gov"
    RELEASES_URL = f"{BASE_URL}/enforcement-litigation/litigation-releases"
    
    # SEC Fair Access Policy: max 10 requests per second
    REQUEST_DELAY = 0.15  # ~6.6 requests per second (conservative)
    
    def __init__(self, output_dir: str = "./data/sec"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Legal-AI-Research/1.0 (academic research; contact@example.edu)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        self._last_request_time = 0
    
    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.REQUEST_DELAY:
            time.sleep(self.REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()
    
    def _get(self, url: str) -> Optional[requests.Response]:
        """Make a rate-limited GET request"""
        self._rate_limit()
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            print(f"Request failed for {url}: {e}")
            return None
    
    def collect_release_list(
        self, 
        year: Optional[int] = None, 
        month: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Collect list of litigation releases from the index page
        
        Args:
            year: Filter by year (1995-present)
            month: Filter by month (1-12)
            limit: Maximum number of releases to collect
            
        Returns:
            List of release metadata dictionaries
        """
        url = self.RELEASES_URL
        params = {}
        if year:
            params["year"] = year
        if month:
            params["month"] = month
            
        response = self._get(url)
        if not response:
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        releases = []
        
        # Find release links - adjust selector based on actual page structure
        release_links = soup.select('a[href*="/enforcement-litigation/litigation-releases/lr-"]')
        
        for i, link in enumerate(release_links):
            if limit and i >= limit:
                break
                
            href = link.get("href", "")
            if not href.startswith("http"):
                href = self.BASE_URL + href
            
            # Extract release number from URL
            match = re.search(r'lr-(\d+)', href)
            release_number = f"LR-{match.group(1)}" if match else ""
            
            releases.append({
                "release_number": release_number,
                "title": link.get_text(strip=True),
                "url": href
            })
        
        return releases
    
    def parse_release_page(self, url: str) -> Optional[LitigationRelease]:
        """
        Parse a single litigation release page
        
        Args:
            url: URL of the release page
            
        Returns:
            LitigationRelease object or None if parsing fails
        """
        response = self._get(url)
        if not response:
            return None
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract release number from URL
        match = re.search(r'lr-(\d+)', url)
        release_number = f"LR-{match.group(1)}" if match else ""
        
        release = LitigationRelease(
            release_number=release_number,
            url=url
        )
        
        # Parse title (usually in h1)
        title_elem = soup.select_one("h1")
        if title_elem:
            release.title = title_elem.get_text(strip=True)
        
        # Parse release date and number from header
        header_text = soup.get_text()
        
        # Look for date pattern
        date_patterns = [
            r'(\w+ \d{1,2}, \d{4})',
            r'(\d{1,2}/\d{1,2}/\d{4})'
        ]
        for pattern in date_patterns:
            date_match = re.search(pattern, header_text)
            if date_match:
                try:
                    date_str = date_match.group(1)
                    for fmt in ["%B %d, %Y", "%m/%d/%Y"]:
                        try:
                            release.release_date = datetime.strptime(date_str, fmt)
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass
                break
        
        # Extract case citation
        citation_pattern = r'(No\.\s*[\w\-:]+\s*\([^)]+\))'
        citation_match = re.search(citation_pattern, header_text)
        if citation_match:
            release.case_citation = citation_match.group(1)
        
        # Extract main content/summary
        content_div = soup.select_one("article, .article-content, main")
        if content_div:
            paragraphs = content_div.find_all("p")
            release.summary = "\n\n".join(p.get_text(strip=True) for p in paragraphs)
        
        # Extract linked documents
        doc_links = soup.select('a[href*="/files/litigation/"]')
        for doc_link in doc_links:
            href = doc_link.get("href", "")
            if not href.startswith("http"):
                href = self.BASE_URL + href
            
            doc_text = doc_link.get_text(strip=True)
            doc_type = self._classify_document_type(doc_text, href)
            
            release.documents.append(LinkedDocument(
                doc_type=doc_type,
                url=href,
                filename=href.split("/")[-1] if "/" in href else None
            ))
        
        # Extract charges from text
        release.charges = self._extract_charges(release.summary)
        
        # Parse defendants from title
        release.defendants = self._parse_defendants(release.title)
        
        return release
    
    def _classify_document_type(self, text: str, url: str) -> str:
        """Classify document type based on link text and URL"""
        text_lower = text.lower()
        url_lower = url.lower()
        
        if "complaint" in text_lower or "comp" in url_lower:
            return "SEC Complaint"
        elif "final judgment" in text_lower or "judg" in url_lower:
            return "Final Judgment"
        elif "default" in text_lower:
            return "Default Judgment"
        elif "consent" in text_lower:
            return "Consent Order"
        elif "stipulation" in text_lower or "stip" in url_lower:
            return "Stipulation"
        elif "order" in text_lower:
            return "Order"
        else:
            return "Other Document"
    
    def _extract_charges(self, text: str) -> List[str]:
        """Extract securities law charges from release text"""
        charges = []
        
        charge_patterns = [
            r'Section 17\(a\)(?:\(\d+\))? of the Securities Act',
            r'Section 10\(b\) of the (?:Securities )?Exchange Act',
            r'Rule 10b-5',
            r'Section 13\([a-z]\) of the Exchange Act',
            r'Section 15\([a-z]\)',
            r'Section 5 of the Securities Act',
            r'Section 206 of the (?:Investment )?Advisers Act',
            r'Section 17\([a-z]\) of the Exchange Act',
        ]
        
        for pattern in charge_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    charges.append(match.group(0))
        
        return list(set(charges))
    
    def _parse_defendants(self, title: str) -> List[Defendant]:
        """Parse defendant names from release title"""
        defendants = []
        
        # Clean up title
        title = re.sub(r'\s+', ' ', title).strip()
        
        # Split on common separators
        parts = re.split(r'[;,]|\s+and\s+', title)
        
        for part in parts:
            part = part.strip()
            if not part or len(part) < 2:
                continue
            
            # Determine if individual or company
            company_indicators = ['Inc.', 'Corp.', 'LLC', 'Ltd.', 'LP', 'LLP', 'Co.', 'Company']
            is_company = any(ind in part for ind in company_indicators)
            
            defendants.append(Defendant(
                name=part,
                defendant_type="company" if is_company else "individual"
            ))
        
        return defendants
    
    def collect_releases(
        self, 
        year: Optional[int] = None,
        limit: Optional[int] = 100,
        save: bool = True
    ) -> List[LitigationRelease]:
        """
        Collect and parse multiple litigation releases
        
        Args:
            year: Filter by year
            limit: Maximum number to collect
            save: Whether to save results to disk
            
        Returns:
            List of LitigationRelease objects
        """
        print(f"Collecting release list (year={year}, limit={limit})...")
        release_list = self.collect_release_list(year=year, limit=limit)
        
        releases = []
        total = len(release_list)
        
        for i, release_meta in enumerate(release_list):
            print(f"Parsing {i+1}/{total}: {release_meta['release_number']}")
            
            release = self.parse_release_page(release_meta["url"])
            if release:
                releases.append(release)
        
        if save:
            self._save_releases(releases, year)
        
        return releases
    
    def _save_releases(self, releases: List[LitigationRelease], year: Optional[int] = None):
        """Save releases to JSON file"""
        filename = f"sec_releases_{year or 'all'}_{datetime.now().strftime('%Y%m%d')}.json"
        filepath = self.output_dir / filename
        
        data = [r.to_dict() for r in releases]
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"Saved {len(releases)} releases to {filepath}")
    
    def download_document(self, url: str, output_dir: Optional[Path] = None) -> Optional[Path]:
        """
        Download a document (PDF, etc.) from SEC
        
        Args:
            url: Document URL
            output_dir: Directory to save file
            
        Returns:
            Path to downloaded file or None
        """
        output_dir = output_dir or self.output_dir / "documents"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = url.split("/")[-1]
        filepath = output_dir / filename
        
        if filepath.exists():
            print(f"Document already exists: {filepath}")
            return filepath
        
        response = self._get(url)
        if not response:
            return None
        
        with open(filepath, "wb") as f:
            f.write(response.content)
        
        print(f"Downloaded: {filepath}")
        return filepath


def main():
    """Example usage"""
    collector = SECLitigationCollector(output_dir="./data/sec")
    
    # Collect recent releases
    releases = collector.collect_releases(year=2025, limit=10)
    
    print(f"\nCollected {len(releases)} releases")
    
    for release in releases[:3]:
        print(f"\n{'='*60}")
        print(f"Release: {release.release_number}")
        print(f"Date: {release.release_date}")
        print(f"Title: {release.title}")
        print(f"Defendants: {[d.name for d in release.defendants]}")
        print(f"Charges: {release.charges}")
        print(f"Documents: {len(release.documents)}")


if __name__ == "__main__":
    main()

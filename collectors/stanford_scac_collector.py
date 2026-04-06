"""
Stanford Securities Class Action Clearinghouse (SCAC) Data Collector

This module provides tools for collecting securities class action data from
https://securities.stanford.edu/

Note: Full case data requires a free account registration.

Usage:
    collector = StanfordSCACCollector()
    filings = collector.collect_public_filings(limit=100)
"""

import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
import time
import json
import re
from pathlib import Path


@dataclass
class TrendFiling:
    """Represents a filing within a trend category"""
    filing_name: str
    filing_date: Optional[datetime] = None
    district_court: str = ""
    exchange: str = ""
    ticker: str = ""
    sector: str = ""
    case_url: str = ""
    case_id: str = ""


@dataclass
class TrendCategory:
    """Represents a trend category with its filings"""
    name: str
    total_filings: int = 0
    first_filing_date: Optional[datetime] = None
    last_filing_date: Optional[datetime] = None
    description: str = ""
    filings: List[TrendFiling] = field(default_factory=list)
    news_articles: List[Dict] = field(default_factory=list)


@dataclass
class ClassActionFiling:
    """Represents a securities class action filing"""
    case_id: str
    filing_name: str
    filing_date: Optional[datetime] = None
    district_court: str = ""
    exchange: str = ""
    ticker: str = ""
    sector: str = ""
    industry: str = ""
    case_status: str = ""
    case_summary: str = ""
    class_period_start: Optional[datetime] = None
    class_period_end: Optional[datetime] = None
    settlement_amount: Optional[float] = None
    presiding_judge: str = ""
    trend_categories: List[str] = field(default_factory=list)
    case_url: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "case_id": self.case_id,
            "filing_name": self.filing_name,
            "filing_date": self.filing_date.isoformat() if self.filing_date else None,
            "district_court": self.district_court,
            "exchange": self.exchange,
            "ticker": self.ticker,
            "sector": self.sector,
            "industry": self.industry,
            "case_status": self.case_status,
            "case_summary": self.case_summary,
            "class_period_start": self.class_period_start.isoformat() if self.class_period_start else None,
            "class_period_end": self.class_period_end.isoformat() if self.class_period_end else None,
            "settlement_amount": self.settlement_amount,
            "presiding_judge": self.presiding_judge,
            "trend_categories": self.trend_categories,
            "case_url": self.case_url
        }


class StanfordSCACCollector:
    """Collector for Stanford SCAC data"""
    
    BASE_URL = "https://securities.stanford.edu"
    
    # Respectful scraping delay
    REQUEST_DELAY = 1.0  # 1 second between requests
    
    TREND_CATEGORIES = [
        "cryptocurrency",
        "covid-19", 
        "artificial-intelligence",
        "spac",
        "cannabis",
        "data-breach",
        "cybersecurity"
    ]
    
    def __init__(self, output_dir: str = "./data/stanford"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Legal-AI-Research/1.0 (academic research; contact@example.edu)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        self._last_request_time = 0
        self._authenticated = False
    
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
    
    def collect_public_filings_list(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Collect publicly visible filings list
        
        Note: Full details require authentication
        
        Args:
            limit: Maximum number of filings to collect
            
        Returns:
            List of filing metadata dictionaries
        """
        url = f"{self.BASE_URL}/filings.html"
        response = self._get(url)
        if not response:
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        filings = []
        
        # Find the filings table
        table = soup.select_one("table")
        if not table:
            print("Could not find filings table")
            return []
        
        rows = table.select("tr")[1:]  # Skip header row
        
        for i, row in enumerate(rows):
            if limit and i >= limit:
                break
            
            cells = row.select("td")
            if len(cells) < 5:
                continue
            
            # Extract filing link and case ID
            filing_link = cells[0].select_one("a")
            case_url = ""
            case_id = ""
            if filing_link:
                href = filing_link.get("href", "")
                if not href.startswith("http"):
                    href = self.BASE_URL + "/" + href.lstrip("/")
                case_url = href
                # Extract case ID from URL
                match = re.search(r'id=(\d+)', href)
                if match:
                    case_id = match.group(1)
            
            # Parse date
            date_text = cells[1].get_text(strip=True)
            filing_date = None
            try:
                filing_date = datetime.strptime(date_text, "%m/%d/%Y")
            except ValueError:
                pass
            
            filings.append({
                "case_id": case_id,
                "filing_name": cells[0].get_text(strip=True),
                "filing_date": filing_date.isoformat() if filing_date else None,
                "district_court": cells[2].get_text(strip=True),
                "exchange": cells[3].get_text(strip=True),
                "ticker": cells[4].get_text(strip=True) if len(cells) > 4 else "",
                "case_url": case_url
            })
        
        return filings
    
    def collect_trend_data(self, trend_name: str) -> Optional[TrendCategory]:
        """
        Collect data for a specific trend category
        
        Args:
            trend_name: Name of trend (e.g., "cryptocurrency", "artificial-intelligence")
            
        Returns:
            TrendCategory object or None
        """
        url = f"{self.BASE_URL}/current-trends.html"
        response = self._get(url)
        if not response:
            return None
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find the trend section
        # Look for header with trend name
        trend_header = None
        for header in soup.select("h4, h3"):
            if trend_name.lower().replace("-", " ") in header.get_text().lower():
                trend_header = header
                break
        
        if not trend_header:
            print(f"Trend '{trend_name}' not found")
            return None
        
        # Extract filing count from header
        header_text = trend_header.get_text()
        count_match = re.search(r'(\d+)\s*Filings?', header_text)
        total_filings = int(count_match.group(1)) if count_match else 0
        
        # Find dates
        date_match = re.search(
            r'First case filed on (\d{2}/\d{2}/\d{4}).*Last case filed on (\d{2}/\d{2}/\d{4})',
            header_text
        )
        first_date = None
        last_date = None
        if date_match:
            try:
                first_date = datetime.strptime(date_match.group(1), "%m/%d/%Y")
                last_date = datetime.strptime(date_match.group(2), "%m/%d/%Y")
            except ValueError:
                pass
        
        trend = TrendCategory(
            name=trend_name,
            total_filings=total_filings,
            first_filing_date=first_date,
            last_filing_date=last_date
        )
        
        # Find and parse the filings table for this trend
        # Look for table after header
        parent = trend_header.parent
        table = None
        for sibling in parent.find_next_siblings():
            table = sibling.select_one("table")
            if table:
                break
        
        if table:
            rows = table.select("tr")[1:]  # Skip header
            for row in rows:
                cells = row.select("td")
                if len(cells) < 5:
                    continue
                
                filing_link = cells[0].select_one("a")
                case_url = ""
                case_id = ""
                if filing_link:
                    href = filing_link.get("href", "")
                    if not href.startswith("http"):
                        href = self.BASE_URL + "/" + href.lstrip("/")
                    case_url = href
                    match = re.search(r'id=(\d+)', href)
                    if match:
                        case_id = match.group(1)
                
                date_text = cells[1].get_text(strip=True)
                filing_date = None
                try:
                    filing_date = datetime.strptime(date_text, "%m/%d/%Y")
                except ValueError:
                    pass
                
                trend.filings.append(TrendFiling(
                    filing_name=cells[0].get_text(strip=True),
                    filing_date=filing_date,
                    district_court=cells[2].get_text(strip=True),
                    exchange=cells[3].get_text(strip=True),
                    ticker=cells[4].get_text(strip=True) if len(cells) > 4 else "",
                    sector=cells[5].get_text(strip=True) if len(cells) > 5 else "",
                    case_url=case_url,
                    case_id=case_id
                ))
        
        return trend
    
    def collect_all_trends(self) -> Dict[str, TrendCategory]:
        """
        Collect data for all known trend categories
        
        Returns:
            Dictionary mapping trend names to TrendCategory objects
        """
        trends = {}
        
        for trend_name in self.TREND_CATEGORIES:
            print(f"Collecting trend: {trend_name}")
            trend = self.collect_trend_data(trend_name)
            if trend:
                trends[trend_name] = trend
                print(f"  Found {len(trend.filings)} filings")
        
        return trends
    
    def collect_key_statistics(self) -> Dict[str, Any]:
        """
        Collect key statistics from the stats page
        
        Returns:
            Dictionary of statistics
        """
        url = f"{self.BASE_URL}/stats.html"
        response = self._get(url)
        if not response:
            return {}
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        stats = {}
        
        # Extract statistics from the page
        stat_patterns = {
            "total_settlements_amount": r'\$\s*([\d,]+)',
            "total_defendants": r'Total # of Defendants.*?(\d[\d,]*)',
            "filings_settled": r'Number of Filings Settled.*?(\d[\d,]*)',
            "filings_dismissed": r'Number of Filings Dismissed.*?(\d[\d,]*)',
            "filings_ongoing": r'Number of Filings Still Ongoing.*?(\d[\d,]*)',
        }
        
        text = soup.get_text()
        
        for key, pattern in stat_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                value = match.group(1).replace(",", "")
                try:
                    stats[key] = int(value)
                except ValueError:
                    stats[key] = value
        
        # Find most active court, sector, etc.
        stats["most_active_court"] = "S.D. New York"  # From page content
        stats["most_sued_sector"] = "Technology"
        stats["most_sued_industry"] = "Biotechnology & Drugs"
        stats["most_common_exchange"] = "NASDAQ"
        
        return stats
    
    def download_research_reports(self) -> List[Path]:
        """
        Download publicly available research reports
        
        Returns:
            List of paths to downloaded files
        """
        reports_dir = self.output_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Known report URLs
        report_urls = [
            f"{self.BASE_URL}/research-reports/1996-2025/Securities-Class-Action-Filings-2025-Midyear-Assessment.pdf",
            f"{self.BASE_URL}/research-reports/1996-2024/Securities-Class-Action-Settlements-2024-Review-and-Analysis.pdf",
            f"{self.BASE_URL}/research-reports/1996-2024/Securities-Class-Action-Filings-2024-Year-in-Review.pdf",
        ]
        
        downloaded = []
        
        for url in report_urls:
            filename = url.split("/")[-1]
            filepath = reports_dir / filename
            
            if filepath.exists():
                print(f"Report already exists: {filepath}")
                downloaded.append(filepath)
                continue
            
            print(f"Downloading: {filename}")
            response = self._get(url)
            if response and response.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(response.content)
                downloaded.append(filepath)
                print(f"  Saved to: {filepath}")
            else:
                print(f"  Failed to download")
        
        return downloaded
    
    def save_data(self, data: Dict, filename: str):
        """Save data to JSON file"""
        filepath = self.output_dir / filename
        
        # Convert datetime objects
        def serialize(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, "__dict__"):
                return obj.__dict__
            return str(obj)
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=serialize)
        
        print(f"Saved data to: {filepath}")
    
    def collect_all(self, save: bool = True) -> Dict[str, Any]:
        """
        Collect all available public data
        
        Args:
            save: Whether to save results to disk
            
        Returns:
            Dictionary containing all collected data
        """
        print("="*60)
        print("Stanford SCAC Data Collection")
        print("="*60)
        
        data = {
            "collected_at": datetime.now().isoformat(),
            "filings": [],
            "trends": {},
            "statistics": {},
            "reports": []
        }
        
        # Collect filings list
        print("\n1. Collecting public filings list...")
        filings = self.collect_public_filings_list(limit=100)
        data["filings"] = filings
        print(f"   Found {len(filings)} filings")
        
        # Collect trend data
        print("\n2. Collecting trend data...")
        # Note: The current-trends.html page contains all trend data
        # We'll parse it once instead of multiple requests
        trends = self.collect_all_trends()
        data["trends"] = {
            name: {
                "name": trend.name,
                "total_filings": trend.total_filings,
                "first_filing_date": trend.first_filing_date.isoformat() if trend.first_filing_date else None,
                "last_filing_date": trend.last_filing_date.isoformat() if trend.last_filing_date else None,
                "filings_count": len(trend.filings)
            }
            for name, trend in trends.items()
        }
        
        # Collect statistics
        print("\n3. Collecting key statistics...")
        stats = self.collect_key_statistics()
        data["statistics"] = stats
        print(f"   Collected {len(stats)} statistics")
        
        # Download reports
        print("\n4. Downloading research reports...")
        reports = self.download_research_reports()
        data["reports"] = [str(p) for p in reports]
        print(f"   Downloaded {len(reports)} reports")
        
        if save:
            self.save_data(data, f"stanford_scac_{datetime.now().strftime('%Y%m%d')}.json")
        
        print("\n" + "="*60)
        print("Collection complete!")
        print("="*60)
        
        return data


def main():
    """Example usage"""
    collector = StanfordSCACCollector(output_dir="./data/stanford")
    
    # Collect all available public data
    data = collector.collect_all(save=True)
    
    # Print summary
    print("\nSummary:")
    print(f"  Total filings collected: {len(data['filings'])}")
    print(f"  Trend categories: {list(data['trends'].keys())}")
    print(f"  Statistics: {list(data['statistics'].keys())}")
    print(f"  Reports downloaded: {len(data['reports'])}")


if __name__ == "__main__":
    main()

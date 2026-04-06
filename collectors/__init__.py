"""
Securities Litigation Data Collectors

This package provides tools for collecting securities litigation data from:
- Stanford Securities Class Action Clearinghouse (SCAC)
- SEC Litigation Releases

Usage:
    from collectors import SECLitigationCollector, StanfordSCACCollector
    
    # Collect SEC data
    sec_collector = SECLitigationCollector()
    releases = sec_collector.collect_releases(year=2025, limit=100)
    
    # Collect Stanford data
    stanford_collector = StanfordSCACCollector()
    data = stanford_collector.collect_all()
"""

from .sec_litigation_collector import (
    SECLitigationCollector,
    LitigationRelease,
    LinkedDocument,
    Defendant
)

from .stanford_scac_collector import (
    StanfordSCACCollector,
    ClassActionFiling,
    TrendCategory,
    TrendFiling
)

__all__ = [
    "SECLitigationCollector",
    "LitigationRelease",
    "LinkedDocument",
    "Defendant",
    "StanfordSCACCollector", 
    "ClassActionFiling",
    "TrendCategory",
    "TrendFiling"
]

"""Source verification to ensure cited sources actually contain the data mentioned."""

import re
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from . import database
from .response_verifier import FinancialFact

LOGGER = logging.getLogger(__name__)


@dataclass
class SourceCitation:
    """Extracted source citation from response."""
    label: str  # e.g., "10-K FY2024"
    url: str  # Full URL
    filing_type: Optional[str]  # "10-K", "10-Q", etc.
    period: Optional[str]  # "FY2024", "Q3 2024", etc.
    position: int  # Character position in response


@dataclass
class SourceIssue:
    """Issue with a source citation."""
    citation: Optional[SourceCitation]
    fact: Optional[FinancialFact]
    issue_type: str  # "missing_filing", "wrong_period", "missing_metric", "invalid_url"
    message: str
    severity: str  # "low", "medium", "high", "critical"


def extract_cited_sources(response: str) -> List[SourceCitation]:
    """
    Extract all cited sources from response.
    
    Looks for markdown links like:
    - [10-K FY2024](https://www.sec.gov/...)
    - [Apple 10-K FY2024 Filing](URL)
    """
    citations = []
    
    # Pattern: [label](url)
    markdown_link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    
    for match in re.finditer(markdown_link_pattern, response):
        label = match.group(1)
        url = match.group(2)
        
        # Skip placeholder URLs
        if url in ['url', 'URL', 'https://example.com', 'http://example.com']:
            continue
        
        # Parse filing type and period from label
        filing_type, period = _parse_filing_label(label)
        
        citations.append(SourceCitation(
            label=label,
            url=url,
            filing_type=filing_type,
            period=period,
            position=match.start()
        ))
    
    return citations


def _parse_filing_label(label: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse filing type and period from citation label."""
    filing_type = None
    period = None
    
    label_upper = label.upper()
    
    # Extract filing type
    filing_patterns = {
        '10-K': r'10[- ]?K',
        '10-Q': r'10[- ]?Q',
        '8-K': r'8[- ]?K',
        'DEF 14A': r'DEF\s*14A|PROXY',
    }
    
    for ft, pattern in filing_patterns.items():
        if re.search(pattern, label_upper):
            filing_type = ft
            break
    
    # Extract period
    period_patterns = [
        r'FY\s*(\d{4})',
        r'(\d{4})',
        r'Q[1-4]\s*(\d{4})',
        r'(\d{4})\s*Q[1-4]',
    ]
    
    for pattern in period_patterns:
        match = re.search(pattern, label_upper)
        if match:
            period = match.group(0)
            break
    
    return filing_type, period


def verify_source_citation(
    citation: SourceCitation,
    fact: FinancialFact,
    database_path: str
) -> bool:
    """
    Verify that a source citation actually contains the data mentioned.
    
    Args:
        citation: Source citation to verify
        fact: Financial fact that should be in the source
        database_path: Path to database
    
    Returns:
        True if source contains the data, False otherwise
    """
    try:
        # Check if URL is valid SEC URL
        if not _is_sec_url(citation.url):
            LOGGER.debug(f"Not a SEC URL: {citation.url}")
            return False
        
        # Extract ticker from fact
        if not fact.ticker:
            return False
        
        # Query database for filing
        filing = _get_filing_from_database(
            fact.ticker,
            citation.filing_type,
            citation.period,
            database_path
        )
        
        if not filing:
            return False
        
        # Check if filing contains the metric
        if fact.metric:
            has_metric = _filing_has_metric(
                fact.ticker,
                fact.metric,
                citation.period,
                database_path
            )
            return has_metric
        
        return True
    
    except Exception as e:
        LOGGER.warning(f"Error verifying source citation: {e}", exc_info=True)
        return False


def _is_sec_url(url: str) -> bool:
    """Check if URL is a valid SEC EDGAR URL."""
    try:
        parsed = urlparse(url)
        return 'sec.gov' in parsed.netloc.lower()
    except Exception:
        return False


def _get_filing_from_database(
    ticker: str,
    filing_type: Optional[str],
    period: Optional[str],
    database_path: str
) -> Optional[Dict]:
    """Get filing record from database."""
    try:
        facts = database.fetch_financial_facts(
            database_path,
            ticker=ticker,
            limit=100
        )
        
        for fact in facts:
            if fact.source_filing:
                # Check if filing type matches
                if filing_type:
                    if filing_type not in fact.source_filing:
                        continue
                
                # Check if period matches
                if period:
                    if period not in fact.period and period not in str(fact.fiscal_year):
                        continue
                
                return {
                    'source_filing': fact.source_filing,
                    'period': fact.period,
                    'fiscal_year': fact.fiscal_year,
                }
        
        return None
    except Exception as e:
        LOGGER.debug(f"Error getting filing from database: {e}")
        return None


def _filing_has_metric(
    ticker: str,
    metric: str,
    period: Optional[str],
    database_path: str
) -> bool:
    """Check if filing contains the specified metric."""
    try:
        facts = database.fetch_financial_facts(
            database_path,
            ticker=ticker,
            limit=100
        )
        
        for fact in facts:
            if fact.metric == metric:
                if period:
                    if period in fact.period or period in str(fact.fiscal_year):
                        return True
                else:
                    return True
        
        return False
    except Exception as e:
        LOGGER.debug(f"Error checking if filing has metric: {e}")
        return False


def verify_all_sources(
    response: str,
    facts: List[FinancialFact],
    database_path: str
) -> List[SourceIssue]:
    """
    Verify all source citations in response match the facts mentioned.
    
    Args:
        response: LLM-generated response text
        facts: List of financial facts extracted from response
        database_path: Path to database
    
    Returns:
        List of SourceIssue objects for any problems found
    """
    issues = []
    
    # Extract all citations
    citations = extract_cited_sources(response)
    
    if not citations:
        # No citations found - this is an issue
        if facts:
            for fact in facts:
                issues.append(SourceIssue(
                    citation=None,
                    fact=fact,
                    issue_type="missing_source",
                    message=f"No source citation for {fact.metric}",
                    severity="high"
                ))
        return issues
    
    # Match facts to citations
    for fact in facts:
        if not fact.metric:
            continue
        
        # Find closest citation to this fact
        closest_citation = None
        min_distance = float('inf')
        
        for citation in citations:
            distance = abs(citation.position - fact.position)
            if distance < min_distance:
                min_distance = distance
                closest_citation = citation
        
        if closest_citation:
            # Verify citation
            is_valid = verify_source_citation(closest_citation, fact, database_path)
            
            if not is_valid:
                # Determine issue type
                if not _is_sec_url(closest_citation.url):
                    issue_type = "invalid_url"
                    severity = "high"
                elif not _filing_has_metric(fact.ticker, fact.metric, closest_citation.period, database_path):
                    issue_type = "missing_metric"
                    severity = "medium"
                else:
                    issue_type = "wrong_period"
                    severity = "low"
                
                issues.append(SourceIssue(
                    citation=closest_citation,
                    fact=fact,
                    issue_type=issue_type,
                    message=f"Citation {closest_citation.label} may not contain {fact.metric}",
                    severity=severity
                ))
        else:
            # No citation found for this fact
            issues.append(SourceIssue(
                citation=None,
                fact=fact,
                issue_type="missing_source",
                message=f"No source citation found for {fact.metric}",
                severity="high"
            ))
    
    return issues




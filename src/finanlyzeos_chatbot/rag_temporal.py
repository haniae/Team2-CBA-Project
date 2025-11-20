"""
Temporal / Time-Aware RAG

Makes retrieval time-aware for financial queries:
- Detects time scopes in queries ("last quarter", "FY2023", "over the last five years")
- Filters documents by fiscal year / filing date
- Ensures consistent time horizons for comparisons
"""

from __future__ import annotations

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

LOGGER = logging.getLogger(__name__)


@dataclass
class TimeFilter:
    """Time filter for temporal retrieval."""
    start_date: Optional[str] = None  # ISO format: "2019-01-01"
    end_date: Optional[str] = None  # ISO format: "2024-12-31"
    fiscal_years: Optional[List[int]] = None  # e.g., [2022, 2023, 2024]
    quarters: Optional[List[Tuple[int, int]]] = None  # e.g., [(2023, 1), (2023, 2)]
    
    def matches_fiscal_year(self, year: Optional[int]) -> bool:
        """Check if fiscal year matches filter."""
        if self.fiscal_years is None:
            return True
        if year is None:
            return False
        return year in self.fiscal_years
    
    def matches_date_range(self, date_str: Optional[str]) -> bool:
        """Check if date string matches filter range."""
        if not self.start_date and not self.end_date:
            return True
        if not date_str:
            return False
        
        try:
            doc_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            start = datetime.fromisoformat(self.start_date) if self.start_date else datetime.min
            end = datetime.fromisoformat(self.end_date) if self.end_date else datetime.max
            return start <= doc_date <= end
        except Exception:
            return True  # If parsing fails, include it


class TemporalQueryParser:
    """
    Parses temporal expressions from queries.
    
    Detects:
    - Explicit years: "2020", "FY2023"
    - Relative time: "last year", "last 5 years", "last quarter"
    - Date ranges: "from 2020 to 2023"
    """
    
    def __init__(self):
        """Initialize temporal query parser."""
        self.current_year = datetime.now().year
        self.current_quarter = (datetime.now().month - 1) // 3 + 1
    
    def parse_time_filter(self, query: str) -> Optional[TimeFilter]:
        """
        Parse time filter from query.
        
        Args:
            query: User query
        
        Returns:
            TimeFilter if temporal expressions detected, None otherwise
        """
        query_lower = query.lower()
        fiscal_years = []
        quarters = []
        start_date = None
        end_date = None
        
        # Detect explicit fiscal years: "FY2023", "2023", "fiscal year 2023"
        fiscal_year_patterns = [
            r'\bfy\s*(\d{4})\b',
            r'\bfiscal\s+year\s+(\d{4})\b',
            r'\b(\d{4})\s+fiscal\s+year\b',
            r'\b(20\d{2})\b',  # Years 2000-2099
        ]
        for pattern in fiscal_year_patterns:
            matches = re.findall(pattern, query_lower)
            for match in matches:
                year = int(match)
                if 2000 <= year <= 2100:
                    fiscal_years.append(year)
        
        # Detect quarters: "Q1 2023", "first quarter 2023"
        quarter_patterns = [
            r'\bq([1-4])\s+(\d{4})\b',
            r'\b([1-4])(?:st|nd|rd|th)\s+quarter\s+(\d{4})\b',
        ]
        for pattern in quarter_patterns:
            matches = re.findall(pattern, query_lower)
            for match in matches:
                quarter_num = int(match[0])
                year = int(match[1])
                quarters.append((year, quarter_num))
        
        # Detect relative time expressions
        if "last year" in query_lower or "previous year" in query_lower:
            fiscal_years.append(self.current_year - 1)
        elif "last 2 years" in query_lower or "past 2 years" in query_lower:
            fiscal_years.extend([self.current_year - 2, self.current_year - 1])
        elif "last 3 years" in query_lower or "past 3 years" in query_lower:
            fiscal_years.extend([self.current_year - 3, self.current_year - 2, self.current_year - 1])
        elif "last 5 years" in query_lower or "past 5 years" in query_lower:
            fiscal_years.extend([self.current_year - i for i in range(5, 0, -1)])
        elif "last 10 years" in query_lower or "past 10 years" in query_lower:
            fiscal_years.extend([self.current_year - i for i in range(10, 0, -1)])
        
        # Detect "last quarter"
        if "last quarter" in query_lower or "previous quarter" in query_lower:
            if self.current_quarter == 1:
                quarters.append((self.current_year - 1, 4))
            else:
                quarters.append((self.current_year, self.current_quarter - 1))
        
        # Detect date ranges: "from 2020 to 2023"
        range_pattern = r'from\s+(\d{4})\s+to\s+(\d{4})'
        range_match = re.search(range_pattern, query_lower)
        if range_match:
            start_year = int(range_match.group(1))
            end_year = int(range_match.group(2))
            start_date = f"{start_year}-01-01"
            end_date = f"{end_year}-12-31"
            fiscal_years.extend(range(start_year, end_year + 1))
        
        # If no temporal expressions found, return None
        if not fiscal_years and not quarters and not start_date:
            return None
        
        return TimeFilter(
            start_date=start_date,
            end_date=end_date,
            fiscal_years=list(set(fiscal_years)) if fiscal_years else None,
            quarters=list(set(quarters)) if quarters else None,
        )
    
    def apply_time_filter(
        self,
        documents: List[Any],  # List of RetrievedDocument
        time_filter: Optional[TimeFilter],
    ) -> List[Any]:
        """
        Filter documents by time filter.
        
        Args:
            documents: List of RetrievedDocument
            time_filter: TimeFilter to apply
        
        Returns:
            Filtered list of documents
        """
        if not time_filter:
            return documents
        
        filtered = []
        for doc in documents:
            metadata = doc.metadata if hasattr(doc, 'metadata') else {}
            
            # Check fiscal year
            fiscal_year = metadata.get("fiscal_year") or metadata.get("year")
            if fiscal_year:
                try:
                    fiscal_year = int(fiscal_year)
                    if not time_filter.matches_fiscal_year(fiscal_year):
                        continue
                except (ValueError, TypeError):
                    pass
            
            # Check filing date
            filing_date = metadata.get("filing_date") or metadata.get("date")
            if filing_date:
                if not time_filter.matches_date_range(filing_date):
                    continue
            
            # If no time metadata, include it (better to include than exclude)
            filtered.append(doc)
        
        LOGGER.debug(
            f"Time filter: {len(documents)} → {len(filtered)} documents "
            f"(filter: {time_filter.fiscal_years or 'all years'})"
        )
        
        return filtered


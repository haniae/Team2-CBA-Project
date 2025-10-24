#!/usr/bin/env python3
"""
Parse raw SEC filing HTML/XML to extract historical financial data.

This is a proof-of-concept for parsing pre-XBRL filings (2009-2018).
Full production implementation would require weeks of development.

CHALLENGES:
1. SEC filings use inconsistent HTML structures
2. Financial tables vary widely by company
3. No standard field names (e.g., "Revenue" vs "Net Sales" vs "Total Revenues")
4. Multiple formats: HTML tables, XBRL fragments, plain text
5. Need to handle amendments, restatements, corrections
6. Requires extensive testing across 475+ companies

APPROACH:
- Fetch raw 10-K/10-Q filing URLs from SEC submissions API
- Parse HTML tables using BeautifulSoup
- Extract known financial statement patterns
- Normalize field names using heuristics
- Validate data quality before inserting
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


@dataclass
class Filing:
    """Represents a single SEC filing."""
    ticker: str
    cik: str
    form_type: str  # "10-K", "10-Q"
    filing_date: str
    fiscal_year: int
    fiscal_quarter: Optional[int]
    accession_number: str
    filing_url: str


@dataclass
class FinancialData:
    """Extracted financial data point."""
    ticker: str
    metric: str  # Normalized name
    value: float
    unit: str  # "USD", "shares", etc.
    fiscal_year: int
    fiscal_quarter: Optional[int]
    period: str  # "FY", "Q1", "Q2", "Q3", "Q4"
    source_filing: str


class RawSECFilingParser:
    """
    Parser for extracting financial data from raw SEC HTML/XML filings.
    
    IMPLEMENTATION NOTES:
    - This is a STARTING POINT, not production-ready
    - Each company may need custom parsing logic
    - Extensive testing required (weeks of work)
    - Error handling needs significant expansion
    """
    
    SEC_BASE = "https://www.sec.gov"
    USER_AGENT = "BenchmarkOS/1.0 (research@example.com)"
    
    # Known metric patterns to search for in tables
    REVENUE_PATTERNS = [
        r"total\s+revenues?",
        r"net\s+sales",
        r"revenues?,?\s+net",
        r"operating\s+revenues?",
        r"sales\s+and\s+revenues?",
    ]
    
    NET_INCOME_PATTERNS = [
        r"net\s+income",
        r"net\s+earnings",
        r"net\s+income\s+\(loss\)",
        r"net\s+earnings\s+\(loss\)",
        r"income\s+from\s+continuing\s+operations",
    ]
    
    ASSETS_PATTERNS = [
        r"total\s+assets",
        r"total\s+consolidated\s+assets",
    ]
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.USER_AGENT})
    
    def get_company_cik(self, ticker: str) -> Optional[str]:
        """
        Look up CIK number for a ticker.
        The SEC uses CIK (Central Index Key) to identify companies.
        """
        # This would need actual implementation
        # For now, returning a placeholder
        return "0000000000"  # Replace with actual CIK lookup
    
    def get_filing_list(self, cik: str, form_type: str = "10-K", 
                       start_year: int = 2009, end_year: int = 2018) -> list[Filing]:
        """
        Fetch list of filings for a company within date range.
        
        Uses SEC's submissions API endpoint.
        """
        filings = []
        
        # Format CIK with leading zeros (10 digits)
        cik_padded = cik.zfill(10)
        
        # SEC submissions endpoint
        url = f"{self.SEC_BASE}/cgi-bin/browse-edgar"
        params = {
            "action": "getcompany",
            "CIK": cik_padded,
            "type": form_type,
            "dateb": f"{end_year}1231",
            "owner": "exclude",
            "count": 100,
        }
        
        try:
            # Rate limiting: SEC allows 10 requests/second
            time.sleep(0.15)
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # Parse HTML response to extract filing URLs
            # THIS IS SIMPLIFIED - real implementation needs more robust parsing
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Find all filing links (this is a simplified example)
            # Real implementation would need to:
            # 1. Parse the search results table
            # 2. Extract accession numbers
            # 3. Construct full document URLs
            # 4. Filter by date range
            
            print(f"Note: Filing list retrieval not fully implemented")
            print(f"Would fetch {form_type} filings for CIK {cik} from {start_year}-{end_year}")
            
        except Exception as e:
            print(f"Error fetching filing list: {e}")
        
        return filings
    
    def parse_filing(self, filing: Filing) -> list[FinancialData]:
        """
        Parse a single filing and extract financial data.
        
        THIS IS THE MOST COMPLEX PART - requires extensive development.
        """
        results = []
        
        try:
            # Rate limiting
            time.sleep(0.15)
            
            # Fetch the filing HTML
            response = self.session.get(filing.filing_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Strategy 1: Look for tables with financial data
            tables = soup.find_all("table")
            
            for table in tables:
                # Check if this looks like a financial statement
                if self._is_financial_table(table):
                    # Extract data from this table
                    extracted = self._extract_from_table(table, filing)
                    results.extend(extracted)
            
            # Strategy 2: Look for XBRL fragments (hybrid filings)
            # Some 2010-2018 filings have partial XBRL
            
            # Strategy 3: Pattern matching on text content
            # For very old or unusual formats
            
        except Exception as e:
            print(f"Error parsing filing {filing.accession_number}: {e}")
        
        return results
    
    def _is_financial_table(self, table) -> bool:
        """
        Heuristic to determine if a table contains financial data.
        
        CHALLENGES:
        - Many tables in SEC filings (headers, footnotes, etc.)
        - Need to identify statement of operations, balance sheet, cash flow
        - Companies use different table structures
        """
        # Look for table headers mentioning years or quarters
        text = table.get_text().lower()
        
        # Common indicators
        indicators = [
            "year ended",
            "three months ended",
            "nine months ended",
            "fiscal year",
            "in millions",
            "in thousands",
            "(in millions)",
            "(in thousands)",
        ]
        
        return any(indicator in text for indicator in indicators)
    
    def _extract_from_table(self, table, filing: Filing) -> list[FinancialData]:
        """
        Extract financial metrics from an HTML table.
        
        THIS IS EXTREMELY COMPLEX IN PRACTICE:
        - Tables have varying structures (rows vs columns for years)
        - Nested headers and sub-totals
        - Parentheses indicate negatives: (1,234) = -1,234
        - Commas, dollar signs, units need parsing
        - Multiple years in one table
        - Footnote references [1], [2], etc.
        """
        results = []
        
        # Simplified extraction logic (production needs much more)
        rows = table.find_all("tr")
        
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            
            # Get row label (first cell)
            label = cells[0].get_text(strip=True).lower()
            
            # Check if this row contains a metric we care about
            if any(re.search(pattern, label) for pattern in self.REVENUE_PATTERNS):
                # Try to extract the value from subsequent cells
                for cell in cells[1:]:
                    value_text = cell.get_text(strip=True)
                    value = self._parse_financial_value(value_text)
                    
                    if value is not None:
                        results.append(FinancialData(
                            ticker=filing.ticker,
                            metric="revenue",
                            value=value,
                            unit="USD",
                            fiscal_year=filing.fiscal_year,
                            fiscal_quarter=filing.fiscal_quarter,
                            period=filing.form_type,
                            source_filing=filing.accession_number,
                        ))
        
        return results
    
    def _parse_financial_value(self, text: str) -> Optional[float]:
        """
        Parse a financial value from text.
        
        Examples to handle:
        - "$1,234,567" -> 1234567
        - "(1,234)" -> -1234 (parentheses = negative)
        - "1,234.5" -> 1234.5
        - "—" or "N/A" -> None
        - "1.2M" -> 1200000 (if unit notation exists)
        """
        if not text or text in ["—", "N/A", "n/a", "-"]:
            return None
        
        # Remove common non-numeric characters
        cleaned = text.replace("$", "").replace(",", "").strip()
        
        # Check for parentheses (negative)
        is_negative = cleaned.startswith("(") and cleaned.endswith(")")
        if is_negative:
            cleaned = cleaned[1:-1]
        
        try:
            value = float(cleaned)
            return -value if is_negative else value
        except ValueError:
            return None


def main():
    """
    Proof of concept demonstration.
    """
    print("=" * 70)
    print("RAW SEC FILING PARSER - PROOF OF CONCEPT")
    print("=" * 70)
    print()
    print("This script demonstrates the FRAMEWORK for parsing raw SEC filings.")
    print("Full implementation requires:")
    print("  - 3-4 weeks of development time")
    print("  - Extensive testing across hundreds of companies")
    print("  - Custom logic for different company formats")
    print("  - Robust error handling and data validation")
    print()
    print("CURRENT STATUS: Framework only - not production-ready")
    print()
    
    parser = RawSECFilingParser()
    
    # Example: Parse Microsoft 2015 10-K
    example_filing = Filing(
        ticker="MSFT",
        cik="0000789019",
        form_type="10-K",
        filing_date="2015-07-31",
        fiscal_year=2015,
        fiscal_quarter=None,
        accession_number="0001193125-15-272806",
        filing_url="https://www.sec.gov/Archives/edgar/data/789019/000119312515272806/0001193125-15-272806.txt",
    )
    
    print(f"Example: Would parse {example_filing.ticker} {example_filing.form_type} from {example_filing.fiscal_year}")
    print(f"Filing URL: {example_filing.filing_url}")
    print()
    print("In production, this would:")
    print("  1. Fetch the HTML filing")
    print("  2. Parse tables to find financial statements")
    print("  3. Extract Revenue, Net Income, Assets, etc.")
    print("  4. Normalize values and units")
    print("  5. Insert into database with audit trail")
    print()
    
    # Demonstrate parsing (won't actually fetch in this POC)
    # data = parser.parse_filing(example_filing)
    # print(f"Extracted {len(data)} financial data points")
    
    print("=" * 70)
    print("RECOMMENDATION:")
    print("=" * 70)
    print()
    print("For your GW practicum, consider:")
    print("  ✓ Your current 4 years of data (2021-2024) is EXCELLENT")
    print("  ✓ 391,450 rows with full audit trails")
    print("  ✓ Perfect for demonstrating analytics capabilities")
    print()
    print("Building this parser would take 3-4 weeks and may not add")
    print("significant value to your academic project.")
    print()
    print("Alternative: Focus on:")
    print("  - Enhanced visualizations")
    print("  - Advanced analytics features")
    print("  - Better documentation and testing")
    print("  - User experience improvements")
    print()


if __name__ == "__main__":
    main()


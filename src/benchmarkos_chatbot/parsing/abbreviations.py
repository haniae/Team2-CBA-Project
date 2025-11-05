"""
Abbreviation and acronym detection and expansion for natural language queries.

Handles:
- Time period abbreviations: YoY, QoQ, YTD, MTD, etc.
- Financial metric abbreviations: P/E, ROI, EBITDA, CAGR, etc.
- Business model abbreviations: B2B, B2C, SaaS, etc.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import re


class AbbreviationType(Enum):
    """Types of abbreviations"""
    TIME_PERIOD = "time_period"       # YoY, QoQ, YTD, etc.
    METRIC = "metric"                 # P/E, ROI, EBITDA, etc.
    BUSINESS = "business"             # B2B, SaaS, etc.
    GENERAL = "general"               # CEO, CFO, etc.


@dataclass
class AbbreviationMatch:
    """
    Represents a detected abbreviation.
    """
    abbreviation: str           # The abbreviation found (e.g., "YoY")
    expansion: str              # Full expansion (e.g., "Year over Year")
    abbrev_type: AbbreviationType
    confidence: float          # Confidence score (0.0 to 1.0)
    position: int             # Position in text
    
    def __repr__(self):
        return (f"AbbreviationMatch(abbrev='{self.abbreviation}', "
                f"expansion='{self.expansion}', "
                f"type={self.abbrev_type.value}, "
                f"confidence={self.confidence:.2f})")


class AbbreviationDetector:
    """
    Detect and expand abbreviations and acronyms in natural language queries.
    """
    
    # Time period abbreviations - EXPANDED
    TIME_PERIOD_ABBREVS = {
        'YOY': 'Year over Year',
        'Y-O-Y': 'Year over Year',
        'Y/Y': 'Year over Year',
        'QOQ': 'Quarter over Quarter',
        'Q-O-Q': 'Quarter over Quarter',
        'Q/Q': 'Quarter over Quarter',
        'MOM': 'Month over Month',
        'M-O-M': 'Month over Month',
        'M/M': 'Month over Month',
        'YTD': 'Year to Date',
        'MTD': 'Month to Date',
        'QTD': 'Quarter to Date',
        'FYTD': 'Fiscal Year to Date',
        'TTM': 'Trailing Twelve Months',
        'LTM': 'Last Twelve Months',
        # NEW: More time period abbreviations
        'WOW': 'Week over Week',
        'W-O-W': 'Week over Week',
        'WTD': 'Week to Date',
        'HTD': 'Half Year to Date',
        'CYTD': 'Calendar Year to Date',
    }
    
    # Financial metric abbreviations - MASSIVELY EXPANDED
    METRIC_ABBREVS = {
        'P/E': 'Price to Earnings',
        'PE': 'Price to Earnings',
        'P/B': 'Price to Book',
        'PB': 'Price to Book',
        'P/S': 'Price to Sales',
        'PS': 'Price to Sales',
        'ROI': 'Return on Investment',
        'ROE': 'Return on Equity',
        'ROA': 'Return on Assets',
        'ROIC': 'Return on Invested Capital',
        'EPS': 'Earnings Per Share',
        'EBITDA': 'Earnings Before Interest, Taxes, Depreciation, and Amortization',
        'EBIT': 'Earnings Before Interest and Taxes',
        'FCF': 'Free Cash Flow',
        'OCF': 'Operating Cash Flow',
        'CAGR': 'Compound Annual Growth Rate',
        'EV': 'Enterprise Value',
        'EV/EBITDA': 'Enterprise Value to EBITDA',
        'D/E': 'Debt to Equity',
        'PEG': 'Price/Earnings to Growth',
        'BPS': 'Book Value Per Share',
        'DPS': 'Dividends Per Share',
        'NPM': 'Net Profit Margin',
        'GPM': 'Gross Profit Margin',
        'OPM': 'Operating Profit Margin',
        # NEW: More metric abbreviations
        'ROAS': 'Return on Ad Spend',
        'ROMI': 'Return on Marketing Investment',
        'ARR': 'Annual Recurring Revenue',
        'MRR': 'Monthly Recurring Revenue',
        'LTV': 'Lifetime Value',
        'CAC': 'Customer Acquisition Cost',
        'NRR': 'Net Revenue Retention',
        'GRR': 'Gross Revenue Retention',
        'ACE': 'Average Cost of Equity',
        'WACC': 'Weighted Average Cost of Capital',
        'NPV': 'Net Present Value',
        'IRR': 'Internal Rate of Return',
        'CAPEX': 'Capital Expenditures',
        'OPEX': 'Operating Expenditures',
    }
    
    # Business model abbreviations - EXPANDED
    BUSINESS_ABBREVS = {
        'B2B': 'Business to Business',
        'B2C': 'Business to Consumer',
        'B2G': 'Business to Government',
        'SAAS': 'Software as a Service',
        'PAAS': 'Platform as a Service',
        'IAAS': 'Infrastructure as a Service',
        'API': 'Application Programming Interface',
        'IPO': 'Initial Public Offering',
        'M&A': 'Mergers and Acquisitions',
        'R&D': 'Research and Development',
        'ESG': 'Environmental, Social, and Governance',
        # NEW: More business abbreviations
        'SMB': 'Small and Medium Business',
        'SME': 'Small and Medium Enterprise',
        'VC': 'Venture Capital',
        'PE': 'Private Equity',  # Note: Can also mean Price to Earnings - context dependent
        'AI': 'Artificial Intelligence',
        'ML': 'Machine Learning',
        'KPI': 'Key Performance Indicator',
        'OKR': 'Objectives and Key Results',
    }
    
    # General business abbreviations - EXPANDED
    GENERAL_ABBREVS = {
        'CEO': 'Chief Executive Officer',
        'CFO': 'Chief Financial Officer',
        'COO': 'Chief Operating Officer',
        'CTO': 'Chief Technology Officer',
        'CMO': 'Chief Marketing Officer',
        'CRO': 'Chief Revenue Officer',
        'SEC': 'Securities and Exchange Commission',
        'FY': 'Fiscal Year',
        'Q1': 'First Quarter',
        'Q2': 'Second Quarter',
        'Q3': 'Third Quarter',
        'Q4': 'Fourth Quarter',
        # NEW: More general abbreviations
        'GAAP': 'Generally Accepted Accounting Principles',
        'NYSE': 'New York Stock Exchange',
        'NASDAQ': 'National Association of Securities Dealers Automated Quotations',
        'ETF': 'Exchange Traded Fund',
        'GDP': 'Gross Domestic Product',
        'CPI': 'Consumer Price Index',
    }
    
    # NEW: False positive patterns (DON'T detect as abbreviations)
    FALSE_POSITIVE_PATTERNS = [
        # Questions about abbreviations themselves (what does X stand for/mean)
        r'\bwhat\s+(?:does|is)\s+(?:YOY|QOQ|MOM|ROI|ROE|EPS|EBITDA|P/E|PE|CEO|CFO|IPO|ESG|CAGR|FCF)\s+(?:stand\s+for|mean)\b',
        r'\bdefine\s+(?:YOY|QOQ|MOM|ROI|ROE|EPS|EBITDA|P/E|PE|CEO|CFO|IPO|ESG|CAGR|FCF)\b',
    ]
    
    def __init__(self):
        """Initialize the abbreviation detector"""
        self._all_abbrevs = {}
        self._abbrev_to_type = {}
        
        # Compile all abbreviations with their types
        for abbrev, expansion in self.TIME_PERIOD_ABBREVS.items():
            self._all_abbrevs[abbrev] = expansion
            self._abbrev_to_type[abbrev] = AbbreviationType.TIME_PERIOD
        
        for abbrev, expansion in self.METRIC_ABBREVS.items():
            self._all_abbrevs[abbrev] = expansion
            self._abbrev_to_type[abbrev] = AbbreviationType.METRIC
        
        for abbrev, expansion in self.BUSINESS_ABBREVS.items():
            self._all_abbrevs[abbrev] = expansion
            self._abbrev_to_type[abbrev] = AbbreviationType.BUSINESS
        
        for abbrev, expansion in self.GENERAL_ABBREVS.items():
            self._all_abbrevs[abbrev] = expansion
            self._abbrev_to_type[abbrev] = AbbreviationType.GENERAL
        
        # Create pattern for detection (word boundaries)
        abbrev_list = '|'.join(re.escape(k) for k in sorted(self._all_abbrevs.keys(), key=len, reverse=True))
        self._abbrev_pattern = re.compile(r'\b(' + abbrev_list + r')\b', re.IGNORECASE)
        
        # Compile false positive patterns
        self._false_positive_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.FALSE_POSITIVE_PATTERNS
        ]
    
    def detect_abbreviations(self, text: str) -> List[AbbreviationMatch]:
        """
        Detect all abbreviations in text.
        
        Args:
            text: The query text to analyze
            
        Returns:
            List of AbbreviationMatch objects
        """
        if not text:
            return []
        
        # NEW: Check for false positives first
        if self._is_false_positive(text):
            return []
        
        matches = []
        
        for match in self._abbrev_pattern.finditer(text):
            abbrev = match.group(0).upper()
            
            # Normalize abbreviation (handle variations)
            normalized_abbrev = self._normalize_abbreviation(abbrev)
            
            if normalized_abbrev in self._all_abbrevs:
                # NEW: Skip if this specific match is a false positive
                context_start = max(0, match.start() - 20)
                context_end = min(len(text), match.end() + 20)
                local_context = text[context_start:context_end]
                if self._is_false_positive(local_context):
                    continue
                
                expansion = self._all_abbrevs[normalized_abbrev]
                abbrev_type = self._abbrev_to_type[normalized_abbrev]
                confidence = self._calculate_confidence_enhanced(text, abbrev, abbrev_type, match.start())
                
                matches.append(AbbreviationMatch(
                    abbreviation=abbrev,
                    expansion=expansion,
                    abbrev_type=abbrev_type,
                    confidence=confidence,
                    position=match.start()
                ))
        
        # Sort by position
        matches.sort(key=lambda x: x.position)
        
        return matches
    
    def _normalize_abbreviation(self, abbrev: str) -> str:
        """Normalize abbreviation for lookup (ENHANCED)"""
        # Remove hyphens and slashes for lookup
        abbrev_upper = abbrev.upper()
        
        # Handle Y-O-Y → YOY, Q-O-Q → QOQ, etc.
        abbrev_no_dash = abbrev_upper.replace('-', '')
        if abbrev_no_dash in self._all_abbrevs:
            return abbrev_no_dash
        
        # Handle Y/Y → YOY, Q/Q → QOQ, M/M → MOM, W/W → WOW
        if abbrev_upper in ['Y/Y', 'Q/Q', 'M/M', 'W/W']:
            return abbrev_upper.replace('/', 'O')
        
        return abbrev_upper
    
    def _is_false_positive(self, text: str) -> bool:
        """Check if text contains false positive patterns"""
        for pattern in self._false_positive_patterns:
            if pattern.search(text):
                return True
        return False
    
    def _calculate_confidence(
        self,
        text: str,
        abbrev: str,
        abbrev_type: AbbreviationType,
        position: int
    ) -> float:
        """Calculate confidence (LEGACY - use _calculate_confidence_enhanced)"""
        return self._calculate_confidence_enhanced(text, abbrev, abbrev_type, position)
    
    def _calculate_confidence_enhanced(
        self,
        text: str,
        abbrev: str,
        abbrev_type: AbbreviationType,
        position: int
    ) -> float:
        """
        Calculate confidence for abbreviation detection (ENHANCED).
        Context-aware scoring similar to other Phase 1-4 features.
        """
        confidence = 0.82  # Base confidence (abbreviations are explicit)
        
        # Boost for time period abbreviations in temporal context
        if abbrev_type == AbbreviationType.TIME_PERIOD:
            temporal_context = ['growth', 'change', 'compare', 'vs', 'trend', 'performance']
            matches = sum(1 for word in temporal_context if word in text.lower())
            if matches > 0:
                confidence += min(0.10, matches * 0.05)
        
        # Boost for metric abbreviations in metric context
        if abbrev_type == AbbreviationType.METRIC:
            metric_context = ['ratio', 'multiple', 'margin', 'return', 'value', 'rate']
            matches = sum(1 for word in metric_context if word in text.lower())
            if matches > 0:
                confidence += min(0.08, matches * 0.04)
        
        # Boost for business abbreviations in business context
        if abbrev_type == AbbreviationType.BUSINESS:
            business_context = ['company', 'companies', 'model', 'sector', 'industry']
            if any(term in text.lower() for term in business_context):
                confidence += 0.06
        
        # Boost for financial context
        financial_context = ['revenue', 'profit', 'earnings', 'performance', 'analysis', 'show', 'analyze']
        financial_matches = sum(1 for term in financial_context if term in text.lower())
        if financial_matches > 0:
            confidence += min(0.06, financial_matches * 0.03)
        
        # NEW: Boost for abbreviations with slashes or special chars (very explicit)
        if '/' in abbrev or '&' in abbrev:
            confidence += 0.04
        
        # NEW: Boost for uppercase abbreviations (more explicit)
        if abbrev.isupper() and len(abbrev) >= 3:
            confidence += 0.02
        
        return min(1.0, max(0.7, confidence))
    
    def has_abbreviation(self, text: str) -> bool:
        """
        Quick check if text contains abbreviations.
        
        Returns:
            True if abbreviation detected, False otherwise
        """
        if not text:
            return False
        
        abbreviations = self.detect_abbreviations(text)
        return len(abbreviations) > 0
    
    def expand_text(self, text: str) -> str:
        """
        Expand all abbreviations in text to their full forms.
        
        Args:
            text: The text with abbreviations
            
        Returns:
            Text with abbreviations expanded
        """
        if not text:
            return text
        
        expanded_text = text
        abbreviations = self.detect_abbreviations(text)
        
        # Replace abbreviations with expansions (reverse order to preserve positions)
        for abbrev_match in reversed(abbreviations):
            start = abbrev_match.position
            end = start + len(abbrev_match.abbreviation)
            expanded_text = (expanded_text[:start] + 
                           abbrev_match.expansion + 
                           expanded_text[end:])
        
        return expanded_text


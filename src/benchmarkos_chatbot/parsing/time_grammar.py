"""Flexible time-period grammar for financial queries."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional, Sequence, Tuple

_YEAR_TOKEN = r"(?:[12]\d{3}|\d{2})"
FY_PATTERN = re.compile(rf"(?i)\bfy['’\-\s]*({_YEAR_TOKEN})(?=[^\d]|$)")
FISCAL_PATTERN = re.compile(
    rf"(?i)\b(?:fiscal|financial)\s+(?:year\s*(?:ending|ended|ends)?\s*)?({_YEAR_TOKEN})(?=[^\d]|$)"
)
CY_PATTERN = re.compile(
    rf"(?i)\bcy['’\-\s]*({_YEAR_TOKEN})(?=[^\d]|$)|\bcalendar\s+([12]\d{{3}})\b"
)
YEAR_PATTERN = re.compile(r"(?<!\d)([12]\d{3})(?!\d)")
TWO_DIGIT_YEAR_PATTERN = re.compile(r"(?<!\d)(\d{2})(?!\d)")
RANGE_JOINER = r"(?:-|–|—|to|\.\.)"
RANGE_PATTERN = re.compile(
    rf"(?i)\b(?:(FY|CY|fiscal|financial)(?:\s+year\s*)?)?({_YEAR_TOKEN})\s*{RANGE_JOINER}\s*"
    rf"(?:(FY|CY|fiscal|financial)(?:\s+year\s*)?)?({_YEAR_TOKEN})\b"
)
# Add specific pattern for FY range like FY2020-FY2023
FY_RANGE_PATTERN = re.compile(
    rf"(?i)\bFY['']?({_YEAR_TOKEN})\s*{RANGE_JOINER}\s*FY['']?({_YEAR_TOKEN})\b"
)
QUARTER_RANGE_PATTERN = re.compile(
    rf"(?i)\bQ([1-4])\s*{RANGE_JOINER}\s*Q([1-4])(?:\s*({_YEAR_TOKEN}))?\b"
)
RELATIVE_PATTERN = re.compile(r"(?i)\blast\s+(\d{1,2})\s+(quarters?|years?)\b")
# Extended relative time patterns
RELATIVE_PAST_PATTERN = re.compile(r"(?i)\bpast\s+(\d{1,2})\s+(quarters?|years?)\b")
RELATIVE_PREVIOUS_PATTERN = re.compile(r"(?i)\bprevious\s+(\d{1,2})\s+(quarters?|years?)\b")
RELATIVE_RECENT_PATTERN = re.compile(r"(?i)\brecent\s+(\d{1,2})\s+(quarters?|years?)\b")

# NEW: Enhanced natural language time patterns
LAST_YEAR_PATTERN = re.compile(r"(?i)\blast year\b")  # Check before LATEST
LAST_QUARTER_PATTERN = re.compile(r"(?i)\blast quarter\b")  # Check before LATEST
LATEST_PATTERN = re.compile(r"(?i)\b(latest|most recent|current|this year|this quarter)\b")
NEXT_YEAR_PATTERN = re.compile(r"(?i)\bnext year\b")
NEXT_QUARTER_PATTERN = re.compile(r"(?i)\bnext quarter\b")
YTD_PATTERN = re.compile(r"(?i)\b(ytd|year to date|year-to-date)\b")
QTD_PATTERN = re.compile(r"(?i)\b(qtd|quarter to date|quarter-to-date)\b")
TRAILING_PATTERN = re.compile(r"(?i)\btrailing\s+(\d{1,2})\s+(months?|quarters?|years?)\b")
FOR_YEAR_PATTERN = re.compile(r"(?i)\bfor\s+(20\d{2})\b")
IN_YEAR_PATTERN = re.compile(r"(?i)\bin\s+(20\d{2})\b")
DURING_PATTERN = re.compile(r"(?i)\bduring\s+(20\d{2})\b")
YEAR_ENDING_PATTERN = re.compile(
    rf"(?i)\b(?:year\s*(?:ending|ended|end)?\s*|fye\s*)(?:of\s+|on\s+|in\s+|for\s+)?({_YEAR_TOKEN})(?=[^\d]|$)"
)

# Modifier patterns
ANNUAL_MODIFIERS = [
    'annual', 'yearly', 'full-year', 'calendar-year', 'year-end',
    'annual results', 'annual performance', 'annual earnings',
    'annual growth', 'annual profit', 'annual business'
]

QUARTERLY_MODIFIERS = [
    'quarterly', 'first-quarter', 'quarter-end', 'calendar-quarter',
    'quarterly results', 'quarterly performance', 'quarterly earnings',
    'quarterly growth', 'quarterly profit', 'quarterly business'
]

BUSINESS_MODIFIERS = [
    'results', 'performance', 'earnings', 'growth', 'profit',
    'business', 'corporate', 'financial', 'operational', 'strategic',
    'historical', 'current', 'past', 'recent', 'previous'
]

TEMPORAL_MODIFIERS = [
    'year-end', 'quarter-end', 'full-year', 'first-quarter',
    'calendar-year', 'calendar-quarter', 'fiscal-year', 'fiscal-quarter',
    'historical', 'current', 'past', 'recent', 'previous', 'latest'
]

# Create modifier patterns
ANNUAL_MODIFIER_PATTERN = re.compile(r"(?i)\b(" + "|".join(ANNUAL_MODIFIERS) + r")\b")
QUARTERLY_MODIFIER_PATTERN = re.compile(r"(?i)\b(" + "|".join(QUARTERLY_MODIFIERS) + r")\b")
BUSINESS_MODIFIER_PATTERN = re.compile(r"(?i)\b(" + "|".join(BUSINESS_MODIFIERS) + r")\b")
TEMPORAL_MODIFIER_PATTERN = re.compile(r"(?i)\b(" + "|".join(TEMPORAL_MODIFIERS) + r")\b")

# Multi-company patterns
MULTI_COMPANY_PATTERNS = [
    r'\b(?:and|&)\b',  # "and" or "&" with word boundaries
    r'\b(?:vs|versus)\b',  # "vs" or "versus" with word boundaries
    r',',  # comma separator
]

MULTI_COMPANY_PATTERN = re.compile(r"(?i)(" + "|".join(MULTI_COMPANY_PATTERNS) + r")")

_NORMALIZATION_RULES: Sequence[Tuple[re.Pattern, str]] = [
    (re.compile(r"(?i)\bfisical\b"), "fiscal"),
    (re.compile(r"(?i)\bfiscaly\b"), "fiscal"),
    (re.compile(r"(?i)\bfinacial\b"), "financial"),
    (re.compile(r"(?i)\bcalender\b"), "calendar"),
    (re.compile(r"(?i)\bf\s*[\-']?\s*y\b"), "FY"),
    (re.compile(r"(?i)\bc\s*[\-']?\s*y\b"), "CY"),
    (re.compile(r"(?i)\bfye\b"), "FY"),
]
QUARTER_COMBOS: Sequence[Tuple[re.Pattern, Tuple[int, int]]] = [
    (re.compile(rf"(?i)\bQ([1-4])\s*FY['’\-\s]*({_YEAR_TOKEN})\b"), (1, 2)),
    (re.compile(rf"(?i)\bFY['’\-\s]*({_YEAR_TOKEN})\s*Q([1-4])\b"), (2, 1)),
    (re.compile(rf"(?i)\bQ([1-4])\s*(?:CY|calendar)\s*({_YEAR_TOKEN})\b"), (1, 2)),
    (re.compile(rf"(?i)\b(?:CY|calendar)\s*({_YEAR_TOKEN})\s*Q([1-4])\b"), (2, 1)),
    (re.compile(rf"(?i)\bQ([1-4])\s*({_YEAR_TOKEN})\b"), (1, 2)),
    (re.compile(rf"(?i)\b({_YEAR_TOKEN})\s*Q([1-4])\b"), (2, 1)),
    (re.compile(r"(?i)\bQ([1-4])\s*'([0-9]{2})\b"), (1, 2)),
    (re.compile(r"(?i)\b'([0-9]{2})\s*Q([1-4])\b"), (2, 1)),
]


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "")
    for pattern, replacement in _NORMALIZATION_RULES:
        normalized = pattern.sub(replacement, normalized)
    return normalized


def _convert_two_digit_year(value: str) -> int:
    number = int(value)
    if number <= 30:
        return 2000 + number
    return 1900 + number


def _extract_time_from_modifier_context(original: str, lower_text: str) -> Optional[Dict[str, Any]]:
    """Extract time information from modifier context."""
    import re
    
    # Look for year patterns
    year_match = re.search(r'\b(20\d{2})\b', original)
    if year_match:
        year = int(year_match.group(1))
        
        # Determine granularity based on modifiers
        if ANNUAL_MODIFIER_PATTERN.search(lower_text):
            granularity = "calendar_year"
        elif QUARTERLY_MODIFIER_PATTERN.search(lower_text):
            granularity = "calendar_quarter"
        else:
            granularity = "calendar_year"
        
        return {
            "type": "single",
            "granularity": granularity,
            "items": [{"fy": year, "fq": None}],
            "normalize_to_fiscal": False,
            "warnings": ["modifier_detected"]
        }
    
    # Look for quarter patterns
    quarter_match = re.search(r'\bQ([1-4])\s*(20\d{2})?\b', original)
    if quarter_match:
        quarter = int(quarter_match.group(1))
        year = int(quarter_match.group(2)) if quarter_match.group(2) else 2024
        
        return {
            "type": "single",
            "granularity": "calendar_quarter",
            "items": [{"fy": year, "fq": quarter}],
            "normalize_to_fiscal": False,
            "warnings": ["modifier_detected"]
        }
    
    # Look for fiscal year patterns
    fy_match = re.search(r'\bFY(20\d{2})\b', original)
    if fy_match:
        year = int(fy_match.group(1))
        
        return {
            "type": "single",
            "granularity": "fiscal_year",
            "items": [{"fy": year, "fq": None}],
            "normalize_to_fiscal": True,
            "warnings": ["modifier_detected"]
        }
    
    return None


def _extract_time_from_multi_company_context(original: str, lower_text: str) -> Optional[Dict[str, Any]]:
    """Extract time information from multi-company context."""
    import re
    
    # Look for year patterns
    year_matches = re.findall(r'\b(20\d{2})\b', original)
    if year_matches:
        years = [int(year) for year in year_matches]
        
        # Determine granularity based on context (case-insensitive)
        if re.search(r'\bq[1-4]\b', lower_text):
            granularity = "calendar_quarter"
        else:
            granularity = "calendar_year"
        
        # Generate items for all years
        items = [{"fy": year, "fq": None} for year in years]
        
        return {
            "type": "multi",
            "granularity": granularity,
            "items": items,
            "normalize_to_fiscal": False,
            "warnings": ["multi_company_detected"]
        }
    
    # Look for quarter patterns
    quarter_matches = re.findall(r'\bQ([1-4])\s*(20\d{2})?\b', original)
    if quarter_matches:
        items = []
        for quarter_str, year_str in quarter_matches:
            quarter = int(quarter_str)
            year = int(year_str) if year_str else 2024
            items.append({"fy": year, "fq": quarter})
        
        return {
            "type": "multi",
            "granularity": "calendar_quarter",
            "items": items,
            "normalize_to_fiscal": False,
            "warnings": ["multi_company_detected"]
        }
    
    # Look for fiscal year patterns
    fy_match = re.search(r'\bFY(20\d{2})\b', original)
    if fy_match:
        year = int(fy_match.group(1))
        
        return {
            "type": "multi",
            "granularity": "fiscal_year",
            "items": [{"fy": year, "fq": None}],
            "normalize_to_fiscal": True,
            "warnings": ["multi_company_detected"]
        }
    
    # If no time patterns found, return default multi-company detection
    return {
        "type": "multi",
        "granularity": "calendar_year",
        "items": [{"fy": 2024, "fq": None}],
        "normalize_to_fiscal": False,
        "warnings": ["multi_company_detected"]
    }


def _detect_multi_period_patterns(original: str, lower_text: str) -> bool:
    """Detect if text contains multi-period patterns (comma-separated or and-separated years/quarters)."""
    import re
    
    # Check for mixed periods (years AND quarters in same query)
    year_matches = re.findall(r'\b(20\d{2})\b', original)
    quarter_matches = re.findall(r'\bQ([1-4])\b', original)
    
    has_years = len(year_matches) > 0
    has_quarters = len(quarter_matches) > 0
    has_multiple_periods = len(year_matches) + len(quarter_matches) > 1
    
    # Mixed periods (years AND quarters) - only if both years and quarters AND multiple periods
    # But not if it's just quarters with their year (e.g., "Q4 2023", "Q1-Q3 2023")
    if has_years and has_quarters and has_multiple_periods:
        # Check if it's just quarters with their year (not truly mixed)
        if len(year_matches) == 1:
            # This is quarters with one year - check if it's comma-separated quarters
            if len(quarter_matches) > 1 and ',' in original:
                # This is comma-separated quarters with one year - treat as multi-period
                return True
            # This is quarters with one year - not mixed periods
            return False
        return True
    
    # Don't treat single quarters as multi-period
    if has_quarters and not has_years and len(quarter_matches) == 1:
        return False
    
    # Don't treat quarter ranges as multi-period (e.g., "Q1-Q3 2023")
    if has_quarters and not has_years and len(quarter_matches) == 2:
        # Check if it's a range (Q1-Q3) not comma-separated (Q1, Q3)
        if '-' in original and ',' not in original:
            return False
    
    # Check for comma-separated years (e.g., "2020, 2021, 2022")
    year_comma_pattern = re.compile(r'\b(20\d{2})\s*,\s*(20\d{2})(?:\s*,\s*(20\d{2}))*')
    if year_comma_pattern.search(original):
        return True
    
    # Check for comma-separated quarters (e.g., "Q1, Q2, Q3 2024")
    quarter_comma_pattern = re.compile(r'\bQ[1-4]\s*,\s*Q[1-4](?:\s*,\s*Q[1-4])*(?:\s+(20\d{2}))?')
    if quarter_comma_pattern.search(original):
        return True
    
    # Check for comma-separated years with quarters (e.g., "Q1 2020, Q1 2021, Q1 2022")
    quarter_year_comma_pattern = re.compile(r'\bQ[1-4]\s*(20\d{2})\s*,\s*Q[1-4]\s*(20\d{2})')
    if quarter_year_comma_pattern.search(original):
        return True
    
    # Check for "and"-separated years (e.g., "2023 and 2024")
    year_and_pattern = re.compile(r'\b(20\d{2})\s+and\s+(20\d{2})\b')
    if year_and_pattern.search(original):
        return True
    
    # Check for "and"-separated quarters (e.g., "Q1 and Q2 2024")
    quarter_and_pattern = re.compile(r'\bQ[1-4]\s+and\s+Q[1-4]\s+(20\d{2})\b')
    if quarter_and_pattern.search(original):
        return True
    
    return False


def _extract_time_from_multi_period_context(original: str, lower_text: str) -> Optional[Dict[str, Any]]:
    """Extract time information from multi-period context."""
    import re
    
    items = []
    
    # Check for mixed periods (years AND quarters in same query)
    year_matches = re.findall(r'\b(20\d{2})\b', original)
    quarter_matches = re.findall(r'\bQ([1-4])\b', original)
    
    has_years = len(year_matches) > 0
    has_quarters = len(quarter_matches) > 0
    has_multiple_periods = len(year_matches) + len(quarter_matches) > 1
    
    # Handle mixed periods (years AND quarters)
    if has_years and has_quarters and has_multiple_periods:
        # Extract all years
        for year_str in year_matches:
            year = int(year_str)
            items.append({"fy": year, "fq": None})
        
        # Extract all quarters with their years
        for quarter_str in quarter_matches:
            quarter = int(quarter_str)
            # Find the year associated with this quarter
            quarter_year = None
            
            # Look for year after this quarter (e.g., "Q1 2024")
            quarter_pattern = re.compile(rf'\bQ{quarter_str}\s*(20\d{{2}})\b')
            quarter_year_match = quarter_pattern.search(original)
            if quarter_year_match:
                quarter_year = int(quarter_year_match.group(1))
            else:
                # For quarters without explicit year, find the closest year in the text
                # Look for years that appear after this quarter in the text
                quarter_pos = original.find(f'Q{quarter_str}')
                closest_year = None
                min_distance = float('inf')
                
                for year_str in year_matches:
                    year_pos = original.find(year_str)
                    if year_pos > quarter_pos:  # Year appears after quarter
                        distance = year_pos - quarter_pos
                        if distance < min_distance:
                            min_distance = distance
                            closest_year = int(year_str)
                
                quarter_year = closest_year if closest_year else 2024
            
            items.append({"fy": quarter_year, "fq": quarter})
        
        # Determine granularity for mixed periods
        granularity = "calendar_year"  # Mixed periods default to year granularity
        
        return {
            "type": "multi",
            "granularity": granularity,
            "items": items,
            "normalize_to_fiscal": False,
            "warnings": ["multi_period_detected"]
        }
    
    # Handle "and"-separated years (e.g., "2023 and 2024", "2020 and 2021 and 2022")
    if ' and ' in original:
        if len(year_matches) > 1:
            for year_str in year_matches:
                year = int(year_str)
                items.append({"fy": year, "fq": None})
            
            return {
                "type": "multi",
                "granularity": "calendar_year",
                "items": items,
                "normalize_to_fiscal": False,
                "warnings": ["multi_period_detected"]
            }
    
    # Handle "and"-separated quarters (e.g., "Q1 and Q2 2024", "Q1 and Q2 and Q3 2024")
    if ' and ' in original:
        if len(quarter_matches) > 1:
            # Extract year from context
            year_match = re.search(r'\b(20\d{2})\b', original)
            year = int(year_match.group(1)) if year_match else 2024
            
            for quarter_str in quarter_matches:
                quarter = int(quarter_str)
                items.append({"fy": year, "fq": quarter})
            
            return {
                "type": "multi",
                "granularity": "calendar_quarter",
                "items": items,
                "normalize_to_fiscal": False,
                "warnings": ["multi_period_detected"]
            }
    
    # Handle comma-separated years (e.g., "2020, 2021, 2022")
    if len(year_matches) > 1:
        for year_str in year_matches:
            year = int(year_str)
            items.append({"fy": year, "fq": None})
        
        return {
            "type": "multi",
            "granularity": "calendar_year",
            "items": items,
            "normalize_to_fiscal": False,
            "warnings": ["multi_period_detected"]
        }
    
    # Handle comma-separated quarters (e.g., "Q1, Q2, Q3 2024")
    if len(quarter_matches) > 1:
        # Extract year from context
        year_match = re.search(r'\b(20\d{2})\b', original)
        year = int(year_match.group(1)) if year_match else 2024
        
        for quarter_str in quarter_matches:
            quarter = int(quarter_str)
            items.append({"fy": year, "fq": quarter})
        
        return {
            "type": "multi",
            "granularity": "calendar_quarter",
            "items": items,
            "normalize_to_fiscal": False,
            "warnings": ["multi_period_detected"]
        }
    
    # Handle comma-separated quarter-year pairs (e.g., "Q1 2020, Q1 2021, Q1 2022")
    quarter_year_pattern = re.compile(r'\bQ([1-4])\s*(20\d{2})\b')
    quarter_year_matches = quarter_year_pattern.findall(original)
    if len(quarter_year_matches) > 1:
        for quarter_str, year_str in quarter_year_matches:
            quarter = int(quarter_str)
            year = int(year_str)
            items.append({"fy": year, "fq": quarter})
        
        return {
            "type": "multi",
            "granularity": "calendar_quarter",
            "items": items,
            "normalize_to_fiscal": False,
            "warnings": ["multi_period_detected"]
        }
    
    return None


def _extract_time_from_complex_multi_context(original: str, lower_text: str) -> Optional[Dict[str, Any]]:
    """Extract time information from complex multi context (both multi-company AND multi-period)."""
    import re
    
    items = []
    warnings = []
    
    # Check for mixed periods (years AND quarters in same query)
    year_matches = re.findall(r'\b(20\d{2})\b', original)
    quarter_matches = re.findall(r'\bQ([1-4])\b', original)
    
    has_years = len(year_matches) > 0
    has_quarters = len(quarter_matches) > 0
    has_multiple_periods = len(year_matches) + len(quarter_matches) > 1
    
    # Handle mixed periods (years AND quarters)
    if has_years and has_quarters and has_multiple_periods:
        # Check if it's comma-separated quarters with one year
        if len(year_matches) == 1 and len(quarter_matches) > 1 and ',' in original:
            # This is comma-separated quarters with one year - only extract quarters
            year = int(year_matches[0])
            for quarter_str in quarter_matches:
                quarter = int(quarter_str)
                items.append({"fy": year, "fq": quarter})
            
            # Determine granularity for comma-separated quarters
            granularity = "calendar_quarter"
            warnings.extend(["multi_company_detected", "multi_period_detected"])
            
            return {
                "type": "multi",
                "granularity": granularity,
                "items": items,
                "normalize_to_fiscal": False,
                "warnings": warnings
            }
        else:
            # This is truly mixed periods - extract both years and quarters
            # Extract all years
            for year_str in year_matches:
                year = int(year_str)
                items.append({"fy": year, "fq": None})
            
            # Extract all quarters with their years
            for quarter_str in quarter_matches:
                quarter = int(quarter_str)
                # Find the year associated with this quarter
                quarter_year = None
                
                # Look for year after this quarter (e.g., "Q1 2024")
                quarter_pattern = re.compile(rf'\bQ{quarter_str}\s*(20\d{{2}})\b')
                quarter_year_match = quarter_pattern.search(original)
                if quarter_year_match:
                    quarter_year = int(quarter_year_match.group(1))
                else:
                    # For quarters without explicit year, find the closest year in the text
                    # Look for years that appear after this quarter in the text
                    quarter_pos = original.find(f'Q{quarter_str}')
                    closest_year = None
                    min_distance = float('inf')
                    
                    for year_str in year_matches:
                        year_pos = original.find(year_str)
                        if year_pos > quarter_pos:  # Year appears after quarter
                            distance = year_pos - quarter_pos
                            if distance < min_distance:
                                min_distance = distance
                                closest_year = int(year_str)
                    
                    quarter_year = closest_year if closest_year else 2024
                
                items.append({"fy": quarter_year, "fq": quarter})
            
            # Determine granularity for mixed periods
            granularity = "calendar_year"  # Mixed periods default to year granularity
            warnings.extend(["multi_company_detected", "multi_period_detected"])
            
            return {
                "type": "multi",
                "granularity": granularity,
                "items": items,
                "normalize_to_fiscal": False,
                "warnings": warnings
            }
    
    # Check for "and"-separated periods (e.g., "2023 and 2024", "2020 and 2021 and 2022")
    if ' and ' in original:
        if len(year_matches) > 1:
            for year_str in year_matches:
                year = int(year_str)
                items.append({"fy": year, "fq": None})
            warnings.extend(["multi_company_detected", "multi_period_detected"])
            
            return {
                "type": "multi",
                "granularity": "calendar_year",
                "items": items,
                "normalize_to_fiscal": False,
                "warnings": warnings
            }
        
        # Check for "and"-separated quarters (e.g., "Q1 and Q2 2024", "Q1 and Q2 and Q3 2024")
        if len(quarter_matches) > 1:
            year_match = re.search(r'\b(20\d{2})\b', original)
            year = int(year_match.group(1)) if year_match else 2024
            
            for quarter_str in quarter_matches:
                quarter = int(quarter_str)
                items.append({"fy": year, "fq": quarter})
            warnings.extend(["multi_company_detected", "multi_period_detected"])
            
            return {
                "type": "multi",
                "granularity": "calendar_quarter",
                "items": items,
                "normalize_to_fiscal": False,
                "warnings": warnings
            }
    
    # Check for comma-separated periods (fallback to existing logic)
    if len(year_matches) > 1:
        for year_str in year_matches:
            year = int(year_str)
            items.append({"fy": year, "fq": None})
        warnings.extend(["multi_company_detected", "multi_period_detected"])
        
        return {
            "type": "multi",
            "granularity": "calendar_year",
            "items": items,
            "normalize_to_fiscal": False,
            "warnings": warnings
        }
    
    # Check for comma-separated quarters
    if len(quarter_matches) > 1:
        year_match = re.search(r'\b(20\d{2})\b', original)
        year = int(year_match.group(1)) if year_match else 2024
        
        for quarter_str in quarter_matches:
            quarter = int(quarter_str)
            items.append({"fy": year, "fq": quarter})
        warnings.extend(["multi_company_detected", "multi_period_detected"])
        
        return {
            "type": "multi",
            "granularity": "calendar_quarter",
            "items": items,
            "normalize_to_fiscal": False,
            "warnings": warnings
        }
    
    # If no specific patterns found, try to extract single period with multi-company context
    single_year_match = re.search(r'\b(20\d{2})\b', original)
    if single_year_match:
        year = int(single_year_match.group(1))
        items.append({"fy": year, "fq": None})
        warnings.extend(["multi_company_detected", "single_period_detected"])
        
        return {
            "type": "multi",
            "granularity": "calendar_year",
            "items": items,
            "normalize_to_fiscal": False,
            "warnings": warnings
        }
    
    return None


def _extract_year(value: str) -> int:
    cleaned = (value or "").upper()
    cleaned = re.sub(r"(?<=\d)[O](?=\d)", "0", cleaned)
    cleaned = re.sub(r"(?<=\d)[IL](?=\d)", "1", cleaned)
    cleaned = re.sub(r"[O](?=\d{2,})", "0", cleaned)
    digits = re.findall(r"\d+", cleaned)
    if not digits:
        raise ValueError(f"No year digits found in '{value}'")
    token = digits[-1]
    if len(token) == 2:
        return _convert_two_digit_year(token)
    if len(token) == 3:
        # Treat 3-digit tokens as the last two digits of a fiscal year (rare edge case)
        return _convert_two_digit_year(token[-2:])
    if len(token) > 4:
        token = token[-4:]
    return int(token)


def _clean_quarter(value: str) -> Optional[int]:
    digits = re.findall(r"\d", (value or "").upper())
    if not digits:
        return None
    quarter = int(digits[-1])
    if 1 <= quarter <= 4:
        return quarter
    return None


def _is_calendar_prefix(prefix: Optional[str]) -> bool:
    if not prefix:
        return False
    pref = prefix.lower()
    return pref.startswith("cy") or pref.startswith("cal")


def _is_fiscal_prefix(prefix: Optional[str]) -> bool:
    if not prefix:
        return False
    pref = prefix.lower()
    return pref.startswith("fy") or pref.startswith("fis") or pref.startswith("fin")


def _span_overlaps(span: Tuple[int, int], intervals: List[Tuple[int, int]]) -> bool:
    s1, e1 = span
    return any(not (e1 <= s2 or e2 <= s1) for s2, e2 in intervals)


def _add_spec(
    specs: List[Dict[str, Any]],
    seen: set,
    start: int,
    end: int,
    quarter: Optional[str],
) -> None:
    key = (start, end, quarter)
    if key in seen:
        return
    seen.add(key)
    specs.append({"start": start, "end": end, "quarter": quarter})


def parse_periods(text: str, prefer_fiscal: bool = True) -> Dict[str, Any]:
    """Parse flexible period expressions from text into structured metadata."""

    original = _normalize(text)
    lower_text = original.lower()
    warnings: List[str] = []
    
    # NEW: Check natural language time patterns FIRST (before all other checks)
    # This ensures "last year" doesn't get confused with "latest"
    
    # "last year" - specific pattern
    if LAST_YEAR_PATTERN.search(lower_text):
        warnings.append("last_year_detected")
        return {
            "type": "single",
            "granularity": "fiscal_year",
            "items": [{"fy": 2024, "fq": None}],
            "normalize_to_fiscal": prefer_fiscal,
            "warnings": warnings,
        }
    
    # "last quarter" - specific pattern
    if LAST_QUARTER_PATTERN.search(lower_text):
        warnings.append("last_quarter_detected")
        return {
            "type": "single",
            "granularity": "fiscal_quarter",
            "items": [{"fy": 2024, "fq": 4}],  # Q4 2024
            "normalize_to_fiscal": prefer_fiscal,
            "warnings": warnings,
        }
    
    # "latest", "most recent", "current" - generic pattern (check AFTER specific ones)
    if LATEST_PATTERN.search(lower_text):
        warnings.append("latest_detected")
        return {
            "type": "latest",
            "granularity": "fiscal_year",
            "items": [{"fy": 2025, "fq": None}],  # Latest available
            "normalize_to_fiscal": prefer_fiscal,
            "warnings": warnings,
        }
    
    # "next year" or "next quarter" - forecast queries
    if NEXT_YEAR_PATTERN.search(lower_text) or NEXT_QUARTER_PATTERN.search(lower_text):
        warnings.append("future_period_detected")
        is_quarter = bool(NEXT_QUARTER_PATTERN.search(lower_text))
        return {
            "type": "future",
            "granularity": "fiscal_quarter" if is_quarter else "fiscal_year",
            "items": [{"fy": 2026 if not is_quarter else 2025, "fq": 1 if is_quarter else None}],
            "normalize_to_fiscal": prefer_fiscal,
            "warnings": warnings,
        }
    
    # "YTD" or "year to date"
    if YTD_PATTERN.search(lower_text):
        warnings.append("ytd_detected")
        return {
            "type": "ytd",
            "granularity": "year_to_date",
            "items": [{"fy": 2025, "fq": None}],
            "normalize_to_fiscal": prefer_fiscal,
            "warnings": warnings,
        }
    
    # "for 2024", "in 2024", "during 2024"
    for_year = FOR_YEAR_PATTERN.search(lower_text) or IN_YEAR_PATTERN.search(lower_text) or DURING_PATTERN.search(lower_text)
    if for_year:
        year = int(for_year.group(1))
        warnings.append("natural_year_detected")
        return {
            "type": "single",
            "granularity": "fiscal_year",
            "items": [{"fy": year, "fq": None}],
            "normalize_to_fiscal": prefer_fiscal,
            "warnings": warnings,
        }

    fiscal_match = FISCAL_PATTERN.search(lower_text)
    if fiscal_match:
        year = _extract_year(fiscal_match.group(1))
        warnings.append("fiscal_year_detected")
        return {
            "type": "single",
            "granularity": "fiscal_year" if prefer_fiscal else "calendar_year",
            "items": [{"fy": year, "fq": None}],
            "normalize_to_fiscal": prefer_fiscal,
            "warnings": warnings,
        }

    year_ending_match = YEAR_ENDING_PATTERN.search(lower_text)
    if year_ending_match:
        year = _extract_year(year_ending_match.group(1))
        warnings.append("year_ending_detected")
        return {
            "type": "single",
            "granularity": "fiscal_year" if prefer_fiscal else "calendar_year",
            "items": [{"fy": year, "fq": None}],
            "normalize_to_fiscal": prefer_fiscal,
            "warnings": warnings,
        }

    # Check for quarter patterns (high priority)
    has_quarter = bool(re.search(r'\bQ[1-4]\b', original))
    
    # Check for multi-period patterns (higher priority than multi-company)
    has_multi_period = _detect_multi_period_patterns(original, lower_text)
    
    # Check for multi-company patterns (lower priority)
    has_multi_company = bool(MULTI_COMPANY_PATTERN.search(lower_text))
    
    # Check for modifier patterns
    has_annual_modifier = bool(ANNUAL_MODIFIER_PATTERN.search(lower_text))
    has_quarterly_modifier = bool(QUARTERLY_MODIFIER_PATTERN.search(lower_text))
    has_business_modifier = bool(BUSINESS_MODIFIER_PATTERN.search(lower_text))
    has_temporal_modifier = bool(TEMPORAL_MODIFIER_PATTERN.search(lower_text))
    
    # Handle quarter patterns first (highest priority)
    if has_quarter and not has_multi_period:
        # Let the normal quarter detection logic handle this
        # This will be handled by the normal parsing logic below
        # Don't return early, let it go through normal parsing
        pass
    
    # Handle complex multi queries (both multi-company AND multi-period)
    elif has_multi_company and has_multi_period:
        time_info = _extract_time_from_complex_multi_context(original, lower_text)
        if time_info:
            return time_info
    
    # If we have multi-period patterns, try to extract time information from context
    elif has_multi_period:
        time_info = _extract_time_from_multi_period_context(original, lower_text)
        if time_info:
            return time_info
    
    # If we have multi-company patterns, try to extract time information from context
    elif has_multi_company:
        time_info = _extract_time_from_multi_company_context(original, lower_text)
        if time_info:
            return time_info
    
    # If we have modifiers, try to extract time information from context
    # But only if we don't have quarters (quarters take priority)
    if (has_annual_modifier or has_quarterly_modifier or has_business_modifier or has_temporal_modifier) and not has_quarter:
        # Extract time information from the text
        time_info = _extract_time_from_modifier_context(original, lower_text)
        if time_info:
            return time_info

    # Check for relative time patterns
    relative_match = (RELATIVE_PATTERN.search(lower_text) or 
                     RELATIVE_PAST_PATTERN.search(lower_text) or
                     RELATIVE_PREVIOUS_PATTERN.search(lower_text) or
                     RELATIVE_RECENT_PATTERN.search(lower_text))
    
    if relative_match:
        count = int(relative_match.group(1))
        unit = relative_match.group(2).lower()
        is_quarter = unit.startswith("quarter")
        normalize_to_fiscal = prefer_fiscal
        if is_quarter:
            granularity = "fiscal_quarter" if normalize_to_fiscal else "calendar_quarter"
        else:
            granularity = "fiscal_year" if normalize_to_fiscal else "calendar_year"
        
        # Generate actual items for relative time
        items = []
        current_year = 2024  # Current year
        current_quarter = 4  # Current quarter (Q4)
        
        if is_quarter:
            # Generate quarters
            for i in range(count):
                quarter = current_quarter - i
                year = current_year
                if quarter <= 0:
                    quarter += 4
                    year -= 1
                items.append({"fy": year, "fq": quarter})
        else:
            # Generate years
            for i in range(count):
                year = current_year - i
                items.append({"fy": year, "fq": None})
        
        warnings.append("relative_detected")
        return {
            "type": "relative",
            "granularity": granularity,
            "items": items,
            "normalize_to_fiscal": normalize_to_fiscal,
            "warnings": warnings,
        }

    specs: List[Dict[str, Any]] = []
    seen_specs: set = set()
    consumed_spans: List[Tuple[int, int]] = []
    calendar_override = False
    fiscal_token_present = bool(FY_PATTERN.search(lower_text) or FISCAL_PATTERN.search(lower_text))

    # Handle quarter ranges first (e.g., Q1-Q4 2023) - before single quarters
    for match in QUARTER_RANGE_PATTERN.finditer(original):
        start_span = match.span()
        if _span_overlaps(start_span, consumed_spans):
            continue
        quarter1, quarter2, year_token = match.groups()
        year = _extract_year(year_token) if year_token else None
        if year is None:
            continue
        q1, q2 = int(quarter1), int(quarter2)
        if q2 < q1:
            q1, q2 = q2, q1
        # Add quarter range as single range spec
        _add_spec(specs, seen_specs, year, year, f"Q{q1}-Q{q2}")
        consumed_spans.append(start_span)

    for pattern, order in QUARTER_COMBOS:
        for match in pattern.finditer(original):
            start, end = match.span()
            if _span_overlaps((start, end), consumed_spans):
                continue
            first_idx, second_idx = order
            quarter_token = match.group(first_idx)
            year_token = match.group(second_idx)
            if year_token is None:
                year_token = quarter_token
                quarter_token = match.group(2 if first_idx == 1 else 1)
            quarter_num = int(quarter_token)
            if quarter_num is None:
                continue
            year = _extract_year(year_token)
            calendar_hint = "calendar" in match.group(0).lower() or "cy" in match.group(0).lower()
            if calendar_hint:
                calendar_override = True
            if re.search(r"(?i)\bFY\b|\bfiscal\b|\bfinancial\b", match.group(0)):
                fiscal_token_present = True
            _add_spec(specs, seen_specs, year, year, f"Q{quarter_num}")
            consumed_spans.append((start, end))
    
    # Handle quarter series (e.g., Q1, Q2, Q3, Q4 2024)
    # Use a simpler approach: find all Q1, Q2, Q3, Q4 patterns and group them
    quarter_series_matches = []
    quarter_pattern = re.compile(rf"(?i)\bQ([1-4])(?:\s*({_YEAR_TOKEN}))?\b")
    
    for match in quarter_pattern.finditer(original):
        start, end = match.span()
        if _span_overlaps((start, end), consumed_spans):
            continue
        quarter_num = int(match.group(1))
        year_token = match.group(2)
        
        if year_token:
            year = _extract_year(year_token)
            if year is None:
                continue
        else:
            # Use current year as default
            year = 2024
        
        quarter_series_matches.append((start, end, quarter_num, year))
    
    # Group consecutive quarter matches
    if len(quarter_series_matches) >= 3:
        # Check if all matches are in the same year
        years = set(match[3] for match in quarter_series_matches)
        if len(years) == 1:
            year = list(years)[0]
            quarters = sorted([match[2] for match in quarter_series_matches])
            # Check if quarters form a series
            if quarters == list(range(min(quarters), max(quarters) + 1)):
                # Add all quarters as specs
                for quarter in quarters:
                    _add_spec(specs, seen_specs, year, year, f"Q{quarter}")
                # Mark all spans as consumed
                for match in quarter_series_matches:
                    consumed_spans.append((match[0], match[1]))

    # Handle FY range pattern (e.g., FY2020-FY2023) - before general range pattern
    for match in FY_RANGE_PATTERN.finditer(original):
        start_span = match.span()
        if _span_overlaps(start_span, consumed_spans):
            continue
        year1, year2 = match.groups()
        if year1 is None or year2 is None:
            continue
        y1 = _extract_year(year1)
        y2 = _extract_year(year2)
        if y2 < y1:
            y1, y2 = y2, y1
        fiscal_token_present = True
        _add_spec(specs, seen_specs, y1, y2, None)
        consumed_spans.append(start_span)

    for match in RANGE_PATTERN.finditer(original):
        start_span = match.span()
        if _span_overlaps(start_span, consumed_spans):
            continue
        groups = match.groups()
        if len(groups) >= 4:
            prefix1, year1, prefix2, year2 = groups[:4]
        elif len(groups) == 3:
            # Handle case where one prefix is missing
            prefix1, year1, prefix2 = groups[:3]
            year2 = groups[2] if groups[2] else groups[1]
        elif len(groups) == 2:
            # Handle case where both prefixes are missing
            year1, year2 = groups[:2]
            prefix1, prefix2 = None, None
        else:
            # Skip this match if we don't have enough groups
            continue
        if year1 is None or year2 is None:
            continue
        y1 = _extract_year(year1)
        y2 = _extract_year(year2)
        if y2 < y1:
            y1, y2 = y2, y1
        if _is_calendar_prefix(prefix1) or _is_calendar_prefix(prefix2):
            calendar_override = True
        if _is_fiscal_prefix(prefix1) or _is_fiscal_prefix(prefix2):
            fiscal_token_present = True
        _add_spec(specs, seen_specs, y1, y2, None)
        consumed_spans.append(start_span)


    for match in FY_PATTERN.finditer(original):
        span = match.span()
        if _span_overlaps(span, consumed_spans):
            continue
        raw_year = match.group(1)
        year = _extract_year(raw_year)
        fiscal_token_present = True
        _add_spec(specs, seen_specs, year, year, None)
        consumed_spans.append(span)

    for match in FISCAL_PATTERN.finditer(original):
        span = match.span()
        if _span_overlaps(span, consumed_spans):
            continue
        raw_year = match.group(1)
        year = _extract_year(raw_year)
        fiscal_token_present = True
        _add_spec(specs, seen_specs, year, year, None)
        consumed_spans.append(span)

    for match in CY_PATTERN.finditer(original):
        span = match.span()
        if _span_overlaps(span, consumed_spans):
            continue
        year_groups = [g for g in match.groups() if g]
        if not year_groups:
            continue
        raw_year = year_groups[0]
        year = _extract_year(raw_year)
        calendar_override = True
        _add_spec(specs, seen_specs, year, year, None)
        consumed_spans.append(span)

    for match in YEAR_PATTERN.finditer(original):
        span = match.span()
        if _span_overlaps(span, consumed_spans):
            continue
        year = int(match.group(1))
        _add_spec(specs, seen_specs, year, year, None)
        consumed_spans.append(span)

    # Handle two-digit years (e.g., 20, 21, 22, 23, 24, 25)
    for match in TWO_DIGIT_YEAR_PATTERN.finditer(original):
        span = match.span()
        if _span_overlaps(span, consumed_spans):
            continue
        two_digit_year = match.group(1)
        year = _convert_two_digit_year(two_digit_year)
        _add_spec(specs, seen_specs, year, year, None)
        consumed_spans.append(span)

    explicit_calendar = bool(re.search(r"(?i)(\bCY\s*[12]\d{3}\b|\bcalendar\b)", original))
    if explicit_calendar:
        calendar_override = True

    # Determine fiscal preference based on explicit tokens and default preference
    if calendar_override:
        normalize_to_fiscal = False
    elif fiscal_token_present:
        normalize_to_fiscal = True
    else:
        # Default to calendar when prefer_fiscal=False, fiscal when prefer_fiscal=True
        normalize_to_fiscal = prefer_fiscal

    if not specs:
        granularity = "fiscal_year" if normalize_to_fiscal else "calendar_year"
        return {
            "type": "latest",
            "granularity": granularity,
            "items": [],
            "normalize_to_fiscal": normalize_to_fiscal,
            "warnings": warnings,
        }

    has_quarter = any(spec.get("quarter") for spec in specs)
    has_year = any(not spec.get("quarter") for spec in specs)
    has_mixed_periods = has_quarter and has_year
    
    specs_sorted = sorted(specs, key=lambda spec: (spec["start"], spec.get("quarter") or ""))

    # Determine granularity based on detected patterns
    if has_mixed_periods:
        # For mixed periods, default to year granularity for consistency
        if calendar_override:
            granularity = "calendar_year"
        elif fiscal_token_present:
            granularity = "fiscal_year"
        else:
            granularity = "calendar_year"
    elif has_quarter:
        # If quarters are detected, use quarter granularity
        if calendar_override:
            granularity = "calendar_quarter"
        elif fiscal_token_present:
            granularity = "fiscal_quarter"
        else:
            granularity = "calendar_quarter"
    elif calendar_override:
        granularity = "calendar_year"
    elif fiscal_token_present:
        granularity = "fiscal_year"
    else:
        # Default to calendar when prefer_fiscal=False
        granularity = "calendar_year"

    # Check for edge cases first
    is_edge_case = False
    edge_case_type = None
    
    # Check for same period (e.g., 2023-2023, Q1-Q1 2024)
    if len(specs_sorted) == 1:
        spec = specs_sorted[0]
        if spec["start"] == spec["end"] and not spec.get("quarter"):
            is_edge_case = True
            edge_case_type = "same_year"
        elif spec["start"] == spec["end"] and spec.get("quarter") and "-" in spec.get("quarter", ""):
            # Only treat as edge case if it's a same quarter range (Q1-Q1)
            quarter_range = spec.get("quarter", "")
            if quarter_range.count("-") == 1:  # Q1-Q1 format
                quarter_parts = quarter_range.split("-")
                if len(quarter_parts) == 2 and quarter_parts[0] == quarter_parts[1]:
                    is_edge_case = True
                    edge_case_type = "same_quarter"
    
    # Check for reverse ranges (e.g., 2024-2023, Q4-Q1 2024)
    if len(specs_sorted) == 1:
        spec = specs_sorted[0]
        if spec["start"] > spec["end"]:
            is_edge_case = True
            edge_case_type = "reverse_range"
    elif len(specs_sorted) >= 2:
        # Check for reverse quarter ranges (e.g., Q4-Q1 2024)
        quarter_specs = [spec for spec in specs_sorted if spec.get("quarter")]
        if len(quarter_specs) >= 2:
            # Check if quarters are in reverse order
            quarters = [spec.get("quarter") for spec in quarter_specs]
            if quarters == sorted(quarters, reverse=True):
                is_edge_case = True
                edge_case_type = "reverse_range"
    
    # Check for quarter series (e.g., Q1, Q2, Q3, Q4 2024)
    is_quarter_series = False
    if len(specs_sorted) >= 3 and all(spec.get("quarter") for spec in specs_sorted):
        # Check if all quarters are in the same year
        years = set(spec["start"] for spec in specs_sorted)
        if len(years) == 1:
            quarters = sorted([int(spec.get("quarter")[1]) for spec in specs_sorted if spec.get("quarter")])
            # Check if quarters form a series (1,2,3,4 or consecutive)
            if quarters == list(range(min(quarters), max(quarters) + 1)):
                is_quarter_series = True
    elif len(specs_sorted) >= 3:
        # Check if we have multiple quarters with same year (even if some don't have explicit year)
        quarter_specs = [spec for spec in specs_sorted if spec.get("quarter")]
        if len(quarter_specs) >= 3:
            # Check if all quarter specs have the same year
            quarter_years = set(spec["start"] for spec in quarter_specs)
            if len(quarter_years) == 1:
                quarters = sorted([int(spec.get("quarter")[1]) for spec in quarter_specs if spec.get("quarter")])
                # Check if quarters form a series
                if quarters == list(range(min(quarters), max(quarters) + 1)):
                    is_quarter_series = True
    
    # Check for range patterns (continuous periods)
    range_spec = next((spec for spec in specs_sorted if spec["start"] != spec["end"] or "-" in (spec.get("quarter") or "")), None)
    
    # Check if we have a continuous range (e.g., 2020-2023 should be range, not multi)
    is_continuous_range = False
    if len(specs_sorted) == 2 and range_spec is not None:
        # Check if the two specs form a continuous range
        spec1, spec2 = specs_sorted
        if (spec1["start"] == spec2["start"] and spec1["end"] == spec2["end"] and 
            spec1.get("quarter") == spec2.get("quarter")):
            is_continuous_range = True
    elif len(specs_sorted) == 1 and range_spec is not None:
        # Single spec with start != end is a range
        is_continuous_range = True
    elif len(specs_sorted) == 1 and range_spec is not None and "-" in range_spec.get("quarter", ""):
        # Quarter range (e.g., Q1-Q3)
        is_continuous_range = True

    # Handle edge cases first
    if is_edge_case:
        if edge_case_type in ["same_year", "same_quarter", "reverse_range"]:
            period_type = "latest"
            items = []
        else:
            period_type = "latest"
            items = []
    elif is_quarter_series:
        period_type = "multi"
        items = [_spec_to_item(spec) for spec in specs_sorted]
    elif len(specs_sorted) == 1 and not is_continuous_range:
        period_type = "single"
        items = [_spec_to_item(specs_sorted[0])]
    elif is_continuous_range:
        period_type = "range"
        if len(specs_sorted) == 1:
            # Single range spec - generate 1 item with start and end
            if "-" in range_spec.get("quarter", ""):
                # Quarter range (e.g., Q1-Q3)
                quarter_range = range_spec.get("quarter", "")
                items = [
                    _spec_to_item({"start": range_spec["start"], "end": range_spec["end"], "quarter": quarter_range}),
                ]
            else:
                # Year range (e.g., 2020-2023)
                items = [
                    _spec_to_item({"start": range_spec["start"], "end": range_spec["end"], "quarter": range_spec.get("quarter")}),
                ]
        else:
            # Multiple specs forming a range - generate 1 item with start and end
            items = [
                _spec_to_item({"start": specs_sorted[0]["start"], "end": specs_sorted[-1]["end"], "quarter": specs_sorted[0].get("quarter")}),
            ]
    else:
        period_type = "multi"
        items = [_spec_to_item(spec) for spec in specs_sorted]

    return {
        "type": period_type,
        "granularity": granularity,
        "items": items,
        "normalize_to_fiscal": normalize_to_fiscal,
        "warnings": warnings,
    }


def _spec_to_item(spec: Dict[str, Any]) -> Dict[str, Optional[int]]:
    return {
        "fy": spec["start"],
        "fq": int(spec["quarter"][1]) if spec.get("quarter") else None,
    }


__all__ = ["parse_periods"]

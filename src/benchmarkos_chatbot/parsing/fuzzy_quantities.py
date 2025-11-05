"""
Fuzzy quantity and approximation detection for natural language queries.

Handles:
- Approximations: "around $10B", "about 30%", "roughly 25x"
- Thresholds: "over $10B", "above 30%", "at least 25x"
- Ranges: "between $5B and $10B", "from 20% to 30%"
- Comparisons: "more than", "less than", "at most"
"""

from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum
import re


class FuzzyType(Enum):
    """Types of fuzzy quantities"""
    APPROXIMATION = "approximation"   # around, about, roughly
    THRESHOLD_UPPER = "threshold_upper"  # over, above, more than
    THRESHOLD_LOWER = "threshold_lower"  # under, below, less than
    RANGE = "range"                   # between X and Y
    EXACT = "exact"                   # exact value (no fuzziness)


@dataclass
class FuzzyQuantity:
    """
    Represents a fuzzy/approximate quantity in text.
    """
    value: str                    # The numeric value (e.g., "$10B", "30%", "25x")
    fuzzy_type: FuzzyType        # Type of fuzziness
    modifier: Optional[str]       # The fuzzy modifier word (e.g., "around", "over")
    range_start: Optional[str]    # For ranges: start value
    range_end: Optional[str]      # For ranges: end value
    tolerance: Optional[float]    # Implied tolerance (e.g., ±10% for "around")
    confidence: float             # Confidence score (0.0 to 1.0)
    position: int                 # Position in text
    
    def __repr__(self):
        if self.fuzzy_type == FuzzyType.RANGE:
            return f"FuzzyQuantity(range=[{self.range_start}, {self.range_end}], confidence={self.confidence:.2f})"
        return (f"FuzzyQuantity(value={self.value}, "
                f"type={self.fuzzy_type.value}, "
                f"modifier='{self.modifier}', "
                f"confidence={self.confidence:.2f})")


class FuzzyQuantityDetector:
    """
    Detect and parse fuzzy quantities and approximations.
    """
    
    # Approximation modifiers - EXPANDED
    APPROXIMATION_PATTERNS = [
        # Standard approximations
        r'\b(around|about|approximately|roughly|circa|near|close\s+to|somewhere\s+around)\b',
        r'\b(~|≈)\s*',
        r'\b(give\s+or\s+take|more\s+or\s+less|ballpark)\b',
        # NEW: More approximation patterns
        r'\b(in\s+the\s+(?:range|ballpark|vicinity)\s+of)\b',
        r'\b(approaching|nearing)\b',
        r'\b(somewhere\s+(?:near|around|close\s+to))\b',
        r'\b(on\s+the\s+order\s+of|order\s+of\s+magnitude)\b',
        r'\b(or\s+so|ish)\b',
    ]
    
    # Upper threshold patterns (greater than) - EXPANDED
    UPPER_THRESHOLD_PATTERNS = [
        # Standard upper thresholds
        r'\b(over|above|more\s+than|greater\s+than|higher\s+than|exceeding)\b',
        r'\b(at\s+least|minimum\s+of|no\s+less\s+than|upwards?\s+of)\b',
        r'\b(north\s+of|beyond)\b',
        r'\b>\s*',
        # NEW: More upper threshold patterns
        r'\b(starting\s+at|starting\s+from|beginning\s+at)\b',
        r'\b(in\s+excess\s+of|exceeds?)\b',
        r'\b(surpassing|surpasses?|beating|beats?)\b',
        r'\b(pushing|tops?|topping)\b',
    ]
    
    # Lower threshold patterns (less than) - EXPANDED
    LOWER_THRESHOLD_PATTERNS = [
        # Standard lower thresholds
        r'\b(under|below|less\s+than|fewer\s+than|lower\s+than|smaller\s+than)\b',
        r'\b(at\s+most|maximum\s+of|no\s+more\s+than|up\s+to)\b',
        r'\b(south\s+of|short\s+of)\b',
        r'\b<\s*',
        # NEW: More lower threshold patterns
        r'\b(capped\s+at|maxing\s+out\s+at)\b',
        r'\b(not\s+(?:exceeding|surpassing|topping))\b',
        r'\b(limited\s+to|constrained\s+to)\b',
    ]
    
    # Range patterns
    RANGE_PATTERNS = [
        r'\b(between|from)\s+([\d\$\.,BMKx]+%?)\s+(?:and|to|-)\s+([\d\$\.,BMKx]+%?)\b',
        r'\b([\d\$\.,BMKx]+%?)\s+(?:to|-)\s+([\d\$\.,BMKx]+%?)\s+range\b',
        r'([\d\.]+%)\s*-\s*([\d\.]+%)',  # Percentage ranges: 20%-30%
        r'\$?([\d\.,]+[BMK]?)\s*-\s*\$?([\d\.,]+[BMK]?)',  # Dollar ranges
    ]
    
    # Value patterns (for extraction)
    VALUE_PATTERNS = [
        r'\$[\d\.,]+[BMK]?',      # Dollar amounts: $10B, $5.5M
        r'\d+(?:\.\d+)?%',        # Percentages: 25%, 10.5%
        r'\d+(?:\.\d+)?[xX×]',    # Multiples: 25x, 10.5X
        r'\d+(?:\.\d+)?',         # Plain numbers: 100, 25.5
    ]
    
    def __init__(self):
        """Initialize the fuzzy quantity detector"""
        self._approximation_patterns = [re.compile(p, re.IGNORECASE) for p in self.APPROXIMATION_PATTERNS]
        self._upper_threshold_patterns = [re.compile(p, re.IGNORECASE) for p in self.UPPER_THRESHOLD_PATTERNS]
        self._lower_threshold_patterns = [re.compile(p, re.IGNORECASE) for p in self.LOWER_THRESHOLD_PATTERNS]
        self._range_patterns = [re.compile(p, re.IGNORECASE) for p in self.RANGE_PATTERNS]
        self._value_patterns = [re.compile(p) for p in self.VALUE_PATTERNS]
    
    def detect_fuzzy_quantities(self, text: str) -> List[FuzzyQuantity]:
        """
        Detect all fuzzy quantities in text.
        
        Args:
            text: The query text to analyze
            
        Returns:
            List of FuzzyQuantity objects
        """
        if not text:
            return []
        
        quantities = []
        
        # Check for ranges first (most specific)
        for pattern in self._range_patterns:
            for match in pattern.finditer(text):
                groups = match.groups()
                # Handle different range pattern structures
                if len(groups) >= 3:
                    # Pattern with keyword: "between X and Y"
                    range_start = groups[1] if groups[1] else groups[0]
                    range_end = groups[2] if groups[2] else groups[1]
                elif len(groups) == 2:
                    # Direct range pattern: "X-Y" or "X to Y"
                    range_start = groups[0]
                    range_end = groups[1]
                else:
                    continue
                
                if range_start and range_end:
                    confidence = self._calculate_confidence(
                        text, "range", match.group(0), match.start()
                    )
                    
                    quantities.append(FuzzyQuantity(
                        value=f"{range_start} to {range_end}",
                        fuzzy_type=FuzzyType.RANGE,
                        modifier="range",
                        range_start=range_start,
                        range_end=range_end,
                        tolerance=None,
                        confidence=confidence,
                        position=match.start()
                    ))
        
        # Check for approximations
        quantities.extend(self._detect_approximations(text))
        
        # Check for upper thresholds
        quantities.extend(self._detect_thresholds(text, 'upper'))
        
        # Check for lower thresholds
        quantities.extend(self._detect_thresholds(text, 'lower'))
        
        # Sort by position
        quantities.sort(key=lambda x: x.position)
        
        return quantities
    
    def _detect_approximations(self, text: str) -> List[FuzzyQuantity]:
        """Detect approximation modifiers with values (handles both before and after)"""
        quantities = []
        
        for pattern in self._approximation_patterns:
            for match in pattern.finditer(text):
                modifier = match.group(0)
                
                # Look for value after the modifier
                remaining_text = text[match.end():]
                value_match = self._find_next_value(remaining_text)
                
                if value_match:
                    value = value_match.group(0)
                    
                    # Calculate tolerance based on modifier
                    tolerance = self._infer_tolerance(modifier, value)
                    
                    confidence = self._calculate_confidence(
                        text, modifier, value, match.start()
                    )
                    
                    quantities.append(FuzzyQuantity(
                        value=value,
                        fuzzy_type=FuzzyType.APPROXIMATION,
                        modifier=modifier,
                        range_start=None,
                        range_end=None,
                        tolerance=tolerance,
                        confidence=confidence,
                        position=match.start()
                    ))
                else:
                    # NEW: Check for value BEFORE modifier (e.g., "30% or so")
                    preceding_text = text[:match.start()]
                    # Look for value at the end of preceding text
                    for value_pattern in self._value_patterns:
                        # Search from end backwards
                        matches = list(value_pattern.finditer(preceding_text))
                        if matches:
                            last_match = matches[-1]
                            # Check if value is close to modifier (within 5 chars)
                            if match.start() - last_match.end() <= 5:
                                value = last_match.group(0)
                                tolerance = self._infer_tolerance(modifier, value)
                                confidence = self._calculate_confidence(
                                    text, modifier, value, last_match.start()
                                )
                                
                                quantities.append(FuzzyQuantity(
                                    value=value,
                                    fuzzy_type=FuzzyType.APPROXIMATION,
                                    modifier=modifier,
                                    range_start=None,
                                    range_end=None,
                                    tolerance=tolerance,
                                    confidence=confidence,
                                    position=last_match.start()
                                ))
                                break
        
        return quantities
    
    def _detect_thresholds(self, text: str, threshold_type: str) -> List[FuzzyQuantity]:
        """Detect threshold modifiers (over/under) with values"""
        quantities = []
        
        patterns = (self._upper_threshold_patterns if threshold_type == 'upper' 
                   else self._lower_threshold_patterns)
        fuzzy_type = (FuzzyType.THRESHOLD_UPPER if threshold_type == 'upper' 
                     else FuzzyType.THRESHOLD_LOWER)
        
        for pattern in patterns:
            for match in pattern.finditer(text):
                modifier = match.group(0)
                
                # Look for value after the modifier
                remaining_text = text[match.end():]
                value_match = self._find_next_value(remaining_text)
                
                if value_match:
                    value = value_match.group(0)
                    
                    confidence = self._calculate_confidence(
                        text, modifier, value, match.start()
                    )
                    
                    quantities.append(FuzzyQuantity(
                        value=value,
                        fuzzy_type=fuzzy_type,
                        modifier=modifier,
                        range_start=None,
                        range_end=None,
                        tolerance=None,
                        confidence=confidence,
                        position=match.start()
                    ))
        
        return quantities
    
    def _find_next_value(self, text: str) -> Optional[re.Match]:
        """Find the next numeric value in text"""
        # Try each value pattern
        for pattern in self._value_patterns:
            match = pattern.search(text)
            if match and match.start() < 20:  # Within 20 chars
                return match
        return None
    
    def _infer_tolerance(self, modifier: str, value: str) -> float:
        """
        Infer tolerance/margin from approximation modifier.
        
        Returns:
            Tolerance as a percentage (e.g., 0.10 for ±10%)
        """
        modifier_lower = modifier.lower()
        
        # Strong approximations (wider tolerance)
        if modifier_lower in ['roughly', 'ballpark', 'give or take']:
            return 0.15  # ±15%
        
        # Standard approximations
        if modifier_lower in ['around', 'about', 'approximately', 'circa']:
            return 0.10  # ±10%
        
        # Weak approximations (tighter tolerance)
        if modifier_lower in ['near', 'close to', 'more or less']:
            return 0.05  # ±5%
        
        # Default
        return 0.10
    
    def _calculate_confidence(
        self,
        text: str,
        modifier: str,
        value: str,
        position: int
    ) -> float:
        """
        Calculate confidence for fuzzy quantity detection.
        Context-aware scoring similar to other Phase 2 features.
        """
        confidence = 0.80  # Base confidence
        
        # Boost for explicit modifiers
        strong_modifiers = ['approximately', 'roughly', 'between', 'from', 'over', 'under']
        if any(mod in modifier.lower() for mod in strong_modifiers):
            confidence += 0.10
        
        # Boost for well-formed values
        if re.match(r'\$[\d\.,]+[BMK]', value):  # Dollar with unit
            confidence += 0.05
        elif re.match(r'\d+(?:\.\d+)?%', value):  # Percentage
            confidence += 0.05
        elif re.match(r'\d+(?:\.\d+)?[xX×]', value):  # Multiple
            confidence += 0.05
        
        # Boost for financial context
        financial_context = [
            'revenue', 'profit', 'margin', 'P/E', 'EPS', 'debt',
            'growth', 'valuation', 'cash', 'dividend', 'earnings',
        ]
        text_lower = text.lower()
        if any(term in text_lower for term in financial_context):
            confidence += 0.05
        
        return min(1.0, confidence)
    
    def has_fuzzy_quantity(self, text: str) -> bool:
        """
        Quick check if text contains fuzzy quantities.
        
        Returns:
            True if fuzzy quantity detected, False otherwise
        """
        if not text:
            return False
        
        # Check for any approximation/threshold patterns
        all_patterns = (self._approximation_patterns + 
                       self._upper_threshold_patterns + 
                       self._lower_threshold_patterns +
                       self._range_patterns)
        
        for pattern in all_patterns:
            if pattern.search(text):
                return True
        
        return False
    
    def extract_range_values(self, fuzzy_quantity: FuzzyQuantity) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract min and max values from a fuzzy quantity.
        
        For approximations: applies tolerance to create a range
        For thresholds: returns open-ended range
        For ranges: returns the specified range
        
        Returns:
            Tuple of (min_value, max_value)
        """
        if fuzzy_quantity.fuzzy_type == FuzzyType.RANGE:
            return (fuzzy_quantity.range_start, fuzzy_quantity.range_end)
        
        elif fuzzy_quantity.fuzzy_type == FuzzyType.APPROXIMATION:
            # Apply tolerance to create range
            base_value = self._parse_numeric_value(fuzzy_quantity.value)
            if base_value and fuzzy_quantity.tolerance:
                margin = base_value * fuzzy_quantity.tolerance
                min_val = base_value - margin
                max_val = base_value + margin
                return (str(min_val), str(max_val))
            return (fuzzy_quantity.value, fuzzy_quantity.value)
        
        elif fuzzy_quantity.fuzzy_type == FuzzyType.THRESHOLD_UPPER:
            # Open-ended upper bound
            return (fuzzy_quantity.value, None)
        
        elif fuzzy_quantity.fuzzy_type == FuzzyType.THRESHOLD_LOWER:
            # Open-ended lower bound
            return (None, fuzzy_quantity.value)
        
        else:
            return (fuzzy_quantity.value, fuzzy_quantity.value)
    
    def _parse_numeric_value(self, value: str) -> Optional[float]:
        """Parse numeric value from string (handles $, %, x, B, M, K)"""
        if not value:
            return None
        
        # Remove currency symbols and units
        cleaned = value.replace('$', '').replace('%', '').replace('x', '').replace('X', '').replace('×', '')
        
        # Handle B/M/K suffixes
        multiplier = 1.0
        if 'B' in value or 'b' in value:
            multiplier = 1_000_000_000
            cleaned = cleaned.replace('B', '').replace('b', '')
        elif 'M' in value or 'm' in value:
            multiplier = 1_000_000
            cleaned = cleaned.replace('M', '').replace('m', '')
        elif 'K' in value or 'k' in value:
            multiplier = 1_000
            cleaned = cleaned.replace('K', '').replace('k', '')
        
        # Parse number
        try:
            cleaned = cleaned.replace(',', '')
            number = float(cleaned)
            return number * multiplier
        except ValueError:
            return None


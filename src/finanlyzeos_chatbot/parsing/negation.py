"""
Negation detection and handling for natural language queries.

Handles:
- Basic negation (not, don't, doesn't, isn't, aren't)
- Exclusion (except, excluding, without, other than)
- Negative conditions (less than, under, below, fewer than)
- Negative logic transformations for filters
"""

from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum
import re


class NegationType(Enum):
    """Types of negation"""
    BASIC = "basic"              # not, don't, isn't
    EXCLUSION = "exclusion"      # except, excluding, without
    THRESHOLD = "threshold"      # less than, under, below
    NONE_TYPE = "none"           # none, no, neither


@dataclass
class NegationSpan:
    """
    Represents a detected negation in text.
    """
    type: NegationType
    negation_word: str       # The negation word/phrase (e.g., "not", "excluding")
    scope: str               # What the negation applies to
    scope_start: int         # Start position of scope
    scope_end: int           # End position of scope
    confidence: float        # Confidence score (0.0 to 1.0)
    
    def __repr__(self):
        return (f"NegationSpan(type={self.type.value}, "
                f"word='{self.negation_word}', "
                f"scope='{self.scope}', "
                f"confidence={self.confidence:.2f})")


class NegationDetector:
    """
    Detect and handle negation in natural language queries.
    """
    
    # Basic negation patterns (EXPANDED - 50+ patterns)
    NEGATION_PATTERNS = {
        'basic': [
            # Standard negations
            r'\b(not|no|don\'t|doesn\'t|didn\'t|isn\'t|aren\'t|wasn\'t|weren\'t)\b',
            r'\b(haven\'t|hasn\'t|hadn\'t|won\'t|wouldn\'t|shouldn\'t|can\'t|couldn\'t)\b',
            r'\b(never|neither|nor|none)\b',
            # NEW: More contractions
            r'\b(ain\'t|shan\'t|mustn\'t|needn\'t|daren\'t|oughtn\'t)\b',
            # NEW: Implicit negations
            r'\b(lacks?|lacking|missing|absent|free\s+of|devoid\s+of)\b',
            r'\b(fails?\s+to|failed\s+to|failing\s+to)\b',
            r'\b(refuses?\s+to|refused\s+to|avoiding?|avoids?)\b',
            # NEW: Negative prefixes in financial context
            r'\b(non-profitable|non-competitive|unprofitable|underperforming)\b',
            r'\b(inefficient|inadequate|insufficient|weak)\b',
        ],
        'threshold': [
            # Standard thresholds (MUST BE CHECKED BEFORE EXCLUSION to avoid "less" conflict)
            r'\b(less\s+than|under|below|fewer\s+than|lower\s+than|smaller\s+than)\b',
            r'\b(at\s+most|no\s+more\s+than|not\s+(?:more|higher|greater|exceeding|surpassing)\s+than)\b',
            # NEW: More threshold variations (multi-word patterns first)
            r'\b(not\s+exceeding|not\s+surpassing|short\s+of)\b',
            r'\b(up\s+to|maximum\s+of|max|capped\s+at)\b',
            r'\b(within|inside)\b',
        ],
        'exclusion': [
            # Standard exclusions
            r'\b(except|excluding|without|other\s+than|besides|aside\s+from|apart\s+from)\b',
            r'\b(but\s+not|rather\s+than|instead\s+of)\b',
            # NEW: More exclusion variations (NOTE: removed "less" and "minus" to avoid threshold conflicts)
            r'\b(save\s+for|with\s+the\s+exception\s+of|barring|exclusive\s+of)\b',
            r'\b(leaving\s+out|omitting)\b',
            r'\b(outside\s+of|beyond)\b',
        ],
    }
    
    # NEW: False positive patterns (NOT negations in these contexts)
    FALSE_POSITIVE_PATTERNS = [
        # Questions about negation aren't negations themselves
        r'\bwhy\s+(?:not|isn\'t|aren\'t|don\'t)\b',
        r'\bwhat\s+if\s+(?:not|isn\'t)\b',
        r'\bhow\s+(?:not|isn\'t)\b',
        # Rhetorical/hypothetical
        r'\bif\s+(?:not|isn\'t|weren\'t)\b',
        r'\bunless\s+(?:not|isn\'t)\b',
        # Common phrases that aren't negations
        r'\bwhy\s+not\?',
        r'\bnot\s+only',
        r'\bnot\s+just',
        r'\bnot\s+to\s+mention',
    ]
    
    # Patterns for detecting what the negation applies to
    SCOPE_PATTERNS = [
        # Adjective negation: "not risky", "isn't overvalued"
        r'(not|isn\'t|aren\'t)\s+([\w\s]+?)(?:\b(?:and|or|,|\.|\?|$))',
        
        # Verb negation: "don't have", "doesn't show"
        r'(don\'t|doesn\'t|didn\'t)\s+([\w\s]+?)(?:\b(?:and|or|,|\.|\?|$))',
        
        # Exclusion: "excluding tech", "except financials"
        r'(except|excluding|without|other\s+than)\s+([\w\s]+?)(?:\b(?:and|or|,|\.|\?|$))',
        
        # Threshold: "less than 20", "under $10B"
        r'(less\s+than|under|below)\s+([\d\$\.,BMK%x]+)',
    ]
    
    def __init__(self):
        """Initialize the negation detector"""
        self._compiled_patterns = self._compile_patterns()
        self._false_positive_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.FALSE_POSITIVE_PATTERNS
        ]
    
    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Pre-compile all regex patterns for efficiency"""
        compiled = {}
        
        # Compile negation type patterns
        for neg_type, patterns in self.NEGATION_PATTERNS.items():
            compiled[f'negation_{neg_type}'] = [re.compile(p, re.IGNORECASE) for p in patterns]
        
        # Compile scope patterns
        compiled['scope'] = [re.compile(p, re.IGNORECASE) for p in self.SCOPE_PATTERNS]
        
        return compiled
    
    def detect_negations(self, text: str) -> List[NegationSpan]:
        """
        Detect all negations in text and their scopes.
        
        Args:
            text: The query text to analyze
            
        Returns:
            List of NegationSpan objects
        """
        if not text:
            return []
        
        # NEW: Check for false positives first
        if self._is_false_positive(text):
            return []
        
        negations = []
        
        # Detect each type of negation (CHECK THRESHOLD BEFORE EXCLUSION to avoid pattern conflicts)
        for neg_type in ['threshold', 'exclusion', 'basic']:
            for pattern in self._compiled_patterns[f'negation_{neg_type}']:
                for match in pattern.finditer(text):
                    negation_word = match.group(0)
                    
                    # NEW: Skip if this specific match is a false positive
                    context_start = max(0, match.start() - 20)
                    context_end = min(len(text), match.end() + 20)
                    local_context = text[context_start:context_end]
                    if self._is_false_positive(local_context):
                        continue
                    
                    # Determine scope (what the negation applies to)
                    scope, scope_start, scope_end = self._extract_scope(
                        text,
                        match.end(),
                        negation_word
                    )
                    
                    # Calculate confidence
                    confidence = self._calculate_confidence_enhanced(
                        text,
                        negation_word,
                        scope,
                        match.start()
                    )
                    
                    negations.append(NegationSpan(
                        type=NegationType[neg_type.upper()] if neg_type != 'threshold' else NegationType.THRESHOLD,
                        negation_word=negation_word,
                        scope=scope,
                        scope_start=scope_start,
                        scope_end=scope_end,
                        confidence=confidence
                    ))
        
        return negations
    
    def _extract_scope(
        self,
        text: str,
        negation_end_pos: int,
        negation_word: str
    ) -> Tuple[str, int, int]:
        """
        Extract what the negation applies to (ENHANCED for complex phrases).
        
        Returns:
            Tuple of (scope_text, start_position, end_position)
        """
        # Get text after the negation word
        remaining = text[negation_end_pos:].strip()
        
        if not remaining:
            return ("", negation_end_pos, negation_end_pos)
        
        # NEW: Handle multi-word financial phrases better
        # Look for complete phrases like "high debt levels", "excessive risk"
        financial_phrase_pattern = r'(?:high|low|excessive|minimal|significant|substantial)\s+\w+(?:\s+\w+)?'
        phrase_match = re.match(financial_phrase_pattern, remaining, re.IGNORECASE)
        
        if phrase_match:
            scope_text = phrase_match.group(0).strip()
            scope_end = negation_end_pos + phrase_match.end()
            return (scope_text, negation_end_pos, scope_end)
        
        # Find the end of the scope (stops at punctuation or conjunctions)
        end_markers = r'\b(and|or|but|,|\.|\?|;|$)'
        end_match = re.search(end_markers, remaining)
        
        if end_match:
            scope_text = remaining[:end_match.start()].strip()
            scope_end = negation_end_pos + end_match.start()
        else:
            scope_text = remaining.strip()
            scope_end = len(text)
        
        scope_start = negation_end_pos
        
        return (scope_text, scope_start, scope_end)
    
    def _calculate_confidence(
        self,
        text: str,
        negation_word: str,
        scope: str
    ) -> float:
        """Calculate confidence for negation detection (LEGACY - use _calculate_confidence_enhanced)"""
        return self._calculate_confidence_enhanced(text, negation_word, scope, 0)
    
    def _calculate_confidence_enhanced(
        self,
        text: str,
        negation_word: str,
        scope: str,
        negation_pos: int
    ) -> float:
        """
        Calculate confidence for negation detection with enhanced context awareness.
        Similar to spelling/comparative/trend confidence scoring.
        """
        confidence = 0.75  # Base confidence
        
        # Boost for clear negation words
        strong_negations = ['not', 'no', "isn't", "aren't", "don't", "doesn't", 'excluding', 'except', 'without']
        if negation_word.lower() in strong_negations:
            confidence += 0.10
        
        # Boost for specific scope
        if scope and len(scope) > 0:
            confidence += 0.05
            
            # Extra boost for multi-word scopes (more specific)
            if len(scope.split()) >= 2:
                confidence += 0.03
        
        # Boost for financial context in scope
        financial_terms = {
            'risky', 'overvalued', 'expensive', 'debt', 'leverage', 'volatile',
            'profitable', 'competitive', 'efficient', 'growing', 'stable',
            'valuation', 'margins', 'revenue', 'earnings', 'cash flow',
        }
        scope_lower = scope.lower() if scope else ""
        financial_matches = sum(1 for term in financial_terms if term in scope_lower)
        if financial_matches > 0:
            confidence += min(0.10, financial_matches * 0.05)
        
        # Boost for question context (clear intent)
        if re.search(r'\b(show|find|get|list|which|what|who)\b', text.lower()):
            confidence += 0.05
        
        # Boost for comparative context
        if re.search(r'\b(that|which|who)\s+(?:are|is|have|has)\b', text.lower()):
            confidence += 0.05
        
        # Penalty for ambiguous negations
        weak_negations = ['lacks', 'missing', 'weak', 'within']
        if negation_word.lower() in weak_negations:
            confidence -= 0.05
        
        return min(1.0, max(0.5, confidence))
    
    def _is_false_positive(self, text: str) -> bool:
        """
        Check if text contains false positive negation patterns.
        
        Returns:
            True if false positive detected, False otherwise
        """
        if not text:
            return False
        
        for pattern in self._false_positive_patterns:
            if pattern.search(text):
                return True
        
        return False
    
    def has_negation(self, text: str) -> bool:
        """
        Quick check if text contains any negation.
        
        Returns:
            True if negation detected, False otherwise
        """
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Check all negation patterns
        for neg_type in ['basic', 'exclusion', 'threshold']:
            for pattern in self._compiled_patterns[f'negation_{neg_type}']:
                if pattern.search(text_lower):
                    return True
        
        return False
    
    def apply_negation_to_filters(
        self,
        filters: Dict[str, Any],
        negations: List[NegationSpan]
    ) -> Dict[str, Any]:
        """
        Transform filters based on detected negations.
        
        Examples:
        - "P/E not above 30" → "P/E <= 30"
        - "excluding tech" → "sector NOT IN ['tech']"
        - "less than $10B" → "< $10B"
        
        Args:
            filters: Original filter dict
            negations: List of detected negations
            
        Returns:
            Modified filter dict with negations applied
        """
        modified_filters = filters.copy()
        
        for negation in negations:
            if negation.type == NegationType.BASIC:
                # Basic negation: flip the condition
                # "not risky" → "risk_level != 'high'"
                self._apply_basic_negation(modified_filters, negation)
            
            elif negation.type == NegationType.EXCLUSION:
                # Exclusion: add to exclusion list
                # "excluding tech" → "sector NOT IN ['tech']"
                self._apply_exclusion(modified_filters, negation)
            
            elif negation.type == NegationType.THRESHOLD:
                # Threshold: set upper bound
                # "less than $10B" → "< $10B"
                self._apply_threshold(modified_filters, negation)
        
        return modified_filters
    
    def _apply_basic_negation(self, filters: Dict, negation: NegationSpan) -> None:
        """Apply basic negation to filters"""
        scope = negation.scope.lower()
        
        # Map common negated adjectives to filter conditions
        negation_mapping = {
            'risky': {'risk_level': {'operator': '!=', 'value': 'high'}},
            'overvalued': {'valuation': {'operator': '!=', 'value': 'overvalued'}},
            'expensive': {'valuation': {'operator': '!=', 'value': 'expensive'}},
            'volatile': {'volatility': {'operator': '!=', 'value': 'high'}},
            'leveraged': {'debt_level': {'operator': '!=', 'value': 'high'}},
        }
        
        for key, filter_spec in negation_mapping.items():
            if key in scope:
                filters.update(filter_spec)
                break
    
    def _apply_exclusion(self, filters: Dict, negation: NegationSpan) -> None:
        """Apply exclusion to filters"""
        scope = negation.scope.lower()
        
        # Common exclusions
        if 'tech' in scope or 'technology' in scope:
            filters.setdefault('sector_exclude', []).append('Technology')
        elif 'financial' in scope or 'finance' in scope:
            filters.setdefault('sector_exclude', []).append('Financials')
        elif 'energy' in scope:
            filters.setdefault('sector_exclude', []).append('Energy')
    
    def _apply_threshold(self, filters: Dict, negation: NegationSpan) -> None:
        """Apply threshold negation to filters"""
        scope = negation.scope.strip()
        
        # Extract value from scope
        value_match = re.search(r'([\d\.,]+)([BMK%]?)', scope)
        if value_match:
            value = value_match.group(0)
            
            # Determine what metric this threshold applies to
            # Context analysis would go here
            # For now, store as generic threshold
            filters['threshold_upper'] = value


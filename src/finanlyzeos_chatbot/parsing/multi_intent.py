"""
Multi-intent detection and handling for natural language queries.

Handles queries with multiple requests or intents:
- "Show revenue AND analyze risk"
- "Compare Apple and Microsoft then tell me which is better"
- "What's the P/E ratio or the EPS?"
- "Get revenue, margins, and debt levels"
"""

from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum
import re


class ConjunctionType(Enum):
    """Types of conjunctions connecting intents"""
    AND = "and"           # Parallel: both needed
    OR = "or"             # Alternative: either works
    THEN = "then"         # Sequential: do first, then second
    ALSO = "also"         # Additive: plus this too
    COMMA = "comma"       # List: multiple items


@dataclass
class SubIntent:
    """
    Represents a single intent within a multi-intent query.
    """
    text: str                    # The sub-query text
    position: int                # Position in original query
    intent_type: Optional[str]   # Classified intent (question, lookup, etc.)
    confidence: float            # Confidence this is a valid sub-intent
    
    def __repr__(self):
        return (f"SubIntent(text='{self.text}', "
                f"intent={self.intent_type}, "
                f"confidence={self.confidence:.2f})")


@dataclass
class MultiIntentQuery:
    """
    Represents a query with multiple intents.
    """
    sub_intents: List[SubIntent]      # List of detected sub-intents
    conjunction: ConjunctionType      # How they're connected
    is_multi_intent: bool             # Whether this is truly multi-intent
    confidence: float                 # Overall confidence score
    
    def __repr__(self):
        return (f"MultiIntentQuery(intents={len(self.sub_intents)}, "
                f"conjunction={self.conjunction.value}, "
                f"confidence={self.confidence:.2f})")


class MultiIntentDetector:
    """
    Detect and decompose queries with multiple intents.
    """
    
    # Conjunction patterns (ordered by specificity) - MASSIVELY EXPANDED
    CONJUNCTION_PATTERNS = {
        'then': [
            r'\b(?:and\s+)?then\b',
            r'\bafter\s+(?:that|which|this)\b',
            r'\bfollowed\s+by\b',
            # NEW: More sequential patterns
            r'\bnext\b',
            r'\bafterwards?\b',
            r'\bsubsequently\b',
            r'\bfinally\b',
            r'\blastly\b',
        ],
        'also': [
            r'\b(?:and\s+)?also\b',
            r'\bplus\b',
            r'\badditionally\b',
            r'\bas\s+well\s+as\b',
            # NEW: More additive patterns
            r'\bfurthermore\b',
            r'\bmoreover\b',
            r'\bbesides\b',
            r'\bin\s+addition\b',
            r'\balong\s+with\b',
            r'\btogether\s+with\b',
        ],
        'and': [
            r'\band\b',
            r'\b&\b',
            # NEW: Expanded AND patterns
            r'\bwhile\b',
            r'\bwhilst\b',
        ],
        'or': [
            r'\bor\b',
            r'\b(?:either|whether)\b',
            # NEW: More alternative patterns
            r'\balternatively\b',
            r'\botherwise\b',
        ],
        'comma': [
            r',\s+(?:and\s+)?',
        ],
    }
    
    # NEW: False positive patterns (DON'T split on these)
    FALSE_POSITIVE_PATTERNS = [
        # Company names with "and"
        r'\b(?:Procter|P)\s+(?:and|&)\s+(?:Gamble|G)\b',
        r'\bAT\s*&\s*T\b',
        r'\bBarnes\s+(?:and|&)\s+Noble\b',
        r'\bBed\s+Bath\s+(?:and|&)\s+Beyond\b',
        # Common phrases
        r'\bup\s+and\s+down\b',
        r'\bhere\s+and\s+there\b',
        r'\bnow\s+and\s+then\b',
        r'\bon\s+and\s+off\b',
        # Financial phrases
        r'\bmergers?\s+and\s+acquisitions?\b',
        r'\bM\s*&\s*A\b',
        r'\bincome\s+and\s+expenses?\b',
        r'\bassets?\s+and\s+liabilities\b',
    ]
    
    # Intent markers that suggest separate requests
    INTENT_MARKERS = [
        # Questions
        r'\b(what|which|how|when|where|who|why|is|are|does|do|can|could|would|should)\b',
        # Commands
        r'\b(show|display|get|find|list|tell|give|provide|analyze|compare|explain)\b',
        # Conditionals
        r'\bif\b',
    ]
    
    def __init__(self):
        """Initialize the multi-intent detector"""
        self._compiled_conjunctions = self._compile_conjunctions()
        self._compiled_markers = [re.compile(p, re.IGNORECASE) for p in self.INTENT_MARKERS]
        self._false_positive_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.FALSE_POSITIVE_PATTERNS
        ]
    
    def _compile_conjunctions(self) -> Dict[str, List[re.Pattern]]:
        """Pre-compile conjunction patterns"""
        compiled = {}
        for conj_type, patterns in self.CONJUNCTION_PATTERNS.items():
            compiled[conj_type] = [re.compile(p, re.IGNORECASE) for p in patterns]
        return compiled
    
    def detect_multi_intent(self, text: str) -> MultiIntentQuery:
        """
        Detect if query contains multiple intents and decompose it.
        
        Args:
            text: The query text to analyze
            
        Returns:
            MultiIntentQuery object with detected sub-intents
        """
        if not text:
            return MultiIntentQuery(
                sub_intents=[],
                conjunction=ConjunctionType.AND,
                is_multi_intent=False,
                confidence=0.0
            )
        
        # NEW: Check for false positives first
        if self._is_false_positive_context(text):
            # Don't split - treat as single intent
            return MultiIntentQuery(
                sub_intents=[SubIntent(
                    text=text,
                    position=0,
                    intent_type=self._classify_sub_intent(text),
                    confidence=1.0
                )],
                conjunction=ConjunctionType.AND,
                is_multi_intent=False,
                confidence=1.0
            )
        
        # Check for conjunctions
        conjunction, conj_positions = self._find_conjunctions(text)
        
        if not conj_positions:
            # Single intent
            return MultiIntentQuery(
                sub_intents=[SubIntent(
                    text=text,
                    position=0,
                    intent_type=None,
                    confidence=1.0
                )],
                conjunction=ConjunctionType.AND,
                is_multi_intent=False,
                confidence=1.0
            )
        
        # Split by conjunctions
        sub_intents = self._split_by_conjunctions(text, conj_positions)
        
        # Validate each sub-intent
        validated_intents = []
        for sub_text, position in sub_intents:
            if self._is_valid_sub_intent(sub_text):
                intent_type = self._classify_sub_intent(sub_text)
                confidence = self._calculate_sub_intent_confidence(sub_text, intent_type)
                
                validated_intents.append(SubIntent(
                    text=sub_text.strip(),
                    position=position,
                    intent_type=intent_type,
                    confidence=confidence
                ))
        
        # Determine if truly multi-intent
        is_multi = len(validated_intents) > 1
        overall_confidence = self._calculate_overall_confidence(validated_intents, conjunction)
        
        return MultiIntentQuery(
            sub_intents=validated_intents,
            conjunction=conjunction,
            is_multi_intent=is_multi,
            confidence=overall_confidence
        )
    
    def _find_conjunctions(self, text: str) -> Tuple[ConjunctionType, List[Tuple[int, int, str]]]:
        """
        Find all conjunctions in text.
        
        Returns:
            Tuple of (conjunction_type, [(start, end, matched_text)])
        """
        all_matches = []
        
        # Check each conjunction type (order matters - most specific first)
        # PRIORITY: then > also > and > or > comma
        for conj_type in ['then', 'also', 'and', 'or', 'comma']:
            for pattern in self._compiled_conjunctions[conj_type]:
                for match in pattern.finditer(text):
                    all_matches.append((
                        conj_type,
                        match.start(),
                        match.end(),
                        match.group(0)
                    ))
        
        if not all_matches:
            return (ConjunctionType.AND, [])
        
        # Sort by position
        all_matches.sort(key=lambda x: x[1])
        
        # Determine primary conjunction type
        # Priority: then > also > and > or > comma (most specific first)
        priority_order = ['then', 'also', 'and', 'or', 'comma']
        primary_type = all_matches[0][0]
        
        for priority_conj in priority_order:
            for match in all_matches:
                if match[0] == priority_conj:
                    primary_type = priority_conj
                    break
            if primary_type == priority_conj:
                break
        
        # Return positions for splitting (filter to only use matches of the primary type or stronger)
        primary_priority = priority_order.index(primary_type)
        positions = [
            (m[1], m[2], m[3]) 
            for m in all_matches 
            if priority_order.index(m[0]) <= primary_priority
        ]
        return (ConjunctionType[primary_type.upper()], positions)
    
    def _split_by_conjunctions(
        self,
        text: str,
        conj_positions: List[Tuple[int, int, str]]
    ) -> List[Tuple[str, int]]:
        """
        Split text by conjunction positions.
        
        Returns:
            List of (sub_text, position) tuples
        """
        if not conj_positions:
            return [(text, 0)]
        
        sub_intents = []
        last_end = 0
        
        for start, end, _ in conj_positions:
            # Get text before conjunction
            if start > last_end:
                sub_text = text[last_end:start].strip()
                if sub_text:
                    sub_intents.append((sub_text, last_end))
            last_end = end
        
        # Get remaining text after last conjunction
        if last_end < len(text):
            sub_text = text[last_end:].strip()
            if sub_text:
                sub_intents.append((sub_text, last_end))
        
        return sub_intents
    
    def _is_false_positive_context(self, text: str) -> bool:
        """
        Check if text contains false positive patterns that shouldn't be split.
        
        Returns:
            True if false positive detected, False otherwise
        """
        if not text:
            return False
        
        for pattern in self._false_positive_patterns:
            if pattern.search(text):
                return True
        
        return False
    
    def _is_valid_sub_intent(self, text: str) -> bool:
        """
        Check if text represents a valid sub-intent (ENHANCED validation).
        
        Returns:
            True if valid, False otherwise
        """
        if not text or len(text.strip()) < 3:
            return False
        
        # NEW: Check if this is just a fragment (too short to be meaningful)
        words = text.strip().split()
        if len(words) == 1 and words[0].lower() not in ['revenue', 'profit', 'risk', 'debt', 'eps', 'p/e']:
            # Single word that's not a key metric - likely a fragment
            return False
        
        # Check for intent markers
        for pattern in self._compiled_markers:
            if pattern.search(text):
                return True
        
        # Check for financial keywords (EXPANDED)
        financial_keywords = [
            'revenue', 'profit', 'earnings', 'margin', 'margins', 'growth', 'debt',
            'risk', 'valuation', 'P/E', 'EPS', 'cash', 'dividend', 'FCF',
            'Apple', 'Microsoft', 'Google', 'Amazon', 'Tesla', 'Meta', 'Netflix',
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NFLX',
            'company', 'stock', 'shares', 'market', 'price', 'ratio',
        ]
        text_lower = text.lower()
        if any(keyword.lower() in text_lower for keyword in financial_keywords):
            return True
        
        return False
    
    def _classify_sub_intent(self, text: str) -> Optional[str]:
        """
        Classify the intent type of a sub-query.
        
        Returns:
            Intent type string or None
        """
        text_lower = text.lower()
        
        # Question patterns
        if re.search(r'\b(what|which|how|who|when|where|why)\b', text_lower):
            return "question"
        
        # Command patterns
        if re.search(r'\b(show|display|get|find|list|give)\b', text_lower):
            return "command"
        
        # Analysis patterns
        if re.search(r'\b(analyze|assess|evaluate|examine|review)\b', text_lower):
            return "analysis"
        
        # Comparison patterns
        if re.search(r'\b(compare|versus|vs|better|worse|which)\b', text_lower):
            return "comparison"
        
        # Default to lookup
        return "lookup"
    
    def _calculate_sub_intent_confidence(self, text: str, intent_type: Optional[str]) -> float:
        """
        Calculate confidence for a sub-intent (ENHANCED context-aware scoring).
        Similar to other Phase 2 confidence scoring.
        """
        confidence = 0.70  # Base confidence
        
        # Boost for clear intent markers
        if intent_type:
            confidence += 0.15
        
        # Boost for complete sentences
        word_count = len(text.split())
        if word_count >= 3:
            confidence += 0.08
        elif word_count >= 5:
            confidence += 0.12  # Even better for longer
        
        # Boost for financial context
        financial_terms = {
            'revenue', 'profit', 'risk', 'valuation', 'P/E', 'EPS', 'margin',
            'growth', 'debt', 'cash', 'dividend', 'earnings', 'ROE', 'ROA',
        }
        text_lower = text.lower()
        financial_matches = sum(1 for term in financial_terms if term.lower() in text_lower)
        if financial_matches > 0:
            confidence += min(0.10, financial_matches * 0.05)
        
        # NEW: Boost for company mentions
        company_pattern = r'\b(Apple|Microsoft|Google|Amazon|Tesla|Meta|AAPL|MSFT|GOOGL|AMZN|TSLA)\b'
        if re.search(company_pattern, text, re.IGNORECASE):
            confidence += 0.03
        
        # NEW: Penalty for fragments (very short or no verbs)
        if word_count < 2:
            confidence -= 0.10
        
        return min(1.0, max(0.5, confidence))
    
    def _calculate_overall_confidence(
        self,
        sub_intents: List[SubIntent],
        conjunction: ConjunctionType
    ) -> float:
        """
        Calculate overall confidence for multi-intent detection (ENHANCED).
        """
        if not sub_intents:
            return 0.0
        
        if len(sub_intents) == 1:
            return sub_intents[0].confidence
        
        # Average of sub-intent confidences
        avg_confidence = sum(si.confidence for si in sub_intents) / len(sub_intents)
        
        # Boost for clear conjunctions
        if conjunction in [ConjunctionType.THEN, ConjunctionType.ALSO]:
            avg_confidence += 0.05
        elif conjunction == ConjunctionType.AND:
            avg_confidence += 0.03
        
        # NEW: Boost if all sub-intents have similar confidence (consistent quality)
        if len(sub_intents) > 1:
            confidences = [si.confidence for si in sub_intents]
            std_dev = (sum((c - avg_confidence) ** 2 for c in confidences) / len(confidences)) ** 0.5
            if std_dev < 0.1:  # Very consistent
                avg_confidence += 0.05
        
        # NEW: Boost if sub-intents have good variety (different intent types)
        intent_types = set(si.intent_type for si in sub_intents if si.intent_type)
        if len(intent_types) >= 2:
            avg_confidence += 0.03
        
        # Penalty for too many sub-intents (might be over-splitting)
        if len(sub_intents) > 4:
            avg_confidence -= 0.05
        elif len(sub_intents) > 6:
            avg_confidence -= 0.10  # Even more penalty
        
        # NEW: Penalty if any sub-intent is very short/weak
        min_confidence = min(si.confidence for si in sub_intents)
        if min_confidence < 0.60:
            avg_confidence -= 0.05
        
        return min(1.0, max(0.0, avg_confidence))
    
    def is_multi_intent(self, text: str) -> bool:
        """
        Quick check if text contains multiple intents.
        
        Returns:
            True if multi-intent detected, False otherwise
        """
        if not text:
            return False
        
        result = self.detect_multi_intent(text)
        return result.is_multi_intent

